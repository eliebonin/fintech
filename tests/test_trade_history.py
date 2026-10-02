"""Trade history reads must retain historical records and count all matches."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, update

from apps.reference_api.db import get_engine
from apps.reference_api.contracts import TradeBookingRequest
from apps.reference_api.repository import book_listed_cash_trade, get_booked_trade_detail, list_booked_trades
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


@pytest.fixture
def connection():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def history(connection, *, limit=1, offset=0, portfolio_code=None, from_date=None, to_date=None, **kwargs):
    return list_booked_trades(connection, DEMO_IDS["tenant"], portfolio_code, from_date, to_date,
                              limit, offset, "v1", "history-test", **kwargs)


def test_total_counts_matches_not_just_current_page(connection):
    result = history(connection)
    expected = connection.scalar(select(func.count()).select_from(m.trade.join(m.strategy)).where(
        m.strategy.c.tenant_id == DEMO_IDS["tenant"]
    ))
    assert len(result.data) == 1
    assert expected > 1
    assert result.meta.total == expected


def test_archiving_strategy_does_not_hide_trade_or_detail(connection):
    first = history(connection).data[0]
    connection.execute(update(m.strategy).where(m.strategy.c.strategy_id == first.strategy_id).values(status="ARCHIVED"))
    detail = get_booked_trade_detail(connection, DEMO_IDS["tenant"], first.trade_id, "v1", "history-test")
    assert detail is not None
    assert detail.data.trade.trade_id == first.trade_id


def test_other_tenant_cannot_read_trade_detail(connection):
    first = history(connection).data[0]
    assert get_booked_trade_detail(connection, uuid4(), first.trade_id, "v1", "history-test") is None


def test_search_matches_trade_id_and_treats_wildcards_literally(connection):
    first = history(connection).data[0]
    result = history(connection, query=str(first.trade_id))
    assert [trade.trade_id for trade in result.data] == [first.trade_id]
    assert result.meta.total == 1
    assert history(connection, query="%_no_literal_match").meta.total == 0


def test_cancelled_trade_remains_visible_and_status_filter_is_explicit(connection):
    first = history(connection).data[0]
    connection.execute(update(m.trade).where(m.trade.c.trade_id == first.trade_id).values(lifecycle_status="CANCELLED"))
    result = history(connection, query=str(first.trade_id), lifecycle_status="CANCELLED")
    assert result.data[0].trade_id == first.trade_id
    assert history(connection, query=str(first.trade_id), lifecycle_status="BOOKED").meta.total == 0
    assert get_booked_trade_detail(connection, DEMO_IDS["tenant"], first.trade_id, "v1", "history-test") is not None


def test_side_filter_uses_signed_quantity(connection):
    first = history(connection).data[0]
    connection.execute(update(m.trade).where(m.trade.c.trade_id == first.trade_id).values(quantity=-7))
    assert history(connection, query=str(first.trade_id), side="SELL").meta.total == 1
    assert history(connection, query=str(first.trade_id), side="BUY").meta.total == 0


def test_pagination_has_stable_order_no_overlap_and_total_on_empty_page(connection):
    first = history(connection, limit=2)
    second = history(connection, limit=2, offset=2)
    assert first.meta.total == second.meta.total
    assert not {trade.trade_id for trade in first.data} & {trade.trade_id for trade in second.data}
    combined = first.data + second.data
    ordering = [(trade.trade_datetime_utc, str(trade.trade_id)) for trade in combined]
    assert ordering == sorted(ordering, reverse=True)
    empty = history(connection, offset=first.meta.total + 1)
    assert empty.data == []
    assert empty.meta.total == first.meta.total


def test_booked_listing_can_be_found_by_symbol_strategy_date_and_side(connection):
    request = TradeBookingRequest(
        listingId=DEMO_IDS["hsbc_xlon_listing_node"], strategyId=DEMO_IDS["strategy"],
        side="SELL", quantity=Decimal("17"), executionPrice=Decimal("10.23"),
        tradeDatetime=datetime(2030, 1, 2, 23, 59, 59, tzinfo=timezone.utc),
        settlementDate=date(2030, 1, 4),
    )
    booked = book_listed_cash_trade(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], request, f"history-{uuid4()}", "history-integration")
    trade = booked.data.trade
    result = history(connection, query=trade.listing_symbol.lower(), portfolio_code=trade.strategy_code,
                     side="SELL", from_date=date(2030, 1, 2), to_date=date(2030, 1, 2))
    assert [item.trade_id for item in result.data] == [trade.trade_id]
    assert result.meta.total == 1
    assert history(connection, query=str(trade.trade_id), from_date=date(2030, 1, 3)).meta.total == 0
    assert get_booked_trade_detail(connection, DEMO_IDS["tenant"], trade.trade_id, "v1", "history-integration").data.lifecycle_events[0].event_type == "BOOKED"


def test_primary_venue_identifiers_do_not_duplicate_trades_or_mislabel_mic(connection):
    # OTC forwards correctly have no venue; test this invariant on a listed execution.
    first = next(trade for trade in history(connection,limit=100).data if trade.execution_venue_id is not None)
    assert first.execution_venue_id is not None
    for scheme in ["EXCHANGE_CODE", "ISO_10383_MIC"]:
        connection.execute(insert(m.market_venue_identifier).values(
            market_venue_identifier_id=UUID("ffffffff-ffff-4fff-bfff-ffffffffffff") if scheme == "ISO_10383_MIC" else uuid4(), market_venue_id=first.execution_venue_id,
            identifier_scheme=scheme, identifier_value=f"history-extra-{uuid4()}", is_primary=True,
        ))
    result = history(connection, query=str(first.trade_id), limit=25)
    assert len(result.data) == 1
    assert result.meta.total == 1
    assert result.data[0].venue_mic == first.venue_mic
