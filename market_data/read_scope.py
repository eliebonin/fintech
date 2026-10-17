"""Transaction-local read reuse, never a cross-request authorization cache."""
from contextlib import contextmanager
from copy import deepcopy
from security_master_schema.governance_clock import governance_date

_KEY = 'market_data_resolution_read_scope'


@contextmanager
def resolution_read_scope(c, *, tenant, actor, strategy, policy, information_cutoff, economic_date):
    if c.get_isolation_level() != 'REPEATABLE READ' or c.get_transaction() is None:
        raise ValueError('Resolution reuse requires an active repeatable-read transaction')
    previous = c.info.get(_KEY)
    c.info[_KEY] = dict(transaction=c.get_transaction(),
        identity=(tenant, actor, strategy, policy, information_cutoff, economic_date, governance_date()), values={})
    try:
        yield
    finally:
        if previous is None:
            c.info.pop(_KEY, None)
        else:
            c.info[_KEY] = previous


def cached_read(c, key, load):
    scope = c.info.get(_KEY)
    if scope is None:
        return load()
    if c.get_transaction() is not scope['transaction']:
        raise RuntimeError('Read reuse cannot cross a transaction boundary')
    values = scope['values']
    if key not in values:
        values[key] = deepcopy(load())
    return deepcopy(values[key])
