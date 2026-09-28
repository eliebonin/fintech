"""Pure contract tests for the structured-product proposal boundary."""

from datetime import date
from uuid import UUID

import pytest

from apps.reference_api.structured_product_contracts import (
    AutocallDraftRequest,
    StructuredProductDraftError,
    aggregate_pay_once_for_group,
    logical_operator_for_scope,
    payout_multiplicity_for_group,
    underlying_aggregation_for_scope,
    validate_autocall_draft,
)


UNDERLYING_A = UUID("00000000-0000-7000-8000-000000000101")
UNDERLYING_B = UUID("00000000-0000-7000-8000-000000000102")
CURRENCY = UUID("00000000-0000-7000-8000-000000000201")
CALENDAR = UUID("00000000-0000-7000-8000-000000000301")


def _component_row(row_id: str, underlying_id: UUID) -> dict[str, object]:
    return {
        "rowId": row_id,
        "rowKind": "COMPONENT",
        "groupCode": "COUPON_COMPONENT",
        "componentKind": "DIGITAL",
        "conditionRole": "COUPON_ELIGIBILITY",
        "conditionOperator": "GE",
        "conditionScope": "WORST_OF",
        "underlyingReferenceNodeId": str(underlying_id),
        "underlyingLabel": "Underlying",
        "participation": 1,
        "couponRate": 6.5,
        "strikeValue": 100,
        "strikePercent": 100,
        "observationDate": "2027-01-01",
        "paymentDate": "2027-01-05",
        "conditionLevel": 70,
        "conditionLevelBasis": "PCT_OF_INITIAL",
        "actionCode": "PAY_COMPONENT",
        "actionTarget": "COMPOSITION",
    }


def _kip_row(row_id: str, underlying_id: UUID) -> dict[str, object]:
    return {
        "rowId": row_id,
        "rowKind": "COMPONENT",
        "groupCode": "CAPITAL_PROTECTION",
        "componentKind": "VANILLA_OPTION",
        "optionType": "PUT",
        "exerciseStyle": "EUROPEAN",
        "conditionRole": "CAPITAL_PROTECTION",
        "observationStyle": "CONTINUOUS",
        "conditionOperator": "LE",
        "conditionScope": "WORST_OF",
        "underlyingReferenceNodeId": str(underlying_id),
        "underlyingLabel": "Underlying",
        "participation": -1,
        "strikeValue": 65,
        "strikePercent": 65,
        "observationDate": "2028-01-01",
        "paymentDate": "2028-01-05",
        "conditionLevel": 65,
        "conditionLevelBasis": "PCT_OF_INITIAL",
        "actionCode": "PAY_COMPONENT",
        "actionTarget": "COMPOSITION",
    }


def _base_payload() -> dict[str, object]:
    return {
        "canonicalName": "Demo consolation autocall",
        "internalCode": "SP_AUTOCALL_CONSOLATION_TEST",
        "effectiveFrom": "2026-01-01",
        "productSubtype": "AUTOCALL_CONSOLATION",
        "issueCurrencyId": str(CURRENCY),
        "scope": "WORST_OF",
        "observationStyle": "DISCRETE",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "ANNUAL",
        "paymentLagBusinessDays": 2,
        "includeKip": True,
        "kipBarrier": 65,
        "includeConsolation": True,
        "consolationRate": 50,
        "finalPayoffBarrier": 90,
        "underlyings": [
            {
                "referenceNodeId": str(UNDERLYING_A),
                "initialFixing": 100,
                "fixingDate": "2027-01-01",
                "fixingBasis": "LEVEL",
                "fixingSource": "MANUAL",
            },
            {
                "referenceNodeId": str(UNDERLYING_B),
                "initialFixing": 200,
                "fixingDate": "2027-01-01",
                "fixingBasis": "LEVEL",
                "fixingSource": "MANUAL",
            },
        ],
        "rows": [
            _component_row("coupon-a", UNDERLYING_A),
            _component_row("coupon-b", UNDERLYING_B),
            _kip_row("kip-a", UNDERLYING_A),
            _kip_row("kip-b", UNDERLYING_B),
            {
                "rowId": "consolation",
                "rowKind": "ACTION",
                "groupCode": "CONSOLATION_ACTION",
                "componentKind": "PARENT_ACTION",
                "conditionRole": "CONSOLATION",
                "conditionOperator": "RANGE",
                "conditionScope": "WORST_OF",
                "underlyingReferenceNodeId": None,
                "underlyingLabel": "Worst of",
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-05",
                "conditionLowerLevel": 65,
                "conditionUpperLevel": 90,
                "conditionLowerInclusive": True,
                "conditionUpperInclusive": False,
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "payoutRate": 50,
                "actionCode": "PAY_CONSOLATION",
                "actionTarget": "PARENT",
            },
        ],
        "submissionMode": "MANUAL",
    }


