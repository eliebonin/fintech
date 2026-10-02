from decimal import Decimal
import pytest
from pydantic import TypeAdapter, ValidationError
from security_master_schema import product_booking as rules
from apps.reference_api.product_booking_contracts import BookingConvention


@pytest.mark.parametrize('nominal,price,factor,want', [
    ('1000000','2','100','20000'), ('1000000','-1.5','100','-15000'),
    ('1000000','0.02','1','20000'), ('1000000','0','100','0'),
    ('-1000000','2','100','-20000'),
    ('99999999999999999.123456789012','1','1','99999999999999999.123456789012'),
])
def test_swap_quote_value(nominal,price,factor,want):
    assert rules.swap_reference_value(Decimal(nominal),Decimal(price),Decimal(factor)) == Decimal(want)


@pytest.mark.parametrize('nominal,price,factor', [
    ('0','1','100'), ('1','NaN','100'), ('1','Infinity','100'),
    ('1','1','0'), ('1','1','-1'), ('1','1','NaN'),
    ('1','1','3'), ('1000000000000000000','1','1'),
])
def test_swap_rejects_invalid_or_inexact_values(nominal,price,factor):
    with pytest.raises(ValueError): rules.swap_reference_value(Decimal(nominal),Decimal(price),Decimal(factor))


def convention(**changes):
    return dict(kind='SWAP',effectiveFrom='2026-09-01',priceCurrencyId='00000000-0000-7000-8000-000000000001',
        quoteFactor='100',sourceReference='Synthetic swap confirmation',quantityUnit='NOMINAL',
        priceBasis='SWAP_VALUE_PER_NOTIONAL',quantityMinimum='1000',quantityIncrement='1000',otcAllowed=True) | changes


def test_swap_convention_requires_explicit_divisor_and_basis():
    adapter=TypeAdapter(BookingConvention)
    assert adapter.validate_python(convention()).quote_factor==100
    assert adapter.validate_python(convention(quoteFactor='1')).quote_factor==1
    for changes in ({'quoteFactor':None},{'quoteFactor':'0'},{'priceBasis':'UNIT_PRICE'},{'quantityUnit':'SHARES'}):
        with pytest.raises(ValidationError):adapter.validate_python(convention(**changes))
