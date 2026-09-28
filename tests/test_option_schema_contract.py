"""Schema contracts for the first vanilla option terms model."""

from sqlalchemy import CheckConstraint, UniqueConstraint

from security_master_schema.models import metadata


def test_option_terms_capture_strike_and_settlement_conventions() -> None:
    """Catches a terms table that cannot distinguish index, FX, and monetary strikes."""

    option_terms = metadata.tables["secm.option_terms"]

    assert {
        "strike_basis",
        "premium_currency_id",
        "settlement_currency_id",
        "exercise_schedule_id",
    }.issubset(set(option_terms.c.keys()))

    foreign_keys = {
        foreign_key.target_fullname
        for column in option_terms.columns
        for foreign_key in column.foreign_keys
    }
    assert "secm.currency.currency_id" in foreign_keys
    assert "secm.schedule.schedule_id" in foreign_keys


def test_option_terms_support_static_versions_and_contractual_strike_resets() -> None:
    """Dynamic strikes must be scheduled contract terms, not overwritten prices."""

    option_terms = metadata.tables["secm.option_terms"]
    reset_rule = metadata.tables["secm.option_strike_reset_rule"]
    fixing = metadata.tables["secm.option_strike_fixing"]

    assert {
        "option_terms_id",
        "version_no",
        "effective_from",
        "effective_to",
        "is_current",
        "status",
        "supersedes_option_terms_id",
        "strike_mode",
        "strike_reset_schedule_id",
        "strike_reference_initial_fixing_id",
    }.issubset(option_terms.c.keys())
    assert {
        "option_strike_reset_rule_id",
        "option_terms_id",
        "schedule_event_id",
        "determination_method",
        "reference_node_id",
        "market_data_series_id",
        "strike_basis",
        "fixed_strike_value",
        "strike_currency_id",
        "floor_value",
        "cap_value",
    }.issubset(reset_rule.c.keys())
    assert {
        "option_strike_fixing_id",
        "option_strike_reset_rule_id",
        "fixing_date",
        "fixing_observed_at_utc",
        "resolved_strike_value",
        "market_data_observation_id",
        "market_data_resolution_snapshot_id",
        "status",
        "supersedes_fixing_id",
    }.issubset(fixing.c.keys())

    reset_rule_fks = {
        foreign_key.target_fullname
        for column in reset_rule.columns
        for foreign_key in column.foreign_keys
    }
    fixing_fks = {
        foreign_key.target_fullname
        for column in fixing.columns
        for foreign_key in column.foreign_keys
    }
    assert "secm.option_terms.option_terms_id" in reset_rule_fks
    assert "secm.schedule_event.schedule_event_id" in reset_rule_fks
    assert "md.market_data_series.market_data_series_id" in reset_rule_fks
    assert "md.market_data_observation.market_data_observation_id" in fixing_fks
    assert "md.market_data_resolution_snapshot.market_data_resolution_snapshot_id" in fixing_fks
    option_fks = {
        foreign_key.target_fullname
        for column in option_terms.columns
        for foreign_key in column.foreign_keys
    }
    assert "secm.structured_product_initial_fixing.structured_product_initial_fixing_id" in option_fks

    adjustment = metadata.tables["secm.option_strike_adjustment"]
    assert {
        "option_strike_adjustment_id",
        "option_terms_id",
        "corporate_action_id",
        "effective_date",
        "pre_adjustment_strike_value",
        "post_adjustment_strike_value",
        "strike_factor",
        "post_adjustment_fixing_value",
        "revision_no",
        "status",
        "supersedes_adjustment_id",
    }.issubset(adjustment.c.keys())

    option_constraints = {constraint.name for constraint in option_terms.constraints}
    reset_constraints = {constraint.name for constraint in reset_rule.constraints}
    fixing_constraints = {constraint.name for constraint in fixing.constraints}
    assert {
        "ck_option_terms_strike_mode",
        "ck_option_terms_dynamic_schedule",
        "ck_option_terms_version_positive",
        "ck_option_terms_valid_period",
        "ck_option_terms_initial_fixing_basis",
    }.issubset(option_constraints)
    adjustment_constraints = {constraint.name for constraint in adjustment.constraints}
    assert "ck_option_strike_adjustment_revision" in adjustment_constraints
    adjustment_unique_constraints = {
        constraint.name
        for constraint in adjustment.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_option_strike_adjustment_revision" in adjustment_unique_constraints
    assert "uq_option_strike_adjustment_action" not in adjustment_unique_constraints
    assert {
        "ck_option_strike_reset_method",
        "ck_option_strike_reset_fixed_value",
        "ck_option_strike_reset_bounds",
    }.issubset(reset_constraints)
    assert {
        "ck_option_strike_fixing_status",
        "ck_option_strike_fixing_positive",
    }.issubset(fixing_constraints)

    index_names = {
        index.name
        for table in metadata.tables.values()
        for index in table.indexes
    }
    assert "uq_option_terms_current" in index_names
    assert "uq_option_strike_fixing_current" in index_names


def test_option_terms_have_governed_vanilla_constraints() -> None:
    """Catches database writes that bypass the vanilla option contract."""

    option_terms = metadata.tables["secm.option_terms"]
    constraint_names = {
        constraint.name
        for constraint in option_terms.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_option_terms_type",
        "ck_option_terms_exercise_style",
        "ck_option_terms_settlement_method",
        "ck_option_terms_strike_basis",
        "ck_option_terms_strike_currency",
        "ck_option_terms_cash_currency",
        "ck_option_terms_bermudan_schedule",
    }.issubset(constraint_names)