def test_valid_consolation_draft_normalises_range_operator() -> None:
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(_base_payload()))

    assert request.product_subtype == "AUTOCALL_CONSOLATION"
    assert request.include_consolation is True
    assert request.rows[-1].condition_operator == "BETWEEN"
    assert request.final_payoff_barrier == 90
    assert request.rows[-1].condition_lower_inclusive is True
    assert request.rows[-1].condition_upper_inclusive is False


def test_phoenix_accepts_independent_coupon_and_autocall_frequencies() -> None:
    payload = _base_payload()
    payload.update({
        "productSubtype": "PHOENIX",
        "couponFrequency": "MONTHLY",
        "autocallFrequency": "QUARTERLY",
    })
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert request.frequency == "ANNUAL"
    assert request.coupon_frequency == "MONTHLY"
    assert request.autocall_frequency == "QUARTERLY"


def test_first_autocall_date_and_final_payment_treatment_are_normalised() -> None:
    payload = _base_payload()
    payload.update({
        "productSubtype": "PHOENIX",
        "memoryMode": "CONDITIONAL_CATCH_UP",
        "firstAutocallObservationDate": "2027-07-01",
        "finalPaymentTreatment": "FORFEIT",
    })
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert request.first_autocall_observation_date == date(2027, 7, 1)
    assert request.final_payment_treatment == "FORFEIT"


def test_final_payment_treatment_is_inactive_without_coupon_memory() -> None:
    payload = _base_payload()
    payload["finalPaymentTreatment"] = "INCLUDE_IN_REDEMPTION"

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert request.memory_mode == "NONE"
    assert request.final_payment_treatment is None


def test_final_redemption_is_unique_and_maturity_dated() -> None:
    payload = _base_payload()
    final_row = {
        "rowId": "final-redemption",
        "rowKind": "ACTION",
        "groupCode": "FINAL_REDEMPTION",
        "componentKind": "PARENT_ACTION",
        "conditionRole": "FINAL_REDEMPTION",
        "conditionOperator": "GE",
        "conditionScope": "WORST_OF",
        "underlyingReferenceNodeId": None,
        "underlyingLabel": "Worst of · maturity if not previously called",
        "observationDate": "2028-01-01",
        "paymentDate": "2028-01-05",
        "conditionLevel": 0,
        "conditionLevelBasis": "PCT_OF_INITIAL",
        "actionCode": "FINAL_REDEMPTION",
        "actionTarget": "PARENT",
    }
    payload["rows"] = [*payload["rows"], final_row]
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))
    assert [row.action_code for row in request.rows].count("FINAL_REDEMPTION") == 1

    payload["rows"] = [*payload["rows"], {**final_row, "rowId": "final-redemption-duplicate"}]
    with pytest.raises(ValueError, match="only one FINAL_REDEMPTION"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_coupon_barrier_inheritance_is_explicit_and_defaults_to_true() -> None:
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(_base_payload()))
    assert request.coupon_barrier_follows_autocall is True

    payload = _base_payload()
    payload["couponBarrierFollowsAutocall"] = False
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))
    assert request.coupon_barrier_follows_autocall is False


