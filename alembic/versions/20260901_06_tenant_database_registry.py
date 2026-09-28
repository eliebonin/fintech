"""Register trusted per-tenant overlay database routes."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_06"
down_revision = "20260901_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_database_registry",
        sa.Column("tenant_database_registry_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one tenant overlay database route."),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False, unique=True, comment="Tenant whose confidential operational overlay is routed to the registered database."),
        sa.Column("database_name", sa.String(length=250), nullable=False, unique=True, comment="Trusted logical PostgreSQL database name for the tenant overlay; never accepted directly from a client request."),
        sa.Column("cluster_id", sa.String(length=250), nullable=False, comment="Trusted PostgreSQL cluster or infrastructure identifier hosting the overlay database."),
        sa.Column("environment", sa.String(length=30), nullable=False, server_default=sa.text("'PROD'"), comment="Deployment environment of the registered tenant database such as PROD, UAT, TEST, or SANDBOX."),
        sa.Column("schema_version", sa.Integer(), nullable=False, comment="Last successfully applied overlay schema revision recorded by the control plane."),
        sa.Column("connection_secret_reference", sa.String(length=500), nullable=False, comment="Reference to a secret-manager entry; credentials are never stored in this table."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Route lifecycle status such as PROVISIONING, ACTIVE, SUSPENDED, RETIRED, or FAILED."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which the route was registered."),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp of the latest route or schema-version update."),
        schema="ten",
    )


def downgrade() -> None:
    op.drop_table("tenant_database_registry", schema="ten")
