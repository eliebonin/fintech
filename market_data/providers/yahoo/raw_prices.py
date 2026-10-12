"""Reconstruct as-traded closes; original Yahoo values and vintages stay immutable.

Operational convention v1: Yahoo Close includes splits through the snapshot's
latest regular-market date. This is an explicit provider-method assumption, not
a claim that Yahoo publishes a certified adjustment anchor. Assess every date
from the requested history through that reference date using retained responses.
"""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from zoneinfo import ZoneInfo
from sqlalchemy import select, exists, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from security_master_schema import models as m
from market_data.contracts import ListingContext
from market_data.price_basis import normalise_as_traded
from market_data.storage import insert_returning
from valuation.economics import evidence_hash
from .adapter import parse_delivery

METHOD = 'YAHOO_SPLIT_TO_AS_TRADED_V1'


def assess_basis(run, windows, listing):
    request=run['report']['request'];symbol=request['symbol']
    start=date.fromisoformat(request['start'])
    receipt=run['received_at_utc']
    if receipt.utcoffset() is None: raise ValueError('Receipt requires timezone')
    payload=json.loads(run['raw_payload'])
    # Reuse the identity/shape checks, rather than certify an unvalidated ticker.
    parse_delivery(payload,symbol=symbol,listing=listing,start=start,
        end=date.fromisoformat(request['end']),received_at=receipt)
    stamp=payload['chart']['result'][0]['meta'].get('regularMarketTime')
    if isinstance(stamp,bool) or not isinstance(stamp,int):
        raise ValueError('ADJUSTMENT_REFERENCE_DATE_MISSING')
    try: instant=datetime.fromtimestamp(stamp,timezone.utc)
    except (OverflowError,OSError,ValueError) as exc:
        raise ValueError('INVALID_ADJUSTMENT_REFERENCE_DATE') from exc
    anchor=instant.astimezone(ZoneInfo(listing.timezone_name)).date()
    if instant>receipt or anchor<start:
        raise ValueError('INVALID_ADJUSTMENT_REFERENCE_DATE')
    chosen={};sources={}
    for item in sorted(windows,key=lambda r:(r['received_at_utc'],str(r['run_id']))):
        req=item['report']['request']
        if req['symbol']!=symbol: continue
        begin,end=date.fromisoformat(req['start']),date.fromisoformat(req['end'])
        if end<start or begin>anchor: continue
        parsed=parse_delivery(json.loads(item['raw_payload']),symbol=symbol,listing=listing,
            start=begin,end=end,received_at=item['received_at_utc'])
        # Dividend defects do not change a split-only factor. Malformed split or
        # event collections cannot establish coverage, even if prices are valid.
        if any(r.get('kind') in (None,'splits') for r in parsed.adjustment_evidence['eventRejections']):
            continue
        splits={e['date']:e for e in parsed.adjustment_evidence['splits']}
        identity=str(item['source_payload_id'])
        sources[identity]=dict(sourcePayloadId=identity,sourceRunId=str(item['run_id']),
            contentSha256=sha256(item['raw_payload'].encode()).hexdigest(),
            receivedAtUtc=item['received_at_utc'].isoformat(),start=begin.isoformat(),end=end.isoformat())
        day=max(start,begin)
        while day<=min(anchor,end):
            chosen[day]=(identity,splits.get(day.isoformat()))
            day+=timedelta(days=1)
    cursor=start;missing=[]
    while cursor<=anchor:
        if cursor not in chosen: missing.append(cursor.isoformat())
        cursor+=timedelta(days=1)
    if missing: raise ValueError('SPLIT_COVERAGE_GAP: '+','.join(missing))
    used={identity for identity,event in chosen.values()}
    return dict(method='SPLIT_ONLY',complete=True,anchorDate=anchor.isoformat(),
        coverageStart=start.isoformat(),coverageEnd=anchor.isoformat(),
        sourceReference='Yahoo chart retained coverage / '+METHOD,
        providerConvention=METHOD,anchorConvention='SNAPSHOT_LATEST_REGULAR_MARKET_DATE',
        anchorTimestampUtc=instant.isoformat(),priceSourcePayloadId=str(run['source_payload_id']),
        coverageSources=[sources[key] for key in sorted(used)],
        splits=[event for day,(identity,event) in sorted(chosen.items()) if event])


