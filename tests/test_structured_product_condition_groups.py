"""Schema contract for structured-product condition groups."""

from sqlalchemy import CheckConstraint

from security_master_schema.models import metadata


def test_condition_groups_own_observation_and_boolean_semantics() -> None:
    """One group represents one Boolean product condition at one observation context."""

    group = metadata.tables["secm.structured_product_condition_group"]

    assert {
        "condition_group_id",
        "structured_product_terms_id",
        "group_code",
        "observation_style",
        "schedule_event_id",
        "logical_operator",
        "underlying_aggregation",
        "underlying_scope",
        "evaluation_sequence",
        "status",
        "source_payload_id",
    }.issubset(group.c.keys())

    constraint_names = {
        constraint.name
        for constraint in group.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_sp_condition_group_operator",
        "ck_sp_condition_group_underlying_aggregation",
        "ck_sp_condition_group_underlying_scope",
        "ck_sp_condition_group_observation",
        "ck_sp_condition_group_evaluation_sequence",
    }.issubset(constraint_names)


def test_atomic_rules_and_actions_belong_to_condition_groups() -> None:
    """Atomic tests aggregate at a group and group actions execute once in order."""

    rule = metadata.tables["secm.barrier_rule"]
    action = metadata.tables["secm.condition_group_action"]

    assert {
        "condition_group_id",
        "owner_reference_node_id",
        "underlying_reference_node_id",
        "condition_sequence",
        "comparison_operator",
        "level_reference_type",
        "lower_level_value",
        "upper_level_value",
        "lower_bound_inclusive",
        "upper_bound_inclusive",
        "underlying_measure",
        "status",
        "source_payload_id",
    }.issubset(rule.c.keys())
    assert {
        "condition_group_id",
        "action_type",
        "target_scope",
        "target_reference_node_id",
        "target_composition_id",
        "payment_amount",
        "payment_rate",
        "payment_currency_id",
        "payment_basis",
        "payment_timing",
        "payment_schedule_id",
        "payment_date",
        "payout_multiplicity",
        "execution_sequence",
        "status",
        "source_payload_id",
    }.issubset(action.c.keys())

    rule_fks = {
        foreign_key.target_fullname
        for column in rule.columns
        for foreign_key in column.foreign_keys
    }
    action_fks = {
        foreign_key.target_fullname
        for column in action.columns
        for foreign_key in column.foreign_keys
    }
    assert "secm.structured_product_condition_group.condition_group_id" in rule_fks
    assert "secm.structured_product_condition_group.condition_group_id" in action_fks

    rule_constraints = {
        constraint.name
        for constraint in rule.constraints
        if isinstance(constraint, CheckConstraint)
    }
    action_constraints = {
        constraint.name
        for constraint in action.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_barrier_rule_comparison",
        "ck_barrier_rule_sequence",
        "ck_barrier_rule_levels",
        "ck_barrier_rule_bound_inclusivity",
    }.issubset(rule_constraints)
    assert {
        "ck_condition_group_action_target_scope",
        "ck_condition_group_action_target_composition",
        "ck_condition_group_action_execution_sequence",
        "ck_condition_group_action_payment_values",
        "ck_condition_group_action_type",
        "ck_condition_group_action_payment_basis",
        "ck_condition_group_action_payout_multiplicity",
    }.issubset(action_constraints)

    action_sql = {
        constraint.name: str(constraint.sqltext)
        for constraint in action.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "PAY_CONSOLATION" in action_sql["ck_condition_group_action_type"]
    assert "PCT_OF_MAX_PAYOFF" in action_sql["ck_condition_group_action_payment_basis"]
    assert "ONCE_PER_PARENT" in action_sql["ck_condition_group_action_payout_multiplicity"]
    assert "PER_UNDERLYING" in action_sql["ck_condition_group_action_payout_multiplicity"]


def test_initial_fixings_retain_effective_value_and_market_data_provenance() -> None:
    fixing = metadata.tables["secm.structured_product_initial_fixing"]

    assert {
        "structured_product_initial_fixing_id",
        "structured_product_terms_id",
        "underlying_reference_node_id",
        "fixing_date",
        "fixing_value",
        "fixing_basis",
        "market_data_observation_id",
        "market_data_resolution_snapshot_id",
        "source_system_id",
        "status",
        "supersedes_fixing_id",
        "recorded_at_utc",
    }.issubset(fixing.c.keys())

    foreign_keys = {
        foreign_key.target_fullname
        for column in fixing.columns
        for foreign_key in column.foreign_keys
    }
    assert "secm.structured_product_terms.structured_product_terms_id" in foreign_keys
    assert "secm.financial_reference_node.reference_node_id" in foreign_keys
    assert "md.market_data_observation.market_data_observation_id" in foreign_keys
    assert "md.market_data_resolution_snapshot.market_data_resolution_snapshot_id" in foreign_keys

    constraints = {
        constraint.name
        for constraint in fixing.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_structured_product_initial_fixing_positive",
        "ck_structured_product_initial_fixing_basis",
        "ck_structured_product_initial_fixing_status",
    }.issubset(constraints)


def test_structured_product_terms_and_coupon_programmes_are_versioned() -> None:
    terms = metadata.tables["secm.structured_product_terms"]
    programme = metadata.tables["secm.structured_product_coupon_programme"]
    period = metadata.tables["secm.structured_product_coupon_period"]

    assert terms.primary_key.columns.keys() == ["structured_product_terms_id"]
    assert {
        "structured_product_terms_id",
        "instrument_node_id",
        "version_no",
        "effective_from",
        "effective_to",
        "is_current",
        "supersedes_structured_product_terms_id",
        "first_autocall_observation_date",
        "default_underlying_scope",
        "source_payload_id",
    }.issubset(terms.c.keys())
    assert {
        "coupon_programme_id",
        "structured_product_terms_id",
        "programme_code",
        "memory_mode",
        "payment_mode",
        "schedule_id",
        "eligibility_condition_group_id",
        "final_payment_treatment",
        "source_payload_id",
    }.issubset(programme.c.keys())
    assert {
        "coupon_period_id",
        "coupon_programme_id",
        "period_sequence",
        "observation_event_id",
        "eligibility_condition_group_id",
        "coupon_rate",
        "coupon_amount",
        "memory_eligible",
        "status",
        "source_payload_id",
    }.issubset(period.c.keys())

    programme_constraints = {
        constraint.name
        for constraint in programme.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_sp_coupon_programme_final_payment_treatment" in programme_constraints

    terms_constraints = {
        constraint.name
        for constraint in terms.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_structured_product_terms_version_no",
        "ck_structured_product_terms_valid_period",
        "ck_structured_product_terms_underlying_scope",
    }.issubset(terms_constraints)


def test_structured_product_components_and_composition_values_are_explicit() -> None:
    component_terms = metadata.tables["secm.structured_product_component_terms"]
    composition = metadata.tables["secm.instrument_composition"]

    assert {
        "structured_product_component_terms_id",
        "instrument_composition_id",
        "component_kind",
        "payoff_style",
        "payout_amount",
        "payout_rate",
        "payout_currency_id",
        "payout_basis",
        "payment_timing",
        "schedule_id",
        "status",
        "source_payload_id",
    }.issubset(component_terms.c.keys())
    assert {
        "instrument_composition_id",
        "parent_instrument_node_id",
        "component_reference_node_id",
        "composition_role",
        "composition_value",
        "composition_value_kind",
        "component_sequence",
        "structured_product_terms_id",
        "composition_date",
        "effective_to",
        "source_payload_id",
    }.issubset(composition.c.keys())
    assert "composition_rate" not in composition.c

    component_constraints = {
        constraint.name
        for constraint in component_terms.constraints
        if isinstance(constraint, CheckConstraint)
    }
    composition_constraints = {
        constraint.name
        for constraint in composition.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_sp_component_terms_payout_values" in component_constraints
    assert "ck_instrument_composition_value_kind" in composition_constraints
