from decimal import Decimal
import pytest
from security_master_schema.product_booking import bond_amounts

@pytest.mark.parametrize('basis,quote,accrual,expected',[('CLEAN','98.5','1250',('98500','99750')),('DIRTY','99.75','1250',('98500','99750')),('CLEAN','98.5','-250',('98500','98250')),('DIRTY','98.25','-250',('98500','98250')),('CLEAN','98.5','0',('98500','98500'))])
def test_exact_bond_breakdown(basis,quote,accrual,expected):
    assert bond_amounts('100000',quote,basis,accrual)==tuple(map(Decimal,expected))

@pytest.mark.parametrize('basis,quote,accrual',[('CLEAN','1','-2000'),('DIRTY','1','2000'),('UNKNOWN','98','0'),('CLEAN','-1','0')])
def test_invalid_bond_breakdown(basis,quote,accrual):
    with pytest.raises(ValueError):bond_amounts('100000',quote,basis,accrual)
