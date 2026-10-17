"""Hand-derived RAW-price share-unit replay, with original executions immutable."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked, request, OPEN, CLOSE, INFO, SUBJECT, CURRENCY
from positions.contracts import SplitEvent, PositionError
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection, MarkKey


def split(ratio='2', when=None, n=1, **changes):
    when=when or OPEN+timedelta(hours=1)
    return replace(SplitEvent(UUID(int=3000+n), UUID(int=4000+n), SUBJECT,
        when, when.date(), OPEN-timedelta(days=1), D(ratio), True,
        {'sourceReference':'Synthetic reviewed test', 'eventType':'STOCK_SPLIT'}), **changes)


def test_split_inside_period_changes_holdings_not_booked_trade_or_economic_value():
    trade=booked(1,'100',OPEN-timedelta(days=10),price='10')
    p=reconstruct([trade],request(),splits=[split()])
    assert (p.buckets[0].opening_quantity,p.buckets[0].closing_quantity)==(100,200)
    assert p.facts[0].booking.quantity==100 and p.facts[0].booking.price==10
    assert p.executions==()
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('10'),MarkKey(SUBJECT,CLOSE):D('5')},CURRENCY)
    assert result.market_pnl==0
    assert (p.split_adjustments[0].quantity_before,p.split_adjustments[0].quantity_after)==(100,200)


def test_post_split_sale_flattens_and_keeps_period_execution_notional():
    p=reconstruct([booked(1,'100',OPEN-timedelta(days=1),'10'),
        booked(2,'-200',CLOSE,'5')],request(),splits=[split()])
    assert p.buckets[0].closing_quantity==0
    assert p.executions[0].booking.quantity==-200
    assert p.exposures[-1].ended_at==CLOSE
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('10')},CURRENCY).market_pnl==0


@pytest.mark.parametrize('quantity,ratio,expected',[('100','1.1','110'),('-100','2','-200'),('100','0.5','50')])
def test_basic_bonus_short_and_reverse_split(quantity,ratio,expected):
    p=reconstruct([booked(1,quantity,OPEN-timedelta(days=2))],request(),splits=[split(ratio)])
    assert p.buckets[0].closing_quantity==D(expected)


def test_multiple_splits_and_new_unit_buy():
    p=reconstruct([booked(1,'100',OPEN-timedelta(days=3)),booked(2,'10',OPEN+timedelta(hours=2))],
        request(),splits=[split(),split('1.1',CLOSE,n=2)])
    assert p.buckets[0].closing_quantity==231


def test_old_post_split_flat_episode_is_not_lineage_of_reopening():
    p=reconstruct([booked(1,'100',OPEN-timedelta(days=5)),booked(2,'-200',OPEN-timedelta(days=2)),
        booked(3,'10',CLOSE)],request(),splits=[split(when=OPEN-timedelta(days=3))])
    assert p.buckets[0].opening_quantity==0 and p.buckets[0].closing_quantity==10
    assert p.buckets[0].trade_ids==(UUID(int=103),)


def test_deferred_recognition_carries_intervening_split():
    trade=booked(1,'100',OPEN-timedelta(days=2),valuation_effective_date=CLOSE.date())
    p=reconstruct([trade],request(),splits=[split()])
    assert p.buckets[0].opening_quantity==0 and p.buckets[0].closing_quantity==200
    assert p.executions[0].booking.quantity==100


def test_action_not_visible_at_information_cutoff_is_not_applied():
    p=reconstruct([booked(1,'100',OPEN-timedelta(days=2))],request(),
        splits=[split(recorded_at=INFO+timedelta(seconds=1))])
    assert p.buckets[0].closing_quantity==100 and p.split_adjustments==()


def test_integer_only_bonus_blocks_fractional_entitlement_without_rounding():
    with pytest.raises(PositionError,match='fraction'):
        reconstruct([booked(1,'105',OPEN-timedelta(days=1))],request(),splits=[split('1.1')])


def test_explicit_fractional_split_can_retain_exact_quantity():
    p=reconstruct([booked(1,'105',OPEN-timedelta(days=1))],request(),
        splits=[split('1.1',whole_shares_only=False)])
    assert p.buckets[0].closing_quantity==D('115.5')


def test_conflicting_same_subject_events_block_instead_of_double_adjusting():
    with pytest.raises(PositionError,match='(?i)conflict'):
        reconstruct([booked(1,'100',OPEN-timedelta(days=1))],request(),splits=[split(),split('3',n=2)])


def test_duplicate_event_is_applied_once_and_exact_boundary_execution_blocks():
    action=split()
    facts=[booked(1,'100',OPEN-timedelta(days=1))]
    assert reconstruct(facts,request(),splits=[action,action]).buckets[0].closing_quantity==200
    with pytest.raises(PositionError,match='ordering'):
        reconstruct([booked(1,'100',action.effective_at)],request(),splits=[action])


def test_raw_prior_day_mark_cannot_value_post_split_units():
    from valuation import corporate_actions as actions
    with pytest.raises(ValueError,match='pre-action'):
        actions.assert_native_mark_units([split(when=CLOSE)],SUBJECT,CLOSE,
            OPEN.date(),daily=False)
    actions.assert_native_mark_units([split(when=CLOSE)],SUBJECT,CLOSE,CLOSE.date(),daily=False)


def test_daily_recognition_uses_post_action_units_and_trade_on_ex_date_does_not_split_twice():
    action=split(when=CLOSE.replace(hour=4))
    trade=booked(1,'100',CLOSE.replace(hour=10))
    p=reconstruct([trade],request(daily=True),splits=[action])
    assert p.buckets[0].opening_quantity==0 and p.buckets[0].closing_quantity==100
    assert p.split_adjustments==()


def test_deferred_trade_on_action_day_is_converted_once():
    action=split(when=CLOSE.replace(hour=4))
    trade=booked(1,'100',OPEN-timedelta(days=1),valuation_effective_date=CLOSE.date())
    p=reconstruct([trade],request(daily=True),splits=[action])
    assert p.buckets[0].opening_quantity==0 and p.buckets[0].closing_quantity==200


def test_approved_split_changes_only_overnight_fx_not_price_pnl():
    gbp=UUID(int=999)
    p=reconstruct([booked(1,'100',OPEN-timedelta(days=1),'10')],request(),splits=[split()])
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('10'),MarkKey(SUBJECT,CLOSE):D('5')},
        gbp,{(CURRENCY,OPEN):D('.85'),(CURRENCY,CLOSE):D('.86')})
    assert result.market_pnl==D('10')
    assert result.lines[0].attribution.price==0 and result.lines[0].attribution.cross==0
    assert result.lines[0].attribution.fx==10
