"""Private FCPGF rate-leg completion; not a product dependency or upload format."""
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.rate_swap_terms import RateSwapTerms
from security_master_schema.access_management import audit
from security_master_schema.booking_controls import authorize_booking
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal
from .fcpgf_instruments import source_instruments,receipt,classify


def rate_plan(bundle,iid,references,currencies,days):
    """Source pairing and explicitly disclosed completion stay outside the product."""
    ins=source_instruments(bundle);item=ins[iid]
    rows=[r for r in bundle.positions if source_id(r['instrument_id'])==iid]
    peers=[k for k,v in ins.items() if v['unique_identifier']==item['unique_identifier']+'USD']
    if len(rows)!=1 or len(peers)!=1:raise ValueError('One explicit source component and its USD companion required')
    row=rows[0];peer=peers[0];peer_rows=[r for r in bundle.positions if source_id(r['instrument_id'])==peer]
    if len(peer_rows)!=1:raise ValueError('One sourced companion position required for notional completion')
    companion=peer_rows[0]
    if (item['currency']!='GBP' or row['trade_currency']!='GBP' or companion['trade_currency']!='USD'
        or companion['trade_datetime_utc']!=row['trade_datetime_utc'] or ins[peer]['maturity_date']!=item['maturity_date']):
        raise ValueError('Companion identity, currency, execution and maturity must agree')
    if row['price_type']!='notional' or any(Decimal(row.get(k) or '1')!=1 for k in ('quote_factor','unit_multiplier')):
        raise ValueError('Explicit source notional quote with unit factors required')
    normal=native_decimal(row['quantity']);usd=native_decimal(companion['quantity'])
    notionals={'GBP':Decimal(normal['value']).copy_abs(),'USD':Decimal(usd['value']).copy_abs()}
    if any(n==0 for n in notionals.values()):raise ValueError('Nonzero source component notionals required')
    source_legs=[r for r in bundle.tables['swaps'] if source_id(r['instrument_id'])==iid]
    if len(source_legs)!=2:raise ValueError('Exactly two source rate legs required')
    legs=[]
    for leg in source_legs:
        ref=source_id(leg.get('funding_instrument_id') or leg.get('funded_instrument_id'));benchmark=ins[ref]
        if ref not in references or benchmark['currency'] not in notionals or Decimal(leg['leverage']) not in (Decimal(1),Decimal(-1)) or source_id(leg['swap_payment_per_year'])!='4':
            raise ValueError('This retained source requires two mapped unit-gearing quarterly rate legs')
        currency=benchmark['currency']
        legs.append(dict(direction='PAY' if Decimal(leg['leverage'])<0 else 'RECEIVE',rateReferenceId=references[ref],currencyId=currencies[currency],
            contractualNotional=str(notionals[currency]),spread=str(Decimal(leg['floating_spread_bps'])/Decimal(10000)),
            dayCountConventionId=days['ACT_360' if currency=='USD' else 'ACT_365F'],
            interestCalculationMethod='RECONCILIATION ASSUMPTION: overnight compounding in arrears; no generated interest or curve valuation.',
            observationDescription='Source supplies quarterly payments; exact observation lag, calendar and fixing schedule were not exported and remain unassessed.',
            resetFrequency='QUARTERLY',paymentFrequency='QUARTERLY'))
    terms=RateSwapTerms(swapKind='RATE_EXCHANGE',tenantIdentifier=item['unique_identifier'],contractualNotional=str(notionals['GBP']),
        notionalCurrencyId=currencies['GBP'],quoteCurrencyId=currencies['GBP'],quoteFactor='1',
        effectiveDate=row['trade_datetime_utc'][:10],maturityDate=item['maturity_date'],
        sourceReference='Owner-clarified two-leg component; retained bundle '+bundle.digest+'. Separate component price; no package consolidation.',
        principalExchange='UNSPECIFIED',principalExchangeDescription='The source export does not establish principal exchanges or FX-reset conventions. No principal movements are inferred.',legs=legs)
    evidence=dict(sourceInstrumentId=iid,companionInstrumentId=peer,companionNativeInstrumentId=str(references[peer]) if peer in references else None,
        originalSwapRows=source_legs,sourceQuantity=normal,companionQuantity=usd,
        notionalCompletion='USD leg inferred from absolute USD companion booking; GBP basis from this component. Independent source quantities retained.',
        schedulingCompletion='Effective date inferred from execution; quarterly resets and overnight day counts are disclosed completion assumptions. No generated payments.',
        bankPricesRemainSeparate=True,bondIncomeVersusTotalReturn='Owner describes income exchange; pre-existing performance-side BOOKED evidence remains retained, not rewritten.')
    return terms,evidence


