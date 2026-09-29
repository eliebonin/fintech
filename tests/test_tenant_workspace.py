"""Database controls for the tenant workspace alpha."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.exc import IntegrityError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, create_schema, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"
SECOND_TENANT_ID = UUID("00000000-0000-7000-8000-000000000301")


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(DATABASE_URL)
    create_schema(engine)
    load_demo_data(engine)
    return engine


def _insert_second_tenant(connection) -> None:
    connection.execute(
        insert(m.tenant).values(
            tenant_id=SECOND_TENANT_ID,
            owning_organisation_id=DEMO_IDS["fortem_organisation"],
            tenant_code="SECOND_ALPHA",
            display_name="Second Alpha Tenant",
            status="ACTIVE",
        )
    )


def _insert_strategy(connection, tenant_id: UUID, code: str) -> None:
    connection.execute(
        insert(m.strategy).values(
            tenant_id=tenant_id,
            strategy_code=code,
            display_name=f"{code} strategy",
            strategy_type="FUND",
            status="ACTIVE",
        )
    )


def test_strategy_code_is_unique_within_tenant_but_reusable_by_another_tenant(engine) -> None:
    with engine.begin() as connection:
        _insert_second_tenant(connection)
        _insert_strategy(connection, DEMO_IDS["tenant"], "ALPHA_CORE")
        _insert_strategy(connection, SECOND_TENANT_ID, "ALPHA_CORE")
        with pytest.raises(IntegrityError, match="uq_strategy_tenant_code"):
            _insert_strategy(connection, DEMO_IDS["tenant"], "ALPHA_CORE")


def test_platform_authority_is_stored_separately_from_tenant_membership(engine) -> None:
    with engine.begin() as connection:
        account_id = uuid4()
        connection.execute(insert(m.user_account).values(user_account_id=account_id, account_type="HUMAN", status="ACTIVE"))
        connection.execute(
            insert(m.platform_user_account).values(
                user_account_id=account_id,
                platform_role="PLATFORM_ADMIN",
                status="ACTIVE",
                valid_from=date(2026, 1, 1),
            )
        )
        role = connection.execute(
            select(m.platform_user_account.c.platform_role).where(
                m.platform_user_account.c.user_account_id == account_id
            )
        ).scalar_one()

    assert role == "PLATFORM_ADMIN"


def test_demo_data_provides_switchable_tenant_and_separate_platform_admin(engine) -> None:
    with engine.connect() as connection:
        memberships = connection.execute(
            select(m.tenant_user_account.c.tenant_id, m.tenant_user_account.c.membership_role)
            .where(m.tenant_user_account.c.user_account_id == DEMO_IDS["demo_user_account"])
            .where(m.tenant_user_account.c.status == "ACTIVE")
        ).all()
        platform_role = connection.execute(
            select(m.platform_user_account.c.platform_role).where(
                m.platform_user_account.c.user_account_id == DEMO_IDS["platform_admin_user_account"]
            )
        ).scalar_one()

    assert set(memberships) >= {
        (DEMO_IDS["tenant"], "TENANT_ADMIN"),
        (DEMO_IDS["second_tenant"], "OPERATIONS"),
    }
    assert platform_role == "PLATFORM_ADMIN"
