"""Private UK bond reconciliation: retained terms enrichment and native booking.

No direct trade writes, automatic cash movements, coupon income or price loading.
This local operator is not a general bond-amendment API.
"""
from datetime import date,datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.access_management import audit
from security_master_schema.reference_authority import require_reference_action
from security_master_schema.strategy_access import require_strategy_action
from .reconciliation import source_id
from .reconciliation_precision import native_decimal

SOURCES=['https://www.dmo.gov.uk/responsibilities/gilt-market/about-gilts/',
         'https://dmo.gov.uk/responsibilities/money-markets/about-treasury-bills/']


def bond_booking_request(row,node,strategy,counterparty,source,context,properties):
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    cv=context.convention
    if context.kind!='BOND' or cv.quantity_unit!='NOMINAL' or cv.price_basis!='PCT_OF_PAR' or cv.quote_factor!=100:
        raise ValueError('Approved nominal percentage bond convention required')
    if row['trade_currency']!=context.currency:raise ValueError('Bond quote currency differs')
    if row.get('active','True')!='True' or row.get('price_type')!='notional':raise ValueError('Active source nominal booking required')
    for key in ('par_value','denomination','quote_factor','unit_multiplier'):
        if not row.get(key) or Decimal(row[key])!=1:raise ValueError('Unsupported source bond sizing: '+key)
    quantity=native_decimal(row['quantity']);price=native_decimal(row['price'],scale='100')
    signed=Decimal(quantity['value'])
    if not signed or price['exactConvertedValue'].startswith('-'):raise ValueError('Nonzero nominal and nonnegative clean price required')
    raw_accrual=row.get('accrued_interests','')
    if raw_accrual:
        accrual=native_decimal(raw_accrual)
        # Source is a signed cash flow. Native accrued adjusts positive-sized
        # consideration before the side determines PAY/RECEIVE. Preserve ex-div signs.
        amount=Decimal(accrual['value'])
        if signed>0:amount=amount.copy_negate()
        accrual.update(basis='SOURCE_CASH_FLOW_TO_SIDE_RELATIVE_CONSIDERATION',nativeValue=format(amount,'f'))
    elif context.coupon_type=='ZERO':
        amount=Decimal(0);accrual=dict(sourceValue=raw_accrual,basis='ZERO_COUPON_TERMS',nativeValue='0')
    else:raise ValueError('Fixed-coupon source accrued interest is required')
    if not row.get('settlement_date'):raise ValueError('Source actual settlement date required')
    execution=datetime.fromisoformat(row['trade_datetime_utc'])
    if execution.tzinfo is None:execution=execution.replace(tzinfo=timezone.utc)
    evidence='Owner confirmed CLEAN fraction-of-par quotes; native price is source x100. Nominal unchanged. Source settlement retained; accrued cash-flow sign translated separately.'
    request=ProductBookingRequest.model_validate(dict(instrumentId=str(node),strategyId=str(strategy),executionRoute='OTC',
        side='BUY' if signed>0 else 'SELL',quantity=format(signed.copy_abs(),'f'),executionPrice=price['value'],
        tradeDatetime=execution.isoformat(),settlementDate=row['settlement_date'],priceType='CLEAN',
        accruedInterestAmount=format(amount,'f'),settlementEvidence=evidence,counterpartyOrganisationId=str(counterparty),
        expectedTermsFingerprint=context.terms_fingerprint,comment='Private reconciliation bond import. '+(row.get('comment') or ''),
        externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(source))],properties=properties))
    return request,dict(quantity=quantity,price=price,accrual=accrual,sourceSettlementDate=row['settlement_date'],
        quotation='OWNER_CONFIRMED_CLEAN',settlementTreatment='SOURCE_ACTUAL_DATE_NO_CASH_MOVEMENT')


def _snapshot(row):
    return json.loads(json.dumps(dict(row),default=str))


