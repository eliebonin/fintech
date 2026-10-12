"""Bound catalogue observation reads without rewriting financial evidence."""
from alembic import op
import sqlalchemy as sa

revision = '20261008_71'
down_revision = '20261008_70'
branch_labels = depends_on = None

INDEX_DEFINITIONS = {
    'ix_md_observation_accepted_latest': "(market_data_series_id, market_date DESC NULLS LAST, observed_at_utc DESC, received_at_utc DESC) WHERE quality_status = 'ACCEPTED'",
    'ix_md_observation_accepted_supersedes': "(supersedes_observation_id) WHERE quality_status = 'ACCEPTED' AND supersedes_observation_id IS NOT NULL",
}


def upgrade():
    # Concurrent builds avoid excluding operating ingestion/booking writes.
    # Each build must run outside a transaction; IF NOT EXISTS supports retry
    # after a successfully built first index but interrupted second build.
    with op.get_context().autocommit_block():
        for name, definition in INDEX_DEFINITIONS.items():
            op.execute(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON md.market_data_observation {definition}')
            if op.get_context().as_sql:
                # Keep the validation in the emitted script: offline generation
                # cannot query PostgreSQL, but execution must still reject an
                # invalid index left behind by an interrupted concurrent build.
                op.execute(f"""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
                        JOIN pg_namespace n ON n.oid=c.relnamespace
                        WHERE n.nspname='md' AND c.relname='{name}' AND i.indisvalid)
                    THEN RAISE EXCEPTION 'Index {name} is invalid; inspect before retrying';
                    END IF;
                END $$""")
                continue
            valid = op.get_bind().scalar(sa.text(
                "SELECT i.indisvalid FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='md' AND c.relname=:name"
            ).bindparams(name=name))
            if valid is not True:
                raise RuntimeError(f'Index {name} is invalid; inspect the interrupted concurrent build before retrying')


def downgrade():
    # Only indexes are removed; observation rows and correction lineage remain.
    with op.get_context().autocommit_block():
        for name in reversed(INDEX_DEFINITIONS):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS md.{name}')
