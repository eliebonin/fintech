"""Schema contracts for the canonical leg-based swap model."""

from sqlalchemy import CheckConstraint

from security_master_schema.models import metadata


def test_swap_uses_common_instrument_dates_without_duplicate_term_dates() -> None:
    """Catches reintroduction of independently editable swap effective/maturity dates."""

    swap_terms = metadata.tables["secm.swap_terms"]
    instrument_dates = metadata.tables["secm.instrument_dates"]

    assert "effective_date" not in swap_terms.c
    assert "termination_date" not in swap_terms.c
    assert {"effective_date", "maturity_date"}.issubset(set(instrument_dates.c.keys()))


def test_swap_leg_schema_persists_governed_role_and_direction_contracts() -> None:
    """Catches database writes that bypass API validation with unsupported leg semantics."""

    swap_leg = metadata.tables["secm.swap_leg"]
    constraint_names = {
        constraint.name
        for constraint in swap_leg.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_swap_leg_role",
        "ck_swap_leg_pay_receive",
        "ck_swap_leg_number",
        "ck_swap_leg_role_requirements",
    }.issubset(constraint_names)

    swap_terms = metadata.tables["secm.swap_terms"]
    term_constraint_names = {
        constraint.name
        for constraint in swap_terms.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_swap_terms_type" in term_constraint_names
