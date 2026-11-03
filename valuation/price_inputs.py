"""Explicit missing-price exceptions and retained partial-population proof.

Only absence/staleness can be softened. This module never repairs permissions,
bad economic conventions, missing calendars or unsupported price-unit evidence.
"""
from dataclasses import asdict,replace
from sqlalchemy import select
from security_master_schema import models as m
from positions.reconstruction import key_identity
from .economics import canonical_payload,evidence_hash

SOFT_MISSING=frozenset({'NO_ELIGIBLE_OBSERVATION','NO_OBSERVATIONS','MAX_STALENESS_EXCEEDED'})


def may_continue(action,code):
    return action in {'WARN','MANUAL_OVERRIDE'} and code in SOFT_MISSING


class MissingPriceInput(Exception):
    """A known eligible policy explicitly permits a retained missing input."""
    def __init__(self,request,selection,action):
        self.request=request;self.selection=selection;self.action=action
        super().__init__(selection.exception_code or selection.status)


def resolve_input(c,request,resolver,*,allow_partial=True):
    selected=resolver(c,request)
    if selected.status!='SELECTED' and selected.policy_rule_id:
        action=c.scalar(select(m.valuation_policy_rule.c.missing_data_action).where(
            m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id))
        if may_continue(action,selected.exception_code):
            from .mark_overrides import approved_mark
            approved=approved_mark(c,request,selected)
            if approved is not None:return approved
            if allow_partial:raise MissingPriceInput(request,selected,action)
    return selected


def gap_identity(request,selection):
    values=asdict(request);values.pop('market_data_as_of_utc')
    return dict(request=values,policyRuleId=selection.policy_rule_id,
        pricingDate=selection.pricing_date_requested,pricingTarget=(selection.pricing_evidence or {}).get('pricingTargetUtc'))


def retain_gap(gaps,missing,position_keys,*,role='PRICE'):
    identity=gap_identity(missing.request,missing.selection);key=evidence_hash(identity)
    gap=gaps.setdefault(key,canonical_payload(dict(inputKey=key,identity=identity,
        request=asdict(missing.request),selection=asdict(missing.selection),
        action=missing.action,role=role,positionKeys=[])))
    gap['positionKeys']=sorted(set(gap['positionKeys'])|set(position_keys))
    return gap


def priced_projection(projection,unpriced_keys):
    allowed={b.key for b in projection.buckets if key_identity(b.key) not in unpriced_keys}
    return replace(projection,buckets=tuple(b for b in projection.buckets if b.key in allowed),
        executions=tuple(e for e in projection.executions if e.key in allowed),
        exposures=tuple(e for e in projection.exposures if e.key in allowed))


def price_coverage(projection,gaps,selections):
    unpriced={key for gap in gaps.values() for key in gap['positionKeys']}
    rows=[]
    for bucket in projection.buckets:
        key=key_identity(bucket.key)
        if key not in unpriced:continue
        facts=[asdict(f) for f in projection.facts if f.trade_id in bucket.trade_ids]
        picked=[s for s in selections if str(s.get('valuation_position_subject_id',s.get('subject_reference_node_id')))==str(bucket.key.subject_id)]
        rows.append(canonical_payload(dict(positionKey=key,subjectId=bucket.key.subject_id,
            currencyId=bucket.key.currency_id,product=bucket.key.product_basis,bucket=asdict(bucket),facts=facts,
            inputKeys=[k for k,g in gaps.items() if key in g['positionKeys']],selections=picked,
            status='UNPRICED',pnl=None,contribution='EXCLUDED_FROM_PRICED_POSITION_SUBTOTAL')))
    return canonical_payload(dict(status='INCOMPLETE' if gaps else 'COMPLETE',missingCount=len(gaps),
        affectedPositionCount=len(rows),positionCount=len(projection.buckets),
        pricedPositionCount=len(projection.buckets)-len(rows),gaps=list(gaps.values()),unpricedPositions=rows))


def assert_complete_prices(summary):
    coverage=summary.get('inputCoverage') or {}
    if summary.get('requiredInputsComplete') is False or coverage.get('missingCount') or coverage.get('unpricedPositions'):
        raise ValueError('Supply missing required price marks or reviewed manual marks and recalculate before publication')


def valid_partial_summary(summary):
    try:
        proof=summary['positionEvidence'];coverage=summary['inputCoverage']
        return (summary['requiredInputsComplete'] is False and summary['resultFormat']=='POSITION_V2'
            and proof['completeKnowledge'] is True and len(proof['inputHash'])==64
            and coverage['missingCount']==len(coverage['gaps'])>0
            and coverage['affectedPositionCount']==len(coverage['unpricedPositions'])
            and (coverage['unpricedPositions'] or coverage.get('unpricedCashAccounts'))
            and all(row['status']=='UNPRICED' and row['pnl'] is None and row['facts'] and row['inputKeys'] for row in coverage['unpricedPositions'])
            and all(row['status']=='UNPRICED' and row['pnl'] is None and row['snapshots'] and row['inputKeys'] for row in coverage.get('unpricedCashAccounts',[])))
    except (KeyError,TypeError,ValueError):return False
