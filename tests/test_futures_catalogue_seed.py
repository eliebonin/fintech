"""The reviewed local seed is atomic, rerunnable and uses real approval rows."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from scripts.seed_futures_catalogue import seed, EXPIRIES
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def counts(connection):
    return tuple(connection.scalar(select(func.count()).select_from(table)) for table in
        (m.future_family, m.future_terms, m.listing, m.reference_data_proposal, m.reference_data_approval, m.trade))


def test_expiry_cutoffs_preserve_chicago_dst():
    for _, final, cutoff, _, _ in EXPIRIES:
        local = datetime.fromisoformat(cutoff.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Chicago'))
        assert local.date().isoformat() == final
        assert (local.hour, local.minute) == (8, 30)
        assert local.weekday() == 4 and 15 <= local.day <= 21


def test_seed_approval_reuse_and_no_trades():
    with get_engine().connect() as connection:
        tx = connection.begin()
        before = counts(connection)
        first = seed(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'])
        after = counts(connection)
        assert tuple(b-a for a,b in zip(before, after)) == (3, 6, 6, 17, 17, 0)
        assert first == seed(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'])
        assert counts(connection) == after
        assert [f['code'] for f in first['families']] == ['CME_ES', 'CME_MES', 'CME_MNQ']
        from apps.reference_api.product_booking import load_context
        from uuid import UUID
        contract = first['families'][0]['contracts'][0]
        facts = load_context(connection, DEMO_IDS['tenant'], UUID(contract['instrumentId']), UUID(contract['listingId']))
        assert facts.underlying_name == 'S&P 500 Price Return'
        assert facts.listing_unit_multiplier == 1 and facts.convention.monetary_multiplier == 50
        # Existing identities must not silently be rewritten to match the seed.
        listing_id = first['families'][0]['contracts'][0]['listingId']
        connection.execute(m.listing.update().where(m.listing.c.listing_node_id == listing_id).values(unit_multiplier=99))
        with pytest.raises(ValueError, match='refusing overwrite'):
            seed(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'])
        tx.rollback()


def test_other_tenant_cannot_reuse_seed_actor():
    with get_engine().begin() as connection:
        with pytest.raises(Exception):
            seed(connection, DEMO_IDS['second_tenant'], DEMO_IDS['demo_user_account'])
