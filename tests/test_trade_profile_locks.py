"""Profile assignment and booking use one tenant-before-strategy lock order."""
from uuid import uuid4
from security_master_schema.booking_controls import lock_booking_strategy


def test_configuration_lock_precedes_strategy_row_lock():
    calls=[];strategy=uuid4()
    class Connection:
        def execute(self,statement):calls.append(('execute',str(statement)))
        def scalar(self,statement):calls.append(('scalar',str(statement)));return strategy
    assert lock_booking_strategy(Connection(),uuid4(),strategy)==strategy
    assert calls[0][0]=='execute' and 'pg_advisory_xact_lock' in calls[0][1]
    assert calls[1][0]=='scalar' and 'FOR UPDATE' in calls[1][1]
