"""Owner-confirmed SPX source-unit correction, normal listing and native booking.

This is a bounded local reconciliation operator, not a general option uploader.
"""
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.access_management import audit
from security_master_schema.reference_authority import require_reference_action
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal

SPEC='https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications'
CODES='https://www.cboe.com/markets/us/options/trading/codes'


def normalize_option_units(row):
    if row.get('price_type')!='unit' or row['trade_currency']!='USD' or Decimal(row['unit_multiplier'])!=1 or Decimal(row.get('quote_factor','1'))!=1:
        raise ValueError('Confirmed USD source units with embedded multiplier required')
    quantity=native_decimal(row['quantity']);premium=native_decimal(row['price'])
    if quantity['truncated'] or premium['truncated']:raise ValueError('Exact option economics required; no contract/premium rounding')
    with localcontext() as ctx:
        ctx.prec=100
        units=Decimal(quantity['value']);contracts=units/100
        if not contracts or contracts!=contracts.to_integral_value():raise ValueError('Source units must convert exactly into whole contracts')
        if Decimal(premium['value'])<0:raise ValueError('Nonnegative premium required')
        gross=units.copy_abs()*Decimal(premium['value'])
        if gross>=Decimal('1e18') or gross!=gross.quantize(Decimal('1e-12')):raise ValueError('Premium exceeds exact native precision')
        gross=gross.quantize(Decimal('1e-12'))
        return dict(originalQuantity=row['quantity'],quantity=format(contracts.quantize(Decimal(1)),'f'),
            premium=premium['value'],premiumMultiplier='100',grossPremium=format(gross,'f'),
            operation='OWNER_CONFIRMED_EMBEDDED_MULTIPLIER_QUANTITY_DIVIDE_100',priceNormalization=premium)


