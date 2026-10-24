"""Permit immutable instrument definitions to be superseded, never edited away."""
from alembic import op

revision='20261023_98'
down_revision='20261023_97'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE OR REPLACE FUNCTION secm.prevent_definition_version_mutation() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'instrument_definition_version' THEN
            IF OLD.is_current AND NOT NEW.is_current AND OLD.status = 'APPROVED' AND NEW.status = 'SUPERSEDED'
               AND (to_jsonb(OLD) - 'is_current' - 'status') = (to_jsonb(NEW) - 'is_current' - 'status') THEN
                RETURN NEW;
            END IF;
        END IF;
        RAISE EXCEPTION 'canonical definition versions are immutable; append a new version instead';
    END;
    $$ LANGUAGE plpgsql;

    CREATE FUNCTION secm.require_instrument_definition_replacement() RETURNS trigger AS $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM secm.instrument_definition_version v
            WHERE v.instrument_node_id = OLD.instrument_node_id
              AND v.sequence_no > OLD.sequence_no AND v.is_current AND v.status = 'APPROVED'
              AND v.approved_by_user_account_id IS NOT NULL AND v.approved_at_utc IS NOT NULL
              AND v.source_payload_id IS NOT NULL
        ) THEN
            RAISE EXCEPTION 'retiring an instrument definition requires a newer sourced approved current replacement';
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE CONSTRAINT TRIGGER instrument_definition_replacement_required
    AFTER UPDATE ON secm.instrument_definition_version
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    WHEN (OLD.is_current AND NOT NEW.is_current)
    EXECUTE FUNCTION secm.require_instrument_definition_replacement();
    """)


def downgrade():
    op.execute("""
    DROP TRIGGER instrument_definition_replacement_required ON secm.instrument_definition_version;
    DROP FUNCTION secm.require_instrument_definition_replacement();
    CREATE OR REPLACE FUNCTION secm.prevent_definition_version_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'canonical definition versions are immutable; append a new version instead';
    END;
    $$ LANGUAGE plpgsql;
    """)
