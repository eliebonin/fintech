"""Private file FX publication. No network, fabricated fixing or vendor rights.

This bounded reconciliation adapter uses the existing storage/rights model.
Original CSV evidence survives; the retained delivery explicitly selects rows.
"""
from datetime import date,datetime,time,timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4
from collections import defaultdict
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from tooling.reconciliation_csv.reconciliation import document,source_id
from tooling.reconciliation_csv.reconciliation_precision import native_decimal
from market_data import storage
from market_data.history import require_admin
from market_data.rights import load_rights

DEFAULT_CURRENCIES=('GBP','USD','EUR','JPY','CHF','CAD','AUD','NZD','SEK','NOK','DKK','SGD','HKD','INR','KRW')
NEW_FIAT={'NZD':'New Zealand dollar','SEK':'Swedish krona','NOK':'Norwegian krone','DKK':'Danish krone'}
TIMING='SOURCE_DATE_ONLY_EOD_BUCKET'


def select_rates(rows,selected=DEFAULT_CURRENCIES,*,source_currency_codes=None):
    selected=set(selected);seen=set();points=[]
    if not 2<=len(selected)<=15 or not selected.issubset(DEFAULT_CURRENCIES):
        raise ValueError('Select two to fifteen supported source fiat currencies')
    for row in rows:
        base,quote=row['base_currency'],row['quote_currency']
        if base not in selected or quote not in selected:continue
        for label,code in [('base',base),('quote',quote)]:
            identifier=row.get(label+'_currency_id')
            if identifier and source_currency_codes is not None and source_currency_codes.get(source_id(identifier))!=code:
                raise ValueError('Source currency ID and ISO code disagree')
        day=date.fromisoformat(row['date']);key=(base,quote,day)
        if key in seen:raise ValueError('Duplicate source pair/date FX value')
        seen.add(key);value=native_decimal(row['rate'])
        if Decimal(value['value'])<=0:raise ValueError('Positive finite FX value required')
        if base==quote:
            if Decimal(row['rate'])!=1:raise ValueError('Invalid identity FX rate')
            continue
        points.append(dict(base=base,quote=quote,day=day,normalization=value,originalRow=dict(row)))
    if not points:raise ValueError('No selected non-identity FX observations')
    return sorted(points,key=lambda p:(p['base'],p['quote'],p['day']))


def _put(c,table,key,predicate,values,*,allow_create=True):
    old=c.execute(select(table).where(*predicate)).mappings().one_or_none()
    if old:
        # Dates describe the first activation; don't backdate on a later replay.
        if any(old[k]!=v for k,v in values.items() if k!='valid_from'):
            raise ValueError('Existing FX import metadata differs: '+table.name)
        return old[key]
    if not allow_create:raise PermissionError('Existing FX dataset governance is missing; explicit review required: '+table.name)
    return storage.insert_returning(c,table,key,**values)


def _pair(c,base,quote,node_type):
    s=m.market_data_series;b=m.market_data_series_dimension.alias('fx_base');q=m.market_data_series_dimension.alias('fx_quote')
    existing=set(c.scalars(select(s.c.reference_node_id).join(b,b.c.market_data_series_id==s.c.market_data_series_id)
        .join(q,q.c.market_data_series_id==s.c.market_data_series_id).where(s.c.status=='ACTIVE',s.c.series_type=='FX_SPOT',
            s.c.value_type=='RATE',b.c.dimension_code=='BASE_CURRENCY',b.c.dimension_value==base,
            q.c.dimension_code=='QUOTE_CURRENCY',q.c.dimension_value==quote)))
    if len(existing)>1:raise ValueError('Ambiguous existing canonical FX pair: '+base+'/'+quote)
    if existing:
        node=next(iter(existing))
        c.execute(select(m.financial_reference_node).join(m.reference_node_scope,
            m.reference_node_scope.c.reference_node_id==m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.reference_node_id==node,m.financial_reference_node.c.reference_node_type_id==node_type,
            m.financial_reference_node.c.status=='ACTIVE',m.reference_node_scope.c.scope_type=='SHARED_CANONICAL',
            m.reference_node_scope.c.status=='ACTIVE')).one()
        return node
    node=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code=='FXPAIR_'+base+quote))
    if node:
        c.execute(select(m.financial_reference_node).join(m.reference_node_scope,
            m.reference_node_scope.c.reference_node_id==m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.reference_node_id==node,m.financial_reference_node.c.reference_node_type_id==node_type,
            m.financial_reference_node.c.status=='ACTIVE',m.reference_node_scope.c.scope_type=='SHARED_CANONICAL',
            m.reference_node_scope.c.status=='ACTIVE')).one()
        return node
    node=storage.insert_returning(c,m.financial_reference_node,'reference_node_id',reference_node_type_id=node_type,
        internal_code='FXPAIR_'+base+quote,canonical_name=base+'/'+quote+' spot reference — '+quote+' per '+base,is_tradable=False,status='ACTIVE')
    c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='SHARED_CANONICAL',status='ACTIVE'))
    return node


