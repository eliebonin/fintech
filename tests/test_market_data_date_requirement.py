"""Database-level validation for date-based market-data observations."""

import os
from datetime import datetime, timezone
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import DBAPIError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.mvp_demo_data import MVP_NAMESPACE


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")


def test_business_daily_series_rejects_an_observation_without_market_date() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    now = datetime.now(timezone.utc)

    with engine.begin() as connection:
        with pytest.raises(DBAPIError, match="market_date"):
            with connection.begin_nested():
                connection.execute(
                    insert(m.market_data_observation).values(
                        market_data_observation_id=uuid4(),
                        market_data_series_id=uuid5(MVP_NAMESPACE, "series:us_equity"),
                        dataset_id=DEMO_IDS["mvp_yahoo_dataset"],
                        acquisition_licence_id=DEMO_IDS["mvp_yahoo_licence"],
                        observed_at_utc=now,
                        received_at_utc=now,
                        value=123.45,
                        value_basis="RAW",
                        source_observation_key=f"test-undated-{uuid4()}",
                        quality_status="ACCEPTED",
                    )
                )
