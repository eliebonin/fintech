"""Contractual amounts are not discounted MTM or cash balances."""
from decimal import Decimal as D
import pytest
from valuation import position_measures as measures


@pytest.mark.parametrize('amount,rate,quote',[
    ('1000000','1.10','-1100000'),('-1000000','1.10','1100000'),
    ('0','1.10','0'),('123.456','1.123456789','-138.697481342784'),
])
def test_forward_contractual_legs_preserve_exact_sign_and_quote_orientation(amount,rate,quote):
    result=measures.fx_forward_legs(D(amount),D(rate))
    assert result==dict(baseAmount=D(amount),quoteAmount=D(quote))


@pytest.mark.parametrize('amount,rate',[
    ('NaN','1.1'),('Infinity','1.1'),('1','NaN'),('1','Infinity'),('1','0'),('1','-1'),
])
def test_invalid_contractual_amounts_are_rejected(amount,rate):
    with pytest.raises(ValueError):measures.fx_forward_legs(D(amount),D(rate))
