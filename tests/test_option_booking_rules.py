"""Lightweight option booking economics, without positions or valuation."""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from security_master_schema.option_booking import gross_option_premium, validate_option_execution


def test_contract_premium_uses_explicit_quote_conversion():
    assert gross_option_premium(10, Decimal('2.50'), Decimal('100'), Decimal('1')) == Decimal('2500')
    assert gross_option_premium(10, Decimal('250'), Decimal('100'), Decimal('100')) == Decimal('2500')


@pytest.mark.parametrize('quantity,premium,multiplier,factor', [
    (0,'2','100','1'), (Decimal('1.5'),'2','100','1'), (1,'-1','100','1'),
    (1,'2','0','1'), (1,'2','100','0'), (1,'NaN','100','1'),
])
def test_invalid_or_missing_economics_never_default(quantity,premium,multiplier,factor):
    with pytest.raises(ValueError):
        gross_option_premium(quantity,Decimal(premium),Decimal(multiplier),Decimal(factor))


def test_zero_premium_is_a_real_value():
    assert gross_option_premium(1,Decimal('0'),Decimal('100'),Decimal('1')) == 0


def test_execution_cutoff_is_an_instant_not_a_guessed_expiry_date():
    cutoff=datetime(2027,1,15,16,30,tzinfo=timezone.utc)
    validate_option_execution(cutoff, cutoff, 'OPEN')
    validate_option_execution(cutoff, cutoff, 'CLOSE')
    with pytest.raises(ValueError): validate_option_execution(datetime(2027,1,15,16,31,tzinfo=timezone.utc),cutoff,'OPEN')
    with pytest.raises(ValueError): validate_option_execution(cutoff.replace(tzinfo=None),cutoff,'OPEN')
    with pytest.raises(ValueError): validate_option_execution(cutoff,cutoff,'MIXED')
