"""Add common exchange-traded-product terms."""

from alembic import op
import sqlalchemy as sa


revision = "20260904_21"
down_revision = "20260904_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "etp_terms",
        sa.Column("etp_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated version of exchange-traded-product terms."),
        sa.Column("instrument_node_id", sa.UUID(), nullable=False, comment="Economic instrument node representing the ETF, ETC, ETN, ETV, or other exchange-traded product."),
        sa.Column("etp_kind", sa.String(length=30), nullable=False, comment="Concrete exchange-traded-product kind such as ETF, ETC, ETN, ETV, or ETI."),
        sa.Column("legal_form", sa.String(length=50), nullable=False, comment="Legal wrapper such as UCITS_FUND, DEBT_NOTE, CERTIFICATE, or OTHER."),
        sa.Column("replication_method", sa.String(length=30), server_default=sa.text("'NOT_APPLICABLE'"), nullable=False, comment="How the product obtains exposure, such as PHYSICAL, SYNTHETIC, HYBRID, or NOT_APPLICABLE."),
        sa.Column("collateralisation_type", sa.String(length=30), server_default=sa.text("'NOT_APPLICABLE'"), nullable=False, comment="Collateral or credit basis such as UNSECURED, SECURED, PHYSICAL, CASH, or NOT_APPLICABLE."),
        sa.Column("redemption_model", sa.String(length=40), nullable=False, comment="Redemption lifecycle such as OPEN_ENDED, FIXED_MATURITY, or ISSUER_REDEEMABLE."),
        sa.Column("distribution_policy", sa.String(length=30), nullable=True, comment="Income policy such as ACCUMULATING, DISTRIBUTING, NONE, or UNKNOWN."),
        sa.Column("reference_node_id", sa.UUID(), nullable=True, comment="Primary reference index, commodity, basket, asset, or other reference node when one is defined."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date for which this version of exchange-traded-product terms is effective."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date for which this version of exchange-traded-product terms is effective."),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Whether this is the current operationally approved ETP terms version."),
        sa.Column("sequence_no", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Monotonically increasing terms version sequence for the same exchange-traded-product instrument."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Source payload evidencing this exchange-traded-product terms version when available."),
        sa.ForeignKeyConstraint(["instrument_node_id"], ["secm.instrument.instrument_node_id"]),
        sa.ForeignKeyConstraint(["reference_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"]),
        sa.PrimaryKeyConstraint("etp_terms_id"),
        sa.UniqueConstraint("instrument_node_id", "sequence_no", name="uq_etp_terms_version"),
        sa.CheckConstraint("etp_kind IN ('ETF', 'ETC', 'ETN', 'ETV', 'ETI')", name="ck_etp_terms_kind"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_etp_terms_valid_period"),
        schema="secm",
    )


def downgrade() -> None:
    op.drop_table("etp_terms", schema="secm")
