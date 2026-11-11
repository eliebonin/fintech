"""Current ledger knowledge uses the database's recording clock.

Economic dates remain explicit. Do not retime immutable facts or add a tolerance
window to historical projections to compensate for host/database clock drift.
"""
from datetime import timezone
from sqlalchemy import select,func

def recording_now(connection):
    """UTC observation time from the same clock that stamps persisted facts."""
    value=connection.scalar(select(func.clock_timestamp()))
    if value is None or value.tzinfo is None:raise ValueError('An aware database recording timestamp is required')
    return value.astimezone(timezone.utc)
