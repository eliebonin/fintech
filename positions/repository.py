"""Scoped, keyset-batched immutable ledger reads in the caller's transaction."""
import json
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select,func,cast,Date
from security_master_schema import models as m
from security_master_schema.tenancy import assert_tenant_owns_strategy
from .contracts import Booking, LedgerFact, PositionError
from .reconstruction import booking_removed

CHUNK_SIZE=500

def iter_ledger_facts(connection, request, *, subject_ids=None):
    assert_tenant_owns_strategy(connection,request.tenant_id,request.strategy_id)
    after=None;currency_cache={};future_identity_cache={};note_identity_cache={}
    while True:
        query=select(m.trade).where(m.trade.c.strategy_id==request.strategy_id,
            # Flow records are validated separately, never as share positions.
            (m.trade.c.price_basis.is_(None) | (m.trade.c.price_basis!='CASH_AMOUNT') | (m.trade.c.trade_type=='INVESTMENT')),
            m.trade.c.trade_datetime_utc<=request.closing_cutoff,
            func.coalesce(m.trade.c.valuation_effective_date,cast(func.timezone('UTC',m.trade.c.trade_datetime_utc),Date))<=request.closing_cutoff.date(),
            m.trade.c.created_at_utc<=request.information_cutoff)
        if subject_ids is not None: query=query.where(m.trade.c.trade_subject_reference_node_id.in_(subject_ids))
        if after is not None: query=query.where(m.trade.c.trade_id>after)
        rows=connection.execute(query.order_by(m.trade.c.trade_id).limit(CHUNK_SIZE)).mappings().all()
        if not rows: return
        from .identity_sources import HistoricalIdentitySources
        identity_sources=HistoricalIdentitySources(connection,request,rows)
        identities=[row['trade_id'] for row in rows]
        chains={identity:[] for identity in identities}; snapshots={}; definitions=set(); parents=set()
        for e in connection.execute(select(m.trade_lifecycle_event).where(
            m.trade_lifecycle_event.c.trade_id.in_(identities),
            m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff).order_by(
                m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.sequence_no)).mappings():
            chains[e['trade_id']].append(e)
        removed=set(); audit={}
        for row in rows:
            identity=row['trade_id']; chain=chains[identity]
            for e in chain:
                if e['event_type']=='BOOKED' and e['event_datetime_utc']!=row['trade_datetime_utc']:
                    raise PositionError('BOOKED execution time is inconsistent')
            audit[identity]=tuple(LedgerFact(e['trade_lifecycle_event_id'],identity,request.tenant_id,request.strategy_id,
                e['sequence_no'],e['event_type'],e['event_datetime_utc'],e['recorded_at_utc'],
                correction_evidence=json.loads(e['event_payload'] or '{}') if e['event_type'] in ('CORRECTED','SUPERSEDED') else None) for e in chain)
            eligible=[f for f in audit[identity] if f.effective_at<=request.closing_cutoff]
            if booking_removed(eligible,request):
                removed.add(identity)
                continue
            for e in chain:
                if e['event_type']!='BOOKED': continue
                try:
                    snapshot=json.loads(e['event_payload'] or '{}')
                    redemption=snapshot.get('lifecycleRedemption')
                    if row['trade_type']=='MATURITY_REDEMPTION':
                        from security_master_schema.evidence import evidence_hash
                        if not redemption or e['payload_hash']!=evidence_hash(snapshot):
                            raise PositionError('Missing or inconsistent frozen maturity redemption evidence')
                        inputs=redemption['inputs'];proof=redemption['authority']
                        from security_master_schema.maturity_evidence import closing_movement
                        move=closing_movement(inputs,redemption.get('movementKey'))
                        if (move is None or UUID(move['subjectId'])!=row['trade_subject_reference_node_id'] or Decimal(move['quantity'])!=row['quantity'] or Decimal(move['price'])!=row['execution_price']
                            or UUID(inputs['instrumentId'])!=row['reference_instrument_node_id'] or UUID(inputs['strategyId'])!=request.strategy_id
                            or inputs['valueDate']!=row['trade_datetime_utc'].date().isoformat() or inputs['scope']!='PRINCIPAL_ONLY'
                            or inputs['paymentRecognised'] is not False or UUID(proof['actorId'])!=e['recorded_by_user_account_id']):
                            raise PositionError('Maturity posting differs from frozen sourced closing economics')
                    if snapshot['kind'] in ('FX_FORWARD_BOOKING','FX_FORWARD_MATURITY'):
                        from .fx_forward import normalize_booking
                        snapshot=normalize_booking(connection,row,snapshot,e,currency_cache=currency_cache)
                    elif snapshot['kind']=='OPTION_BOOKING':
                        from .option import normalize_booking
                        snapshot=normalize_booking(connection,row,snapshot,e,sources=identity_sources)
                    elif snapshot['kind']=='PRODUCT_BOOKING':
                        kind=snapshot['economics']['terms']['kind']
                        if kind in ('FUTURE','STRUCTURED_PRODUCT'):
                            if kind=='FUTURE':
                                from .future import normalize_booking
                                snapshot=normalize_booking(connection,row,snapshot,identity_cache=future_identity_cache,sources=identity_sources)
                            else:
                                from .structured_note import normalize_booking
                                snapshot=normalize_booking(connection,row,snapshot,identity_cache=note_identity_cache,sources=identity_sources)
                            definition=UUID(snapshot['instrumentDefinitionId']);parent=UUID(snapshot['instrumentId'])
                            snapshots[e['trade_id']]=(snapshot,definition,parent)
                            definitions.add(definition);parents.add(parent)
                            continue
                        if kind=='SWAP':
                            from security_master_schema.swap_valuation import frozen_swap_conventions
                            snapshot=snapshot | dict(valuationConventions=frozen_swap_conventions(row,snapshot))
                        if kind not in ('BOND','ACTIVELY_MANAGED_CERTIFICATE','SWAP') or 'valuationConventions' not in snapshot:
                            raise PositionError('Unsupported booking economics; missing frozen product valuation conventions')
                        if kind=='BOND':
                            # Read the original booked terms, never today's security-master terms.
                            frozen=snapshot['valuationConventions'];coupon=snapshot['economics']['terms'].get('couponType')
                            if coupon is not None:
                                if frozen.get('couponType') is not None and frozen['couponType']!=coupon:
                                    raise PositionError('Conflicting frozen bond coupon types')
                                snapshot=snapshot | dict(valuationConventions=frozen | dict(couponType=coupon))
                        if kind=='ACTIVELY_MANAGED_CERTIFICATE':
                            frozen=snapshot['valuationConventions'];convention=snapshot['economics']['terms']['convention']
                            from security_master_schema.amc_quotation import quotation_factors
                            factors=quotation_factors(convention,row['quantity_unit'])
                            if (row['price_basis']!=convention['priceBasis'] or frozen.get('priceBasis')!=convention['priceBasis']
                                    or frozen.get('productBasis')!=kind or factors!=(Decimal(frozen['unitMultiplier']),Decimal(frozen['quoteFactor']))):
                                raise PositionError('AMC frozen quotation differs from approved booked conventions')
                            frozen=frozen | dict(amcConvention=convention)
                            snapshot=snapshot | dict(valuationConventions=frozen)
                        snapshot=snapshot['valuationConventions'] | dict(kind={'BOND':'BOND_BOOKING','SWAP':'SWAP_BOOKING','ACTIVELY_MANAGED_CERTIFICATE':'AMC_BOOKING'}[kind],
                            bondDetails=snapshot['economics'].get('bondDetails'),valuationRecognition=snapshot.get('valuationRecognition'),
                            redemptionEvidence=redemption)
                    elif snapshot['kind']!='CASH_BOOKING': raise PositionError('Unsupported booking economics')
                    definition=UUID(snapshot['instrumentDefinitionId']); parent=UUID(snapshot['instrumentId'])
                    snapshots[e['trade_id']]=(snapshot,definition,parent)
                    definitions.add(definition); parents.add(parent)
                except (KeyError,TypeError,ValueError) as exc:
                    raise PositionError('Missing frozen BOOKED conventions or unsupported booking economics') from exc
        products={row.instrument_definition_version_id:(row.instrument_node_id,row.type_code)
            for row in connection.execute(select(m.instrument_definition_version.c.instrument_definition_version_id,
                m.instrument_definition_version.c.instrument_node_id,m.instrument_type.c.type_code).join(m.instrument_type).where(
                    m.instrument_definition_version.c.instrument_definition_version_id.in_(definitions)))}
        etp={}
        if any(product=='ETP' for _,product in products.values()):
            for term in connection.execute(select(m.etp_terms).where(m.etp_terms.c.instrument_node_id.in_(parents))
                    .order_by(m.etp_terms.c.sequence_no.desc())).mappings():
                etp.setdefault(term['instrument_node_id'],[]).append(term)
        for row in rows:
            if row['trade_id'] in removed:
                yield from audit[row['trade_id']]
                continue
            chain=chains[row['trade_id']]
            if not chain or row['trade_id'] not in snapshots: raise PositionError('Missing original BOOKED evidence')
            snapshot,definition,parent=snapshots[row['trade_id']]
            recognised=snapshot.get('valuationRecognition')
            if recognised is None:
                if row['valuation_effective_date'] is not None:
                    raise PositionError('Missing frozen valuation recognition')
                day=row['trade_datetime_utc'].date(); basis='LEGACY_UTC_TRADE_DATE'; reason=None
            else:
                try:
                    day=date.fromisoformat(recognised['date']); basis=recognised['basis']; reason=recognised['reason']
                    default=row['trade_datetime_utc'].date()
                    if (recognised['timezone']!='UTC' or day<default or
                        (day==default and basis!='UTC_TRADE_DATE') or
                        (day>default and (basis!='EXPLICIT_OVERRIDE' or not isinstance(reason,str) or not reason.strip())) or
                        (day,basis,reason)!=(row['valuation_effective_date'],row['valuation_date_basis'],row['valuation_override_reason'])):
                        raise ValueError()
                except (KeyError,TypeError,ValueError):
                    raise PositionError('Inconsistent frozen valuation recognition') from None
            if definition not in products or products[definition][0]!=parent: raise PositionError('Frozen definition identity mismatch')
            product=products[definition][1]
            if snapshot['kind']=='CASH_BOOKING':
                from security_master_schema.cash_products import cash_product_basis
                try:product,_=cash_product_basis(product,etp.get(parent,[]),row['trade_datetime_utc'].date(),snapshot)
                except ValueError as exc:raise PositionError(str(exc)) from exc
                if snapshot.get('quantityUnit') is not None and snapshot['quantityUnit']!=row['quantity_unit']:
                    raise PositionError('Frozen cash quantity unit differs from booked trade')
            if product=='FUND_SHARE_CLASS': product='FUND'
            from security_master_schema.quantity_movements import movement_proof
            try:movement_proof(snapshot,product=product,price=row['execution_price'],quantity=row['quantity'],trade_type=row['trade_type'])
            except ValueError as exc:raise PositionError(str(exc)) from exc
            from security_master_schema.cash_products import QUOTED_WRAPPERS
            if product not in {'EQUITY','ETF','FUND','BOND','FX_FORWARD','SWAP','OPTION','FUTURE','STRUCTURED_PRODUCT','DIGITAL_ASSET','ACTIVELY_MANAGED_CERTIFICATE'}|QUOTED_WRAPPERS: raise PositionError('Unsupported booking product')
            try:
                currency=UUID(snapshot['priceCurrencyId'])
                price=row['execution_price']
                if product=='BOND':
                    if snapshot['kind']!='BOND_BOOKING' or row['price_basis']!='PCT_OF_PAR' or row['quantity_unit']!='NOMINAL':
                        raise PositionError('Frozen bond quantity/price basis mismatch')
                    from decimal import localcontext
                    with localcontext() as ctx:
                        ctx.prec=512
                        clean_amount=Decimal(snapshot['cleanExecutionAmount'])
                        price=clean_amount*100/abs(row['quantity'])
                        details=snapshot['bondDetails']
                        quoted=abs(row['quantity'])*row['execution_price']/100
                        accrual=Decimal(details['accruedInterestAmount'])
                        if (Decimal(details['cleanAmount'])!=clean_amount or Decimal(details['dirtyAmount'])!=clean_amount+accrual
                            or quoted!=(clean_amount if details['priceType']=='CLEAN' else clean_amount+accrual)):
                            raise PositionError('Frozen bond clean/dirty execution bridge mismatch')
                quantity_unit=row['quantity_unit']
                if snapshot['kind']=='CASH_BOOKING':
                    from security_master_schema.cash_products import canonical_cash_unit
                    quantity_unit=canonical_cash_unit(product,quantity_unit)
                    if quantity_unit!=row['quantity_unit']:
                        snapshot=snapshot|dict(bookedQuantityUnit=row['quantity_unit'],normalizedQuantityUnit=quantity_unit,
                            quantityUnitNormalization='CASH_SECURITY_UNIT_LABEL_ONLY_NO_RESCALING')
                booking=Booking(row['trade_id'],row['trade_subject_reference_node_id'],currency,quantity_unit,
                    row['quantity'],price,Decimal(snapshot['unitMultiplier']),Decimal(snapshot['quoteFactor']),definition,product,
                    day,basis,reason,snapshot if product in {'BOND','FUND','FX_FORWARD','SWAP','OPTION','FUTURE','STRUCTURED_PRODUCT','DIGITAL_ASSET','ACTIVELY_MANAGED_CERTIFICATE'}|QUOTED_WRAPPERS else None)
            except (KeyError,ValueError,TypeError) as exc: raise PositionError('Invalid frozen BOOKED conventions') from exc
            if product=='FX_FORWARD' and (snapshot['kind']!='FX_RATE_BOOKING' or row['quantity_unit']!='CURRENCY_AMOUNT'):
                raise PositionError('Frozen forward units mismatch')
            expected_basis=snapshot['priceBasis'] if product in ('SWAP','OPTION','FUTURE','STRUCTURED_PRODUCT','ACTIVELY_MANAGED_CERTIFICATE') else 'PCT_OF_PAR' if product=='BOND' else 'RATE' if product=='FX_FORWARD' else 'UNIT_PRICE'
            if currency!=row['price_currency_id'] or row['price_basis']!=expected_basis:
                raise PositionError('Frozen booking price currency/basis is inconsistent')
            for e in chain:
                if e['event_type']=='BOOKED' and e['event_datetime_utc']!=row['trade_datetime_utc']:
                    raise PositionError('BOOKED execution time is inconsistent')
                yield LedgerFact(e['trade_lifecycle_event_id'],row['trade_id'],request.tenant_id,request.strategy_id,
                    e['sequence_no'],e['event_type'],e['event_datetime_utc'],e['recorded_at_utc'],
                    booking if e['event_type']=='BOOKED' else None,
                    json.loads(e['event_payload'] or '{}') if e['event_type'] in ('CORRECTED','SUPERSEDED') else None)
        after=rows[-1]['trade_id']
