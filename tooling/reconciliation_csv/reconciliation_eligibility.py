"""Explicit local personal-file valuation setup; never upstream legal clearance.

Caller owns the transaction. Original deliveries, rights and policies are retained.
No trade, financial result, source value or fixing/publication time is rewritten.
"""
from datetime import date,datetime,time,timedelta,timezone
from hashlib import sha256
import json
from uuid import UUID
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from security_master_schema.access_management import audit
from market_data.rights import load_rights
from tooling.reconciliation_csv.reconciliation_fx import _put,TIMING


def build_policy(strategy,cut,calendar,prices,fx,first,types,*,include_fund_nav=False,fund_nav_calendar_id=None):
    from apps.reference_api.valuation_policy_contracts import PolicyCreate,PolicyRuleInput
    products=[('BOND','CLOSE',prices),('ACTIVELY_MANAGED_CERTIFICATE','CLOSE',prices),
        ('OPTION','CLOSE',prices),('SWAP','MARK',prices),('FX_FORWARD','FX_FORWARD',prices),(None,'FX_SPOT',fx)]
    if include_fund_nav:
        if fund_nav_calendar_id is None:raise ValueError('A published tenant valuation calendar is required for fund NAVs')
        products.append(('FUND_SHARE_CLASS','NAV',prices))
    return PolicyCreate(policyCode='RECON_EOD_'+str(strategy).replace('-',''),
        displayName='Imported EoD — prior-day fund NAVs (personal reconciliation)' if include_fund_nav else 'Imported EoD — source date only (personal reconciliation)',
        strategyId=strategy,valuationCutId=cut,selectionMode='STRICT',validFrom=first,
        rules=[PolicyRuleInput(ruleSequence=i,datasetId=dataset,seriesType=kind,valueBasis='RAW',
            instrumentTypeId=types[product] if product else None,subjectType=None if product else 'FX_PAIR',
            pricingConvention='NAV_DATE' if kind=='NAV' else 'EXPLICIT_TIME',pricingCutId=None if kind=='NAV' else cut,marketCalendarId=fund_nav_calendar_id if kind=='NAV' else calendar,selectionMethod='LAST_BEFORE_CUT',
            pricingDateRule='FIXED_LAG' if kind=='NAV' else 'SAME_DAY',lagBusinessDays=1 if kind=='NAV' else 0,
            maxStalenessBusinessDays=0,missingDataAction='FAIL')
            for i,(product,kind,dataset) in enumerate(products,1)])


def _calendar(c,actor,first,last):
    """Generic UTC date partitions, NOT exchange hours or inferred holidays."""
    from market_data.calendar_store import publish_reference_calendar
    begin=date(first.year,1,1);end=date(last.year,12,31)
    code=f'UTC_DATE_BUCKET_{begin.year}_{end.year}'
    definition=dict(method='INTERNAL_UTC_DAY_PARTITION_V1',description='Every UTC date is an available valuation bucket; missing observations still fail. Not exchange/fixing hours or holidays.')
    source=c.execute(select(m.market_calendar).where(m.market_calendar.c.calendar_code==code)).mappings().one_or_none()
    if source:
        if source['definition_json']!=definition or source['tenant_id'] is not None or source['status']!='ACTIVE':raise ValueError('UTC date calendar differs')
    else:
        identity=c.scalar(m.market_calendar.insert().values(calendar_code=code,display_name='UTC daily date buckets (not exchange sessions)',
            timezone_name='UTC',calendar_kind='CONTINUOUS_24X7',definition_json=definition).returning(m.market_calendar.c.market_calendar_id))
        c.execute(m.market_calendar_session.insert(),[dict(market_calendar_id=identity,session_date=begin+timedelta(days=n),session_status='OPEN',
            open_local_time=time.min,close_local_time=time.max,source_reference='Internal UTC Gregorian date partition, no holiday inference') for n in range((end-begin).days+1)])
        source=c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id==identity)).mappings().one()
    published=c.execute(select(m.market_calendar).where(m.market_calendar.c.logical_code==code,m.market_calendar.c.sealed,
        m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.tenant_id.is_(None)).order_by(m.market_calendar.c.version_no.desc())).mappings().first()
    if published:return published['market_calendar_id']
    return publish_reference_calendar(c,source['market_calendar_id'],actor,'Publish internal UTC date buckets for source-date-only EoD selection; no venue/fixing assertion.')


