"""Database fixtures for composable tenant profiles and module entitlements."""

from datetime import date

from sqlalchemy import create_engine, select

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, create_schema, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_demo_tenant_has_multiple_profiles_and_explicit_capability_grants() -> None:
    engine = create_engine(DATABASE_URL)
    create_schema(engine)
    load_demo_data(engine)

    with engine.connect() as connection:
        profiles = connection.execute(
            select(m.operating_profile.c.profile_code)
            .join(
                m.tenant_operating_profile_assignment,
                m.tenant_operating_profile_assignment.c.operating_profile_id == m.operating_profile.c.operating_profile_id,
            )
            .where(m.tenant_operating_profile_assignment.c.tenant_id == DEMO_IDS["tenant"])
            .where(m.tenant_operating_profile_assignment.c.status == "ACTIVE")
            .where(m.tenant_operating_profile_assignment.c.valid_from <= date(2026, 8, 28))
        ).scalars().all()
        modules = connection.execute(
            select(m.platform_module.c.module_code)
            .join(
                m.tenant_module_entitlement,
                m.tenant_module_entitlement.c.platform_module_id == m.platform_module.c.platform_module_id,
            )
            .where(m.tenant_module_entitlement.c.tenant_id == DEMO_IDS["tenant"])
            .where(m.tenant_module_entitlement.c.entitlement_state == "GRANTED")
        ).scalars().all()

    assert set(profiles) == {"FUND_MANAGER", "TRADING_BOOK_MANAGER"}
    assert {"SECURITY_MASTER", "TRADING", "VALUATION", "FUND_MANAGEMENT"}.issubset(modules)
