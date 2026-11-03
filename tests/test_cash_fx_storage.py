"""Native cash ownership and frozen source selection on owned PostgreSQL only."""
from dataclasses import replace
from datetime import date,datetime,time,timezone
from decimal import Decimal as D
from uuid import uuid4
from sqlalchemy import select,func
import pytest
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service
from valuation import storage,tables as t


def add_account(c,r,label='Synthetic custody'):
    company=c.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.status=='ACTIVE').limit(1))
    return c.scalar(m.cash_account.insert().values(strategy_id=r.strategy_id,custodian_organisation_id=company,
        display_label=label+' '+uuid4().hex,account_type='CUSTODY').returning(m.cash_account.c.cash_account_id))


def add_balance(c,r,account,day,amount,currency=None,revision=1,received=None):
    return c.scalar(m.cash_balance.insert().values(strategy_id=r.strategy_id,cash_account_id=account,
        currency_id=currency or ids['gbp_currency'],balance_as_of_date=day,
        balance_as_of_datetime_utc=datetime.combine(day,time.max,timezone.utc),balance_type='LEDGER',
        source_system_id='TENANT_EOD',amount=D(amount),revision=revision,source_reference='Synthetic cash statement',
        received_at_utc=received or datetime.combine(day,time(20),timezone.utc),
        created_by_user_account_id=ids['demo_user_account']).returning(m.cash_balance.c.cash_balance_id))


def daily(r):
    return replace(r,daily=True,
        opening_cutoff=datetime.combine(r.opening_cutoff.date(),time.max,timezone.utc),
        closing_cutoff=datetime.combine(r.closing_cutoff.date(),time.max,timezone.utc))


def seed_fx(c,r):
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    cut=uuid4();c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='CASH_FX_'+cut.hex,
        display_name='Synthetic cash fixing',timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    series=uuid4();c.execute(m.market_data_series.insert().values(market_data_series_id=series,reference_node_id=ids['gbpusd_fx_pair_node'],
        default_dataset_id=source['dataset_id'],series_type='FX_SPOT',value_type='RATE',currency_id=ids['usd_currency'],
        source_system_id='SYNTHETIC_CASH_FX',valuation_cut_id=cut,measure_definition_id=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=r.policy_id,rule_sequence=98,subject_type='FX_PAIR',
        series_type='FX_SPOT',value_basis='RAW',market_data_series_id=series,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,
        market_calendar_id=rule['market_calendar_id'],selection_method='LAST_BEFORE_CUT',max_staleness_business_days=0))
    for day,rate in [(date(2026,9,29),'.75'),(date(2026,9,30),'.76'),(date(2026,10,1),'.77')]:
        stamp=datetime.combine(day,time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            market_date=day,value=D(rate),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,
            source_observation_key='CASH_FX_'+uuid4().hex))))


def cancel_investment(c,trade):
    event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=event['event_datetime_utc'],supersedes_event_id=event['trade_lifecycle_event_id'],
        recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))


def stage(c,r,result):
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    return storage.stage(c,attempt,ids['demo_user_account'],result)


def reviewer(c):
    actor=uuid4();c.execute(m.user_account.insert().values(user_account_id=actor,account_type='HUMAN'))
    return actor


def test_cash_only_daily_fx_stages_without_fake_instrument_and_publishes(valued):
    from valuation.evidence_access import assert_batch_display
    c,r,trade=valued;cancel_investment(c,trade);seed_fx(c,r);account=add_account(c,r)
    for day,amount in [(date(2026,9,29),'100000'),(date(2026,9,30),'120000'),(date(2026,10,1),'90000')]:add_balance(c,r,account,day,amount)
    r=replace(daily(r),reporting_currency_id=ids['usd_currency'])
    before=c.scalar(select(func.count()).select_from(m.trade))
    result=service().calculate(c,r)
    assert result.period.market_pnl==0
    assert result.cash.amount==D('2200')
    assert result.net_pnl==D('2200')
    batch=stage(c,r,result);view=storage.batch_view(c,r.tenant_id,batch)
    assert len(view['items'])==1
    row=view['items'][0]
    assert row['trade_id'] is row['subject_id'] is row['position_key'] is None
    assert row['cash_account_id']==account and row['cash_currency_id']==ids['gbp_currency']
    assert row['components']=={'CASH_FX':'2200'}
    assert view['summary']['cashFxPnl']=='2200'
    assert row['evidence']['cashFx']['convention']=='OPENING_BALANCE_EOD_MOVEMENTS'
    assert len(row['evidence']['cashFx']['days'])==2
    assert_batch_display(c,r.tenant_id,view)
    with pytest.raises(ValueError,match='independent'):storage.publish(c,r.tenant_id,batch,ids['demo_user_account'],'Own result')
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Cash inputs and convention checked')
    assert len(storage.published(c,r.tenant_id,r.strategy_id,r.closing_cutoff.date()))==1
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(t.attribution.update().where(t.attribution.c.attribution_id==row['attribution_id']).values(net_pnl=0))


