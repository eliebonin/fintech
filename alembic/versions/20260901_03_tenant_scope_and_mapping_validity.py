"""Add tenant strategy scope and PostgreSQL external-mapping validity controls."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_03"
down_revision = "20260831_02_static_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tenant ownership and reject overlapping/incompatible external mappings."""

    op.add_column(
        "strategy",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=True,
            comment="Tenant permitted to own and operate the strategy; unscoped legacy strategies are rejected by tenant-facing services.",
        ),
        schema="trd",
    )
    op.create_foreign_key(
        "fk_strategy_tenant_id",
        "strategy",
        "tenant",
        ["tenant_id"],
        ["tenant_id"],
        source_schema="trd",
        referent_schema="ten",
    )
    op.create_index("ix_strategy_tenant", "strategy", ["tenant_id"], schema="trd")

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE ing.external_object_mapping
        ADD CONSTRAINT ex_external_object_mapping_effective_period
        EXCLUDE USING gist (
            external_id_namespace_id WITH =,
            external_object_type WITH =,
            external_id_value WITH =,
            COALESCE(context_market_venue_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status IN ('PROPOSED', 'VERIFIED'))
        """
    )
    op.execute(
        """
        CREATE FUNCTION ing.validate_external_mapping_target() RETURNS trigger AS $$
        BEGIN
            IF NEW.target_object_type = 'REFERENCE_NODE' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.financial_reference_node WHERE reference_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not a reference node', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'LISTING' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.listing WHERE listing_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not a listing', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'INSTRUMENT' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.instrument WHERE instrument_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not an instrument', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'STRATEGY' THEN
                IF NOT EXISTS (SELECT 1 FROM trd.strategy WHERE strategy_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not a strategy', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'ORGANISATION' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.organisation WHERE organisation_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not an organisation', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'TRADE' THEN
                IF NOT EXISTS (SELECT 1 FROM trd.trade WHERE trade_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not a trade', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'PERSON' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.person WHERE person_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'external mapping target % is not a person', NEW.target_object_id;
                END IF;
            ELSE
                RAISE EXCEPTION 'unsupported external mapping target type %', NEW.target_object_type;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_validate_external_mapping_target
        BEFORE INSERT OR UPDATE OF target_object_type, target_object_id
        ON ing.external_object_mapping
        FOR EACH ROW EXECUTE FUNCTION ing.validate_external_mapping_target()
        """
    )


def downgrade() -> None:
    """Remove the controlled validity rules and tenant strategy ownership field."""

    op.execute("DROP TRIGGER IF EXISTS trg_validate_external_mapping_target ON ing.external_object_mapping")
    op.execute("DROP FUNCTION IF EXISTS ing.validate_external_mapping_target()")
    op.execute("ALTER TABLE ing.external_object_mapping DROP CONSTRAINT IF EXISTS ex_external_object_mapping_effective_period")
    op.drop_index("ix_strategy_tenant", table_name="strategy", schema="trd")
    op.drop_constraint("fk_strategy_tenant_id", "strategy", schema="trd", type_="foreignkey")
    op.drop_column("strategy", "tenant_id", schema="trd")
