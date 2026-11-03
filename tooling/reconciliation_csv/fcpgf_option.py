"""Reuse the already imported standard SPX contract in the same tenant."""
from datetime import datetime,timezone,date
from decimal import Decimal
from hashlib import sha256
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.access_management import audit
from .reconciliation import source_id,document
from .reconciliation_option import normalize_option_units,post_option


def book_standard_option(c,bundle,tenant,actor,foundation,properties,parties):
    from security_master_schema.booking_controls import authorize_booking
    from apps.reference_api.option_booking import load,book
    from apps.reference_api.contracts import OptionBookingRequest
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    matches=c.execute(select(m.listing).join(m.reference_node_scope,
        m.reference_node_scope.c.reference_node_id==m.listing.c.listing_node_id).where(
        m.listing.c.trading_symbol=='SPX.202612.P.05800000',m.listing.c.status=='ACTIVE',
        m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')).mappings().all()
    if not matches:return post_option(c,bundle,tenant,actor,foundation,properties)
    if len(matches)!=1:raise ValueError('Ambiguous existing SPX listing')
    listing=matches[0];node=listing['instrument_node_id']
    # Only reuse the previously audited source-20265 standard contract, never a
    # name-only match or another tenant's private reference.
    proof=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action=='RECONCILIATION_OPTION_BOOKED',m.access_audit_event.c.details['instrumentId'].as_string()==str(node),
        m.access_audit_event.c.details['sourceInstrumentId'].as_string()=='20265'))
    if not proof:raise ValueError('Existing standard contract lacks reviewed source identity evidence')
    rows=[r for r in bundle.positions if source_id(r['instrument_id'])=='20265']
    if len(rows)!=1:raise ValueError('One source standard option execution required')
    row=rows[0];normal=normalize_option_units(row);execution=datetime.fromisoformat(row['trade_datetime_utc'])
    if execution.tzinfo is None:execution=execution.replace(tzinfo=timezone.utc)
    _,context=load(c,tenant,listing['listing_node_id'],as_of=execution.date())
    stored=c.execute(select(m.option_terms).where(m.option_terms.c.instrument_node_id==node,m.option_terms.c.is_current)).mappings().one()
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    expiry=date(2026,12,18)
    dates=c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id==node)).mappings().one()
    if (stored['option_type']!='PUT' or stored['strike_value']!=Decimal('5800') or stored['premium_multiplier']!=100
        or dates['expiry_date']!=expiry or stored['exercise_style']!='EUROPEAN' or stored['settlement_method']!='CASH'
        or currencies[stored['premium_currency_id']]!='USD' or currencies[stored['strike_currency_id']]!='USD'
        or context.premium_multiplier!='100' or context.quote_factor!='1' or context.deliverable_units!='100' or not context.booking_eligible):
        raise ValueError('Existing standard SPX option differs from source contract')
    definitions={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE'))}
    request=OptionBookingRequest(listingId=listing['listing_node_id'],strategyId=foundation['strategyId'],side='BUY' if Decimal(normal['quantity'])>0 else 'SELL',
        quantity=Decimal(normal['quantity']).copy_abs(),executionPrice=normal['premium'],tradeDatetime=execution,settlementDate=row['settlement_date'],positionEffect='OPEN',
        expectedTermsFingerprint=context.terms_fingerprint,counterpartyOrganisationId=parties[source_id(row['counterparty_id'])],
        properties=[dict(definitionId=definitions[k].definition_id,value=v) for k,v in properties.items()],
        externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(foundation['sourceId']))],
        comment='Private reconciliation; source units /100 into the same tenant standard SPX contract. Source execution price unchanged. OPEN inferred from sole supplied source execution.')
    key='recon-option-trade:'+sha256(document(dict(sourceId=str(foundation['sourceId']),tradeId=row['trade_id']))).hexdigest()
    detail=book(c,tenant,actor,request,key,'reconciliation-import');trade=detail.data.trade.trade_id
    if Decimal(detail.data.trade.option_economics.gross_premium)!=Decimal(normal['grossPremium']):raise ValueError('Standardization changed gross premium')
    if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.action=='RECONCILIATION_OPTION_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(trade))):
        audit(c,actor,tenant,'RECONCILIATION_OPTION_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
            sourceInstrumentId='20265',sourceTradeId=row['trade_id'],tradeId=str(trade),instrumentId=str(node),listingId=str(listing['listing_node_id']),
            originalRow=row,normalization=normal,reusedReviewedContract=True,positionEffectAssumption='OPEN from sole source execution'))
    return dict(tradeId=trade,instrumentId=node,listingId=listing['listing_node_id'],quantity=normal['quantity'],premiumMultiplier='100',grossPremium=normal['grossPremium'])
