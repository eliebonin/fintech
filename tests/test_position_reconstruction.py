"""Price-independent reference reconstruction: ledger evidence is authoritative."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest

from positions.contracts import Booking, LedgerFact, ProjectionRequest, PositionError
from positions.reconstruction import reconstruct

UTC = timezone.utc
TENANT, STRATEGY, SUBJECT, CURRENCY = [UUID(int=i) for i in range(1, 5)]
OPEN = datetime(2026, 10, 6, 20, tzinfo=UTC)
CLOSE = OPEN + timedelta(days=1)
INFO = CLOSE + timedelta(days=1)


def request(**changes):
    return replace(ProjectionRequest(TENANT, STRATEGY, CLOSE, INFO, OPEN, 'PERIOD'), **changes)


def booked(n, quantity, when, price='100', **changes):
    booking = replace(Booking(UUID(int=100+n), SUBJECT, CURRENCY, 'SHARES', D(quantity),
                              D(price), D('1'), D('1'), UUID(int=50), 'EQUITY'), **changes)
    return LedgerFact(UUID(int=1000+n), booking.trade_id, TENANT, STRATEGY, 1,
                      'BOOKED', when, when, booking)


def event(original, kind, when, recorded=None, sequence=2):
    return LedgerFact(UUID(int=2000+original.trade_id.int), original.trade_id,
                      TENANT, STRATEGY, sequence, kind, when, recorded or when)


def test_old_flat_episode_requires_no_position_line():
    p = reconstruct([booked(1,'5',OPEN-timedelta(days=4)),
                     booked(2,'-5',OPEN-timedelta(days=3))], request())
    assert p.buckets == () and p.executions == ()
    assert p.facts_scanned == 2

def test_old_closed_episode_is_not_lineage_of_a_new_holding():
    p=reconstruct([booked(1,'5',OPEN-timedelta(days=4)),booked(2,'-5',OPEN-timedelta(days=3)),
                   booked(3,'2',OPEN-timedelta(days=1)),booked(4,'1',CLOSE)],request())
    assert p.buckets[0].trade_ids==(UUID(int=103),UUID(int=104))
    assert p.buckets[0].opening_quantity==2 and p.buckets[0].closing_quantity==3


def test_round_trip_and_reopening_keep_every_period_execution():
    p = reconstruct([booked(1,'2',OPEN+timedelta(hours=1)),
                     booked(2,'-2',OPEN+timedelta(hours=2),'110'),
                     booked(3,'4',OPEN+timedelta(hours=3))], request())
    assert p.buckets[0].opening_quantity == 0
    assert p.buckets[0].closing_quantity == 4
    assert [x.booking.quantity for x in p.executions] == [2,-2,4]


def test_longstanding_fractional_holding_and_partial_sale():
    p = reconstruct([booked(1,'0.003',OPEN-timedelta(days=1000)),
                     booked(2,'-0.001',CLOSE)], request())
    assert p.buckets[0].opening_quantity == D('0.003')
    assert p.buckets[0].closing_quantity == D('0.002')


def test_short_reversal_and_cutoff_boundaries():
    p = reconstruct([booked(1,'-3',OPEN), booked(2,'5',CLOSE),
                     booked(3,'8',CLOSE+timedelta(seconds=1))], request())
    assert p.buckets[0].opening_quantity == -3
    assert p.buckets[0].closing_quantity == 2
    assert [x.booking.trade_id for x in p.executions] == [UUID(int=102)]


@pytest.mark.parametrize('change', [dict(subject_id=UUID(int=9)),dict(currency_id=UUID(int=9)),
    dict(unit_multiplier=D('2')),dict(quote_factor=D('100')),dict(quantity_unit='UNITS')])
def test_incompatible_economics_do_not_net(change):
    p = reconstruct([booked(1,'2',OPEN),booked(2,'-2',OPEN,**change)], request())
    assert len(p.buckets) == 2


def test_definition_id_alone_does_not_split_equivalent_buckets():
    p = reconstruct([booked(1,'2',OPEN),booked(2,'3',OPEN,definition_id=UUID(int=51))], request())
    assert len(p.buckets) == 1 and p.buckets[0].closing_quantity == 5
    assert set(p.buckets[0].definition_ids) == {UUID(int=50),UUID(int=51)}


def test_recorded_cutoff_controls_historical_cancellation():
    b = booked(1,'2',OPEN-timedelta(days=2))
    cancel = event(b,'CANCELLED',OPEN-timedelta(days=1),INFO+timedelta(seconds=1))
    assert reconstruct([b,cancel],request()).buckets[0].closing_quantity == 2
    assert reconstruct([b,cancel],request(information_cutoff=cancel.recorded_at)).buckets == ()


def test_in_period_cancellation_is_not_a_sale():
    b = booked(1,'2',OPEN)
    with pytest.raises(PositionError,match='in-period'):
        reconstruct([b,event(b,'CANCELLED',CLOSE)],request())


@pytest.mark.parametrize('kind',['EXPIRED','DELIVERED','UNKNOWN'])
def test_unsupported_lifecycle_blocks_instead_of_disappearing(kind):
    b = booked(1,'2',OPEN)
    with pytest.raises(PositionError,match='Unsupported lifecycle'):
        reconstruct([b,event(b,kind,CLOSE)],request())


def test_missing_sequence_and_scope_mismatch_block():
    b = booked(1,'2',OPEN)
    with pytest.raises(PositionError,match='sequence'):
        reconstruct([b,event(b,'CORRECTED',CLOSE,sequence=3)],request())
    with pytest.raises(PositionError,match='scope'):
        reconstruct([replace(b,tenant_id=UUID(int=999))],request())


def test_same_time_order_does_not_change_hash_or_projection():
    a,b = booked(1,'2',OPEN),booked(2,'-1',OPEN)
    assert reconstruct([a,b],request()) == reconstruct([b,a],request())


def test_valid_empty_and_as_of_views():
    p = reconstruct([],request())
    assert p.buckets == () and p.complete_knowledge is True
    p = reconstruct([booked(1,'2',OPEN)],request(mode='AS_OF',opening_cutoff=None))
    assert p.buckets[0].opening_quantity == 0 and p.buckets[0].closing_quantity == 2
    assert p.executions == ()
    assert reconstruct([],request(information_cutoff=OPEN)).complete_knowledge is False


def test_missing_original_booking_is_not_empty_success():
    b = booked(1,'2',OPEN)
    with pytest.raises(PositionError,match='BOOKED'):
        reconstruct([event(b,'CORRECTED',CLOSE,sequence=1)],request())
