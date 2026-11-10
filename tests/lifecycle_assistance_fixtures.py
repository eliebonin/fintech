"""Explicit synthetic configuration for pre-existing lifecycle service fixtures."""
from lifecycle.assistance import selection,configure_assistance
from lifecycle.assistance_contracts import AssistanceChange
from lifecycle.entitlements import lifecycle_subscription_view,preview_subscription_change,change_subscription
from lifecycle.assistance_contracts import SubscriptionChange
from security_master_schema.demo_data import DEMO_IDS as ids


def enable(c,tenant,strategy,event):
    current=lifecycle_subscription_view(c,tenant)
    if current['maximumTier']!=3:
        preview=preview_subscription_change(c,ids['platform_admin_user_account'],tenant,3,current['revision'])
        current=change_subscription(c,ids['platform_admin_user_account'],ids['platform_admin_user_account'],tenant,SubscriptionChange(maximumTier=3,expectedRevision=current['revision'],expectedImpactHash=preview['inputHash'],reason='Explicit disposable lifecycle fixture',confirmChange=True,confirmBlockedWorkflows=True))
    row=selection(c,tenant,strategy,event)
    configure_assistance(c,tenant,ids['demo_user_account'],ids['demo_user_account'],AssistanceChange(strategyId=strategy,eventType=event,selectedTier=3,expectedRevision=row['revision'] if row else 0,expectedSubscriptionRevision=current['revision'],reason='Explicit disposable lifecycle fixture'))
