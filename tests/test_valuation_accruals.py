from decimal import Decimal as D
import pytest


def accrued(**changes):
    from valuation.accruals import accrual_amounts
    return accrual_amounts(dict(openingBalance=D('990'),dailyEarned=D('10'),closingBalance=D('0'),
        balanceMovements=D('-1000'),openingFx=D('.85'),closingFx=D('.86'))|changes)


def test_coupon_balance_reset_is_not_negative_earned_interest_or_new_coupon_income():
    amounts=accrued()
    assert amounts['dailyLocal']==D('10')
    assert amounts['dailyBase']==D('8.60')
    assert amounts['balanceLocal']==0
    assert amounts['balanceBase']==0
    assert amounts['receivableFx']==D('9.90')


def test_unreconciled_balance_and_nonfinite_daily_interest_reject():
    with pytest.raises(ValueError): accrued(closingBalance=D('1'))
    with pytest.raises(ValueError): accrued(dailyEarned=D('NaN'))


def test_confirmed_zero_is_not_missing_input():
    amounts=accrued(openingBalance=D('0'),dailyEarned=D('0'),balanceMovements=D('0'))
    assert amounts['dailyBase']==0
    with pytest.raises(ValueError): accrued(dailyEarned=None)


def test_accrual_revisions_are_immutable_and_replay_at_information_cutoff(valued):
    from datetime import date,datetime,timedelta,timezone
    from uuid import uuid4
    from sqlalchemy import select
    from valuation.accruals import record_accrual,read_accruals
    from valuation import tables as t
    from security_master_schema.demo_data import DEMO_IDS as ids
    c,r,_=valued
    stamp=datetime.now(timezone.utc)-timedelta(seconds=5)
    payload=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=date(2026,10,1),
        inputType='DAILY_INTEREST',sourceReference='SYNTHETIC-COUPON',eligibleNominal=D('100000'),
        currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],eligibilityConvention='OPS_ASSESSED_NOMINAL',
        inputs=dict(openingBalance=D('990'),dailyEarned=D('10'),closingBalance=D('0'),balanceMovements=D('-1000'),openingFx=D('1'),closingFx=D('1')),
        fxEvidence=[],supersedesInputId=None)
    from valuation.accruals import accrual_amounts
    payload['amounts']=accrual_amounts(payload['inputs'])
    with pytest.raises(ValueError,match='amounts'):
        record_accrual(c,r.tenant_id,ids['demo_user_account'],payload|dict(amounts=payload['amounts']|dict(dailyBase=D('999'))),str(uuid4()))
    first=record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()),recorded_at=stamp)
    # Input correction and publication share a strategy-wide lock, including
    # corrections to earlier dates inside a multi-day candidate.
    from hashlib import sha256
    from sqlalchemy import func
    lock_id=int.from_bytes(sha256(f'valuation-inputs:{r.tenant_id}:{r.strategy_id}'.encode()).digest()[:8],'big',signed=True)
    with c.engine.connect() as other:
        assert other.scalar(select(func.pg_try_advisory_xact_lock(lock_id))) is False
    replacement=record_accrual(c,r.tenant_id,ids['demo_user_account'],payload|dict(supersedesInputId=first,sourceReference='CORRECTED'),
        str(uuid4()),recorded_at=stamp+timedelta(seconds=1))
    old=read_accruals(c,r.tenant_id,r.strategy_id,date(2026,10,1),date(2026,10,1),stamp)
    assert old[0]['input_id']==first
    current=read_accruals(c,r.tenant_id,r.strategy_id,date(2026,10,1),date(2026,10,1),stamp+timedelta(seconds=2))
    assert current[0]['input_id']==replacement
    from valuation.accruals import assert_current_accrual_versions
    candidate=[dict(strategy_id=r.strategy_id,evidence=dict(economicInputs=[dict(kind='DAILY_ACCRUAL',inputId=str(first),
        payload=dict(instrumentId=str(payload['instrumentId']),valueDate=payload['valueDate'].isoformat()))]))]
    with pytest.raises(ValueError,match='revision changed'): assert_current_accrual_versions(c,r.tenant_id,candidate)
    assert c.scalar(select(t.accrual_input.c.revision).where(t.accrual_input.c.input_id==first))==1
    with pytest.raises(ValueError,match='revision'):
        record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()),recorded_at=stamp+timedelta(seconds=2))


from tests.test_valuation_service import valued


def test_daily_accrual_is_attached_once_not_per_listing_and_tracks_stock_fx():
    from dataclasses import replace
    from types import SimpleNamespace
    from valuation.accruals import attach_accruals,AccrualInput
    from valuation.position_calculation import PositionPeriodAttribution,PositionLine
    from valuation.economics import MarketAttribution
    from datetime import date
    zero=D('0');key='a';other='b'
    line=PositionLine(SimpleNamespace(key=key),MarketAttribution(zero,zero,zero,zero,zero,zero),zero)
    period=PositionPeriodAttribution((line,replace(line,bucket=SimpleNamespace(key=other))),zero,zero,zero,zero)
    source=AccrualInput('id','bond',date(2026,10,1),1,dict(amounts=accrued()),key)
    result=attach_accruals(period,(source,))
    assert sum(l.economic_components.get('ACCRUAL',zero) for l in result.lines)==D('8.60')
    assert result.lines[0].economic_components['CARRY']==D('9.90')
    assert result.lines[1].economic_components=={}
