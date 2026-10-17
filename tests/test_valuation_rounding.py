from decimal import Decimal as D
import pytest


def test_stored_components_reconcile_and_preserve_exact_run_values():
    from valuation.rounding import rounded_result
    parts = {'PRICE': D('18290.0464683529188977927'),
             'FX': D('505.32591238784199189395'),
             'PRICE_FX_CROSS': D('14.4723660543160162121')}
    result = rounded_result(parts, market=D('18809.84474679507690589875'),
                            gross=D('18809.84474679507690589875'),
                            net=D('18809.84474679507690589875'))
    assert result['components']['PRICE'] == D('18290.046468352919')
    assert result['market'] == result['gross'] == result['net'] == D('18809.844746795077')
    assert sum(result['components'].values()) == result['market']
    assert result['evidence']['exact']['components'] == parts
    assert result['evidence']['adjustments']['market'] == D('0.00000000000009410125')


def test_half_even_handles_negative_ties_and_reconciles_income_costs():
    from valuation.rounding import rounded_result
    result = rounded_result({'PRICE': D('-1.0000000000005'), 'FX': D('0.0000000000005'),
                             'DIVIDEND': D('0.0000000000015'), 'TAX': D('-0.0000000000015')},
                            market=D('-1'), gross=D('-0.9999999999985'), net=D('-1'))
    assert result['components']['PRICE'] == D('-1')
    assert result['components']['FX'] == 0
    assert result['gross'] == D('-0.999999999998')
    assert result['net'] == D('-1')


@pytest.mark.parametrize('amount', ['1000000000000000000', '999999999999999999.9999999999999', 'NaN', 'Infinity'])
def test_invalid_or_overflowing_amount_is_explicit(amount):
    from valuation.rounding import rounded_result, StorageAmountError
    with pytest.raises(StorageAmountError):
        rounded_result({'PRICE': D(amount)}, market=D(amount), gross=D(amount), net=D(amount))


def test_maximum_representable_amount_is_not_lost_to_default_decimal_context():
    from valuation.rounding import rounded_result
    maximum = D('999999999999999999.999999999999')
    result = rounded_result({'PRICE': maximum}, market=maximum, gross=maximum, net=maximum)
    assert result['market'] == maximum
