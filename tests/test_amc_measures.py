"""Native AMC booking, governed marks and exact preview/P&L in an owned DB."""
from uuid import uuid4
from decimal import Decimal as D
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued


@pytest.mark.parametrize('unit,basis,denomination,quantity,value,pnl',[
    ('UNITS','UNIT_PRICE',None,'10','1000','20'),
    ('UNITS','PCT_OF_PAR','1000','10','10000','200'),
    ('NOMINAL','PCT_OF_PAR',None,'10000','10000','200'),
])
def test_amc_governed_preview_and_daily_bridge_agree(valued,unit,basis,denomination,quantity,value,pnl):
    from tests.test_amc import draft
    from apps.reference_api.amc_contracts import AmcProposalRequest
    from apps.reference_api.product_booking import submit_proposal,decide_proposal,load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    from tests.test_measure_inputs import preview
    from valuation.service import calculate
    c,r,_=valued;data=draft();data['convention'].update(quantityUnit=unit,priceBasis=basis,
        quoteFactor='100' if basis=='PCT_OF_PAR' else '1',denomination=denomination)
    proposal=submit_proposal(c,r.tenant_id,ids['demo_user_account'],AmcProposalRequest.model_validate(data))
    node=decide_proposal(c,r.tenant_id,ids['demo_user_account'],proposal.proposal_id,'APPROVED','Synthetic quote verified').reference_node_id
    context=load_context(c,r.tenant_id,node,as_of=r.closing_cutoff.date())
    booked=book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(
        instrumentId=str(node),strategyId=str(r.strategy_id),executionRoute='OTC',side='BUY',quantity=quantity,
        executionPrice='98',tradeDatetime='2026-09-30T12:00:00Z',settlementDate='2026-10-02',
        counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=context.terms_fingerprint)),
        str(uuid4()),'ACTIVELY_MANAGED_CERTIFICATE','amc-measures-test')
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    obs=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],
        m.market_data_observation.c.market_date==r.closing_cutoff.date())).mappings().one())
    series=uuid4()
    from datetime import time
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='AMC_'+cut.hex,
        display_name='Synthetic issuer 16 UTC quote',timezone_name='UTC',local_time=time(16),
        market_calendar_id=rule['market_calendar_id'],status='ACTIVE'))
    c.execute(m.market_data_series.insert().values(**(source | dict(market_data_series_id=series,reference_node_id=node))))
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code='AMC_PRICE_BASIS',dimension_value=basis))
    c.execute(m.valuation_policy_rule.insert().values(**(rule | dict(valuation_policy_rule_id=uuid4(),rule_sequence=995,
        subject_type=None,instrument_type_id=None,market_venue_id=None,subject_reference_node_id=node,market_data_series_id=series,
        price_requirement=None,require_official_close=False,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut))))
    c.execute(m.market_data_observation.insert().values(**(obs | dict(market_data_observation_id=uuid4(),market_data_series_id=series,
        value=D('100'),source_observation_key='AMC_'+uuid4().hex))))
    result=preview(c,r);row=next(x for x in result['items'] if x['instrumentId']==str(node))
    assert {v['localAmount'] for v in row['measures'].values()}=={value},row['evidence']['issues']
    assert {v['strategyAmount'] for v in row['measures'].values()}=={value}
    assert row['evidence']['route']=='AMC_'+basis
    from dataclasses import replace
    foreign=next(x for x in preview(c,replace(r,reporting_currency_id=ids['usd_currency']))['items'] if x['instrumentId']==str(node))
    assert {v['localAmount'] for v in foreign['measures'].values()}=={value}
    assert {v['status'] for v in foreign['measures'].values()}=={'LOCAL_ONLY'}
    assert {v['strategyAmount'] for v in foreign['measures'].values()}=={None}
    calculated=calculate(c,r)
    line=next(x for x in calculated.period.lines if x.bucket.key.subject_id==node)
    assert line.attribution.closing_value==D(value) and line.attribution.market_pnl==D(pnl)
    # Wrong semantics must fail, even when an observation and its numerical value exist.
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series)
        .values(dimension_value='UNIT_PRICE' if basis=='PCT_OF_PAR' else 'PCT_OF_PAR'))
    row=next(x for x in preview(c,r)['items'] if x['instrumentId']==str(node))
    assert row['measures']['marketValue']['status']=='UNAVAILABLE'
