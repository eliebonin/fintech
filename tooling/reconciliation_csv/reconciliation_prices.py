"""Private dated source quotes; explicit native mappings and measurement units.

No provider acquisition, invented cutoffs, policy edits or valuation-use grants.
"""
from collections import defaultdict
from datetime import date,datetime,time,timezone
from decimal import Decimal
from hashlib import sha256
from uuid import UUID
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from security_master_schema.access_management import audit
from tooling.reconciliation_csv.reconciliation import source_id,document
from tooling.reconciliation_csv.reconciliation_precision import native_decimal
from market_data import storage
from .reconciliation_fx import _put,TIMING
from market_data.history import require_admin
from market_data.rights import load_rights


def normalize_prices(rows,instruments,*,amc_ids=()):
    points=[];seen=set();amcs=set(amc_ids)
    for row in rows:
        identifier=source_id(row['instrument_id']);day=date.fromisoformat(row['date'])
        if (identifier,day) in seen:raise ValueError('Duplicate source instrument/date price')
        seen.add((identifier,day));item=instruments[identifier];kind=item['instrument_type'];quote=item['price_type']
        dimensions={};series_type='CLOSE';value_type='PRICE';measure='PRICE';scale='1'
        if kind=='BOND':
            if quote!='notional':raise ValueError('Confirmed nominal bond quote required')
            scale='100';dimensions.update(BOND_PRICE_TYPE='CLEAN',PRICE_BASIS='PCT_OF_PAR',QUOTE_FACTOR='100',QUANTITY_UNIT='NOMINAL')
        elif identifier in amcs:
            if quote!='unit':raise ValueError('Confirmed unit AMC quote required')
            dimensions.update(AMC_PRICE_BASIS='UNIT_PRICE',QUOTE_FACTOR='1',QUANTITY_UNIT='UNITS')
        elif kind=='DIVER OTC':
            if quote not in ('unit','unitlev','notional'):raise ValueError('Unsupported swap quote basis')
            nominal=quote=='notional';series_type='MARK'
            dimensions.update(SWAP_PRICE_BASIS='WHOLE_SWAP_MTM_PER_NOTIONAL' if nominal else 'WHOLE_SWAP_MTM_PER_UNIT',
                QUOTE_FACTOR='1',QUANTITY_UNIT='NOMINAL' if nominal else 'UNITS',LEVERAGE_TREATMENT='SOURCE_WHOLE_SWAP_MARK_NO_EXTRA_MULTIPLICATION')
        elif kind=='VANILLA':
            if identifier!='20265' or quote!='unit':raise ValueError('Confirmed standard option quote required')
            dimensions.update(OPTION_PRICE_BASIS='PREMIUM_POINTS',PREMIUM_MULTIPLIER='100',QUOTE_FACTOR='1',QUANTITY_UNIT='CONTRACTS')
        elif kind=='FXFWD':
            if identifier not in ('20764','21105'):raise ValueError('Confirmed forward orientation required')
            series_type='FORWARD_RATE';value_type='RATE';measure='FX_RATE'
            dimensions.update(BASE_CURRENCY='USD',QUOTE_CURRENCY='GBP',QUOTE_CONVENTION='GBP_PER_USD',FORWARD_RATE_KIND='CONTRACT_OUTRIGHT_RATE')
        elif kind=='INDEX':
            if identifier in ('1396','1048'):
                series_type='RATE';value_type='RATE';measure='RATE';dimensions['RATE_UNIT']='PERCENT_ANNUAL'
            else:series_type='INDEX_LEVEL';value_type='INDEX_LEVEL';measure='INDEX_LEVEL'
        else:raise ValueError('Unsupported source price product: '+kind)
        normalized=native_decimal(row['price'],scale=scale)
        if Decimal(normalized['value'])<0 and kind not in ('DIVER OTC','INDEX'):raise ValueError('Unexpected negative non-swap price')
        points.append(dict(sourceId=identifier,day=day,currency=item['currency'],seriesType=series_type,valueType=value_type,
            measure=measure,dimensions=dimensions,normalization=normalized,originalRow=dict(row)))
    if not points:raise ValueError('No source price observations')
    return sorted(points,key=lambda p:(p['sourceId'],p['day']))