def post_option(c,bundle,tenant,actor,foundation,property_values):
    from apps.reference_api.booking_controls import authorize_booking
    from apps.reference_api.option_onboarding import submit_option_proposal,decide_option_proposal
    from apps.reference_api.option_booking import load,book
    from apps.reference_api.repository import submit_equity_listing_proposal,decide_equity_proposal
    from apps.reference_api.contracts import OptionProposalRequest,EquityListingCreateProposalRequest,OptionBookingRequest
    from .reconciliation_postings import prepare_position_metadata
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    require_reference_action(c,tenant,actor,'REFERENCE_PROPOSE')
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    c.execute(select(m.integration_source_system).where(m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).one()
    payloads={}
    for kind in ('trades','all_instruments'):
        receipt=c.execute(select(m.source_payload).where(m.source_payload.c.tenant_id==tenant,
            m.source_payload.c.integration_source_system_id==foundation['sourceId'],
            m.source_payload.c.external_message_reference==bundle.digest+':'+kind)).mappings().one()
        if receipt['payload_sha256']!=sha256(bundle.files[kind]).hexdigest():raise ValueError('Retained source hash differs')
        payloads[kind]=receipt['source_payload_id']
    rows=[r for r in bundle.positions if source_id(r['instrument_id'])=='20265']
    if len(rows)!=1:raise ValueError('Exactly one confirmed source SPX execution required')
    row=rows[0];normalized=normalize_option_units(row)
    item=next(i for i in bundle.tables['all_instruments'] if source_id(i['instrument_id'])=='20265')
    if item['instrument_type']!='VANILLA' or item['short_name']!='SPX.202612.P.05800000' or item['maturity_date']!='2026-12-18':
        raise ValueError('Confirmed source SPX put identity required')
    lock=int.from_bytes(sha256(('reconciliation-option:'+str(foundation['sourceId'])).encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    events=c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action=='RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED',
        m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
        m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)).scalars().all()
    old_nodes={e['options']['20265'] for e in events if '20265' in e.get('options',{})}
    if len(old_nodes)!=1:raise ValueError('One audited private normalized option mapping required')
    old=UUID(old_nodes.pop())
    c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==old,
        m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')).one()
    c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==old).with_for_update()).one()
    if c.scalar(select(func.count()).select_from(m.trade).where(or_(m.trade.c.reference_instrument_node_id==old,m.trade.c.trade_subject_reference_node_id==old))):
        raise ValueError('Normalized placeholder has bookings; explicit correction required')
    old_terms=c.execute(select(m.option_terms).where(m.option_terms.c.instrument_node_id==old,m.option_terms.c.is_current)).mappings().one()
    if old_terms['premium_multiplier']!=1 or old_terms['strike_value']!=5800 or old_terms['option_type']!='PUT':raise ValueError('Normalized placeholder changed')
    execution=datetime.fromisoformat(row['trade_datetime_utc'])
    if execution.tzinfo is None:execution=execution.replace(tzinfo=timezone.utc)
    expiry=datetime.strptime('2026-12-18','%Y-%m-%d').date()
    cutoff=datetime.combine(expiry-timedelta(days=1),time(17),ZoneInfo('America/New_York')).astimezone(timezone.utc)
    req=OptionProposalRequest(canonicalName=item['short_name']+' [standard SPX contract]',effectiveFrom=execution.date(),
        underlyingId=old_terms['underlying_reference_node_id'],optionType='PUT',strike='5800',
        strikeCurrencyId=old_terms['strike_currency_id'],premiumCurrencyId=old_terms['premium_currency_id'],
        premiumMultiplier='100',deliverableUnits='100',expiryDate=expiry,lastTradingAtUtc=cutoff,exerciseStyle='EUROPEAN',settlementMethod='CASH',
        idempotencyKey='recon-standard-spx:'+bundle.digest+':20265')
    proposal=submit_option_proposal(c,tenant,actor,req)
    if proposal.status=='PENDING':proposal=decide_option_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED',
        'Owner confirmed embedded multiplier: source 2000 units = 20 standard contracts, multiplier 100. Cboe European/cash terms; standard monthly AM expiry inferred from SPX symbol, not broker-confirmed. '+SPEC)
    if proposal.status!='APPROVED':raise ValueError('Standard option not approved')
    node=proposal.reference_node_id
    mic=m.market_venue_identifier
    venue=c.scalar(select(m.market_venue.c.market_venue_id).join(mic).where(mic.c.identifier_scheme=='ISO_10383_MIC',mic.c.identifier_value=='XCBO'))
    if venue is None:
        venue=c.scalar(m.market_venue.insert().values(venue_type='EXCHANGE',display_name='Cboe Options Exchange',country_code='USA',
            city='Chicago',timezone_name='America/New_York',status='ACTIVE').returning(m.market_venue.c.market_venue_id))
        c.execute(mic.insert().values(market_venue_id=venue,identifier_scheme='ISO_10383_MIC',identifier_value='XCBO',is_primary=True))
        audit(c,actor,tenant,'RECONCILIATION_OPTION_VENUE_CREATED',dict(venueId=str(venue),mic='XCBO',source=CODES,
            calendarStatus='NOT_CONFIGURED; booking only, not valuation/session readiness'))
    listing_req=EquityListingCreateProposalRequest(instrumentId=node,listing=dict(marketVenueId=venue,
        tradingSymbol=item['short_name'],tradingCurrencyId=old_terms['premium_currency_id'],quoteFactor='1',unitMultiplier='100',
        effectiveFrom=execution.date(),isPrimaryListing=True),submissionMode='AUTOMATED',sourceSystemId=foundation['sourceId'],
        sourcePayloadId=payloads['all_instruments'],idempotencyKey='recon-standard-spx-listing:'+bundle.digest)
    listing_proposal=submit_equity_listing_proposal(c,tenant,actor,listing_req)
    if listing_proposal.status=='PENDING':listing_proposal=decide_equity_proposal(c,tenant,actor,listing_proposal.proposal_id,'APPROVED',
        'Source SPX label used as internal listing symbol; not asserted as an official OCC/vendor alias. XCBO venue verified from Cboe. '+CODES)
    if listing_proposal.status!='APPROVED':raise ValueError('SPX listing not approved')
    listing=c.execute(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==node,m.listing.c.market_venue_id==venue)).scalar_one()
    _,terms=load(c,tenant,listing,as_of=execution.date())
    if not terms.booking_eligible:raise ValueError(terms.ineligibility_message)
    if terms.premium_multiplier!='100' or terms.quote_factor!='1' or terms.deliverable_units!='100':raise ValueError('Standard option convention changed')
    _,parties=prepare_position_metadata(c,bundle,tenant,actor,foundation,product_nodes={'20265':node})
    defs={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE'))}
    if set(property_values)-set(defs) or any(d.required and d.code not in property_values for d in defs.values()):raise ValueError('Complete property mapping required')
    request=OptionBookingRequest(listingId=listing,strategyId=foundation['strategyId'],side='BUY' if Decimal(normalized['quantity'])>0 else 'SELL',
        quantity=Decimal(normalized['quantity']).copy_abs(),executionPrice=normalized['premium'],tradeDatetime=execution,
        settlementDate=row['settlement_date'],positionEffect='OPEN',expectedTermsFingerprint=terms.terms_fingerprint,
        counterpartyOrganisationId=parties[source_id(row['counterparty_id'])],
        properties=[dict(definitionId=str(defs[k].definition_id),value=v) for k,v in property_values.items()],
        externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(foundation['sourceId']))],
        comment='Private reconciliation. Owner confirmed source units /100 into standard contracts. OPEN inferred from sole source execution; standard AM expiry inferred. '+(row.get('comment') or ''))
    key='recon-option-trade:'+sha256(document(dict(sourceId=str(foundation['sourceId']),tradeId=row['trade_id']))).hexdigest()
    detail=book(c,tenant,actor,request,key,'reconciliation-import');trade_id=detail.data.trade.trade_id
    if Decimal(detail.data.trade.option_economics.gross_premium)!=Decimal(normalized['grossPremium']):raise ValueError('Option premium changed during normalization')
    if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action=='RECONCILIATION_OPTION_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(trade_id))):
        c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==old).values(is_tradable=False,status='INACTIVE'))
        audit(c,actor,tenant,'RECONCILIATION_OPTION_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
            strategyId=str(foundation['strategyId']),sourceTradeId=row['trade_id'],sourceInstrumentId='20265',originalRow=row,
            sourcePayloadIds={k:str(v) for k,v in payloads.items()},normalization=normalized,instrumentId=str(node),listingId=str(listing),tradeId=str(trade_id),
            supersededUnbookedInstrumentId=str(old),sources=[SPEC,CODES],mappedProperties=property_values,
            assumptions=dict(positionEffect='OPEN from sole supplied execution; not independent inventory proof',
                expiryStyle='STANDARD_MONTHLY_AM inferred from source SPX symbol and third-Friday expiry; not broker-confirmed',
                venue='XCBO contract venue; source does not independently confirm actual execution venue',
                calendar='Venue calendar not configured; no valuation readiness implied')))
    return dict(tradeId=trade_id,instrumentId=node,listingId=listing,quantity=normalized['quantity'],premiumMultiplier='100',grossPremium=normalized['grossPremium'])
