"""Immutable attributed pricing-policy versions; legacy records remain legacy."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='20261007_67'
down_revision='20261007_66'
branch_labels=depends_on=None


def upgrade():
    for column in [
        sa.Column('strategy_id',UUID(as_uuid=True),sa.ForeignKey('trd.strategy.strategy_id'),comment='Optional tenant-owned strategy scope; null means tenant-shared policy.'),
        sa.Column('created_by_user_account_id',UUID(as_uuid=True),sa.ForeignKey('secm.user_account.user_account_id'),comment='Actor creating a managed immutable version; null denotes legacy configuration.'),
        sa.Column('created_at_utc',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('CURRENT_TIMESTAMP'),comment='Time this policy version was recorded; legacy creation time is not historical evidence.'),
        sa.Column('submission_key',sa.String(255),comment='Tenant-scoped idempotency key for managed policy creation.'),
        sa.Column('submission_fingerprint',sa.String(64),comment='Canonical creation-payload SHA256 used for idempotent policy replay.'),
    ]:
        op.add_column('valuation_policy',column,schema='ten')
    op.create_unique_constraint('uq_valuation_policy_submission','valuation_policy',['tenant_id','submission_key'],schema='ten')
    op.execute("""
      CREATE FUNCTION ten.protect_managed_pricing_policy() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.created_by_user_account_id IS NOT NULL AND OLD.status <> 'DRAFT' THEN
          RAISE EXCEPTION 'Managed policy versions are immutable';
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER protect_managed_pricing_policy BEFORE UPDATE OR DELETE ON ten.valuation_policy
      FOR EACH ROW EXECUTE FUNCTION ten.protect_managed_pricing_policy();
      CREATE FUNCTION ten.protect_managed_pricing_rule() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE parent uuid; locked boolean;
      BEGIN
        IF TG_OP <> 'INSERT' THEN
          SELECT created_by_user_account_id IS NOT NULL AND status <> 'DRAFT' INTO locked
          FROM ten.valuation_policy WHERE valuation_policy_id = OLD.valuation_policy_id FOR SHARE;
          IF locked THEN RAISE EXCEPTION 'Managed policy rules are immutable'; END IF;
        END IF;
        IF TG_OP <> 'DELETE' THEN
          SELECT created_by_user_account_id IS NOT NULL AND status <> 'DRAFT' INTO locked
          FROM ten.valuation_policy WHERE valuation_policy_id = NEW.valuation_policy_id FOR SHARE;
          IF locked THEN RAISE EXCEPTION 'Managed policy rules are immutable'; END IF;
          RETURN NEW;
        END IF;
        RETURN OLD;
      END $$;
      CREATE TRIGGER protect_managed_pricing_rule BEFORE INSERT OR UPDATE OR DELETE ON ten.valuation_policy_rule
      FOR EACH ROW EXECUTE FUNCTION ten.protect_managed_pricing_rule();
    """)


def downgrade():
    raise RuntimeError('Forward-only: preserve managed policy audit evidence.')
