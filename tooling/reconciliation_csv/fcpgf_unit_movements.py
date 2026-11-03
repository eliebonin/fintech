"""Owner-approved FCPGF source guesses, isolated from the native movement model."""
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.access_management import audit
from security_master_schema.booking_controls import authorize_booking
from trading.position_movements import FundUnitMovementRequest,book_fund_unit_movement
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal
from .fcpgf_instruments import receipt,source_instruments

RECURRING_DATES=frozenset({'2021-12-20','2022-02-03','2022-05-09','2022-11-07','2022-12-07','2023-05-17'})


def classify(row):
    if Decimal(row['price'])!=0 or Decimal(row['quantity'])==0:raise ValueError('Nonzero unit movement at source price zero required')
    return 'REINVESTMENT' if row['trade_datetime_utc'][:10] in RECURRING_DATES and Decimal(row['quantity'])>0 else 'TRANSFER'


def post(c,bundle,tenant,actor,foundation,nodes,listings,parties,property_values):
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    if bundle.digest!=foundation['bundleHash']:raise ValueError('Retained source bundle differs')
    payload=receipt(c,bundle,foundation,'trades')
    source=c.execute(select(m.source_payload).where(m.source_payload.c.source_payload_id==payload,m.source_payload.c.tenant_id==tenant,
        m.source_payload.c.integration_source_system_id==foundation['sourceId'])).mappings().one()
    if source['payload_sha256']!=sha256(bundle.files['trades']).hexdigest():raise ValueError('Retained source receipt differs')
    definitions={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE'))}
    if set(property_values)-set(definitions) or any(d.required and d.code not in property_values for d in definitions.values()):raise ValueError('Complete active property mapping required')
    props=[dict(definitionId=definitions[k].definition_id,value=v) for k,v in property_values.items()]
    instruments=source_instruments(bundle);result=[];counts={'TRANSFER':0,'REINVESTMENT':0}
    for row in sorted(bundle.positions,key=lambda r:(r['trade_datetime_utc'],r['trade_id'])):
        iid=source_id(row['instrument_id']);item=instruments[iid]
        if item['instrument_type']!='FUND' or Decimal(row['price'])!=0:continue
        if iid not in listings or iid not in nodes or row['trade_currency']!=item['currency']:raise ValueError('Owned source fund listing/currency mapping required')
        if row.get('price_type')!='unit' or any(Decimal(row.get(k) or '1')!=1 for k in ('unit_multiplier','quote_factor')):raise ValueError('Explicit source fund unit basis required')
        kind=classify(row);normal=native_decimal(row['quantity']);q=Decimal(normal['value'])
        when=datetime.fromisoformat(row['trade_datetime_utc'])
        if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
        reason='Owner-approved best-guess source classification on 2026-10-30: '+('recurring fund unit credit treated as reinvestment; distribution income remains separately unassessed.' if kind=='REINVESTMENT' else 'allocation, offset/rebooking or reduction treated as a fund-unit transfer.')
        request=FundUnitMovementRequest(listingId=listings[iid],strategyId=foundation['strategyId'],side='BUY' if q>0 else 'SELL',quantity=q.copy_abs(),
            tradeDatetime=when,settlementDate=row['settlement_date'],counterpartyOrganisationId=parties[source_id(row['counterparty_id'])],properties=props,
            movementKind=kind,movementReason=reason,comment=reason+' No cash movement or execution price inferred.',
            externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(foundation['sourceId']))])
        key='fcpgf-units:'+sha256(document(dict(source=str(foundation['sourceId']),trade=row['trade_id']))).hexdigest()
        native=book_fund_unit_movement(c,tenant,actor,request,key)
        prior=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.action=='RECONCILIATION_TRADE_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(native.trade_id)))
        if not prior:audit(c,actor,tenant,'RECONCILIATION_TRADE_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
            sourceTradeId=row['trade_id'],sourceRowHash=sha256(document(row)).hexdigest(),sourcePayloadId=str(payload),tradeId=str(native.trade_id),originalRow=row,
            normalization=dict(quantity=normal,price=native_decimal(row['price'])),mappedProperties=property_values,
            ownerClassification=dict(kind=kind,reason=reason,sourcePriceIsNotAnExecutionPrice=True,cashGenerated=False,incomeAutomaticallyRecognised=False)))
        result.append(dict(sourceTradeId=row['trade_id'],tradeId=str(native.trade_id),kind=kind));counts[kind]+=1
    return dict(posted=len(result),byKind=counts,rows=result,classification='OWNER_AUTHORISED_INFERENCE_NOT_BROKER_CONFIRMED')
