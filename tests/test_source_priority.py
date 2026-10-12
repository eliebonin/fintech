"""Preferences must beat arrival times, never eligibility or market date."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_preferred_same_date_source_beats_later_arrival_but_not_newer_market_date():
    from market_data.source_priority import choose_row
    now=datetime.now(timezone.utc)
    def row(source,day,received):
        return dict(dataset_id=source,market_date=day,received_at_utc=received,observed_at_utc=received,market_data_observation_id=uuid4())
    rows=[row('first',date(2026,10,7),now-timedelta(hours=1)), row('second',date(2026,10,7),now)]
    priority=dict(datasetIds=['first','second'])
    assert choose_row(rows,priority)['dataset_id']=='first'
    rows.append(row('second',date(2026,10,8),now))
    assert choose_row(rows,priority)['market_date']==date(2026,10,8)
    assert choose_row(rows,dict(datasetIds=[])) is None
    assert choose_row(rows,dict(datasetIds=['unrelated'])) is None


def test_saved_exclusion_blocks_even_an_explicit_policy_dataset_and_freezes_evidence():
    from apps.reference_api.market_data_sources import save_priority
    from apps.reference_api.market_data_source_contracts import SourcePriorityInput
    from security_master_schema.market_data_resolver import resolve_market_data
    from tests.test_market_data_resolver import _request
    from market_data.source_priority import effective_priority
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            day=c.scalar(select(m.valuation_policy.c.valid_from).where(m.valuation_policy.c.valuation_policy_id==ids['valuation_policy']))
            request=_request(day)
            baseline=resolve_market_data(c,request)
            assert baseline.status=='SELECTED'
            # Derive the type through the selected listing, not the pricing policy.
            type_id=c.scalar(select(m.instrument.c.instrument_type_id).join(m.listing).where(m.listing.c.listing_node_id==request.subject_reference_node_id))
            saved=save_priority(c,ids['tenant'],ids['demo_user_account'],SourcePriorityInput(instrumentTypeId=type_id,datasetIds=[]),str(uuid4()))
            # Anchor the boundary to the authoritative recorded timestamp. Host
            # and PostgreSQL clocks need not agree, even on the same machine.
            assert effective_priority(c,ids['tenant'],type_id,saved['createdAt']-timedelta(microseconds=1))['datasetIds'] is None
            from dataclasses import replace
            result=resolve_market_data(c,replace(request,market_data_as_of_utc=saved['createdAt']+timedelta(seconds=1)))
            assert result.status!='SELECTED'
            assert result.exception_code=='SOURCE_PRIORITY_EXCLUDED'
            assert result.pricing_evidence['sourcePriority']['tenantVersionId']==str(saved['versionId'])
        finally:tx.rollback()


# Imported pytest fixture supplies real governed sessions in an isolated database.
from tests.test_composite_policy_resolution import composite


def test_preferred_provider_cannot_win_with_a_premature_session_close(composite):
    from market_data.policy_selection import select_composite
    from security_master_schema.market_data_resolver import _entitled_observations
    c,request,_=composite
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    rows=[dict(row) for _,row in _entitled_observations(c,request,rule)]
    assert rows
    valid=next(row for row in rows if row['market_data_observation_id']==ids['market_data_observation'])
    invalid=dict(valid,dataset_id=uuid4(),market_data_observation_id=uuid4(),
        received_at_utc=datetime(2026,8,28,9,tzinfo=timezone.utc),source_published_at_utc=datetime(2026,8,28,9,tzinfo=timezone.utc))
    priority=dict(datasetIds=[str(invalid['dataset_id']),str(valid['dataset_id'])])
    selected=select_composite(c,request,rule,[invalid,valid],priority)
    assert selected['row'] is not None, selected
    assert selected['row']['market_data_observation_id']==valid['market_data_observation_id']


def test_resolver_uses_saved_source_order_not_arrival_time():
    from apps.reference_api.market_data_sources import save_priority
    from apps.reference_api.market_data_source_contracts import SourcePriorityInput
    from security_master_schema.market_data_resolver import resolve_market_data
    from tests.test_market_data_resolver import _request
    from dataclasses import replace
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            original=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
            base=c.execute(select(m.dataset).where(m.dataset.c.dataset_id==original['dataset_id'])).mappings().one()
            second=c.scalar(m.dataset.insert().values(provider_product_id=base['provider_product_id'],dataset_code='PRIORITY_TEST_'+uuid4().hex,
                display_name='Second synthetic source',data_domain='MARKET_DATA',valid_from=base['valid_from']).returning(m.dataset.c.dataset_id))
            c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=ids['tenant'],dataset_id=second,use_purpose='VALUATION',valid_from=base['valid_from']))
            clone=dict(original,market_data_observation_id=uuid4(),dataset_id=second,market_data_vintage_id=None,
                received_at_utc=original['received_at_utc']+timedelta(minutes=1),value=Decimal('999'))
            c.execute(m.market_data_observation.insert().values(**clone))
            c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(dataset_id=None))
            type_id=c.scalar(select(m.instrument.c.instrument_type_id).where(m.instrument.c.instrument_node_id==ids['hsbc_instrument_node']))
            save_priority(c,ids['tenant'],ids['demo_user_account'],SourcePriorityInput(instrumentTypeId=type_id,datasetIds=[original['dataset_id'],second]),str(uuid4()))
            request=replace(_request(original['market_date']),market_data_as_of_utc=datetime.now(timezone.utc)+timedelta(days=1))
            result=resolve_market_data(c,request)
            assert result.status=='SELECTED'
            assert result.market_data_observation_id==original['market_data_observation_id']
            assert result.pricing_evidence['sourcePriority']['scope']=='TENANT'
        finally:tx.rollback()