def test_consolation_requires_an_explicit_final_payoff_barrier() -> None:
    payload = _base_payload()
    payload.pop("finalPayoffBarrier")
    with pytest.raises(ValueError, match="finalPayoffBarrier"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    payload = _base_payload()
    payload["finalPayoffBarrier"] = 65
    with pytest.raises(ValueError, match="final payoff barrier"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_consolation_requires_a_valid_lower_barrier_and_range() -> None:
    payload = _base_payload()
    payload["includeKip"] = False
    payload["rows"] = [row for row in payload["rows"] if row.get("conditionRole") != "CAPITAL_PROTECTION"]
    with pytest.raises(ValueError, match="consolationLowerBarrier"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    payload = _base_payload()
    payload["rows"] = [*payload["rows"][:-1], {**payload["rows"][-1], "conditionUpperLevel": 65}]
    with pytest.raises(ValueError, match="upper"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_consolation_can_use_an_explicit_lower_barrier_without_a_kip_leg() -> None:
    payload = _base_payload()
    payload["includeKip"] = False
    payload["kipBarrier"] = 0
    payload["consolationLowerBarrier"] = 65
    payload["rows"] = [row for row in payload["rows"] if row.get("conditionRole") != "CAPITAL_PROTECTION"]

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert request.include_kip is False
    assert request.consolation_lower_barrier == 65
    assert request.rows[-1].condition_lower_level == 65


def test_consolation_without_kip_requires_an_explicit_lower_barrier() -> None:
    payload = _base_payload()
    payload["includeKip"] = False
    payload["kipBarrier"] = 0
    payload["rows"] = [row for row in payload["rows"] if row.get("conditionRole") != "CAPITAL_PROTECTION"]

    with pytest.raises(ValueError, match="consolationLowerBarrier"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_unsupported_basket_scope_is_rejected_until_weighted_aggregation_exists() -> None:
    payload = _base_payload()
    payload["scope"] = "BASKET"
    payload["rows"] = [
        {**row, "conditionScope": "BASKET"}
        for row in payload["rows"]
    ]

    with pytest.raises(ValueError, match="BASKET"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_multi_underlying_scopes_reduce_to_minimum_or_maximum_explicitly() -> None:
    assert underlying_aggregation_for_scope("SINGLE") == "SINGLE"
    assert underlying_aggregation_for_scope("WORST_OF") == "MIN"
    assert underlying_aggregation_for_scope("BEST_OF") == "MAX"
    assert underlying_aggregation_for_scope("SINGLE", has_predicate=False) == "NONE"
    assert logical_operator_for_scope("SINGLE") == "ALL"
    # Multi-underlying groups reduce measurements to MIN/MAX and apply one
    # predicate.  ANY/ALL would be incorrect for LE and BETWEEN conditions.
    assert logical_operator_for_scope("WORST_OF") == "NONE"
    assert logical_operator_for_scope("BEST_OF") == "NONE"
    assert logical_operator_for_scope("SINGLE", has_predicate=False) == "NONE"
    with pytest.raises(StructuredProductDraftError, match="BASKET"):
        underlying_aggregation_for_scope("BASKET")


def test_aggregate_coupon_actions_pay_once_for_multi_underlying_groups() -> None:
    assert aggregate_pay_once_for_group("WORST_OF", "COUPON_ELIGIBILITY", "PAY_COMPONENT") is True
    assert aggregate_pay_once_for_group("BEST_OF", "CAPITAL_PROTECTION", "PAY_COMPONENT") is True
    assert aggregate_pay_once_for_group("WORST_OF", "OPTION_PAYOFF", "PAY_COMPONENT") is False
    assert aggregate_pay_once_for_group("SINGLE", "COUPON_ELIGIBILITY", "PAY_COMPONENT") is False


def test_payout_multiplicity_is_derived_from_group_scope_and_action() -> None:
    assert payout_multiplicity_for_group("WORST_OF", "CAPITAL_PROTECTION", "PAY_COMPONENT") == "ONCE_PER_PARENT"
    assert payout_multiplicity_for_group("BEST_OF", "COUPON_ELIGIBILITY", "PAY_COMPONENT") == "ONCE_PER_PARENT"
    assert payout_multiplicity_for_group("SINGLE", "CAPITAL_PROTECTION", "PAY_COMPONENT") == "PER_COMPONENT"
    assert payout_multiplicity_for_group("EACH_UNDERLYING", "CAPITAL_PROTECTION", "PAY_COMPONENT") == "PER_UNDERLYING"
    assert payout_multiplicity_for_group("WORST_OF", "REDEEM_PARENT", "REDEEM_PARENT") == "ONCE_PER_PARENT"


def test_kip_requires_exactly_one_child_for_each_underlying() -> None:
    payload = _base_payload()
    payload["rows"] = [
        *payload["rows"],
        _kip_row("kip-a-duplicate", UNDERLYING_A),
        _kip_row("kip-a-second", UNDERLYING_A),
    ]

    with pytest.raises(ValueError, match="exactly one CAPITAL_PROTECTION KIP component per underlying"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_multi_underlying_condition_group_requires_one_shared_predicate() -> None:
    payload = _base_payload()
    payload["rows"] = [
        payload["rows"][0],
        {**payload["rows"][1], "conditionLevel": 75},
        *[row for row in payload["rows"] if row.get("conditionRole") == "CAPITAL_PROTECTION"],
        payload["rows"][-1],
    ]

    with pytest.raises(ValueError, match="one shared predicate"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_market_data_fixing_requires_observation_or_resolution_provenance() -> None:
    payload = _base_payload()
    payload["underlyings"] = [{
        **payload["underlyings"][0],
        "fixingSource": "MARKET_DATA",
    }, payload["underlyings"][1]]
    with pytest.raises(ValueError, match="provenance"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_missing_fixing_date_defaults_to_start_date() -> None:
    """The UI may omit a separate fixing date when it equals the observation start."""

    payload = _base_payload()
    payload["underlyings"] = [
        {key: value for key, value in underlying.items() if key != "fixingDate"}
        for underlying in payload["underlyings"]
    ]

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert all(underlying.fixing_date == date(2027, 1, 1) for underlying in request.underlyings)


def test_composed_vanilla_with_kip_accepts_unconditional_option_payoff_component() -> None:
    payload = {
        "canonicalName": "Demo vanilla with KIP",
        "internalCode": "SP_VANILLA_KIP_TEST",
        "effectiveFrom": "2027-01-01",
        "productSubtype": "VANILLA_KIP",
        "issueCurrencyId": str(CURRENCY),
        "scope": "SINGLE",
        "observationStyle": "FINAL_ONLY",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "ANNUAL",
        "paymentLagBusinessDays": 2,
        "includeKip": True,
        "includeConsolation": False,
        "underlyings": [{
            "referenceNodeId": str(UNDERLYING_A),
            "initialFixing": 100,
            "fixingDate": "2027-01-01",
            "fixingBasis": "LEVEL",
            "fixingSource": "MANUAL",
        }],
        "rows": [
            {
                "rowId": "option-leg",
                "rowKind": "COMPONENT",
                "groupCode": "OPTION_LEG",
                "componentKind": "VANILLA_OPTION",
                "optionType": "CALL",
                "exerciseStyle": "EUROPEAN",
                "conditionRole": "OPTION_PAYOFF",
                "observationStyle": "FINAL_ONLY",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "participation": 1,
                "strikeValue": 100,
                "strikePercent": 100,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-04",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "conditionLevel": None,
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "kip-leg",
                "rowKind": "COMPONENT",
                "groupCode": "CAPITAL_PROTECTION",
                "componentKind": "VANILLA_OPTION",
                "optionType": "PUT",
                "exerciseStyle": "EUROPEAN",
                "conditionRole": "CAPITAL_PROTECTION",
                "observationStyle": "CONTINUOUS",
                "conditionOperator": "LE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "participation": -1,
                "strikeValue": 65,
                "strikePercent": 65,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-04",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "conditionLevel": 65,
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
        ],
    }

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    assert request.product_subtype == "VANILLA_KIP"
    assert request.rows[0].condition_role == "OPTION_PAYOFF"
    assert request.rows[0].condition_level is None
    assert request.rows[1].observation_style == "CONTINUOUS"


def test_composed_vanilla_spread_rejects_mixed_option_types() -> None:
    option_row = {
        "rowId": "option-leg",
        "rowKind": "COMPONENT",
        "groupCode": "OPTION_LEG",
        "componentKind": "VANILLA_OPTION",
        "optionType": "CALL",
        "exerciseStyle": "EUROPEAN",
        "conditionRole": "OPTION_PAYOFF",
        "observationStyle": "FINAL_ONLY",
        "conditionOperator": "GE",
        "conditionScope": "SINGLE",
        "underlyingReferenceNodeId": str(UNDERLYING_A),
        "underlyingLabel": "Underlying",
        "participation": 1,
        "strikeValue": 100,
        "strikePercent": 100,
        "observationDate": "2028-01-01",
        "paymentDate": "2028-01-04",
        "conditionLevelBasis": "PCT_OF_INITIAL",
        "conditionLevel": None,
        "actionCode": "PAY_COMPONENT",
        "actionTarget": "COMPOSITION",
    }
    kip_row = {
        "rowId": "kip-leg",
        "rowKind": "COMPONENT",
        "groupCode": "CAPITAL_PROTECTION",
        "componentKind": "VANILLA_OPTION",
        "optionType": "PUT",
        "exerciseStyle": "EUROPEAN",
        "conditionRole": "CAPITAL_PROTECTION",
        "observationStyle": "CONTINUOUS",
        "conditionOperator": "LE",
        "conditionScope": "SINGLE",
        "underlyingReferenceNodeId": str(UNDERLYING_A),
        "underlyingLabel": "Underlying",
        "participation": -1,
        "strikeValue": 65,
        "strikePercent": 65,
        "observationDate": "2028-01-01",
        "paymentDate": "2028-01-04",
        "conditionLevelBasis": "PCT_OF_INITIAL",
        "conditionLevel": 65,
        "actionCode": "PAY_COMPONENT",
        "actionTarget": "COMPOSITION",
    }
    payload = {
        "canonicalName": "Demo vanilla spread with KIP",
        "effectiveFrom": "2027-01-01",
        "productSubtype": "VANILLA_SPREAD_KIP",
        "issueCurrencyId": str(CURRENCY),
        "scope": "SINGLE",
        "observationStyle": "FINAL_ONLY",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "ANNUAL",
        "includeKip": True,
        "underlyings": [{
            "referenceNodeId": str(UNDERLYING_A),
            "initialFixing": 100,
            "fixingDate": "2027-01-01",
            "fixingBasis": "LEVEL",
        }],
        "rows": [option_row, {**option_row, "rowId": "option-leg-2", "optionType": "PUT", "participation": -1, "strikePercent": 110, "strikeValue": 110}, kip_row],
    }

    with pytest.raises(ValueError, match="same option type"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_composed_digital_requires_explicit_payout() -> None:
    payload = {
        "canonicalName": "Demo digital with KIP",
        "effectiveFrom": "2027-01-01",
        "productSubtype": "DIGITAL_KIP",
        "issueCurrencyId": str(CURRENCY),
        "scope": "SINGLE",
        "observationStyle": "FINAL_ONLY",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "ANNUAL",
        "includeKip": True,
        "underlyings": [{
            "referenceNodeId": str(UNDERLYING_A),
            "initialFixing": 100,
            "fixingDate": "2027-01-01",
            "fixingBasis": "LEVEL",
        }],
        "rows": [
            {
                "rowId": "digital",
                "rowKind": "COMPONENT",
                "groupCode": "OPTION_LEG",
                "componentKind": "DIGITAL",
                "optionType": "DIGITAL",
                "conditionRole": "OPTION_PAYOFF",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-01",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "conditionLevel": None,
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "kip",
                "rowKind": "COMPONENT",
                "groupCode": "CAPITAL_PROTECTION",
                "componentKind": "VANILLA_OPTION",
                "optionType": "PUT",
                "conditionRole": "CAPITAL_PROTECTION",
                "observationStyle": "CONTINUOUS",
                "conditionOperator": "LE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-01",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "conditionLevel": 65,
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
        ],
    }
    with pytest.raises(ValueError, match="digital payout"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_row_ids_and_underlying_references_are_unique_and_owned() -> None:
    payload = _base_payload()
    payload["rows"] = [payload["rows"][0], {**payload["rows"][1], "rowId": payload["rows"][0]["rowId"]}]
    with pytest.raises(ValueError, match="rowId"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    payload = _base_payload()
    payload["rows"] = [{**payload["rows"][0], "underlyingReferenceNodeId": "00000000-0000-7000-8000-000000009999"}]
    with pytest.raises(ValueError, match="underlying"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_range_accrual_requires_explicit_accrual_convention_and_final_redemption() -> None:
    payload = {
        "canonicalName": "Demo range accrual",
        "effectiveFrom": "2027-01-01",
        "productSubtype": "RANGE_ACCRUAL",
        "issueCurrencyId": str(CURRENCY),
        "scope": "SINGLE",
        "observationStyle": "DISCRETE",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "QUARTERLY",
        "includeKip": False,
        "rangeObservationFrequency": "DAILY",
        "rangeAccrualBasis": "OBSERVATION_COUNT",
        "rangeNonBusinessDayRule": "BUSINESS_DAYS_ONLY",
        "rangeLowerLevel": 70,
        "rangeUpperLevel": 130,
        "rangeCouponRatePerAnnum": 8,
        "underlyings": [{
            "referenceNodeId": str(UNDERLYING_A),
            "initialFixing": 100,
            "fixingDate": "2027-01-01",
            "fixingBasis": "LEVEL",
        }],
        "rows": [
            {
                "rowId": "range-coupon",
                "rowKind": "COMPONENT",
                "groupCode": "COUPON_COMPONENT",
                "componentKind": "DIGITAL",
                "optionType": "DIGITAL",
                "conditionRole": "COUPON_ELIGIBILITY",
                "conditionOperator": "RANGE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "couponRate": 8,
                "conditionLowerLevel": 70,
                "conditionUpperLevel": 130,
                "observationDate": "2027-04-01",
                "paymentDate": "2027-04-05",
                "conditionLowerInclusive": True,
                "conditionUpperInclusive": True,
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "range-final",
                "rowKind": "ACTION",
                "groupCode": "FINAL_REDEMPTION",
                "componentKind": "PARENT_ACTION",
                "conditionRole": "FINAL_REDEMPTION",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": None,
                "underlyingLabel": "Parent product",
                "conditionLevel": 0,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-03",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "FINAL_REDEMPTION",
                "actionTarget": "PARENT",
            },
        ],
    }

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))
    assert request.product_subtype == "RANGE_ACCRUAL"
    assert request.range_accrual_basis == "OBSERVATION_COUNT"
    assert request.rows[0].condition_operator == "BETWEEN"

    payload["rangeUpperLevel"] = 70
    with pytest.raises(ValueError, match="upper level"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))


def test_supertracker_requires_leveraged_call_pair_when_capped() -> None:
    payload = {
        "canonicalName": "Demo supertracker",
        "effectiveFrom": "2027-01-01",
        "productSubtype": "SUPERTRACKER",
        "issueCurrencyId": str(CURRENCY),
        "scope": "SINGLE",
        "observationStyle": "FINAL_ONLY",
        "memoryMode": "NONE",
        "calendarId": str(CALENDAR),
        "startDate": "2027-01-01",
        "maturityDate": "2028-01-01",
        "frequency": "ANNUAL",
        "includeKip": True,
        "supertrackerParticipationRate": 1.35,
        "supertrackerIncludeCap": True,
        "supertrackerCapReturn": 25,
        "underlyings": [{
            "referenceNodeId": str(UNDERLYING_A),
            "initialFixing": 100,
            "fixingDate": "2027-01-01",
            "fixingBasis": "LEVEL",
        }],
        "rows": [
            {
                "rowId": "super-upside",
                "rowKind": "COMPONENT",
                "groupCode": "OPTION_LEG",
                "componentKind": "VANILLA_OPTION",
                "optionType": "CALL",
                "exerciseStyle": "EUROPEAN",
                "conditionRole": "OPTION_PAYOFF",
                "observationStyle": "FINAL_ONLY",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "participation": 1.35,
                "strikeValue": 100,
                "strikePercent": 100,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-03",
                "conditionLevel": None,
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "super-cap",
                "rowKind": "COMPONENT",
                "groupCode": "OPTION_LEG",
                "componentKind": "VANILLA_OPTION",
                "optionType": "CALL",
                "exerciseStyle": "EUROPEAN",
                "conditionRole": "OPTION_PAYOFF",
                "observationStyle": "FINAL_ONLY",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "participation": -1.35,
                "strikeValue": 125,
                "strikePercent": 125,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-03",
                "conditionLevel": None,
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "super-kip",
                "rowKind": "COMPONENT",
                "groupCode": "CAPITAL_PROTECTION",
                "componentKind": "VANILLA_OPTION",
                "optionType": "PUT",
                "exerciseStyle": "EUROPEAN",
                "conditionRole": "CAPITAL_PROTECTION",
                "observationStyle": "CONTINUOUS",
                "conditionOperator": "LE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": str(UNDERLYING_A),
                "underlyingLabel": "Underlying",
                "participation": -1,
                "strikeValue": 65,
                "strikePercent": 65,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-03",
                "conditionLevel": 65,
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "PAY_COMPONENT",
                "actionTarget": "COMPOSITION",
            },
            {
                "rowId": "super-final",
                "rowKind": "ACTION",
                "groupCode": "FINAL_REDEMPTION",
                "componentKind": "PARENT_ACTION",
                "conditionRole": "FINAL_REDEMPTION",
                "observationStyle": "FINAL_ONLY",
                "conditionOperator": "GE",
                "conditionScope": "SINGLE",
                "underlyingReferenceNodeId": None,
                "underlyingLabel": "Parent product",
                "conditionLevel": 0,
                "observationDate": "2028-01-01",
                "paymentDate": "2028-01-03",
                "conditionLevelBasis": "PCT_OF_INITIAL",
                "actionCode": "FINAL_REDEMPTION",
                "actionTarget": "PARENT",
            },
        ],
    }

    request = validate_autocall_draft(AutocallDraftRequest.model_validate(payload))
    assert str(request.supertracker_participation_rate) == "1.35"
    assert str(request.supertracker_cap_return) == "25"

    valid_rows = payload["rows"]
    payload["rows"] = valid_rows[:1] + valid_rows[2:]
    with pytest.raises(ValueError, match="optional second cap call"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(payload))

    invalid_strike_payload = {
        **payload,
        "rows": [
            {**valid_rows[0], "strikePercent": 101},
            valid_rows[1],
            *valid_rows[2:],
        ],
    }
    with pytest.raises(ValueError, match="struck at 100"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(invalid_strike_payload))

    missing_kip_payload = {
        **payload,
        "rows": [row for row in valid_rows if row.get("conditionRole") != "CAPITAL_PROTECTION"],
    }
    with pytest.raises(ValueError, match="includeKip"):
        validate_autocall_draft(AutocallDraftRequest.model_validate(missing_kip_payload))