def prepare_bond_nodes(c,bundle,tenant,actor,foundation):
    """Complete only approved, source-bound, private unbooked UK plain bonds.

    Append terms/definition versions; retain earlier values and original proposals.
    Receipt hashes, source scope, steward authority and drift checks precede replay.
    """
    from apps.reference_api.booking_controls import authorize_booking
    from apps.reference_api.product_booking import submit_proposal,decide_proposal,lock_booking_currency
    from apps.reference_api.product_booking_contracts import ConventionProposalRequest
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    require_reference_action(c,tenant,actor,'REFERENCE_PROPOSE')
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    source=c.execute(select(m.integration_source_system).where(m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).mappings().one()
    payloads={}
    for kind in ('bonds','trades'):
        p=c.execute(select(m.source_payload).where(m.source_payload.c.integration_source_system_id==source['integration_source_system_id'],
            m.source_payload.c.tenant_id==tenant,m.source_payload.c.external_message_reference==bundle.digest+':'+kind)).mappings().one()
        if p['payload_sha256']!=sha256(bundle.files[kind]).hexdigest():raise ValueError('Retained source hash differs')
        payloads[kind]=p['source_payload_id']
    lock=int.from_bytes(sha256(('reconciliation-bonds:'+str(foundation['sourceId'])).encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    events=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action.in_(['RECONCILIATION_BOND_APPROVED','RECONCILIATION_GILT_REVIEW_APPLIED']),
        m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest,
        m.access_audit_event.c.details['strategyId'].as_string()==str(foundation['strategyId']))).scalars().all()
    nodes={}
    for bond in bundle.bonds:
        identifier=source_id(bond['instrument_id'])
        rows=[r for r in bundle.positions if source_id(r['instrument_id'])==identifier]
        if not rows:continue
        if bond['crncy']!='GBP' or not bond['id_isin'].startswith('GB') or bond.get('px_dirty_clean')!='CLEAN' or Decimal(bond.get('par_amt') or '0')!=Decimal('.01'):
            raise ValueError('Reviewed UK penny-nominal/CLEAN scope required: '+identifier)
        candidates=[e for e in events if e['sourceId']==identifier]
        if len(candidates)!=1:raise ValueError('Exactly one audited approved source bond required: '+identifier)
        approved=candidates[0];node=UUID(approved['instrumentId']);nodes[identifier]=node
        c.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.reference_data_proposal_id==UUID(approved['proposalId']),
            m.reference_data_proposal.c.tenant_id==tenant,m.reference_data_proposal.c.source_system_id==foundation['sourceId'],
            m.reference_data_proposal.c.reference_node_id==node,m.reference_data_proposal.c.status=='APPROVED')).one()
        c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
            m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.status=='ACTIVE')).one()
        lock_booking_currency(c,node)
        instrument=c.execute(select(m.instrument).where(m.instrument.c.instrument_node_id==node).with_for_update()).mappings().one()
        definition=c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==node,
            m.instrument_definition_version.c.is_current,m.instrument_definition_version.c.status=='APPROVED').with_for_update()).mappings().one()
        terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==node,m.bond_terms.c.is_current).with_for_update()).mappings().one()
        if any(definition[key]!=instrument[key] for key in ('effective_from','effective_to','base_currency_id','issuer_organisation_id','instrument_type_id')):
            raise ValueError('Instrument changed from approved definition')
        existing=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action=='RECONCILIATION_BOND_BOOKING_PREPARED',
            m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
            m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest,
            m.access_audit_event.c.details['instrumentId'].as_string()==str(node))).scalars().all()
        if existing:
            if len(existing)!=1 or existing[0]['termsAfter']!=_snapshot(terms) or existing[0]['definitionAfter']!=_snapshot(definition):
                raise ValueError('Prepared bond terms or definition changed; explicit review required')
            current=c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==node)
                .order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().one()
            if existing[0]['conventionAfter']!=_snapshot(current):raise ValueError('Prepared bond convention changed; explicit review required')
            continue
        if c.scalar(select(func.count()).select_from(m.trade).where(or_(m.trade.c.trade_subject_reference_node_id==node,
            m.trade.c.reference_instrument_node_id==node))):
            raise ValueError('Cannot enrich already booked bond through reconciliation preparation')
        dates=c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id==node)).mappings().one()
        first=min(datetime.fromisoformat(r['trade_datetime_utc']).date() for r in rows)
        start=min(instrument['effective_from'],first)
        if any(not r.get('settlement_date') or date.fromisoformat(r['settlement_date'])<dates['issue_date'] for r in rows):
            raise ValueError('Bond settlement precedes actual issue date')
        if terms['par_amount'] is not None and terms['par_amount']!=Decimal('.01'):raise ValueError('Conflicting approved par denomination')
        if terms['coupon_type'] not in {'ZERO','FIXED'} or terms['redemption_amount_per_par']!=100:raise ValueError('Plain at-par redemption required')
        before=dict(terms=_snapshot(terms),definition=_snapshot(definition))
        # Retrospective completion of previously unbooked definitions, not a new
        # economic issuance. Superseded terms and request payloads remain retained.
        new_terms=dict(terms);new_terms.pop('bond_terms_id')
        new_terms.update(par_amount=Decimal('.01'),effective_from=start,sequence_no=terms['sequence_no']+1)
        c.execute(m.bond_terms.update().where(m.bond_terms.c.bond_terms_id==terms['bond_terms_id']).values(is_current=False))
        terms=c.execute(m.bond_terms.insert().values(**new_terms).returning(m.bond_terms)).mappings().one()
        if start!=instrument['effective_from']:
            c.execute(m.instrument_definition_version.update().where(m.instrument_definition_version.c.instrument_definition_version_id==definition['instrument_definition_version_id']).values(is_current=False,status='SUPERSEDED'))
            fields=dict(definition);fields.pop('instrument_definition_version_id')
            fields.update(sequence_no=definition['sequence_no']+1,effective_from=start,source_payload_id=payloads['trades'],
                approved_by_user_account_id=actor,approved_at_utc=c.scalar(select(func.now())))
            definition=c.execute(m.instrument_definition_version.insert().values(**fields).returning(m.instrument_definition_version)).mappings().one()
            c.execute(m.instrument.update().where(m.instrument.c.instrument_node_id==node).values(effective_from=start,sequence_no=definition['sequence_no']))
        convention=dict(kind='BOND',effectiveFrom=str(start),priceCurrencyId=str(instrument['base_currency_id']),quoteFactor='100',
            sourceReference='Owner-confirmed CLEAN nominal source. DMO penny transfer units; source par_amt=0.01. '+SOURCES[0],
            quantityUnit='NOMINAL',priceBasis='PCT_OF_PAR',principalBasis='UNADJUSTED_NOMINAL',quantityMinimum='.01',quantityIncrement='.01',
            accrual='MANUAL_CONFIRMATION',otcAllowed=True)
        req=ConventionProposalRequest(instrumentId=node,convention=convention,idempotencyKey='recon-bond-convention:'+bundle.digest+':'+identifier)
        proposal=submit_proposal(c,tenant,actor,req)
        if proposal.status=='PENDING':proposal=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Owner-authorized source bond reconciliation; CLEAN percentage quotes, nominal quantities, penny transfer increments; source settlements retained.')
        if proposal.status!='APPROVED':raise ValueError('Bond convention not approved')
        current=c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==node)
            .order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().one()
        audit(c,actor,tenant,'RECONCILIATION_BOND_BOOKING_PREPARED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
            sourceInstrumentId=identifier,instrumentId=str(node),strategyId=str(foundation['strategyId']),before=before,
            termsAfter=_snapshot(terms),definitionAfter=_snapshot(definition),conventionAfter=_snapshot(current),
            originalBondRow=bond,sourcePayloadIds={k:str(v) for k,v in payloads.items()},reviewedOn='2026-10-23',sources=SOURCES,
            recognition='Historical definition extended only to first evidenced execution; actual issue date unchanged; settlement cannot precede issue'))
    return nodes


def post_bonds(c,bundle,tenant,actor,foundation,property_values):
    from .reconciliation_postings import prepare_position_metadata,post_positions
    nodes=prepare_bond_nodes(c,bundle,tenant,actor,foundation)
    nodes,parties=prepare_position_metadata(c,bundle,tenant,actor,foundation,product_nodes=nodes)
    result=post_positions(c,bundle,tenant,actor,foundation,nodes,parties,property_values,instrument_ids=set(nodes))
    if result['failed']:
        raise ValueError('Bond batch refused; caller transaction must roll back: '+
            json.dumps([r for r in result['rows'] if r['status']=='NOT_POSTED']))
    result['sourceResetFlowsExcludedFromThisBatch']=result.pop('datedResetFlowsNotPosted')
    return result
