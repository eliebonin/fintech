"""Point-in-time corporate-action derivation tests."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine, insert, select

from security_master_schema import models as m
from security_master_schema.corporate_action_service import derive_adjusted_observation
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"
ACTION_ID = UUID("00000000-0000-7000-8000-000000000190")
FACTOR_ID = UUID("00000000-0000-7000-8000-000000000191")


def test_split_adjustment_respects_information_cut_and_preserves_raw_close() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                insert(m.corporate_action).values(
                    corporate_action_id=ACTION_ID,
                    affected_instrument_node_id=DEMO_IDS["hsbc_instrument_node"],
                    event_type="STOCK_SPLIT",
                    status="CONFIRMED",
                    sequence_no=1,
                    recorded_at_utc=datetime(2026, 8, 28, 12, tzinfo=timezone.utc),
                )
            )
            connection.execute(
                insert(m.market_data_adjustment_factor).values(
                    market_data_adjustment_factor_id=FACTOR_ID,
                    corporate_action_id=ACTION_ID,
                    raw_market_data_series_id=DEMO_IDS["market_data_series"],
                    derived_market_data_series_id=DEMO_IDS["market_data_series"],
                    adjustment_basis="SPLIT_ADJUSTED",
                    effective_date=date(2026, 8, 29),
                    factor=Decimal("0.5"),
                    calculation_method="test-split-v1",
                )
            )
            before_known = derive_adjusted_observation(
                connection,
                DEMO_IDS["market_data_observation"],
                "SPLIT_ADJUSTED",
                datetime(2026, 8, 28, 11, tzinfo=timezone.utc),
            )
            after_known = derive_adjusted_observation(
                connection,
                DEMO_IDS["market_data_observation"],
                "SPLIT_ADJUSTED",
                datetime(2026, 8, 28, 13, tzinfo=timezone.utc),
            )
            raw_value = connection.scalar(
                select(m.market_data_observation.c.value).where(
                    m.market_data_observation.c.market_data_observation_id
                    == DEMO_IDS["market_data_observation"]
                )
            )
            assert before_known.derived_value == Decimal("1023.000000000000")
            assert after_known.derived_value == Decimal("511.5000000000000")
            assert after_known.adjustment_factor_ids == (FACTOR_ID,)
            assert raw_value == Decimal("1023.000000000000")
        finally:
            transaction.rollback()
