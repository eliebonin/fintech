"""Model versioned option terms, contractual strike resets, and fixings."""

from alembic import op
import sqlalchemy as sa


revision = "20260907_24"
down_revision = "20260906_23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing installations have one option terms row per instrument.  Add a
    # surrogate version identity first, then replace the old instrument PK so
    # future legal amendments can be retained without changing instrument UUID.
    op.add_column(
        "option_terms",
        sa.Column(
            "option_terms_id",
            sa.UUID(),
            server_default=sa.text("uuidv7()"),
            nullable=True,
            comment="Immutable UUIDv7 identifier for one version of an economic option's static contract terms.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "version_no",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=True,
            comment="Monotonically increasing version number for corrected or amended static option terms.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "effective_from",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=True,
            comment="First business date on which this static option-terms version is contractually effective.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "effective_to",
            sa.Date(),
            nullable=True,
            comment="Last business date on which this static option-terms version is contractually effective.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=True,
            comment="Operational pointer indicating the currently approved option-terms version for this instrument; as-of queries still use dates and status.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'ACTIVE'"),
            nullable=True,
            comment="Lifecycle state of this option-terms version such as DRAFT, ACTIVE, SUPERSEDED, or RETIRED.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "supersedes_option_terms_id",
            sa.UUID(),
            nullable=True,
            comment="Prior option-terms version superseded by this version when a correction or legal amendment is recorded.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "strike_mode",
            sa.String(length=30),
            server_default=sa.text("'FIXED'"),
            nullable=True,
            comment="How the contractual strike is supplied: FIXED, FORWARD_START, or RESET.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "strike_reset_schedule_id",
            sa.UUID(),
            nullable=True,
            comment="Schedule containing contractual strike-determination events for FORWARD_START or RESET options.",
        ),
        schema="secm",
    )

    op.execute(
        sa.text(
            """
            UPDATE secm.option_terms AS option_row
            SET
                option_terms_id = COALESCE(option_row.option_terms_id, uuidv7()),
                version_no = COALESCE(option_row.version_no, 1),
                effective_from = COALESCE(option_row.effective_from, instrument_row.effective_from, CURRENT_DATE),
                is_current = COALESCE(option_row.is_current, true),
                status = COALESCE(option_row.status, 'ACTIVE'),
                strike_mode = COALESCE(option_row.strike_mode, 'FIXED')
            FROM secm.instrument AS instrument_row
            WHERE instrument_row.instrument_node_id = option_row.instrument_node_id
            """
        )
    )
    op.alter_column("option_terms", "option_terms_id", nullable=False, schema="secm")
    op.alter_column("option_terms", "version_no", nullable=False, schema="secm")
    op.alter_column("option_terms", "effective_from", nullable=False, schema="secm")
    op.alter_column("option_terms", "is_current", nullable=False, schema="secm")
    op.alter_column("option_terms", "status", nullable=False, schema="secm")

    op.drop_constraint("option_terms_pkey", "option_terms", schema="secm", type_="primary")
    op.create_primary_key("option_terms_pkey", "option_terms", ["option_terms_id"], schema="secm")
    op.create_unique_constraint(
        "uq_option_terms_version",
        "option_terms",
        ["instrument_node_id", "version_no"],
        schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_supersedes",
        "option_terms",
        "option_terms",
        ["supersedes_option_terms_id"],
        ["option_terms_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_strike_reset_schedule",
        "option_terms",
        "schedule",
        ["strike_reset_schedule_id"],
        ["schedule_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_version_positive",
        "option_terms",
        "version_no > 0",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_valid_period",
        "option_terms",
        "effective_to IS NULL OR effective_to >= effective_from",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_strike_mode",
        "option_terms",
        "strike_mode IN ('FIXED', 'FORWARD_START', 'RESET')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_dynamic_schedule",
        "option_terms",
        "(strike_mode = 'FIXED' AND strike_value IS NOT NULL) OR (strike_mode <> 'FIXED' AND strike_reset_schedule_id IS NOT NULL)",
        schema="secm",
    )

    op.create_table(
        "option_strike_reset_rule",
        sa.Column("option_strike_reset_rule_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one scheduled strike-determination rule."),
        sa.Column("option_terms_id", sa.UUID(), nullable=False, comment="Option-terms version whose contractual reset process contains this rule."),
        sa.Column("schedule_event_id", sa.UUID(), nullable=False, comment="Scheduled event at which the rule determines or resets the option strike."),
        sa.Column("determination_method", sa.String(length=30), nullable=False, comment="Strike determination method: FIXED, SPOT_AT_RESET, FORWARD_AT_RESET, PREVIOUS_FIXING, or FORMULA."),
        sa.Column("reference_node_id", sa.UUID(), nullable=True, comment="Underlying or reference node used by the determination method when the reset is not a standalone fixed value."),
        sa.Column("market_data_series_id", sa.UUID(), nullable=True, comment="Market-data series used to resolve a market-derived strike when applicable."),
        sa.Column("strike_basis", sa.String(length=30), server_default=sa.text("'ABSOLUTE'"), nullable=False, comment="Meaning of the fixed or resolved strike value: ABSOLUTE, INDEX_POINTS, FX_RATE, or PERCENT_OF_SPOT."),
        sa.Column("fixed_strike_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Pre-specified strike for a FIXED reset rule; null when the value is determined from a fixing or formula."),
        sa.Column("strike_currency_id", sa.UUID(), nullable=True, comment="Currency of a monetary fixed or resolved strike when required by the strike basis."),
        sa.Column("floor_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Optional minimum strike allowed after this reset rule is applied."),
        sa.Column("cap_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Optional maximum strike allowed after this reset rule is applied."),
        sa.ForeignKeyConstraint(["option_terms_id"], ["secm.option_terms.option_terms_id"], name="fk_option_strike_reset_rule_terms"),
        sa.ForeignKeyConstraint(["schedule_event_id"], ["secm.schedule_event.schedule_event_id"], name="fk_option_strike_reset_rule_event"),
        sa.ForeignKeyConstraint(["reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_option_strike_reset_rule_reference"),
        sa.ForeignKeyConstraint(["market_data_series_id"], ["md.market_data_series.market_data_series_id"], name="fk_option_strike_reset_rule_series"),
        sa.ForeignKeyConstraint(["strike_currency_id"], ["secm.currency.currency_id"], name="fk_option_strike_reset_rule_currency"),
        sa.PrimaryKeyConstraint("option_strike_reset_rule_id"),
        sa.UniqueConstraint("option_terms_id", "schedule_event_id", name="uq_option_strike_reset_rule_event"),
        sa.CheckConstraint("determination_method IN ('FIXED', 'SPOT_AT_RESET', 'FORWARD_AT_RESET', 'PREVIOUS_FIXING', 'FORMULA')", name="ck_option_strike_reset_method"),
        sa.CheckConstraint("strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT')", name="ck_option_strike_reset_basis"),
        sa.CheckConstraint("determination_method <> 'FIXED' OR fixed_strike_value IS NOT NULL", name="ck_option_strike_reset_fixed_value"),
        sa.CheckConstraint("floor_value IS NULL OR cap_value IS NULL OR cap_value >= floor_value", name="ck_option_strike_reset_bounds"),
        schema="secm",
    )
    op.create_table(
        "option_strike_fixing",
        sa.Column("option_strike_fixing_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one resolved strike fixing."),
        sa.Column("option_strike_reset_rule_id", sa.UUID(), nullable=False, comment="Reset rule whose scheduled strike value was resolved."),
        sa.Column("fixing_date", sa.Date(), nullable=False, comment="Business date on which the contractual strike was determined."),
        sa.Column("fixing_observed_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the source observation used for the fixing was observed."),
        sa.Column("resolved_strike_value", sa.Numeric(precision=30, scale=12), nullable=False, comment="Strike value resolved for the scheduled event, expressed using the reset rule's strike basis."),
        sa.Column("market_data_observation_id", sa.UUID(), nullable=True, comment="Source market-data observation used to resolve this strike when applicable."),
        sa.Column("market_data_resolution_snapshot_id", sa.UUID(), nullable=True, comment="Resolution snapshot proving the entitled market-data inputs used for this fixing."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACCEPTED'"), nullable=False, comment="Fixing lifecycle state: ACCEPTED, SUPERSEDED, or REJECTED."),
        sa.Column("supersedes_fixing_id", sa.UUID(), nullable=True, comment="Prior fixing superseded by this corrected fixing, without mutating the original fact."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which Fortem recorded the fixing."),
        sa.ForeignKeyConstraint(["option_strike_reset_rule_id"], ["secm.option_strike_reset_rule.option_strike_reset_rule_id"], name="fk_option_strike_fixing_rule"),
        sa.ForeignKeyConstraint(["market_data_observation_id"], ["md.market_data_observation.market_data_observation_id"], name="fk_option_strike_fixing_observation"),
        sa.ForeignKeyConstraint(["market_data_resolution_snapshot_id"], ["md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"], name="fk_option_strike_fixing_resolution_snapshot"),
        sa.ForeignKeyConstraint(["supersedes_fixing_id"], ["secm.option_strike_fixing.option_strike_fixing_id"], name="fk_option_strike_fixing_supersedes"),
        sa.PrimaryKeyConstraint("option_strike_fixing_id"),
        sa.CheckConstraint("resolved_strike_value > 0", name="ck_option_strike_fixing_positive"),
        sa.CheckConstraint("status IN ('ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_option_strike_fixing_status"),
        schema="secm",
    )

    op.create_index(
        "uq_option_terms_current",
        "option_terms",
        ["instrument_node_id"],
        unique=True,
        schema="secm",
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "ix_option_terms_effective",
        "option_terms",
        ["instrument_node_id", "effective_from", "effective_to"],
        schema="secm",
    )
    op.create_index(
        "ix_option_strike_reset_rule_event",
        "option_strike_reset_rule",
        ["schedule_event_id", "option_terms_id"],
        schema="secm",
    )
    op.create_index(
        "uq_option_strike_fixing_current",
        "option_strike_fixing",
        ["option_strike_reset_rule_id", "fixing_date"],
        unique=True,
        schema="secm",
        postgresql_where=sa.text("status = 'ACCEPTED'"),
    )
    op.create_index(
        "ix_option_strike_fixing_rule_date",
        "option_strike_fixing",
        ["option_strike_reset_rule_id", "fixing_date", "recorded_at_utc"],
        schema="secm",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM secm.option_terms
                    GROUP BY instrument_node_id
                    HAVING COUNT(*) > 1
                ) THEN
                    RAISE EXCEPTION 'Cannot downgrade dynamic option terms while multiple versions exist for an instrument';
                END IF;
            END $$;
            """
        )
    )
    op.drop_index("ix_option_strike_fixing_rule_date", table_name="option_strike_fixing", schema="secm")
    op.drop_index("uq_option_strike_fixing_current", table_name="option_strike_fixing", schema="secm")
    op.drop_index("ix_option_strike_reset_rule_event", table_name="option_strike_reset_rule", schema="secm")
    op.drop_index("ix_option_terms_effective", table_name="option_terms", schema="secm")
    op.drop_index("uq_option_terms_current", table_name="option_terms", schema="secm")
    op.drop_table("option_strike_fixing", schema="secm")
    op.drop_table("option_strike_reset_rule", schema="secm")
    for name in ("ck_option_terms_dynamic_schedule", "ck_option_terms_strike_mode", "ck_option_terms_valid_period", "ck_option_terms_version_positive"):
        op.drop_constraint(name, "option_terms", schema="secm", type_="check")
    op.drop_constraint("fk_option_terms_strike_reset_schedule", "option_terms", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_option_terms_supersedes", "option_terms", schema="secm", type_="foreignkey")
    op.drop_constraint("uq_option_terms_version", "option_terms", schema="secm", type_="unique")
    op.drop_constraint("option_terms_pkey", "option_terms", schema="secm", type_="primary")
    op.create_primary_key("option_terms_pkey", "option_terms", ["instrument_node_id"], schema="secm")
    for column_name in (
        "strike_reset_schedule_id",
        "strike_mode",
        "supersedes_option_terms_id",
        "status",
        "is_current",
        "effective_to",
        "effective_from",
        "version_no",
        "option_terms_id",
    ):
        op.drop_column("option_terms", column_name, schema="secm")
