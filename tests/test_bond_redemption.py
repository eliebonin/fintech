from decimal import Decimal as D
from types import SimpleNamespace
import pytest


def test_remaining_long_and_short_are_closed_at_sourced_redemption_price():
    from lifecycle.bond_redemption import closing_movements
    buckets=[SimpleNamespace(key=SimpleNamespace(quantity_unit='NOMINAL',unit_multiplier=D(1),quote_factor=D(100)),closing_quantity=D(60000)),
             SimpleNamespace(key=SimpleNamespace(quantity_unit='NOMINAL',unit_multiplier=D(1),quote_factor=D(100)),closing_quantity=D(-20000))]
    result=closing_movements(buckets,D('105'))
    assert result==[{'quantity':'-60000','price':'105','cleanAmount':'63000'}, {'quantity':'20000','price':'105','cleanAmount':'21000'}]


@pytest.mark.parametrize('price',[None,D(0),D('NaN'),D('-1')])
def test_unknown_or_unsupported_redemption_price_is_not_defaulted(price):
    from lifecycle.bond_redemption import closing_movements
    with pytest.raises(ValueError): closing_movements([],price)
