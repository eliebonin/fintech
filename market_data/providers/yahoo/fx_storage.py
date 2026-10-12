"""Personal FX catalogue and immutable publishing; no network or API dependency."""
from datetime import date,datetime,timezone
from hashlib import sha256
import json
from sqlalchemy import select,exists
from security_master_schema import models as m
from market_data import storage
from market_data.rights import load_rights
from market_data.history import require_admin
from .fx_adapter import parse_fx,CUTS
from .onboarding import DATASET_CODE as EQUITY_CODE

DATASET_CODE='YAHOO_PERSONAL_FX_GBP'
SYMBOLS=('EURGBP=X','USDGBP=X')

def configure_fx(c,tenant,actor):
    """Reuse recorded owner research evidence, never invent a provider licence.

    Separate FX dataset/namespace, same local personal scope. No valuation,
    non-display, redistribution or commercial permissions are introduced.
    """
    require_admin(c,tenant,actor)
    original=c.execute(select(m.dataset,m.dataset_access_profile).join(m.dataset_access_profile).where(m.dataset.c.dataset_code==EQUITY_CODE)).mappings().one()
    if original['permitted_tenant_id']!=tenant or original['usage_scope']!='PERSONAL' or original['status']!='ACTIVE':
        raise PermissionError('Existing personal Yahoo profile is not available')
    for activity in ('ACQUIRE','STORE','DISPLAY'):
        if not load_rights(c,original['dataset_id'],activity,date.today()).allowed:raise PermissionError('Personal Yahoo access is not effective')
    dataset_id=c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_code==DATASET_CODE))
    if not dataset_id:
        provider=c.scalar(select(m.provider_product.c.data_provider_id).where(m.provider_product.c.provider_product_id==original['provider_product_id']))
        product=c.scalar(select(m.provider_product.c.provider_product_id).where(m.provider_product.c.data_provider_id==provider,m.provider_product.c.product_code=='PUBLIC_CHART_FX'))
        if not product:product=storage.insert_returning(c,m.provider_product,'provider_product_id',data_provider_id=provider,product_code='PUBLIC_CHART_FX',display_name='Public FX daily and intraday charts — personal research')
        dataset_id=storage.insert_returning(c,m.dataset,'dataset_id',provider_product_id=product,dataset_code=DATASET_CODE,
            display_name='Yahoo GBP FX daily closes and cutoff snapshots — personal research',data_domain='MARKET_DATA',
            coverage_description='GBP per EUR/USD. Daily provider close; separate 5-minute/hourly samples ending at 16:00 London/New York. Not benchmark fixings.',delivery_channel='API',valid_from=date.today())
        old_namespace=c.execute(select(m.external_id_namespace).where(m.external_id_namespace.c.external_id_namespace_id==original['external_id_namespace_id'])).mappings().one()
        namespace=storage.insert_returning(c,m.external_id_namespace,'external_id_namespace_id',integration_source_system_id=old_namespace['integration_source_system_id'],
            namespace_code='YAHOO_PERSONAL_FX_GBP_SYMBOL',external_object_type='REFERENCE_NODE',valid_from=date.today(),description='FX_PAIR reference nodes; direct GBP per foreign-currency unit; not inverted or triangulated.')
        c.execute(m.dataset_access_profile.insert().values(dataset_id=dataset_id,licensee_organisation_id=original['licensee_organisation_id'],permitted_tenant_id=tenant,
            external_id_namespace_id=namespace,usage_scope='PERSONAL',provider_enabled=True,status='ACTIVE',activation_reference='Owner requested personal GBP FX acquisition on 2026-10-08; existing personal research evidence reused, not provider permission.'))
        assignments={}
        for assignment in c.execute(select(m.dataset_licence_assignment).where(m.dataset_licence_assignment.c.dataset_id==original['dataset_id'])).mappings():
            values={k:assignment[k] for k in ('data_licence_id','licence_role','valid_from','valid_to','status')}
            aid=storage.insert_returning(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',dataset_id=dataset_id,**values)
            assignments[assignment['dataset_licence_assignment_id']]=aid
            for grant in c.execute(select(m.licence_activity_grant).where(m.licence_activity_grant.c.dataset_licence_assignment_id==assignment['dataset_licence_assignment_id'],m.licence_activity_grant.c.activity.in_(['ACQUIRE','STORE','DISPLAY']))).mappings():
                c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=aid,**{k:grant[k] for k in ('activity','usage_scope','evidence_basis','evidence_reference','valid_from','valid_to','status')}))
        for requirement in c.execute(select(m.dataset_right_requirement).where(m.dataset_right_requirement.c.dataset_id==original['dataset_id'],m.dataset_right_requirement.c.activity.in_(['ACQUIRE','STORE','DISPLAY']))).mappings():
            c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset_id,activity=requirement['activity'],requirement_code=requirement['requirement_code'],dataset_licence_assignment_id=assignments.get(requirement['dataset_licence_assignment_id'])))
        c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=tenant,dataset_id=dataset_id,use_purpose='INTERNAL_REPORTING',valid_from=date.today()))
    # Update only our original catalogue text; preserve operator-edited metadata.
    c.execute(m.dataset.update().where(m.dataset.c.dataset_id==dataset_id,
        m.dataset.c.coverage_description=='GBP per EUR/USD. Daily provider close; 16:00 London/New York exact closed five-minute research samples. Not benchmark fixings.').values(
        coverage_description='GBP per EUR/USD. Daily provider close; separate 5-minute/hourly samples ending at 16:00 London/New York. Not benchmark fixings.'))
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id)).mappings().one()
    if profile['permitted_tenant_id']!=tenant or profile['usage_scope']!='PERSONAL' or profile['status']!='ACTIVE' or not profile['provider_enabled']:
        raise PermissionError('Existing FX profile is not active personal scope')
    for activity in ('ACQUIRE','STORE','DISPLAY'):
        if not load_rights(c,dataset_id,activity,date.today()).allowed:raise PermissionError('FX personal access is not effective; refusing reactivation')
    cuts={}
    for label,zone in CUTS.items():
        code=f'YAHOO_RESEARCH_{label}_1600'
        cut=c.scalar(select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.cut_code==code))
        if not cut:cut=storage.insert_returning(c,m.valuation_cut,'valuation_cut_id',cut_code=code,display_name=f'Yahoo research {label} 16:00 cutoff snapshot (not a benchmark)',timezone_name=zone,local_time='16:00:00')
        reference=c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id==cut)).mappings().one()
        if reference['status']!='ACTIVE' or reference['timezone_name']!=zone or str(reference['local_time'])!='16:00:00':raise ValueError('Existing FX cutoff differs; explicit review required')
        cuts[label]=cut
    pairs={}
    node_type=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='FX_PAIR'))
    for symbol in SYMBOLS:
        base=symbol[:3];code=f'FXPAIR_{base}GBP'
        node=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code==code))
        if not node:
            node=storage.insert_returning(c,m.financial_reference_node,'reference_node_id',reference_node_type_id=node_type,internal_code=code,canonical_name=f'{base}/GBP spot reference — GBP per {base}',is_tradable=False)
            c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='SHARED_CANONICAL'))
        reference=c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==node)).mappings().one()
        scope=c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node)).mappings().one()
        if reference['status']!='ACTIVE' or reference['reference_node_type_id']!=node_type or scope['scope_type']!='SHARED_CANONICAL' or scope['status']!='ACTIVE':raise ValueError('Existing FX reference differs')
        mapping=c.execute(select(m.external_object_mapping).where(m.external_object_mapping.c.external_id_namespace_id==profile['external_id_namespace_id'],m.external_object_mapping.c.external_id_value==symbol)).mappings().one_or_none()
        if not mapping:
            c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=profile['external_id_namespace_id'],external_object_type='REFERENCE_NODE',external_id_value=symbol,target_object_type='REFERENCE_NODE',target_object_id=node,mapping_method='RULE',status='PROPOSED',valid_from=date.today()))
        elif mapping['target_object_id']!=node or mapping['status'] not in {'PROPOSED','VERIFIED'}:raise ValueError('Existing FX mapping differs')
        pairs[symbol]=node
    return {'datasetId':dataset_id,'namespaceId':profile['external_id_namespace_id'],'tenantId':tenant,'pairs':pairs,'cuts':cuts}

