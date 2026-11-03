"""Same linear variation for index, cash-crypto and deliverable crypto contracts."""
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
import json
from uuid import UUID
import pytest
from security_master_schema.booking_conventions import FutureConvention
from security_master_schema.future_valuation import frozen_future_conventions
from tests.test_future_frozen_valuation import frozen


def crypto_frozen(settlement='CASH',size='5'):
    row,snapshot,identities=frozen()
    terms=snapshot['economics']['terms'];cv=terms['convention']
    cv.update(priceBasis='UNDERLYING_UNIT',settlementMethod=settlement,contractSize=size,
        contractSizeCurrencyId=str(UUID(int=20)),monetaryMultiplier=size,tickSize='5')
    if settlement=='PHYSICAL':cv.update(deliveryStartDate=cv['finalSettlementDate'],deliveryEndDate=cv['finalSettlementDate'])
    row.update(execution_price=D('100000'),price_basis='UNDERLYING_UNIT')
    snapshot['economics']['amount']=str(D(2)*D('100000')*D(size))
    original=deepcopy(terms);original.update(bookingEligible=False,termsFingerprint=None);original.pop('readinessStatus',None)
    terms['termsFingerprint']=sha256(json.dumps(identities|original,sort_keys=True,default=str).encode()).hexdigest()
    return row,snapshot,identities


@pytest.mark.parametrize('settlement',['CASH','PHYSICAL'])
def test_linear_crypto_frozen_economics_preserve_contract_size_and_original_identity(settlement):
    row,snapshot,identities=crypto_frozen(settlement)
    result=frozen_future_conventions(row,snapshot,identities)
    assert result['priceBasis']=='UNDERLYING_UNIT' and result['unitMultiplier']=='5'
    assert result['futureConvention']['settlementMethod']==settlement
    assert result['originalContextFingerprint']==snapshot['economics']['terms']['termsFingerprint']


@pytest.mark.parametrize('settlement',['CASH','PHYSICAL'])
def test_shared_linear_capability_accepts_coherent_existing_contract_forms(settlement):
    from security_master_schema.future_economics import require_linear_future
    _,snapshot,_=crypto_frozen(settlement)
    require_linear_future(FutureConvention.model_validate(snapshot['economics']['terms']['convention']))
    _,index,_=frozen()
    require_linear_future(FutureConvention.model_validate(index['economics']['terms']['convention']))


@pytest.mark.parametrize('price,expected',[('100000','1000000'),('0','0'),('-5','-50')])
def test_linear_asset_unit_execution_reference_value(price,expected):
    from security_master_schema.product_booking import execution_amount
    assert execution_amount('2',price,quantity_unit='CONTRACTS',price_basis='UNDERLYING_UNIT',quote_factor='1',multiplier='5')==D(expected)


@pytest.mark.parametrize('mutation',[{'price_basis':'INVERSE'},{'settlement_method':'OTHER'},
    {'contract_size':D('10')},{'contract_size_currency_id':None},{'quote_factor':D(0)}])
def test_shared_capability_rejects_unsupported_or_incoherent_quotation_even_if_a_model_was_copied(mutation):
    from security_master_schema.future_economics import require_linear_future
    _,snapshot,_=crypto_frozen()
    cv=FutureConvention.model_validate(snapshot['economics']['terms']['convention']).model_copy(update=mutation)
    with pytest.raises(ValueError):require_linear_future(cv)


@pytest.mark.parametrize('settlement',['CASH','PHYSICAL'])
def test_crypto_mark_context_returns_actual_contract_price_dimensions(settlement):
    from types import SimpleNamespace as S
    from valuation.futures_pnl import future_mark_context
    row,snapshot,identities=crypto_frozen(settlement)
    proof=frozen_future_conventions(row,snapshot,identities)
    booking=S(product_basis='FUTURE',quantity_unit='CONTRACTS',product_evidence=proof,currency_id=row['price_currency_id'],
        unit_multiplier=D(5),quote_factor=D(1),valuation_effective_date=None)
    trade=UUID(int=30);subject=row['trade_subject_reference_node_id'];stamp=row['trade_datetime_utc']
    projection=S(buckets=[S(key=S(subject_id=subject),trade_ids=[trade])],facts=[S(booking=booking,trade_id=trade,effective_at=stamp)],request=S(daily=True))
    dimensions,cv=future_mark_context(projection,subject,stamp)
    assert dict(dimensions)=={'CONTRACT_INSTRUMENT_ID':str(row['reference_instrument_node_id']),'FUTURE_PRICE_BASIS':'UNDERLYING_UNIT'}
    assert cv.monetary_multiplier==5


