"""Hand-derived expectations for exact attribution, not mirrored formulas."""
from decimal import Decimal as D
from uuid import UUID
import importlib
import pytest


def kernel():
    # A missing implementation is reported as an assertion in the initial RED run.
    try:
        return importlib.import_module('valuation.economics')
    except ModuleNotFoundError:
        pytest.fail('The dedicated valuation economics kernel is not implemented')


def inputs(**overrides):
    values = dict(quantity=D('10'), opening_price=D('100'), closing_price=D('110'),
                  opening_fx=D('1'), closing_fx=D('1.2'), unit_multiplier=D('1'), quote_factor=D('1'))
    return kernel().MarketInputs(**(values | overrides))


def test_exact_price_fx_cross_decomposition():
    result = kernel().attribute_market(inputs())
    assert result.price == D('100')
    assert result.fx == D('200')
    assert result.cross == D('20')
    assert result.market_pnl == D('320')
    assert result.opening_value == D('1000')
    assert result.closing_value == D('1320')


def test_short_and_quote_factor_are_applied_once():
    result = kernel().attribute_market(inputs(quantity=D('-10'), quote_factor=D('100'), unit_multiplier=D('50')))
    assert result.market_pnl == D('-160')
    assert result.price == D('-50')


def test_execution_to_close_contribution():
    result = kernel().attribute_market(inputs(quantity=D('-5'), opening_price=D('108'), opening_fx=D('1.2')))
    assert result.market_pnl == D('-12')


def test_precision_is_independent_of_callers_decimal_context():
    from decimal import localcontext
    with localcontext() as context:
        context.prec = 6
        result = kernel().attribute_market(inputs(quantity=D('1000000000000000000'), opening_price=D('100.000000000001'),
                                                 closing_price=D('100.000000000002'), closing_fx=D('1')))
    assert result.market_pnl == D('1000000')


@pytest.mark.parametrize('field,value', [('quantity', 1.0), ('opening_price', D('NaN')),
    ('closing_price', D('-1')), ('opening_fx', D('0')), ('quote_factor', D('0')), ('unit_multiplier', D('-1'))])
def test_invalid_numeric_inputs_fail_closed(field, value):
    with pytest.raises(ValueError):
        kernel().attribute_market(inputs(**{field: value}))


def test_hash_retains_decimal_precision_and_normalizes_mapping_order():
    k = kernel()
    a = {'id': UUID(int=1), 'price': D('100.0000000000000000001')}
    b = {'price': D('100.0000000000000000002'), 'id': UUID(int=1)}
    assert k.evidence_hash(a) != k.evidence_hash(b)
    assert k.evidence_hash(a) == k.evidence_hash(dict(reversed(list(a.items()))))
    assert k.canonical_payload(a)['price'] == '100.0000000000000000001'


def test_component_totals_do_not_hide_adjustments_in_market_pnl():
    k = kernel()
    k.validate_totals({'PRICE': D('100'), 'FX': D('200'), 'PRICE_FX_CROSS': D('20'),
                       'ACCRUAL': D('3'), 'BROKER_FEE': D('-2'), 'ADJUSTMENT': D('1')},
                      market=D('320'), gross=D('323'), net=D('322'))
    with pytest.raises(ValueError):
        k.validate_totals({'PRICE': D('100'), 'ADJUSTMENT': D('1')}, market=D('101'), gross=D('100'), net=D('101'))
    with pytest.raises(ValueError):
        k.validate_totals({'TYPO': D('100')}, market=D('0'), gross=D('0'), net=D('100'))

def test_equal_decimal_values_have_equal_identity_including_negative_zero():
    k=kernel()
    assert k.evidence_hash({'value':D('-0.00')})==k.evidence_hash({'value':D('0')})
    assert k.evidence_hash({'value':D('1.00')})==k.evidence_hash({'value':D('1')})

def test_nonterminating_normalization_requires_explicit_rounding_policy():
    with pytest.raises(ValueError,match='rounding'):
        kernel().attribute_market(inputs(quantity=D('1'),quote_factor=D('3')))