def _raw_series(c, source):
    dimension=m.market_data_series_dimension
    sid=c.scalar(select(dimension.c.market_data_series_id).join(m.market_data_series).where(
        m.market_data_series.c.default_dataset_id==source['default_dataset_id'],
        dimension.c.dimension_code=='NORMALIZED_FROM_SERIES',
        dimension.c.dimension_value==str(source['market_data_series_id'])))
    if sid: return sid
    fields=('reference_node_id','series_type','closing_method','value_type','measure_definition_id',
        'currency_id','default_dataset_id','valuation_cut_id','expected_frequency_code',
        'expected_market_calendar_id','source_system_id','is_official')
    sid=insert_returning(c,m.market_data_series,'market_data_series_id',**{k:source[k] for k in fields})
    for code,value in [('SOURCE_FIELD','DERIVED_RAW_CLOSE'),('VALUE_BASIS','RAW'),
            ('TIMESTAMP_SEMANTICS','PROVIDER_DAILY_BAR_TIMESTAMP'),('NORMALIZATION_METHOD',METHOD),
            ('NORMALIZED_FROM_SERIES',str(source['market_data_series_id']))]:
        c.execute(dimension.insert().values(market_data_series_id=sid,dimension_code=code,dimension_value=value))
    # Same dataset and exact coverage classification: normalization grants no rights.
    for row in c.execute(select(m.market_data_series_coverage).where(
            m.market_data_series_coverage.c.market_data_series_id==source['market_data_series_id'])).mappings():
        c.execute(m.market_data_series_coverage.insert().values(dataset_id=row['dataset_id'],
            market_data_series_id=sid,coverage_package_id=row['coverage_package_id']))
    return sid


def _publish(c,run,assessment,recorded):
    obs=m.market_data_observation;newer=obs.alias('newer_yahoo_raw_source')
    source_rows=c.execute(select(obs).join(m.market_data_series).where(
        obs.c.dataset_id==run['dataset_id'],obs.c.source_payload_id==run['source_payload_id'],
        obs.c.value_basis=='SPLIT_ADJUSTED',obs.c.quality_status=='ACCEPTED',
        m.market_data_series.c.series_type=='CLOSE',
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id==obs.c.market_data_observation_id,
            newer.c.quality_status=='ACCEPTED')))).mappings().all()
    if not source_rows: return dict(rawCreated=0,duplicates=0,sourceProofs=0)
    source=c.execute(select(m.market_data_series).where(
        m.market_data_series.c.market_data_series_id==source_rows[0]['market_data_series_id'])).mappings().one()
    sid=_raw_series(c,source)
    current={row['market_date']:row for row in c.execute(select(obs).where(
        obs.c.market_data_series_id==sid,obs.c.quality_status=='ACCEPTED',
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id==obs.c.market_data_observation_id,
            newer.c.quality_status=='ACCEPTED')))).mappings()}
    normalization_digest=evidence_hash(assessment)
    key='yahoo-raw-v1:'+str(run['run_id'])+':'+normalization_digest[:24]
    vintage=c.scalar(select(m.market_data_vintage.c.market_data_vintage_id).where(
        m.market_data_vintage.c.dataset_id==run['dataset_id'],m.market_data_vintage.c.source_vintage_key==key))
    if vintage and all((prior:=current.get(row['market_date'])) is not None
            and prior['market_data_vintage_id']==vintage for row in source_rows):
        # This exact assessed vintage and its proofs were published atomically.
        # Daily updates must not repeatedly attempt every historical proof insert.
        return dict(rawCreated=0,duplicates=len(source_rows),sourceProofs=len(source_rows))
    provider=c.scalar(select(m.market_data_vintage.c.data_provider_id).where(
        m.market_data_vintage.c.market_data_vintage_id==source_rows[0]['market_data_vintage_id']))
    if not vintage:
        vintage=insert_returning(c,m.market_data_vintage,'market_data_vintage_id',dataset_id=run['dataset_id'],
            data_provider_id=provider,source_vintage_key=key,received_at_utc=recorded,value_basis='RAW',
            content_hash=normalization_digest,source_payload_id=run['source_payload_id'])
    pending=[];proofs=[];duplicates=0
    identifiers=iter(c.scalars(select(func.uuidv7()).select_from(func.generate_series(1,len(source_rows)))))
    for row in source_rows:
        proof=dict(assessment,marketDate=row['market_date'].isoformat(),
            sourceObservationId=str(row['market_data_observation_id']))
        normalized=normalise_as_traded(row['value'],'SPLIT_ADJUSTED',proof,allow_split_conversion=True)
        proofs.append(dict(observation_id=row['market_data_observation_id'],proof_json=proof,
            proof_hash=evidence_hash(proof),recorded_at_utc=recorded))
        previous=current.get(row['market_date'])
        if previous and previous['value']==normalized.valuation_value:
            duplicates+=1;continue
        # Only current source observations are processed; publication is serialized
        # by the dataset lock. A re-run cannot restore superseded source vintages.
        oid=next(identifiers)
        values={k:row[k] for k in ('dataset_id','acquisition_licence_id','source_payload_id','market_date',
            'valuation_cut_id','observed_at_utc','source_timestamp_utc','source_published_at_utc')}
        values.update(market_data_observation_id=oid,market_data_series_id=sid,market_data_vintage_id=vintage,
            received_at_utc=recorded,value=normalized.valuation_value,value_basis='RAW',quality_status='ACCEPTED',
            source_observation_key='RAW:'+row['source_observation_key'],
            supersedes_observation_id=previous['market_data_observation_id'] if previous else None)
        pending.append(values)
        raw_proof=dict(normalized.evidence,method='DERIVED_SPLIT_ONLY',derivedObservationId=str(oid))
        proofs.append(dict(observation_id=oid,proof_json=raw_proof,proof_hash=evidence_hash(raw_proof),recorded_at_utc=recorded))
    for offset in range(0,len(pending),500): c.execute(obs.insert(),pending[offset:offset+500])
    for offset in range(0,len(proofs),500):
        c.execute(pg_insert(m.market_data_price_basis_proof).values(proofs[offset:offset+500])
            .on_conflict_do_nothing(constraint='uq_price_basis_proof_content'))
    return dict(rawCreated=len(pending),duplicates=duplicates,sourceProofs=len(source_rows))


