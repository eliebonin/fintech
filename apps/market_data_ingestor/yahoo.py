"""Local personal-project Yahoo onboarding and bounded, auditable EOD import."""
import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import time
from uuid import UUID

import httpx
from sqlalchemy import create_engine, select, or_, func, exists
from sqlalchemy.engine import make_url

from .config import IngestorSettings
from market_data.providers.yahoo.adapter import YAHOO_DAILY_EQUITY, YAHOO_EQUITY_HISTORY, fetch_chart, parse_delivery
from security_master_schema.demo_data import DEMO_IDS
from market_data.ingestion import ingest_delivery
from market_data.rights import load_rights
from market_data.providers.yahoo.onboarding import onboard_personal, enable_personal_research
from security_master_schema import models as m


def ingest_chart(c, **kwargs):
    """Compose Yahoo normalization with the provider-neutral daily publisher."""
    return ingest_delivery(c, provider=YAHOO_DAILY_EQUITY, parser=parse_delivery, **kwargs)


def completed_request(c, dataset_id, namespace_id, symbol, start, end):
    """Skip a successfully retained exact history request, never a failed-only one."""
    run = m.market_data_ingestion_run
    request = dict(namespaceId=str(namespace_id), symbol=symbol, start=start.isoformat(), end=end.isoformat())
    report=c.scalar(select(run.c.report).where(run.c.dataset_id == dataset_id,
        run.c.report.contains(dict(request=request)),
        or_(run.c.report['accepted'].as_integer() > 0, run.c.report['duplicates'].as_integer() > 0))
        .order_by(run.c.received_at_utc.desc()).limit(1))
    if report is None or not report.get('rejected'):
        return report
    # Re-assess only explicit missing prices against current stored points. Keep
    # the immutable original report and its run identity intact.
    mapping=c.scalar(select(m.external_object_mapping.c.target_object_id).where(
        m.external_object_mapping.c.external_id_namespace_id==namespace_id,
        m.external_object_mapping.c.external_id_value==symbol,
        m.external_object_mapping.c.target_object_type=='LISTING',
        m.external_object_mapping.c.status.in_(['PROPOSED','VERIFIED'])))
    if mapping is None:
        return report
    observation,series=m.market_data_observation,m.market_data_series
    newer=observation.alias('newer_resume_point')
    available=set(c.execute(select(series.c.series_type,observation.c.market_date).select_from(observation.join(series)).where(
        observation.c.dataset_id==dataset_id,series.c.reference_node_id==mapping,
        observation.c.quality_status=='ACCEPTED',observation.c.market_date.between(start,end),
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id==observation.c.market_data_observation_id,
            newer.c.quality_status=='ACCEPTED')))).all())
    remaining=[]
    for rejection in report['rejections']:
        try:
            identity=({'CLOSE':'CLOSE','ADJ_CLOSE':'ADJUSTED_CLOSE'}[rejection['field']],date.fromisoformat(rejection['marketDate']))
        except (KeyError,ValueError,TypeError):
            identity=None
        if rejection.get('reason')!='Missing or malformed equity price' or identity not in available:
            remaining.append(rejection)
    return dict(report,originalRejected=report['rejected'],rejected=len(remaining),rejections=remaining)


