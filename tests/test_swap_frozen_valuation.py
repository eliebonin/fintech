"""Frozen swap economics, including bookings predating explicit valuation metadata."""
from copy import deepcopy
from decimal import Decimal as D
from uuid import uuid4
import json
import pytest
from tests.test_swap_creation_rules import payload


def frozen(unit='UNITS'):
    node,definition,currency=map(str,(uuid4(),uuid4(),uuid4()))
    terms=payload(notionalCurrencyId=currency,quoteCurrencyId=currency,quoteFactor='100',leverage='1.5')
    if unit=='UNITS':terms.update(quantityUnit=unit,contractualUnits='10000',notionalPerUnit='100')
    convention=dict(kind='SWAP',quantityUnit=unit,priceBasis='SWAP_VALUE_PER_UNIT' if unit=='UNITS' else 'SWAP_VALUE_PER_NOTIONAL',
        quoteFactor='100',priceCurrencyId=currency,otcAllowed=True)
    snapshot=dict(kind='PRODUCT_BOOKING',economics=dict(terms=dict(kind='SWAP',instrumentId=node,listingId=None,
        executionRoute='OTC',maturityDate=terms['maturityDate'],convention=convention,
        swapDetails=dict(genericTerms=terms,sourceFacts=dict(
            approvedDefinition=dict(instrument_definition_version_id=definition,instrument_node_id=node,base_currency_id=currency,status='APPROVED'),
            genericDefinition=dict(instrument_definition_version_id=definition,schema_version=1,economics_payload=terms),
            bookingConvention=dict(instrument_node_id=node,convention_payload=json.dumps(convention))))),
        amount='-2',bookedNotional='10000' if unit=='UNITS' else '100',bookedUnits='100' if unit=='UNITS' else None))
    row=dict(reference_instrument_node_id=node,trade_subject_reference_node_id=node,quantity_unit=unit,quantity=D('100'),
        execution_price=D('-2'),price_basis=convention['priceBasis'],price_currency_id=currency)
    return row,snapshot


@pytest.mark.parametrize('unit',['UNITS','NOMINAL'])
def test_legacy_snapshot_normalizes_without_changing_frozen_evidence(unit):
    from security_master_schema.swap_valuation import frozen_swap_conventions
    row,snapshot=frozen(unit);before=deepcopy(snapshot)
    proof=frozen_swap_conventions(row,snapshot)
    assert proof['unitMultiplier']=='1' and proof['quoteFactor']=='100'
    assert proof['swapPriceBasis']=='WHOLE_SWAP_MTM_PER_'+('UNIT' if unit=='UNITS' else 'NOTIONAL')
    assert snapshot==before
    assert frozen_swap_conventions(row,snapshot|dict(valuationConventions=proof))==proof


@pytest.mark.parametrize('change',['quantity','currency','factor','definition','generic','explicit','missing'])
def test_inconsistent_or_incomplete_frozen_evidence_is_refused(change):
    from security_master_schema.swap_valuation import frozen_swap_conventions
    row,snapshot=frozen();proof=frozen_swap_conventions(row,snapshot)
    terms=snapshot['economics']['terms'];facts=terms['swapDetails']['sourceFacts']
    if change=='quantity':row['quantity']=D(101)
    if change=='currency':row['price_currency_id']=str(uuid4())
    if change=='factor':terms['convention']['quoteFactor']='1'
    if change=='definition':facts['genericDefinition']['instrument_definition_version_id']=str(uuid4())
    if change=='generic':terms['swapDetails']['genericTerms']=terms['swapDetails']['genericTerms']|dict(leverage='2')
    if change=='explicit':snapshot['valuationConventions']=proof|dict(unitMultiplier='1.5')
    if change=='missing':terms['swapDetails'].pop('sourceFacts')
    with pytest.raises(ValueError):frozen_swap_conventions(row,snapshot)
