"""Listed option approval and booking against a disposable migrated database."""
from uuid import uuid4
import pytest
from tests.test_fx_forward_booking_api import request
from security_master_schema.demo_data import DEMO_IDS
from apps.reference_api.db import get_engine
from apps.reference_api.option_booking import book,load
from apps.reference_api.contracts import OptionBookingRequest
from security_master_schema import models as m
from sqlalchemy import select,update,func
from uuid import UUID
from decimal import Decimal


@pytest.fixture(scope='module')
def listing():
    proposed=request('POST','/v1/option-proposals',dict(canonicalName=f'Synthetic option {uuid4()}',effectiveFrom='2026-09-01',underlyingId=str(DEMO_IDS['hsbc_instrument_node']),optionType='CALL',strike='10',strikeCurrencyId=str(DEMO_IDS['gbp_currency']),premiumCurrencyId=str(DEMO_IDS['gbp_currency']),premiumMultiplier='100',deliverableUnits='100',expiryDate='2027-09-17',lastTradingAtUtc='2027-09-17T16:30:00Z',exerciseStyle='AMERICAN',settlementMethod='PHYSICAL'))
    assert proposed.status_code==201,proposed.text
    queue=request('GET','/v1/work-queue')
    item=next(item for item in queue.json()['items'] if item['referenceId']==proposed.json()['data']['proposalId'])
    assert item['reviewPath']==f"/reference-data/review/{proposed.json()['data']['proposalId']}"
    assert 'equity proposal' not in item['detail']
    approved=request('POST',f"/v1/reference-data-proposals/{proposed.json()['data']['proposalId']}/decision",dict(decision='APPROVED',reason='Verified synthetic option terms.'))
    assert approved.status_code==200,approved.text
    instrument=approved.json()['data']['referenceNodeId']
    proposed=request('POST','/v1/listing-proposals',dict(instrumentId=instrument,listing=dict(marketVenueId=str(DEMO_IDS['xlon_venue']),tradingSymbol=f'OPT{uuid4().hex[:8]}',tradingCurrencyId=str(DEMO_IDS['gbp_currency']),quoteFactor='1',unitMultiplier='100',effectiveFrom='2026-09-01')))
    assert proposed.status_code==201,proposed.text
    approved=request('POST',f"/v1/reference-data-proposals/{proposed.json()['data']['proposalId']}/decision",dict(decision='APPROVED',reason='Verified synthetic option listing.'))
    assert approved.status_code==200,approved.text
    from sqlalchemy import select
    from apps.reference_api.db import get_engine
    from security_master_schema import models as m
    with get_engine().connect() as connection:
        return str(connection.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==instrument)))


def payload(listing,**changes):
    response=request('GET',f'/v1/trades/option-listings/{listing}')
    assert response.status_code==200,response.text
    assert response.json()['data']['bookingEligible'],response.text
    return dict(listingId=listing,strategyId=str(DEMO_IDS['strategy']),side='BUY',quantity='10',executionPrice='2.5',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05',positionEffect='OPEN',expectedTermsFingerprint=response.json()['data']['termsFingerprint'])|changes


def test_option_instrument_inspection(listing):
    listing_view=request('GET',f'/v1/trades/option-listings/{listing}').json()['data']
    detail=request('GET',f"/v1/instruments/{listing_view['instrumentId']}")
    assert detail.status_code==200,detail.text
    terms=detail.json()['data']['optionTerms']
    assert terms['optionType']=='CALL'
    assert terms['underlyingName']=='HSBC Demo ordinary shares'
    assert terms['premiumMultiplier']=='100'
    assert terms['deliverableUnits']=='100'
    assert terms['lastTradingAtUtc']=='2027-09-17T16:30:00+00:00'
    assert terms['premiumStyle']=='UPFRONT'



@pytest.mark.parametrize('side,effect,direction',[('BUY','OPEN','PAY'),('SELL','CLOSE','RECEIVE')])
def test_book_option(listing,side,effect,direction):
    response=request('POST','/v1/trades/options',payload(listing,side=side,positionEffect=effect))
    assert response.status_code==201,response.text
    trade=response.json()['data']['trade']
    assert trade['quantityUnit']=='CONTRACTS'
    assert trade['priceBasis']=='OPTION_PREMIUM'
    assert trade['positionEffect']==effect
    assert trade['optionEconomics']['grossPremium']=='2500'
    assert trade['optionEconomics']['premiumDirection']==direction


@pytest.mark.parametrize('change',[{'quantity':'1.5'},{'executionPrice':'-1'},{'positionEffect':'MIXED'},{'tradeDatetime':'2027-09-17T16:30:01Z','settlementDate':'2027-09-20'}])
def test_reject_invalid_option(listing,change):
    response=request('POST','/v1/trades/options',payload(listing,**change))
    assert response.status_code==422,response.text


def test_option_replay(listing):
    data=payload(listing); key=str(uuid4())
    first=request('POST','/v1/trades/options',data,key)
    assert first.status_code==201,first.text
    replay=request('POST','/v1/trades/options',data|{'executionPrice':'2.500'},key)
    assert replay.status_code==201,replay.text
    assert replay.json()['data']['trade']['tradeId']==first.json()['data']['trade']['tradeId']
    conflict=request('POST','/v1/trades/options',data|{'quantity':'11'},key)
    assert conflict.status_code==409,conflict.text


@pytest.fixture
def connection():
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try: yield connection
        finally: transaction.rollback()


def direct_payload(connection,listing,**changes):
    _,terms=load(connection,DEMO_IDS['tenant'],UUID(listing))
    return OptionBookingRequest.model_validate(dict(listingId=listing,strategyId=str(DEMO_IDS['strategy']),side='BUY',positionEffect='OPEN',quantity='10',executionPrice='2.5',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05',expectedTermsFingerprint=terms.terms_fingerprint)|changes)


def direct_book(connection,data,key=None):
    return book(connection,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],data,key or str(uuid4()),'option-test')


def test_inspection_does_not_disclose_hidden_underlying(connection,listing):
    from apps.reference_api.repository import _option_inspection_terms
    row,_=load(connection,DEMO_IDS['tenant'],UUID(listing))
    connection.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==row.underlying_reference_node_id).values(scope_type='TENANT_PRIVATE',owner_tenant_id=DEMO_IDS['second_tenant']))
    terms=_option_inspection_terms(connection,DEMO_IDS['tenant'],row.instrument_node_id)
    assert terms.underlying_id is None
    assert terms.underlying_name is None
    assert terms.premium_multiplier=='100'