def normalize_dataset(c,dataset_id,tenant_id,actor_id,*,symbols=None,on_symbol=None):
    """No HTTP. Caller owns commit; append derived RAW, proofs and job evidence."""
    from market_data.history import require_admin
    from market_data.rights import load_rights
    from market_data import storage
    from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job
    require_admin(c,tenant_id,actor_id)
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id)).mappings().one()
    if profile['usage_scope']!='PERSONAL' or profile['permitted_tenant_id']!=tenant_id:
        raise PermissionError('Owning personal dataset administrator required')
    namespace=profile['external_id_namespace_id']
    storage.lock_dataset(c,dataset_id,namespace)
    rights=load_rights(c,dataset_id,'STORE',date.today(),'PERSONAL')
    if not rights.allowed: raise PermissionError('Current STORE rights required')
    runs=c.execute(select(m.market_data_ingestion_run).join(m.source_payload).where(
        m.market_data_ingestion_run.c.dataset_id==dataset_id,m.source_payload.c.processing_status=='VALIDATED')
        .order_by(m.market_data_ingestion_run.c.received_at_utc,m.market_data_ingestion_run.c.run_id)).mappings().all()
    runs=[r for r in runs if r['report']['request'].get('namespaceId')==str(namespace)
        and (not symbols or r['report']['request']['symbol'] in symbols)]
    if not runs: raise ValueError('No validated retained deliveries in requested scope')
    for run in runs:
        if sha256(run['raw_payload'].encode()).hexdigest()!=run['content_sha256']:
            raise ValueError('Retained source integrity mismatch')
    chosen=sorted({r['report']['request']['symbol'] for r in runs})
    start=min(date.fromisoformat(r['report']['request']['start']) for r in runs)
    end=max(date.fromisoformat(r['report']['request']['end']) for r in runs)
    job=start_job(c,dataset_id,namespace,tenant_id,actor_id,chosen,start,end)
    summary=dict(jobId=str(job),rawCreated=0,duplicates=0,sourceProofs=0,blocked=0,symbols=len(chosen),failures=[])
    recorded=datetime.now(timezone.utc)
    for symbol in chosen:
        selected=[r for r in runs if r['report']['request']['symbol']==symbol]
        attempt=start_attempt(c,job,symbol,start,end)
        problems=[];totals=dict(rawCreated=0,duplicates=0,sourceProofs=0)
        for run in selected:
            if run['report'].get('eventCoverageOnly'): continue
            try:
                with c.begin_nested():
                    _,listing=storage.resolve_listing(c,namespace_id=namespace,symbol=symbol,
                        received_at=run['received_at_utc'],permitted_tenant_id=tenant_id)
                    context=ListingContext(listing['currency_code'],listing['mic'],listing['timezone_name'])
                    basis=assess_basis(run,selected,context)
                    stats=_publish(c,run,basis,recorded)
                for key,value in stats.items(): totals[key]+=value
            except ValueError as exc:
                problems.append(dict(sourceRunId=str(run['run_id']),symbol=symbol,reason=str(exc)))
        for key,value in totals.items(): summary[key]+=value
        summary['blocked']+=len(problems);summary['failures'].extend(problems)
        finish_attempt(c,attempt,'PARTIAL' if problems and totals['sourceProofs'] else 'BLOCKED' if problems else 'COMPLETE',
            dict(**totals,failures=problems,normalizationMethod=METHOD,storeRightsEvidence=rights.evidence,
                assessedAtUtc=recorded.isoformat()))
        if on_symbol: on_symbol(dict(symbol=symbol,**totals,blocked=len(problems)))
    summary['status']=finish_job(c,job,summary)
    return summary


