"""UTC historical-booking boundaries; pure checks first, isolated writers next."""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from apps.reference_api import booking_controls, repository, fx_forward_booking, option_booking, product_booking
from apps.reference_api.contracts import TradeBookingRequest, OptionBookingRequest, FxForwardBookingRequest
from apps.reference_api.product_booking_contracts import ProductBookingRequest
from apps.reference_api.trade_properties import TradeFieldError
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_execution_date_uses_utc_not_local_date():
    assert booking_controls.validate_execution_date(datetime.fromisoformat('2026-10-06T00:30:00+02:00'), today=date(2026,10,5)) == date(2026,10,5)


def test_future_utc_date_is_refused_and_same_day_is_allowed():
    with pytest.raises(TradeFieldError) as error:
        booking_controls.validate_execution_date(datetime.fromisoformat('2026-10-05T23:30:00-02:00'), today=date(2026,10,5))
    assert error.value.field == 'tradeDatetime'
    assert booking_controls.validate_execution_date(datetime(2026,10,5,23,tzinfo=timezone.utc), today=date(2026,10,5)) == date(2026,10,5)


def test_cash_settlement_uses_utc_execution_day():
    request = TradeBookingRequest(listingId=uuid4(), strategyId=uuid4(), side='BUY', quantity='1', executionPrice='1',
        tradeDatetime='2026-10-06T00:30:00+02:00', settlementDate='2026-10-05')
    assert request.settlement_date == date(2026,10,5)


@pytest.mark.parametrize('kind', ['CASH','FX_FORWARD','OPTION','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP'])
def test_every_new_writer_refuses_future_date_before_missing_reference_lookup(kind):
    common=dict(listingId=uuid4(),strategyId=ids['strategy'],side='BUY',quantity='1',executionPrice='1',
        tradeDatetime='2099-01-01T10:00:00Z',settlementDate='2099-01-02')
    with get_engine().connect() as c:
        transaction=c.begin()
        try:
            before=c.scalar(select(func.count()).select_from(m.trade))
            with pytest.raises(TradeFieldError) as error:
                if kind=='CASH':
                    repository.book_listed_cash_trade(c,ids['tenant'],ids['demo_user_account'],TradeBookingRequest(**common),str(uuid4()),'dates')
                elif kind=='OPTION':
                    option_booking.book(c,ids['tenant'],ids['demo_user_account'],OptionBookingRequest(**common,positionEffect='OPEN',expectedTermsFingerprint='a'*64),str(uuid4()),'dates')
                elif kind=='FX_FORWARD':
                    request=FxForwardBookingRequest(instrumentId=uuid4(),strategyId=ids['strategy'],side='BUY',quantity='1',tradeDatetime=common['tradeDatetime'],counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint='a'*64)
                    fx_forward_booking.book_fx_forward_trade(c,ids['tenant'],ids['demo_user_account'],request,str(uuid4()),'dates')
                else:
                    request=ProductBookingRequest(**(common|dict(listingId=None,instrumentId=uuid4(),executionRoute='OTC',expectedTermsFingerprint='a'*64)))
                    product_booking.book(c,ids['tenant'],ids['demo_user_account'],request,str(uuid4()),kind,'dates')
            assert error.value.field=='tradeDatetime'
            assert c.scalar(select(func.count()).select_from(m.trade))==before
        finally:
            transaction.rollback()
