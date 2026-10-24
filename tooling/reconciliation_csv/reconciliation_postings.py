"""Scoped source-to-native booking adapter, never a direct trade-table loader.

Unmapped/unsupported records are reported explicitly. RESET remains a dated flow,
not an investment position. Every successful row retains original source text.
"""
from datetime import datetime,timezone
from decimal import Decimal,localcontext
from hashlib import sha256
from uuid import UUID
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal


def booking_request(row,node,strategy,counterparty,source,context,properties):
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    if context.kind=='BOND':
        from .reconciliation_bond_postings import bond_booking_request
        return bond_booking_request(row,node,strategy,counterparty,source,context,properties)
    if context.kind not in {'SWAP','ACTIVELY_MANAGED_CERTIFICATE'}:
        raise ValueError('Product requires a separately mapped booking adapter')
    if row['trade_currency']!=context.currency:
        raise ValueError('Source trade currency disagrees with approved quote currency')
    if row.get('active','True')!='True':raise ValueError('Inactive source trade is not an investment booking')
    for field in ('quote_factor','unit_multiplier'):
        if row.get(field) and Decimal(row[field])!=1:
            raise ValueError('Non-unit source factors require explicit mapping')
    if context.convention.quote_factor!=1:
        raise ValueError('Source unit quotations require native divisor one')
    expected='SWAP_VALUE_PER_UNIT' if context.convention.quantity_unit=='UNITS' else 'SWAP_VALUE_PER_NOTIONAL'
    if context.convention.price_basis!=('UNIT_PRICE' if context.kind=='ACTIVELY_MANAGED_CERTIFICATE' else expected):
        raise ValueError('Source and native quotation bases differ')
    quantity=native_decimal(row['quantity']);price=native_decimal(row['price'])
    signed=Decimal(quantity['value'])
    if signed==0:raise ValueError('Truncation would remove the source quantity')
    if context.kind=='ACTIVELY_MANAGED_CERTIFICATE':
        # Native funded consideration is fixed-scale. Preserve the position
        # quantity, then retain the greatest price precision that fits exactly.
        with localcontext() as ctx:
            ctx.prec=100
            for places in range(12,-1,-1):
                candidate=native_decimal(row['price'],decimal_places=places)
                amount=signed.copy_abs()*Decimal(candidate['value'])
                if amount==amount.quantize(Decimal('1e-12')):
                    delta=Decimal(candidate['delta']).copy_abs()
                    if delta>Decimal('1e-9') or (Decimal(row['price']) and delta/Decimal(row['price']).copy_abs()>Decimal('1e-9')):
                        raise ValueError('Native consideration would require material price truncation; explicit source review required')
                    price=candidate
                    price['reason']='MAXIMUM_PRICE_PRECISION_WITH_UNCHANGED_QUANTITY_AND_NATIVE_12DP_CONSIDERATION'
                    break
        if Decimal(row['price'])!=0 and Decimal(price['value'])==0:
            raise ValueError('Native precision would remove the nonzero AMC execution price')
    execution=datetime.fromisoformat(row['trade_datetime_utc'])
    # Export explicitly identifies this column as UTC; do not use host timezone.
    execution=execution.replace(tzinfo=timezone.utc) if execution.tzinfo is None else execution.astimezone(timezone.utc)
    settlement=row.get('settlement_date') or None
    if context.kind=='SWAP':settlement=None
    elif not settlement:raise ValueError('Actual AMC settlement date is required')
    request=ProductBookingRequest.model_validate(dict(instrumentId=str(node),strategyId=str(strategy),
        executionRoute='OTC',side='BUY' if signed>0 else 'SELL',quantity=format(signed.copy_abs(),'f'),
        executionPrice=price['value'],tradeDatetime=execution.isoformat(),settlementDate=settlement,
        counterpartyOrganisationId=str(counterparty),expectedTermsFingerprint=context.terms_fingerprint,
        comment='Private reconciliation import. Original annotations retained in source evidence. '+(row.get('comment') or ''),
        externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(source))],
        properties=properties))
    return request,dict(quantity=quantity,price=price,sourceSettlementDate=row.get('settlement_date'),
        settlementTreatment='NO_SWAP_CASH_OR_PAYMENT_POSTING' if context.kind=='SWAP' else 'SOURCE_ACTUAL_DATE')


