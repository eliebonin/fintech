"""Allow retained assessed CLEAN-note stocks, preserving immutable scope guards."""
from alembic import op
from sqlalchemy import text

revision='20261028_102'
down_revision='20261027_101'
branch_labels=None
depends_on=None


def upgrade():
    original=op.get_bind().scalar(text("SELECT pg_get_functiondef('nav.protect_accrued_balance_snapshot()'::regprocedure)"))
    anchor="WHERE i.instrument_node_id=NEW.instrument_id AND t.type_code='BOND'"
    if original.count(anchor)!=1:raise RuntimeError('Unexpected accrued stock guard; review before extending')
    replacement="""WHERE i.instrument_node_id=NEW.instrument_id AND (t.type_code='BOND' OR
          (t.type_code='STRUCTURED_PRODUCT' AND NEW.evidence->'sourceRefs'->>'kind'='STRUCTURED_NOTE_CLEAN_ASSESSED'
           AND NEW.basis IN ('STRUCTURED_NOTE_CLEAN_ASSESSED','NOT_ASSESSED')))"""
    op.execute(original.replace(anchor,replacement).replace('requires a canonical bond','requires a canonical bond or assessed CLEAN note'))


def downgrade():
    raise RuntimeError('Retained note stock evidence cannot be downgraded safely')
