"""Component requests create reviewed candidates, never mutable P&L edits."""
from datetime import datetime,timezone
from decimal import Decimal,localcontext
from uuid import uuid4
from sqlalchemy import select,func
from . import tables as t,storage
from .economics import canonical_payload,evidence_hash,validate_totals,INCOME,COSTS,finite_decimal
from .evidence_access import assert_batch_display


def _base(c,tenant,batch_id):
    header=storage.batch_view(c,tenant,batch_id)
    storage._lock(c,tenant,header['strategy_id'],header['value_date'])
    return storage.batch_view(c,tenant,batch_id)


def request_component_change(c,tenant,base_id,attribution_id,actor,payload,key,*,real_operator_id=None):
    table=t.amendment
    digest=evidence_hash(dict(baseBatchId=base_id,attributionId=attribution_id,actor=actor,payload=payload))
    from apps.reference_api.booking_controls import booking_lock_key
    c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant,'pnl-amendment',key))))
    old=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.submission_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=digest: raise ValueError('Amendment key reused for different inputs')
        from .review_authority import request_operator_lineage
        if (real_operator_id or actor) not in request_operator_lineage(c,tenant,old['request_id']).operators:
            raise ValueError('Amendment request key belongs to a different real operator')
        assert_batch_display(c,tenant,storage.batch_view(c,tenant,old['base_batch_id']))
        return old['request_id']
    base=_base(c,tenant,base_id)
    assert_batch_display(c,tenant,base)
    if base['status']!='STAGED': raise ValueError('Only staged candidates can be amended; recalculate a published result')
    if not any(row['attribution_id']==attribution_id for row in base['items']): raise LookupError('Attribution not selected in candidate')
    component=payload['component'];amount=storage._amount(finite_decimal(payload['amount'],'amendment amount'))
    if component not in (INCOME|COSTS)-{'ACCRUAL','COUPON','CARRY'}:
        raise ValueError('Market/accrual/coupon corrections require source input correction and recalculation')
    if amount==0 or not payload['reason'].strip() or not payload['sourceReference'].strip(): raise ValueError('Nonzero signed amount, reason and source reference required')
    request_id=c.scalar(table.insert().values(tenant_id=tenant,strategy_id=base['strategy_id'],requested_by=actor,
        base_batch_id=base_id,base_attribution_id=attribution_id,population_hash=storage.population_hash(base['items']),
        submission_key=key,request_hash=digest,component=component,amount=amount,reason=payload['reason'],
        source_reference=payload['sourceReference'],status='PENDING').returning(table.c.request_id))
    storage._event(c,base['attempt_id'],'AMENDMENT_REQUESTED','AMENDMENT',
        {'requestId':request_id,'realOperatorId':real_operator_id or actor})
    return request_id


def _request(c,tenant,request_id):
    row=c.execute(select(t.amendment).where(t.amendment.c.request_id==request_id,t.amendment.c.tenant_id==tenant)).mappings().one_or_none()
    if not row: raise LookupError('Amendment request not found')
    base=_base(c,tenant,row['base_batch_id'])
    row=c.execute(select(t.amendment).where(t.amendment.c.request_id==request_id).with_for_update()).mappings().one()
    assert_batch_display(c,tenant,base)
    return row,base


def _decision(c,row,actor,status,comment,batch_id=None):
    if not isinstance(comment,str) or not comment.strip() or len(comment)>2000: raise ValueError('Review explanation required')
    c.execute(t.amendment.update().where(t.amendment.c.request_id==row['request_id'],t.amendment.c.status=='PENDING')
        .values(status=status,reviewed_by=actor,review_comment=comment.strip(),reviewed_at=datetime.now(timezone.utc),applied_batch_id=batch_id))


