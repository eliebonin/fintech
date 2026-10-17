"""Frozen deliverable-forward bookings and retained maturity closing rates."""
from datetime import date
from decimal import Decimal,localcontext
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from .contracts import PositionError


def normalize_booking(c,row,snapshot,event,*,currency_cache=None):
    parent=row['reference_instrument_node_id'];kind=snapshot['kind']
    if parent!=row['trade_subject_reference_node_id'] or row['quantity_unit']!='CURRENCY_AMOUNT' or row['price_basis']!='RATE':
        raise PositionError('Forward must use canonical contract, base amount and quote-per-base rate')
    conventions=snapshot.get('valuationConventions')
    if conventions is None:
        # Legacy evidence is not relabelled. Only an exact unchanged contractual
        # fingerprint permits deriving the otherwise absent definition reference.
        from security_master_schema.fx_forward_reference import load_fx_forward_booking_terms
        from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
        terms=load_fx_forward_booking_terms(c,row['tenant_id'] if 'tenant_id' in row else _tenant(c,row['strategy_id']),parent,as_of=row['trade_datetime_utc'].date())
        fingerprint=snapshot['economics']['termsFingerprint'] if kind=='FX_FORWARD_BOOKING' else snapshot['inputs']['termsFingerprint']
        if fx_forward_terms_fingerprint(terms)!=fingerprint:raise PositionError('Legacy forward terms changed; frozen proof required')
        definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(
            m.instrument_definition_version.c.instrument_node_id==parent,m.instrument_definition_version.c.is_current,m.instrument_definition_version.c.status=='APPROVED'))
        if not definition:raise PositionError('Approved forward definition required')
        conventions=dict(instrumentDefinitionId=str(definition),instrumentId=str(parent),priceCurrencyId=str(terms.quote_currency_id),baseCurrencyId=str(terms.base_currency_id),
            agreedRate=str(terms.agreed_rate),maturityDate=terms.maturity_date.isoformat(),quoteConvention=terms.quote_convention,settlementType=terms.settlement_type,
            unitMultiplier='1',quoteFactor='1',legacyProof='EXACT_CURRENT_TERMS_FINGERPRINT')
    if (conventions['instrumentId']!=str(parent) or conventions['priceCurrencyId']!=str(row['price_currency_id'])
        or conventions['settlementType']!='DELIVERABLE' or Decimal(conventions['unitMultiplier'])!=1 or Decimal(conventions['quoteFactor'])!=1):
        raise PositionError('Frozen forward identity/currency/conventions mismatch')
    agreed=Decimal(conventions['agreedRate'])
    pair=frozenset((UUID(conventions['baseCurrencyId']),UUID(conventions['priceCurrencyId'])))
    codes=currency_cache.get(pair) if currency_cache is not None else None
    if codes is None:
        codes=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(
            m.currency.c.currency_id.in_(pair))).all())
        if currency_cache is not None:currency_cache[pair]=codes
    base=codes[UUID(conventions['baseCurrencyId'])];quote=codes[UUID(conventions['priceCurrencyId'])]
    if base==quote or conventions['quoteConvention']!=f'{quote}_PER_{base}':raise PositionError('Forward quote direction mismatch')
    from valuation.economics import finite_decimal,evidence_hash
    finite_decimal(agreed,'agreed forward rate',positive=True)
    maturity=None
    if kind=='FX_FORWARD_BOOKING':
        e=snapshot['economics']
        if (snapshot['baseCurrencyId']!=conventions['baseCurrencyId'] or snapshot['quoteCurrencyId']!=conventions['priceCurrencyId']
            or e['quoteConvention']!=conventions['quoteConvention'] or Decimal(e['agreedRate'])!=agreed or row['execution_price']!=agreed):
            raise PositionError('Frozen forward booking rate/currency mismatch')
        with localcontext() as context:
            context.prec=512
            base=abs(row['quantity']);quote=base*agreed
        received,paid=(base,quote) if row['quantity']>0 else (quote,base)
        if Decimal(e['receiveAmount'])!=received or Decimal(e['payAmount'])!=paid:raise PositionError('Frozen forward amounts mismatch')
        currencies=(codes[UUID(conventions['baseCurrencyId'])],codes[UUID(conventions['priceCurrencyId'])])
        if row['quantity']<0:currencies=currencies[::-1]
        if (e['receiveCurrency'],e['payCurrency'])!=currencies:raise PositionError('Frozen forward delivery currency mismatch')
    else:
        maturity=snapshot['inputs'];move=maturity['movements'][0]
        if (event['payload_hash']!=evidence_hash(snapshot) or row['trade_type']!='MATURITY_CLOSE'
            or maturity['instrumentId']!=str(parent) or maturity['strategyId']!=str(row['strategy_id'])
            or maturity['valueDate']!=row['trade_datetime_utc'].date().isoformat() or maturity['valueDate']!=conventions['maturityDate']
            or Decimal(move['quantity'])!=row['quantity'] or Decimal(maturity['price'])!=row['execution_price']
            or maturity['paymentRecognised'] is not False or maturity['scope']!='EXPOSURE_ONLY'
            or maturity['currencyId']!=conventions['priceCurrencyId'] or maturity['baseCurrencyId']!=conventions['baseCurrencyId']
            or Decimal(maturity['agreedRate'])!=agreed or maturity['quoteConvention']!=conventions['quoteConvention']
            or snapshot['authority']['actorId']!=str(event['recorded_by_user_account_id'])):raise PositionError('Frozen maturity closing evidence mismatch')
    recognition=snapshot.get('valuationRecognition')
    if recognition is None and kind=='FX_FORWARD_MATURITY':
        recognition=dict(date=row['valuation_effective_date'].isoformat(),basis='UTC_TRADE_DATE',timezone='UTC',reason=None)
    return conventions|dict(kind='FX_RATE_BOOKING',valuationRecognition=recognition,maturityEvidence=maturity)


def _tenant(c,strategy):
    return c.scalar(select(m.strategy.c.tenant_id).where(m.strategy.c.strategy_id==strategy))
