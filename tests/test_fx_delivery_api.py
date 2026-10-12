"""Use disposable database runner only; no operating settlement data."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select, func, update
from apps.reference_api.db import get_engine
from apps.reference_api.fx_delivery import DeliveryRequest, record_delivery, get_delivery
from apps.reference_api.trade_properties import TradeFieldError
from apps.reference_api.booking_errors import IdempotencyKeyConflict, RepositoryNotFound
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.tenant_workspace import TenantActionForbidden
from tests.test_fx_forward_booking_api import request


@pytest.fixture(scope='module')
def matured():
    proposal=request('POST','/v1/fx-forward-proposals',dict(canonicalName=f'Synthetic delivery {uuid4()}',effectiveFrom='2026-09-01',baseCurrencyId=str(ids['eur_currency']),quoteCurrencyId=str(ids['usd_currency']),quoteConvention='USD_PER_EUR',agreedForwardRate='1.1',settlementType='DELIVERABLE',maturityDate='2026-10-01',submissionMode='MANUAL'))
    assert proposal.status_code==201,proposal.text
    approved=request('POST',f"/v1/reference-data-proposals/{proposal.json()['data']['proposalId']}/decision",dict(decision='APPROVED',reason='Synthetic delivery fixture'))
    assert approved.status_code==200,approved.text
    instrument=approved.json()['data']['referenceNodeId']
    view=request('GET',f'/v1/trades/fx-forward-instruments/{instrument}?asOfDate=2026-09-30')
    assert view.status_code==200,view.text
    return dict(instrumentId=instrument,strategyId=str(ids['strategy']),side='BUY',quantity='100',tradeDatetime='2026-09-30T10:00:00Z',counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=view.json()['data']['termsFingerprint'])

@pytest.fixture
def c():
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try: yield connection
        finally: transaction.rollback()

def book(c,matured):
    from apps.reference_api.fx_forward_booking import book_fx_forward_trade
    from apps.reference_api.contracts import FxForwardBookingRequest
    return book_fx_forward_trade(c,ids['tenant'],ids['demo_user_account'],FxForwardBookingRequest(**matured),str(uuid4()),'test').data.trade.trade_id

def payload(sequence=1,**changes):
    return dict(expectedSequenceNo=sequence,action='CONFIRM',leg='RECEIVE',amount='40',effectiveAt='2026-10-01T12:00:00Z',evidence='Synthetic custodian reference')|changes

def post(c,trade,data=None,key=None):
    return record_delivery(c,ids['tenant'],ids['demo_user_account'],trade,DeliveryRequest(**(data or payload())),key or str(uuid4()),'test')

def test_partial_two_leg_delivery_and_reversal_retain_booking(c,matured):
    trade=book(c,matured)
    assert get_delivery(c,ids['tenant'],trade,'test').data.status=='DUE'
    assert post(c,trade).data.receive_outstanding=='60'
    assert post(c,trade,payload(2,amount='60')).data.status=='PARTIAL'
    assert post(c,trade,payload(3,leg='PAY',amount='110')).data.status=='DELIVERED'
    reversed=post(c,trade,dict(expectedSequenceNo=4,action='REVERSE',targetSequenceNo=2,effectiveAt='2026-10-02T12:00:00Z',evidence='Wrong synthetic confirmation'))
    assert reversed.data.receive_outstanding=='40' and reversed.data.pay_outstanding=='0'
    assert c.scalar(select(m.trade.c.lifecycle_status).where(m.trade.c.trade_id==trade))=='BOOKED'
    assert c.scalar(select(func.count()).select_from(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade))==5
    from apps.reference_api.trade_corrections import cancel_booking
    from apps.reference_api.contracts import CancelBookingRequest
    with pytest.raises(TradeFieldError): cancel_booking(c,ids['tenant'],ids['demo_user_account'],trade,CancelBookingRequest(expectedSequenceNo=5,reason='erroneous'),str(uuid4()),'test')

def test_replay_stale_overfill_and_changed_key_are_atomic(c,matured):
    trade=book(c,matured);key=str(uuid4())
    post(c,trade,key=key)
    assert post(c,trade,key=key).data.expected_sequence_no==2
    with pytest.raises(IdempotencyKeyConflict): post(c,trade,payload(amount='50'),key)
    with pytest.raises(TradeFieldError): post(c,trade)
    with pytest.raises(TradeFieldError): post(c,trade,payload(2,amount='61'))
    assert get_delivery(c,ids['tenant'],trade,'test').data.expected_sequence_no==2

def test_hidden_trade_and_revoked_replay(c,matured):
    trade=book(c,matured);key=str(uuid4());post(c,trade,key=key)
    with pytest.raises(RepositoryNotFound): get_delivery(c,ids['second_tenant'],trade,'test')
    c.execute(update(m.user_account).where(m.user_account.c.user_account_id==ids['demo_user_account']).values(status='INACTIVE'))
    with pytest.raises(TenantActionForbidden): post(c,trade,key=key)

@pytest.mark.parametrize('changes',[dict(amount='NaN'),dict(amount='0'),dict(amount=True),dict(effectiveAt='2026-10-01T12:00:00'),dict(evidence=' '),dict(currency='EUR'),dict(action='REVERSE'),dict(targetSequenceNo=1),dict(expectedSequenceNo=True)])
def test_strict_delivery_request(changes):
    with pytest.raises(ValueError): DeliveryRequest(**payload(**changes))

def test_http_delivery_contract_and_opaque_foreign_trade(matured):
    booked=request('POST','/v1/trades/fx-forwards',matured)
    assert booked.status_code==201,booked.text
    trade=booked.json()['data']['trade']['tradeId'];path=f'/v1/trades/{trade}/fx-delivery'
    assert request('GET',path).json()['data']['status']=='DUE'
    key=str(uuid4());saved=request('POST',path,payload(),key)
    assert saved.status_code==200,saved.text
    assert saved.json()['data']['receiveConfirmed']=='40'
    assert request('POST',path,payload(),key).status_code==200
    assert request('POST',path,payload()).status_code==409
    # This legacy shared user has no group grant in the second tenant: deny
    # authority before looking up the trade. Authorized foreign-ID 404 is also
    # checked by tenant-access HTTP acceptance with the seeded second admin.
    assert request('GET',path,tenant='second_tenant').status_code==403
    invalid=request('POST',path,payload(2,amount='61'))
    # The request shape is valid but it conflicts with the remaining booked obligation.
    assert invalid.status_code==409,invalid.text
    assert request('GET',path).json()['data']['expectedSequenceNo']==2
