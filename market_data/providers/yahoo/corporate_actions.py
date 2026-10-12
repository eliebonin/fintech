"""Yahoo event semantics and retained-delivery reassessment; never invent proof.

Source events are ANNOUNCED facts, not reviewed cash flows or executed trades.
Date timestamps identify ex-dates, not intraday entitlement ordering.
"""
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation,localcontext
from hashlib import sha256
import json
from zoneinfo import ZoneInfo
from sqlalchemy import select
from security_master_schema import models as m


def parse_events(result,*,symbol,timezone_name,start,end):
    actions=[];splits=[];dividends=[];rejections=[]
    events=result.get('events',{})
    if not isinstance(events,dict):
        return (),[],[],[{'reason':'Malformed corporate-action collection'}]
    def positive(raw):
        if isinstance(raw,bool): raise ValueError('Boolean economic value')
        value=Decimal(str(raw))
        if not value.is_finite() or not 0<value<Decimal('1e18'): raise ValueError('Invalid economic value')
        return value
    for kind,items in events.items():
        if kind not in ('splits','dividends'):
            rejections.append({'kind':kind,'reason':'Unsupported corporate-action family'});continue
        if not isinstance(items,dict):
            rejections.append({'kind':kind,'reason':'Malformed corporate-action family'});continue
        for key,event in items.items():
            try:
                stamp=event['date']
                if isinstance(stamp,bool) or not isinstance(stamp,int) or str(stamp)!=str(key):
                    raise ValueError('Event identity and timestamp disagree')
                day=datetime.fromtimestamp(stamp,timezone.utc).astimezone(ZoneInfo(timezone_name)).date()
                if not start<=day<=end: raise ValueError('Corporate action outside requested window')
                action=dict(event_reference=f'YAHOO_FINANCE_PERSONAL:{symbol}:{kind}:{key}',date_role='EX',
                    date_value=day,timezone_name=timezone_name,ratio=None,cash_amount=None)
                with localcontext() as ctx:
                    ctx.prec=60
                    if kind=='splits':
                        numerator,denominator=positive(event['numerator']),positive(event['denominator'])
                        if event.get('splitRatio'):
                            a,b=event['splitRatio'].split(':')
                            if positive(a)*denominator!=positive(b)*numerator:
                                raise ValueError('Split ratio fields disagree')
                        ratio=numerator/denominator
                        if not 0<ratio<Decimal('1e18'): raise ValueError('Split ratio exceeds storage bounds')
                        ratio=ratio.quantize(Decimal('0.000000000001'))
                        if ratio<=0: raise ValueError('Split ratio below storage precision')
                        action.update(event_type='STOCK_SPLIT',ratio=ratio)
                        splits.append(dict(date=day.isoformat(),numerator=str(numerator),denominator=str(denominator)))
                    else:
                        amount=positive(event['amount']).quantize(Decimal('0.000000000001'))
                        if amount<=0: raise ValueError('Dividend below storage precision')
                        action.update(event_type='CASH_DIVIDEND',cash_amount=amount)
                        dividends.append(dict(date=day.isoformat(),amount=str(amount)))
                actions.append(action)
            except (KeyError,TypeError,ValueError,InvalidOperation,OverflowError,OSError) as exc:
                rejections.append(dict(kind=kind,eventKey=str(key),reason=str(exc)))
    return tuple(actions),sorted(splits,key=lambda e:e['date']),sorted(dividends,key=lambda e:e['date']),rejections


