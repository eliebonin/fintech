"""Tenant calendar versions and immutable assignment decisions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID,JSONB
revision='20261007_68'
down_revision='20261007_67'
branch_labels=depends_on=None

def upgrade():
    columns=[
        sa.Column('tenant_id',UUID(as_uuid=True),sa.ForeignKey('ten.tenant.tenant_id'),comment='Owner of a managed fund calendar; null identifies platform reference calendars.'),
        sa.Column('logical_code',sa.String(100),comment='Tenant-local calendar identity shared by immutable versions.'),
        sa.Column('version_no',sa.Integer,comment='Monotonically increasing tenant-local calendar version.'),
        sa.Column('coverage_from',sa.Date,comment='First date explicitly assessed by this calendar version.'),
        sa.Column('coverage_to',sa.Date,comment='Last date explicitly assessed by this calendar version.'),
        sa.Column('definition_json',JSONB,comment='Frozen configuration and component/day decision evidence.'),
        sa.Column('sealed',sa.Boolean,nullable=False,server_default=sa.text('false'),comment='Published tenant versions and their dated records are immutable when sealed.'),
        sa.Column('created_by_user_account_id',UUID(as_uuid=True),sa.ForeignKey('secm.user_account.user_account_id'),comment='Administrator publishing this tenant version; null for legacy reference definitions.'),
        sa.Column('created_at_utc',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('CURRENT_TIMESTAMP'),comment='Recording time; legacy values do not establish historical calendar publication.'),
        sa.Column('submission_key',sa.String(255),comment='Tenant-scoped calendar publication idempotency key.'),
        sa.Column('submission_fingerprint',sa.String(64),comment='SHA256 of the publication payload for exact replay validation.'),
    ]
    for column in columns: op.add_column('market_calendar',column,schema='cal')
    op.create_unique_constraint('uq_calendar_tenant_version','market_calendar',['tenant_id','logical_code','version_no'],schema='cal')
    op.create_unique_constraint('uq_calendar_tenant_submission','market_calendar',['tenant_id','submission_key'],schema='cal')
    op.create_table('calendar_assignment',
        sa.Column('calendar_assignment_id',UUID(as_uuid=True),primary_key=True,server_default=sa.text('uuidv7()'),comment='Immutable identifier of a version-pinned calendar assignment decision.'),
        sa.Column('tenant_id',UUID(as_uuid=True),sa.ForeignKey('ten.tenant.tenant_id'),nullable=False,comment='Tenant owning this calendar assignment.'),
        sa.Column('market_calendar_id',UUID(as_uuid=True),sa.ForeignKey('cal.market_calendar.market_calendar_id'),nullable=False,comment='Exact published calendar version assigned to this target.'),
        sa.Column('target_kind',sa.String(20),nullable=False,comment='Target class STRATEGY or FUND_REFERENCE.'),
        sa.Column('target_id',UUID(as_uuid=True),nullable=False,comment='Validated tenant strategy or visible fund reference UUID.'),
        sa.Column('purpose',sa.String(20),nullable=False,comment='Calendar purpose VALUATION, DEALING or SETTLEMENT.'),
        sa.Column('valid_from',sa.Date,nullable=False,comment='First effective date of this assignment.'),
        sa.Column('valid_to',sa.Date,nullable=False,comment='Last effective date of this assignment.'),
        sa.Column('reason',sa.String(500),nullable=False,comment='Administrator rationale for this assignment or reassignment.'),
        sa.Column('created_by_user_account_id',UUID(as_uuid=True),sa.ForeignKey('secm.user_account.user_account_id'),nullable=False,comment='Administrator recording this assignment decision.'),
        sa.Column('created_at_utc',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('CURRENT_TIMESTAMP'),comment='UTC recording time used for historical information-cutoff selection.'),
        sa.Column('submission_key',sa.String(255),nullable=False,comment='Tenant-scoped assignment idempotency key.'),
        sa.Column('submission_fingerprint',sa.String(64),nullable=False,comment='SHA256 of the canonical assignment payload.'),
        sa.UniqueConstraint('tenant_id','submission_key',name='uq_calendar_assignment_submission'),
        sa.CheckConstraint('valid_to >= valid_from',name='ck_calendar_assignment_dates'),
        sa.CheckConstraint("target_kind IN ('STRATEGY','FUND_REFERENCE')",name='ck_calendar_assignment_target'),
        sa.CheckConstraint("purpose IN ('VALUATION','DEALING','SETTLEMENT')",name='ck_calendar_assignment_purpose'),schema='cal')
    op.execute("""
      CREATE FUNCTION cal.protect_tenant_calendar() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.sealed THEN RAISE EXCEPTION 'Published calendar versions are immutable'; END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW;
      END $$;
      CREATE TRIGGER protect_tenant_calendar BEFORE UPDATE OR DELETE ON cal.market_calendar
      FOR EACH ROW EXECUTE FUNCTION cal.protect_tenant_calendar();
      CREATE FUNCTION cal.protect_calendar_child() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE locked boolean;
      BEGIN
        IF TG_OP <> 'INSERT' THEN
          SELECT sealed INTO locked FROM cal.market_calendar WHERE market_calendar_id=OLD.market_calendar_id FOR SHARE;
          IF locked THEN RAISE EXCEPTION 'Published calendar dates are immutable'; END IF;
        END IF;
        IF TG_OP <> 'DELETE' THEN
          SELECT sealed INTO locked FROM cal.market_calendar WHERE market_calendar_id=NEW.market_calendar_id FOR SHARE;
          IF locked THEN RAISE EXCEPTION 'Published calendar dates are immutable'; END IF;
          RETURN NEW;
        END IF; RETURN OLD;
      END $$;
      CREATE TRIGGER protect_calendar_sessions BEFORE INSERT OR UPDATE OR DELETE ON cal.market_calendar_session
      FOR EACH ROW EXECUTE FUNCTION cal.protect_calendar_child();
      CREATE TRIGGER protect_calendar_holidays BEFORE INSERT OR UPDATE OR DELETE ON cal.market_calendar_holiday
      FOR EACH ROW EXECUTE FUNCTION cal.protect_calendar_child();
      CREATE FUNCTION cal.protect_calendar_assignment() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Calendar assignments are append-only'; END $$;
      CREATE TRIGGER protect_calendar_assignment BEFORE UPDATE OR DELETE ON cal.calendar_assignment
      FOR EACH ROW EXECUTE FUNCTION cal.protect_calendar_assignment();
    """)

def downgrade():
    raise RuntimeError('Forward-only: preserve calendar publication and assignment evidence.')