def dataset_coverage(c, dataset_id, start, end):
    series, observation, listing = m.market_data_series, m.market_data_observation, m.listing
    newer = observation.alias('newer_coverage_point')
    return [dict(row) for row in c.execute(select(listing.c.listing_node_id.label('listingId'), listing.c.trading_symbol, series.c.series_type,
        func.min(observation.c.market_date).label('firstDate'), func.max(observation.c.market_date).label('lastDate'),
        func.count().label('observations')).select_from(observation.join(series).join(listing,
            series.c.reference_node_id == listing.c.listing_node_id)).where(
        observation.c.dataset_id == dataset_id, observation.c.quality_status == 'ACCEPTED',
        observation.c.market_date.between(start, end),
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id == observation.c.market_data_observation_id,
            newer.c.quality_status == 'ACCEPTED'))).group_by(listing.c.listing_node_id, listing.c.trading_symbol, series.c.series_type)
        .order_by(listing.c.trading_symbol, series.c.series_type)).mappings()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Commit onboarding and each accepted source delivery')
    parser.add_argument('--initialize-only', action='store_true', help='Configure personal catalogue without contacting Yahoo')
    parser.add_argument('--personal-research-exception', action='store_true',
        help='Explicitly record owner-approved local Yahoo research acquisition exception; never provider permission')
    parser.add_argument('--retry-gaps',action='store_true',help='Retry only explicit missing-price dates in an exact retained --start window')
    parser.add_argument('--audit-only',action='store_true',help='Read-only calendar/continuity audit; no Yahoo request or onboarding')
    parser.add_argument('--abort-job',type=UUID,help='Explicitly close a confirmed interrupted job; --declaration supplies evidence')
    parser.add_argument('--acknowledge-personal-access', action='store_true',
        help='Operator acknowledges personal scope and responsibility for source access conditions; not commercial clearance')
    parser.add_argument('--declaration', required=True, help='Recorded owner personal-project declaration, not a provider licence')
    parser.add_argument('--tenant', type=UUID, default=DEMO_IDS['tenant'])
    parser.add_argument('--actor', type=UUID, default=DEMO_IDS['demo_user_account'])
    parser.add_argument('--symbols', nargs='*', help='Explicit Yahoo symbols; e.g. AAPL AIR.PA MT.AS')
    parser.add_argument('--limit', type=int, default=5, help='Maximum listings this run, from 1 to 543')
    parser.add_argument('--request-spacing-seconds', type=float, default=5,
        help='Serial HTTP request spacing, 1..60 seconds; 429 backoff is unchanged')
    window = parser.add_mutually_exclusive_group()
    window.add_argument('--days', type=int, help='Calendar days ending at --through, from 1 to 365; default 14')
    window.add_argument('--start', type=date.fromisoformat,
        help='Explicit history start, at most 1830 days; resumes exact successful ticker windows')
    parser.add_argument('--through', type=date.fromisoformat, default=date.today() - timedelta(days=1))
    args = parser.parse_args()
    if not 1 <= args.request_spacing_seconds <= 60:
        parser.error('Request spacing must be 1..60 seconds.')
    if args.retry_gaps and not args.start:
        parser.error('--retry-gaps requires --start for an exact original request')
    if args.audit_only and (args.retry_gaps or args.personal_research_exception or args.initialize_only or args.apply or args.abort_job):
        parser.error('--audit-only cannot combine with write/retry/activation flags')
    if args.abort_job and (not args.apply or args.retry_gaps or args.initialize_only or args.personal_research_exception):
        parser.error('--abort-job requires --apply and cannot combine with ingestion/activation flags')
    if args.days is None:
        args.days = 14
    settings = IngestorSettings.from_environment()
    url = make_url(settings.database_url)
    if (settings.environment != 'local' or url.host not in {'localhost', '127.0.0.1'}
            or url.port != 54329 or url.database != 'fortem_secm'):
        parser.error('Yahoo personal ingestion is restricted to local fortem_secm on port 54329.')
    if not 1 <= args.limit <= 543 or not 1 <= args.days <= 365 or args.through >= date.today():
        parser.error('Use limit 1..543, days 1..365, and a completed prior market date.')
    start = args.start or args.through - timedelta(days=args.days - 1)
    provider = YAHOO_EQUITY_HISTORY if args.start else YAHOO_DAILY_EQUITY
    if start > args.through or (args.through - start).days + 1 > provider.max_window_days:
        parser.error('History must be ordered and at most 1830 calendar days.')
    if args.personal_research_exception and (not args.apply or not args.acknowledge_personal_access):
        parser.error('Research exception activation requires --apply and --acknowledge-personal-access.')
    if args.apply and not args.initialize_only and not args.abort_job and not args.acknowledge_personal_access:
        parser.error('Network acquisition requires --acknowledge-personal-access. Personal scope is not commercial or automated-access legal clearance.')
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    if args.abort_job:
        from market_data.jobs import abort_job
        with engine.begin() as c:
            abort_job(c,args.abort_job,args.tenant,args.actor,args.declaration)
        print(json.dumps({'status':'ABORTED','jobId':str(args.abort_job)}),flush=True)
        engine.dispose()
        return 0
    if args.audit_only:
        from market_data.coverage import audit_dataset
        from market_data.providers.yahoo.onboarding import DATASET_CODE
        with engine.connect() as c:
            configured=c.execute(select(m.dataset_access_profile).join(m.dataset).where(
                m.dataset.c.dataset_code==DATASET_CODE)).mappings().one()
            symbols=c.execute(select(m.external_object_mapping.c.external_id_value).where(
                m.external_object_mapping.c.external_id_namespace_id==configured['external_id_namespace_id']
            ).order_by(m.external_object_mapping.c.external_id_value)).scalars().all()
            if args.symbols and set(args.symbols)-set(symbols):
                raise ValueError('Audit symbol is outside the configured namespace')
            chosen=[s for s in symbols if not args.symbols or s in args.symbols][:args.limit]
            report=audit_dataset(c,configured['dataset_id'],configured['external_id_namespace_id'],
                args.tenant,args.actor,start,args.through,chosen)
        print(json.dumps(report,default=str),flush=True)
        engine.dispose()
        return 0
    with engine.connect() as c:
        tx = c.begin()
        try:
            activate = enable_personal_research if args.personal_research_exception else onboard_personal
            onboarded = activate(c, args.tenant, args.actor, args.declaration)
            selected = [r for r in onboarded['mappings'] if not args.symbols or r['symbol'] in args.symbols]
            if args.symbols and set(args.symbols) - {r['symbol'] for r in selected}:
                raise ValueError('Requested symbol is not part of the reviewed seeded universe')
            selected = selected[:args.limit]
            acquisition = load_rights(c, UUID(onboarded['datasetId']), 'ACQUIRE', date.today(), 'PERSONAL')
            if args.apply:
                tx.commit()
            else:
                tx.rollback()
        except Exception:
            tx.rollback()
            raise
    summary = dict(database=url.database, mode='PERSONAL_APPLIED' if args.apply else 'ROLLED_BACK_PREVIEW',
                   datasetId=onboarded['datasetId'], proposedUniverseMappings=len(onboarded['mappings']),
                   selected=[r['symbol'] for r in selected], acquisitionAllowed=acquisition.allowed,
                   acquisitionEvidenceBases=sorted({e['basis'] for e in acquisition.evidence}),
                   commercialRights=False, redistributionRights=False)
    print(json.dumps(summary), flush=True)
    if not args.apply or args.initialize_only:
        return 0
    from .yahoo_run import execute
    try:
        outcome=execute(engine,dataset_id=UUID(onboarded['datasetId']),namespace_id=UUID(onboarded['namespaceId']),
            tenant_id=args.tenant,actor_id=args.actor,selected=selected,start=start,end=args.through,
            provider=provider,parser=parse_delivery,fetch=fetch_chart,lookup_previous=completed_request,
            history=bool(args.start),retry_gaps=args.retry_gaps,sleep=time.sleep,
            request_spacing_seconds=args.request_spacing_seconds)
        if outcome not in (0,3):
            return outcome  # Failed/blocked source acquisition is not RAW readiness.
        # Publication and split normalization are distinct stages. Complete source
        # ingestion is not an assertion that every derived RAW price is ready.
        from market_data.providers.yahoo.raw_prices import normalize_dataset
        with engine.begin() as c:
            normalized=normalize_dataset(c,UUID(onboarded['datasetId']),args.tenant,args.actor,
                symbols=[r['symbol'] for r in selected])
        exit_code=outcome or (0 if normalized['status']=='COMPLETE' else 3)
        # Keep event identity and normalization result distinct; normalize_dataset
        # already supplies a status, so expanding it into dict(status=...) crashes.
        print(json.dumps(dict(status='RAW_NORMALIZATION_FINISHED',normalization=normalized,
            sourceOutcome='COMPLETE' if outcome==0 else 'PARTIAL',
            outcome='COMPLETE' if exit_code==0 else 'PARTIAL')),flush=True)
        return exit_code
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