def backfill_retained_actions(c,dataset_id,tenant_id,actor_id,*,symbols=None):
    """Caller owns commit; assess stored Yahoo equity deliveries with durable jobs.

No network, new price/vintage, original-payload rewrite or automatic proof creation.
"""
    from market_data.history import require_admin
    from market_data.rights import load_rights
    from market_data import storage
    from market_data.corporate_actions import publish_actions
    from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job
    from .adapter import parse_delivery
    from market_data.contracts import ListingContext
    require_admin(c,tenant_id,actor_id)
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id)).mappings().one()
    if profile['usage_scope']!='PERSONAL' or profile['permitted_tenant_id']!=tenant_id:
        raise PermissionError('Only the owning personal dataset can be reassessed')
    namespace=profile['external_id_namespace_id']
    dataset,_=storage.lock_dataset(c,dataset_id,namespace)
    decision=load_rights(c,dataset_id,'STORE',date.today(),'PERSONAL')
    if not decision.allowed: raise PermissionError('Current STORE rights required')
    source=m.source_payload
    runs=c.execute(select(m.market_data_ingestion_run).join(source).where(
        m.market_data_ingestion_run.c.dataset_id==dataset_id,source.c.processing_status=='VALIDATED')
        .order_by(m.market_data_ingestion_run.c.received_at_utc,m.market_data_ingestion_run.c.run_id)).mappings().all()
    runs=[r for r in runs if r['report'].get('request',{}).get('namespaceId')==str(namespace)
        and (not symbols or r['report']['request']['symbol'] in symbols)]
    if not runs: raise ValueError('No validated retained equity deliveries in requested scope')
    selection=sorted({r['report']['request']['symbol'] for r in runs})
    start=min(date.fromisoformat(r['report']['request']['start']) for r in runs)
    end=max(date.fromisoformat(r['report']['request']['end']) for r in runs)
    job=start_job(c,dataset_id,namespace,tenant_id,actor_id,selection,start,end)
    totals=dict(jobId=str(job),deliveries=len(runs),symbols=len(selection),inserted=0,duplicates=0,revised=0,rejectedEvents=0,
        failedDeliveries=0,normalizationProofsCreated=0,assessments=[])
    symbol_outcomes={symbol:[] for symbol in selection}
    for run in runs:
        request=run['report']['request'];symbol=request['symbol']
        begin,finish=date.fromisoformat(request['start']),date.fromisoformat(request['end'])
        attempt=start_attempt(c,job,symbol,begin,finish)
        report=dict(sourceRunId=str(run['run_id']),sourcePayloadId=str(run['source_payload_id']),symbol=symbol,
            requestedStart=begin.isoformat(),requestedEnd=finish.isoformat(),priceBasisReady=False,
            assessedAtUtc=datetime.now(timezone.utc).isoformat(),storeRightsEvidence=decision.evidence,
            dividendAmountBasis='PROVIDER_REPORTED_UNASSESSED',financialFlowsCreated=False)
        try:
            with c.begin_nested():
                if sha256(run['raw_payload'].encode()).hexdigest()!=run['content_sha256']:
                    raise ValueError('Retained payload hash mismatch')
                _,listing=storage.resolve_listing(c,namespace_id=namespace,symbol=symbol,
                    received_at=run['received_at_utc'],permitted_tenant_id=tenant_id)
                parsed=parse_delivery(json.loads(run['raw_payload']),symbol=symbol,
                    listing=ListingContext(listing['currency_code'],listing['mic'],listing['timezone_name']),
                    start=begin,end=finish,received_at=run['received_at_utc'])
                stats=publish_actions(c,parsed.corporate_actions,listing=listing,source_payload_id=run['source_payload_id'])
                report.update(stats,adjustmentEvidence=parsed.adjustment_evidence)
            for key in ('inserted','duplicates','revised'): totals[key]+=stats[key]
            rejected=len(parsed.adjustment_evidence['eventRejections'])+stats['reviewRequired']
            totals['rejectedEvents']+=rejected
            outcome='PARTIAL' if rejected else 'COMPLETE'
            finish_attempt(c,attempt,outcome,report,run['run_id'])
        except (ValueError,TypeError,KeyError) as exc:
            totals['failedDeliveries']+=1;report['reason']=str(exc)
            outcome='FAILED';finish_attempt(c,attempt,outcome,report,run['run_id'])
        symbol_outcomes[symbol].append(outcome)
        # The complete per-delivery evidence is in ingestion attempts; summaries
        # retain counts, not a second copy of all source events.
        totals['assessments'].append({k:v for k,v in report.items() if k!='adjustmentEvidence'})
    # Ordinary price ingestion reports the latest attempt for each symbol. This
    # reassessment covers every retained vintage, so earlier warnings still count.
    for symbol,outcomes in symbol_outcomes.items():
        if any(state!='COMPLETE' for state in outcomes):
            attempt=start_attempt(c,job,symbol,start,end)
            finish_attempt(c,attempt,'FAILED' if all(state=='FAILED' for state in outcomes) else 'PARTIAL',
                dict(assessmentSummary=True,retainedDeliveryOutcomes=outcomes))
    totals['status']=finish_job(c,job,{k:v for k,v in totals.items() if k!='assessments'})
    return totals