def post(c,bundle,tenant,actor,foundation,nodes,parties,properties):
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    from apps.reference_api.product_booking import submit_proposal,decide_proposal,load_context,book
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    if bundle.digest!=foundation['bundleHash']:raise ValueError('Retained source bundle differs')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    days=dict(c.execute(select(m.day_count_convention.c.code,m.day_count_convention.c.day_count_convention_id).where(m.day_count_convention.c.status=='ACTIVE')).all())
    definitions={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE'))}
    if set(properties)-set(definitions) or any(d.required and d.code not in properties for d in definitions.values()):raise ValueError('Complete active native trade-property mapping required')
    props=[dict(definitionId=definitions[k].definition_id,value=v) for k,v in properties.items()]
    ins=source_instruments(bundle);rows=[]
    for iid in sorted(source_id(r['instrument_id']) for r in bundle.positions if r['unique_identifier'] in ('ASWAP13','ASWAP15','ASWAP22','ASWAP24')):
        row=next(r for r in bundle.positions if source_id(r['instrument_id'])==iid)
        terms,evidence=rate_plan(bundle,iid,nodes,currencies,days);target=nodes[iid]
        original=c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==target).order_by(m.instrument_definition_version.c.sequence_no)).mappings().first()
        if original is None:raise ValueError('Retained non-tradable reference definition required')
        identity=sha256(document(dict(source=str(foundation['sourceId']),instrument=iid))).hexdigest()
        request=SwapProposalRequest(canonicalName=ins[iid]['unique_identifier']+' — SOFR / SONIA rate exchange',terms=terms,
            existingReferenceId=target,expectedReferenceDefinitionId=original['instrument_definition_version_id'],idempotencyKey='fcpgf-rate-terms:'+identity)
        proposal=submit_proposal(c,tenant,actor,request)
        if proposal.status=='PENDING':proposal=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Owner-authorised two separately priced components; retained source and disclosed completion reviewed.')
        if proposal.status!='APPROVED' or proposal.reference_node_id!=target:raise ValueError('Source reference completion must preserve identity')
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.action=='RECONCILIATION_RATE_SWAP_APPROVED',m.access_audit_event.c.details['instrumentId'].as_string()==str(target))):
            audit(c,actor,tenant,'RECONCILIATION_RATE_SWAP_APPROVED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),instrumentId=str(target),proposalId=str(proposal.proposal_id),**evidence))
        classify(c,tenant,actor,bundle,foundation,target,'ASWAP',terms.effective_date)
        when=datetime.fromisoformat(row['trade_datetime_utc']);when=when if when.tzinfo else when.replace(tzinfo=timezone.utc)
        context=load_context(c,tenant,target,as_of=when.date())
        if not context.booking_eligible:raise ValueError('Approved rate-swap booking not ready: '+str(context.ineligibility_message))
        q=native_decimal(row['quantity']);price=native_decimal(row['price']);quantity=Decimal(q['value'])
        ticket=ProductBookingRequest(instrumentId=target,strategyId=foundation['strategyId'],executionRoute='OTC',side='BUY' if quantity>0 else 'SELL',
            quantity=quantity.copy_abs(),executionPrice=price['value'],tradeDatetime=when,counterpartyOrganisationId=parties[source_id(row['counterparty_id'])],properties=props,
            expectedTermsFingerprint=context.terms_fingerprint,externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(foundation['sourceId']))],
            comment='Separate bank-priced rate-exchange component. '+evidence['notionalCompletion']+' '+evidence['schedulingCompletion'])
        key='fcpgf-rate-trade:'+sha256(document(dict(source=str(foundation['sourceId']),trade=row['trade_id']))).hexdigest()
        trade=book(c,tenant,actor,ticket,key,'SWAP','fcpgf-rate-import').data.trade.trade_id
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.action=='RECONCILIATION_TRADE_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(trade))):
            audit(c,actor,tenant,'RECONCILIATION_TRADE_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
                sourceTradeId=row['trade_id'],sourceRowHash=sha256(document(row)).hexdigest(),sourcePayloadId=str(receipt(c,bundle,foundation,'trades')),
                tradeId=str(trade),originalRow=row,normalization=dict(quantity=q,price=price),mappedProperties=properties,rateLegCompletion=evidence))
        rows.append(dict(sourceInstrumentId=iid,instrumentId=str(target),tradeId=str(trade),proposalId=str(proposal.proposal_id),sourceTradeId=row['trade_id']))
    return dict(posted=len(rows),rows=rows,independentComponentPrices=True)
