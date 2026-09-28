"""Indicative Soft-NAV orchestration tests."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.soft_nav_service import SoftNavRequest, calculate_soft_nav


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_soft_nav_freezes_entitled_input_and_calculates_listing_quote_factor() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            run_id = calculate_soft_nav(
                connection,
                SoftNavRequest(
                    tenant_id=DEMO_IDS["tenant"],
                    strategy_id=DEMO_IDS["strategy"],
                    position_snapshot_id=DEMO_IDS["position_snapshot"],
                    valuation_policy_id=DEMO_IDS["valuation_policy"],
                    valuation_date=datetime(2026, 8, 28, tzinfo=timezone.utc).date(),
                    valuation_cut_id=DEMO_IDS["valuation_cut"],
                    market_data_as_of_utc=datetime(2026, 8, 28, 16, 30, tzinfo=timezone.utc),
                    reporting_currency_id=DEMO_IDS["gbp_currency"],
                    calculation_version="test-v1",
                ),
            )
            result = connection.execute(
                select(m.nav_result.c.net_asset_value).where(
                    m.nav_result.c.nav_calculation_run_id == run_id
                )
            ).scalar_one()
            input_count = connection.scalar(
                select(m.nav_input_snapshot_item.c.nav_input_snapshot_item_id)
                .select_from(
                    m.nav_input_snapshot_item.join(
                        m.nav_input_snapshot,
                        m.nav_input_snapshot_item.c.nav_input_snapshot_id
                        == m.nav_input_snapshot.c.nav_input_snapshot_id,
                    )
                )
                .where(m.nav_input_snapshot.c.nav_calculation_run_id == run_id)
            )
            assert result == Decimal("10230.000000000000")
            assert input_count is not None
        finally:
            transaction.rollback()
