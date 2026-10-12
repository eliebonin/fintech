"""Integration check for the explicitly reconciled local PostgreSQL bootstrap database."""

from alembic.config import Config
from alembic.script import ScriptDirectory
import os
from sqlalchemy import create_engine, text


DATABASE_URL = os.environ["DATABASE_URL"]


def test_docker_database_is_at_head_with_migration_only_controls() -> None:
    """The local MVP database must be versioned and retain DB-only safeguards."""

    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        constraints = set(
            connection.execute(
                text(
                    """
                    SELECT conname
                    FROM pg_constraint
                    WHERE conname IN (
                        'ex_cfg_external_data_object_mapping_effective_period',
                        'ex_tenant_operating_profile_assignment_effective_period',
                        'ex_tenant_module_entitlement_effective_period'
                    )
                    """
                )
            ).scalars()
        )
        trigger_exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_trigger
                    WHERE tgname = 'trg_validate_external_data_mapping_target'
                      AND tgrelid = 'cfg.external_data_object_mapping'::regclass
                      AND NOT tgisinternal
                )
                """
            )
        ).scalar_one()

    assert revision == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    assert constraints == {
        "ex_cfg_external_data_object_mapping_effective_period",
        "ex_tenant_operating_profile_assignment_effective_period",
        "ex_tenant_module_entitlement_effective_period",
    }
    assert trigger_exists is True
