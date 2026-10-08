"""Personal onboarding does not grant commercial rights or rewrite the master."""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def test_symbols_are_venue_specific():
    from market_data.providers.yahoo.onboarding import yahoo_symbol
    assert yahoo_symbol('BRK.B', 'XNYS') == 'BRK-B'
    assert yahoo_symbol('AIR', 'XPAR') == 'AIR.PA'
    assert yahoo_symbol('MT', 'XAMS') == 'MT.AS'
    with pytest.raises(ValueError):
        yahoo_symbol('FOO', 'UNKNOWN')


def test_personal_setup_is_repeatable_and_scoped_without_financial_writes():
    from market_data.providers.yahoo.onboarding import onboard_personal
    from market_data.rights import load_rights
    from security_master_schema.index_universe_seed import seed
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            seed(c, DEMO_IDS['demo_user_account'])
            from tests.test_api_reference_authority import revoke_module
            revoke_module(c, 'MARKET_DATA')
            before = c.scalar(select(func.count()).select_from(m.market_data_observation))
            first = onboard_personal(c, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], 'User declared local personal project')
            second = onboard_personal(c, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], 'User declared local personal project')
            assert first['datasetId'] == second['datasetId']
            from security_master_schema.tenant_workspace import resolve_tenant_workspace
            assert 'MARKET_DATA' in resolve_tenant_workspace(c, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], date.today()).module_codes
            assert len(first['mappings']) == 543
            assert c.scalar(select(func.count()).select_from(m.market_data_observation)) == before
            profile = c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id == first['datasetId'])).mappings().one()
            assert profile['usage_scope'] == 'PERSONAL' and profile['permitted_tenant_id'] == DEMO_IDS['tenant']
            assert load_rights(c, first['datasetId'], 'DISPLAY', date.today()).allowed
            acquisition = load_rights(c, first['datasetId'], 'ACQUIRE', date.today())
            assert not acquisition.allowed and 'AUTOMATED_SOURCE_ACCESS' in acquisition.reason
            assert not load_rights(c, first['datasetId'], 'DISPLAY', date.today(), 'COMMERCIAL').allowed
            assert not load_rights(c, first['datasetId'], 'REDISTRIBUTE', date.today()).allowed
            assert c.scalar(select(func.count()).select_from(m.tenant_dataset_entitlement).where(
                m.tenant_dataset_entitlement.c.dataset_id == first['datasetId'],
                m.tenant_dataset_entitlement.c.tenant_id == DEMO_IDS['second_tenant'])) == 0
            with pytest.raises(ValueError, match='different tenant'):
                onboard_personal(c, DEMO_IDS['second_tenant'], DEMO_IDS['demo_user_account'], 'User declaration')
        finally:
            tx.rollback()


def test_missing_actor_cannot_onboard_dataset():
    from market_data.providers.yahoo.onboarding import onboard_personal
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            with pytest.raises(ValueError, match='active'):
                onboard_personal(c, DEMO_IDS['tenant'], uuid4(), 'User declaration')
        finally:
            tx.rollback()


def test_explicit_research_exception_is_audited_repeatable_and_not_reactivated():
    from market_data.providers.yahoo.onboarding import enable_personal_research
    from market_data.rights import load_rights
    from security_master_schema.index_universe_seed import seed
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            seed(c, DEMO_IDS['demo_user_account'])
            args = (c, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], 'Owner approval on 2026-10-07')
            first = enable_personal_research(*args)
            second = enable_personal_research(*args)
            assert first['datasetId'] == second['datasetId']
            decision = load_rights(c, first['datasetId'], 'ACQUIRE', date.today(), 'PERSONAL')
            assert decision.allowed
            exceptions = [e for e in decision.evidence if e['basis'] == 'PERSONAL_RESEARCH_EXCEPTION']
            assert len(exceptions) == 1
            assert str(DEMO_IDS['demo_user_account']) in exceptions[0]['reference']
            assert 'not provider permission' in exceptions[0]['reference']
            assert not load_rights(c, first['datasetId'], 'ACQUIRE', date.today(), 'COMMERCIAL').allowed
            assert not load_rights(c, first['datasetId'], 'REDISTRIBUTE', date.today()).allowed
            c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.grant_id == exceptions[0]['grantId']).values(status='SUSPENDED'))
            with pytest.raises(ValueError, match='not effective'):
                enable_personal_research(*args)
            assert not load_rights(c, first['datasetId'], 'ACQUIRE', date.today()).allowed
        finally:
            tx.rollback()
