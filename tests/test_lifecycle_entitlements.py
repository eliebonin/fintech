"""Subscription ceiling is platform-owned and independent of user grants."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def change(c,tier):
    from lifecycle.entitlements import preview_subscription_change,change_subscription
    from lifecycle.assistance_contracts import SubscriptionChange
    from lifecycle.entitlements import lifecycle_subscription_view
    revision=lifecycle_subscription_view(c,TENANT)['revision']
    preview=preview_subscription_change(c,ids['platform_admin_user_account'],TENANT,tier,revision)
    return change_subscription(c,ids['platform_admin_user_account'],ids['platform_admin_user_account'],TENANT,
        SubscriptionChange(maximumTier=tier,expectedRevision=revision,expectedImpactHash=preview['inputHash'],reason='Synthetic subscription',confirmChange=True,confirmBlockedWorkflows=True))


def test_subscription_absent_is_manual_and_changes_do_not_grant_user_actions(connection):
    from lifecycle.entitlements import lifecycle_subscription_view
    before=connection.scalar(select(func.count()).select_from(m.access_group_grant))
    assert lifecycle_subscription_view(connection,TENANT)['maximumTier']==0
    assert change(connection,3)['maximumTier']==3
    assert change(connection,2)['revision']==2
    assert connection.scalar(select(func.count()).select_from(m.tenant_lifecycle_subscription))==2
    assert connection.scalar(select(func.count()).select_from(m.access_group_grant))==before
    assert change(connection,0)['maximumTier']==0


def test_platform_only_revision_and_generic_module_bypass(connection):
    from lifecycle.entitlements import preview_subscription_change
    from security_master_schema.access_management import set_module
    with pytest.raises(PermissionError):preview_subscription_change(connection,ACTOR,TENANT,3,0)
    change(connection,3)
    with pytest.raises(ValueError,match='changed|revision'):preview_subscription_change(connection,ids['platform_admin_user_account'],TENANT,2,0)
    with pytest.raises(ValueError,match='subscription|tier'):set_module(connection,TENANT,ids['platform_admin_user_account'],'LIFECYCLE_MANAGEMENT',False)


def test_subscription_contract_rejects_invalid_tiers():
    from lifecycle.assistance_contracts import SubscriptionChange
    from pydantic import ValidationError
    for tier in [-1,4,True,'3']:
        with pytest.raises(ValidationError):SubscriptionChange(maximumTier=tier,expectedRevision=0,expectedImpactHash='a'*64,reason='x',confirmChange=True)


def test_expiry_is_non_grant_and_database_refuses_ambiguous_overlap(connection):
    from datetime import timedelta
    from sqlalchemy import update
    from lifecycle.entitlements import lifecycle_subscription_view
    from security_master_schema.governance_clock import governance_date
    change(connection,3)
    module=connection.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code=='LIFECYCLE_MANAGEMENT'))
    row=dict(connection.execute(select(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_id==TENANT,m.tenant_module_entitlement.c.platform_module_id==module)).mappings().one())
    with connection.begin_nested():
        connection.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_module_entitlement_id==row['tenant_module_entitlement_id']).values(valid_from=governance_date()-timedelta(days=10),valid_to=governance_date()-timedelta(days=1)))
        view=lifecycle_subscription_view(connection,TENANT)
        assert view['maximumTier']==0 and view['configuredMaximumTier']==3
    from sqlalchemy.exc import IntegrityError
    row.update(tenant_module_entitlement_id=uuid4(),valid_from=governance_date(),valid_to=None)
    connection.execute(m.tenant_module_entitlement.insert().values(**row))
    assert lifecycle_subscription_view(connection,TENANT)['maximumTier']==3
    # The deployed exclusion constraint is stronger than an ambiguous fixture:
    # it must reject overlapping periods before runtime can observe them.
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_module_entitlement_id!=row['tenant_module_entitlement_id'],m.tenant_module_entitlement.c.tenant_id==TENANT,m.tenant_module_entitlement.c.platform_module_id==module).values(valid_to=None))


def test_subscription_history_cannot_be_updated(connection):
    from sqlalchemy.exc import DBAPIError
    change(connection,3)
    with pytest.raises(DBAPIError),connection.begin_nested():connection.execute(m.tenant_lifecycle_subscription.update().where(m.tenant_lifecycle_subscription.c.tenant_id==TENANT).values(maximum_tier=0))
