"""Focused tests for governed market-data observation meaning."""

import os
from sqlalchemy import create_engine, select

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, create_schema, load_demo_data
from security_master_schema.seed_data import seed_defaults


DATABASE_URL = os.environ["DATABASE_URL"]


def test_seeded_measure_definitions_distinguish_return_and_change_conventions() -> None:
    engine = create_engine(DATABASE_URL)
    create_schema(engine)
    with engine.begin() as connection:
        seed_defaults(connection)
        rows = {
            measure_code: (change_method, change_unit)
            for measure_code, change_method, change_unit in connection.execute(
                select(
                    m.series_measure_definition.c.measure_code,
                    m.series_measure_definition.c.default_change_method,
                    m.series_measure_definition.c.change_display_unit,
                ).where(
                    m.series_measure_definition.c.measure_code.in_(
                        ("PRICE", "FX_RATE", "IMPLIED_VOLATILITY", "YIELD", "RATE")
                    )
                )
            ).tuples()
        }

    assert rows["PRICE"] == ("RELATIVE_RETURN", "PERCENT")
    assert rows["FX_RATE"] == ("RELATIVE_RETURN", "PERCENT")
    assert rows["IMPLIED_VOLATILITY"] == ("ABSOLUTE_CHANGE", "VOLATILITY_POINTS")
    assert rows["YIELD"] == ("BASIS_POINT_CHANGE", "BASIS_POINTS")
    assert rows["RATE"] == ("BASIS_POINT_CHANGE", "BASIS_POINTS")


def test_demo_price_nav_and_fx_series_link_to_their_governed_measurements() -> None:
    engine = create_engine(DATABASE_URL)
    create_schema(engine)
    load_demo_data(engine)

    with engine.connect() as connection:
        rows = dict(
            connection.execute(
                select(
                    m.market_data_series.c.market_data_series_id,
                    m.series_measure_definition.c.measure_code,
                )
                .join(
                    m.series_measure_definition,
                    m.market_data_series.c.measure_definition_id
                    == m.series_measure_definition.c.series_measure_definition_id,
                )
                .where(
                    m.market_data_series.c.market_data_series_id.in_(
                        (
                            DEMO_IDS["market_data_series"],
                            DEMO_IDS["demo_fund_nav_series"],
                            DEMO_IDS["uk_gbpusd_series"],
                        )
                    )
                )
            ).tuples().all()
        )

    assert rows[DEMO_IDS["market_data_series"]] == "PRICE"
    assert rows[DEMO_IDS["demo_fund_nav_series"]] == "NAV"
    assert rows[DEMO_IDS["uk_gbpusd_series"]] == "FX_RATE"
