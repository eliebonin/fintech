"""Assessed note stocks must retain exact ownership/nominal/evidence meaning."""
from datetime import date
from decimal import Decimal as D
from uuid import uuid4
import pytest
from security_master_schema.evidence import evidence_hash
from valuation.note_measure_balances import assessed_note_stock
from valuation.accruals import accrual_amounts


def source():
    instrument,currency=uuid4(),uuid4()
    inputs=dict(openingBalance=D('100'),dailyEarned=D('25'),closingBalance=D('125'),balanceMovements=D('0'),openingFx=D('1'),closingFx=D('1'))
    payload=dict(eligibleNominal='100000',inputs=inputs,amounts=accrual_amounts(inputs))
    row=dict(input_id=uuid4(),revision=2,value_date=date(2026,10,1),currency_id=currency,payload=payload,input_hash=evidence_hash(payload))
    return instrument,currency,row


def test_assessed_note_stock_retains_source_identity_and_bridge_without_reusing_source_fx():
    instrument,currency,row=source()
    amount,proof=assessed_note_stock({instrument:row},instrument,currency,D('100000'),compatible_positions=1)
    assert amount==125 and proof['inputId']==str(row['input_id']) and proof['revision']==2
    assert 'inputs' not in proof and 'amounts' not in proof


@pytest.mark.parametrize('change',['currency','nominal','allocation','hash'])
def test_incompatible_or_unverified_note_stock_stays_unavailable(change):
    instrument,currency,row=source();nominal=D('100000');count=1
    if change=='currency':currency=uuid4()
    if change=='nominal':nominal=D('200000')
    if change=='allocation':count=2
    if change=='hash':row['input_hash']='0'*64
    with pytest.raises(ValueError):assessed_note_stock({instrument:row},instrument,currency,nominal,compatible_positions=count)
