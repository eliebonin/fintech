from datetime import date,datetime,time,timezone
from decimal import Decimal as D
from uuid import uuid4,UUID
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from security_master_schema import models as m,access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids


def setup(c,r,side='BUY'):
    from apps.reference_api.fx_forward_booking import load_fx_forward_booking_terms,book_fx_forward_trade
    from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
    from apps.reference_api.contracts import FxForwardBookingRequest
    instrument=ids['fx_forward_instrument_node'];day=r.closing_cutoff.date()
    c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==instrument).values(
        maturity_date=day,settlement_date=day,final_settlement_date=day,cash_settlement_date=None))
    c.execute(m.fx_forward_terms.update().where(m.fx_forward_terms.c.instrument_node_id==instrument).values(
        quote_currency_id=ids['usd_currency'],quote_convention='USD_PER_GBP',agreed_forward_rate=D('1.10')))
    terms=load_fx_forward_booking_terms(c,r.tenant_id,instrument,as_of=date(2026,9,30))
    actions=['LIFECYCLE_READ','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','LIFECYCLE_CONFIGURE','TRADE_WRITE','TRADE_CORRECT','MARKET_DATA_READ']
    group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='FXMAT_'+uuid4().hex,name='Mock FX maturity',actions=actions,
        scope_mode='SELECTED',strategy_ids=[r.strategy_id])
    c.execute(m.access_group_member.insert().values(tenant_id=r.tenant_id,group_id=group,user_account_id=ids['demo_user_account']))
    booked=book_fx_forward_trade(c,r.tenant_id,ids['demo_user_account'],FxForwardBookingRequest.model_validate(dict(
        instrumentId=str(instrument),strategyId=str(r.strategy_id),side=side,quantity='1000000',tradeDatetime='2026-09-30T10:00:00Z',
        counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=fx_forward_terms_fingerprint(terms))),str(uuid4()),'mock-maturity')
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    cut=uuid4();c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='FXMAT_'+cut.hex,display_name='Mock FX maturity cut',
        timezone_name='UTC',local_time='16:00',market_calendar_id=rule['market_calendar_id']))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    series=uuid4();measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))
    c.execute(m.market_data_series.insert().values(market_data_series_id=series,reference_node_id=ids['gbpusd_fx_pair_node'],default_dataset_id=source['dataset_id'],
        series_type='FX_SPOT',value_type='RATE',currency_id=ids['usd_currency'],source_system_id='MOCK_FX_MATURITY',valuation_cut_id=cut,measure_definition_id=measure))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=r.policy_id,rule_sequence=99,subject_type='FX_PAIR',series_type='FX_SPOT',value_basis='RAW',
        market_data_series_id=series,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,market_calendar_id=rule['market_calendar_id'],selection_method='LAST_BEFORE_CUT',max_staleness_business_days=0))
    stamp=datetime.combine(day,time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,market_date=day,value=D('1.12'),
        market_data_vintage_id=None,received_at_utc=stamp,observed_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='FXMAT_'+uuid4().hex))))
    return instrument,group,r.cut_id,series


@pytest.mark.parametrize('side,closing',[('BUY',D(-1000000)),('SELL',D(1000000))])
def test_direct_forward_closure_uses_maturity_rate_without_cash(valued,side,closing):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r,side)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock closure',r.policy_id,cut)
    data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    assert data['price']=='1.12' and data['fxEvidence']['observationDate']=='2026-10-01'
    assert D(data['movements'][0]['quantity'])==closing
    repeated=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    assert repeated[1]==fingerprint,{k:(data[k],repeated[0][k]) for k in data if data[k]!=repeated[0][k]}
    key=str(uuid4());result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(result['trade_ids'][0]))).mappings().one()
    assert row['trade_type']=='MATURITY_CLOSE' and row['execution_price']==D('1.12')
    assert row['settlement_date'] is None and row['quantity']==closing
    assert svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)['trade_ids']==result['trade_ids']
    with pytest.raises(svc.RedemptionConflict):svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(result['posting_id']),'Mock correction',str(uuid4()))
    assert D(svc.candidate(c,r.tenant_id,r.strategy_id,instrument)[0]['movements'][0]['quantity'])==closing


def test_review_refuses_self_approval_and_changed_rate(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'REVIEW',0,'Mock review',r.policy_id,cut)
    _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    p=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint)
    with pytest.raises(PermissionError):svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(p['proposalId']))
    reviewer=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Mock FX reviewer');am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],reviewer,[group])
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=D('1.13')))
    with pytest.raises(svc.RedemptionConflict):svc.post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(p['proposalId']))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=D('1.12')))
    result=svc.post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(p['proposalId']))
    assert result['evidence']['authority']['operation']=='APPROVE'
    assert result['actor_id']==str(reviewer)


def test_missing_maturity_observation_does_not_use_prior_day(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock missing rate',r.policy_id,cut)
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_data_series_id==series))
    data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    assert data['price'] is None and data['rateSource']=='MISSING'
    with pytest.raises(ValueError,match='sourced manual rate required'):
        svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))


def test_wrong_policy_cut_is_rejected_at_configuration(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    with pytest.raises(ValueError,match='Active pricing policy'):
        svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Wrong cut',r.policy_id,uuid4())


def test_prefilled_rate_override_retains_suggestion_and_manual_source(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'MANUAL',0,'Mock manual closure',r.policy_id,cut)
    override=dict(rate='1.125',sourceReference='Counterparty confirmation ABC',reason='Confirmed contractual closing rate')
    data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
    assert data['price']=='1.125' and data['suggestedPrice']=='1.12'
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),rate_override=override)
    assert result['evidence']['rateOverride']==override
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(result['trade_ids'][0]))).mappings().one()
    assert row['execution_price']==D('1.125') and row['settlement_date'] is None


def test_manual_rate_can_close_when_spot_is_missing_without_silent_fallback(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock missing spot',r.policy_id,cut)
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_data_series_id==series))
    override=dict(rate='1.11',sourceReference='Ops-confirmed maturity rate',reason='Provider observation missing')
    data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
    assert data['suggestedPrice'] is None and data['rateSelectionError']
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),rate_override=override)
    assert result['evidence']['price']=='1.11' and result['evidence']['fxEvidence'] is None


def test_review_uses_retained_override_and_never_accepts_approval_rate_change(valued):
    from lifecycle import fx_service as svc
    c,r,_=valued;instrument,group,cut,series=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'REVIEW',0,'Mock manual review',r.policy_id,cut)
    override=dict(rate='1.115',sourceReference='Signed confirmation',reason='Counterparty rate')
    _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
    p=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,rate_override=override)
    reviewer=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Manual rate reviewer');am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],reviewer,[group])
    with pytest.raises(ValueError,match='retained proposal'):
        svc.post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(p['proposalId']),rate_override=override|dict(rate='1.20'))
    result=svc.post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(p['proposalId']))
    assert result['evidence']['price']=='1.115' and result['evidence']['authority']['operation']=='APPROVE'