def approve_component_change(c,tenant,request_id,actor,comment,*,real_operator_id=None):
    row,base=_request(c,tenant,request_id)
    if actor==row['requested_by']: raise ValueError('An independent amendment approver is required')
    from .review_authority import assert_request_independent,batch_operator_lineage,request_operator_lineage
    assert_request_independent(c,tenant,request_id,actor,real_operator_id)
    if not isinstance(comment,str) or not comment.strip() or len(comment)>2000: raise ValueError('Review explanation required')
    if row['status']=='APPLIED': return row['applied_batch_id']
    if row['status']=='STALE': return None
    if row['status']!='PENDING': raise ValueError('Request is no longer pending')
    if (base['status']!='STAGED' or storage.population_hash(base['items'])!=row['population_hash']
        or storage.population_hash(storage.published(c,tenant,base['strategy_id'],base['value_date']))!=base['base_population_hash']):
        _decision(c,row,actor,'STALE',comment)
        return None
    target=next(item for item in base['items'] if item['attribution_id']==row['base_attribution_id'])
    from .accruals import assert_current_accrual_versions
    assert_current_accrual_versions(c,tenant,base['items'])
    if not target['position_key']: raise ValueError('Legacy trade-owned results require recalculation before amendment')
    components={k:Decimal(v) for k,v in target['components'].items()}
    with localcontext() as ctx:
        ctx.prec=512
        components[row['component']]=components.get(row['component'],Decimal(0))+row['amount']
        gross=target['gross_pnl']+(row['amount'] if row['component'] in INCOME else Decimal(0))
        net=target['net_pnl']+row['amount']
    validate_totals(components,market=target['market_pnl'],gross=gross,net=net)
    for amount in (*components.values(),gross,net): storage._amount(amount)
    stamp=datetime.now(timezone.utc)
    audit=dict(requestId=request_id,baseAttributionId=target['attribution_id'],component=row['component'],amount=row['amount'],
        reason=row['reason'],sourceReference=row['source_reference'],requestedBy=row['requested_by'],approvedBy=actor,reviewComment=comment)
    digest=evidence_hash(dict(baseInputHash=base['input_hash'],amendment=audit))
    attempt=c.scalar(t.attempt.insert().values(tenant_id=tenant,strategy_id=base['strategy_id'],initiated_by=row['requested_by'],
        request_key='amendment:'+str(request_id),request_hash=digest,request_payload=base['summary']['request'],
        correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id))
    base_operators=batch_operator_lineage(c,tenant,base['batch_id'])
    requester=request_operator_lineage(c,tenant,request_id)
    storage._event(c,attempt,'STARTED','AMENDMENT',{'requestId':request_id,'baseBatchId':base['batch_id'],
        'contributorOperatorIds':sorted(map(str,base_operators.operators | requester.operators)),
        'operatorLineageComplete':base_operators.complete and requester.complete})
    last=c.scalar(select(func.max(t.attribution.c.version)).where(t.attribution.c.tenant_id==tenant,
        t.attribution.c.strategy_id==base['strategy_id'],t.attribution.c.value_date==base['value_date'],t.attribution.c.position_key==target['position_key']))
    evidence=dict(target['evidence']);identity=dict(evidence['identity'],components=canonical_payload(components),amendment=canonical_payload(audit))
    evidence.update(identity=identity,amendment=canonical_payload(audit))
    values={k:target[k] for k in ('tenant_id','strategy_id','trade_id','position_key','subject_id','value_date','method','currency_id','market_pnl')}
    attribution=c.scalar(t.attribution.insert().values(**values,attempt_id=attempt,version=last+1,
        supersedes_attribution_id=target['attribution_id'],input_hash=evidence_hash(identity),gross_pnl=gross,net_pnl=net,
        components=canonical_payload(components),evidence=evidence).returning(t.attribution.c.attribution_id))
    if target['lineage']:
        c.execute(t.lineage.insert(),[dict(attribution_id=attribution,trade_id=e['trade_id'],event_id=e['event_id'],role=e['role']) for e in target['lineage']])
    summary=dict(base['summary'],inputHash=digest,parentBatchId=str(base['batch_id']),amendmentRequestId=str(request_id))
    with localcontext() as ctx:
        ctx.prec=512
        summary['grossPnl']=canonical_payload(sum((i['gross_pnl'] for i in base['items']),Decimal(0))+(gross-target['gross_pnl']))
        summary['netPnl']=canonical_payload(sum((i['net_pnl'] for i in base['items']),Decimal(0))+row['amount'])
    revised=c.scalar(t.batch.insert().values(tenant_id=tenant,strategy_id=base['strategy_id'],staged_by=row['requested_by'],
        attempt_id=attempt,value_date=base['value_date'],status='STAGED',mode='AUTHORITATIVE',input_hash=digest,
        base_population_hash=base['base_population_hash'],summary=summary).returning(t.batch.c.batch_id))
    for item in base['items']:
        c.execute(t.item.insert().values(tenant_id=tenant,batch_id=revised,attribution_id=attribution if item['attribution_id']==target['attribution_id'] else item['attribution_id'],
            trade_id=item['trade_id'],position_key=item['position_key']))
    c.execute(t.batch.update().where(t.batch.c.batch_id==base['batch_id']).values(status='CANCELLED'))
    c.execute(t.review_event.insert().values(batch_id=base['batch_id'],actor_id=actor,action='CANCELLED',comment='Replaced by approved amendment candidate'))
    c.execute(t.review_event.insert().values(batch_id=revised,actor_id=actor,action='STAGED',comment=comment.strip()))
    _decision(c,row,actor,'APPLIED',comment,revised)
    storage._event(c,attempt,'AMENDMENT_APPROVED','REVIEW',{'requestId':request_id,'batchId':revised,
        'reviewerId':actor,'realOperatorId':real_operator_id or actor})
    for other in c.execute(select(t.amendment).where(t.amendment.c.base_batch_id==base['batch_id'],t.amendment.c.status=='PENDING')).mappings():
        _decision(c,other,actor,'STALE','Base candidate replaced by another approved amendment')
    c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt).values(status='COMPLETED',completed_at=stamp))
    storage._event(c,attempt,'COMPLETED','AMENDMENT',{'batchId':revised,'requestId':request_id})
    return revised


def reject_component_change(c,tenant,request_id,actor,comment,*,real_operator_id=None):
    row,base=_request(c,tenant,request_id)
    if actor==row['requested_by']: raise ValueError('An independent amendment reviewer is required')
    from .review_authority import assert_request_independent
    assert_request_independent(c,tenant,request_id,actor,real_operator_id)
    if row['status']!='PENDING': raise ValueError('Request is no longer pending')
    _decision(c,row,actor,'REJECTED',comment)
    storage._event(c,base['attempt_id'],'AMENDMENT_REJECTED','REVIEW',{'requestId':request_id,
        'reviewerId':actor,'realOperatorId':real_operator_id or actor})
    return row['request_id']
