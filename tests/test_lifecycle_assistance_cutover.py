"""Technical cutover copies only explicit old policy intent; no paid grant."""
from sqlalchemy import select,func
from uuid import uuid4
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_cutover_preserves_native_history_and_does_not_enable_subscription(connection):
    from scripts.cutover_lifecycle_assistance import backfill_lifecycle_assistance
    from lifecycle.entitlements import lifecycle_subscription_view
    from lifecycle.assistance import selection
    tenant,strategy=uuid4(),uuid4()
    organisation=connection.scalar(select(m.tenant.c.owning_organisation_id).where(m.tenant.c.tenant_id==TENANT))
    connection.execute(m.tenant.insert().values(tenant_id=tenant,owning_organisation_id=organisation,tenant_code='CUTOVER_'+tenant.hex,display_name='Owned cutover tenant'))
    connection.execute(m.strategy.insert().values(strategy_id=strategy,tenant_id=tenant,strategy_code='CUTOVER',display_name='Owned cutover strategy',strategy_type='FUND'))
    before=connection.execute(select(m.trade_lifecycle_event.c.trade_lifecycle_event_id,m.trade_lifecycle_event.c.event_payload)).all()
    grants=connection.scalar(select(func.count()).select_from(m.access_group_grant))
    connection.execute(m.bond_redemption_policy.insert().values(tenant_id=tenant,strategy_id=strategy,revision=1,mode='DIRECT',reason='Retained legacy choice',actor_id=ACTOR,real_operator_id=ACTOR))
    native=connection.execute(select(m.bond_redemption_policy)).all()
    assert backfill_lifecycle_assistance(connection,ids['platform_admin_user_account'],tenant)['createdSelections']==1
    assert selection(connection,tenant,strategy,'BOND_MATURITY')['selected_tier']==3
    assert lifecycle_subscription_view(connection,tenant)['maximumTier']==0
    assert backfill_lifecycle_assistance(connection,ids['platform_admin_user_account'],tenant)['createdSelections']==0
    assert connection.execute(select(m.bond_redemption_policy)).all()==native
    assert connection.execute(select(m.trade_lifecycle_event.c.trade_lifecycle_event_id,m.trade_lifecycle_event.c.event_payload)).all()==before
    assert connection.scalar(select(func.count()).select_from(m.access_group_grant))==grants
