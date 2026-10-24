"""Whole-swap mark conventions from immutable BOOKED evidence only.

Older generic bookings already retained the approved definition and convention.
Reading those facts is not a migration or a substitution of today's master data.
Unknown legacy leg-only swaps deliberately remain unsupported.
"""
import json
from decimal import Decimal, localcontext, Inexact
from uuid import UUID
from .swap_terms import GenericSwapTerms


def frozen_swap_conventions(row, snapshot):
    """Validate booked units/quotation and return the compact valuation contract."""
    try:
        economics=snapshot['economics'];context=economics['terms']
        details=context['swapDetails'];facts=details['sourceFacts']
        terms=GenericSwapTerms.model_validate(details['genericTerms'])
        approved=facts['approvedDefinition'];generic=facts['genericDefinition']
        node=UUID(context['instrumentId']);definition=UUID(str(approved['instrument_definition_version_id']))
        basis='SWAP_VALUE_PER_UNIT' if terms.quantity_unit=='UNITS' else 'SWAP_VALUE_PER_NOTIONAL'
        if (snapshot['kind']!='PRODUCT_BOOKING' or context['kind']!='SWAP'
            or context.get('listingId') is not None or context['executionRoute']!='OTC'
            or node!=UUID(str(row['reference_instrument_node_id'])) or node!=UUID(str(row['trade_subject_reference_node_id']))
            or node!=UUID(str(approved['instrument_node_id'])) or approved['status']!='APPROVED'
            or UUID(str(approved['base_currency_id']))!=terms.notional_currency_id
            or UUID(str(generic['instrument_definition_version_id']))!=definition or generic['schema_version']!=terms.schema_version
            or GenericSwapTerms.model_validate(generic['economics_payload'])!=terms
            or context['maturityDate']!=terms.maturity_date.isoformat()):
            raise ValueError('Inconsistent frozen swap definition')
        stored=facts['bookingConvention']
        if UUID(str(stored['instrument_node_id']))!=node:raise ValueError('Frozen swap convention identity differs')
        for convention in (context['convention'],json.loads(stored['convention_payload'])):
            if (convention['kind']!='SWAP' or convention['quantityUnit']!=terms.quantity_unit
                or convention['priceBasis']!=basis or Decimal(convention['quoteFactor'])!=terms.quote_factor
                or UUID(convention['priceCurrencyId'])!=terms.quote_currency_id or convention['otcAllowed'] is not True):
                raise ValueError('Inconsistent frozen swap quotation')
        if (row['quantity_unit']!=terms.quantity_unit or row['price_basis']!=basis
            or UUID(str(row['price_currency_id']))!=terms.quote_currency_id):
            raise ValueError('Booked swap units/currency differ from frozen quotation')
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            quantity=Decimal(row['quantity']);price=Decimal(row['execution_price'])
            if not quantity.is_finite() or not quantity or not price.is_finite():raise ValueError('Invalid swap execution')
            if (Decimal(economics['amount'])!=quantity*price/terms.quote_factor
                or Decimal(economics['bookedNotional'])!=terms.booked_reference_notional(abs(quantity))
                or (Decimal(economics['bookedUnits']) if economics.get('bookedUnits') is not None else None)
                    !=(abs(quantity) if terms.quantity_unit=='UNITS' else None)):
                raise ValueError('Frozen swap execution economics differ')
        proof=dict(instrumentDefinitionId=str(definition),instrumentId=str(node),productBasis='SWAP',
            priceCurrencyId=str(terms.quote_currency_id),unitMultiplier='1',quoteFactor=str(terms.quote_factor),
            priceBasis=basis,swapPriceBasis='WHOLE_SWAP_MTM_PER_'+('UNIT' if terms.quantity_unit=='UNITS' else 'NOTIONAL'),
            maturityDate=terms.maturity_date.isoformat())
        explicit=snapshot.get('valuationConventions')
        if explicit is not None:
            for name,value in proof.items():
                equal=Decimal(explicit[name])==Decimal(value) if name in ('unitMultiplier','quoteFactor') else explicit[name]==value
                if not equal:raise ValueError('Explicit swap valuation metadata conflicts with frozen terms')
        return proof
    except (KeyError,TypeError,ArithmeticError) as exc:
        raise ValueError('Complete consistent frozen generic swap evidence required') from exc
