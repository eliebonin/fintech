"""A proven record correction can remove economics, never its audit history."""
from dataclasses import replace
from datetime import timedelta
import pytest
from positions.contracts import PositionError
from positions.reconstruction import reconstruct
from tests.test_position_reconstruction import booked,event,request,OPEN,CLOSE,INFO


@pytest.mark.parametrize('kind',['CANCELLED','SUPERSEDED'])
def test_removed_legacy_booking_needs_no_economic_snapshot_but_retains_audit(kind):
    original=replace(booked(1,'2',OPEN-timedelta(days=2)),booking=None)
    removed=event(original,kind,original.effective_at)
    projection=reconstruct([original,removed],request())
    assert projection.buckets==projection.executions==projection.exposures==()
    assert [f.kind for f in projection.facts]==['BOOKED',kind]


def test_active_legacy_booking_remains_blocked_before_cancellation_is_known():
    original=replace(booked(1,'2',OPEN-timedelta(days=2)),booking=None)
    removed=event(original,'CANCELLED',original.effective_at,recorded=INFO+timedelta(seconds=1))
    with pytest.raises(PositionError,match='BOOKED'):
        reconstruct([original,removed],request())


def test_in_period_removal_without_snapshot_is_not_silently_excluded():
    original=replace(booked(1,'2',OPEN),booking=None)
    with pytest.raises(PositionError,match='in-period'):
        reconstruct([original,event(original,'CANCELLED',CLOSE)],request())


@pytest.mark.parametrize('change',[dict(sequence=3),dict(kind='DELIVERED'),dict(effective_at=OPEN-timedelta(days=3))])
def test_malformed_legacy_removal_chain_is_not_empty_success(change):
    original=replace(booked(1,'2',OPEN-timedelta(days=2)),booking=None)
    removed=replace(event(original,'CANCELLED',original.effective_at),**change)
    with pytest.raises(PositionError): reconstruct([original,removed],request())
