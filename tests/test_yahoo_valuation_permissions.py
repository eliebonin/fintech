"""Explicit local personal valuation activation never grants commercial use."""
from datetime import date
from sqlalchemy import select,func
import pytest
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_personal_valuation_is_explicit_scoped_repeatable_and_not_reactivated():
    from market_data.providers.yahoo.valuation_permissions import enable_personal_valuation
    from market_data.providers.yahoo.onboarding import enable_personal_research
    from market_data.providers.yahoo.fx_storage import configure_fx
    from market_data.rights import load_rights
    from security_master_schema.index_universe_seed import seed
    engine=get_engine()
    assert engine.url.database.startswith('fortem_isolated_tests_')
    with engine.connect() as c:
        tx=c.begin()
        try:
            seed(c,ids['demo_user_account'])
            equity=enable_personal_research(c,ids['tenant'],ids['demo_user_account'],'Synthetic research approval')
            fx=configure_fx(c,ids['tenant'],ids['demo_user_account'])
            before=c.scalar(select(func.count()).select_from(m.market_data_observation))
            for dataset in (equity['datasetId'],fx['datasetId']):
                args=(c,ids['tenant'],ids['demo_user_account'],dataset,'Synthetic personal valuation approval')
                first=enable_personal_valuation(*args)
                assert enable_personal_valuation(*args)==first
                assert load_rights(c,dataset,'NON_DISPLAY',date.today(),'PERSONAL').allowed
                assert not load_rights(c,dataset,'NON_DISPLAY',date.today(),'COMMERCIAL').allowed
                assert not load_rights(c,dataset,'REDISTRIBUTE',date.today()).allowed
                ent=c.execute(select(m.tenant_dataset_entitlement).where(
                    m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id==first['entitlementId'])).mappings().one()
                assert ent['use_purpose']=='VALUATION' and ent['coverage_mode']=='DATASET'
                assert ent['tenant_id']==ids['tenant']
                with pytest.raises(PermissionError):
                    enable_personal_valuation(c,ids['second_tenant'],ids['demo_user_account'],dataset,'Other tenant')
                c.execute(m.tenant_dataset_entitlement.update().where(
                    m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id==ent['tenant_dataset_entitlement_id']).values(status='SUSPENDED'))
                with pytest.raises(ValueError,match='reactivat'):
                    enable_personal_valuation(*args)
            assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before
        finally:
            tx.rollback()


def test_empty_evidence_and_non_yahoo_datasets_are_rejected():
    from market_data.providers.yahoo.valuation_permissions import enable_personal_valuation
    with get_engine().connect() as c:
        with pytest.raises(ValueError,match='reference'):
            enable_personal_valuation(c,ids['tenant'],ids['demo_user_account'],ids['dataset'],' ')
        with pytest.raises(ValueError,match='Yahoo'):
            enable_personal_valuation(c,ids['tenant'],ids['demo_user_account'],ids['dataset'],'Synthetic approval')
