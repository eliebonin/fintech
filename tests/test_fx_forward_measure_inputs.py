"""Real forward bookings, scoped reconstruction and governed reporting FX."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import uuid4,UUID
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_fx_maturity_service import setup
from tests.test_measure_inputs import preview


def forward_row(c,r):
    return next(x for x in preview(c,r)['items'] if x['instrumentType']=='FX_FORWARD')


def book_more(c,r,instrument,side,amount):
    from apps.reference_api.fx_forward_booking import load_fx_forward_booking_terms,book_fx_forward_trade
    from apps.reference_api.contracts import FxForwardBookingRequest
    from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
    terms=load_fx_forward_booking_terms(c,r.tenant_id,instrument,as_of=r.opening_cutoff.date())
    return book_fx_forward_trade(c,r.tenant_id,ids['demo_user_account'],FxForwardBookingRequest.model_validate(dict(
        instrumentId=str(instrument),strategyId=str(r.strategy_id),side=side,quantity=amount,
        tradeDatetime='2026-09-30T11:00:00Z',counterpartyOrganisationId=str(ids['bank_a_organisation']),
        expectedTermsFingerprint=fx_forward_terms_fingerprint(terms))),str(uuid4()),'mock-measures')


def add_reporting_pair(c,r,prototype,base,quote,rate,sequence):
    """Own a synthetic FX pair, rule and dated observation; no external calls."""
    series=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==prototype)).mappings().one())
    node=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==series['reference_node_id'])).mappings().one())
    subject=uuid4();identity=uuid4()
    c.execute(m.financial_reference_node.insert().values(**(node|dict(reference_node_id=subject,canonical_name='Synthetic reporting FX',internal_code='MEASURES_'+subject.hex))))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=subject,scope_type='SHARED_CANONICAL',status='ACTIVE'))
    currency=c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code==quote))
    c.execute(m.market_data_series.insert().values(**(series|dict(market_data_series_id=identity,reference_node_id=subject,currency_id=currency))))
    for code,value in [('BASE_CURRENCY',base),('QUOTE_CURRENCY',quote)]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=identity,dimension_code=code,dimension_value=value))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,m.valuation_policy_rule.c.rule_sequence==99)).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=sequence,subject_reference_node_id=subject,market_data_series_id=identity))))
    obs=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==prototype)).mappings().one())
    c.execute(m.market_data_observation.insert().values(**(obs|dict(market_data_observation_id=uuid4(),market_data_series_id=identity,value=D(rate),source_observation_key='MEASURES_'+uuid4().hex))))


def test_third_strategy_currency_converts_both_legs_independently(valued):
    c,r,_=valued;_,_,_,series=setup(c,r)
    add_reporting_pair(c,r,series,'GBP','EUR','1.2',100)
    add_reporting_pair(c,r,series,'USD','EUR','0.9',101)
    row=forward_row(c,replace(r,reporting_currency_id=ids['eur_currency']))
    assert row['measures']['referenceNotional']['strategyAmount']=='1200000',row['evidence']['issues']
    legs=row['measures']['economicExposure']['legs']
    assert [(leg['currency'],leg['strategyAmount'],leg['strategyCurrency']) for leg in legs]==[
        ('GBP','1200000','EUR'),('USD','-990000','EUR')]
    assert row['evidence']['selections']['baseLegFx']['observationDate']=='2026-10-01'
    assert row['evidence']['selections']['quoteLegFx']['method']=='DIRECT'


@pytest.mark.parametrize('side,base,quote',[('BUY','1000000','-1100000'),('SELL','-1000000','1100000')])
def test_contractual_legs_use_agreed_not_current_rate_and_separate_fund_fx(valued,side,base,quote):
    c,r,_=valued;setup(c,r,side)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,
        m.valuation_policy_rule.c.rule_sequence==99).values(allow_inverse_fx=True))
    row=forward_row(c,r);measures=row['measures']
    assert measures['referenceNotional']==dict(localAmount=base,currency='GBP',strategyAmount=base,strategyCurrency='GBP',status='AVAILABLE'),row['evidence']['issues']
    exposure=measures['economicExposure']
    assert exposure['status']=='MULTI_CURRENCY' and exposure['localAmount'] is None
    assert [(x['role'],x['localAmount'],x['currency']) for x in exposure['legs']]==[('BASE',base,'GBP'),('QUOTE',quote,'USD')]
    assert exposure['legs'][0]['strategyAmount']==base
    # 1 / 1.12 rounded HALF_EVEN to 12dp = 0.892857142857.
    assert D(exposure['legs'][1]['strategyAmount'])==D('-982142.8571427')*(1 if side=='BUY' else -1)
    assert measures['marketValue']['localAmount'] is None
    assert 'discount' in row['evidence']['issues']['marketValue'].lower()
    assert row['evidence']['selections']['quoteLegFx']['method']=='RECIPROCAL'


def test_missing_quote_conversion_preserves_both_contractual_amounts(valued):
    c,r,_=valued;setup(c,r)
    row=forward_row(c,r)
    assert row['measures']['referenceNotional']['status']=='AVAILABLE',row['evidence']['issues']
    legs=row['measures']['economicExposure']['legs']
    assert legs[0]['status']=='AVAILABLE'
    assert legs[1]['status']=='LOCAL_ONLY' and legs[1]['strategyAmount'] is None
    assert legs[1]['localAmount']=='-1100000'


def test_trade_currency_is_not_mislabelled_as_base_when_reporting_in_quote(valued):
    c,r,_=valued;setup(c,r)
    row=forward_row(c,replace(r,reporting_currency_id=ids['usd_currency']))
    assert row['measures']['referenceNotional']['currency']=='GBP'
    assert row['measures']['referenceNotional']['strategyAmount']=='1120000'
    assert row['measures']['economicExposure']['legs'][1]['strategyAmount']=='-1100000'


def test_maturity_close_removes_both_legs_and_cancellation_restores_them(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued
    r=replace(r,closing_cutoff=r.closing_cutoff.replace(hour=23,minute=59,second=59,microsecond=999999))
    instrument,_,cut,_=setup(c,r)
    assert forward_row(c,r)['measures']['economicExposure']['legs'][0]['localAmount']=='1000000'
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock closure',r.policy_id,cut)
    _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    assert not [x for x in preview(c,r)['items'] if x['instrumentType']=='FX_FORWARD' and x['quantity']!='0']
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from apps.reference_api.strategy_workspace import measure_position_rows
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,request);projection=project_holdings(facts,request)
    from valuation.forward_measures import contractual_legs
    closed=next(b for b in projection.buckets if b.key.product_basis=='FX_FORWARD')
    assert contractual_legs(c,r,closed)['quoteAmount']==0
    assert not [x for x in measure_position_rows(c,r,projection,descriptions) if x['instrumentType']=='FX_FORWARD']
    svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(result['posting_id']),'Mock correction',str(uuid4()))
    assert forward_row(c,r)['measures']['economicExposure']['legs'][1]['localAmount']=='-1100000'


def test_unclosed_past_maturity_keeps_obligations_with_ops_warning(valued):
    c,r,_=valued;setup(c,r)
    row=forward_row(c,replace(r,closing_cutoff=r.closing_cutoff+timedelta(days=1)))
    assert row['measures']['economicExposure']['legs'][0]['localAmount']=='1000000'
    assert 'closure' in row['evidence']['issues']['lifecycle'].lower()


def test_multiple_fills_partial_close_and_cancel_are_reconstructed_once(valued):
    c,r,_=valued;instrument,_,_,_=setup(c,r)
    book_more(c,r,instrument,'BUY','500000')
    sale=book_more(c,r,instrument,'SELL','250000')
    row=forward_row(c,r)
    assert row['quantity']=='1250000'
    assert row['measures']['economicExposure']['legs'][1]['localAmount']=='-1375000'
    trade=sale.data.trade.trade_id
    stamp=c.scalar(select(m.trade.c.trade_datetime_utc).where(m.trade.c.trade_id==trade))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=stamp,recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    row=forward_row(c,r)
    assert row['quantity']=='1500000'
    assert row['measures']['economicExposure']['legs'][1]['localAmount']=='-1650000'


def test_changed_agreement_is_not_silently_netted_at_one_rate(valued):
    c,r,_=valued;instrument,_,_,_=setup(c,r)
    c.execute(m.fx_forward_terms.update().where(m.fx_forward_terms.c.instrument_node_id==instrument).values(agreed_forward_rate=D('1.20')))
    book_more(c,r,instrument,'BUY','500000')
    row=forward_row(c,r)
    assert row['measures']['referenceNotional']['status']=='UNAVAILABLE'
    assert 'Mixed forward agreements' in row['evidence']['issues']['contract']


def test_fx_display_denial_is_not_turned_into_local_only(valued):
    from market_data.display_access import EvidenceDisplayDenied
    from tests.test_position_measures_assurance import deny_dataset_display
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from apps.reference_api.strategy_workspace import position_rows
    from valuation.measure_inputs import preview_measures
    c,r,_=valued;setup(c,r)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,
        m.valuation_policy_rule.c.rule_sequence==99).values(allow_inverse_fx=True))
    deny_dataset_display(c,r)
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,request);projection=project_holdings(facts,request)
    rows=[x for x in position_rows(projection,descriptions) if x['instrumentType']=='FX_FORWARD']
    assert len(rows)==1
    with pytest.raises(EvidenceDisplayDenied):preview_measures(c,r,projection,descriptions,rows)


def test_zero_base_with_mixed_rates_is_not_filtered_out_as_closed(valued):
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from apps.reference_api import strategy_workspace as workspace
    c,r,_=valued;instrument,_,_,_=setup(c,r)
    c.execute(m.fx_forward_terms.update().where(m.fx_forward_terms.c.instrument_node_id==instrument).values(agreed_forward_rate=D('1.20')))
    book_more(c,r,instrument,'SELL','1000000')
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,request);projection=project_holdings(facts,request)
    rows=workspace.measure_position_rows(c,r,projection,descriptions)
    row=next(x for x in rows if x['instrumentType']=='FX_FORWARD')
    assert row['quantity']=='0'
    from valuation.measure_inputs import preview_measures
    output=preview_measures(c,r,projection,descriptions,[row])['items'][0]
    assert output['measures']['economicExposure']['status']=='UNAVAILABLE'
    assert 'Mixed forward agreements' in output['evidence']['issues']['contract']
