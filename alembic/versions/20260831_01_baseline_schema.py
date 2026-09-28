"""Create the initial Security Master domain schemas and SQLAlchemy metadata."""

from alembic import op

revision = "20260831_01"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA_NAMES = ("secm", "ten", "ing", "md", "trd", "nav")


def upgrade() -> None:
    """Create the stable domain-schema containers used by the frozen baseline revision."""

    for schema_name in SCHEMA_NAMES:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')


def downgrade() -> None:
    """Remove the empty domain-schema containers after the frozen revision drops its tables."""

    for schema_name in reversed(SCHEMA_NAMES):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
