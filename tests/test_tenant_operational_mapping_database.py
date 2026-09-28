"""Database fixture coverage for tenant fund operational mappings."""

from datetime import date

from sqlalchemy import create_engine, select

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, create_schema, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_demo_administrator_profiles_resolve_fund_and_share_class_records() -> None:
    engine = create_engine(DATABASE_URL)
    create_schema(engine)
    load_demo_data(engine)

    with engine.connect() as connection:
        profile = connection.execute(
            select(m.external_data_mapping_profile).where(
                m.external_data_mapping_profile.c.external_data_mapping_profile_id
                == DEMO_IDS["abc_daily_valuation_profile"]
            )
        ).mappings().one()
        mappings = connection.execute(
            select(m.external_data_object_mapping)
            .where(m.external_data_object_mapping.c.external_data_mapping_profile_id == profile["external_data_mapping_profile_id"])
            .where(m.external_data_object_mapping.c.valid_from <= date(2026, 8, 28))
        ).mappings().all()

    assert profile["profile_code"] == "ABC_DAILY_VALUATION"
    assert profile["operational_context"] == "VALUATION"
    assert {(row["source_object_scope"], row["target_object_id"]) for row in mappings} == {
        ("FUND_SHARE_CLASS", DEMO_IDS["demo_share_class_instrument_node"]),
    }
