from decimal import Decimal
import pytest
from security_master_schema.product_booking import execution_amount, validate_increment


@pytest.mark.parametrize('quantity,unit,basis,factor,denomination,price,expected',[
    ('100000','NOMINAL','PCT_OF_PAR','100',None,'98.5','98500'),
    ('100','UNITS','PCT_OF_PAR','100','1000','98.5','98500'),
    ('10','UNITS','UNIT_PRICE','100',None,'250','25'),
    ('2','CONTRACTS','INDEX_POINTS','1',None,'6000','60000'),
    ('2','CONTRACTS','INDEX_POINTS','1',None,'-1.25','-12.5'),
    ('2','CONTRACTS','INDEX_POINTS','1',None,'0','0'),
])
def test_exact_economics(quantity,unit,basis,factor,denomination,price,expected):
    assert execution_amount(quantity,price,quantity_unit=unit,price_basis=basis,
        quote_factor=factor,denomination=denomination,multiplier='5') == Decimal(expected)


def test_reject_missing_denomination():
    with pytest.raises(ValueError):
        execution_amount('1','98',quantity_unit='UNITS',price_basis='PCT_OF_PAR',quote_factor='100')


@pytest.mark.parametrize('value,step,minimum',[('1.5','1','1'),('6000.1','.25',None),('999','1000','1000')])
def test_reject_increment(value,step,minimum):
    with pytest.raises(ValueError): validate_increment(value,step,minimum=minimum)


def test_minimum_anchor_and_negative_tick():
    validate_increment('1500','500',minimum='1000')
    validate_increment('-1.25','.25')


def test_no_silent_rounding():
    with pytest.raises(ValueError):
        execution_amount('1','1',quantity_unit='UNITS',price_basis='UNIT_PRICE',quote_factor='3')