@pytest.mark.parametrize('settlement,size,held,sell,want',[
    ('CASH','5','2',None,'10000'),('PHYSICAL','1','3',None,'3000'),
    ('CASH','5','0','2','5000'),('CASH','5','2','-1','7500'),
    ('PHYSICAL','1','2','-2','1000'),('CASH','5','2','-3','2500'),('CASH','5','-2',None,'-10000')])
def test_linear_contract_variation_uses_contracts_and_multiplier_once(settlement,size,held,sell,want):
    from dataclasses import replace
    from positions.reconstruction import reconstruct
    from tests.test_futures_pnl import future
    from tests.test_position_reconstruction import request,OPEN,CLOSE,SUBJECT,CURRENCY
    from valuation.position_calculation import attribute_projection,MarkKey
    facts=[]
    for number,quantity,stamp,price in [(1,held,OPEN,'100000'),(2,sell,CLOSE,'100500')]:
        if quantity is None or D(quantity)==0:continue
        fact=future(number,quantity,stamp,price)
        facts.append(replace(fact,booking=replace(fact.booking,unit_multiplier=D(size),
            product_evidence={'allowNegativePrice':False,'settlementMethod':settlement})))
    projection=reconstruct(facts,request())
    marks={MarkKey(SUBJECT,OPEN):D('100000'),MarkKey(SUBJECT,CLOSE):D('101000')}
    result=attribute_projection(projection,marks,CURRENCY)
    assert result.market_pnl==D(want) and result.settlement_variation==D(want)


def test_physical_contract_final_mark_boundary_does_not_authorize_new_trades_or_erase_open_exposure():
    from types import SimpleNamespace as S
    from datetime import datetime,timezone
    from valuation.futures_pnl import future_mark_context
    row,snapshot,identities=crypto_frozen('PHYSICAL');proof=frozen_future_conventions(row,snapshot,identities)
    booking=S(product_basis='FUTURE',quantity_unit='CONTRACTS',product_evidence=proof,currency_id=row['price_currency_id'],
        unit_multiplier=D(5),quote_factor=D(1),valuation_effective_date=None)
    trade=UUID(int=30);subject=row['trade_subject_reference_node_id']
    projection=S(buckets=[S(key=S(subject_id=subject),trade_ids=[trade])],facts=[S(booking=booking,trade_id=trade,effective_at=row['trade_datetime_utc'])],request=S(daily=True))
    future_mark_context(projection,subject,datetime(2026,12,18,23,tzinfo=timezone.utc))
    with pytest.raises(ValueError,match='recorded Ops closure'):
        future_mark_context(projection,subject,datetime(2026,12,19,23,tzinfo=timezone.utc))


def test_retained_variation_explains_frozen_physical_delivery_conventions():
    from dataclasses import replace
    from positions.reconstruction import reconstruct
    from tests.test_futures_pnl import future
    from tests.test_position_reconstruction import request,OPEN,CLOSE,SUBJECT,CURRENCY
    from valuation.position_calculation import attribute_projection,MarkKey
    _,snapshot,_=crypto_frozen('PHYSICAL');cv=snapshot['economics']['terms']['convention']
    fact=future(1,'2',OPEN,'100000')
    fact=replace(fact,booking=replace(fact.booking,unit_multiplier=D(5),product_evidence={'futureConvention':cv,'allowNegativePrice':False}))
    result=attribute_projection(reconstruct([fact],request()),{MarkKey(SUBJECT,OPEN):D('100000'),MarkKey(SUBJECT,CLOSE):D('101000')},CURRENCY)
    assert result.lines[0].economic_evidence[0]['contractConvention']==cv


@pytest.mark.parametrize('price,asset',[(30,20),(20,30)])
def test_booking_locks_quote_and_asset_currency_roles_in_one_global_order(price,asset):
    from types import SimpleNamespace as S
    from apps.reference_api.product_booking import lock_booking_currency
    from tests.test_future_specification_rules import specification
    locks=[];price_id,asset_id=UUID(int=price),UUID(int=asset)
    record=dict(base_currency_id=price_id,specification_payload=json.dumps(specification(contractSizeCurrencyId=str(asset_id))))
    class Connection:
        def scalar(self,statement):return price_id
        def execute(self,statement):
            if 'base_currency_id' in str(statement):return S(mappings=lambda:S(one_or_none=lambda:record))
            locks.extend(statement.compile().params.values())
            return S(all=lambda:[])
    assert lock_booking_currency(Connection(),UUID(int=40))==(price_id,frozenset((price_id,asset_id)))
    assert locks==sorted([price_id,asset_id])
