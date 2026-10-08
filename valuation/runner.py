"""Engine-owned attempt orchestration with rollback-independent diagnostics."""
from time import perf_counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from . import storage as store, tables as t
from .service import calculate,ValuationBlocked


class ValuationInProgress(RuntimeError):
    """A duplicate caller must not fail or restart the active worker's attempt."""

@contextmanager
def calculation_transaction(engine):
    """One stable database snapshot for all economic and selection evidence."""
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
        with c.begin():
            yield c


def recover_attempt(engine, tenant, attempt_id, actor, reason, *, confirmed_worker_stopped=False, configure_transaction=None):
    """Operator recovery, not cancellation: refuses an active worker lock.

    CLI caller confirms the worker stopped and enforces administrator authority.
    Retain the failed attempt; retry with a NEW request key.
    """
    if not isinstance(reason,str) or not reason.strip() or len(reason)>500:
        raise ValueError('Recovery explanation required (1–500 characters)')
    if not confirmed_worker_stopped:
        raise ValueError('Confirm the worker is stopped before recovery')
    from sqlalchemy import func
    with engine.begin() as c:
        if configure_transaction: configure_transaction(c)
        from security_master_schema.tenant_workspace import resolve_tenant_workspace
        workspace=resolve_tenant_workspace(c,tenant,actor,datetime.now(timezone.utc).date())
        if workspace.membership_role!='TENANT_ADMIN' or not {'MARKET_DATA','VALUATION'}.issubset(workspace.module_codes):
            raise PermissionError('Valuation administrator authority required')
        from security_master_schema import models as m
        if c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor))!='ACTIVE':
            raise PermissionError('Active administrator account required')
        if not c.scalar(select(t.attempt.c.attempt_id).where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==tenant)):
            raise LookupError('Attempt not found')
        lock_id=int.from_bytes(attempt_id.bytes[:8],'big',signed=True)
        if not c.scalar(select(func.pg_try_advisory_xact_lock(lock_id))):
            raise ValueError('Attempt has an active calculation worker')
        row=c.execute(select(t.attempt).where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==tenant).with_for_update()).mappings().one_or_none()
        if not row: raise LookupError('Attempt not found')
        if row['status']!='RUNNING': raise ValueError('Only RUNNING attempts can be recovered')
        now=datetime.now(timezone.utc)
        if row['started_at']>now-timedelta(minutes=15): raise ValueError('Attempt is not stale (15 minutes required)')
        if c.scalar(select(t.batch.c.batch_id).where(t.batch.c.attempt_id==attempt_id).limit(1)):
            raise ValueError('Financial batch exists; investigate before recovery')
        c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt_id).values(
            status='FAILED',error_code='INTERRUPTED',completed_at=now))
        store._event(c,attempt_id,'FAILED','RECOVERY',dict(errorCode='INTERRUPTED',actorId=actor,reason=reason.strip()))


def execute(engine, request, actor, key, correlation_id, *, configure_transaction=None):
    attempt_id=store.begin_attempt(engine,request,actor,key,correlation_id,configure_transaction=configure_transaction)
    started=perf_counter()
    owns_attempt=False
    try:
        # Duplicate callers do not wait through the worker's execution: bounded
        # lock waits can time out and must never fail a shared active attempt.
        # Different staging scopes can still cause serialization failures;
        # retry those only, retaining the same key and a fresh input snapshot.
        for retry in range(3):
            try:
                with calculation_transaction(engine) as c:
                    if configure_transaction: configure_transaction(c)
                    lock_id=int.from_bytes(attempt_id.bytes[:8],'big',signed=True)
                    from sqlalchemy import func
                    if not c.scalar(select(func.pg_try_advisory_xact_lock(lock_id))):
                        raise ValuationInProgress(f'Attempt {attempt_id} is already running. Inspect its status or retry the unchanged request with the same key.')
                    owns_attempt=True
                    attempt=c.execute(select(t.attempt).where(t.attempt.c.attempt_id==attempt_id)).mappings().one()
                    if attempt['status']=='FAILED': raise ValuationBlocked('Failed attempt retained; use a new key after correcting inputs')
                    if attempt['status']=='COMPLETED': return attempt_id
                    result=calculate(c,request)
                    calculated_ms=int((perf_counter()-started)*1000)
                    store._event(c,attempt_id,'VALIDATED','CALCULATION',{'elapsedMs':calculated_ms,'lineCount':len(result.period.lines),
                        'scope':'MARKET_ONLY','externalComparison':'NOT_COMPARED','serializationRetries':retry,
                        'method':result.method,'factsScanned':result.projection.facts_scanned,
                        'positionCount':len(result.projection.buckets),'executionCount':len(result.projection.executions),
                        'markRequestCount':result.evidence['requiredMarkCount']})
                    store.stage(c,attempt_id,actor,result)
                return attempt_id
            except DBAPIError as exc:
                if getattr(exc.orig,'sqlstate',None)!='40001': raise
                if retry==2:
                    raise ValuationBlocked('Concurrent input or staging changes prevented a consistent calculation; retry with a new key.') from exc
    except ValuationInProgress:
        raise
    except (ValuationBlocked,ValueError,PermissionError) as exc:
        # Only our deliberately safe domain error is suitable for an Ops log.
        # Database exceptions and arbitrary provider messages never enter it.
        reason=str(exc).replace('\r',' ').replace('\n',' ')[:500] if isinstance(exc,ValuationBlocked) else 'Required calculation scope or inputs are unavailable.'
        if owns_attempt:
            store.fail_attempt(engine,request.tenant_id,attempt_id,'VALUATION_BLOCKED',reason=reason,configure_transaction=configure_transaction)
        raise ValuationBlocked(f'Attempt {attempt_id} blocked. Inspect its operational log and correct the required inputs.') from exc
    except Exception:
        if owns_attempt:
            store.fail_attempt(engine,request.tenant_id,attempt_id,'CALCULATION_FAILED',configure_transaction=configure_transaction)
        raise
