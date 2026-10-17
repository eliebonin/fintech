from datetime import date
from scripts.seed_valuation_review_trades import scenarios, settlement_day


def test_named_history_contains_multiple_executions_and_period_trades():
    rows=scenarios()
    assert len(rows)==29
    assert len({r['symbol'] for r in rows})==8
    assert min(r['date'] for r in rows)==date(2024,10,15)
    assert max(r['date'] for r in rows)==date(2026,10,8)
    assert sum(r['date']==date(2026,10,8) for r in rows)==3
    assert next(r['date'] for r in rows if r['symbol']=='AI')==date(2026,7,15)
    for symbol in {r['symbol'] for r in rows}:
        quantity=0
        for row in sorted((r for r in rows if r['symbol']==symbol),key=lambda r:r['date']):
            quantity+=row['quantity'] if row['side']=='BUY' else -row['quantity']
            assert quantity>0  # Partial sells, not accidental short positions.


def test_settlement_business_days_skip_weekends_and_source_closed_dates():
    assert settlement_day(date(2026,10,8))==date(2026,10,12)
    assert settlement_day(date(2026,4,2),{date(2026,4,3),date(2026,4,6)})==date(2026,4,8)
