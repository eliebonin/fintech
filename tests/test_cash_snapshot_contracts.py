from datetime import date
from uuid import uuid4
import pytest


def row():
    return dict(accountId=str(uuid4()),currencyId=str(uuid4()),valueDate='2026-10-12',
        amount='-100.123456789012',sourceReference='Statement',note='Restricted cash')


def test_upload_preserves_exact_signed_amount_and_notes():
    from apps.reference_api.cash_snapshot_contracts import CashUpload
    value=CashUpload(strategyId=uuid4(),rows=[row()])
    assert str(value.rows[0].amount)=='-100.123456789012'
    assert value.rows[0].note=='Restricted cash'


@pytest.mark.parametrize('amount',[1.5,'NaN','Infinity','1.1234567890123'])
def test_invalid_precision_and_float_amounts_rejected(amount):
    from apps.reference_api.cash_snapshot_contracts import CashUpload
    data=row();data['amount']=amount
    with pytest.raises(ValueError): CashUpload(strategyId=uuid4(),rows=[data])


def test_duplicate_date_account_currency_rows_and_unreasoned_correction_reject():
    from apps.reference_api.cash_snapshot_contracts import CashUpload
    data=row()
    with pytest.raises(ValueError): CashUpload(strategyId=uuid4(),rows=[data,data])
    data['expectedRevision']=1
    with pytest.raises(ValueError): CashUpload(strategyId=uuid4(),rows=[data])


def test_date_specific_selection_never_carries_a_previous_balance_forward():
    from valuation.cash_snapshots import latest_on_date
    rows=[dict(balance_as_of_date=date(2026,10,11),revision=1,amount='100',cash_account_id='a',currency_id='eur'),
          dict(balance_as_of_date=date(2026,10,12),revision=1,amount='0',cash_account_id='a',currency_id='eur'),
          dict(balance_as_of_date=date(2026,10,12),revision=2,amount='20',cash_account_id='a',currency_id='eur')]
    assert latest_on_date(rows,date(2026,10,12))[0]['amount']=='20'
    assert latest_on_date(rows,date(2026,10,13))==[]
