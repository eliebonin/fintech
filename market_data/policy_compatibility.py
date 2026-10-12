"""Read-only setup metadata: never prices, grants or valuation readiness claims."""
from collections import defaultdict
from datetime import date,datetime,timezone
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.market_data_visibility import visible_subject_clause
from .entitlements import tenant_series_entitlement_clause
from .rights import denied_activity_datasets
from .source_priority import effective_priority,rank
from .closing_prices import matches_definition, requires_official


def profile_rows(c,tenant,subject=None):
    """Metadata for stored series with at least one currently visible source grant.

    Package scope is checked per series, even for informational reporting access.
    Neither observation values nor confidential permission evidence are selected.
    """
    s,n,t,l,i,v,cal=m.market_data_series,m.financial_reference_node,m.reference_node_type,m.listing,m.instrument,m.market_venue,m.market_calendar
    observation=m.market_data_observation
    # Collapse historical observations before correlated coverage checks: inventory
    # work scales with distinct series/source/basis, not every daily price row.
    inventory=select(observation.c.market_data_series_id,observation.c.dataset_id,observation.c.value_basis).distinct()
    if subject is not None:
        inventory=inventory.where(observation.c.market_data_series_id.in_(select(s.c.market_data_series_id).where(s.c.reference_node_id==subject)))
    o=inventory.subquery('stored_profiles')
    query=select(s.c.market_data_series_id,s.c.reference_node_id,s.c.series_type,s.c.closing_method,o.c.value_basis,o.c.dataset_id,
        t.c.type_code.label('subject_type'),i.c.instrument_type_id,l.c.market_venue_id,
        cal.c.sealed.label('calendar_sealed'),
        tenant_series_entitlement_clause(o.c.dataset_id,s.c.market_data_series_id,tenant,'VALUATION',date.today()).label('valuation_allowed')
    ).select_from(s.join(o,s.c.market_data_series_id==o.c.market_data_series_id).join(n,s.c.reference_node_id==n.c.reference_node_id).join(t)
        .outerjoin(l,l.c.listing_node_id==s.c.reference_node_id)
        .outerjoin(i,i.c.instrument_node_id==func.coalesce(l.c.instrument_node_id,s.c.reference_node_id))
        .outerjoin(v,l.c.market_venue_id==v.c.market_venue_id).outerjoin(cal,v.c.market_calendar_id==cal.c.market_calendar_id)
    ).where(s.c.status=='ACTIVE',visible_subject_clause(s.c.reference_node_id,tenant),
        tenant_series_entitlement_clause(o.c.dataset_id,s.c.market_data_series_id,tenant,None,date.today())).distinct()
    if subject is not None:query=query.where(s.c.reference_node_id==subject)
    return [dict(row) for row in c.execute(query).mappings()]


def data_options(c,tenant,source_catalogue):
    grouped=defaultdict(list)
    for row in profile_rows(c,tenant):grouped[row['dataset_id']].append(row)
    result=[];denied=set(denied_activity_datasets(c,tenant,date.today(),['NON_DISPLAY']))
    for source in source_catalogue:
        profiles=defaultdict(list)
        for row in grouped[source['datasetId']]:profiles[(row['series_type'],row['value_basis'],row['closing_method'])].append(row)
        result.append(dict(datasetId=source['datasetId'],label=source['label'],provider=source['provider'],
            purposes=sorted(set(source['purposes'])),nonDisplayAllowed=source['datasetId'] not in denied,
            priceProfiles=[dict(seriesType=series,valueBasis=basis,closingMethod=method,seriesCount=len({r['market_data_series_id'] for r in rows}),
                valuationSeriesCount=len({r['market_data_series_id'] for r in rows if r['valuation_allowed']}))
                for (series,basis,method),rows in sorted(profiles.items())]))
    return dict(sources=result)


def matches_scope(rule,row):
    fields=('subject_type','instrument_type_id','market_venue_id','market_data_series_id','dataset_id')
    return (all(getattr(rule,f) is None or getattr(rule,f)==row[f] for f in fields)
        and (rule.subject_reference_node_id is None or rule.subject_reference_node_id==row['reference_node_id']))


def describe_price(series,basis):
    families={'CLOSE':'closing price','ADJUSTED_CLOSE':'adjusted closing price','OFFICIAL_CLOSE':'designated official closing price','FX_SPOT':'spot FX rate','NAV':'fund NAV'}
    adjustments={'RAW':'unadjusted','SPLIT_ADJUSTED':'split-adjusted','VENDOR_ADJUSTED':'provider-adjusted','TOTAL_RETURN':'total-return adjusted'}
    return f"{families.get(series,series)} / {adjustments.get(basis,basis or 'any adjustment basis')} ({series}/{basis or 'any'})"


