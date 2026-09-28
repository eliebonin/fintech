"""Add generic return profiles and index semantic subtype tables."""

from alembic import op
import sqlalchemy as sa


revision = "20260904_20"
down_revision = "20260903_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "return_profile",
        sa.Column("return_profile_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed generic performance-return profile."),
        sa.Column("profile_code", sa.String(length=60), nullable=False, comment="Stable controlled code such as PRICE_RETURN, NET_TOTAL_RETURN, or EXCESS_TOTAL_RETURN."),
        sa.Column("display_name", sa.String(length=150), nullable=False, comment="Human-readable name of the generic return profile."),
        sa.Column("description", sa.Text(), nullable=False, comment="Plain-language definition of how performance or income is represented."),
        sa.Column("base_return_basis", sa.String(length=30), nullable=False, comment="Underlying basis of the profile, such as PRICE, TOTAL, or INCOME_ONLY."),
        sa.Column("income_treatment", sa.String(length=50), nullable=False, comment="Treatment of distributed income, such as NONE, REINVESTED_GROSS, REINVESTED_NET, or POINTS_ONLY."),
        sa.Column("tax_treatment", sa.String(length=50), nullable=True, comment="Tax convention applied to income when relevant, such as NONE, GROSS, or NET_WITHHOLDING."),
        sa.Column("financing_treatment", sa.String(length=50), server_default=sa.text("'NONE'"), nullable=False, comment="Treatment of financing or reference-rate adjustments, such as NONE or SUBTRACT_REFERENCE_RATE."),
        sa.Column("requires_financing_reference", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Whether a consumer must provide a financing-rate reference for this profile."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed return profile."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering value for operational profile lists."),
        sa.PrimaryKeyConstraint("return_profile_id"),
        sa.UniqueConstraint("profile_code"),
        schema="secm",
    )
    op.create_table(
        "index_family",
        sa.Column("index_family_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a conceptual index family or lineage."),
        sa.Column("family_node_id", sa.UUID(), nullable=False, comment="Non-tradeable INDEX_FAMILY reference node representing the conceptual grouping."),
        sa.Column("provider_organisation_id", sa.UUID(), nullable=True, comment="Organisation administering or publishing the index family when known."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the index family."),
        sa.ForeignKeyConstraint(["family_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.ForeignKeyConstraint(["provider_organisation_id"], ["secm.organisation.organisation_id"]),
        sa.PrimaryKeyConstraint("index_family_id"),
        sa.UniqueConstraint("family_node_id"),
        schema="secm",
    )
    op.create_table(
        "index_terms",
        sa.Column("index_node_id", sa.UUID(), nullable=False, comment="Concrete INDEX reference node representing one return or currency variant."),
        sa.Column("index_family_id", sa.UUID(), nullable=True, comment="Conceptual index family to which this concrete index variant belongs."),
        sa.Column("index_kind", sa.String(length=40), nullable=False, comment="Index kind such as PUBLIC, QIS, PROPRIETARY, or CUSTOM_BASKET."),
        sa.Column("return_profile_id", sa.UUID(), nullable=True, comment="Generic return profile governing the variant; nullable while an unapproved source definition remains incomplete."),
        sa.Column("base_currency_id", sa.UUID(), nullable=True, comment="Currency in which the index level is calculated or published."),
        sa.Column("administrator_organisation_id", sa.UUID(), nullable=True, comment="Organisation responsible for administering the index methodology when known."),
        sa.Column("calculation_agent_organisation_id", sa.UUID(), nullable=True, comment="Organisation responsible for calculating or disseminating the index level when distinct from the administrator."),
        sa.Column("base_date", sa.Date(), nullable=True, comment="Base date from which the index level history is defined."),
        sa.Column("base_level", sa.Numeric(precision=30, scale=12), nullable=True, comment="Starting index level on the base date."),
        sa.Column("methodology_reference", sa.String(length=500), nullable=True, comment="Reference to the governing methodology document or source identifier."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the concrete index variant."),
        sa.ForeignKeyConstraint(["administrator_organisation_id"], ["secm.organisation.organisation_id"]),
        sa.ForeignKeyConstraint(["base_currency_id"], ["secm.currency.currency_id"]),
        sa.ForeignKeyConstraint(["calculation_agent_organisation_id"], ["secm.organisation.organisation_id"]),
        sa.ForeignKeyConstraint(["index_family_id"], ["secm.index_family.index_family_id"]),
        sa.ForeignKeyConstraint(["index_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.ForeignKeyConstraint(["return_profile_id"], ["secm.return_profile.return_profile_id"]),
        sa.PrimaryKeyConstraint("index_node_id"),
        schema="secm",
    )
    op.create_table(
        "index_methodology_version",
        sa.Column("index_methodology_version_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated index methodology version."),
        sa.Column("index_node_id", sa.UUID(), nullable=False, comment="Concrete index variant governed by this methodology version."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, comment="Monotonically increasing methodology version sequence for the index variant."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date on which this methodology version applies."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date on which this methodology version applies."),
        sa.Column("weighting_method", sa.String(length=100), nullable=True, comment="Weighting method such as MARKET_CAP, EQUAL_WEIGHT, PRICE_WEIGHTED, or RULE_BASED."),
        sa.Column("rebalance_frequency", sa.String(length=100), nullable=True, comment="Scheduled rebalancing frequency or rule."),
        sa.Column("calculation_frequency", sa.String(length=100), nullable=True, comment="Frequency at which the index level is calculated or disseminated."),
        sa.Column("dividend_treatment", sa.String(length=100), nullable=True, comment="Methodology-specific dividend, distribution, or income treatment."),
        sa.Column("financing_reference_node_id", sa.UUID(), nullable=True, comment="Reference rate or curve used by an excess-return methodology when applicable."),
        sa.Column("launch_date", sa.Date(), nullable=True, comment="Provider launch date of the methodology or index variant."),
        sa.Column("is_backtested_history", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Whether the methodology version describes pre-launch hypothetical or back-tested history."),
        sa.Column("methodology_document_uri", sa.String(length=1000), nullable=True, comment="URI or stable locator for the methodology document when available."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Approval lifecycle status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Source payload evidencing this methodology version when available."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="User account approving this methodology version."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this methodology version was approved."),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"]),
        sa.ForeignKeyConstraint(["financing_reference_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.ForeignKeyConstraint(["index_node_id"], ["secm.index_terms.index_node_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"]),
        sa.PrimaryKeyConstraint("index_methodology_version_id"),
        sa.UniqueConstraint("index_node_id", "sequence_no", name="uq_index_methodology_version_sequence"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_index_methodology_version_valid_period"),
        schema="secm",
    )
    op.create_index("ix_index_terms_family", "index_terms", ["index_family_id"], schema="secm")
    op.create_index("ix_index_methodology_index_effective", "index_methodology_version", ["index_node_id", "effective_from", "effective_to"], schema="secm")
    op.add_column(
        "swap_leg",
        sa.Column("return_profile_id", sa.UUID(), nullable=True, comment="Generic performance-return profile contractually applied by the leg when its reference is performance-based."),
        schema="secm",
    )
    op.create_foreign_key(
        "fk_swap_leg_return_profile",
        "swap_leg",
        "return_profile",
        ["return_profile_id"],
        ["return_profile_id"],
        source_schema="secm",
        referent_schema="secm",
    )


def downgrade() -> None:
    op.drop_constraint("fk_swap_leg_return_profile", "swap_leg", schema="secm", type_="foreignkey")
    op.drop_column("swap_leg", "return_profile_id", schema="secm")
    op.drop_index("ix_index_methodology_index_effective", table_name="index_methodology_version", schema="secm")
    op.drop_index("ix_index_terms_family", table_name="index_terms", schema="secm")
    op.drop_table("index_methodology_version", schema="secm")
    op.drop_table("index_terms", schema="secm")
    op.drop_table("index_family", schema="secm")
    op.drop_table("return_profile", schema="secm")
