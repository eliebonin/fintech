from decimal import Decimal as D
import pytest


@pytest.mark.parametrize('quantity,expected', [('1000000','-1000000'),('-1000000','1000000')])
def test_closure_preserves_base_amount_and_quote_rate(quantity,expected):
    from lifecycle.fx_maturity import closing_economics
    result=closing_economics(D(quantity),D('1.12'))
    assert result['quantity']==expected
    assert result['price']=='1.12'
    assert D(result['quoteAmount'])==D('1120000')
    assert result['paymentRecognised'] is False


@pytest.mark.parametrize('rate',[D(0),D(-1),D('NaN'),D('Infinity')])
def test_unknown_or_invalid_rate_never_defaults(rate):
    from lifecycle.fx_maturity import closing_economics
    with pytest.raises(ValueError):closing_economics(D(100),rate)


def test_flat_exposure_does_not_create_closure():
    from lifecycle.fx_maturity import closing_economics
    with pytest.raises(ValueError):closing_economics(D(0),D('1.12'))


@pytest.mark.parametrize('value',[
 {'rate':'0','sourceReference':'CP','reason':'Confirmed'},
 {'rate':'NaN','sourceReference':'CP','reason':'Confirmed'},
 {'rate':'1.1234567890123','sourceReference':'CP','reason':'Confirmed'},
 {'rate':'1000000000000000000','sourceReference':'CP','reason':'Confirmed'},
 {'rate':'1.12','sourceReference':'  ','reason':'Confirmed'},
 {'rate':'1.12','sourceReference':'CP','reason':''},
 {'rate':1.12,'sourceReference':'CP','reason':'Confirmed'},
])
def test_invalid_manual_rates_and_missing_provenance_are_rejected(value):
    from lifecycle.fx_maturity import validated_override
    with pytest.raises(ValueError):validated_override(value)
