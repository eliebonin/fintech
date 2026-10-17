"""Explicit group strategy scopes and optimistic access revisions."""
from alembic import op
from sqlalchemy import text
from security_master_schema import models as m

revision='20261013_85'
down_revision='20261013_84'
branch_labels=None
depends_on=None

def upgrade():
    c=op.get_bind()
    op.execute("ALTER TABLE ten.access_group ADD COLUMN IF NOT EXISTS scope_mode varchar(20) NOT NULL DEFAULT 'ALL'")
    op.execute('ALTER TABLE ten.access_group ADD COLUMN IF NOT EXISTS version_no integer NOT NULL DEFAULT 1')
    op.execute("ALTER TABLE ten.access_group ALTER COLUMN scope_mode SET DEFAULT 'SELECTED'")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_access_group_strategy_mode') THEN ALTER TABLE ten.access_group ADD CONSTRAINT ck_access_group_strategy_mode CHECK(scope_mode IN ('ALL','SELECTED')); END IF; END $$")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_strategy_scope_identity') THEN ALTER TABLE trd.strategy ADD CONSTRAINT uq_strategy_scope_identity UNIQUE(tenant_id,strategy_id); END IF; END $$")
    m.access_group_strategy.create(c,checkfirst=True)
    op.execute('ALTER TABLE md.market_data_resolution_snapshot ADD COLUMN IF NOT EXISTS strategy_id uuid REFERENCES trd.strategy(strategy_id)')
    op.execute("ALTER TABLE md.market_data_resolution_snapshot ADD COLUMN IF NOT EXISTS context_scope varchar(20) NOT NULL DEFAULT 'LEGACY_UNKNOWN'")
    op.execute("UPDATE md.market_data_resolution_snapshot s SET strategy_id=p.strategy_id,context_scope='STRATEGY' FROM ten.valuation_policy p WHERE s.valuation_policy_id=p.valuation_policy_id AND p.strategy_id IS NOT NULL AND s.context_scope='LEGACY_UNKNOWN'")
    op.execute("DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='ck_resolution_context_scope') THEN ALTER TABLE md.market_data_resolution_snapshot ADD CONSTRAINT ck_resolution_context_scope CHECK(context_scope IN ('SHARED','STRATEGY','LEGACY_UNKNOWN')); END IF; END $$")
    op.execute("DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='ck_resolution_context_identity') THEN ALTER TABLE md.market_data_resolution_snapshot ADD CONSTRAINT ck_resolution_context_identity CHECK((strategy_id IS NOT NULL AND context_scope='STRATEGY') OR (strategy_id IS NULL AND context_scope IN ('SHARED','LEGACY_UNKNOWN'))); END IF; END $$")
    op.execute("INSERT INTO ten.access_group_grant(tenant_id,group_id,action_code) SELECT tenant_id,group_id,'STRATEGY_CREATE' FROM ten.access_group_grant WHERE action_code='STRATEGY_WRITE' ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO ten.access_audit_event(tenant_id,actor_id,subject_id,action,details) SELECT g.tenant_id,a.user_account_id,a.user_account_id,'STRATEGY_SCOPE_TRANSITION',jsonb_build_object('revision','20261013_85','groupId',g.group_id,'scopeMode',g.scope_mode,'reason','Preserve existing tenant-wide grants explicitly') FROM ten.access_group g JOIN LATERAL (SELECT user_account_id FROM ten.tenant_user_account WHERE tenant_id=g.tenant_id AND membership_role='TENANT_ADMIN' ORDER BY user_account_id LIMIT 1) a ON true WHERE NOT EXISTS(SELECT 1 FROM ten.access_audit_event e WHERE e.tenant_id=g.tenant_id AND e.action='STRATEGY_SCOPE_TRANSITION' AND e.details->>'groupId'=g.group_id::text)")

def downgrade():
    raise RuntimeError('Forward-only: removing strategy scopes would widen operational access.')
