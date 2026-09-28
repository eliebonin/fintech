"""Harden structured-product terms, composition, and payout metadata."""

from alembic import op
import sqlalchemy as sa


revision = "20260909_31"
down_revision = "20260908_30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 30 introduced a surrogate terms id but left the legacy
    # instrument primary key and the old condition-group foreign key in place.
    # Repair that shape before adding dependants so every contractual graph is
    # anchored to a terms version rather than to the stable instrument id.
    # Both the new condition-group FK and the unnamed FK emitted for the
    # coupon programme depend on the terms unique index.  They must be
    # recreated after the terms primary key is moved to structured_product_terms_id.
    op.drop_constraint("fk_sp_condition_group_terms_version", "structured_product_condition_group", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_sp_condition_group_terms", "structured_product_condition_group", schema="secm", type_="foreignkey")
    op.execute(
        "ALTER TABLE secm.structured_product_coupon_programme "
        "DROP CONSTRAINT IF EXISTS structured_product_coupon_prog_structured_product_terms_id_fkey"
    )
    op.execute(
        "ALTER TABLE secm.structured_product_coupon_programme "
        "DROP CONSTRAINT IF EXISTS structured_product_coupon_programme_structured_product_terms_id_fkey"
    )
    op.drop_constraint("uq_structured_product_terms_id", "structured_product_terms", schema="secm", type_="unique")
    op.drop_constraint("structured_product_terms_pkey", "structured_product_terms", schema="secm", type_="primary")
    op.create_primary_key("structured_product_terms_pkey", "structured_product_terms", ["structured_product_terms_id"], schema="secm")
    op.create_foreign_key(
        "fk_structured_product_terms_supersedes",
        "structured_product_terms",
        "structured_product_terms",
        ["supersedes_structured_product_terms_id"],
        ["structured_product_terms_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.add_column(
        "structured_product_terms",
        sa.Column(
            "default_underlying_scope",
            sa.String(length=30),
            server_default=sa.text("'SINGLE'"),
            nullable=True,
            comment="Default underlying aggregation for product conditions: SINGLE, BEST_OF, WORST_OF, BASKET, or EACH_UNDERLYING.",
        ),
        schema="secm",
    )
    op.add_column(
        "structured_product_terms",
        sa.Column(
            "source_payload_id",
            sa.UUID(),
            nullable=True,
            comment="Retained source payload evidencing this complete terms version when available.",
        ),
        schema="secm",
    )
    op.execute("UPDATE secm.structured_product_terms SET default_underlying_scope = COALESCE(default_underlying_scope, 'SINGLE')")
    op.alter_column("structured_product_terms", "default_underlying_scope", nullable=False, schema="secm")
    op.create_foreign_key(
        "fk_structured_product_terms_source_payload",
        "structured_product_terms",
        "source_payload",
        ["source_payload_id"],
        ["source_payload_id"],
        source_schema="secm",
        referent_schema="ing",
    )
    op.create_foreign_key(
        "fk_sp_condition_group_terms_version",
        "structured_product_condition_group",
        "structured_product_terms",
        ["structured_product_terms_id"],
        ["structured_product_terms_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "fk_sp_coupon_programme_terms",
        "structured_product_coupon_programme",
        "structured_product_terms",
        ["structured_product_terms_id"],
        ["structured_product_terms_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.alter_column("structured_product_terms", "structured_product_terms_id", comment="Immutable UUIDv7 identifier for one version of the contractual structured-product terms graph.", schema="secm")
    op.alter_column("structured_product_terms", "instrument_node_id", comment="Stable parent structured-product economic instrument whose terms are versioned.", schema="secm")
    op.alter_column("structured_product_terms", "version_no", comment="Positive monotonic version number for the parent structured-product terms.", schema="secm")
    op.alter_column("structured_product_terms", "effective_from", comment="First date on which this structured-product terms version is contractually effective.", schema="secm")
    op.alter_column("structured_product_terms", "effective_to", comment="Last date on which this structured-product terms version is contractually effective.", schema="secm")
    op.alter_column("structured_product_terms", "is_current", comment="Whether this is the current operational terms version for the parent instrument.", schema="secm")
    op.alter_column("structured_product_terms", "supersedes_structured_product_terms_id", comment="Prior terms version replaced by this amendment, when the contract graph was superseded.", schema="secm")
    op.create_check_constraint("ck_structured_product_terms_version_no", "structured_product_terms", "version_no > 0", schema="secm")
    op.create_check_constraint("ck_structured_product_terms_valid_period", "structured_product_terms", "effective_to IS NULL OR effective_to >= effective_from", schema="secm")
    op.create_check_constraint("ck_structured_product_terms_underlying_scope", "structured_product_terms", "default_underlying_scope IN ('SINGLE', 'BEST_OF', 'WORST_OF', 'BASKET', 'EACH_UNDERLYING')", schema="secm")

    op.drop_constraint("uq_sp_condition_group_code", "structured_product_condition_group", schema="secm", type_="unique")
    op.drop_constraint("uq_sp_condition_group_event_sequence", "structured_product_condition_group", schema="secm", type_="unique")
    op.add_column(
        "structured_product_condition_group",
        sa.Column(
            "underlying_scope",
            sa.String(length=30),
            server_default=sa.text("'SINGLE'"),
            nullable=True,
            comment="How the group evaluates its underlying members: SINGLE, BEST_OF, WORST_OF, BASKET, or EACH_UNDERLYING.",
        ),
        schema="secm",
    )
    op.execute("UPDATE secm.structured_product_condition_group SET underlying_scope = COALESCE(underlying_scope, 'SINGLE')")
    op.alter_column("structured_product_condition_group", "underlying_scope", nullable=False, schema="secm")
    op.drop_column("structured_product_condition_group", "structured_product_instrument_node_id", schema="secm")
    op.create_unique_constraint("uq_sp_condition_group_code", "structured_product_condition_group", ["structured_product_terms_id", "group_code"], schema="secm")
    op.create_unique_constraint("uq_sp_condition_group_event_sequence", "structured_product_condition_group", ["structured_product_terms_id", "schedule_event_id", "evaluation_sequence"], schema="secm")
    op.create_check_constraint("ck_sp_condition_group_underlying_scope", "structured_product_condition_group", "underlying_scope IN ('SINGLE', 'BEST_OF', 'WORST_OF', 'BASKET', 'EACH_UNDERLYING')", schema="secm")
    op.alter_column("structured_product_condition_group", "structured_product_terms_id", comment="Structured-product terms version owning this Boolean condition group.", schema="secm")

    # The composition table is shared by contractual payoff graphs and dated
    # reference portfolios.  The value-kind discriminator prevents one
    # overloaded rate column from silently changing meaning by product type.
    op.alter_column(
        "instrument_composition",
        "composition_rate",
        new_column_name="composition_value",
        comment="Signed value applied to the component; interpretation is governed by composition_value_kind.",
        schema="secm",
    )
    op.add_column(
        "instrument_composition",
        sa.Column(
            "composition_value_kind",
            sa.String(length=30),
            server_default=sa.text("'SIGNED_MULTIPLIER'"),
            nullable=True,
            comment="Interpretation of composition_value: SIGNED_MULTIPLIER, PERCENT_WEIGHT, QUANTITY, or NOTIONAL_AMOUNT.",
        ),
        schema="secm",
    )
    op.add_column(
        "instrument_composition",
        sa.Column(
            "component_sequence",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=True,
            comment="Deterministic component occurrence order within the parent, terms version, and composition date.",
        ),
        schema="secm",
    )
    op.add_column(
        "instrument_composition",
        sa.Column(
            "structured_product_terms_id",
            sa.UUID(),
            nullable=True,
            comment="Structured-product terms version governing this row; null for baskets, portfolios, and other non-contractual compositions.",
        ),
        schema="secm",
    )
    op.add_column(
        "instrument_composition",
        sa.Column(
            "source_payload_id",
            sa.UUID(),
            nullable=True,
            comment="Retained source payload evidencing this composition entry when available.",
        ),
        schema="secm",
    )
    op.execute(
        sa.text(
            """
            WITH ordered AS (
                SELECT instrument_composition_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY parent_instrument_node_id, composition_date
                           ORDER BY instrument_composition_id
                       )::integer AS component_sequence
                FROM secm.instrument_composition
            )
            UPDATE secm.instrument_composition AS composition
            SET component_sequence = ordered.component_sequence
            FROM ordered
            WHERE ordered.instrument_composition_id = composition.instrument_composition_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE secm.instrument_composition AS composition
            SET structured_product_terms_id = terms.structured_product_terms_id
            FROM secm.structured_product_terms AS terms
            WHERE composition.parent_instrument_node_id = terms.instrument_node_id
              AND terms.is_current = true
              AND composition.structured_product_terms_id IS NULL
            """
        )
    )
    op.alter_column("instrument_composition", "composition_value_kind", nullable=False, schema="secm")
    op.alter_column("instrument_composition", "component_sequence", nullable=False, schema="secm")
    op.create_foreign_key("fk_instrument_composition_terms", "instrument_composition", "structured_product_terms", ["structured_product_terms_id"], ["structured_product_terms_id"], source_schema="secm", referent_schema="secm")
    op.create_foreign_key("fk_instrument_composition_source_payload", "instrument_composition", "source_payload", ["source_payload_id"], ["source_payload_id"], source_schema="secm", referent_schema="ing")
    op.create_unique_constraint("uq_instrument_composition_component_sequence", "instrument_composition", ["parent_instrument_node_id", "structured_product_terms_id", "composition_date", "component_sequence"], schema="secm")
    op.create_check_constraint("ck_instrument_composition_value_kind", "instrument_composition", "composition_value_kind IN ('SIGNED_MULTIPLIER', 'PERCENT_WEIGHT', 'QUANTITY', 'NOTIONAL_AMOUNT')", schema="secm")
    op.create_check_constraint("ck_instrument_composition_component_sequence", "instrument_composition", "component_sequence > 0", schema="secm")
    op.create_check_constraint("ck_instrument_composition_valid_period", "instrument_composition", "effective_to IS NULL OR effective_to >= composition_date", schema="secm")

    # A component-specific payoff record carries the facts that do not belong
    # in the child option terms (for example a digital coupon amount or a
    # principal-redemption treatment).
    op.create_table(
        "structured_product_component_terms",
        sa.Column("structured_product_component_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for payoff terms attached to one structured-product composition occurrence."),
        sa.Column("instrument_composition_id", sa.UUID(), nullable=False, comment="Exact parent-component composition occurrence to which these payoff terms apply."),
        sa.Column("component_kind", sa.String(length=40), nullable=False, comment="Component role such as DIGITAL, VANILLA_OPTION, BARRIER, COUPON, PRINCIPAL_REDEMPTION, CAP, FLOOR, or CASHFLOW."),
        sa.Column("payoff_style", sa.String(length=40), nullable=False, comment="Payoff representation: FIXED_AMOUNT, RATE_OF_NOTIONAL, OPTION_PAYOFF, UNDERLYING_RETURN, or PRINCIPAL_REDEMPTION."),
        sa.Column("payout_amount", sa.Numeric(precision=30, scale=12), nullable=True, comment="Absolute payout amount when the component pays a fixed cash amount."),
        sa.Column("payout_rate", sa.Numeric(precision=30, scale=12), nullable=True, comment="Payout rate in percentage points when the component pays a percentage; 5 means 5%."),
        sa.Column("payout_currency_id", sa.UUID(), nullable=True, comment="Currency of the component payout when it is a monetary amount."),
        sa.Column("payout_basis", sa.String(length=40), nullable=True, comment="Basis for payout_amount or payout_rate: PER_UNIT, PCT_OF_NOTIONAL, PCT_OF_PAR, or ABSOLUTE."),
        sa.Column("payment_timing", sa.String(length=30), nullable=True, comment="When the component pays: ON_OBSERVATION, ON_TRIGGER, ON_AUTOCALL, or ON_MATURITY."),
        sa.Column("schedule_id", sa.UUID(), nullable=True, comment="Optional schedule governing this component's payment or observation timing."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing these component payoff terms when available."),
        sa.ForeignKeyConstraint(["instrument_composition_id"], ["secm.instrument_composition.instrument_composition_id"], name="fk_sp_component_terms_composition"),
        sa.ForeignKeyConstraint(["payout_currency_id"], ["secm.currency.currency_id"], name="fk_sp_component_terms_currency"),
        sa.ForeignKeyConstraint(["schedule_id"], ["secm.schedule.schedule_id"], name="fk_sp_component_terms_schedule"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_sp_component_terms_source_payload"),
        sa.PrimaryKeyConstraint("structured_product_component_terms_id"),
        sa.UniqueConstraint("instrument_composition_id", name="uq_sp_component_terms_composition"),
        sa.CheckConstraint("component_kind IN ('DIGITAL', 'VANILLA_OPTION', 'BARRIER', 'COUPON', 'PRINCIPAL_REDEMPTION', 'CAP', 'FLOOR', 'CASHFLOW', 'OTHER')", name="ck_sp_component_terms_kind"),
        sa.CheckConstraint("payoff_style IN ('FIXED_AMOUNT', 'RATE_OF_NOTIONAL', 'OPTION_PAYOFF', 'UNDERLYING_RETURN', 'PRINCIPAL_REDEMPTION')", name="ck_sp_component_terms_payoff_style"),
        sa.CheckConstraint("payout_amount IS NULL OR payout_amount >= 0", name="ck_sp_component_terms_payout_amount"),
        sa.CheckConstraint("payout_rate IS NULL OR payout_rate >= 0", name="ck_sp_component_terms_payout_rate"),
        sa.CheckConstraint("(payout_amount IS NULL OR payout_rate IS NULL) OR (payout_amount >= 0 AND payout_rate >= 0)", name="ck_sp_component_terms_payout_values"),
        sa.CheckConstraint("payout_basis IS NULL OR payout_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'ABSOLUTE')", name="ck_sp_component_terms_payout_basis"),
        sa.CheckConstraint("payment_timing IS NULL OR payment_timing IN ('ON_OBSERVATION', 'ON_TRIGGER', 'ON_AUTOCALL', 'ON_MATURITY')", name="ck_sp_component_terms_payment_timing"),
        schema="secm",
    )

    op.add_column("structured_product_coupon_programme", sa.Column("schedule_id", sa.UUID(), nullable=True, comment="Default observation/payment schedule for the programme; periods may override it through their events."), schema="secm")
    op.add_column("structured_product_coupon_programme", sa.Column("eligibility_condition_group_id", sa.UUID(), nullable=True, comment="Optional default condition group governing coupon eligibility when a period does not override it."), schema="secm")
    op.add_column("structured_product_coupon_programme", sa.Column("final_payment_treatment", sa.String(length=40), nullable=True, comment="Treatment of accrued coupon at final redemption, such as PAY_SEPARATELY, INCLUDE_IN_REDEMPTION, or FORFEIT."), schema="secm")
    op.add_column("structured_product_coupon_programme", sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing the coupon programme when available."), schema="secm")
    op.create_foreign_key("fk_sp_coupon_programme_schedule", "structured_product_coupon_programme", "schedule", ["schedule_id"], ["schedule_id"], source_schema="secm", referent_schema="secm")
    op.create_foreign_key("fk_sp_coupon_programme_eligibility_group", "structured_product_coupon_programme", "structured_product_condition_group", ["eligibility_condition_group_id"], ["condition_group_id"], source_schema="secm", referent_schema="secm")
    op.create_foreign_key("fk_sp_coupon_programme_source_payload", "structured_product_coupon_programme", "source_payload", ["source_payload_id"], ["source_payload_id"], source_schema="secm", referent_schema="ing")
    op.alter_column("structured_product_coupon_programme", "coupon_programme_id", comment="Immutable UUIDv7 identifier for one coupon programme within a terms version.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "structured_product_terms_id", comment="Structured-product terms version owning this coupon programme.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "programme_code", comment="Stable terms-local code identifying a coupon programme such as MAIN_COUPON or MEMORY_COUPON.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "payment_mode", comment="Coupon payment timing mode: PERIODIC, ON_AUTOCALL, or ON_MATURITY.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "memory_mode", comment="Coupon memory behaviour: NONE, CONDITIONAL_CATCH_UP, or ACCUMULATE_TO_REDEMPTION.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "coupon_currency_id", comment="Currency in which coupon amounts are paid; null when inherited from the parent terms.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "default_coupon_rate", comment="Default coupon rate per period, expressed in percentage points so 5 means 5%.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "default_coupon_amount", comment="Default absolute coupon amount per applicable unit or notional, in coupon_currency_id.", schema="secm")
    op.alter_column("structured_product_coupon_programme", "status", comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED.", schema="secm")
    op.create_check_constraint("ck_sp_coupon_programme_payment_mode", "structured_product_coupon_programme", "payment_mode IN ('PERIODIC', 'ON_AUTOCALL', 'ON_MATURITY')", schema="secm")
    op.create_check_constraint("ck_sp_coupon_programme_memory_mode", "structured_product_coupon_programme", "memory_mode IN ('NONE', 'CONDITIONAL_CATCH_UP', 'ACCUMULATE_TO_REDEMPTION')", schema="secm")
    op.create_check_constraint("ck_sp_coupon_programme_rate", "structured_product_coupon_programme", "default_coupon_rate IS NULL OR default_coupon_rate >= 0", schema="secm")
    op.create_check_constraint("ck_sp_coupon_programme_amount", "structured_product_coupon_programme", "default_coupon_amount IS NULL OR default_coupon_amount >= 0", schema="secm")

    op.add_column("structured_product_coupon_period", sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing this coupon period when available."), schema="secm")
    op.alter_column("structured_product_coupon_period", "eligibility_condition_group_id", nullable=True, comment="Optional condition group that must be satisfied for this period's coupon to be payable.", schema="secm")
    op.alter_column("structured_product_coupon_period", "coupon_period_id", comment="Immutable UUIDv7 identifier for one dated coupon period.", schema="secm")
    op.alter_column("structured_product_coupon_period", "coupon_programme_id", comment="Coupon programme owning this period.", schema="secm")
    op.alter_column("structured_product_coupon_period", "period_sequence", comment="Positive chronological sequence of the period within its coupon programme.", schema="secm")
    op.alter_column("structured_product_coupon_period", "observation_event_id", comment="Scheduled event at which this period's coupon eligibility is observed.", schema="secm")
    op.alter_column("structured_product_coupon_period", "payment_date", comment="Contractual coupon payment date when distinct from the observation event payment date.", schema="secm")
    op.alter_column("structured_product_coupon_period", "coupon_rate", comment="Period-specific coupon rate in percentage points so 5 means 5%; overrides the programme default when supplied.", schema="secm")
    op.alter_column("structured_product_coupon_period", "coupon_amount", comment="Period-specific absolute coupon amount; overrides the programme default when supplied.", schema="secm")
    op.alter_column("structured_product_coupon_period", "memory_eligible", comment="Whether a missed eligible coupon can participate in the programme's memory behaviour.", schema="secm")
    op.alter_column("structured_product_coupon_period", "status", comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED.", schema="secm")
    op.create_foreign_key("fk_sp_coupon_period_source_payload", "structured_product_coupon_period", "source_payload", ["source_payload_id"], ["source_payload_id"], source_schema="secm", referent_schema="ing")
    op.create_check_constraint("ck_sp_coupon_period_sequence", "structured_product_coupon_period", "period_sequence > 0", schema="secm")
    op.create_check_constraint("ck_sp_coupon_period_rate", "structured_product_coupon_period", "coupon_rate IS NULL OR coupon_rate >= 0", schema="secm")
    op.create_check_constraint("ck_sp_coupon_period_amount", "structured_product_coupon_period", "coupon_amount IS NULL OR coupon_amount >= 0", schema="secm")

    op.add_column("condition_group_action", sa.Column("target_composition_id", sa.UUID(), nullable=True, comment="Exact component composition occurrence affected by a COMPONENT action; null for PARENT actions."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_amount", sa.Numeric(precision=30, scale=12), nullable=True, comment="Absolute amount paid by this action when the action itself carries a fixed payout."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_rate", sa.Numeric(precision=30, scale=12), nullable=True, comment="Percentage-point rate paid by this action when the payout is rate-based; 5 means 5%."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_currency_id", sa.UUID(), nullable=True, comment="Currency of the action payout when it is monetary."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_basis", sa.String(length=40), nullable=True, comment="Basis for a payment amount or rate: PER_UNIT, PCT_OF_NOTIONAL, PCT_OF_PAR, or ABSOLUTE."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_timing", sa.String(length=30), nullable=True, comment="Payment timing for the action: ON_OBSERVATION, ON_TRIGGER, ON_AUTOCALL, or ON_MATURITY."), schema="secm")
    op.add_column("condition_group_action", sa.Column("payment_schedule_id", sa.UUID(), nullable=True, comment="Optional schedule governing when an action payout is settled."), schema="secm")
    op.create_foreign_key("fk_condition_group_action_composition", "condition_group_action", "instrument_composition", ["target_composition_id"], ["instrument_composition_id"], source_schema="secm", referent_schema="secm")
    op.create_foreign_key("fk_condition_group_action_currency", "condition_group_action", "currency", ["payment_currency_id"], ["currency_id"], source_schema="secm", referent_schema="secm")
    op.create_foreign_key("fk_condition_group_action_schedule", "condition_group_action", "schedule", ["payment_schedule_id"], ["schedule_id"], source_schema="secm", referent_schema="secm")
    op.execute(
        sa.text(
            """
            UPDATE secm.condition_group_action AS action
            SET target_composition_id = matched.instrument_composition_id
            FROM (
                SELECT action_row.condition_group_action_id,
                       composition.instrument_composition_id
                FROM secm.condition_group_action AS action_row
                JOIN secm.structured_product_condition_group AS condition_group
                  ON condition_group.condition_group_id = action_row.condition_group_id
                JOIN secm.structured_product_terms AS terms
                  ON terms.structured_product_terms_id = condition_group.structured_product_terms_id
                JOIN secm.instrument_composition AS composition
                  ON composition.parent_instrument_node_id = terms.instrument_node_id
                 AND composition.structured_product_terms_id = terms.structured_product_terms_id
                 AND composition.component_reference_node_id = action_row.target_reference_node_id
                 AND composition.composition_role = 'PAYOFF_COMPONENT'
                WHERE action_row.target_scope = 'COMPONENT'
                  AND action_row.target_composition_id IS NULL
            ) AS matched
            WHERE action.condition_group_action_id = matched.condition_group_action_id
            """
        )
    )
    op.create_check_constraint("ck_condition_group_action_target_composition", "condition_group_action", "(target_scope = 'COMPONENT' AND target_composition_id IS NOT NULL) OR (target_scope = 'PARENT' AND target_composition_id IS NULL)", schema="secm")
    op.create_check_constraint("ck_condition_group_action_payment_amount", "condition_group_action", "payment_amount IS NULL OR payment_amount >= 0", schema="secm")
    op.create_check_constraint("ck_condition_group_action_payment_rate", "condition_group_action", "payment_rate IS NULL OR payment_rate >= 0", schema="secm")
    op.create_check_constraint("ck_condition_group_action_payment_values", "condition_group_action", "(payment_amount IS NULL OR payment_rate IS NULL) OR (payment_amount >= 0 AND payment_rate >= 0)", schema="secm")
    op.create_check_constraint("ck_condition_group_action_payment_basis", "condition_group_action", "payment_basis IS NULL OR payment_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'ABSOLUTE')", schema="secm")
    op.create_check_constraint("ck_condition_group_action_payment_timing", "condition_group_action", "payment_timing IS NULL OR payment_timing IN ('ON_OBSERVATION', 'ON_TRIGGER', 'ON_AUTOCALL', 'ON_MATURITY')", schema="secm")


def downgrade() -> None:
    # These foreign keys point at the terms primary-key index and therefore
    # must be removed before the terms identity is moved back to instrument_node_id.
    op.drop_constraint("fk_sp_condition_group_terms_version", "structured_product_condition_group", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_sp_coupon_programme_terms", "structured_product_coupon_programme", schema="secm", type_="foreignkey")
    op.drop_constraint("ck_condition_group_action_payment_timing", "condition_group_action", schema="secm", type_="check")
    op.drop_constraint("ck_condition_group_action_payment_basis", "condition_group_action", schema="secm", type_="check")
    op.drop_constraint("ck_condition_group_action_payment_values", "condition_group_action", schema="secm", type_="check")
    op.drop_constraint("ck_condition_group_action_payment_rate", "condition_group_action", schema="secm", type_="check")
    op.drop_constraint("ck_condition_group_action_payment_amount", "condition_group_action", schema="secm", type_="check")
    op.drop_constraint("ck_condition_group_action_target_composition", "condition_group_action", schema="secm", type_="check")
    for name in ("fk_condition_group_action_schedule", "fk_condition_group_action_currency", "fk_condition_group_action_composition"):
        op.drop_constraint(name, "condition_group_action", schema="secm", type_="foreignkey")
    for column in ("payment_schedule_id", "payment_timing", "payment_basis", "payment_currency_id", "payment_rate", "payment_amount", "target_composition_id"):
        op.drop_column("condition_group_action", column, schema="secm")

    for name in ("ck_sp_coupon_period_amount", "ck_sp_coupon_period_rate", "ck_sp_coupon_period_sequence"):
        op.drop_constraint(name, "structured_product_coupon_period", schema="secm", type_="check")
    op.drop_constraint("fk_sp_coupon_period_source_payload", "structured_product_coupon_period", schema="secm", type_="foreignkey")
    op.drop_column("structured_product_coupon_period", "source_payload_id", schema="secm")
    for name in ("ck_sp_coupon_programme_amount", "ck_sp_coupon_programme_rate", "ck_sp_coupon_programme_memory_mode", "ck_sp_coupon_programme_payment_mode"):
        op.drop_constraint(name, "structured_product_coupon_programme", schema="secm", type_="check")
    for name in ("fk_sp_coupon_programme_source_payload", "fk_sp_coupon_programme_eligibility_group", "fk_sp_coupon_programme_schedule"):
        op.drop_constraint(name, "structured_product_coupon_programme", schema="secm", type_="foreignkey")
    for column in ("source_payload_id", "final_payment_treatment", "eligibility_condition_group_id", "schedule_id"):
        op.drop_column("structured_product_coupon_programme", column, schema="secm")

    op.drop_table("structured_product_component_terms", schema="secm")
    for name in ("ck_instrument_composition_valid_period", "ck_instrument_composition_component_sequence", "ck_instrument_composition_value_kind"):
        op.drop_constraint(name, "instrument_composition", schema="secm", type_="check")
    op.drop_constraint("uq_instrument_composition_component_sequence", "instrument_composition", schema="secm", type_="unique")
    op.drop_constraint("fk_instrument_composition_source_payload", "instrument_composition", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_instrument_composition_terms", "instrument_composition", schema="secm", type_="foreignkey")
    for column in ("source_payload_id", "structured_product_terms_id", "component_sequence", "composition_value_kind"):
        op.drop_column("instrument_composition", column, schema="secm")
    op.alter_column("instrument_composition", "composition_value", new_column_name="composition_rate", comment="Signed quantity, weight, or leverage of the component in the parent composition.", schema="secm")

    op.drop_constraint("ck_sp_condition_group_underlying_scope", "structured_product_condition_group", schema="secm", type_="check")
    op.drop_constraint("uq_sp_condition_group_event_sequence", "structured_product_condition_group", schema="secm", type_="unique")
    op.drop_constraint("uq_sp_condition_group_code", "structured_product_condition_group", schema="secm", type_="unique")
    op.add_column("structured_product_condition_group", sa.Column("structured_product_instrument_node_id", sa.UUID(), nullable=True, comment="Parent structured-product instrument whose contractual terms contain this condition group."), schema="secm")
    op.execute(
        "UPDATE secm.structured_product_condition_group AS condition_group "
        "SET structured_product_instrument_node_id = terms.instrument_node_id "
        "FROM secm.structured_product_terms AS terms "
        "WHERE terms.structured_product_terms_id = condition_group.structured_product_terms_id"
    )
    op.alter_column("structured_product_condition_group", "structured_product_instrument_node_id", nullable=False, schema="secm")
    op.drop_column("structured_product_condition_group", "underlying_scope", schema="secm")
    op.drop_constraint("fk_structured_product_terms_source_payload", "structured_product_terms", schema="secm", type_="foreignkey")
    op.drop_constraint("ck_structured_product_terms_underlying_scope", "structured_product_terms", schema="secm", type_="check")
    op.drop_constraint("ck_structured_product_terms_valid_period", "structured_product_terms", schema="secm", type_="check")
    op.drop_constraint("ck_structured_product_terms_version_no", "structured_product_terms", schema="secm", type_="check")
    op.drop_column("structured_product_terms", "source_payload_id", schema="secm")
    op.drop_column("structured_product_terms", "default_underlying_scope", schema="secm")
    op.drop_constraint("fk_structured_product_terms_supersedes", "structured_product_terms", schema="secm", type_="foreignkey")
    op.drop_constraint("structured_product_terms_pkey", "structured_product_terms", schema="secm", type_="primary")
    op.create_primary_key("structured_product_terms_pkey", "structured_product_terms", ["instrument_node_id"], schema="secm")
    op.create_unique_constraint("uq_structured_product_terms_id", "structured_product_terms", ["structured_product_terms_id"], schema="secm")
    op.create_foreign_key("fk_sp_condition_group_terms", "structured_product_condition_group", "structured_product_terms", ["structured_product_instrument_node_id"], ["instrument_node_id"], source_schema="secm", referent_schema="secm")
