from datetime import date
from decimal import Decimal as D

from valuation.accrued_balance import replay_balances


def replay(*, earnings=None, movements=None, payments=None, anchors=None):
    return replay_balances(date(2026,10,1),date(2026,10,3),
        earnings=earnings or {}, movements=movements or {}, payments=payments or {},
        opening=D('990'), anchors=anchors or {})


def test_coupon_payment_is_stock_movement_and_preserves_new_period_interest():
    rows=replay(earnings={date(2026,10,1):D(10),date(2026,10,2):D(20),date(2026,10,3):D(20)},
                payments={date(2026,10,2):D(1000)})
    assert [(r.opening,r.closing) for r in rows]==[(D(990),D(1000)),(D(1000),D(20)),(D(20),D(40))]
    assert rows[1].daily_earned==20 and rows[1].coupon_paid==1000


def test_missing_earned_amount_is_unknown_not_zero_and_anchor_recovers_next_day():
    rows=replay(earnings={date(2026,10,1):D(10),date(2026,10,3):D(5)},anchors={date(2026,10,2):D(123)})
    assert rows[1].daily_earned is None and rows[1].opening==1000
    assert rows[1].closing==123 and rows[1].basis=='SUPPLIED_CLOSING_ANCHOR'
    assert rows[2].opening==123 and rows[2].closing==128
    broken=replay(earnings={date(2026,10,1):D(10),date(2026,10,3):D(5)})
    assert broken[1].closing is None and broken[2].opening is None and broken[2].closing is None


def test_negative_trade_accrued_and_partial_receipts_are_not_forced_to_zero():
    rows=replay(earnings={date(2026,10,1):D(10),date(2026,10,2):D(10),date(2026,10,3):D(10)},
        movements={date(2026,10,1):D(-25),date(2026,10,2):D(-300)},payments={date(2026,10,3):D(200)})
    assert rows[0].closing==975 and rows[1].closing==685 and rows[2].closing==495


def test_missing_payment_conversion_breaks_stock_but_preserves_known_opening():
    rows=replay(earnings={date(2026,10,1):D(10),date(2026,10,2):D(10),date(2026,10,3):D(10)},
                payments={date(2026,10,2):None})
    assert rows[1].opening==1000 and rows[1].closing is None
    assert rows[2].opening is None