def _mappings(c,bundle,tenant,foundation,points):
    events=c.execute(select(m.access_audit_event.c.action,m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action.in_(['RECONCILIATION_PRODUCTS_SEEDED','RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED',
            'RECONCILIATION_BOND_BOOKING_PREPARED','RECONCILIATION_FORWARD_BOOKED','RECONCILIATION_OPTION_BOOKED']),
        m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
        m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest,
        m.access_audit_event.c.details['strategyId'].as_string()==str(foundation['strategyId']))).mappings().all()
    nodes={}
    def add(key,value):
        key=source_id(key);value=UUID(value)
        if key in nodes and nodes[key]!=value:raise ValueError('Conflicting native price mapping: '+key)
        nodes[key]=value
    for event in events:
        data=event['details'];action=event['action']
        if action=='RECONCILIATION_PRODUCTS_SEEDED':
            for key in ('references','swaps'):
                for identifier,node in data[key].items():add(identifier,node)
        elif action=='RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED':
            for identifier,node in data['certificates'].items():add(identifier,node)
            # Never use its superseded multiplier-one option mapping.
        else:add(data['sourceInstrumentId'],data['instrumentId'])
    identifiers={p['sourceId'] for p in points}
    for identifier in identifiers:
        if identifier not in nodes:raise ValueError('Missing audited '+('standard option' if identifier=='20265' else 'native')+' price mapping: '+identifier)
    selected={k:v for k,v in nodes.items() if k in identifiers}
    visible=set(c.scalars(select(m.financial_reference_node.c.reference_node_id).join(m.reference_node_scope,
        m.reference_node_scope.c.reference_node_id==m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.reference_node_id.in_(set(selected.values())),m.financial_reference_node.c.status=='ACTIVE',
            m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')))
    if visible!=set(selected.values()):raise ValueError('Every price target must be active and tenant-private')
    native={r.instrument_node_id:r for r in c.execute(select(m.instrument.c.instrument_node_id,m.instrument_type.c.type_code,m.currency.c.currency_code)
        .join(m.instrument_type,m.instrument_type.c.instrument_type_id==m.instrument.c.instrument_type_id)
        .join(m.currency,m.currency.c.currency_id==m.instrument.c.base_currency_id).where(m.instrument.c.instrument_node_id.in_(visible)))}
    forwards={r.instrument_node_id:r for r in c.execute(select(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id.in_(visible)))}
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    for p in {p['sourceId']:p for p in points}.values():
        node=selected[p['sourceId']]
        if p['seriesType']=='FORWARD_RATE':
            f=forwards.get(node)
            if not f or f.base_currency_id!=currencies['USD'] or f.quote_currency_id!=currencies['GBP'] or p['currency']!='GBP':
                raise ValueError('Forward rate must retain approved GBP-per-USD orientation')
        if node in native:
            target=native[node]
            if p['seriesType']!='FORWARD_RATE' and target.currency_code!=p['currency']:raise ValueError('Source/native quote currency differs')
            expected={'BOND_PRICE_TYPE':'BOND','AMC_PRICE_BASIS':'ACTIVELY_MANAGED_CERTIFICATE','SWAP_PRICE_BASIS':'SWAP','OPTION_PRICE_BASIS':'OPTION'}
            if any(k in p['dimensions'] and target.type_code!=kind for k,kind in expected.items()):raise ValueError('Source/native product differs')
    return selected


def import_prices(c,bundle,tenant,actor,foundation,operator):
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    require_admin(c,tenant,actor);require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    source=c.execute(select(m.source_payload).join(m.integration_source_system).where(m.source_payload.c.tenant_id==tenant,
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],m.integration_source_system.c.tenant_id==tenant,
        m.integration_source_system.c.status=='ACTIVE',m.source_payload.c.external_message_reference==bundle.digest+':prices')).mappings().one()
    if sha256(bundle.files['prices']).hexdigest()!=source['payload_sha256']:raise ValueError('Retained source price hash differs')
    c.execute(select(m.organisation).where(m.organisation.c.organisation_id==operator,m.organisation.c.status=='ACTIVE')).one()
    instruments={source_id(i['instrument_id']):i for i in bundle.tables['all_instruments']}
    points=normalize_prices(bundle.tables['prices'],instruments,amc_ids=bundle.manifest['amcSourceIds'])
    nodes=_mappings(c,bundle,tenant,foundation,points)
    now=c.scalar(select(func.clock_timestamp()));today=governance_date()
    first,last=min(p['day'] for p in points),max(p['day'] for p in points)
    if last>today:raise ValueError('Future source prices are not supported')
    prefix='RECON_'+foundation['sourceId'].hex+'_PRICES'
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(prefix.encode()).digest()[:8],'big',signed=True))))
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    provider=_put(c,m.data_provider,'data_provider_id',[m.data_provider.c.provider_code==prefix],dict(provider_code=prefix,
        organisation_id=operator,owner_tenant_id=tenant,display_name='Private tenant reconciliation price delivery',status='ACTIVE'))
    product=_put(c,m.provider_product,'provider_product_id',[m.provider_product.c.data_provider_id==provider,m.provider_product.c.product_code=='DAILY_PRICE_FILE'],
        dict(data_provider_id=provider,product_code='DAILY_PRICE_FILE',display_name='Owner-supplied date-only price export',status='ACTIVE'))
    new=c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==prefix)) is None
    dataset=_put(c,m.dataset,'dataset_id',[m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==prefix],dict(provider_product_id=product,
        dataset_code=prefix,display_name=bundle.name+' — imported daily market prices',data_domain='MARKET_DATA',delivery_channel='FILE',
        coverage_description='Owner-supplied dated quotes with explicit bond/AMC/swap/option/rate units. Source time, upstream vendor and official status unverified. Personal inspection only.',
        valid_from=first,status='ACTIVE'))
    namespace=_put(c,m.external_id_namespace,'external_id_namespace_id',[m.external_id_namespace.c.namespace_code==prefix],dict(
        integration_source_system_id=foundation['sourceId'],namespace_code=prefix,external_object_type='REFERENCE_NODE',valid_from=today,
        description='Audited private native reference IDs, never a source numeric-ID lookup',status='ACTIVE'))
    declaration='Owner requested local personal import/inspection of supplied prices. Actor '+str(actor)+', original receipt '+str(source['source_payload_id'])+'. Not an upstream ownership assertion, provider contract, valuation-use or redistribution clearance.'
    licence=_put(c,m.data_licence,'data_licence_id',[m.data_licence.c.licence_code==prefix+'_DECLARATION'],dict(licensor_organisation_id=operator,
        licensee_organisation_id=operator,licence_code=prefix+'_DECLARATION',display_name='Personal local-price-file declaration — upstream rights unverified',
        licence_reference='LOCAL_FILE_OWNER_INSTRUCTION',permitted_use_description=declaration,valid_from=today,status='ACTIVE'),allow_create=new)
    assignment=_put(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',[m.dataset_licence_assignment.c.dataset_id==dataset,m.dataset_licence_assignment.c.data_licence_id==licence],
        dict(dataset_id=dataset,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=today,status='ACTIVE'),allow_create=new)
    _put(c,m.dataset_access_profile,'dataset_id',[m.dataset_access_profile.c.dataset_id==dataset],dict(dataset_id=dataset,licensee_organisation_id=operator,
        permitted_tenant_id=tenant,external_id_namespace_id=namespace,usage_scope='PERSONAL',provider_enabled=True,activation_reference=declaration,status='ACTIVE'),allow_create=new)
    evidence=[]
    for activity in ('ACQUIRE','STORE','DISPLAY'):
        _put(c,m.licence_activity_grant,'grant_id',[m.licence_activity_grant.c.dataset_licence_assignment_id==assignment,m.licence_activity_grant.c.activity==activity],
            dict(dataset_licence_assignment_id=assignment,activity=activity,usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',evidence_reference=declaration,valid_from=today,status='ACTIVE'),allow_create=new)
        _put(c,m.dataset_right_requirement,'requirement_id',[m.dataset_right_requirement.c.dataset_id==dataset,m.dataset_right_requirement.c.activity==activity],
            dict(dataset_id=dataset,activity=activity,requirement_code='OWNER_SUPPLIED_LOCAL_FILE_PERSONAL_USE',dataset_licence_assignment_id=assignment),allow_create=new)
        decision=load_rights(c,dataset,activity,today)
        if not decision.allowed:raise PermissionError('Price import rights: '+decision.reason)
        evidence.extend(decision.evidence)
    _put(c,m.tenant_dataset_entitlement,'tenant_dataset_entitlement_id',[m.tenant_dataset_entitlement.c.tenant_id==tenant,m.tenant_dataset_entitlement.c.dataset_id==dataset,
        m.tenant_dataset_entitlement.c.use_purpose=='INTERNAL_REPORTING'],dict(tenant_id=tenant,dataset_id=dataset,dataset_licence_assignment_id=assignment,
            use_purpose='INTERNAL_REPORTING',coverage_mode='DATASET',valid_from=today,status='ACTIVE'),allow_create=new)
    raw=document(dict(bundleHash=bundle.digest,originalSourcePayloadId=str(source['source_payload_id']),originalSha256=source['payload_sha256'],
        nativeMappings={k:str(v) for k,v in nodes.items()},rows=[p['originalRow'] for p in points])).decode()
    digest=sha256(raw.encode()).hexdigest();delivery='RECON_PRICES:'+digest
    prior=storage.previous_delivery(c,dataset,delivery)
    if prior:
        if prior['content_sha256']!=digest:raise ValueError('Retained price delivery differs')
        return dict(datasetId=dataset,series=prior['report']['series'],observations=prior['report']['accepted'],firstDate=str(first),lastDate=str(last),replayed=True)
    # A changed target mapping is not a new silent delivery of the same source file.
    if c.scalar(select(func.count()).select_from(m.market_data_ingestion_run).where(m.market_data_ingestion_run.c.dataset_id==dataset)):
        raise ValueError('Existing source price delivery/mapping changed; explicit correction required')
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset)).mappings().one()
    run,payload=storage.retain_payload(c,namespace_id=namespace,profile=profile,delivery_key=delivery,digest=digest,received_at=now)
    vintage=storage.insert_returning(c,m.market_data_vintage,'market_data_vintage_id',dataset_id=dataset,data_provider_id=provider,
        source_vintage_key=delivery,received_at_utc=now,value_basis='RAW',content_hash=digest,source_payload_id=payload)
    measures=dict(c.execute(select(m.series_measure_definition.c.measure_code,m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.status=='ACTIVE')).all())
    groups=defaultdict(list)
    for p in points:groups[p['sourceId']].append(p)
    rows=[];transforms=[]
    for identifier,values in groups.items():
        p=values[0];series=storage.insert_returning(c,m.market_data_series,'market_data_series_id',reference_node_id=nodes[identifier],default_dataset_id=dataset,
            series_type=p['seriesType'],value_type=p['valueType'],measure_definition_id=measures[p['measure']],currency_id=currencies[p['currency']],
            expected_frequency_code='BUSINESS_DAILY',coverage_start_date=values[0]['day'],coverage_end_date=values[-1]['day'],source_system_id=prefix,is_official=False,status='ACTIVE')
        dimensions=dict(p['dimensions'],SOURCE_INSTRUMENT_ID=identifier,SOURCE_FIELD='PRICE',VALUE_BASIS='RAW',
            TIMESTAMP_SEMANTICS=TIMING,SESSION='UNSPECIFIED_DAILY',DATA_ORIGIN='OWNER_SUPPLIED_RECONCILIATION_FILE')
        c.execute(m.market_data_series_dimension.insert(),[dict(market_data_series_id=series,dimension_code=k,dimension_value=v) for k,v in dimensions.items()])
        for point in values:
            rows.append(dict(market_data_series_id=series,dataset_id=dataset,market_data_vintage_id=vintage,source_payload_id=payload,acquisition_licence_id=licence,
                market_date=point['day'],observed_at_utc=datetime.combine(point['day'],time.max,timezone.utc),received_at_utc=now,
                value=Decimal(point['normalization']['value']),value_basis='RAW',quality_status='ACCEPTED',
                source_observation_key=identifier+':'+str(point['day'])+':'+point['originalRow']['id'],source_payload_reference=str(source['source_payload_id'])))
            if point['normalization']['scale']!='1' or point['normalization']['truncated']:
                transforms.append(dict(sourceId=point['originalRow']['id'],sourceInstrumentId=identifier,**point['normalization']))
    for offset in range(0,len(rows),1000):c.execute(m.market_data_observation.insert(),rows[offset:offset+1000])
    report=dict(accepted=len(rows),duplicates=0,rejections=[],series=len(groups),priceTransforms=transforms,timing=TIMING,valuationEnabled=False,
        nativeMappings={k:str(v) for k,v in nodes.items()},request=dict(originalSourcePayloadId=str(source['source_payload_id']),start=str(first),end=str(last)))
    storage.finish_delivery(c,run_id=run,dataset_id=dataset,source_payload_id=payload,delivery_key=delivery,digest=digest,
        raw_payload=raw,received_at=now,evidence=evidence,report=report)
    audit(c,actor,tenant,'RECONCILIATION_PRICES_IMPORTED',dict(sourceId=str(foundation['sourceId']),bundleHash=bundle.digest,datasetId=str(dataset),**report))
    return dict(datasetId=dataset,series=len(groups),observations=len(rows),firstDate=str(first),lastDate=str(last),replayed=False)
