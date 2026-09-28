"""Store tenant-local evidence for central canonical UUID links."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_08"
down_revision = "20260901_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canonical_reference_link",
        sa.Column("canonical_reference_link_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for tenant-local evidence linking an object to central canonical identity."),
        sa.Column("local_object_type", sa.String(length=50), nullable=False, comment="Tenant-database object kind carrying the central reference, such as TRADE_SUBJECT, POSITION_LINE, or OVERRIDE."),
        sa.Column("local_object_id", sa.UUID(), nullable=False, comment="UUID of the object in the tenant overlay database; no cross-database foreign key is possible."),
        sa.Column("canonical_reference_node_id", sa.UUID(), nullable=False, comment="Immutable central financial-reference UUID validated through the canonical API."),
        sa.Column("canonical_object_type", sa.String(length=50), nullable=False, comment="Central object kind validated for the link, such as INSTRUMENT, LISTING, REFERENCE_NODE, or CURRENCY."),
        sa.Column("canonical_version", sa.Integer(), nullable=False, comment="Canonical definition version observed and validated when this link evidence was recorded."),
        sa.Column("canonical_status", sa.String(length=30), nullable=False, comment="Central lifecycle status observed during validation, such as ACTIVE or MATURED."),
        sa.Column("validated_as_of_date", sa.Date(), nullable=False, comment="Business date on which the canonical API validation was effective."),
        sa.Column("validated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which the central UUID was validated."),
        sa.Column("validation_result", sa.String(length=30), nullable=False, server_default=sa.text("'VALID'"), comment="Validation result such as VALID, STALE, REJECTED, or NOT_FOUND."),
        sa.Column("central_api_version", sa.String(length=100), nullable=False, comment="Version of the central canonical API contract that supplied the validation response."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Lifecycle status of this tenant-local link evidence."),
        sa.UniqueConstraint("local_object_type", "local_object_id", name="uq_canonical_reference_link_local_object"),
        schema="ten",
    )
    op.create_index("ix_canonical_reference_link_canonical", "canonical_reference_link", ["canonical_reference_node_id", "canonical_object_type"], schema="ten")


def downgrade() -> None:
    op.drop_index("ix_canonical_reference_link_canonical", table_name="canonical_reference_link", schema="ten")
    op.drop_table("canonical_reference_link", schema="ten")
