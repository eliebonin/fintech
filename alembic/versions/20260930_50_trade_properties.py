"""Tenant-owned, immutable trade property and tag annotations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260930_50"
down_revision = "20260930_49"
branch_labels = None
depends_on = None

def _audit_columns():
    return [sa.Column("created_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False), sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("retired_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id")), sa.Column("retired_at_utc", sa.DateTime(timezone=True))]

def upgrade():
    op.create_table("trade_property_definition",
        sa.Column("definition_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False), sa.Column("label", sa.String(250), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("value_type", sa.String(20), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("choices", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"), *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", "version_no", name="uq_trade_property_version"),
        sa.CheckConstraint("value_type IN ('TEXT','DECIMAL','DATE','BOOLEAN','CHOICE') AND version_no > 0", name="ck_trade_property_type"),
        sa.CheckConstraint("status IN ('ACTIVE','RETIRED') AND (status <> 'RETIRED' OR (retired_by_user_account_id IS NOT NULL AND retired_at_utc IS NOT NULL))", name="ck_trade_property_status"), schema="trd")
    op.create_index("uq_trade_property_active_code", "trade_property_definition", ["tenant_id", "code"], unique=True, schema="trd", postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table("trade_tag", sa.Column("tag_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False), sa.Column("label", sa.String(250), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"), *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_trade_tag_code"),
        sa.CheckConstraint("status IN ('ACTIVE','RETIRED') AND (status <> 'RETIRED' OR (retired_by_user_account_id IS NOT NULL AND retired_at_utc IS NOT NULL))", name="ck_trade_tag_status"), schema="trd")
    op.create_table("trade_property_value",
        sa.Column("trade_id", sa.UUID(), sa.ForeignKey("trd.trade.trade_id"), primary_key=True),
        sa.Column("definition_id", sa.UUID(), sa.ForeignKey("trd.trade_property_definition.definition_id"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.CheckConstraint("jsonb_typeof(value) IN ('string','boolean')", name="ck_trade_property_scalar"), schema="trd")
    op.create_table("trade_tag_assignment",
        sa.Column("trade_id", sa.UUID(), sa.ForeignKey("trd.trade.trade_id"), primary_key=True),
        sa.Column("tag_id", sa.UUID(), sa.ForeignKey("trd.trade_tag.tag_id"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False), schema="trd")
    op.execute("""
    CREATE FUNCTION trd.guard_trade_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE owner_tenant uuid; registry_tenant uuid;
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Trade annotations are immutable' USING ERRCODE='23514'; END IF;
      SELECT s.tenant_id INTO owner_tenant FROM trd.trade t JOIN trd.strategy s USING(strategy_id) WHERE t.trade_id=NEW.trade_id;
      IF TG_TABLE_NAME='trade_property_value' THEN
        SELECT tenant_id INTO registry_tenant FROM trd.trade_property_definition WHERE definition_id=NEW.definition_id AND status='ACTIVE' FOR SHARE;
      ELSE
        SELECT tenant_id INTO registry_tenant FROM trd.trade_tag WHERE tag_id=NEW.tag_id AND status='ACTIVE' FOR SHARE;
      END IF;
      IF owner_tenant IS NULL OR registry_tenant IS NULL OR NEW.tenant_id<>owner_tenant OR NEW.tenant_id<>registry_tenant THEN
        RAISE EXCEPTION 'Trade annotation tenant mismatch or inactive definition' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_trade_property_value BEFORE INSERT OR UPDATE OR DELETE ON trd.trade_property_value FOR EACH ROW EXECUTE FUNCTION trd.guard_trade_annotation();
    CREATE TRIGGER guard_trade_tag_assignment BEFORE INSERT OR UPDATE OR DELETE ON trd.trade_tag_assignment FOR EACH ROW EXECUTE FUNCTION trd.guard_trade_annotation();
    CREATE FUNCTION trd.guard_trade_catalogue_meaning() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Retire catalogue items rather than deleting history' USING ERRCODE='23514'; END IF;
      IF (to_jsonb(NEW)-'status'-'retired_at_utc'-'retired_by_user_account_id') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'retired_at_utc'-'retired_by_user_account_id')
        OR (OLD.status='RETIRED' AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD)) THEN
        RAISE EXCEPTION 'Catalogue meaning is immutable; create a replacement' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_trade_property_definition BEFORE UPDATE OR DELETE ON trd.trade_property_definition FOR EACH ROW EXECUTE FUNCTION trd.guard_trade_catalogue_meaning();
    CREATE TRIGGER guard_trade_tag BEFORE UPDATE OR DELETE ON trd.trade_tag FOR EACH ROW EXECUTE FUNCTION trd.guard_trade_catalogue_meaning();
    """)

def downgrade():
    op.drop_table("trade_tag_assignment", schema="trd")
    op.drop_table("trade_property_value", schema="trd")
    op.drop_table("trade_tag", schema="trd")
    op.drop_table("trade_property_definition", schema="trd")
    op.execute("DROP FUNCTION trd.guard_trade_annotation(); DROP FUNCTION trd.guard_trade_catalogue_meaning();")
