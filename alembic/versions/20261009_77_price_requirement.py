"""Explicit economic price requirements; existing policies remain unchanged."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_77'
down_revision = '20261008_76'
branch_labels = depends_on = None


def upgrade():
    op.add_column('valuation_policy_rule', sa.Column('price_requirement', sa.String(30)), schema='ten')
    op.add_column('valuation_policy_rule', sa.Column('allow_split_conversion', sa.Boolean(),
        nullable=False, server_default=sa.text('false')), schema='ten')
    op.create_check_constraint('ck_policy_price_requirement', 'valuation_policy_rule',
        "(price_requirement IS NULL AND NOT allow_split_conversion) OR "
        "(price_requirement='AS_TRADED' AND pricing_convention<>'LEGACY' AND "
        "series_type IN ('CLOSE','OFFICIAL_CLOSE') AND (value_basis IS NULL OR "
        "value_basis IN ('RAW','SPLIT_ADJUSTED')))", schema='ten')
    op.create_table('market_data_price_basis_proof',
        sa.Column('proof_id', sa.UUID(), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('observation_id', sa.UUID(), sa.ForeignKey('md.market_data_observation.market_data_observation_id'), nullable=False),
        sa.Column('recorded_at_utc', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('proof_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('proof_hash', sa.String(64), nullable=False),
        sa.UniqueConstraint('observation_id','proof_hash', name='uq_price_basis_proof_content'), schema='md')
    op.create_index('ix_price_basis_proof_asof', 'market_data_price_basis_proof', ['observation_id','recorded_at_utc'], schema='md')
    op.execute('CREATE TRIGGER price_basis_proof_immutable BEFORE UPDATE OR DELETE ON md.market_data_price_basis_proof '
        'FOR EACH ROW EXECUTE FUNCTION md.prevent_resolution_snapshot_mutation()')


def downgrade():
    raise RuntimeError('Forward-only: retain immutable economic policy versions.')