def test_inspection_does_not_default_missing_conventions(connection,listing):
    from apps.reference_api.repository import _option_inspection_terms
    row,_=load(connection,DEMO_IDS['tenant'],UUID(listing))
    connection.execute(update(m.option_terms).where(m.option_terms.c.instrument_node_id==row.instrument_node_id).values(premium_multiplier=None,premium_style=None,last_trading_at_utc=None))
    terms=_option_inspection_terms(connection,DEMO_IDS['tenant'],row.instrument_node_id)
    assert terms.premium_multiplier is None
    assert terms.premium_style is None
    assert terms.last_trading_at_utc is None


def clone_listing(connection,listing,overrides):
    """Construct separate fixtures without bypassing immutable version triggers."""
    row,_=load(connection,DEMO_IDS['tenant'],UUID(listing))
    instrument_id,listing_id=uuid4(),uuid4()
    for table,key,source,target in [
        (m.financial_reference_node,'reference_node_id',row.instrument_node_id,instrument_id),
        (m.instrument,'instrument_node_id',row.instrument_node_id,instrument_id),
        (m.instrument_definition_version,'instrument_node_id',row.instrument_node_id,instrument_id),
        (m.instrument_dates,'instrument_node_id',row.instrument_node_id,instrument_id),
        (m.instrument_contract_unit_terms,'instrument_node_id',row.instrument_node_id,instrument_id),
        (m.option_terms,'instrument_node_id',row.instrument_node_id,instrument_id),
        (m.financial_reference_node,'reference_node_id',UUID(listing),listing_id),
        (m.listing,'listing_node_id',UUID(listing),listing_id),
        (m.listing_definition_version,'listing_node_id',UUID(listing),listing_id)]:
        values=dict(connection.execute(select(table).where(table.c[key]==source)).mappings().one())
        values[key]=target
        for primary in table.primary_key.columns:
            if primary.name!=key:values[primary.name]=uuid4()
        if table is m.financial_reference_node:values.update(canonical_name=f'Synthetic clone {target}',internal_code=f'CLONE_{target.hex}')
        if table is m.listing:values.update(instrument_node_id=instrument_id,trading_symbol=f'OPT{listing_id.hex[:8]}')
        if table is m.listing_definition_version:values['trading_symbol']=f'OPT{listing_id.hex[:8]}'
        values.update(overrides.get(table.name,{}))
        connection.execute(table.insert().values(**values))
    return str(listing_id)


