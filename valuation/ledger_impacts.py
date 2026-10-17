"""Current source health is separate from immutable financial publication."""
from datetime import datetime
from sqlalchemy import select, func
from security_master_schema import models as m
from . import tables as t


def capture_ledger_state(c, request):
    # Shared strategy row serialization covers every DB writer through triggers;
    # NO KEY UPDATE permits FK checks used by independently retained run logs.
    owner=c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_id==request.strategy_id,
        m.strategy.c.tenant_id==request.tenant_id).with_for_update(key_share=True))
    if owner is None: raise PermissionError('Strategy unavailable')
    revision=c.scalar(select(func.max(t.ledger_change.c.revision)).where(
        t.ledger_change.c.tenant_id==request.tenant_id,t.ledger_change.c.strategy_id==request.strategy_id,
        t.ledger_change.c.recorded_at<=request.information_cutoff)) or 0
    return {'version':1,'revision':revision,'informationCutoff':request.information_cutoff.isoformat()}


def _source_state(header):
    state=header['summary'].get('ledgerSource')
    if not state: return None
    try:
        if state.get('version')!=1 or type(state['revision']) is not int or state['revision']<0: raise ValueError()
        info=datetime.fromisoformat(state['informationCutoff'])
        if info.tzinfo is None: raise ValueError()
    except (KeyError,TypeError,ValueError,AttributeError):
        return None
    return state['revision'],info


def source_health_statuses(c, headers):
    """One indexed EXISTS per frozen header in one SQL round trip.

    History needs the status, not up to 100 complete change records per batch.
    Detail/publication retain source_health and its full diagnostics.
    """
    from sqlalchemy import values,column
    statuses={header['batch_id']:'UNKNOWN_LEGACY' for header in headers}
    rows=[]
    for header in headers:
        state=_source_state(header)
        if state is not None:
            rows.append((header['batch_id'],header['tenant_id'],header['strategy_id'],header['value_date'],*state))
    if not rows: return statuses
    frozen=values(column('batch_id',t.batch.c.batch_id.type),column('tenant_id',t.batch.c.tenant_id.type),
        column('strategy_id',t.batch.c.strategy_id.type),column('value_date',t.batch.c.value_date.type),
        column('revision',t.ledger_change.c.revision.type),column('information_cutoff',t.ledger_change.c.recorded_at.type)
        ).data(rows).cte('history_frozen_ledger')
    changed=select(1).where(t.ledger_change.c.tenant_id==frozen.c.tenant_id,
        t.ledger_change.c.strategy_id==frozen.c.strategy_id,t.ledger_change.c.economic_from<=frozen.c.value_date,
        (t.ledger_change.c.revision>frozen.c.revision)|(t.ledger_change.c.recorded_at>frozen.c.information_cutoff)).exists()
    for identity,stale in c.execute(select(frozen.c.batch_id,changed)):
        statuses[identity]='REASSESSMENT_REQUIRED' if stale else 'CURRENT'
    return statuses


def source_health(c, header):
    state=_source_state(header)
    if state is None: return {'status':'UNKNOWN_LEGACY','changes':[]}
    revision,info=state
    changes=c.execute(select(t.ledger_change).where(t.ledger_change.c.tenant_id==header['tenant_id'],
        t.ledger_change.c.strategy_id==header['strategy_id'],t.ledger_change.c.economic_from<=header['value_date'],
        (t.ledger_change.c.revision>revision) | (t.ledger_change.c.recorded_at>info))
        .order_by(t.ledger_change.c.revision).limit(100)).mappings().all()
    return {'status':'REASSESSMENT_REQUIRED' if changes else 'CURRENT',
        'changes':[{'revision':r['revision'],'tradeId':str(r['trade_id']),'economicFrom':r['economic_from'].isoformat(),
            'recordedAt':r['recorded_at'].isoformat(),'reason':r['reason']} for r in changes],
        'changesTruncated':len(changes)==100}


def batch_source_health(c, tenant_id, batch_id):
    row=c.execute(select(t.batch).where(t.batch.c.tenant_id==tenant_id,t.batch.c.batch_id==batch_id)).mappings().one_or_none()
    if row is None: raise LookupError('Review batch not found')
    return source_health(c,row)


def assert_batch_ledger_current(c, tenant_id, batch_id):
    if batch_source_health(c,tenant_id,batch_id)['status']!='CURRENT':
        raise ValueError('Ledger inputs changed or lack revision proof; recalculate before publication')
