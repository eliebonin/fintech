"""Independent quotation examples: percentages are not decimal fractions or unit prices."""
from decimal import Decimal as D
import pytest


def convention(unit='UNITS',basis='UNIT_PRICE',factor='1',denomination=None):
    return dict(kind='ACTIVELY_MANAGED_CERTIFICATE',quantityUnit=unit,priceBasis=basis,
        quoteFactor=factor,denomination=denomination,funding='FULLY_FUNDED',accrual='NONE')


@pytest.mark.parametrize('terms,quantity,price,expected',[
    (convention(),D('10'),D('125'),D('1250')),
    (convention('UNITS','PCT_OF_PAR','100','1000'),D('10'),D('98'),D('9800')),
    (convention('NOMINAL','PCT_OF_PAR','100'),D('10000'),D('98'),D('9800')),
    (convention('UNITS','PCT_OF_PAR','100','1000'),D('-2'),D('98'),D('-1960')),
])
def test_quotation_dimensions_produce_equal_funded_security_measures(terms,quantity,price,expected):
    from security_master_schema.amc_quotation import quotation_factors
    from valuation.position_measures import cash_security
    multiplier,factor=quotation_factors(terms,terms['quantityUnit'])
    assert cash_security(quantity,price,multiplier,factor)==dict(referenceNotional=expected,economicExposure=expected,marketValue=expected)


@pytest.mark.parametrize('terms,unit',[
    (convention('UNITS','PCT_OF_PAR','100'), 'UNITS'),
    (convention('UNITS','PCT_OF_PAR','1','1000'),'UNITS'),
    (convention('NOMINAL','UNIT_PRICE'), 'NOMINAL'),
    (convention('UNITS','PCT_OF_PAR','100','NaN'),'UNITS'),
    (convention(), 'NOMINAL'),
])
def test_incomplete_or_conflicting_quote_dimensions_are_not_guessed(terms,unit):
    from security_master_schema.amc_quotation import quotation_factors
    with pytest.raises(ValueError):quotation_factors(terms,unit)