def test_historical_option_uses_execution_day_for_all_effective_terms(connection,listing):
    from datetime import date
    clone=clone_listing(connection,listing,{
        'instrument':{'effective_to':date(2026,10,2)},
        'instrument_definition_version':{'effective_to':date(2026,10,2)},
        'listing':{'effective_to':date(2026,10,2)},
        'listing_definition_version':{'effective_to':date(2026,10,2)},
        'option_terms':{'effective_to':date(2026,10,2)},
        'instrument_contract_unit_terms':{'valid_to':date(2026,10,2)}})
    _,terms=load(connection,DEMO_IDS['tenant'],UUID(clone),as_of=date(2026,10,1))
    assert terms.booking_eligible
    request=OptionBookingRequest.model_validate(dict(listingId=clone,strategyId=str(DEMO_IDS['strategy']),side='BUY',positionEffect='OPEN',quantity='10',executionPrice='2.5',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05',expectedTermsFingerprint=terms.terms_fingerprint))
    assert direct_book(connection,request).data.trade.option_economics.gross_premium=='2500'


def test_historical_option_definition_cannot_start_after_execution(connection,listing):
    from datetime import date
    from security_master_schema.option_booking import OptionBookingError
    clone=clone_listing(connection,listing,{'instrument_definition_version':{'effective_from':date(2026,10,2)}})
    data=direct_payload(connection,clone)
    with pytest.raises(OptionBookingError): direct_book(connection,data)


@pytest.mark.parametrize('table,column,value',[
    (m.option_terms,'premium_multiplier',None),(m.option_terms,'premium_style','FUTURES_STYLE'),
    (m.option_terms,'exercise_style','BERMUDAN'),(m.option_terms,'status','RETIRED'),
    (m.option_terms,'last_trading_at_utc',None),(m.instrument,'is_current',False),
    (m.instrument_definition_version,'is_current',False),(m.listing_definition_version,'is_current',False),
    (m.financial_reference_node,'status','INACTIVE')])
def test_reject_ineligible_atomically(connection,listing,table,column,value):
    from security_master_schema.option_booking import OptionBookingError
    data=direct_payload(connection,listing)
    if table in (m.instrument_definition_version,m.listing_definition_version):
        clone=clone_listing(connection,listing,{table.name:{column:value}})
        with pytest.raises(OptionBookingError): direct_book(connection,data.model_copy(update={'listing_id':UUID(clone)}))
        return
    row,_=load(connection,DEMO_IDS['tenant'],UUID(listing))
    if column=='exercise_style':
        # BERMUDAN requires an exercise schedule: use an already valid style
        # outside this alpha by keeping a schedule from the demo instrument.
        schedule=connection.scalar(select(m.option_terms.c.exercise_schedule_id).where(m.option_terms.c.exercise_style=='BERMUDAN'))
        connection.execute(update(m.option_terms).where(m.option_terms.c.instrument_node_id==row.instrument_node_id).values(exercise_schedule_id=schedule))
    key=table.c.listing_node_id if table is m.listing_definition_version else table.c.reference_node_id if table is m.financial_reference_node else table.c.instrument_node_id
    target=UUID(listing) if table is m.listing_definition_version else row.instrument_node_id
    connection.execute(update(table).where(key==target).values({column:value}))
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(OptionBookingError): direct_book(connection,data)
    assert connection.scalar(select(func.count()).select_from(m.trade))==before


def test_stale_terms_and_historical_snapshot(connection,listing):
    from security_master_schema.option_booking import OptionBookingError
    data=direct_payload(connection,listing);key=str(uuid4());first=direct_book(connection,data,key)
    connection.execute(update(m.option_terms).where(m.option_terms.c.instrument_node_id==first.data.trade.instrument_id).values(premium_multiplier=200))
    with pytest.raises(OptionBookingError,match='Terms changed'):direct_book(connection,data)
    replay=direct_book(connection,data,key)
    assert replay.data.trade.option_economics.terms.premium_multiplier=='100'
    assert replay.data.trade.option_economics.gross_premium=='2500'


def test_minor_quotes_and_zero_premium(connection,listing):
    listing=clone_listing(connection,listing,{'listing':{'quote_factor':100},'listing_definition_version':{'quote_factor':100}})
    result=direct_book(connection,direct_payload(connection,listing,executionPrice='250'))
    assert result.data.trade.option_economics.gross_premium=='2500'
    assert direct_book(connection,direct_payload(connection,listing,executionPrice='0')).data.trade.option_economics.gross_premium=='0'


def test_unknown_annotations_roll_back(connection,listing):
    from apps.reference_api.trade_properties import TradeFieldError
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TradeFieldError):direct_book(connection,direct_payload(connection,listing,properties=[{'definitionId':str(uuid4()),'value':'bad'}]))
    assert connection.scalar(select(func.count()).select_from(m.trade))==before


def test_other_tenant_cannot_see_private_option(listing):
    response=request('GET',f'/v1/trades/option-listings/{listing}',tenant='second_tenant')
    assert response.status_code in {403,404},response.text


def test_option_cannot_be_booked_as_plain_cash(connection,listing):
    from apps.reference_api.repository import book_listed_cash_trade
    from apps.reference_api.contracts import TradeBookingRequest
    data=payload(listing);data.pop('positionEffect');data.pop('expectedTermsFingerprint')
    with pytest.raises(ValueError):book_listed_cash_trade(connection,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],TradeBookingRequest.model_validate(data),str(uuid4()),'test')


def test_concurrent_retry_creates_one_option_trade(listing):
    from concurrent.futures import ThreadPoolExecutor
    data=payload(listing);key=str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:request('POST','/v1/trades/options',data,key),range(2)))
    assert [r.status_code for r in responses]==[201,201]
    assert len({r.json()['data']['trade']['tradeId'] for r in responses})==1
