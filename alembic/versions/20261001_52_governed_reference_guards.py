"""Prevent scalar/reference substitution and destructive catalogue lifecycle."""
from alembic import op

revision = "20261001_52"
down_revision = "20261001_51"
branch_labels = depends_on = None

def upgrade():
    op.execute("""
    CREATE FUNCTION trd.guard_scalar_property_kind() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM trd.trade_property_definition WHERE definition_id=NEW.definition_id AND value_type='REFERENCE') THEN
        RAISE EXCEPTION 'Reference properties require a relational reference assignment' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_scalar_property_kind BEFORE INSERT ON trd.trade_property_value FOR EACH ROW EXECUTE FUNCTION trd.guard_scalar_property_kind();
    CREATE FUNCTION trd.guard_reference_catalogue() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Retire catalogues rather than deleting history' USING ERRCODE='23514'; END IF;
      IF (to_jsonb(NEW)-'status'-'retired_at_utc'-'retired_by_user_account_id') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'retired_at_utc'-'retired_by_user_account_id')
        OR (OLD.status='RETIRED' AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD))
        OR (OLD.status='ACTIVE' AND NEW.status='DRAFT') THEN
        RAISE EXCEPTION 'Catalogue meaning and published lifecycle cannot be rewritten' USING ERRCODE='23514';
      END IF;
      IF NEW.status='RETIRED' AND (NEW.retired_at_utc IS NULL OR NEW.retired_by_user_account_id IS NULL OR EXISTS(SELECT 1 FROM trd.trade_property_definition WHERE catalogue_id=NEW.catalogue_id AND status='ACTIVE')) THEN
        RAISE EXCEPTION 'Retirement requires audit and no active field bindings' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_reference_catalogue BEFORE UPDATE OR DELETE ON trd.reference_catalogue FOR EACH ROW EXECUTE FUNCTION trd.guard_reference_catalogue();
    """)

def downgrade():
    op.execute("DROP TRIGGER guard_reference_catalogue ON trd.reference_catalogue; DROP FUNCTION trd.guard_reference_catalogue(); DROP TRIGGER guard_scalar_property_kind ON trd.trade_property_value; DROP FUNCTION trd.guard_scalar_property_kind();")