def test_same_company_accounts_stay_separate_and_same_currency_needs_no_market_data(valued):
    c,r,trade=valued;cancel_investment(c,trade)
    for label in ('Custody','Third-party venue'):
        account=add_account(c,r,label)
        for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100')
    r=daily(r);result=service().calculate(c,r)
    assert len(result.cash.lines)==2
    assert result.cash.amount==0 and result.resolution_snapshot_ids==()
    view=storage.batch_view(c,r.tenant_id,stage(c,r,result))
    from valuation.evidence_access import assert_batch_display
    assert_batch_display(c,r.tenant_id,view)
    assert all(row['evidence']['selections']==[] for row in view['items'])
    assert all(row['evidence']['cashFx']['days'][0]['fx_mode']=='IDENTITY' for row in view['items'])


def test_missing_opening_or_closing_snapshot_is_omitted_not_zero_or_carried(valued):
    c,r,_=valued;account=add_account(c,r)
    add_balance(c,r,account,date(2026,9,29),'100');add_balance(c,r,account,date(2026,10,1),'0')
    result=service().calculate(c,daily(r))
    assert result.cash.lines==()
    assert result.cash.coverage['status']=='MISSING_INPUTS'
    assert result.cash.coverage['missingCount']==2
    assert result.cash.coverage['suppliedCount']==0
    assert result.evidence['pnlCompleteness']=='PARTIAL'
    assert result.net_pnl==result.period.lines[0].net_pnl
    from tests.test_position_attribution_storage import reviewer
    batch=stage(c,result.request,result)
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Optional cash omissions reviewed; available components retained')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_historical_cash_and_unused_accounts_do_not_create_current_expectations(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;current=add_account(c,r,'Current');old=add_account(c,r,'Historical')
    add_account(c,r,'Never supplied')
    add_balance(c,r,old,date(2026,1,1),'500',currency=ids['usd_currency'])
    # A discontinued currency on a still-used account is not expected forever.
    add_balance(c,r,current,date(2026,1,1),'200',currency=ids['usd_currency'])
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):
        add_balance(c,r,current,day,'100')
    result=load_cash_fx(c,daily(r))
    assert result.coverage['status']=='INCLUDED'
    assert result.coverage['knownScopeCount']==1
    assert result.coverage['missing']==[]
    assert result.coverage['suppliedCount']==2
    assert len(result.lines)==1 and result.lines[0].account_id==current
    assert result.amount==0


