"""Historical replay and trading bridge edge cases with hand-derived P&L."""
from datetime import datetime, timezone
from decimal import Decimal as D
from uuid import UUID
import importlib
import pytest

def module():
    try: return importlib.import_module('tests.legacy_valuation_positions')
    except ModuleNotFoundError: pytest.fail('Historical position replay is not implemented')

def stamp(day): return datetime(2026, 10, day, 16, tzinfo=timezone.utc)

def booked(trade=1, quantity='10', price='100', day=1, recorded=1, **overrides):
    k = module()
    values = dict(trade_id=UUID(int=trade), subject_id=UUID(int=100), quantity=D(quantity),
                  price=D(price), currency_id=UUID(int=200), quantity_unit='SHARES',
                  unit_multiplier=D('1'), quote_factor=D('1'), executed_at=stamp(day))
    return k.BookingEvent(UUID(int=trade*10), UUID(int=trade), 1, 'BOOKED', stamp(day), stamp(recorded),
                          k.BookedLot(**(values | overrides)))

def test_historical_replay_ignores_late_recorded_cancellation_until_information_cutoff():
    k = module()
    event = k.BookingEvent(UUID(int=11), UUID(int=1), 2, 'CANCELLED', stamp(1), stamp(5))
    assert len(k.replay_bookings([booked(), event], stamp(3), stamp(3))) == 1
    assert k.replay_bookings([booked(), event], stamp(3), stamp(6)) == ()

def test_unrecorded_booking_is_not_known_history():
    assert module().replay_bookings([booked(recorded=5)], stamp(3), stamp(3)) == ()

def test_replacement_uses_original_economic_time_and_retains_only_new_lot():
    k=module()
    events=[booked(), k.BookingEvent(UUID(int=11), UUID(int=1), 2, 'SUPERSEDED', stamp(1), stamp(5)),
            booked(trade=2, quantity='12', recorded=5),
            k.BookingEvent(UUID(int=21), UUID(int=2), 2, 'CORRECTED', stamp(1), stamp(5))]
    lots=k.replay_bookings(events, stamp(3), stamp(6))
    assert [lot.trade_id for lot in lots] == [UUID(int=2)]
    assert lots[0].quantity == D('12')

@pytest.mark.parametrize('kind', ['AMENDED','DELIVERED','EXPIRED','NOVATED'])
def test_unimplemented_lifecycle_effects_fail_closed(kind):
    k=module()
    with pytest.raises(ValueError, match='Unsupported lifecycle'):
        k.replay_bookings([booked(), k.BookingEvent(UUID(int=11),UUID(int=1),2,kind,stamp(2),stamp(2))],stamp(3),stamp(3))

def test_unknown_future_event_does_not_block_prior_historical_view():
    k=module()
    events=[booked(),k.BookingEvent(UUID(int=11),UUID(int=1),2,'EXPIRED',stamp(5),stamp(2))]
    assert len(k.replay_bookings(events,stamp(3),stamp(3))) == 1

def test_missing_booked_evidence_and_duplicate_sequences_fail_closed():
    k=module()
    with pytest.raises(ValueError):
        k.replay_bookings([k.BookingEvent(UUID(int=11),UUID(int=1),2,'CANCELLED',stamp(1),stamp(2))],stamp(3),stamp(3))
    with pytest.raises(ValueError): k.replay_bookings([booked(),booked()],stamp(3),stamp(3))

def test_naive_cutoffs_and_bad_lot_evidence_fail_closed():
    k=module()
    with pytest.raises(ValueError): k.replay_bookings([booked()],datetime(2026,10,3),stamp(3))
    with pytest.raises(ValueError): k.replay_bookings([booked(quantity_unit='CONTRACTS')],stamp(3),stamp(3))

def test_period_opening_holdings_plus_new_sale_contribution():
    k=module()
    events=[booked(),booked(trade=2,quantity='-5',price='108',day=3,recorded=3)]
    marks={UUID(int=100):k.PeriodMarks(D('100'),D('110'),D('1'),D('1'))}
    result=k.attribute_period(events,stamp(2),stamp(4),stamp(4),marks,execution_fx={UUID(int=2):D('1')})
    assert result.market_pnl == D('90')
    assert result.opening_value == D('1000')
    assert result.closing_value == D('550')
    assert result.execution_value == D('-540')
    assert len(result.lines) == 2

def test_same_day_round_trip_is_not_lost_when_closing_position_is_zero():
    k=module()
    events=[booked(price='100',day=3,recorded=3),booked(trade=2,quantity='-10',price='108',day=3,recorded=3)]
    marks={UUID(int=100):k.PeriodMarks(D('99'),D('110'),D('1'),D('1'))}
    result=k.attribute_period(events,stamp(2),stamp(4),stamp(4),marks,execution_fx={UUID(int=1):D('1'),UUID(int=2):D('1')})
    assert result.market_pnl == D('80')
    assert result.closing_value == D('0')
    assert result.execution_value == D('-80')

def test_missing_execution_fx_and_market_marks_are_explicit_errors():
    k=module()
    events=[booked(day=3,recorded=3)]
    with pytest.raises(ValueError,match='mark'): k.attribute_period(events,stamp(2),stamp(4),stamp(4),{},execution_fx={})
    with pytest.raises(ValueError,match='execution FX'):
        k.attribute_period(events,stamp(2),stamp(4),stamp(4),{UUID(int=100):k.PeriodMarks(D('100'),D('110'),D('1'),D('1'))},execution_fx={})
