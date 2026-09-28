"""Add explicit fund/share-class and versioned bond contractual terms."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_05"
down_revision = "20260901_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create minimal terms needed for fund NAV selection and bond accrual."""

    op.create_table(
        "fund",
        sa.Column("fund_reference_node_id", sa.UUID(), sa.ForeignKey("secm.financial_reference_node.reference_node_id"), primary_key=True, comment="Canonical non-tradeable fund, umbrella, or sub-fund reference node; fund share classes remain separate economic instruments."),
        sa.Column("fund_kind", sa.String(length=40), nullable=False, comment="Fund structural kind such as UMBRELLA, SUB_FUND, STANDALONE, ETF_ISSUER, or PARTNERSHIP."),
        sa.Column("parent_fund_reference_node_id", sa.UUID(), sa.ForeignKey("secm.fund.fund_reference_node_id"), nullable=True, comment="Optional umbrella or parent fund reference node for a sub-fund; null for a standalone fund or top-level umbrella."),
        sa.Column("fund_manager_organisation_id", sa.UUID(), sa.ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation appointed as fund manager or AIFM/management company where applicable."),
        sa.Column("domicile_country_code", sa.String(length=3), nullable=True, comment="ISO 3166-1 alpha-3 domicile country code of the fund vehicle or sub-fund."),
        sa.Column("legal_form", sa.String(length=100), nullable=True, comment="Legal form such as OEIC, SICAV, ICAV, UNIT_TRUST, LIMITED_PARTNERSHIP, or CONTRACTUAL_FUND."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Lifecycle status such as DRAFT, ACTIVE, CLOSED, LIQUIDATING, or TERMINATED."),
        schema="secm",
    )
    op.create_table(
        "fund_share_class_terms",
        sa.Column("fund_share_class_terms_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one effective-dated version of fund share-class terms."),
        sa.Column("instrument_node_id", sa.UUID(), sa.ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument node representing the subscribable or tradeable fund share class."),
        sa.Column("fund_reference_node_id", sa.UUID(), sa.ForeignKey("secm.fund.fund_reference_node_id"), nullable=False, comment="Fund or sub-fund to which the share class belongs."),
        sa.Column("share_class_code", sa.String(length=100), nullable=False, comment="Manager or administrator share-class code, such as I_ACC_GBP or A_DIST_EUR."),
        sa.Column("share_currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which the share class NAV, dealing and nominal share value are denominated."),
        sa.Column("income_treatment", sa.String(length=30), nullable=False, comment="Income treatment such as ACCUMULATION, DISTRIBUTION, INCOME, or UNKNOWN."),
        sa.Column("dealing_frequency", sa.String(length=30), nullable=True, comment="Normal subscription and redemption dealing frequency such as DAILY, WEEKLY, MONTHLY, or CLOSED_ENDED."),
        sa.Column("nav_frequency", sa.String(length=30), nullable=True, comment="Official NAV calculation frequency such as DAILY, WEEKLY, MONTHLY, or AD_HOC."),
        sa.Column("nav_publication_lag_business_days", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="Expected business-day publication lag of the official NAV after its market date; a valuation policy still decides whether and how to use it."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date for which this version of share-class terms is effective."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date for which this version of share-class terms is effective."),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Whether this is the current operationally approved share-class terms version."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="Monotonically increasing version sequence for the same share-class instrument."),
        sa.UniqueConstraint("instrument_node_id", "sequence_no", name="uq_fund_share_class_terms_version"),
        schema="secm",
    )
    op.create_table(
        "bond_terms",
        sa.Column("bond_terms_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one effective-dated version of bond contractual terms."),
        sa.Column("instrument_node_id", sa.UUID(), sa.ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic bond instrument governed by these terms."),
        sa.Column("issue_currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id"), nullable=False, comment="Contractual denomination and principal currency of the bond."),
        sa.Column("par_amount", sa.Numeric(30, 12), nullable=True, comment="Contractual denomination or par amount represented by one bond unit when applicable."),
        sa.Column("coupon_type", sa.String(length=40), nullable=False, comment="Coupon style such as FIXED, FLOATING, ZERO, INFLATION_LINKED, STEP_UP, PIK, or OTHER."),
        sa.Column("coupon_rate", sa.Numeric(20, 12), nullable=True, comment="Contractual annual coupon rate in decimal form when fixed or the current quoted reference rate when relevant; null for non-rate coupon forms."),
        sa.Column("coupon_frequency_per_year", sa.Integer(), nullable=True, comment="Number of regular coupon payment periods per year; null for zero-coupon or irregular schedules."),
        sa.Column("day_count_convention", sa.String(length=40), nullable=True, comment="Accrual convention such as ACT_360, ACT_365F, ACT_ACT_ICMA, or THIRTY_360."),
        sa.Column("redemption_amount_per_par", sa.Numeric(30, 12), nullable=True, comment="Contractual final redemption amount per unit of par, normally 100 when quoted as percentage of par."),
        sa.Column("quotation_basis", sa.String(length=40), nullable=False, server_default=sa.text("'PCT_OF_PAR'"), comment="Price quotation basis such as PCT_OF_PAR, CURRENCY_PER_UNIT, or YIELD; distinct from listing quote factor."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date for which this version of bond terms is effective."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date for which this version of bond terms is effective."),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Whether this is the current operationally approved bond-terms version."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="Monotonically increasing version sequence for the same bond instrument."),
        sa.UniqueConstraint("instrument_node_id", "sequence_no", name="uq_bond_terms_version"),
        schema="secm",
    )


def downgrade() -> None:
    """Remove the focused terms tables in reverse dependency order."""

    op.drop_table("bond_terms", schema="secm")
    op.drop_table("fund_share_class_terms", schema="secm")
    op.drop_table("fund", schema="secm")
