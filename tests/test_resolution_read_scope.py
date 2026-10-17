"""Cached decisions belong to one transaction and are not mutable shared state."""
from datetime import date,datetime,timezone
from types import SimpleNamespace
import pytest
from market_data.read_scope import cached_read,resolution_read_scope


def scope(c,actor='one'):
    return resolution_read_scope(c,tenant='tenant',actor=actor,strategy='strategy',policy='policy',
        information_cutoff=datetime(2026,10,16,tzinfo=timezone.utc),economic_date=date(2026,10,15))


def connection():
    c=SimpleNamespace(info={},transaction=object())
    c.get_isolation_level=lambda:'REPEATABLE READ'
    c.get_transaction=lambda:c.transaction
    return c


def test_reuse_is_scoped_restored_and_returns_independent_values():
    c=connection();calls=[]
    def load():calls.append(1);return {'decisions':['allowed']}
    with scope(c):
        result=cached_read(c,'rights',load);result['decisions'].clear()
        assert cached_read(c,'rights',load)=={'decisions':['allowed']}
        with scope(c,'another'):
            assert cached_read(c,'rights',load)=={'decisions':['allowed']}
        assert len(calls)==2
    assert c.info=={}
    cached_read(c,'rights',load)
    assert len(calls)==3


def test_reuse_rejects_transaction_change_and_cleans_up_on_failure():
    c=connection()
    with pytest.raises(RuntimeError,match='transaction boundary'):
        with scope(c):
            c.transaction=object();cached_read(c,'rights',lambda:'allowed')
    assert c.info=={}


def test_read_committed_connection_cannot_enable_reuse():
    c=connection();c.get_isolation_level=lambda:'READ COMMITTED'
    with pytest.raises(ValueError,match='repeatable-read'):
        with scope(c):pass
