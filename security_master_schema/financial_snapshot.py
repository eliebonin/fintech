"""Stable financial reads; current access must be checked separately on release."""
from contextlib import contextmanager


@contextmanager
def repeatable_read_transaction(engine):
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            yield connection