def retain_event_coverage(c,*,dataset_id,namespace_id,symbol,raw_payload,start,end,received_at):
    """Retain a validated suffix for split coverage; never publish its price bars."""
    from market_data import storage
    from market_data.rights import load_rights
    from market_data.corporate_actions import publish_actions
    dataset,profile=storage.lock_dataset(c,dataset_id,namespace_id)
    evidence=[]
    for activity in ('ACQUIRE','STORE'):
        rights=load_rights(c,dataset_id,activity,received_at.date(),'PERSONAL')
        if not rights.allowed: raise PermissionError(activity+': '+rights.reason)
        evidence.extend(rights.evidence)
    if profile['usage_scope']!='PERSONAL': raise PermissionError('Personal dataset required')
    from .adapter import MAX_BYTES
    if (received_at.utcoffset() is None or end<start or (end-start).days+1>1830
            or end>received_at.date() or len(raw_payload.encode())>MAX_BYTES):
        raise ValueError('Invalid event coverage window/payload/receipt')
    _,listing=storage.resolve_listing(c,namespace_id=namespace_id,symbol=symbol,
        received_at=received_at,permitted_tenant_id=profile['permitted_tenant_id'])
    parsed=parse_delivery(json.loads(raw_payload),symbol=symbol,
        listing=ListingContext(listing['currency_code'],listing['mic'],listing['timezone_name']),
        start=start,end=end,received_at=received_at)
    if any(r.get('kind') in (None,'splits') for r in parsed.adjustment_evidence['eventRejections']):
        raise ValueError('Invalid split-event coverage')
    digest=sha256(raw_payload.encode()).hexdigest()
    key=f'{symbol}:split-coverage:{start}:{end}:{digest}'
    previous=storage.previous_delivery(c,dataset_id,key)
    if previous: return dict(previous['report'],replayed=True)
    run,payload=storage.retain_payload(c,namespace_id=namespace_id,profile=profile,
        delivery_key=key,digest=digest,received_at=received_at)
    report=dict(accepted=0,duplicates=0,rejected=0,rejections=[],eventCoverageOnly=True,
        sourcePayloadId=str(payload),request=dict(namespaceId=str(namespace_id),symbol=symbol,start=str(start),end=str(end)),
        adjustmentEvidence=parsed.adjustment_evidence,
        corporateActions=publish_actions(c,parsed.corporate_actions,listing=listing,source_payload_id=payload))
    storage.finish_delivery(c,run_id=run,dataset_id=dataset_id,source_payload_id=payload,delivery_key=key,
        digest=digest,raw_payload=raw_payload,received_at=received_at,evidence=evidence,report=report)
    return report
