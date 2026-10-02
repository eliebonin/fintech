"""Swap booking on disposable databases; no operating trades or terms touched."""
from datetime import date
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_product_booking_api import approve
from tests.test_swap_booking_rules import convention


@pytest.fixture(scope='module')
def swap():
    node=uuid4()
    original=DEMO_IDS['autocall_total_return_swap_node']
    with get_engine().begin() as connection:
        for table,key in [(m.financial_reference_node,'reference_node_id'),(m.instrument,'instrument_node_id'),
                          (m.instrument_definition_version,'instrument_node_id'),(m.instrument_dates,'instrument_node_id'),(m.swap_terms,'instrument_node_id')]:
            values=dict(connection.execute(select(table).where(table.c[key]==original)).mappings().one())
            values[key]=node
            for primary in table.primary_key.columns:
                if primary.name!=key:values[primary.name]=uuid4()
            if table is m.financial_reference_node:values.update(canonical_name=f'Synthetic autocall swap {node}',internal_code=f'SWAP_{node.hex}')
            if table in (m.instrument,m.instrument_definition_version):values['effective_from']=date(2026,9,1)
            if table is m.instrument_dates:values.update(effective_date=date(2026,9,1),maturity_date=date(2029,8,28))
            connection.execute(table.insert().values(**values))
        schedule=uuid4()
        connection.execute(m.schedule.insert().values(schedule_id=schedule,owner_reference_node_id=node,schedule_type='RESET_PAYMENT'))
        connection.execute(m.schedule_event.insert().values(schedule_id=schedule,event_sequence=1,event_type='RESET',event_date=date(2026,11,28),payment_date=date(2026,12,4)))
        for leg in connection.execute(select(m.swap_leg).where(m.swap_leg.c.swap_instrument_node_id==original)).mappings():
            values=dict(leg)|dict(swap_leg_id=uuid4(),swap_instrument_node_id=node,currency_id=DEMO_IDS['gbp_currency'],schedule_id=schedule)
            connection.execute(m.swap_leg.insert().values(**values))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=DEMO_IDS['tenant'],status='ACTIVE'))
    approve(request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=str(node),convention=convention(priceCurrencyId=str(DEMO_IDS['gbp_currency'])))))
    return str(node)


def context(swap):
    response=request('GET',f'/v1/trades/product-instruments/{swap}?asOfDate=2026-10-01')
    assert response.status_code==200,response.text
    return response.json()['data']


def ticket(swap,**changes):
    return dict(instrumentId=swap,executionRoute='OTC',strategyId=str(DEMO_IDS['strategy']),side='BUY',quantity='1000000',
        executionPrice='2',tradeDatetime='2026-10-01T10:00:00Z',counterpartyOrganisationId=str(DEMO_IDS['bank_a_organisation']),
        expectedTermsFingerprint=context(swap)['termsFingerprint'])|changes


def test_swap_context(swap):
    value=context(swap)
    assert value['bookingEligible'],value
    assert value['kind']=='SWAP' and value['convention']['priceBasis']=='SWAP_VALUE_PER_NOTIONAL'
    details=value['swapDetails']
    assert details['performanceReferenceId']==str(DEMO_IDS['autocall_instrument_node'])
    assert details['fundingSpread']=='0.01000000'
    assert details['performanceDirection']=='RECEIVE' and details['fundingDirection']=='PAY'
    response=request('GET','/v1/trades/product-instruments?kind=SWAP&route=OTC&q=Synthetic&asOfDate=2026-10-01')
    assert response.status_code==200,response.text
    assert any(row['instrumentId']==swap for row in response.json()['data'])


@pytest.mark.parametrize('side,price,want',[('BUY','2','20000'),('BUY','0','0'),('BUY','-1.5','-15000'),('SELL','2','-20000')])
def test_swap_one_trade_and_replay(swap,side,price,want):
    data=ticket(swap,side=side,executionPrice=price);key=str(uuid4())
    with get_engine().connect() as connection:before=connection.scalar(select(func.count()).select_from(m.trade))
    response=request('POST','/v1/trades/swaps',data,key)
    assert response.status_code==201,response.text
    trade=response.json()['data']['trade'];economics=trade['productEconomics']
    assert economics['amount']==want and economics['amountKind']=='ENTRY_REFERENCE_VALUE' and economics['direction'] is None
    assert trade['settlementDate'] is None and trade['listingId'] is None
    assert trade['quantityUnit']=='NOMINAL' and trade['priceBasis']=='SWAP_VALUE_PER_NOTIONAL'
    assert float(trade['executionPrice'])==float(price)
    assert float(trade['quantity'])==(-1000000 if side=='SELL' else 1000000)
    assert request('POST','/v1/trades/swaps',data,key).json()['data']['trade']['tradeId']==trade['tradeId']
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.trade))==before+1
        assert connection.scalar(select(func.count()).select_from(m.trade_fee).where(m.trade_fee.c.trade_id==UUID(trade['tradeId'])))==0
    assert request('POST','/v1/trades/swaps',data|{'executionPrice':'3'},key).status_code==409
    assert request('GET',f"/v1/trades/{trade['tradeId']}").json()['data']['trade']['productEconomics']==economics


