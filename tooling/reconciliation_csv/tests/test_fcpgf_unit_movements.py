"""Owner-approved inference is bounded to the supplied zero-price fund rows."""
import pytest


def test_recurring_credits_are_reinvestments_and_other_movements_are_transfers():
    from tooling.reconciliation_csv.fcpgf_unit_movements import classify
    assert classify(dict(price='0',quantity='100',trade_datetime_utc='2022-02-03 12:30:00'))=='REINVESTMENT'
    assert classify(dict(price='0',quantity='1000000',trade_datetime_utc='2021-06-21 12:30:00'))=='TRANSFER'
    assert classify(dict(price='0',quantity='-100000',trade_datetime_utc='2021-06-30 12:30:00'))=='TRANSFER'
    with pytest.raises(ValueError):classify(dict(price='1',quantity='100',trade_datetime_utc='2022-02-03 12:30:00'))
