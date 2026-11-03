"""Batch review-decision health, separate from frozen financial evidence."""
from uuid import UUID
from sqlalchemy import select
from . import mark_override_tables as t


def mark_health_statuses(c,headers):
    used=[(header,mark) for header in headers for mark in header['summary'].get('markOverrideInputs',[])]
    if not used:return {}
    # A later approval supersedes earlier values for this exact scope. A later
    # withdrawal never makes an older approved quote current again.
    keys={mark['inputKey'] for _,mark in used};tenants={h['tenant_id'] for h,_ in used}
    rows=c.execute(select(t.request.c.tenant_id,t.request.c.strategy_id,t.request.c.input_key,
        t.decision.c.request_id,t.decision.c.decision_id).join(t.request).where(
            t.request.c.tenant_id.in_(tenants),t.request.c.input_key.in_(keys),t.decision.c.action=='APPROVED')
        .order_by(t.decision.c.recorded_at.desc(),t.decision.c.decision_id.desc())).mappings()
    newest={}
    for row in rows:newest.setdefault((row['tenant_id'],row['strategy_id'],row['input_key']),row)
    ids={UUID(mark['requestId']) for _,mark in used}
    decisions=c.execute(select(t.decision).where(t.decision.c.request_id.in_(ids))
        .order_by(t.decision.c.recorded_at.desc(),t.decision.c.decision_id.desc())).mappings()
    latest={}
    for row in decisions:latest.setdefault(row['request_id'],row)
    result={}
    for header,mark in used:
        current=newest.get((header['tenant_id'],header['strategy_id'],mark['inputKey']))
        last=latest.get(UUID(mark['requestId']))
        if (not current or str(current['decision_id'])!=mark['decisionId'] or not last
            or last['action']!='APPROVED' or str(last['decision_id'])!=mark['decisionId']):
            result[header['batch_id']]='REASSESSMENT_REQUIRED'
    return result