def check_configuration(c,tenant,payload,source_catalogue):
    rows=profile_rows(c,tenant);sources={s['datasetId']:s for s in source_catalogue}
    denied=set(denied_activity_datasets(c,tenant,date.today(),['NON_DISPLAY']))
    priorities={};checks=[]
    for origin,rules in [('EXPLICIT',payload.rules),('DEFAULT',payload.default_rules)]:
        for rule in rules:
            scope=[r for r in rows if matches_scope(rule,r)]
            matching=[r for r in scope if matches_definition(rule,r)]
            eligible=[];issues=[]
            for row in matching:
                tid=row['instrument_type_id']
                if tid not in priorities:priorities[tid]=effective_priority(c,tenant,tid,datetime.now(timezone.utc))
                if row['valuation_allowed'] and row['dataset_id'] not in denied and rank(priorities[tid],row['dataset_id']) is not None:
                    eligible.append(row)
            def issue(code,message,action):issues.append(dict(code=code,message=message,action=action))
            if not matching:
                actual=', '.join(sorted({describe_price(r['series_type'],r['value_basis']) for r in scope})) or 'no stored series in this scope'
                official=' with exchange-official closing designation' if rule.require_official_close else ''
                issue('PRICE_NOT_AVAILABLE',f'Requires {describe_price(rule.series_type,rule.value_basis)}{official}; available: {actual}.',
                    'Choose a recorded compatible price family and adjustment basis, or arrange the required data. Do not relabel adjusted prices as unadjusted.')
            if scope and not any(r['valuation_allowed'] for r in scope):
                issue('VALUATION_USE_NOT_GRANTED','These visible sources have no recorded valuation-use coverage for the matching series.',
                    'Review Data sources and arrange the correct permission/coverage; reporting access alone does not enable valuation.')
            if matching and not eligible:
                issue('NO_ELIGIBLE_SOURCE','No matching source passes current valuation coverage, automated calculation rights and source priority.',
                    'Review Data sources, package coverage and source priorities. A policy does not grant permissions.')
            if rule.pricing_convention!='SESSION_CLOSE' or rule.series_type not in ('CLOSE','OFFICIAL_CLOSE') or not (rule.value_basis=='RAW' or rule.price_requirement=='AS_TRADED'):
                issue('VALUATION_ALPHA_UNSUPPORTED','The current valuation alpha supports unadjusted listed closing prices only.',
                    'This rule may be useful for data selection, but adjusted prices, NAVs and FX conversion require separate valuation support.')
            if rule.max_staleness_business_days is None:
                issue('UNBOUNDED_FRESHNESS','Unbounded carried-forward prices are not valuation-ready.', 'Set an explicit finite allowance in expected pricing sessions.')
            if rule.pricing_convention=='SESSION_CLOSE':
                sealed=c.scalar(select(m.market_calendar.c.sealed).where(m.market_calendar.c.market_calendar_id==rule.market_calendar_id)) if rule.market_calendar_id else None
                if (rule.market_calendar_id and not sealed) or (not rule.market_calendar_id and scope and not any(r['calendar_sealed'] for r in scope)):
                    issue('GOVERNED_CALENDAR_REQUIRED','No sealed exchange calendar is configured for these matching sources.',
                        'Arrange a governed reference calendar. An installed exchange schedule is a preview aid, not valuation signoff.')
            checks.append(dict(ruleSequence=rule.rule_sequence,origin=origin,matchingSeriesCount=len({r['market_data_series_id'] for r in matching}),
                eligibleSeriesCount=len({r['market_data_series_id'] for r in eligible}),
                sourceLabels=sorted({sources[r['dataset_id']]['label'] for r in scope if r['dataset_id'] in sources}),issues=issues))
    return dict(status='ACTION_REQUIRED' if any(r['issues'] for r in checks) else 'COMPATIBLE_CONFIGURATION',
        scope='Current configuration metadata only; not instrument/date coverage, a price validation, licensing clearance or a successful valuation.',rules=checks)


def missing_input_message(c,tenant,subject,day,rule,code):
    """Safe operational context without exposing prices from restricted sources."""
    symbol=c.scalar(select(m.listing.c.trading_symbol).where(m.listing.c.listing_node_id==subject)) or str(subject)
    profiles=profile_rows(c,tenant,subject)
    actual=', '.join(sorted({describe_price(r['series_type'],r['value_basis']) for r in profiles})[:3]) or 'no visible stored series'
    expected=describe_price(rule['series_type'],rule['value_basis']) if rule else 'a matching policy rule'
    if rule and requires_official(rule):expected+=' with exchange-official closing designation'
    permission='; visible data has no valuation-use coverage' if profiles and not any(r['valuation_allowed'] for r in profiles) else ''
    return f'Input selection blocked: {code}. {symbol} ({subject}) on {day}: requires {expected}; available {actual}{permission}. Check Pricing policies and Data sources.'