def fund_nav_calendar_payload(strategy,first,last):
    """Explicit reconciliation weekday baseline, not inferred fund holidays."""
    from apps.reference_api.calendar_contracts import CalendarPublish
    code='RECON_NAV_DATE_'+strategy.hex
    return CalendarPublish(calendarCode=code,displayName='Imported NAV valuation weekdays — holiday calendar not supplied',
        purpose='VALUATION',timezoneName='UTC',decisionTime='23:59:59',coverageFrom=first,coverageTo=last,
        mode='WEEKDAYS',weekdays=[0,1,2,3,4],baseCalendarIds=[],
        sourceReference='Owner-confirmed previous valuation-day NAV convention. Monday-Friday reconciliation baseline only; actual fund holidays require governed dates, never inferred from missing prices.')


def _fund_nav_calendar(c,tenant,actor,strategy,first,last):
    from apps.reference_api.calendar_service import publish_calendar
    payload=fund_nav_calendar_payload(strategy,first,last)
    return publish_calendar(c,tenant,actor,payload,payload.calendar_code+'_WEEKDAYS_V2').calendarId


def _grant(c,tenant,actor,dataset,profile,first,declaration,*,create):
    today=governance_date();prefix='RECON_VAL_'+dataset.hex
    licence=_put(c,m.data_licence,'data_licence_id',[m.data_licence.c.licence_code==prefix],dict(
        licensor_organisation_id=profile['licensee_organisation_id'],licensee_organisation_id=profile['licensee_organisation_id'],
        licence_code=prefix,display_name='Local personal historical-valuation instruction — upstream rights unverified',
        licence_reference='OWNER_SUPPLIED_PERSONAL_VALUATION_INSTRUCTION',permitted_use_description=declaration,valid_from=today,status='ACTIVE'),allow_create=create)
    assignment=_put(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',[
        m.dataset_licence_assignment.c.dataset_id==dataset,m.dataset_licence_assignment.c.data_licence_id==licence],
        dict(dataset_id=dataset,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=today,status='ACTIVE'),allow_create=create)
    _put(c,m.licence_activity_grant,'grant_id',[m.licence_activity_grant.c.dataset_licence_assignment_id==assignment,m.licence_activity_grant.c.activity=='NON_DISPLAY'],
        dict(dataset_licence_assignment_id=assignment,activity='NON_DISPLAY',usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
            evidence_reference=declaration,valid_from=today,status='ACTIVE'),allow_create=create)
    _put(c,m.dataset_right_requirement,'requirement_id',[m.dataset_right_requirement.c.dataset_id==dataset,m.dataset_right_requirement.c.activity=='NON_DISPLAY',
        m.dataset_right_requirement.c.requirement_code=='OWNER_SUPPLIED_PERSONAL_VALUATION'],dict(dataset_id=dataset,activity='NON_DISPLAY',
            requirement_code='OWNER_SUPPLIED_PERSONAL_VALUATION',dataset_licence_assignment_id=assignment),allow_create=create)
    # This records historical economic-date coverage for calculations performed
    # now. The separate permission declaration is recorded/effective today.
    _put(c,m.tenant_dataset_entitlement,'tenant_dataset_entitlement_id',[
        m.tenant_dataset_entitlement.c.tenant_id==tenant,m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION'],
        dict(tenant_id=tenant,dataset_id=dataset,dataset_licence_assignment_id=assignment,use_purpose='VALUATION',coverage_mode='DATASET',valid_from=first,status='ACTIVE'),allow_create=create)
    decision=load_rights(c,dataset,'NON_DISPLAY',today,'PERSONAL')
    if not decision.allowed:raise PermissionError('Personal valuation rights: '+decision.reason)
    return decision.evidence


def _forward_aliases(c,tenant,strategy,dataset,profile,*,create):
    """Identity quotation normalization; original observations stay immutable."""
    from market_data import storage
    from positions.fx_forward import normalize_booking
    series=c.execute(select(m.market_data_series).where(m.market_data_series.c.default_dataset_id==dataset,
        m.market_data_series.c.series_type=='FORWARD_RATE')).mappings().all()
    aliases=[]
    for source in series:
        snapshots=[]
        for trade in c.execute(select(m.trade).where(m.trade.c.strategy_id==strategy,m.trade.c.reference_instrument_node_id==source['reference_node_id'],m.trade.c.price_basis=='RATE')).mappings():
            event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade['trade_id'],m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one()
            proof=normalize_booking(c,trade,json.loads(event['event_payload']),event)
            snapshots.append((proof['baseCurrencyId'],proof['priceCurrencyId'],proof['maturityDate']))
        if not snapshots or len(set(snapshots))!=1:raise ValueError('Unique frozen forward currencies/maturity required')
        base,quote,maturity=snapshots[0]
        codes=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(m.currency.c.currency_id.in_([UUID(base),UUID(quote)]))).all())
        dims=dict(c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value).where(
            m.market_data_series_dimension.c.market_data_series_id==source['market_data_series_id'])).all())
        if (dims.get('BASE_CURRENCY')!=codes[UUID(base)] or dims.get('QUOTE_CURRENCY')!=codes[UUID(quote)]
            or dims.get('FORWARD_RATE_KIND')!='CONTRACT_OUTRIGHT_RATE' or source['currency_id']!=UUID(quote)):
            raise ValueError('Source forward orientation/whole-contract rate differs')
        key='FORWARD_QUOTE_IDENTITY_V1:'+str(source['market_data_series_id'])
        observations=[dict(row) for row in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==source['market_data_series_id'],
            m.market_data_observation.c.dataset_id==dataset).order_by(m.market_data_observation.c.market_date,m.market_data_observation.c.market_data_observation_id)).mappings()]
        raw=json.dumps(dict(method='FORWARD_QUOTE_IDENTITY_V1',sourceSeriesId=str(source['market_data_series_id']),maturityDate=maturity,
            observations=[{k:str(row[k]) for k in ('market_data_observation_id','value','market_date','observed_at_utc','received_at_utc','source_published_at_utc','value_basis','quality_status')} for row in observations]),sort_keys=True)
        digest=sha256(raw.encode()).hexdigest()
        old=storage.previous_delivery(c,dataset,key)
        if old:
            if old['content_sha256']!=digest:raise ValueError('Source forward history changed; explicit normalization revision required')
            alias=UUID(old['report']['normalizedSeriesId'])
            if not c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.market_data_series_id==alias,m.market_data_series.c.status=='ACTIVE')):
                raise ValueError('Normalized forward series removed or inactive')
            aliases.append(alias);continue
        if not create:raise ValueError('Normalized forward evidence removed; explicit repair required')
        now=c.scalar(select(func.clock_timestamp()))
        run,payload=storage.retain_payload(c,namespace_id=profile['external_id_namespace_id'],profile=profile,delivery_key=key,digest=digest,received_at=now)
        provider=c.scalar(select(m.provider_product.c.data_provider_id).join(m.dataset).where(m.dataset.c.dataset_id==dataset))
        vintage=storage.insert_returning(c,m.market_data_vintage,'market_data_vintage_id',dataset_id=dataset,data_provider_id=provider,
            source_vintage_key=key,received_at_utc=now,value_basis='RAW',content_hash=digest,source_payload_id=payload)
        values={k:v for k,v in source.items() if k not in ('market_data_series_id','created_at_utc')}
        alias=storage.insert_returning(c,m.market_data_series,'market_data_series_id',**(values|dict(series_type='FX_FORWARD',closing_method='UNKNOWN')))
        dimensions=dims|dict(RATE_BASIS='FORWARD_OUTRIGHT',MATURITY_DATE=maturity,NORMALIZATION_METHOD='FORWARD_QUOTE_IDENTITY_V1',SOURCE_SERIES_ID=str(source['market_data_series_id']))
        c.execute(m.market_data_series_dimension.insert(),[dict(market_data_series_id=alias,dimension_code=k,dimension_value=v) for k,v in dimensions.items()])
        if observations:
            c.execute(m.market_data_observation.insert(),[{k:v for k,v in row.items() if k not in ('market_data_observation_id','source_sequence','supersedes_observation_id')}
                |dict(market_data_series_id=alias,market_data_vintage_id=vintage,source_payload_id=payload,received_at_utc=now,
                    source_observation_key=str(row['market_data_observation_id']),source_payload_reference='Original observation '+str(row['market_data_observation_id'])) for row in observations])
        storage.finish_delivery(c,run_id=run,dataset_id=dataset,source_payload_id=payload,delivery_key=key,digest=digest,raw_payload=raw,
            received_at=now,evidence=[],report=dict(accepted=len(observations),rejections=[],normalizedSeriesId=str(alias),method='FORWARD_QUOTE_IDENTITY_V1'))
        aliases.append(alias)
    return aliases


