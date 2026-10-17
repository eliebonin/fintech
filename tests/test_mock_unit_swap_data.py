"""Synthetic examples are deterministic evidence, never a production pricer."""
from decimal import Decimal


def test_mock_swap_histories_are_dated_whole_swap_unit_values():
    from scripts.mock_unit_swap_data import build_history
    for code in ('SPX','UKX'):
        data=build_history(code)
        assert data['synthetic'] is True
        assert len(data['prices'])>490
        assert data['prices'][0]['date']=='2024-10-15'
        assert Decimal(data['prices'][0]['close'])==0
        assert data['prices'][-1]['date']=='2026-10-14'
        assert not any(point['date']=='2024-12-25' for point in data['prices'])
        assert all(Decimal(point['close']).is_finite() and point['observedAt'].endswith('+00:00') for point in data['prices'])
        assert data==build_history(code)


def test_mock_leverage_is_applied_once_not_to_trade_quantity():
    from scripts.mock_unit_swap_data import build_history
    unlevered=build_history('UKX',leverage=Decimal('1'))
    leveraged=build_history('UKX')
    for first,second in zip(unlevered['prices'],leveraged['prices']):
        assert first['indexLevel']==second['indexLevel']
        assert abs(Decimal(second['close'])-Decimal(first['close'])*Decimal('1.5'))<=Decimal('0.000000015')
