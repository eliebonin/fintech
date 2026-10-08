from datetime import datetime,timezone,timedelta

def test_transaction_budgets_are_transaction_local():
    from apps.reference_api.resource_limits import configure_transaction_budget
    from apps.reference_api.config import Settings
    class Recorder:
        def __init__(self): self.calls=[]
        def execute(self,statement): self.calls.append(statement.compile().params)
    connection=Recorder()
    configure_transaction_budget(connection,Settings.from_environment())
    assert len(connection.calls)==2
    assert {'statement_timeout','30000',True}==set(connection.calls[0].values())
    assert {'lock_timeout','10000',True}==set(connection.calls[1].values())

def test_governance_clock_is_utc():
    from apps.reference_api.resource_limits import governance_date
    local=datetime(2026,10,6,23,tzinfo=timezone(timedelta(hours=-5)))
    assert governance_date(local).isoformat()=='2026-10-07'