@pytest.mark.parametrize('changes',[{'settlementDate':'2026-10-05'},{'quantity':'1000001'},{'counterpartyOrganisationId':None},
    {'executionPrice':None},{'priceType':'CLEAN'},{'tradeDatetime':'2026-10-01T10:00:00'},{'executionRoute':'LISTED','listingId':str(uuid4())}])
def test_swap_invalid_inputs(swap,changes):
    response=request('POST','/v1/trades/swaps',ticket(swap,**changes))
    assert response.status_code in {422,404},response.text


def test_swap_stale_funding_and_snapshot(swap):
    data=ticket(swap);first=request('POST','/v1/trades/swaps',data)
    assert first.status_code==201,first.text
    with get_engine().begin() as connection:
        connection.execute(m.swap_leg.update().where(m.swap_leg.c.swap_instrument_node_id==UUID(swap),m.swap_leg.c.leg_role=='FUNDING').values(spread='0.02'))
    try:
        assert request('POST','/v1/trades/swaps',data).status_code==409
        old=request('GET',f"/v1/trades/{first.json()['data']['trade']['tradeId']}").json()['data']['trade']['productEconomics']
        assert old['terms']['swapDetails']['fundingSpread']=='0.01000000'
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.swap_leg.update().where(m.swap_leg.c.swap_instrument_node_id==UUID(swap),m.swap_leg.c.leg_role=='FUNDING').values(spread='0.01'))


def test_missing_funding_facts_and_hidden_swap(swap):
    with get_engine().begin() as connection:
        connection.execute(m.swap_leg.update().where(m.swap_leg.c.swap_instrument_node_id==UUID(swap),m.swap_leg.c.leg_role=='FUNDING').values(spread=None))
    try:assert not context(swap)['bookingEligible']
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.swap_leg.update().where(m.swap_leg.c.swap_instrument_node_id==UUID(swap),m.swap_leg.c.leg_role=='FUNDING').values(spread='0.01'))
    assert request('GET',f'/v1/trades/product-instruments/{swap}',tenant='second_tenant').status_code in {403,404}


def test_swap_pnl_deferred(swap):
    assert request('POST','/v1/trades/swaps',ticket(swap)).status_code==201
    with get_engine().connect() as connection:code=connection.scalar(select(m.strategy.c.strategy_code).where(m.strategy.c.strategy_id==DEMO_IDS['strategy']))
    assert request('GET',f'/v1/portfolios/{code}/pnl?asOfDate=2026-10-01').status_code==422


def test_retired_underlying_projection_is_ineligible(swap):
    from apps.reference_api.swap_booking import load_swap_context
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try:
            connection.execute(m.instrument.update().where(m.instrument.c.instrument_node_id==DEMO_IDS['autocall_instrument_node']).values(is_current=False))
            with pytest.raises(ValueError,match='current active'):
                load_swap_context(connection,DEMO_IDS['tenant'],UUID(swap),date(2026,10,1))
        finally:
            transaction.rollback()


def test_swap_concurrent_replay(swap):
    from concurrent.futures import ThreadPoolExecutor
    data=ticket(swap); key=str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:request('POST','/v1/trades/swaps',data,key),range(2)))
    assert all(response.status_code==201 for response in responses),[response.text for response in responses]
    assert len({response.json()['data']['trade']['tradeId'] for response in responses})==1


def test_invalid_swap_property_rolls_back(swap):
    with get_engine().connect() as connection:
        before=connection.scalar(select(func.count()).select_from(m.trade))
    response=request('POST','/v1/trades/swaps',ticket(swap,properties=[{'definitionId':str(uuid4()),'value':'0'}]))
    assert response.status_code==422,response.text
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.trade))==before


def test_changed_swap_schedule_invalidates_review(swap):
    data=ticket(swap)
    with get_engine().begin() as connection:
        schedule=connection.scalar(select(m.swap_leg.c.schedule_id).where(m.swap_leg.c.swap_instrument_node_id==UUID(swap)).limit(1))
        connection.execute(m.schedule_event.update().where(m.schedule_event.c.schedule_id==schedule).values(payment_date=date(2026,12,5)))
    try:
        response=request('POST','/v1/trades/swaps',data)
        assert response.status_code==409,response.text
        assert response.json()['code']=='product.terms_changed'
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.schedule_event.update().where(m.schedule_event.c.schedule_id==schedule).values(payment_date=date(2026,12,4)))