def ingest_fx(c,*,config,symbol,raw_payload,start,end,received_at,interval):
    if (symbol not in config['pairs'] or interval not in {'1d','5m','1h'} or received_at.utcoffset() is None
        or end<start or (end-start).days+1>({'5m':60,'1h':730}.get(interval,1830)) or len(raw_payload.encode())>4*1024*1024):
        raise ValueError('Invalid FX delivery scope')
    dataset,profile=storage.lock_dataset(c,config['datasetId'],config['namespaceId'])
    if profile['permitted_tenant_id']!=config['tenantId']:raise PermissionError('FX tenant mismatch')
    evidence=[]
    for activity in ('ACQUIRE','STORE'):
        decision=load_rights(c,config['datasetId'],activity,received_at.date())
        if not decision.allowed:raise PermissionError(decision.reason)
        evidence.extend(decision.evidence)
    # Version the normalizer so retained rejected deliveries can be explicitly
    # reprocessed after a reviewed alias fix, without overwriting old evidence.
    digest=sha256(raw_payload.encode()).hexdigest();key=f'FXv1:{symbol}:{interval}:{start}:{end}:{digest[:20]}'
    previous=storage.previous_delivery(c,config['datasetId'],key)
    if previous:return dict(previous['report'],replayed=True)
    run,payload=storage.retain_payload(c,namespace_id=config['namespaceId'],profile=profile,delivery_key=key,digest=digest,received_at=received_at)
    report={'accepted':0,'duplicates':0,'rejected':0,'rejections':[],'request':{'namespaceId':str(config['namespaceId']),'symbol':symbol,'start':str(start),'end':str(end)},'interval':interval,'normalizationVersion':1}
    try:points,rejections=parse_fx(json.loads(raw_payload),symbol=symbol,start=start,end=end,received_at=received_at,interval=interval)
    except ValueError as exc:points=[];rejections=[{'reason':str(exc)}]
    report['rejections']=rejections
    if points:
        provider=c.scalar(select(m.provider_product.c.data_provider_id).where(m.provider_product.c.provider_product_id==dataset['provider_product_id']))
        vintage=storage.insert_returning(c,m.market_data_vintage,'market_data_vintage_id',dataset_id=config['datasetId'],data_provider_id=provider,source_vintage_key=key,received_at_utc=received_at,value_basis='RAW',content_hash=digest,source_payload_id=payload)
        currency=c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code=='GBP'))
        series_ids={}
        for point in points:
            cut=config['cuts'].get(point.label)
            semantics='PROVIDER_DAILY_BAR_TIMESTAMP' if interval=='1d' else f'EXACT_COMPLETED_{interval.upper()}_BAR_AT_LOCAL_CUTOFF'
            if point.label not in series_ids:
                # Sampling interval is part of immutable series identity: hourly
                # history must not rewrite an existing five-minute definition.
                series=c.execute(select(m.market_data_series).where(m.market_data_series.c.reference_node_id==config['pairs'][symbol],m.market_data_series.c.default_dataset_id==config['datasetId'],m.market_data_series.c.series_type=='FX_SPOT',m.market_data_series.c.valuation_cut_id==cut,
                    m.market_data_series.c.market_data_series_id.in_(select(m.market_data_series_dimension.c.market_data_series_id).where(m.market_data_series_dimension.c.dimension_code=='TIMESTAMP_SEMANTICS',m.market_data_series_dimension.c.dimension_value==semantics)))).mappings().one_or_none()
                if series:
                    if series['value_type']!='RATE' or series['currency_id']!=currency or series['status']!='ACTIVE' or series['is_official'] or series['source_system_id']!='YAHOO_FINANCE_PERSONAL':raise ValueError('Existing FX series differs')
                    sid=series['market_data_series_id']
                else:
                    sid=storage.insert_returning(c,m.market_data_series,'market_data_series_id',reference_node_id=config['pairs'][symbol],default_dataset_id=config['datasetId'],series_type='FX_SPOT',value_type='RATE',currency_id=currency,valuation_cut_id=cut,source_system_id='YAHOO_FINANCE_PERSONAL',is_official=False,expected_frequency_code='BUSINESS_DAILY',measure_definition_id=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE')))
                    for code,value in {'BASE_CURRENCY':symbol[:3],'QUOTE_CURRENCY':'GBP','VALUE_BASIS':'RAW','SOURCE_FIELD':'CLOSE','SESSION':point.label,'TIMESTAMP_SEMANTICS':semantics,'SAMPLING_INTERVAL':interval}.items():
                        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=sid,dimension_code=code,dimension_value=value))
                series_ids[point.label]=sid
            sid=series_ids[point.label];newer=m.market_data_observation.alias('fx_newer')
            old=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==sid,m.market_data_observation.c.dataset_id==config['datasetId'],m.market_data_observation.c.market_date==point.market_date,m.market_data_observation.c.quality_status=='ACCEPTED',~exists(select(1).select_from(newer).where(newer.c.supersedes_observation_id==m.market_data_observation.c.market_data_observation_id,newer.c.quality_status=='ACCEPTED')))).mappings().one_or_none()
            if old and old['value']==point.value and old['source_timestamp_utc']==point.source_at:report['duplicates']+=1;continue
            if old and old['received_at_utc']>received_at:raise ValueError('FX correction receipt precedes predecessor')
            c.execute(m.market_data_observation.insert().values(market_data_series_id=sid,dataset_id=config['datasetId'],market_data_vintage_id=vintage,source_payload_id=payload,market_date=point.market_date,valuation_cut_id=cut,observed_at_utc=point.observed_at,source_timestamp_utc=point.source_at,received_at_utc=received_at,value=point.value,value_basis='RAW',source_observation_key=f'{symbol}:{point.label}:{point.market_date}',quality_status='ACCEPTED',supersedes_observation_id=old['market_data_observation_id'] if old else None))
            report['accepted']+=1
        c.execute(m.external_object_mapping.update().where(m.external_object_mapping.c.external_id_namespace_id==config['namespaceId'],m.external_object_mapping.c.external_id_value==symbol,m.external_object_mapping.c.status=='PROPOSED').values(status='VERIFIED',verified_at_utc=received_at,source_payload_id=payload))
    storage.finish_delivery(c,run_id=run,dataset_id=config['datasetId'],source_payload_id=payload,delivery_key=key,digest=digest,raw_payload=raw_payload,received_at=received_at,evidence=evidence,report=report)
    return dict(report,replayed=False)