def post_positions(c,bundle,tenant,actor,foundation,nodes,counterparties,property_values,*,instrument_ids=None):
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.access_management import audit
    from security_master_schema.strategy_access import require_strategy_action
    from apps.reference_api.booking_controls import authorize_booking
    from apps.reference_api.product_booking import load_context,book
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    require_strategy_action(c,tenant,actor,'TRADE_READ',foundation['strategyId'])
    if bundle.digest!=foundation['bundleHash']:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':trades'))
    if not payload:raise ValueError('Owned retained trade source required')
    lock=int.from_bytes(sha256(('reconciliation-trades:'+str(foundation['sourceId'])).encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    definitions=c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,
        m.trade_property_definition.c.status=='ACTIVE')).mappings().all()
    by_code={d['code']:d for d in definitions}
    if set(property_values)-set(by_code):raise ValueError('Unknown tenant property configuration')
    properties=[dict(definitionId=str(by_code[k]['definition_id']),value=v) for k,v in property_values.items()]
    missing=[d['code'] for d in definitions if d['required'] and d['code'] not in property_values]
    if missing:raise ValueError('Required source property mapping missing: '+','.join(missing))
    result=dict(booked=0,replayed=0,failed=0,rows=[],datedResetFlowsNotPosted=len(bundle.flows))
    for row in sorted(bundle.positions,key=lambda r:(r['trade_datetime_utc'],r['trade_id'])):
        if instrument_ids is not None and source_id(row['instrument_id']) not in instrument_ids:continue
        try:
            with c.begin_nested():
                digest=sha256(document(row)).hexdigest()
                old=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
                    m.access_audit_event.c.action=='RECONCILIATION_TRADE_BOOKED',
                    m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
                    m.access_audit_event.c.details['sourceTradeId'].as_string()==row['trade_id'])).scalars().all()
                if old:
                    if len(old)!=1 or old[0]['sourceRowHash']!=digest or old[0]['strategyId']!=str(foundation['strategyId']):
                        raise ValueError('Source trade identity already has different economics or strategy')
                    trade=c.execute(select(m.trade).join(m.strategy).where(m.trade.c.trade_id==UUID(old[0]['tradeId']),
                        m.strategy.c.tenant_id==tenant,m.trade.c.strategy_id==foundation['strategyId'])).mappings().one()
                    if trade['lifecycle_status']!='BOOKED':raise ValueError('Imported trade is no longer booked; explicit correction required')
                    result['replayed']+=1
                    result['rows'].append(dict(sourceTradeId=row['trade_id'],tradeId=old[0]['tradeId'],status='REPLAYED'))
                    continue
                identifier=source_id(row['instrument_id']);company=source_id(row.get('counterparty_id'))
                if identifier not in nodes:raise ValueError('Instrument/booking adapter not mapped: '+identifier)
                if company not in counterparties:raise ValueError('Source counterparty not mapped: '+company)
                node=nodes[identifier]
                # Never adopt a shared/other-tenant node through an arbitrary map.
                c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
                    m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',
                    m.reference_node_scope.c.status=='ACTIVE')).one()
                context=load_context(c,tenant,node,as_of=datetime.fromisoformat(row['trade_datetime_utc']).date())
                if not context.booking_eligible:raise ValueError(context.ineligibility_message or 'Product not ready')
                request,precision=booking_request(row,node,foundation['strategyId'],counterparties[company],foundation['sourceId'],context,properties)
                key='recon-trade:'+sha256(document(dict(sourceId=str(foundation['sourceId']),tradeId=row['trade_id']))).hexdigest()
                detail=book(c,tenant,actor,request,key,context.kind,'reconciliation-import')
                trade_id=detail.data.trade.trade_id
                audit(c,actor,tenant,'RECONCILIATION_TRADE_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
                    strategyId=str(foundation['strategyId']),sourcePayloadId=str(payload),sourceTradeId=row['trade_id'],
                    sourceRowHash=digest,tradeId=str(trade_id),originalRow=dict(row),normalization=precision,
                    mappedProperties=property_values,propertyAssumptions='Operator-supplied reconciliation configuration; not exported source facts'))
                result['booked']+=1
                result['rows'].append(dict(sourceTradeId=row['trade_id'],tradeId=str(trade_id),status='BOOKED'))
        except ValueError as exc:
            result['failed']+=1
            result['rows'].append(dict(sourceTradeId=row['trade_id'],sourceInstrumentId=row['instrument_id'],status='NOT_POSTED',reason=str(exc)))
    return result


