"""Add composite pricing conventions without rewriting legacy rules or evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '20261007_66'
down_revision = '20261007_65'
branch_labels = depends_on = None


def upgrade():
    columns = [
        sa.Column('market_venue_id', UUID(as_uuid=True), sa.ForeignKey('secm.market_venue.market_venue_id'), comment='Optional selected-listing venue filter; never inferred from instrument currency.'),
        sa.Column('pricing_convention', sa.String(30), nullable=False, server_default='LEGACY', comment='LEGACY, SESSION_CLOSE, NAMED_FIXING or EXPLICIT_TIME selection semantics.'),
        sa.Column('pricing_cut_id', UUID(as_uuid=True), sa.ForeignKey('md.valuation_cut.valuation_cut_id'), comment='Rule-specific local pricing time definition, separate from the information cutoff.'),
        sa.Column('fixing_code', sa.String(100), comment='Exact declared FIXING_CODE series dimension required for named fixing selection.'),
        sa.Column('value_basis', sa.String(50), comment='Optional required observation value basis; no implicit adjustment conversion.'),
    ]
    for column in columns:
        op.add_column('valuation_policy_rule', column, schema='ten')
    op.add_column('market_data_resolution_snapshot_item', sa.Column('pricing_evidence', JSONB,
        comment='Frozen composite pricing target, calendar provenance and convention; null for legacy snapshots.'), schema='md')


def downgrade():
    raise RuntimeError('Forward-only: preserve frozen pricing evidence.')
