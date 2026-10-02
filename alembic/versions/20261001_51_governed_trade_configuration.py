"""Governed tenant reference catalogues and standard trade eligibility."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261001_51"
down_revision = "20260930_50"
branch_labels = depends_on = None

def audit():
    return [sa.Column("created_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False),
            sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("retired_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id")),
            sa.Column("retired_at_utc", sa.DateTime(timezone=True))]

def upgrade():
    op.create_table("reference_catalogue",
        sa.Column("catalogue_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False), sa.Column("label", sa.String(250), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"), *audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_reference_catalogue_code"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','RETIRED')", name="ck_reference_catalogue_status"), schema="trd")
    op.create_table("reference_catalogue_record",
        sa.Column("record_version_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("catalogue_id", sa.UUID(), sa.ForeignKey("trd.reference_catalogue.catalogue_id"), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False), sa.Column("code", sa.String(100), nullable=False),
        sa.Column("label", sa.String(250), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"), *audit(),
        sa.UniqueConstraint("catalogue_id", "code", "version_no", name="uq_reference_record_version"),
        sa.CheckConstraint("version_no > 0 AND status IN ('ACTIVE','RETIRED')", name="ck_reference_record_status"), schema="trd")
    op.create_index("uq_reference_record_active_code", "reference_catalogue_record", ["catalogue_id", "code"], schema="trd", unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.add_column("trade_property_definition", sa.Column("catalogue_id", sa.UUID(), sa.ForeignKey("trd.reference_catalogue.catalogue_id")), schema="trd")
    op.drop_constraint("ck_trade_property_type", "trade_property_definition", schema="trd")
    op.create_check_constraint("ck_trade_property_type", "trade_property_definition", "value_type IN ('TEXT','INTEGER','DECIMAL','DATE','BOOLEAN','CHOICE','REFERENCE') AND version_no > 0", schema="trd")
    op.create_check_constraint("ck_trade_property_binding", "trade_property_definition", "(value_type = 'REFERENCE') = (catalogue_id IS NOT NULL)", schema="trd")
    op.create_table("trade_property_reference",
        sa.Column("trade_id", sa.UUID(), sa.ForeignKey("trd.trade.trade_id"), primary_key=True),
        sa.Column("definition_id", sa.UUID(), sa.ForeignKey("trd.trade_property_definition.definition_id"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("record_version_id", sa.UUID(), sa.ForeignKey("trd.reference_catalogue_record.record_version_id"), nullable=False), schema="trd")
    op.create_table("trade_selection_policy",
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), primary_key=True), sa.Column("role", sa.String(30), primary_key=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("role IN ('COUNTERPARTY','EXECUTING_BROKER','TRADER') AND version_no > 0", name="ck_trade_selection_role"), schema="trd")
    op.create_table("trade_selection_member",
        sa.Column("member_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False), sa.Column("role", sa.String(30), nullable=False),
        sa.Column("organisation_id", sa.UUID(), sa.ForeignKey("secm.organisation.organisation_id")),
        sa.Column("person_id", sa.UUID(), sa.ForeignKey("secm.person.person_id")),
        sa.ForeignKeyConstraint(["tenant_id", "role"], ["trd.trade_selection_policy.tenant_id", "trd.trade_selection_policy.role"]),
        sa.UniqueConstraint("tenant_id", "role", "organisation_id", name="uq_trade_selection_organisation"),
        sa.UniqueConstraint("tenant_id", "role", "person_id", name="uq_trade_selection_person"),
        sa.CheckConstraint("(role = 'TRADER' AND person_id IS NOT NULL AND organisation_id IS NULL) OR (role IN ('COUNTERPARTY','EXECUTING_BROKER') AND organisation_id IS NOT NULL AND person_id IS NULL)", name="ck_trade_selection_target"), schema="trd")
    op.create_table("trade_configuration_event",
        sa.Column("event_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False),
        sa.Column("actor_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False), sa.Column("subject_id", sa.UUID()),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("payload", JSONB(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), schema="trd")
    op.execute("""
    CREATE TRIGGER guard_reference_record BEFORE UPDATE OR DELETE ON trd.reference_catalogue_record FOR EACH ROW EXECUTE FUNCTION trd.guard_trade_catalogue_meaning();
    CREATE FUNCTION trd.guard_governed_reference() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Reference assignments and audit events are immutable' USING ERRCODE='23514'; END IF;
      IF TG_TABLE_NAME='trade_configuration_event' THEN RETURN NEW; END IF;
      IF NOT EXISTS (
        SELECT 1 FROM trd.trade t JOIN trd.strategy s USING(strategy_id)
        JOIN trd.trade_property_definition d ON d.definition_id=NEW.definition_id
        JOIN trd.reference_catalogue c ON c.catalogue_id=d.catalogue_id
        JOIN trd.reference_catalogue_record r ON r.catalogue_id=c.catalogue_id AND r.record_version_id=NEW.record_version_id
        WHERE t.trade_id=NEW.trade_id AND s.tenant_id=NEW.tenant_id AND d.tenant_id=NEW.tenant_id AND c.tenant_id=NEW.tenant_id
          AND d.value_type='REFERENCE' AND d.status='ACTIVE' AND c.status='ACTIVE' AND r.status='ACTIVE'
      ) THEN RAISE EXCEPTION 'Invalid governed reference assignment' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_trade_property_reference BEFORE INSERT OR UPDATE OR DELETE ON trd.trade_property_reference FOR EACH ROW EXECUTE FUNCTION trd.guard_governed_reference();
    CREATE TRIGGER guard_trade_configuration_event BEFORE UPDATE OR DELETE ON trd.trade_configuration_event FOR EACH ROW EXECUTE FUNCTION trd.guard_governed_reference();
    CREATE FUNCTION trd.guard_property_binding() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.value_type='REFERENCE' AND NOT EXISTS(SELECT 1 FROM trd.reference_catalogue WHERE catalogue_id=NEW.catalogue_id AND tenant_id=NEW.tenant_id AND status='ACTIVE') THEN
        RAISE EXCEPTION 'Property requires an active tenant catalogue' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_property_binding BEFORE INSERT ON trd.trade_property_definition FOR EACH ROW EXECUTE FUNCTION trd.guard_property_binding();
    """)

def downgrade():
    # Empty test installations can revert; populated installations need archival.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM trd.reference_catalogue) OR EXISTS(SELECT 1 FROM trd.trade_selection_policy)
        OR EXISTS(SELECT 1 FROM trd.trade_configuration_event)
        OR EXISTS(SELECT 1 FROM trd.trade_property_definition WHERE value_type IN ('INTEGER','REFERENCE')) THEN
        RAISE EXCEPTION 'Governed trade history requires archival before downgrade; restore a backup instead';
      END IF;
    END $$;""")
    op.drop_table("trade_property_reference",schema="trd")
    op.drop_table("trade_selection_member",schema="trd")
    op.drop_table("trade_selection_policy",schema="trd")
    op.drop_table("trade_configuration_event",schema="trd")
    op.execute("DROP TRIGGER guard_property_binding ON trd.trade_property_definition; DROP FUNCTION trd.guard_property_binding(); DROP FUNCTION trd.guard_governed_reference();")
    op.drop_constraint("ck_trade_property_binding","trade_property_definition",schema="trd")
    op.drop_column("trade_property_definition","catalogue_id",schema="trd")
    op.drop_constraint("ck_trade_property_type","trade_property_definition",schema="trd")
    op.create_check_constraint("ck_trade_property_type","trade_property_definition","value_type IN ('TEXT','DECIMAL','DATE','BOOLEAN','CHOICE') AND version_no > 0",schema="trd")
    op.drop_table("reference_catalogue_record",schema="trd")
    op.drop_table("reference_catalogue",schema="trd")
