"""Explicit, retryable recalculation; never automatic publication."""
from datetime import datetime, timezone
from uuid import UUID
from hashlib import sha256
from sqlalchemy import select, func
from . import tables as t
from .economics import evidence_hash, canonical_payload
from .service import ValuationRequest, ValuationBlocked
from .runner import execute, ValuationInProgress


def recalculate(engine, tenant, actor, batches, reason, key, correlation, *, operator=None, configure_transaction=None):
    identity=dict(actor=str(actor),operator=str(operator or actor),batches=[str(b['batch_id']) for b in batches],reason=reason)
    fingerprint=evidence_hash(identity)
    with engine.begin() as c:
        if configure_transaction: configure_transaction(c)
        lock=int.from_bytes(sha256(f'reassessment:{tenant}:{key}'.encode()).digest()[:8],'big',signed=True)
        c.execute(select(func.pg_advisory_xact_lock(lock)))
        retained=c.execute(select(t.reassessment_request).where(t.reassessment_request.c.tenant_id==tenant,
            t.reassessment_request.c.request_key==key)).mappings().one_or_none()
        if retained and retained['request_hash']!=fingerprint: raise ValueError('Recalculation key reused with different inputs')
        if retained is None:
            retained=c.execute(t.reassessment_request.insert().values(tenant_id=tenant,actor_id=actor,request_key=key,
                request_hash=fingerprint,payload=identity).returning(t.reassessment_request)).mappings().one()
        cutoff=retained['information_cutoff'].astimezone(timezone.utc)
        from security_master_schema.command_audit import retain_command_audit
        retain_command_audit(c, resources=[retained['request_id']], phase='REQUEST_ACCEPTED')
    outcomes=[]
    for base in batches:
        child=sha256(f'{tenant}:{key}:{base["batch_id"]}'.encode()).hexdigest()
        try:
            original=base['summary']['request']
            request=ValuationRequest(tenant_id=tenant,strategy_id=base['strategy_id'],
                policy_id=UUID(original['policy_id']),cut_id=UUID(original['cut_id']),reporting_currency_id=UUID(original['reporting_currency_id']),
                opening_cutoff=datetime.fromisoformat(original['opening_cutoff']),closing_cutoff=datetime.fromisoformat(original['closing_cutoff']),
                information_cutoff=cutoff,daily=original.get('daily',False),predecessor_batch_id=base['batch_id'],recalculation_reason=reason)
            attempt=execute(engine,request,actor,child,correlation,configure_transaction=configure_transaction,real_operator_id=operator)
            with engine.begin() as c:
                if configure_transaction: configure_transaction(c)
                from .storage import batch_view
                new_id=c.scalar(select(t.batch.c.batch_id).where(t.batch.c.attempt_id==attempt).order_by(t.batch.c.created_at.desc()).limit(1))
                if new_id is None:
                    event=c.execute(select(t.run_event.c.details).where(t.run_event.c.attempt_id==attempt,
                        t.run_event.c.details['batchId'].astext.is_not(None)).order_by(t.run_event.c.recorded_at.desc()).limit(1)).scalar_one()
                    new_id=UUID(event['batchId'])
                result=batch_view(c,tenant,new_id)
                from .evidence_access import assert_batch_display
                assert_batch_display(c,tenant,result)
                from security_master_schema import models as m
                currency=c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==UUID(result['summary']['reportingCurrencyId'])))
                outcomes.append(dict(baseBatchId=base['batch_id'],status=result['status'],attemptId=attempt,batchId=new_id,currency=currency,
                    comparison=dict(old=base['summary'],new=result['summary'],
                        ledgerChanges=base.get('sourceHealth',{}).get('changes',[]),
                        note='New information cutoff may change market inputs too. Ad hoc attribution amendments are not automatically reapplied; compare and review them before publication.')))
        except Exception as error:
            with engine.begin() as c:
                if configure_transaction: configure_transaction(c)
                attempt=c.scalar(select(t.attempt.c.attempt_id).where(t.attempt.c.tenant_id==tenant,t.attempt.c.request_key==child))
            expected=isinstance(error,(ValueError,KeyError,ValuationInProgress,PermissionError))
            outcomes.append(dict(baseBatchId=base['batch_id'],status='BLOCKED' if expected else 'FAILED',attemptId=attempt,
                reason=('Current evidence access required' if isinstance(error,PermissionError) else str(error))
                    if expected else 'Calculation failed; inspect its retained operational log.'))
    return canonical_payload(dict(informationCutoff=cutoff,items=outcomes))