def prepare(c,tenant,actor,platform_actor,strategy,source_id,prices,fx,declaration,*,include_fund_nav=False):
    """Add separately attributable permission, date policy and unit normalization."""
    from market_data.history import require_admin
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.tenant_workspace import resolve_platform_role
    from apps.reference_api.valuation_policies import create_policy
    require_admin(c,tenant,actor)
    for action in ('STRATEGY_WRITE','TRADE_READ','VALUATION_RUN'):require_strategy_action(c,tenant,actor,action,strategy)
    if resolve_platform_role(c,platform_actor,governance_date())!='PLATFORM_ADMIN':raise PermissionError('Platform calendar publication authority required')
    if not isinstance(declaration,str) or len(declaration.strip())<40:raise ValueError('Explicit attributable personal-use instruction required')
    if prices==fx:raise ValueError('Distinct price and FX datasets required')
    if not c.scalar(select(m.external_object_mapping.c.external_object_mapping_id).join(m.external_id_namespace).where(
        m.external_object_mapping.c.tenant_id==tenant,m.external_object_mapping.c.target_object_id==strategy,
        m.external_object_mapping.c.target_object_type=='STRATEGY',m.external_object_mapping.c.status=='VERIFIED',
        m.external_id_namespace.c.status=='ACTIVE',m.external_id_namespace.c.integration_source_system_id==source_id)):
        raise ValueError('Strategy is not owned by the retained source integration')
    signature_fields=dict(tenant=str(tenant),strategy=str(strategy),sourceId=str(source_id),prices=str(prices),fx=str(fx),declaration=declaration)
    if include_fund_nav:signature_fields['includeFundNav']=True
    signature=sha256(json.dumps(signature_fields,sort_keys=True).encode()).hexdigest()
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(('eligibility:'+str(strategy)).encode()).digest()[:8],'big',signed=True))))
    old=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.action=='RECONCILIATION_VALUATION_ELIGIBILITY',
        m.access_audit_event.c.details['strategyId'].as_string()==str(strategy))).scalars().all()
    if len(old)>1 or old and old[0]['signature']!=signature:raise ValueError('Existing eligibility instruction differs; create an explicitly reviewed revision')
    profiles={};first=None;last=None;evidence=[]
    for dataset in (prices,fx):
        action='RECONCILIATION_PRICES_IMPORTED' if dataset==prices else 'RECONCILIATION_FX_IMPORTED'
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action==action,m.access_audit_event.c.details['datasetId'].as_string()==str(dataset),
            m.access_audit_event.c.details['sourceId'].as_string()==str(source_id))):
            raise ValueError('Dataset has no matching owned reconciliation import evidence')
        if not c.scalar(select(m.dataset.c.dataset_id).select_from(m.dataset.join(m.provider_product).join(m.data_provider)).where(
            m.dataset.c.dataset_id==dataset,m.data_provider.c.owner_tenant_id==tenant,m.data_provider.c.status=='ACTIVE',m.provider_product.c.status=='ACTIVE')):
            raise PermissionError('Only this tenant private file provider is in scope')
        profile=c.execute(select(m.dataset_access_profile).select_from(m.dataset_access_profile.join(m.external_id_namespace,
            m.dataset_access_profile.c.external_id_namespace_id==m.external_id_namespace.c.external_id_namespace_id).join(m.integration_source_system,
            m.external_id_namespace.c.integration_source_system_id==m.integration_source_system.c.integration_source_system_id)).where(
            m.dataset_access_profile.c.dataset_id==dataset,m.dataset_access_profile.c.permitted_tenant_id==tenant,
            m.dataset_access_profile.c.usage_scope=='PERSONAL',m.dataset_access_profile.c.provider_enabled,
            m.external_id_namespace.c.integration_source_system_id==source_id,m.integration_source_system.c.tenant_id==tenant,
            m.dataset_access_profile.c.status=='ACTIVE',m.integration_source_system.c.status=='ACTIVE')).mappings().one()
        for activity in ('ACQUIRE','STORE','DISPLAY'):
            if not load_rights(c,dataset,activity,governance_date()).allowed:raise PermissionError('Existing local-file activity is not permitted: '+activity)
        if not c.scalar(select(m.market_data_series.c.market_data_series_id).join(m.market_data_series_dimension).where(
            m.market_data_series.c.default_dataset_id==dataset,m.market_data_series_dimension.c.dimension_code=='TIMESTAMP_SEMANTICS',m.market_data_series_dimension.c.dimension_value==TIMING)):
            raise ValueError('Only explicitly date-bucketed retained reconciliation datasets are supported')
        start,end=c.execute(select(func.min(m.market_data_observation.c.market_date),func.max(m.market_data_observation.c.market_date)).where(m.market_data_observation.c.dataset_id==dataset)).one()
        if start is None:raise ValueError('Stored historical observations required')
        first=start if first is None else min(first,start);last=end if last is None else max(last,end)
        evidence.extend(_grant(c,tenant,actor,dataset,profile,start,declaration,create=not old));profiles[dataset]=profile
    aliases=_forward_aliases(c,tenant,strategy,prices,profiles[prices],create=not old)
    if old:
        result=old[0]['result']
        if not c.scalar(select(m.market_calendar.c.market_calendar_id).where(m.market_calendar.c.market_calendar_id==UUID(result['calendarId']),
            m.market_calendar.c.sealed,m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.tenant_id.is_(None))):raise ValueError('Retained UTC calendar is unavailable')
        if not c.scalar(select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.valuation_cut_id==UUID(result['cutId']),
            m.valuation_cut.c.status=='ACTIVE',m.valuation_cut.c.local_time==time.max.isoformat(),m.valuation_cut.c.timezone_name=='UTC',
            m.valuation_cut.c.market_calendar_id==UUID(result['calendarId']))):raise ValueError('Retained source-date cut changed')
        if not c.scalar(select(m.valuation_policy.c.valuation_policy_id).where(m.valuation_policy.c.valuation_policy_id==UUID(result['policyId']),
            m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.strategy_id==strategy,m.valuation_policy.c.status=='ACTIVE')):raise ValueError('Retained policy is unavailable')
        if include_fund_nav and not c.scalar(select(m.market_calendar.c.market_calendar_id).where(
            m.market_calendar.c.market_calendar_id==UUID(result['fundNavCalendarId']),m.market_calendar.c.tenant_id==tenant,
            m.market_calendar.c.calendar_kind=='VALUATION',m.market_calendar.c.sealed,m.market_calendar.c.status=='ACTIVE')):
            raise ValueError('Retained fund NAV calendar is unavailable')
        return {k:UUID(v) if k in ('policyId','cutId','calendarId','fundNavCalendarId') else v for k,v in result.items()}
    calendar=_calendar(c,platform_actor,first,last)
    code='RECON_EOD_'+strategy.hex
    cut=_put(c,m.valuation_cut,'valuation_cut_id',[m.valuation_cut.c.cut_code==code],dict(cut_code=code,display_name='Source-date EoD UTC bucket — not a market fixing',
        timezone_name='UTC',local_time=time.max.isoformat(),market_calendar_id=calendar,status='ACTIVE'))
    types=dict(c.execute(select(m.instrument_type.c.type_code,m.instrument_type.c.instrument_type_id)).all())
    nav_calendar=_fund_nav_calendar(c,tenant,actor,strategy,first,last) if include_fund_nav else None
    policy=create_policy(c,tenant,actor,build_policy(strategy,cut,calendar,prices,fx,first,types,include_fund_nav=include_fund_nav,
        fund_nav_calendar_id=nav_calendar),code+'_V1')
    result=dict(policyId=policy.valuationPolicyId,cutId=cut,calendarId=calendar,normalizedForwardSeries=len(aliases))
    if nav_calendar:result['fundNavCalendarId']=nav_calendar
    audit(c,actor,tenant,'RECONCILIATION_VALUATION_ELIGIBILITY',dict(signature=signature,strategyId=str(strategy),sourceId=str(source_id),
        personalInstruction=declaration,calendarPublishedBy=str(platform_actor),rights=list(evidence),result={k:str(v) if isinstance(v,UUID) else v for k,v in result.items()}))
    return result
