"""Reconcile migration-only safeguards for metadata-bootstrapped local databases.

Revision ID: 20260911_43
Revises: 20260911_42
"""

from alembic import op


revision = "20260911_43"
down_revision = "20260911_42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add database-only integrity controls idempotently after bootstrap reconciliation."""

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ex_cfg_external_data_object_mapping_effective_period'
                  AND conrelid = 'cfg.external_data_object_mapping'::regclass
            ) THEN
                ALTER TABLE cfg.external_data_object_mapping
                ADD CONSTRAINT ex_cfg_external_data_object_mapping_effective_period
                EXCLUDE USING gist (
                    external_data_mapping_profile_id WITH =,
                    source_object_scope WITH =,
                    external_id_normalized WITH =,
                    daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
                ) WHERE (status = 'APPROVED');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cfg.validate_external_data_mapping_target() RETURNS trigger AS $$
        BEGIN
            IF NEW.target_object_type = 'FUND' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.fund WHERE fund_reference_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'operational mapping target % is not a fund', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'FUND_SHARE_CLASS' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.instrument WHERE instrument_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'operational mapping target % is not a fund share-class instrument', NEW.target_object_id;
                END IF;
            ELSE
                RAISE EXCEPTION 'unsupported operational mapping target type %', NEW.target_object_type;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_validate_external_data_mapping_target'
                  AND tgrelid = 'cfg.external_data_object_mapping'::regclass
                  AND NOT tgisinternal
            ) THEN
                CREATE TRIGGER trg_validate_external_data_mapping_target
                BEFORE INSERT OR UPDATE OF target_object_type, target_object_id
                ON cfg.external_data_object_mapping
                FOR EACH ROW EXECUTE FUNCTION cfg.validate_external_data_mapping_target();
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ex_tenant_operating_profile_assignment_effective_period'
                  AND conrelid = 'ten.tenant_operating_profile_assignment'::regclass
            ) THEN
                ALTER TABLE ten.tenant_operating_profile_assignment
                ADD CONSTRAINT ex_tenant_operating_profile_assignment_effective_period
                EXCLUDE USING gist (
                    tenant_id WITH =,
                    operating_profile_id WITH =,
                    daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
                ) WHERE (status = 'ACTIVE');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ex_tenant_module_entitlement_effective_period'
                  AND conrelid = 'ten.tenant_module_entitlement'::regclass
            ) THEN
                ALTER TABLE ten.tenant_module_entitlement
                ADD CONSTRAINT ex_tenant_module_entitlement_effective_period
                EXCLUDE USING gist (
                    tenant_id WITH =,
                    platform_module_id WITH =,
                    daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
                ) WHERE (entitlement_state IN ('GRANTED', 'SUSPENDED'));
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Remove reconciliation-only database controls in reverse dependency order."""

    op.execute("ALTER TABLE ten.tenant_module_entitlement DROP CONSTRAINT IF EXISTS ex_tenant_module_entitlement_effective_period")
    op.execute("ALTER TABLE ten.tenant_operating_profile_assignment DROP CONSTRAINT IF EXISTS ex_tenant_operating_profile_assignment_effective_period")
    op.execute("DROP TRIGGER IF EXISTS trg_validate_external_data_mapping_target ON cfg.external_data_object_mapping")
    op.execute("DROP FUNCTION IF EXISTS cfg.validate_external_data_mapping_target()")
    op.execute("ALTER TABLE cfg.external_data_object_mapping DROP CONSTRAINT IF EXISTS ex_cfg_external_data_object_mapping_effective_period")