def prepare_position_metadata(c,bundle,tenant,actor,foundation,*,product_nodes=None):
    """Configure this private reconciliation fixture through existing approvals.

    Does not rewrite instrument definitions or historical booked evidence. Unknown
    company IDs get unverified operational placeholders, never fabricated LEIs.
    """
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_confirmed_company
    from apps.reference_api.tenant_organisations import organisation_detail,save_organisation
    from apps.reference_api.product_booking import CONVENTION,submit_proposal,decide_proposal
    from apps.reference_api.product_booking_contracts import ConventionProposalRequest
    from uuid import uuid4
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'TRADE_WRITE',foundation['strategyId'])
    source=c.execute(select(m.integration_source_system).where(m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).mappings().one()
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Bundle differs')
    nodes={}
    for action,key in ([] if product_nodes is not None else [('RECONCILIATION_PRODUCTS_SEEDED','swaps'),('RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED','certificates')]):
        details=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action==action,m.access_audit_event.c.details['sourceId'].as_string()==str(source['integration_source_system_id']),
            m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest).order_by(m.access_audit_event.c.recorded_at_utc.desc())).scalars().all()
        for item in details:
            for identifier,value in item.get(key,{}).items():
                if identifier in nodes and nodes[identifier]!=UUID(value):raise ValueError('Conflicting source node mappings')
                nodes[identifier]=UUID(value)
    if product_nodes is not None:
        nodes=dict(product_nodes)
        for node in nodes.values():
            c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
                m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',
                m.reference_node_scope.c.status=='ACTIVE')).one()
    if not nodes:raise ValueError('No audited source product mappings')
    parties={}
    for company in sorted({source_id(r.get('counterparty_id')) for r in bundle.positions if source_id(r['instrument_id']) in nodes}):
        if not company:raise ValueError('Missing source counterparty')
        organisation=apply_confirmed_company(c,bundle,tenant,actor,foundation,company,
            'Northern Trust' if bundle.name=='FCAGF' and company=='21' else 'Unverified source company '+company,
            confirmed=bundle.name=='FCAGF' and company=='21')
        detail=organisation_detail(c,tenant,actor,organisation)
        # Preserve all existing selections; add only this import's source parties.
        if detail['policies']['COUNTERPARTY']['mode']=='CURATED' and not detail['roles']['COUNTERPARTY']:
            save_organisation(c,tenant,actor,organisation,dict(expectedVersion=detail['versionNo'],
                expectedRoleVersions={r:p['versionNo'] for r,p in detail['policies'].items()},roles={'COUNTERPARTY':True},
                label=detail['label'],internalCode=detail['internalCode'],notes=detail['notes'],
                reason='Owner-authorized reconciliation source counterparty; unverified placeholders remain labelled.',idempotencyKey=str(uuid4())))
        parties[company]=organisation
    for identifier,node in nodes.items():
        quantities=[Decimal(r['quantity']) for r in bundle.positions if source_id(r['instrument_id'])==identifier]
        if not any(q!=q.to_integral_value() for q in quantities):continue
        stored=c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==node)
            .order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().one()
        cv=CONVENTION.validate_json(stored['convention_payload'])
        if cv.kind=='BOND':continue  # Preserve governed penny-nominal bond increments.
        if cv.quantity_minimum==Decimal('0.000000000001') and cv.quantity_increment==Decimal('0.000000000001'):continue
        data=cv.model_dump(mode='json',by_alias=True)
        data.update(quantityMinimum='0.000000000001',quantityIncrement='0.000000000001',
            sourceReference='MOCKUP reconciliation dealing precision; owner-authorized fractional source units, not independently confirmed contractual minima. Bundle '+bundle.digest)
        request=ConventionProposalRequest(instrumentId=node,convention=data,idempotencyKey='recon-fractional:'+bundle.digest+':'+identifier)
        proposal=submit_proposal(c,tenant,actor,request)
        if proposal.status=='PENDING':proposal=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED',
            'Reconciliation-only fractional dealing configuration. Existing product validators and historical evidence unchanged.')
        if proposal.status!='APPROVED':raise ValueError('Fractional convention not approved')
        audit(c,actor,tenant,'RECONCILIATION_FRACTIONAL_CONVENTION',dict(sourceId=str(foundation['sourceId']),bundleHash=bundle.digest,
            instrumentId=str(node),proposalId=str(proposal.proposal_id),sourceInstrumentId=identifier,mockup=True))
    return nodes,parties
