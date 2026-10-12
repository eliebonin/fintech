"""Integration checks for the versioned PostgreSQL schema boundary."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    os.environ["DATABASE_URL"],
).rsplit("/", 1)[0] + "/postgres"
TEST_DATABASE_NAME = "fortem_secm_migration_test"
TEST_DATABASE_URL = ADMIN_DATABASE_URL.rsplit("/", 1)[0] + f"/{TEST_DATABASE_NAME}"


def _run_alembic(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ | {"DATABASE_URL": TEST_DATABASE_URL}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _recreate_test_database() -> None:
    engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE_NAME}"))
        connection.execute(text(f"CREATE DATABASE {TEST_DATABASE_NAME}"))


def test_migrations_create_schemas_and_preserve_forward_only_history() -> None:
    _recreate_test_database()

    upgrade = _run_alembic("upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stderr

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as connection:
        revision_before = connection.scalar(text('SELECT version_num FROM public.alembic_version'))
        schema_names = set(connection.scalars(text("SELECT schema_name FROM information_schema.schemata")))
        assert {"secm", "ten", "ing", "md", "trd", "nav", "cal", "fee"}.issubset(schema_names)
        table_names = set(
            connection.scalars(
                text(
                    """
                    SELECT table_schema || '.' || table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('secm', 'md', 'trd')
                    """
                )
            )
        )
        assert {
            "secm.return_profile",
            "secm.index_family",
            "secm.index_terms",
            "secm.index_methodology_version",
            "secm.etp_terms",
            "secm.option_strike_reset_rule",
            "secm.option_strike_fixing",
            "secm.structured_product_condition_group",
            "secm.barrier_rule",
            "secm.condition_group_action",
            "secm.structured_product_coupon_programme",
            "secm.structured_product_coupon_period",
            "secm.structured_product_component_terms",
            "secm.structured_product_range_accrual_terms",
            "secm.structured_product_supertracker_terms",
            "secm.option_strike_adjustment",
        }.issubset(table_names)

        option_columns = set(
            connection.scalars(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'secm' AND table_name = 'option_terms'
                    """
                )
            )
        )
        assert {
            "option_terms_id",
            "version_no",
            "effective_from",
            "effective_to",
            "is_current",
            "strike_mode",
            "strike_reset_schedule_id",
            "strike_reference_initial_fixing_id",
        }.issubset(option_columns)

        adjustment_columns = set(
            connection.scalars(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'secm' AND table_name = 'option_strike_adjustment'
                    """
                )
            )
        )
        assert {"option_strike_adjustment_id", "revision_no", "supersedes_adjustment_id"}.issubset(adjustment_columns)

        index_names = set(
            connection.scalars(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'secm'
                    """
                )
            )
        )
        assert "uq_option_terms_current" in index_names
        assert "uq_option_strike_fixing_current" in index_names

        structured_product_columns = set(
            connection.scalars(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'secm' AND table_name = 'structured_product_terms'
                    """
                )
            )
        )
        assert {
            "structured_product_terms_id",
            "instrument_node_id",
            "version_no",
            "default_underlying_scope",
            "first_autocall_observation_date",
            "source_payload_id",
        }.issubset(structured_product_columns)

        action_columns = set(
            connection.scalars(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'secm' AND table_name = 'condition_group_action'
                    """
                )
            )
        )
        assert "payment_date" in action_columns
        assert "payout_multiplicity" in action_columns

    downgrade = _run_alembic("downgrade", "base")
    assert downgrade.returncode != 0
    assert 'Forward-only' in downgrade.stderr

    with engine.connect() as connection:
        remaining_schema_names = set(connection.scalars(text("SELECT schema_name FROM information_schema.schemata")))
        assert {"secm", "ten", "ing", "md", "trd", "nav", "cal", "fee"}.issubset(remaining_schema_names)
        assert connection.scalar(text('SELECT version_num FROM public.alembic_version')) == revision_before
