from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError
from valuation.interest_review_contracts import ReviewCommand


def body():
    return dict(strategyId=str(uuid4()),valueDate='2026-10-20',stage='DAILY',state='VALIDATED',sourceHash='a'*64,
        rows=[dict(instrumentId=str(uuid4()),currencyId=str(uuid4()),amount='10.123456789012',coveredDays=3)])


def test_review_amounts_are_exact_and_population_is_unique():
    data=body();assert ReviewCommand(**data).rows[0].amount==Decimal('10.123456789012')
    for amount in (10.12,'NaN','1.0000000000001','1000000000000000000'):
        with pytest.raises(ValidationError):ReviewCommand(**(data|dict(rows=[data['rows'][0]|dict(amount=amount)])))
    with pytest.raises(ValidationError):ReviewCommand(**(data|dict(rows=data['rows']*2)))
    with pytest.raises(ValidationError):ReviewCommand(**(data|dict(rows=[data['rows'][0]|dict(coveredDays=0)])))
