"""A commercial change waits for current shared lifecycle use through commit."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic,sleep
from uuid import uuid4
from sqlalchemy import select,text
from tests.test_governed_trade_configuration import engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from lifecycle.entitlements import lifecycle_lock,preview_subscription_change,change_subscription
from lifecycle.assistance_contracts import SubscriptionChange


def test_subscription_change_waits_for_shared_lifecycle_transaction(engine):
    tenant=uuid4()
    with engine.begin() as c:
        base=dict(c.execute(select(m.tenant).where(m.tenant.c.tenant_id==ids['tenant'])).mappings().one())
        c.execute(m.tenant.insert().values(**(base|dict(tenant_id=tenant,tenant_code='LIFERACE_'+tenant.hex))))
    channel=Queue()
    def change():
        with engine.begin() as c:
            channel.put(c.scalar(text('select pg_backend_pid()')))
            preview=preview_subscription_change(c,ids['platform_admin_user_account'],tenant,3,0)
            return change_subscription(c,ids['platform_admin_user_account'],ids['platform_admin_user_account'],tenant,SubscriptionChange(maximumTier=3,expectedRevision=0,expectedImpactHash=preview['inputHash'],reason='Owned DB race check',confirmChange=True))
    with engine.connect() as held,ThreadPoolExecutor(max_workers=1) as pool:
        transaction=held.begin();lifecycle_lock(held,tenant);owner=held.scalar(text('select pg_backend_pid()'))
        future=pool.submit(change)
        try:
            waiter=channel.get(timeout=5);blocked=False;deadline=monotonic()+8
            while monotonic()<deadline:
                blocked=owner in held.scalar(text('select pg_blocking_pids(:pid)'),dict(pid=waiter))
                if blocked:break
                sleep(.05)
            assert blocked and not future.done()
        finally:transaction.rollback()
        assert future.result(timeout=10)['maximumTier']==3
