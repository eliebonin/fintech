from dataclasses import replace
from datetime import date,datetime,timezone,timedelta
from decimal import Decimal as D
from tests.test_position_reconstruction import booked,request,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import required_marks,attribute_projection

def daily(opening=6,closing=7):
    return request(opening_cutoff=datetime(2026,10,opening,23,59,59,999999,tzinfo=timezone.utc),
        closing_cutoff=datetime(2026,10,closing,23,59,59,999999,tzinfo=timezone.utc),
        information_cutoff=datetime(2026,10,9,tzinfo=timezone.utc),daily=True)

def trade(n,quantity,price='100',recognition_day=8):
    return booked(n,quantity,datetime(2026,10,7,18,tzinfo=timezone.utc),price,
        valuation_effective_date=date(2026,10,recognition_day))

def test_deferred_trade_has_no_position_or_execution_until_recognition_date():
    fact=trade(1,'2')
    before=reconstruct([fact],daily())
    assert before.buckets==before.executions==()
    after=reconstruct([fact],daily(7,8))
    assert after.buckets[0].opening_quantity==0 and after.buckets[0].closing_quantity==2
    assert len(after.executions)==1
    marks=required_marks(after)
    result=attribute_projection(after,{marks[0].key:D(110)},CURRENCY)
    assert result.market_pnl==20 and result.execution_value==200
    assert after.exposures[0].started_at==fact.effective_at

def test_deferred_round_trip_moves_both_execution_contributions():
    facts=[trade(1,'2'),trade(2,'-2','110')]
    after=reconstruct(facts,daily(7,8))
    assert required_marks(after)==()
    assert attribute_projection(after,{},CURRENCY).market_pnl==20

def test_legacy_execution_late_in_day_enters_daily_position():
    fact=booked(1,'2',datetime(2026,10,7,23,30,tzinfo=timezone.utc))
    after=reconstruct([fact],daily())
    assert after.buckets[0].closing_quantity==2 and len(after.executions)==1

def test_cancellation_before_deferred_recognition_does_not_make_missing_booked_chain():
    original=trade(1,'2')
    cancelled=replace(original,event_id=original.event_id.__class__(int=9000),sequence=2,kind='CANCELLED',booking=None)
    assert reconstruct([original,cancelled],daily(7,8)).buckets==()


def test_deferred_reporting_does_not_bypass_actual_corporate_action_exposure():
    from valuation.corporate_actions import action_requires_replay
    fact=trade(1,'2')
    projection=reconstruct([fact],daily(7,8))
    interval=projection.exposures[0]
    # The action is after execution but before recognition, so still blocks
    # raw-position valuation until action replay is supported.
    action=dict(timestamp_value_utc=datetime(2026,10,7,19,tzinfo=timezone.utc))
    assert action_requires_replay(interval.started_at,interval.ended_at,[action],'UTC')


def test_late_recording_obeys_frozen_information_cutoff():
    fact=replace(trade(1,'2'),recorded_at=datetime(2026,10,9,1,tzinfo=timezone.utc))
    assert reconstruct([fact],daily(7,8)).buckets==()