def test_historical_only_cash_is_not_reported_as_missing_current_snapshots(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;account=add_account(c,r)
    add_balance(c,r,account,date(2026,1,1),'100')
    result=load_cash_fx(c,daily(r))
    assert result.coverage['knownScopeCount']==0
    assert result.coverage['missingCount']==0
    assert result.coverage['status']=='NOT_ASSESSED'
    assert result.lines==()


def test_absent_daily_pair_does_not_extend_a_disappeared_scope_forever(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;account=add_account(c,r)
    add_balance(c,r,account,date(2026,9,29),'100')
    add_balance(c,r,account,date(2026,9,30),'100')
    r=replace(daily(r),closing_cutoff=datetime(2026,10,3,23,59,59,999999,tzinfo=timezone.utc))
    result=load_cash_fx(c,r)
    assert result.coverage['suppliedCount']==1
    # 1 October has an actual one-sided input; 2/3 October have no inputs at all.
    assert result.coverage['missing']==[dict(accountId=str(account),currencyId=str(ids['gbp_currency']),
        valueDate='2026-10-01',missingOpening=False,missingClosing=True)]


def test_source_cutoff_selects_exact_revision_and_never_another_tenant(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;account=add_account(c,r);original=add_balance(c,r,account,date(2026,9,29),'100')
    cutoff=datetime(2026,10,2,tzinfo=timezone.utc)
    add_balance(c,r,account,date(2026,9,29),'200',revision=2,received=datetime(2026,10,3,tzinfo=timezone.utc))
    for day in (date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100')
    result=load_cash_fx(c,replace(daily(r),information_cutoff=cutoff))
    assert result.lines[0].days[0].opening['cash_balance_id']==str(original)
    assert result.lines[0].days[0].opening['amount']=='100'
    with pytest.raises(PermissionError):load_cash_fx(c,replace(daily(r),tenant_id=ids['second_tenant']))


def test_inactive_currency_cannot_hide_behind_zero_cash_exposure(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;account=add_account(c,r)
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):
        add_balance(c,r,account,day,'0',currency=ids['usd_currency'])
    c.execute(m.currency.update().where(m.currency.c.currency_id==ids['usd_currency']).values(status='INACTIVE'))
    with pytest.raises(ValueError,match='currency'):
        load_cash_fx(c,daily(r))


def test_zero_foreign_opening_needs_no_fx_and_new_cash_is_not_income(valued):
    from valuation.evidence_access import assert_batch_display,batch_datasets
    c,r,trade=valued;cancel_investment(c,trade);account=add_account(c,r)
    add_balance(c,r,account,date(2026,9,30),'0',currency=ids['usd_currency'])
    add_balance(c,r,account,date(2026,10,1),'100000',currency=ids['usd_currency'])
    r=replace(daily(r),opening_cutoff=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc))
    result=service().calculate(c,r)
    assert result.cash.amount==0 and result.resolution_snapshot_ids==()
    view=storage.batch_view(c,r.tenant_id,stage(c,r,result));assert_batch_display(c,r.tenant_id,view)
    # A foreign/nonzero contribution cannot claim the no-market-data exception.
    from copy import deepcopy
    invalid=deepcopy(view);invalid['items'][0]['evidence']['cashFx']['days'][0]['fx_mode']='POLICY_FX'
    with pytest.raises(PermissionError):batch_datasets(invalid)


def test_partial_cash_pairs_are_included_once_and_missing_first_balance_is_not_zero(valued):
    from valuation.cash_fx_inputs import load_cash_fx
    c,r,_=valued;account=add_account(c,r);seed_fx(c,r)
    # Scope first appears on 30 Sep: no invented zero on 29 Sep.
    add_balance(c,r,account,date(2026,9,30),'-100000')
    add_balance(c,r,account,date(2026,10,1),'-80000')
    result=load_cash_fx(c,replace(daily(r),reporting_currency_id=ids['usd_currency']))
    assert result.amount==D('-1000')
    assert result.coverage['status']=='PARTIAL'
    assert result.coverage['missingCount']==1 and result.coverage['suppliedCount']==1
    assert result.coverage['missing'][0]['missingOpening'] is True
    assert len(result.lines[0].days)==1


def test_cash_scope_constraints_prevent_relinking_or_fake_instruments(valued):
    c,r,_=valued;account=add_account(c,r);other=add_account(c,r,'Other account')
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100')
    r=daily(r);batch=stage(c,r,service().calculate(c,r))
    item=dict(c.execute(select(t.item).where(t.item.c.batch_id==batch,t.item.c.cash_account_id.is_not(None))).mappings().one())
    with pytest.raises(Exception,match='review attribution scope mismatch'):
        with c.begin_nested():c.execute(t.item.update().where(t.item.c.item_id==item['item_id']).values(cash_account_id=other))
    row=dict(c.execute(select(t.attribution).where(t.attribution.c.attribution_id==item['attribution_id'])).mappings().one())
    with pytest.raises(Exception,match='check constraint|scope mismatch'):
        with c.begin_nested():c.execute(t.attribution.insert().values(**(row|dict(attribution_id=uuid4(),version=100,
            position_key='fake-position',subject_id=ids['hsbc_xlon_listing_node']))))


def test_cash_fx_evidence_requires_current_provider_display_rights(valued):
    from valuation.evidence_access import assert_batch_display
    c,r,trade=valued;cancel_investment(c,trade);seed_fx(c,r);account=add_account(c,r)
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100000')
    r=replace(daily(r),reporting_currency_id=ids['usd_currency'])
    view=storage.batch_view(c,r.tenant_id,stage(c,r,service().calculate(c,r)))
    assert_batch_display(c,r.tenant_id,view)
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id==ids['dataset']).values(status='SUSPENDED'))
    with pytest.raises(PermissionError):assert_batch_display(c,r.tenant_id,view)
