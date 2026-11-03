"""Owner-confirmed USD quantities and GBP/USD quotations, via native services."""
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
from uuid import UUID
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal


def forward_proposal(bundle,instrument,row,currencies,source,payload,*,base,quote):
    from apps.reference_api.contracts import FxForwardProposalRequest
    if row['trade_currency']!=base:raise ValueError('Source quantity currency disagrees with confirmed base')
    price=native_decimal(row['price'])
    maturity=instrument['maturity_date']
    if row['settlement_date']!=maturity:raise ValueError('Forward settlement conflicts with maturity')
    request=FxForwardProposalRequest(canonicalName=instrument['short_name']+' [reconciliation]',
        internalCode='RECON_'+source.hex+'_FWD_'+source_id(row['instrument_id']),effectiveFrom=instrument['effective_date'],
        baseCurrencyId=currencies[base],quoteCurrencyId=currencies[quote],quoteConvention=quote+'_PER_'+base,
        agreedForwardRate=price['value'],settlementType='DELIVERABLE',maturityDate=maturity,settlementDate=maturity,
        cashSettlementDate=instrument.get('cash_settlement_date') or None,submissionMode='AUTOMATED',
        sourceSystemId=source,sourcePayloadId=payload,idempotencyKey='recon-fwd:'+bundle.digest+':'+row['instrument_id'])
    return request,price


def post_forwards(c,bundle,tenant,actor,foundation,companies,property_values,orientations,*,orientation_evidence=None):
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.access_management import audit
    from apps.reference_api.booking_controls import authorize_booking
    from apps.reference_api.repository import submit_fx_forward_proposal,decide_fx_forward_proposal
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument,book_fx_forward_trade
    from apps.reference_api.contracts import FxForwardBookingRequest
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':trades'))
    if not payload:raise ValueError('Owned retained forward source required')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    defs={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE'))}
    if set(property_values)-set(defs) or any(r.required and r.code not in property_values for r in defs.values()):
        raise ValueError('Complete explicit property mapping required')
    properties=[dict(definitionId=str(defs[k].definition_id),value=v) for k,v in property_values.items()]
    instruments={source_id(i['instrument_id']):i for i in bundle.tables['all_instruments']}
    result=[]
    for row in bundle.positions:
        identifier=source_id(row['instrument_id'])
        if identifier not in orientations:continue
        if instruments[identifier]['instrument_type']!='FXFWD':raise ValueError('Source forward classification differs')
        base,quote=orientations[identifier]
        req,price=forward_proposal(bundle,instruments[identifier],row,currencies,foundation['sourceId'],payload,base=base,quote=quote)
        proposal=submit_fx_forward_proposal(c,tenant,actor,req)
        if proposal.status=='PENDING':proposal=decide_fx_forward_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED',
            (orientation_evidence or 'Owner confirmed source quantities are USD and rates GBP per USD; no inversion.')+' Exact source and authorized truncation retained in audit. Deliverable maturity inferred from source dates.')
        if proposal.status!='APPROVED' or not proposal.instrument_id:raise ValueError('Forward proposal is not approved')
        node=proposal.instrument_id
        signed=Decimal(native_decimal(row['quantity'])['value'])
        execution=datetime.fromisoformat(row['trade_datetime_utc'])
        if execution.tzinfo is None:execution=execution.replace(tzinfo=timezone.utc)
        context=get_fx_forward_booking_instrument(c,tenant,node,as_of=execution.date())
        if not context.booking_eligible:raise ValueError(context.ineligibility_message)
        request=FxForwardBookingRequest(instrumentId=node,strategyId=foundation['strategyId'],side='BUY' if signed>0 else 'SELL',
            quantity=signed.copy_abs(),tradeDatetime=execution,counterpartyOrganisationId=companies[source_id(row['counterparty_id'])],
            expectedTermsFingerprint=context.terms_fingerprint,properties=properties,tradePurpose='HEDGING',
            comment=('Private reconciliation. '+orientation_evidence+' Source currency labels retained in import evidence.') if orientation_evidence else 'Private reconciliation. USD quantity, GBP per USD rate confirmed by owner; source currency labels retained in import evidence.',
            externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(foundation['sourceId']))])
        key='recon-fwd-trade:'+sha256(document(dict(source=str(foundation['sourceId']),trade=row['trade_id']))).hexdigest()
        detail=book_fx_forward_trade(c,tenant,actor,request,key,'reconciliation-import')
        trade_id=detail.data.trade.trade_id
        old=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action=='RECONCILIATION_FORWARD_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(trade_id)))
        if not old:audit(c,actor,tenant,'RECONCILIATION_FORWARD_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
            strategyId=str(foundation['strategyId']),sourcePayloadId=str(payload),sourceTradeId=row['trade_id'],sourceInstrumentId=identifier,
            instrumentId=str(node),tradeId=str(trade_id),originalRow=dict(row),priceNormalization=price,
            quantityNormalization=native_decimal(row['quantity']),quantityCurrency=base,priceCurrency=quote,rateInverted=False,
            settlementAssumption='DELIVERABLE inferred from dated forward export; no cash balances or maturity closure generated',mappedProperties=property_values))
        result.append(dict(sourceInstrumentId=identifier,instrumentId=str(node),tradeId=str(trade_id),status='BOOKED'))
    return result
