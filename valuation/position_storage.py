"""Immutable position result versions and original ledger links, no fake trades."""
from dataclasses import asdict
from decimal import Decimal
from sqlalchemy import select
from positions.reconstruction import key_identity
from . import tables as t
from .economics import canonical_payload,evidence_hash

def stage_line(c,attempt_id,calculation,line,*,facts,selections):
    from .storage import selection_identity
    r=calculation.request; bucket=line.bucket; key=key_identity(bucket.key)
    identity=dict(method=calculation.method,bucket=asdict(bucket),components=line.attribution.components(),
        openingValue=line.attribution.opening_value,closingValue=line.attribution.closing_value,executionValue=line.execution_value,
        openingCutoff=r.opening_cutoff,closingCutoff=r.closing_cutoff,policyId=r.policy_id,
        reportingCurrency=r.reporting_currency_id,facts=[asdict(f) for f in facts],
        selections=[selection_identity(s) for s in selections])
    digest=evidence_hash(identity)
    prior=c.execute(select(t.attribution).where(t.attribution.c.tenant_id==r.tenant_id,
        t.attribution.c.strategy_id==r.strategy_id,t.attribution.c.value_date==r.closing_cutoff.date(),
        t.attribution.c.position_key==key).order_by(t.attribution.c.version.desc()).limit(1)).mappings().one_or_none()
    if prior and prior['input_hash']==digest: return key,prior['attribution_id']
    evidence=canonical_payload(dict(identity=identity,resultFormat='POSITION_V2',informationCutoff=r.information_cutoff,
        scope=calculation.scope,selections=selections,resolutionSnapshotIds=calculation.resolution_snapshot_ids,
        noMarketMarksRequired=bucket.opening_quantity==0 and bucket.closing_quantity==0))
    attribution=c.execute(t.attribution.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,
        attempt_id=attempt_id,position_key=key,subject_id=bucket.key.subject_id,value_date=r.closing_cutoff.date(),
        version=prior['version']+1 if prior else 1,supersedes_attribution_id=prior['attribution_id'] if prior else None,
        method=calculation.method,input_hash=digest,currency_id=r.reporting_currency_id,
        market_pnl=line.attribution.market_pnl,gross_pnl=line.attribution.market_pnl,net_pnl=line.attribution.market_pnl,
        components=canonical_payload(line.attribution.components()),evidence=evidence).returning(t.attribution.c.attribution_id)).scalar_one()
    if facts:
        c.execute(t.lineage.insert(),[dict(attribution_id=attribution,trade_id=f.trade_id,event_id=f.event_id,
            role=('PERIOD_EXECUTION' if f.kind=='BOOKED' and f.effective_at>r.opening_cutoff else
                  'OPENING_EVIDENCE' if f.kind=='BOOKED' else 'LIFECYCLE_EVIDENCE')) for f in facts])
    return key,attribution

def valid_empty_summary(summary):
    """Only positively evidenced v2 zero populations bypass missing-source denial."""
    try:
        p=summary['positionEvidence']
        return (summary['resultFormat']=='POSITION_V2' and p['engine']=='position-reconstruction-v1'
            and p['completeKnowledge'] is True and len(p['inputHash'])==64
            and p['bucketCount']==p['executionCount']==p['requiredMarkCount']==0
            and all(Decimal(summary[k])==0 for k in ('marketPnl','openingValue','closingValue','executionValue')))
    except (KeyError,TypeError,ArithmeticError): return False
