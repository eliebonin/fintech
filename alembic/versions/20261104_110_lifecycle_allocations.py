"""Retained tenant lifecycle allocation field policies."""
from alembic import op
revision='20261104_110'
down_revision='20261102_109'
branch_labels=depends_on=None

def upgrade():
    from security_master_schema import models as m
    m.lifecycle_allocation_policy.create(op.get_bind(),checkfirst=False)
    op.execute("""CREATE FUNCTION trd.protect_lifecycle_allocation_policy() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Allocation policies are immutable'; END IF;
      IF NEW.revision<>(SELECT COALESCE(max(revision),0)+1 FROM trd.lifecycle_allocation_policy WHERE tenant_id=NEW.tenant_id)
        THEN RAISE EXCEPTION 'Allocation policy revision conflict'; END IF;
      IF EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.fields) f WHERE
          f->>'behavior' IS NULL OR f->>'behavior' NOT IN ('ALLOCATION','INHERIT','INPUT') OR NOT EXISTS(
          SELECT 1 FROM trd.trade_property_definition d WHERE d.definition_id=(f->>'definitionId')::uuid AND d.tenant_id=NEW.tenant_id AND (d.status='ACTIVE' OR EXISTS(SELECT 1 FROM trd.lifecycle_allocation_policy prior, jsonb_array_elements(prior.fields) oldfield WHERE prior.tenant_id=NEW.tenant_id AND prior.revision=NEW.revision-1 AND oldfield->>'definitionId'=f->>'definitionId' AND oldfield->>'behavior'=f->>'behavior'))))
        OR (SELECT count(*) FROM jsonb_array_elements(NEW.fields))<>(SELECT count(DISTINCT f->>'definitionId') FROM jsonb_array_elements(NEW.fields) f)
        THEN RAISE EXCEPTION 'Invalid allocation field scope'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER lifecycle_allocation_policy_guard BEFORE INSERT OR UPDATE OR DELETE ON trd.lifecycle_allocation_policy
      FOR EACH ROW EXECUTE FUNCTION trd.protect_lifecycle_allocation_policy();""")

def downgrade():
    raise RuntimeError('Forward-only: preserve lifecycle allocation decisions')
