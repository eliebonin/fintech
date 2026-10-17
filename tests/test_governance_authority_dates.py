"""Current authority and current dataset visibility share one pinned UTC date."""
from datetime import date, datetime, timezone
from sqlalchemy import update
from tests.test_access_management import connection
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.governance_clock import governance_scope


class HostLocalTomorrow(date):
    @classmethod
    def today(cls):return cls(2026,10,17)


def test_admin_strategy_and_dataset_checks_do_not_follow_host_date(connection,monkeypatch):
    from security_master_schema import access_management as am, strategy_access as sa
    from market_data import display_access as display
    end=date(2026,10,16)
    connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==ids['tenant'])
        .values(valid_to=end))
    connection.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_id==ids['tenant'])
        .values(valid_to=end))
    connection.execute(update(m.tenant_dataset_entitlement).where(m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'])
        .values(valid_to=end))
    for module in (am,sa,display):monkeypatch.setattr(module,'date',HostLocalTomorrow,raising=False)
    with governance_scope(datetime(2026,10,16,23,59,tzinfo=timezone.utc)):
        am.require_admin(connection,ids['tenant'],ids['demo_user_account'])
        sa.require_strategy_action(connection,ids['tenant'],ids['demo_user_account'],'VALUATION_READ',ids['strategy'])
        display.assert_dataset_display(connection,ids['tenant'],{ids['dataset']},series_contexts={(ids['dataset'],ids['market_data_series'])})