def import_fx(c,bundle,tenant,actor,foundation,operator,*,selected=DEFAULT_CURRENCIES):
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    require_admin(c,tenant,actor);require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    source=c.execute(select(m.source_payload).join(m.integration_source_system).where(m.source_payload.c.tenant_id==tenant,
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],m.integration_source_system.c.tenant_id==tenant,
        m.integration_source_system.c.status=='ACTIVE',m.source_payload.c.external_message_reference==bundle.digest+':fx_rates')).mappings().one()
    if sha256(bundle.files['fx_rates']).hexdigest()!=source['payload_sha256']:raise ValueError('Retained source FX hash differs')
    c.execute(select(m.organisation).where(m.organisation.c.organisation_id==operator,m.organisation.c.status=='ACTIVE')).one()
    points=select_rates(bundle.tables['fx_rates'],selected,source_currency_codes={source_id(r['currency_id']):r['currency'] for r in bundle.tables['currencies']})
    selected=sorted(set(selected))
    first,last=min(p['day'] for p in points),max(p['day'] for p in points)
    now=c.scalar(select(func.clock_timestamp()));today=governance_date()
    if last>today:raise ValueError('Future source FX observations are not supported')
    prefix='RECON_'+foundation['sourceId'].hex+'_FX'
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(prefix.encode()).digest()[:8],'big',signed=True))))
    # Shared pair identities are public dimensional references, not public rates.
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(b'canonical-fx-pair-import').digest()[:8],'big',signed=True))))
    currencies={}
    for code in selected:
        row=c.execute(select(m.currency).where(m.currency.c.currency_code==code)).mappings().one_or_none()
        if not row:
            if code not in NEW_FIAT:raise ValueError('Missing reviewed currency reference: '+code)
            currencies[code]=storage.insert_returning(c,m.currency,'currency_id',currency_code=code,display_name=NEW_FIAT[code],
                currency_kind='FIAT',minor_unit=2,status='ACTIVE')
        elif row['status']!='ACTIVE' or row['currency_kind']!='FIAT':raise ValueError('Active fiat currency required: '+code)
        else:currencies[code]=row['currency_id']
    provider=_put(c,m.data_provider,'data_provider_id',[m.data_provider.c.provider_code==prefix],dict(provider_code=prefix,
        organisation_id=operator,owner_tenant_id=tenant,display_name='Private tenant reconciliation file delivery',status='ACTIVE'))
    product=_put(c,m.provider_product,'provider_product_id',[m.provider_product.c.data_provider_id==provider,m.provider_product.c.product_code=='DAILY_FX_FILE'],
        dict(data_provider_id=provider,product_code='DAILY_FX_FILE',display_name='Owner-supplied date-only FX export',status='ACTIVE'))
    code=prefix+'_'+sha256(document(selected)).hexdigest()[:8]
    new_dataset=c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==code)) is None
    dataset=_put(c,m.dataset,'dataset_id',[m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==code],dict(provider_product_id=product,
        dataset_code=code,display_name=bundle.name+' — imported daily FX ('+str(len(selected))+' currencies)',data_domain='MARKET_DATA',
        coverage_description='Direct supplied cross-rates; quote currency per base unit. Date-only; fixing/publication time and upstream vendor unverified. Personal inspection only; not UK/US fixings.',
        delivery_channel='FILE',valid_from=first,status='ACTIVE'))
    namespace=_put(c,m.external_id_namespace,'external_id_namespace_id',[m.external_id_namespace.c.namespace_code==prefix+'_PAIR'],
        dict(integration_source_system_id=foundation['sourceId'],namespace_code=prefix+'_PAIR',external_object_type='REFERENCE_NODE',valid_from=today,
            description='Direct source FX pair codes, quote per base; no synthetic inverse or triangulation',status='ACTIVE'))
    declaration=('Owner requested local personal import and inspection of the supplied reconciliation FX file. '
        'Recorded actor '+str(actor)+'. Original source '+str(source['source_payload_id'])+'. '
        'Not a provider contract, upstream ownership assertion, valuation-use permission or commercial/redistribution clearance.')
    licence=_put(c,m.data_licence,'data_licence_id',[m.data_licence.c.licence_code==code+'_DECLARATION'],dict(
        licensor_organisation_id=operator,licensee_organisation_id=operator,licence_code=code+'_DECLARATION',
        display_name='Personal local-file use declaration — upstream rights unverified',licence_reference='LOCAL_FILE_OWNER_INSTRUCTION',
        permitted_use_description=declaration,valid_from=today,status='ACTIVE'),allow_create=new_dataset)
    assignment=_put(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',[m.dataset_licence_assignment.c.dataset_id==dataset,
        m.dataset_licence_assignment.c.data_licence_id==licence],dict(dataset_id=dataset,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=today,status='ACTIVE'),allow_create=new_dataset)
    _put(c,m.dataset_access_profile,'dataset_id',[m.dataset_access_profile.c.dataset_id==dataset],dict(dataset_id=dataset,
        licensee_organisation_id=operator,permitted_tenant_id=tenant,external_id_namespace_id=namespace,usage_scope='PERSONAL',
        provider_enabled=True,activation_reference=declaration,status='ACTIVE'),allow_create=new_dataset)
    rights=[]
    for activity in ('ACQUIRE','STORE','DISPLAY'):
        _put(c,m.licence_activity_grant,'grant_id',[m.licence_activity_grant.c.dataset_licence_assignment_id==assignment,m.licence_activity_grant.c.activity==activity],
            dict(dataset_licence_assignment_id=assignment,activity=activity,usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
                evidence_reference=declaration,valid_from=today,status='ACTIVE'),allow_create=new_dataset)
        _put(c,m.dataset_right_requirement,'requirement_id',[m.dataset_right_requirement.c.dataset_id==dataset,m.dataset_right_requirement.c.activity==activity],
            dict(dataset_id=dataset,activity=activity,requirement_code='OWNER_SUPPLIED_LOCAL_FILE_PERSONAL_USE',dataset_licence_assignment_id=assignment),allow_create=new_dataset)
        decision=load_rights(c,dataset,activity,today)
        if not decision.allowed:raise PermissionError('FX import rights: '+decision.reason)
        rights.extend(decision.evidence)
    _put(c,m.tenant_dataset_entitlement,'tenant_dataset_entitlement_id',[m.tenant_dataset_entitlement.c.tenant_id==tenant,
        m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='INTERNAL_REPORTING'],
        dict(tenant_id=tenant,dataset_id=dataset,dataset_licence_assignment_id=assignment,use_purpose='INTERNAL_REPORTING',
            coverage_mode='DATASET',valid_from=today,status='ACTIVE'),allow_create=new_dataset)
    raw=document(dict(originalSourcePayloadId=str(source['source_payload_id']),originalSha256=source['payload_sha256'],
        bundleHash=bundle.digest,selectedCurrencies=selected,rows=[p['originalRow'] for p in points])).decode()
    digest=sha256(raw.encode()).hexdigest();delivery='RECON_FX:'+digest
    prior=storage.previous_delivery(c,dataset,delivery)
    if prior:
        if prior['content_sha256']!=digest:raise ValueError('Retained FX delivery differs')
        return dict(datasetId=dataset,series=prior['report']['series'],observations=prior['report']['accepted'],
            selectedCurrencies=selected,firstDate=str(first),lastDate=str(last),replayed=True)
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset)).mappings().one()
    run,payload=storage.retain_payload(c,namespace_id=namespace,profile=profile,delivery_key=delivery,digest=digest,received_at=now)
    vintage=storage.insert_returning(c,m.market_data_vintage,'market_data_vintage_id',dataset_id=dataset,data_provider_id=provider,
        source_vintage_key=delivery,received_at_utc=now,value_basis='RAW',content_hash=digest,source_payload_id=payload)
    node_type=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='FX_PAIR',m.reference_node_type.c.status=='ACTIVE'))
    measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))
    if not node_type or not measure:raise ValueError('Governed FX pair and rate catalogues required')
    groups=defaultdict(list)
    for p in points:groups[(p['base'],p['quote'])].append(p)
    rows=[];transformations=[]
    for (base,quote),values in sorted(groups.items()):
        node=_pair(c,base,quote,node_type)
        series=storage.insert_returning(c,m.market_data_series,'market_data_series_id',reference_node_id=node,default_dataset_id=dataset,
            series_type='FX_SPOT',value_type='RATE',measure_definition_id=measure,currency_id=currencies[quote],
            expected_frequency_code='BUSINESS_DAILY',coverage_start_date=values[0]['day'],coverage_end_date=values[-1]['day'],
            source_system_id=prefix,is_official=False,status='ACTIVE')
        dimensions={'BASE_CURRENCY':base,'QUOTE_CURRENCY':quote,'VALUE_BASIS':'RAW','SOURCE_FIELD':'RATE',
            'TIMESTAMP_SEMANTICS':TIMING,'SESSION':'UNSPECIFIED_DAILY','DATA_ORIGIN':'OWNER_SUPPLIED_RECONCILIATION_FILE'}
        c.execute(m.market_data_series_dimension.insert(),[dict(market_data_series_id=series,dimension_code=k,dimension_value=v) for k,v in dimensions.items()])
        for point in values:
            rows.append(dict(market_data_series_id=series,dataset_id=dataset,market_data_vintage_id=vintage,source_payload_id=payload,
                acquisition_licence_id=licence,market_date=point['day'],observed_at_utc=datetime.combine(point['day'],time.max,timezone.utc),
                received_at_utc=now,value=Decimal(point['normalization']['value']),value_basis='RAW',quality_status='ACCEPTED',
                source_observation_key=base+'/'+quote+':'+str(point['day'])+':'+point['originalRow'].get('id',''),
                source_payload_reference=str(source['source_payload_id'])))
            if point['normalization']['truncated']:transformations.append(dict(sourceId=point['originalRow'].get('id'),**point['normalization']))
    for offset in range(0,len(rows),1000):c.execute(m.market_data_observation.insert(),rows[offset:offset+1000])
    report=dict(accepted=len(rows),duplicates=0,rejections=[],series=len(groups),selectedCurrencies=selected,
        request=dict(originalSourcePayloadId=str(source['source_payload_id']),start=str(first),end=str(last)),
        timing=TIMING,priceTransforms=transformations,valuationEnabled=False)
    storage.finish_delivery(c,run_id=run,dataset_id=dataset,source_payload_id=payload,delivery_key=delivery,digest=digest,
        raw_payload=raw,received_at=now,evidence=rights,report=report)
    audit(c,actor,tenant,'RECONCILIATION_FX_IMPORTED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
        datasetId=str(dataset),sourcePayloadId=str(source['source_payload_id']),**report))
    return dict(datasetId=dataset,series=len(groups),observations=len(rows),selectedCurrencies=selected,
        firstDate=str(first),lastDate=str(last),replayed=False)
