"""Tenant-scope checks for tenant-facing operating data."""

from uuid import UUID

import pytest
import os
from sqlalchemy import create_engine

from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.tenancy import TenantScopeError, assert_tenant_owns_strategy


DATABASE_URL = os.environ["DATABASE_URL"]


def test_tenant_can_use_its_owned_strategy() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        assert_tenant_owns_strategy(connection, DEMO_IDS["tenant"], DEMO_IDS["strategy"])


def test_tenant_cannot_use_strategy_outside_its_scope() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        with pytest.raises(TenantScopeError):
            assert_tenant_owns_strategy(
                connection,
                UUID("00000000-0000-7000-8000-000000000199"),
                DEMO_IDS["strategy"],
            )
