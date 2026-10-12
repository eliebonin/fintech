"""Run only through scripts/run_isolated_python_tests.py, never on app data."""
from datetime import date, timedelta
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from apps.reference_api.cash_booking_integrity import load_cash_booking_listing, CashBookingRefusal
from apps.reference_api.repository import book_listed_cash_trade
from apps.reference_api.contracts import TradeBookingRequest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.index_universe_seed import seed
from apps.market_data_ingestor.index_trading_history import apply_history, booking_start

MANIFEST = Path(__file__).resolve().parents[1]/'security_master_schema/data/index_trading_starts_2026_10_08.json'


def test_all_seed_history_idempotent_current_approvals_and_financial_data_preserved():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            seed(c, ids['demo_user_account'])
            financial = (m.trade, m.trade_lifecycle_event, m.market_data_observation, m.cash_balance)
            before = [c.scalar(select(func.count()).select_from(t)) for t in financial]
            originals = {t.name: [dict(v) for v in c.execute(select(t).where(t.c.is_current)).mappings()]
                         for t in (m.instrument_definition_version, m.listing_definition_version)}
            first = apply_history(c, ids['demo_user_account'], MANIFEST)
            assert first['appendedDefinitions'] == 1086
            assert apply_history(c, ids['demo_user_account'], MANIFEST)['appendedDefinitions'] == 0
            assert seed(c, ids['demo_user_account'])['createdListings'] == 0
            assert [c.scalar(select(func.count()).select_from(t)) for t in financial] == before
            for t in (m.instrument_definition_version, m.listing_definition_version):
                assert [dict(v) for v in c.execute(select(t).where(t.c.is_current)).mappings()] == originals[t.name]
            for row in json.loads(MANIFEST.read_text())['securities']:
                listing = c.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                    m.financial_reference_node.c.internal_code == 'PUBLIC_LIST_'+row['isin']+'_'+row['mic']))
                start = booking_start(row)
                snapshot = load_cash_booking_listing(c, ids['tenant'], listing, start, lock=False)['booking_snapshot']
                historical_id = c.scalar(select(m.listing_definition_version.c.listing_definition_version_id).where(
                    m.listing_definition_version.c.listing_node_id == listing, m.listing_definition_version.c.is_current.is_(False)))
                assert snapshot['listingDefinitionId'] == str(historical_id)
                with pytest.raises(CashBookingRefusal):
                    load_cash_booking_listing(c, ids['tenant'], listing, start-timedelta(days=1), lock=False)
                load_cash_booking_listing(c, ids['tenant'], listing, date(2026,10,8), lock=False)
            # A real synthetic booking freezes historical definition identities.
            listing = c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.trading_symbol == 'AAPL'))
            request = TradeBookingRequest(listingId=listing, strategyId=ids['strategy'], side='BUY',
                quantity='1', executionPrice='100', tradeDatetime='2026-05-08T14:00:00Z', settlementDate='2026-05-12')
            booked = book_listed_cash_trade(c, ids['tenant'], ids['demo_user_account'], request, str(uuid4()), 'historical-test')
            event = c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id == booked.data.trade.trade_id))
            assert json.loads(event)['listingDefinitionId'] == load_cash_booking_listing(c, ids['tenant'], listing, date(2026,5,8))['booking_snapshot']['listingDefinitionId']
        finally:
            tx.rollback()


@pytest.mark.parametrize('conflict', ['changed_economics', 'private_scope'])
def test_seed_rejects_changed_economics_and_private_scope(conflict):
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            seed(c, ids['demo_user_account'])
            listing = c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.trading_symbol == 'AAPL'))
            if conflict == 'changed_economics':
                c.execute(m.listing.update().where(m.listing.c.listing_node_id == listing).values(unit_multiplier=99))
            else:
                c.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == listing).values(
                    scope_type='TENANT_PRIVATE', owner_tenant_id=ids['tenant']))
            with pytest.raises(ValueError, match='refusing overwrite'):
                apply_history(c, ids['demo_user_account'], MANIFEST)
        finally:
            tx.rollback()


def test_earlier_projection_alone_does_not_enable_unapproved_history():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            seed(c, ids['demo_user_account'])
            listing = c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.trading_symbol == 'AAPL'))
            c.execute(m.listing.update().where(m.listing.c.listing_node_id == listing).values(effective_from=date(1980,12,12)))
            with pytest.raises(CashBookingRefusal, match='outside'):
                load_cash_booking_listing(c, ids['tenant'], listing, date(2026,5,8))
        finally:
            tx.rollback()
