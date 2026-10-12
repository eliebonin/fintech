"""Operator orchestration for personal FX activation; caller owns the transaction.

No prices or old policies are rewritten. Historical coverage is explicitly
scoped to the requested series/dates; permission evidence is recorded today.
"""
from datetime import date,datetime,time,timedelta,timezone
from hashlib import sha256
from sqlalchemy import select,func
from security_master_schema import models as m
from market_data.history import require_admin
from market_data.rights import load_rights
from market_data.storage import insert_returning
from market_data.calendar_store import publish_reference_calendar
from apps.reference_api.valuation_policies import policy_view,create_policy
from apps.reference_api.valuation_policy_contracts import PolicyCreate,PolicyRuleInput


def prepare_fx_valuation(c,tenant,actor,platform_actor,base_policy,start,end,reference):
    require_admin(c,tenant,actor)
    from security_master_schema.tenant_workspace import resolve_platform_role,resolve_tenant_workspace
    if 'VALUATION' not in resolve_tenant_workspace(c,tenant,actor,date.today()).module_codes:
        raise PermissionError('VALUATION access required')
    if resolve_platform_role(c,platform_actor,date.today())!='PLATFORM_ADMIN':
        raise PermissionError('Platform calendar publication authority required')
    if not reference.strip() or not 0 <= (end-start).days <= 30 or end>date.today():
        raise ValueError('Explicit owner reference and bounded historical period required')
    old=policy_view(c,tenant,base_policy)
    digest=sha256(f'{tenant}:{actor}:{platform_actor}:{base_policy}:{start}:{end}:{reference}'.encode()).hexdigest()
    key='yahoo-fx-valuation:'+digest
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(key.encode()).digest()[:8],'big',signed=True))))
    replay=c.scalar(select(m.valuation_policy.c.valuation_policy_id).where(m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.submission_key==key))
    if replay: return {'policyId':replay,'basePolicyId':base_policy}
    dataset=c.execute(select(m.dataset).where(m.dataset.c.dataset_code=='YAHOO_PERSONAL_FX_GBP').with_for_update()).mappings().one()
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset['dataset_id'])).mappings().one()
    if profile['permitted_tenant_id']!=tenant or profile['usage_scope']!='PERSONAL':
        raise PermissionError('Only the owning personal Yahoo tenant is eligible')
    for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
        if not load_rights(c,dataset['dataset_id'],activity,date.today(),'PERSONAL').allowed:
            raise PermissionError('Existing personal source rights must remain active')
    eligible=[]
    for s in c.execute(select(m.market_data_series).where(m.market_data_series.c.default_dataset_id==dataset['dataset_id'],
        m.market_data_series.c.series_type=='FX_SPOT',m.market_data_series.c.status=='ACTIVE')).mappings():
        dims=dict(c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value).where(
            m.market_data_series_dimension.c.market_data_series_id==s['market_data_series_id'])).all())
        if dims.get('BASE_CURRENCY')=='EUR' and dims.get('QUOTE_CURRENCY')=='GBP' and dims.get('SESSION')=='UK' and dims.get('TIMESTAMP_SEMANTICS')=='EXACT_COMPLETED_5M_BAR_AT_LOCAL_CUTOFF':
            eligible.append(s)
    if len(eligible)!=1: raise ValueError('Unique EUR/GBP UK completed five-minute sample series required')
    series=eligible[0]
    cut=c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id==series['valuation_cut_id'])).mappings().one()
    if cut['timezone_name']!='Europe/London' or str(cut['local_time'])!='16:00:00' or cut['status']!='ACTIVE':
        raise ValueError('Active London 16:00 research cutoff required')
    from zoneinfo import ZoneInfo
    days=[start+timedelta(days=n) for n in range((end-start).days+1)]
    source_ids=[]
    for day in days:
        target=datetime.combine(day,time(16),ZoneInfo('Europe/London')).astimezone(timezone.utc)
        row=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series['market_data_series_id'],
            m.market_data_observation.c.dataset_id==dataset['dataset_id'],m.market_data_observation.c.market_date==day,
            m.market_data_observation.c.quality_status=='ACCEPTED',m.market_data_observation.c.value_basis=='RAW',
            m.market_data_observation.c.observed_at_utc==target,m.market_data_observation.c.source_timestamp_utc==target-timedelta(minutes=5))
            .order_by(m.market_data_observation.c.received_at_utc.desc()).limit(1)).mappings().one_or_none()
        if not row: raise ValueError(f'Missing exact completed UK research sample on {day}')
        source_ids.append(str(row['market_data_observation_id']))
    stamp=datetime.now(timezone.utc)
    evidence=(f'Owner authorization recorded {stamp.isoformat()}, actor {actor}, tenant {tenant}: {reference.strip()}. '
        f'Current personal valuation using EUR/GBP UK completed samples for business dates {start} through {end}. '
        f'Original dataset coverage start {dataset["valid_from"]}. Not historical authorization, provider consent, commercial rights or a benchmark fixing. '
        f'Observation evidence: {source_ids}')
    licence=insert_returning(c,m.data_licence,'data_licence_id',licensor_organisation_id=profile['licensee_organisation_id'],
        licensee_organisation_id=profile['licensee_organisation_id'],licence_code='YAHOO_FX_HISTORY_'+digest[:32],
        display_name='Owner historical FX personal declaration',licence_reference=reference[:500],permitted_use_description=evidence,valid_from=date.today())
    assignment=insert_returning(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',dataset_id=dataset['dataset_id'],
        data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=date.today())
    c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,activity='NON_DISPLAY',usage_scope='PERSONAL',
        evidence_basis='PERSONAL_DECLARATION',evidence_reference=evidence,valid_from=date.today()))
    c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset['dataset_id'],activity='NON_DISPLAY',
        requirement_code='OWNER_HISTORICAL_FX_'+digest[:32],dataset_licence_assignment_id=assignment))
    provider=c.scalar(select(m.provider_product.c.data_provider_id).where(m.provider_product.c.provider_product_id==dataset['provider_product_id']))
    package=insert_returning(c,m.dataset_coverage_package,'coverage_package_id',dataset_id=dataset['dataset_id'],package_code='EURGBP_UK_'+digest[:32],
        display_name=f'EUR/GBP UK research samples {start}–{end}',content_owner_provider_id=provider,information_timing='HISTORICAL',
        evidence_reference=evidence,valid_from=start,valid_to=end)
    # Never repurpose an existing reviewed classification.
    if c.scalar(select(m.market_data_series_coverage.c.coverage_package_id).where(m.market_data_series_coverage.c.dataset_id==dataset['dataset_id'],
        m.market_data_series_coverage.c.market_data_series_id==series['market_data_series_id'])):
        raise ValueError('Existing FX classification requires separate review')
    c.execute(m.market_data_series_coverage.insert().values(dataset_id=dataset['dataset_id'],market_data_series_id=series['market_data_series_id'],coverage_package_id=package))
    entitlement=insert_returning(c,m.tenant_dataset_entitlement,'tenant_dataset_entitlement_id',tenant_id=tenant,dataset_id=dataset['dataset_id'],
        dataset_licence_assignment_id=assignment,use_purpose='VALUATION',coverage_mode='SCOPED',valid_from=start,valid_to=end)
    c.execute(m.tenant_dataset_coverage.insert().values(tenant_dataset_entitlement_id=entitlement,dataset_id=dataset['dataset_id'],coverage_package_id=package))
    if dataset['valid_from']>start:
        c.execute(m.dataset.update().where(m.dataset.c.dataset_id==dataset['dataset_id']).values(valid_from=start))
    draft=insert_returning(c,m.market_calendar,'market_calendar_id',calendar_code='YAHOO_FX_RESEARCH_'+digest[:32],
        display_name=f'Yahoo UK research sample dates {start}–{end} (not exchange holidays)',timezone_name='Europe/London',calendar_kind='TRADING')
    for day in days:
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=draft,session_date=day,session_status='OPEN',
            open_local_time=time(0),close_local_time=time(16),source_reference=f'Yahoo observed completed UK sample; declaration {licence}; observations {source_ids}'))
    calendar=publish_reference_calendar(c,draft,platform_actor,'Observed research sample dates only; not an authoritative FX holiday calendar')
    rules=old.rules+[PolicyRuleInput(ruleSequence=max(r.rule_sequence for r in old.rules+old.defaultRules)+1,
        subjectType='FX_PAIR',subjectReferenceNodeId=series['reference_node_id'],marketDataSeriesId=series['market_data_series_id'],
        datasetId=dataset['dataset_id'],seriesType='FX_SPOT',valueBasis='RAW',pricingConvention='EXPLICIT_TIME',pricingCutId=series['valuation_cut_id'],
        marketCalendarId=calendar,selectionMethod='LAST_BEFORE_CUT',maxStalenessBusinessDays=0)]
    payload=PolicyCreate(policyCode=old.policyCode,displayName=old.displayName+' + EUR/GBP UK research FX',valuationCutId=old.valuationCutId,
        strategyId=old.strategyId,validFrom=old.validFrom,validTo=old.validTo,selectionMode=old.selectionMode,rules=rules,defaultRules=old.defaultRules)
    new=create_policy(c,tenant,actor,payload,key)
    return {'policyId':new.valuationPolicyId,'basePolicyId':base_policy}
