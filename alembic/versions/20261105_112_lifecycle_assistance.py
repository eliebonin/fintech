"""Lifecycle assistance subscriptions and strategy/event selections."""
from alembic import op
import sqlalchemy as sa
revision='20261105_112'
down_revision='20261104_111'
branch_labels=depends_on=None


def upgrade():
    from security_master_schema import models as m
    for table in (m.tenant_lifecycle_subscription,m.strategy_lifecycle_assistance):table.create(op.get_bind())
    op.execute("""CREATE FUNCTION ten.reject_lifecycle_assistance_history_change() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Lifecycle subscription and assistance history is immutable'; END $$;
      CREATE TRIGGER lifecycle_subscription_immutable BEFORE UPDATE OR DELETE ON ten.tenant_lifecycle_subscription FOR EACH ROW EXECUTE FUNCTION ten.reject_lifecycle_assistance_history_change();
      CREATE TRIGGER lifecycle_assistance_immutable BEFORE UPDATE OR DELETE ON ten.strategy_lifecycle_assistance FOR EACH ROW EXECUTE FUNCTION ten.reject_lifecycle_assistance_history_change();
      INSERT INTO ten.platform_module(platform_module_id,module_code,display_name,description,module_category,sort_order)
      VALUES(uuidv7(),'LIFECYCLE_MANAGEMENT','Lifecycle management','Tiered Ops assistance; notification discovery is a subsequent delivery.','TRADING',90)
      ON CONFLICT(module_code) DO NOTHING;""")


def downgrade():
    raise RuntimeError('Retained lifecycle configuration history cannot be discarded by downgrade.')
