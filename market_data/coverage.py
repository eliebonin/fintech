"""Read-only versioned session comparison, not an authoritative calendar feed."""
from functools import lru_cache
from datetime import date
from sqlalchemy import select,exists
from security_master_schema import models as m
from .rights import load_rights
from .history import history_status,require_admin


@lru_cache(maxsize=32)
def calendar_sessions(mic,start,end):
    calendars={'XNYS':'NYSE','XNAS':'NASDAQ','XPAR':'XPAR','XAMS':'XAMS'}
    name=calendars.get(mic)
    if not name:
        return None,{'status':'NOT_ASSESSED','reason':'Unsupported exchange calendar','mic':mic}
    try:
        import pandas_market_calendars as calendars_module
        from importlib.metadata import version
        calendar=calendars_module.get_calendar(name)
        days=frozenset(d.date() for d in calendar.valid_days(start_date=start,end_date=end))
        return days,{'calendar':name,'package':'pandas_market_calendars',
            'packageVersion':version('pandas_market_calendars'),'authoritative':False}
    except (ImportError,KeyError,ValueError,RuntimeError) as exc:
        return None,{'status':'NOT_ASSESSED','reason':str(exc),'mic':mic}


def reconcile_dates(observed,expected):
    if expected is None:
        return {'status':'NOT_ASSESSED','missingSessions':[], 'unavailableLeadingSessions':[], 'unexpectedDates':[]}
    missing=set(expected)-set(observed)
    leading={d for d in missing if observed and d<min(observed)}
    gaps=missing-leading
    unexpected=set(observed)-set(expected)
    status=('EMPTY' if not observed else 'GAPS' if gaps or unexpected else
            'SHORT_HISTORY' if leading else 'MATCHES_CALENDAR')
    return {'status':status,'missingSessions':[d.isoformat() for d in sorted(gaps)],
        'unavailableLeadingSessions':[d.isoformat() for d in sorted(leading)],
        'unexpectedDates':[d.isoformat() for d in sorted(unexpected)]}


def audit_dataset(c,dataset_id,namespace_id,tenant_id,actor_id,start,end,symbols=None):
    require_admin(c,tenant_id,actor_id)
    if end<start or (end-start).days+1>1830:
        raise ValueError('Audit requires an ordered bounded history window')
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id,
        m.dataset_access_profile.c.external_id_namespace_id==namespace_id,
        m.dataset_access_profile.c.permitted_tenant_id==tenant_id)).mappings().one_or_none()
    if not profile or not load_rights(c,dataset_id,'DISPLAY',date.today()).allowed:
        raise PermissionError('DISPLAY permission for this tenant dataset is required')
    mapping,listing,mic=m.external_object_mapping,m.listing,m.market_venue_identifier
    rows=c.execute(select(mapping.c.external_object_mapping_id,mapping.c.external_id_value,listing.c.listing_node_id,
        listing.c.trading_symbol,mic.c.identifier_value.label('mic')).select_from(mapping.join(listing,
        mapping.c.target_object_id==listing.c.listing_node_id).join(mic,listing.c.market_venue_id==mic.c.market_venue_id)).where(
        mapping.c.external_id_namespace_id==namespace_id,mapping.c.target_object_type=='LISTING',
        mapping.c.status.in_(['PROPOSED','VERIFIED']),mic.c.identifier_scheme=='ISO_10383_MIC',mic.c.is_primary.is_(True))).mappings().all()
    rows=[r for r in rows if symbols is None or r['external_id_value'] in symbols]
    series,observation=m.market_data_series,m.market_data_observation
    newer=observation.alias('newer_audit_point')
    points=c.execute(select(series.c.reference_node_id,series.c.series_type,observation.c.market_date).select_from(
        observation.join(series)).where(observation.c.dataset_id==dataset_id,
        observation.c.quality_status=='ACCEPTED',observation.c.market_date.between(start,end),
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id==observation.c.market_data_observation_id,
            newer.c.quality_status=='ACCEPTED')))).all()
    dates={}
    for node,kind,day in points:
        dates.setdefault((node,kind),[]).append(day)
    results=[]
    for row in rows:
        expected,evidence=calendar_sessions(row['mic'],start,end)
        continuity=history_status(c,row['external_object_mapping_id'],start,end)
        for kind in ('CLOSE','ADJUSTED_CLOSE'):
            actual=dates.get((row['listing_node_id'],kind),[])
            results.append(dict(symbol=row['external_id_value'],listingId=str(row['listing_node_id']),
                seriesType=kind,mic=row['mic'],observations=len(actual),distinctDates=len(set(actual)),
                ambiguousDates=len(actual)-len(set(actual)),firstDate=min(actual).isoformat() if actual else None,
                lastDate=max(actual).isoformat() if actual else None,historicalContinuity=continuity,
                calendarEvidence=evidence,**reconcile_dates(set(actual),expected)))
    return {'datasetId':str(dataset_id),'start':start.isoformat(),'end':end.isoformat(),
        'listingCount':len(rows),'series':results,'pricesModified':False,'calendarCertification':False}
