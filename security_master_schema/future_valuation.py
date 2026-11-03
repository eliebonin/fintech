"""Original futures booking economics; no current multiplier substitution."""
from copy import deepcopy
from decimal import Decimal,localcontext,Inexact
from hashlib import sha256
import json
from uuid import UUID
from .booking_conventions import FutureConvention
from .future_economics import require_linear_future


def frozen_future_conventions(row,snapshot,identities):
    try:
        economics=snapshot['economics'];terms=economics['terms'];cv=FutureConvention.model_validate(terms['convention'])
        require_linear_future(cv)
        parent=UUID(terms['instrumentId']);listing=UUID(terms['listingId'])
        if (snapshot['kind']!='PRODUCT_BOOKING' or terms['kind']!='FUTURE' or terms['executionRoute']!='LISTED'
            or parent!=row['reference_instrument_node_id'] or listing!=row['trade_subject_reference_node_id']
            or row['quantity_unit']!='CONTRACTS' or row['price_basis']!=cv.price_basis
            or row['price_currency_id']!=cv.price_currency_id or row['execution_venue_id']!=UUID(identities['venueId'])):
            raise ValueError('Inconsistent frozen futures contract quotation')
        # The original context hash contained these version IDs and the pre-ready
        # context. Rebuild it from retained facts, not today's reference labels.
        original=deepcopy(terms);original.update(bookingEligible=False,termsFingerprint=None)
        original.pop('readinessStatus',None)
        digest=sha256(json.dumps(dict(identities)|original,sort_keys=True,default=str).encode()).hexdigest()
        if digest!=terms['termsFingerprint']:raise ValueError('Original futures context fingerprint differs')
        quantity=Decimal(row['quantity']);price=Decimal(row['execution_price'])
        if not quantity.is_finite() or not quantity or quantity!=quantity.to_integral_value():raise ValueError('Whole futures contracts required')
        if not price.is_finite() or price<0 and not cv.allow_negative_price:raise ValueError('Invalid frozen futures price')
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            amount=abs(quantity)*price*cv.monetary_multiplier/cv.quote_factor
        if (Decimal(economics['amount'])!=amount or economics['amountKind']!='REFERENCE_CONTRACT_VALUE'
            or economics.get('direction') is not None):raise ValueError('Futures reference amount differs from booked units')
        day=row['trade_datetime_utc'].date()
        if day<cv.effective_from or row['trade_datetime_utc']>cv.last_trading_at_utc:raise ValueError('Execution outside frozen futures trading dates')
        return dict(kind='FUTURE_PRICE_BOOKING',instrumentId=str(parent),instrumentDefinitionId=identities['definitionId'],
            listingDefinitionId=identities['listingDefinitionId'],productBasis='FUTURE',priceBasis=cv.price_basis,
            priceCurrencyId=str(cv.price_currency_id),unitMultiplier=str(cv.monetary_multiplier),quoteFactor=str(cv.quote_factor),
            allowNegativePrice=cv.allow_negative_price,futureConvention=cv.model_dump(mode='json',by_alias=True),
            originalContextFingerprint=terms['termsFingerprint'])
    except (KeyError,TypeError,ArithmeticError) as exc:
        raise ValueError('Complete consistent frozen futures economics required') from exc