@pytest.mark.parametrize('retire_group',[False,True])
def test_retired_autocall_trigger_is_ineligible(swap,retire_group):
    from apps.reference_api.swap_booking import load_swap_context
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try:
            terms=connection.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==DEMO_IDS['autocall_instrument_node'],m.structured_product_terms.c.is_current))
            groups=select(m.structured_product_condition_group.c.condition_group_id).where(m.structured_product_condition_group.c.structured_product_terms_id==terms)
            if retire_group:
                connection.execute(m.structured_product_condition_group.update().where(m.structured_product_condition_group.c.condition_group_id.in_(groups)).values(status='RETIRED'))
            else:
                connection.execute(m.condition_group_action.update().where(m.condition_group_action.c.condition_group_id.in_(groups),m.condition_group_action.c.action_type=='REDEEM_PARENT').values(status='RETIRED'))
            with pytest.raises(ValueError,match='autocall redemption'):
                load_swap_context(connection,DEMO_IDS['tenant'],UUID(swap),date(2026,10,1))
        finally:transaction.rollback()


def test_component_coupon_override_event_changes_fingerprint(swap):
    from apps.reference_api.product_booking import load_context
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try:
            terms=connection.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==DEMO_IDS['autocall_instrument_node'],m.structured_product_terms.c.is_current))
            component=connection.scalar(select(m.instrument_composition.c.component_reference_node_id).where(m.instrument_composition.c.parent_instrument_node_id==DEMO_IDS['autocall_instrument_node']).limit(1))
            schedule,event=uuid4(),uuid4()
            connection.execute(m.schedule.insert().values(schedule_id=schedule,owner_reference_node_id=component,schedule_type='RESET_PAYMENT'))
            connection.execute(m.schedule_event.insert().values(schedule_event_id=event,schedule_id=schedule,event_sequence=1,event_type='RESET',event_date=date(2026,11,28)))
            programmes=select(m.structured_product_coupon_programme.c.coupon_programme_id).where(m.structured_product_coupon_programme.c.structured_product_terms_id==terms)
            connection.execute(m.structured_product_coupon_period.update().where(m.structured_product_coupon_period.c.coupon_programme_id.in_(programmes)).values(observation_event_id=event))
            before=load_context(connection,DEMO_IDS['tenant'],UUID(swap),as_of=date(2026,10,1))
            connection.execute(m.schedule_event.update().where(m.schedule_event.c.schedule_event_id==event).values(event_date=date(2026,11,29)))
            after=load_context(connection,DEMO_IDS['tenant'],UUID(swap),as_of=date(2026,10,1))
            assert before.terms_fingerprint!=after.terms_fingerprint
        finally:transaction.rollback()


def test_booking_locks_underlying_projection(swap):
    from apps.reference_api.swap_booking import load_swap_context
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    with get_engine().connect() as connection, get_engine().connect() as competitor:
        transaction=connection.begin(); other=competitor.begin()
        try:
            load_swap_context(connection,DEMO_IDS['tenant'],UUID(swap),date(2026,10,1),lock=True)
            competitor.execute(text("SET LOCAL lock_timeout='100ms'"))
            with pytest.raises(DBAPIError,match='lock timeout'):
                competitor.execute(m.instrument.update().where(m.instrument.c.instrument_node_id==DEMO_IDS['autocall_instrument_node']).values(is_current=False))
        finally:
            other.rollback();transaction.rollback()


def test_swap_persistence_failure_rolls_back(swap,monkeypatch):
    from apps.reference_api import repository
    def fail(*args,**kwargs):raise RuntimeError('Synthetic persistence failure')
    monkeypatch.setattr(repository,'persist_trade_annotations',fail)
    data=ticket(swap)
    with get_engine().connect() as connection:before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(RuntimeError,match='Synthetic persistence failure'):
        request('POST','/v1/trades/swaps',data)
    with get_engine().connect() as connection:assert connection.scalar(select(func.count()).select_from(m.trade))==before


def test_swap_required_properties_accept_zero_and_false(swap):
    from apps.reference_api.trade_configuration import create_property,retire_property
    actor=DEMO_IDS['demo_user_account'];tenant=DEMO_IDS['tenant'];definitions=[]
    try:
        with get_engine().begin() as connection:
            for kind in ['BOOLEAN','DECIMAL']:
                definitions.append(create_property(connection,tenant,actor,dict(code='SWAP_TEST_'+uuid4().hex,label='Synthetic required '+kind,valueType=kind,required=True,acknowledgeRequiredImpact=True,choices=[]))['definitionId'])
        data=ticket(swap)
        assert request('POST','/v1/trades/swaps',data).status_code==422
        data['properties']=[dict(definitionId=str(definitions[0]),value=False),dict(definitionId=str(definitions[1]),value='0')]
        response=request('POST','/v1/trades/swaps',data)
        assert response.status_code==201,response.text
        properties=response.json()['data']['properties']
        assert {str(item['definitionId']):item['value'] for item in properties}=={str(definitions[0]):False,str(definitions[1]):'0'}
    finally:
        with get_engine().begin() as connection:
            for definition in definitions:retire_property(connection,tenant,actor,definition)
