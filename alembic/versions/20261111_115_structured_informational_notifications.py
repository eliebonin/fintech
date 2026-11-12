"""Information-only structured schedules; no grants or financial defaults."""
from alembic import op
revision='20261111_115'
down_revision='20261111_114'
branch_labels=depends_on=None

def upgrade():
    op.drop_constraint('ck_lifecycle_assistance_tier','strategy_lifecycle_assistance',schema='ten',type_='check')
    op.create_check_constraint('ck_lifecycle_assistance_tier','strategy_lifecycle_assistance',"selected_tier BETWEEN 0 AND 3 AND event_type IN ('BOND_MATURITY','FX_FORWARD_MATURITY','FUTURE_EXPIRY','OPTION_EXPIRY','STRUCTURED_OBSERVATION') AND (event_type NOT IN ('FUTURE_EXPIRY','OPTION_EXPIRY','STRUCTURED_OBSERVATION') OR selected_tier <= 1)",schema='ten')

def downgrade():
    raise RuntimeError('Retained structured-notification selections cannot be discarded by downgrade.')
