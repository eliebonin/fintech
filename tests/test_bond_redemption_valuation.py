from dataclasses import replace
from datetime import datetime,time,timezone,timedelta
from decimal import Decimal as D
from uuid import uuid4
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup
from tests.test_economic_pnl_acceptance import add_bond
from security_master_schema.demo_data import DEMO_IDS as ids


def test_redemption_proceeds_enter_T_bridge_with_zero_closing_mark(valued):
    from lifecycle.bond_service import configure,candidate,post
    from positions.contracts import ProjectionRequest
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    from valuation.position_calculation import required_marks,MarkKey,attribute_projection
    c,r,trade=valued;listing,booked,_=setup(c,r,trade)
    configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic financial bridge')
    _,fingerprint,_,_=candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()))
    end=datetime.combine(r.closing_cutoff.date(),time.max,timezone.utc)
    opening=datetime.combine(r.closing_cutoff.date()-timedelta(days=1),time.max,timezone.utc)
    request=ProjectionRequest(r.tenant_id,r.strategy_id,end,r.information_cutoff,opening,'PERIOD')
    p=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=[listing])),request)
    assert len(required_marks(p))==1 and required_marks(p)[0].key.cutoff==opening
    result=attribute_projection(p,{MarkKey(listing,opening):D(99)},ids['gbp_currency'])
    assert result.closing_value==0 and result.opening_value==D(99000)
    assert result.execution_value==D(-100000) and result.market_pnl==D(1000)


def test_bond_cancel_and_rebook_closure_does_not_double_redemption(valued):
    from lifecycle.bond_service import configure,candidate,post,cancel
    from positions.contracts import ProjectionRequest
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    from valuation.position_calculation import MarkKey,attribute_projection
    from uuid import UUID
    c,r,trade=valued;listing,booked,_=setup(c,r,trade)
    configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic correction')
    instrument=ids['bond_instrument_node']
    _,fingerprint,_,_=candidate(c,r.tenant_id,r.strategy_id,instrument)
    posted=post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(posted['posting_id']),'Synthetic incorrect closure',str(uuid4()))
    end=datetime.combine(r.closing_cutoff.date(),time.max,timezone.utc)
    opening=datetime.combine(r.closing_cutoff.date()-timedelta(days=1),time.max,timezone.utc)
    request=ProjectionRequest(r.tenant_id,r.strategy_id,end,r.information_cutoff,opening,'PERIOD')
    restored=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=[listing])),request)
    assert restored.buckets[0].closing_quantity==100000
    _,fingerprint,_,_=candidate(c,r.tenant_id,r.strategy_id,instrument)
    post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    projection=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=[listing])),request)
    result=attribute_projection(projection,{MarkKey(listing,opening):D(99)},ids['gbp_currency'])
    assert result.closing_value==0 and result.market_pnl==1000
    assert len(projection.executions)==1


def test_full_valuation_and_staging_keep_final_daily_interest_separate(valued):
    import json
    from sqlalchemy import select
    from dataclasses import replace
    from security_master_schema import models as m
    from lifecycle.bond_service import configure,candidate,post
    from valuation.service import calculate_position
    from valuation.accruals import accrual_amounts,record_accrual
    from valuation import storage
    from apps.reference_api.db import get_engine
    c,r,trade=valued
    r=replace(r,opening_cutoff=datetime.combine(r.closing_cutoff.date()-timedelta(days=1),time.max,timezone.utc),
        closing_cutoff=datetime.combine(r.closing_cutoff.date(),time.max,timezone.utc),daily=True)
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    listing,booked,_=setup(c,r,trade)
    # Remove the unrelated synthetic equity through an actual retained cancellation.
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic staging')
    _,fingerprint,_,_=candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()))
    series=c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.reference_node_id==listing))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series)).mappings().one())
    stamp=r.opening_cutoff.replace(hour=22,minute=0,second=0,microsecond=0)
    c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        value=D(99),received_at_utc=stamp,observed_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='MATURITY_OPEN_'+uuid4().hex))))
    inputs=dict(openingBalance=D(990),dailyEarned=D(10),closingBalance=D(0),balanceMovements=D(-1000),openingFx=D(1),closingFx=D(1))
    payload=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=r.closing_cutoff.date(),inputType='DAILY_INTEREST',
        currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],eligibleNominal=D(100000),sourceReference='Synthetic final daily interest',
        eligibilityConvention='OPS_ASSESSED_NOMINAL',inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[],supersedesInputId=None)
    record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
    result=calculate_position(c,r)
    assert result.period.market_pnl==D(1000)
    assert result.gross_pnl==D(1010)
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    staged=storage.batch_view(c,r.tenant_id,batch)
    assert D(staged['summary']['marketPnl'])==1000 and D(staged['summary']['grossPnl'])==1010
    assert any(rule['code']=='BOND_MATURITY_REDEMPTION' for item in staged['items'] for rule in item['evidence']['appliedRules'])
    assert any(rule['code']=='DAILY_EARNED_ACCRUAL' for rule in result.evidence['appliedRules'])
    rules=[rule for item in staged['items'] for rule in item['evidence']['appliedRules']]
    assert any(rule['code']=='CLEAN_BOND_NOMINAL' for rule in rules)
    assert any(rule['code']=='POSITION_VALUE_BRIDGE' and rule['closingValue']=='0' for rule in rules)
