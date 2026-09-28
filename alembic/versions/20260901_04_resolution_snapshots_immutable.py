"""Protect frozen market-data resolution evidence from in-place mutation."""

from alembic import op


revision = "20260901_04"
down_revision = "20260901_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make completed resolver headers and items append-only audit records."""

    op.execute(
        """
        CREATE FUNCTION md.prevent_resolution_snapshot_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'market-data resolution snapshots are immutable; create a new snapshot instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_resolution_snapshot_immutable
        BEFORE UPDATE OR DELETE ON md.market_data_resolution_snapshot
        FOR EACH ROW EXECUTE FUNCTION md.prevent_resolution_snapshot_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_resolution_snapshot_item_immutable
        BEFORE UPDATE OR DELETE ON md.market_data_resolution_snapshot_item
        FOR EACH ROW EXECUTE FUNCTION md.prevent_resolution_snapshot_mutation()
        """
    )


def downgrade() -> None:
    """Remove snapshot mutation protection for an explicit schema rollback."""

    op.execute("DROP TRIGGER IF EXISTS trg_resolution_snapshot_item_immutable ON md.market_data_resolution_snapshot_item")
    op.execute("DROP TRIGGER IF EXISTS trg_resolution_snapshot_immutable ON md.market_data_resolution_snapshot")
    op.execute("DROP FUNCTION IF EXISTS md.prevent_resolution_snapshot_mutation()")
