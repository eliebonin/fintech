from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued


def core(strategy=None,amount='10'):
    return dict(strategyId=str(strategy or ids['strategy']),instrumentId=str(ids['bond_instrument_node']),
        valueDate='2026-10-01',dailyEarned=amount,currencyId=str(ids['gbp_currency']))


def test_minimal_contract_requires_exact_amount_currency_not_optional_balances():
    from apps.reference_api.valuation_input_contracts import AccrualCreate
    model=AccrualCreate.model_validate(core(amount='0'))
    assert model.daily_earned==0 and model.currency_id==ids['gbp_currency']
    assert model.opening_balance is None
    for amount in (None,1.25,'NaN','1.0000000000001','1000000000000000000'):
        with pytest.raises(ValidationError): AccrualCreate.model_validate(core(amount=amount))
    with pytest.raises(ValidationError): AccrualCreate.model_validate(core()|dict(currencyId=None))
    with pytest.raises(ValidationError): AccrualCreate.model_validate(core()|dict(openingBalance='0'))


def test_minimal_api_stores_typed_zero_retries_and_versions(valued):
    from tests.test_composite_policy_api import call
    from valuation import tables as t
    c,r,_=valued
    c.rollback()  # The fixture's independently committed strategy is enough for HTTP scope.
    data=core(strategy=r.strategy_id,amount='0');key=str(uuid4())
    first=call('POST','/v1/valuation/accrual-inputs',data,key)
    assert first.status_code==201,first.text
    row=first.json()
    assert D(row['daily_earned_interest'])==0
    assert row['currency_id']==str(ids['gbp_currency'])
    assert row['payload']['balanceReconciliation']=='NOT_PROVIDED'
    assert 'amounts' not in row['payload']
    assert call('POST','/v1/valuation/accrual-inputs',data,key).json()['input_id']==row['input_id']
    correction=data|dict(dailyEarned='10',supersedesInputId=row['input_id'])
    new=call('POST','/v1/valuation/accrual-inputs',correction,str(uuid4()))
    assert new.status_code==201,new.text
    assert new.json()['revision']==row['revision']+1
    from apps.reference_api.db import get_engine
    with get_engine().begin() as c:
        assert c.scalar(select(t.accrual_input.c.daily_earned_interest).where(t.accrual_input.c.input_id==row['input_id']))==0
        with pytest.raises(Exception,match='immutable'):
            with c.begin_nested():
                c.execute(t.accrual_input.update().where(t.accrual_input.c.input_id==row['input_id']).values(daily_earned_interest=99))


def test_minimal_daily_interest_is_valued_without_inventing_balance_or_carry(valued):
    from datetime import date
    from tests.test_economic_pnl_acceptance import add_bond
    from valuation.accruals import record_accrual
    from valuation.service import calculate_position
    c,r,trade=valued
    add_bond(c,r,trade)
    for day,amount in [(date(2026,9,30),'0'),(date(2026,10,1),'10')]:
        record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,
            instrumentId=ids['bond_instrument_node'],valueDate=day,inputType='DAILY_INTEREST',
            dailyEarned=D(amount),currencyId=ids['gbp_currency'],balanceReconciliation='NOT_PROVIDED'),str(uuid4()))
    result=calculate_position(c,r)
    bonds=[l for l in result.period.lines if l.bucket.key.product_basis=='BOND']
    assert bonds[0].components()['ACCRUAL']==10
    assert 'CARRY' not in bonds[0].components()
    proof=bonds[0].economic_evidence[0]
    assert proof['payload']['balanceReconciliation']=='NOT_PROVIDED'
    assert 'balanceLocal' not in proof['payload']['amounts']
    assert 'ACCRUED_BALANCE_NOT_ASSESSED' in result.evidence['limitations']


def test_full_writer_promotes_exact_amount_and_rejects_disagreement(valued):
    from datetime import date
    from valuation.accruals import record_accrual,accrual_amounts
    from valuation import tables as t
    c,r,_=valued
    inputs=dict(openingBalance=D(0),dailyEarned=D('1.234567890123'),closingBalance=D('1.234567890123'),
        balanceMovements=D(0),openingFx=D(1),closingFx=D(1))
    data=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=date(2026,10,1),
        inputType='DAILY_INTEREST',currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],
        eligibleNominal=D(1),sourceReference='Synthetic',eligibilityConvention='ASSESSED',inputs=inputs,
        amounts=accrual_amounts(inputs),fxEvidence=[])
    with pytest.raises(ValueError,match='daily'):
        record_accrual(c,r.tenant_id,ids['demo_user_account'],data|dict(dailyEarned=D(2)),str(uuid4()))
    identity=record_accrual(c,r.tenant_id,ids['demo_user_account'],data,str(uuid4()))
    assert c.scalar(select(t.accrual_input.c.daily_earned_interest).where(t.accrual_input.c.input_id==identity))==D('1.234567890123')


def test_legacy_request_key_fingerprint_still_replays_after_contract_extension(valued):
    from datetime import date
    from tests.test_valuation_input_api import payload
    from tests.test_composite_policy_api import call
    from apps.reference_api.valuation_input_contracts import AccrualCreate
    from valuation.accruals import record_accrual,accrual_amounts
    from valuation.economics import evidence_hash
    c,r,_=valued
    wire=payload()|dict(strategyId=str(r.strategy_id));key=str(uuid4())
    original_request=AccrualCreate.model_validate(wire).model_dump(mode='json')
    original_request.pop('currency_id')  # field did not exist before migration 93
    inputs=dict(openingBalance=D(990),dailyEarned=D(10),closingBalance=D(0),balanceMovements=D(-1000),openingFx=D(1),closingFx=D(1))
    data=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=date(2026,10,1),inputType='DAILY_INTEREST',
        currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],eligibleNominal=D(100000),
        sourceReference='SYNTHETIC COUPON',eligibilityConvention='OPS_ASSESSED_NOMINAL',inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[])
    identity=record_accrual(c,r.tenant_id,ids['demo_user_account'],data,key,request_hash=evidence_hash(original_request))
    c.commit()  # Persist only synthetic fixture state for the real HTTP replay.
    response=call('POST','/v1/valuation/accrual-inputs',wire,key)
    assert response.status_code==201,response.text
    assert response.json()['input_id']==str(identity)
