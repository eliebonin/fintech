"""Validated draft contract for structured-product/autocall onboarding.

The browser schedule is a projection for review.  This module is the server
boundary: it turns the projection into a typed, deterministic payload before a
proposal can be stored or approved.  It deliberately contains no pricing
logic and no database writes.
"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


StructuredProductSubtype = Literal[
    "AUTOCALL",
    "AUTOCALL_CONSOLATION",
    "PHOENIX",
    "ATHENA",
    "VANILLA_SPREAD_KIP",
    "VANILLA_KIP",
    "DIGITAL_KIP",
    "RANGE_ACCRUAL",
    "SUPERTRACKER",
]
ScheduleScope = Literal["SINGLE", "BEST_OF", "WORST_OF", "BASKET", "EACH_UNDERLYING"]
UnderlyingAggregation = Literal["SINGLE", "MIN", "MAX", "NONE"]
ConditionLogicalOperator = Literal["ALL", "ANY", "NONE"]
ConditionOperator = Literal["GE", "GT", "LE", "LT", "BETWEEN", "RANGE", "OUTSIDE"]
FinalPaymentTreatment = Literal["PAY_SEPARATELY", "INCLUDE_IN_REDEMPTION", "FORFEIT"]
PayoutMultiplicity = Literal["ONCE_PER_PARENT", "PER_UNDERLYING", "PER_COMPONENT"]


class StructuredProductDraftError(ValueError):
    """Stable domain validation error for an unpersistable draft graph."""


def underlying_aggregation_for_scope(
    scope: ScheduleScope,
    *,
    has_predicate: bool = True,
) -> UnderlyingAggregation:
    """Return the explicit reduction used by a condition group.

    ``BEST_OF`` and ``WORST_OF`` are economic selectors, not Boolean labels:
    they reduce the underlying performance to a maximum or minimum before the
    group predicate is applied.  Basket weighting and per-underlying outcomes
    need more contractual inputs than this onboarding slice has, so they fail
    closed rather than being stored with ambiguous semantics.
    """

    if not has_predicate:
        return "NONE"
    if scope == "SINGLE":
        return "SINGLE"
    if scope == "BEST_OF":
        return "MAX"
    if scope == "WORST_OF":
        return "MIN"
    raise StructuredProductDraftError(
        f"{scope} scope is not supported until its explicit aggregation terms are available"
    )


def logical_operator_for_scope(
    scope: ScheduleScope,
    *,
    has_predicate: bool = True,
) -> ConditionLogicalOperator:
    """Return the Boolean fold used by the current condition-group contract.

    Multi-underlying groups reduce the measurements to one scalar first
    (``MAX`` for best-of, ``MIN`` for worst-of) and then apply the predicate
    once.  They therefore do *not* use a Boolean ``ANY``/``ALL`` fold: that
    shortcut would be wrong for downward tests and bounded ranges.  ``NONE``
    records that the group has one aggregate predicate; the explicit
    ``underlying_aggregation`` column remains authoritative.
    """

    if not has_predicate:
        return "NONE"
    if scope in {"BEST_OF", "WORST_OF"}:
        return "NONE"
    if scope == "SINGLE":
        return "ALL"
    raise StructuredProductDraftError(
        f"{scope} scope is not supported until its explicit aggregation terms are available"
    )


def aggregate_pay_once_for_group(
    scope: ScheduleScope,
    condition_role: str,
    action_code: str,
) -> bool:
    """Whether a multi-underlying condition has one aggregate payout.

    Coupon eligibility and capital-protection conditions are tests on one
    best-/worst-of measurement. Their child rows retain each underlying so the
    predicate is auditable, but the aggregate result is one parent event, not
    one payment per name. Independent option legs remain component-targeted
    actions.
    """

    return payout_multiplicity_for_group(scope, condition_role, action_code) == "ONCE_PER_PARENT"


def payout_multiplicity_for_group(
    scope: ScheduleScope,
    condition_role: str,
    action_code: str,
) -> PayoutMultiplicity:
    """Derive how many payouts a persisted group action may create.

    The representation always keeps one component row per underlying.  The
    condition group's scope then determines whether the lifecycle evaluator
    reduces those children to one parent outcome or applies a component
    outcome to each child.  This is deliberately derived from the governed
    graph rather than entered as a second, potentially contradictory UI
    value.
    """

    if action_code in {"REDEEM_PARENT", "PAY_CONSOLATION", "FINAL_REDEMPTION"}:
        return "ONCE_PER_PARENT"
    if action_code != "PAY_COMPONENT":
        raise StructuredProductDraftError(f"Unsupported action code: {action_code}")
    if scope in {"BEST_OF", "WORST_OF"} and condition_role in {
        "COUPON_ELIGIBILITY",
        "CAPITAL_PROTECTION",
    }:
        return "ONCE_PER_PARENT"
    if scope == "EACH_UNDERLYING":
        return "PER_UNDERLYING"
    return "PER_COMPONENT"


class AutocallUnderlyingRequest(BaseModel):
    reference_node_id: UUID = Field(alias="referenceNodeId")
    initial_fixing: Decimal = Field(alias="initialFixing", gt=0)
    fixing_date: date | None = Field(default=None, alias="fixingDate")
    fixing_basis: Literal["LEVEL", "INDEX_POINTS", "FX_RATE", "PERCENT_OF_INITIAL"] = Field(alias="fixingBasis")
    fixing_source: Literal["MANUAL", "MARKET_DATA", "PROVIDER", "DERIVED"] = Field(default="MANUAL", alias="fixingSource")
    market_data_observation_id: UUID | None = Field(default=None, alias="marketDataObservationId")
    market_data_resolution_snapshot_id: UUID | None = Field(default=None, alias="marketDataResolutionSnapshotId")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    label: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class AutocallScheduleRowRequest(BaseModel):
    """One draft component or parent action projected by the UI schedule.

    Despite the historical class name, this row contract also carries the
    composed-option templates. ``observation_style`` is row-level because a
    continuous KIP and a final-only option payoff can share one terms version.
    """

    row_id: str = Field(alias="rowId", min_length=1, max_length=200)
    row_kind: Literal["COMPONENT", "ACTION"] = Field(alias="rowKind")
    group_code: str = Field(alias="groupCode", min_length=1, max_length=100)
    component_kind: Literal["DIGITAL", "VANILLA_OPTION", "PARENT_ACTION"] = Field(alias="componentKind")
    option_type: Literal["DIGITAL", "CALL", "PUT"] | None = Field(default=None, alias="optionType")
    exercise_style: Literal["EUROPEAN", "AMERICAN", "BERMUDAN"] | None = Field(default=None, alias="exerciseStyle")
    condition_role: Literal[
        "COUPON_ELIGIBILITY",
        "AUTOCALL",
        "CAPITAL_PROTECTION",
        "CONSOLATION",
        "FINAL_REDEMPTION",
        "OPTION_PAYOFF",
    ] = Field(alias="conditionRole")
    observation_style: Literal["CONTINUOUS", "DISCRETE", "FINAL_ONLY"] | None = Field(default=None, alias="observationStyle")
    condition_operator: ConditionOperator = Field(alias="conditionOperator")
    condition_scope: ScheduleScope = Field(alias="conditionScope")
    underlying_reference_node_id: UUID | None = Field(default=None, alias="underlyingReferenceNodeId")
    underlying_label: str | None = Field(default=None, alias="underlyingLabel", max_length=500)
    participation: Decimal | None = None
    coupon_rate: Decimal | None = Field(default=None, alias="couponRate", ge=0)
    strike_value: Decimal | None = Field(default=None, alias="strikeValue", gt=0)
    strike_percent: Decimal | None = Field(default=None, alias="strikePercent", ge=0)
    observation_date: date = Field(alias="observationDate")
    payment_date: date = Field(alias="paymentDate")
    condition_level: Decimal | None = Field(default=None, alias="conditionLevel", ge=0)
    condition_lower_level: Decimal | None = Field(default=None, alias="conditionLowerLevel", ge=0)
    condition_upper_level: Decimal | None = Field(default=None, alias="conditionUpperLevel", ge=0)
    condition_lower_inclusive: bool = Field(default=True, alias="conditionLowerInclusive")
    condition_upper_inclusive: bool = Field(default=True, alias="conditionUpperInclusive")
    condition_level_basis: Literal["PCT_OF_INITIAL", "PCT_OF_STRIKE", "ABSOLUTE_LEVEL", "PCT_OF_PAR"] = Field(alias="conditionLevelBasis")
    payout_rate: Decimal | None = Field(default=None, alias="payoutRate", ge=0, le=100)
    action_code: Literal["PAY_COMPONENT", "REDEEM_PARENT", "PAY_CONSOLATION", "FINAL_REDEMPTION"] = Field(alias="actionCode")
    action_target: Literal["COMPOSITION", "PARENT"] = Field(alias="actionTarget")

    model_config = ConfigDict(populate_by_name=True)


class AutocallDraftRequest(BaseModel):
    """Complete, versioned draft payload sent by the autocall builder."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    effective_from: date = Field(alias="effectiveFrom")
    product_subtype: StructuredProductSubtype = Field(alias="productSubtype")
    issue_currency_id: UUID = Field(alias="issueCurrencyId")
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    guarantor_organisation_id: UUID | None = Field(default=None, alias="guarantorOrganisationId")
    counterparty_organisation_id: UUID | None = Field(default=None, alias="counterpartyOrganisationId")
    notional_amount: Decimal | None = Field(default=None, alias="notionalAmount", gt=0)
    scope: ScheduleScope
    observation_style: Literal["DISCRETE", "CONTINUOUS", "FINAL_ONLY"] = Field(alias="observationStyle")
    memory_mode: Literal["NONE", "CONDITIONAL_CATCH_UP", "ACCUMULATE_TO_REDEMPTION"] = Field(alias="memoryMode")
    final_payment_treatment: FinalPaymentTreatment | None = Field(default=None, alias="finalPaymentTreatment")
    calendar_id: UUID = Field(alias="calendarId")
    start_date: date = Field(alias="startDate")
    maturity_date: date = Field(alias="maturityDate")
    first_autocall_observation_date: date | None = Field(default=None, alias="firstAutocallObservationDate")
    frequency: Literal["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"]
    # ``frequency`` remains the backwards-compatible single-cadence field.
    # Phoenix may provide independent coupon and parent-observation cadences.
    coupon_frequency: Literal["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"] | None = Field(default=None, alias="couponFrequency")
    autocall_frequency: Literal["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"] | None = Field(default=None, alias="autocallFrequency")
    payment_lag_business_days: int = Field(default=0, alias="paymentLagBusinessDays", ge=0, le=30)
    coupon_rate: Decimal = Field(default=Decimal("0"), alias="couponRate", ge=0)
    coupon_barrier: Decimal = Field(default=Decimal("0"), alias="couponBarrier", ge=0)
    coupon_barrier_follows_autocall: bool = Field(default=True, alias="couponBarrierFollowsAutocall")
    autocall_barrier_start: Decimal = Field(default=Decimal("0"), alias="autocallBarrierStart", ge=0)
    autocall_barrier_step: Decimal = Field(default=Decimal("0"), alias="autocallBarrierStep")
    autocall_barrier_floor: Decimal = Field(default=Decimal("0"), alias="autocallBarrierFloor", ge=0)
    kip_barrier: Decimal = Field(default=Decimal("0"), alias="kipBarrier", ge=0)
    final_payoff_barrier: Decimal | None = Field(default=None, alias="finalPayoffBarrier", ge=0)
    consolation_lower_barrier: Decimal | None = Field(default=None, alias="consolationLowerBarrier", ge=0)
    include_kip: bool = Field(default=True, alias="includeKip")
    include_consolation: bool = Field(default=False, alias="includeConsolation")
    consolation_rate: Decimal | None = Field(default=None, alias="consolationRate", ge=0, le=100)
    range_observation_frequency: Literal["DAILY", "WEEKLY", "MONTHLY"] | None = Field(default=None, alias="rangeObservationFrequency")
    range_accrual_basis: Literal["OBSERVATION_COUNT", "CALENDAR_DAYS"] | None = Field(default=None, alias="rangeAccrualBasis")
    range_non_business_day_rule: Literal["BUSINESS_DAYS_ONLY", "CARRY_FORWARD_PREVIOUS", "CALENDAR_DAYS"] | None = Field(default=None, alias="rangeNonBusinessDayRule")
    range_lower_level: Decimal | None = Field(default=None, alias="rangeLowerLevel", ge=0)
    range_upper_level: Decimal | None = Field(default=None, alias="rangeUpperLevel", ge=0)
    range_coupon_rate_per_annum: Decimal | None = Field(default=None, alias="rangeCouponRatePerAnnum", ge=0)
    supertracker_participation_rate: Decimal | None = Field(default=None, alias="supertrackerParticipationRate", gt=0)
    supertracker_include_cap: bool = Field(default=False, alias="supertrackerIncludeCap")
    supertracker_cap_return: Decimal | None = Field(default=None, alias="supertrackerCapReturn", gt=0)
    underlyings: list[AutocallUnderlyingRequest] = Field(min_length=1, max_length=100)
    rows: list[AutocallScheduleRowRequest] = Field(min_length=1, max_length=5000)
    submission_mode: Literal["MANUAL", "AUTOMATED"] = Field(default="MANUAL", alias="submissionMode")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", min_length=1, max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


def validate_autocall_draft(request: AutocallDraftRequest | dict) -> AutocallDraftRequest:
    """Validate and normalise a browser draft before proposal persistence.

    ``RANGE`` is retained as an input compatibility alias for the existing UI,
    but the canonical graph uses SQL ``BETWEEN``.  Parent actions are required
    to be explicit and are never silently copied once per underlying.
    """

    if not isinstance(request, AutocallDraftRequest):
        request = AutocallDraftRequest.model_validate(request)

    if request.maturity_date < request.start_date:
        raise StructuredProductDraftError("Maturity date must be on or after start date")
    if request.maturity_date < request.effective_from:
        raise StructuredProductDraftError("Maturity date must be on or after effectiveFrom")
    first_autocall_date = request.first_autocall_observation_date or request.start_date
    if first_autocall_date < request.start_date or first_autocall_date > request.maturity_date:
        raise StructuredProductDraftError("First autocall observation must fall between the start and maturity dates")
    if request.autocall_barrier_step < 0 and request.autocall_barrier_floor > request.autocall_barrier_start:
        raise StructuredProductDraftError("Autocall barrier floor cannot exceed the starting barrier")

    underlying_ids = [underlying.reference_node_id for underlying in request.underlyings]
    if len(set(underlying_ids)) != len(underlying_ids):
        raise StructuredProductDraftError("Underlying reference nodes must be unique")
    if request.scope == "SINGLE" and len(underlying_ids) != 1:
        raise StructuredProductDraftError("SINGLE scope requires exactly one underlying")
    if request.scope in {"BEST_OF", "WORST_OF"} and len(underlying_ids) < 2:
        raise StructuredProductDraftError("BEST_OF and WORST_OF scopes require at least two underlyings")
    if request.scope in {"BASKET", "EACH_UNDERLYING"}:
        raise StructuredProductDraftError(
            f"{request.scope} scope is not supported until explicit weighting or per-underlying outcome terms are available"
        )

    normalised_underlyings = [
        underlying.model_copy(update={"fixing_date": underlying.fixing_date or request.start_date})
        for underlying in request.underlyings
    ]
    for underlying in normalised_underlyings:
        if underlying.fixing_date > request.maturity_date:
            raise StructuredProductDraftError("Initial fixing date must be on or before maturity date")
        if underlying.fixing_source == "MARKET_DATA" and not (
            underlying.market_data_observation_id or underlying.market_data_resolution_snapshot_id
        ):
            raise StructuredProductDraftError(
                "Market-data initial fixing requires observation or resolution snapshot provenance"
            )
        if underlying.fixing_source == "PROVIDER" and not (
            underlying.source_system_id or underlying.source_payload_id
        ):
            raise StructuredProductDraftError("Provider initial fixing requires source provenance")

    row_ids = [row.row_id for row in request.rows]
    if len(set(row_ids)) != len(row_ids):
        raise StructuredProductDraftError("Schedule rowId values must be unique")

    normalised_rows: list[AutocallScheduleRowRequest] = []
    consolation_rows = 0
    final_redemption_rows = 0
    for row in request.rows:
        operator = "BETWEEN" if row.condition_operator == "RANGE" else row.condition_operator
        row = row.model_copy(update={"condition_operator": operator})
        if row.underlying_reference_node_id is not None and row.underlying_reference_node_id not in set(underlying_ids):
            raise StructuredProductDraftError("Schedule row references an underlying not present in the draft")
        if row.observation_date < request.start_date or row.observation_date > request.maturity_date:
            raise StructuredProductDraftError("Schedule observation date must fall within the draft dates")
        if row.payment_date < row.observation_date:
            raise StructuredProductDraftError("Schedule payment date cannot precede observation date")

        if operator in {"BETWEEN", "OUTSIDE"}:
            if row.condition_lower_level is None or row.condition_upper_level is None:
                raise StructuredProductDraftError("Range condition requires lower and upper levels")
            if row.condition_upper_level <= row.condition_lower_level:
                raise StructuredProductDraftError("Range condition upper level must be above lower level")
        elif row.condition_level is None and row.condition_role != "OPTION_PAYOFF":
            raise StructuredProductDraftError("Scalar condition requires conditionLevel")

        if row.condition_role == "OPTION_PAYOFF":
            if row.row_kind != "COMPONENT" or row.component_kind not in {"DIGITAL", "VANILLA_OPTION"}:
                raise StructuredProductDraftError("OPTION_PAYOFF must be a DIGITAL or VANILLA_OPTION component")
            if row.condition_operator != "GE" or row.action_code != "PAY_COMPONENT":
                raise StructuredProductDraftError("OPTION_PAYOFF must be an unconditional PAY_COMPONENT row")

        if row.row_kind == "COMPONENT":
            if row.underlying_reference_node_id is None:
                raise StructuredProductDraftError("Component row requires an underlying reference node")
            if row.action_code != "PAY_COMPONENT" or row.action_target != "COMPOSITION":
                raise StructuredProductDraftError("Component row must pay its composition")
        else:
            if row.action_code == "PAY_COMPONENT" or row.action_target != "PARENT":
                raise StructuredProductDraftError("Parent action row must target the parent product")
            if row.underlying_reference_node_id is not None:
                raise StructuredProductDraftError("Parent action row must not duplicate an underlying reference")

        if row.action_code == "PAY_CONSOLATION":
            consolation_rows += 1
            if row.condition_role != "CONSOLATION":
                raise StructuredProductDraftError("Consolation action must use the CONSOLATION condition role")
            if operator != "BETWEEN" or row.payout_rate is None:
                raise StructuredProductDraftError("Consolation action requires a bounded range and payout rate")
            if not (0 <= row.payout_rate <= 100):
                raise StructuredProductDraftError("Consolation payout rate must be between 0 and 100 percent")
            if not row.condition_lower_inclusive or row.condition_upper_inclusive:
                raise StructuredProductDraftError("Consolation range must include the KIP barrier and exclude the final payoff barrier")

        if row.action_code == "FINAL_REDEMPTION":
            final_redemption_rows += 1
            if final_redemption_rows > 1:
                raise StructuredProductDraftError("Draft may contain only one FINAL_REDEMPTION action")
            if row.condition_role != "FINAL_REDEMPTION":
                raise StructuredProductDraftError("Final redemption must use the FINAL_REDEMPTION condition role")
            if row.observation_date != request.maturity_date:
                raise StructuredProductDraftError("Final redemption must occur at maturity")

        normalised_rows.append(row)

    kip_rows = [row for row in normalised_rows if row.condition_role == "CAPITAL_PROTECTION"]
    if request.include_kip:
        if len(kip_rows) != len(underlying_ids):
            raise StructuredProductDraftError(
                "includeKip requires exactly one CAPITAL_PROTECTION KIP component per underlying"
            )
        kip_underlying_ids = [row.underlying_reference_node_id for row in kip_rows]
        if any(underlying_id is None for underlying_id in kip_underlying_ids) or set(kip_underlying_ids) != set(underlying_ids):
            raise StructuredProductDraftError(
                "includeKip requires exactly one CAPITAL_PROTECTION KIP component per underlying"
            )
        if any(
            row.row_kind != "COMPONENT"
            or row.component_kind != "VANILLA_OPTION"
            or row.option_type != "PUT"
            or row.action_code != "PAY_COMPONENT"
            or row.action_target != "COMPOSITION"
            or row.condition_scope != request.scope
            for row in kip_rows
        ):
            raise StructuredProductDraftError(
                "Each KIP component must be a PUT composition row with the draft underlying scope"
            )
    elif kip_rows:
        raise StructuredProductDraftError("CAPITAL_PROTECTION KIP rows require includeKip")

    # A MIN/MAX reduction is only well-defined for one shared predicate.  If
    # a user edits one underlying's barrier independently, silently persisting
    # the group would make the evaluator choose between different meanings
    # (per-name barriers versus one worst/best-of test).  Keep this first slice
    # deterministic and fail closed; per-underlying thresholds can be added
    # later as a separately governed payoff shape.
    predicate_groups: dict[tuple[str, date, str, str], list[AutocallScheduleRowRequest]] = {}
    for row in normalised_rows:
        if row.condition_role in {"OPTION_PAYOFF", "FINAL_REDEMPTION"}:
            continue
        if row.condition_scope not in {"BEST_OF", "WORST_OF"}:
            continue
        predicate_groups.setdefault(
            (row.group_code, row.observation_date, row.condition_role, row.action_code),
            [],
        ).append(row)
    for grouped_rows in predicate_groups.values():
        if len(grouped_rows) < 2:
            continue
        signatures = {
            (
                row.condition_scope,
                row.condition_operator,
                row.condition_level_basis,
                row.condition_level,
                row.condition_lower_level,
                row.condition_upper_level,
                row.condition_lower_inclusive,
                row.condition_upper_inclusive,
            )
            for row in grouped_rows
        }
        if len(signatures) != 1:
            raise StructuredProductDraftError(
                "Best-of and worst-of condition groups require one shared predicate across all underlyings"
            )

    include_consolation = request.include_consolation or request.product_subtype == "AUTOCALL_CONSOLATION"
    if include_consolation:
        if request.consolation_rate is None:
            raise StructuredProductDraftError("Consolation requires consolationRate")
        if request.final_payoff_barrier is None:
            raise StructuredProductDraftError("Consolation requires finalPayoffBarrier")
        consolation_lower_barrier = request.kip_barrier if request.include_kip else request.consolation_lower_barrier
        if not request.include_kip and consolation_lower_barrier is None:
            raise StructuredProductDraftError(
                "Consolation without a KIP leg requires consolationLowerBarrier"
            )
        if consolation_lower_barrier is None or request.final_payoff_barrier <= consolation_lower_barrier:
            lower_label = "KIP barrier" if request.include_kip else "consolation lower barrier"
            raise StructuredProductDraftError(f"Consolation final payoff barrier must be above the {lower_label}")
        if consolation_rows == 0:
            raise StructuredProductDraftError("Consolation subtype requires a PAY_CONSOLATION parent action")
        for row in normalised_rows:
            if row.action_code == "PAY_CONSOLATION" and row.condition_lower_level != consolation_lower_barrier:
                raise StructuredProductDraftError("Consolation range lower bound must match its configured lower barrier")
            if row.action_code == "PAY_CONSOLATION" and row.condition_upper_level != request.final_payoff_barrier:
                raise StructuredProductDraftError("Consolation range upper bound must equal the final payoff barrier")
    elif consolation_rows:
        raise StructuredProductDraftError("PAY_CONSOLATION rows require includeConsolation")

    composed_templates = {"VANILLA_SPREAD_KIP", "VANILLA_KIP", "DIGITAL_KIP"}
    if request.product_subtype in composed_templates:
        if request.include_consolation or consolation_rows:
            raise StructuredProductDraftError("Composed option templates do not support consolation actions")
        if not request.include_kip:
            raise StructuredProductDraftError("Composed option templates require the KIP component")
        option_payoff_rows = [row for row in normalised_rows if row.condition_role == "OPTION_PAYOFF"]
        kip_rows = [row for row in normalised_rows if row.condition_role == "CAPITAL_PROTECTION"]
        expected_option_count = 2 if request.product_subtype == "VANILLA_SPREAD_KIP" else 1
        if len(option_payoff_rows) != expected_option_count:
            raise StructuredProductDraftError(
                f"{request.product_subtype} requires exactly {expected_option_count} OPTION_PAYOFF component rows"
            )
        if not kip_rows:
            raise StructuredProductDraftError("Composed option templates require a CAPITAL_PROTECTION KIP row")
        if request.product_subtype == "DIGITAL_KIP" and any(row.component_kind != "DIGITAL" or row.option_type != "DIGITAL" for row in option_payoff_rows):
            raise StructuredProductDraftError("DIGITAL_KIP requires a DIGITAL option payoff row")
        if request.product_subtype == "DIGITAL_KIP" and any(row.payout_rate is None for row in option_payoff_rows):
            raise StructuredProductDraftError("DIGITAL_KIP requires an explicit digital payout rate")
        if request.product_subtype != "DIGITAL_KIP" and any(row.component_kind != "VANILLA_OPTION" or row.option_type not in {"CALL", "PUT"} for row in option_payoff_rows):
            raise StructuredProductDraftError("Vanilla composed templates require CALL or PUT option payoff rows")
        if request.product_subtype == "VANILLA_SPREAD_KIP":
            option_types = {row.option_type for row in option_payoff_rows}
            if len(option_types) != 1:
                raise StructuredProductDraftError("VANILLA_SPREAD_KIP requires both payoff legs to use the same option type")
            participations = [row.participation for row in option_payoff_rows]
            if any(value is None or value == 0 for value in participations) or not (any(value > 0 for value in participations if value is not None) and any(value < 0 for value in participations if value is not None)):
                raise StructuredProductDraftError("VANILLA_SPREAD_KIP requires at least one long and one short signed option leg")

    if request.product_subtype == "RANGE_ACCRUAL":
        if request.include_consolation or consolation_rows:
            raise StructuredProductDraftError("Range accrual does not support consolation actions")
        if request.include_kip:
            raise StructuredProductDraftError("Range accrual does not use a KIP component in this onboarding slice")
        if request.range_observation_frequency is None:
            raise StructuredProductDraftError("Range accrual requires rangeObservationFrequency")
        if request.range_accrual_basis is None:
            raise StructuredProductDraftError("Range accrual requires rangeAccrualBasis")
        if request.range_non_business_day_rule is None:
            raise StructuredProductDraftError("Range accrual requires rangeNonBusinessDayRule")
        if request.range_lower_level is None or request.range_upper_level is None:
            raise StructuredProductDraftError("Range accrual requires range lower and upper levels")
        if request.range_upper_level <= request.range_lower_level:
            raise StructuredProductDraftError("Range accrual upper level must be above the lower level")
        if request.range_coupon_rate_per_annum is None:
            raise StructuredProductDraftError("Range accrual requires rangeCouponRatePerAnnum")
        range_rows = [row for row in normalised_rows if row.condition_role == "COUPON_ELIGIBILITY"]
        if not range_rows:
            raise StructuredProductDraftError("Range accrual requires coupon eligibility rows")
        for row in range_rows:
            if row.row_kind != "COMPONENT" or row.component_kind != "DIGITAL" or row.option_type != "DIGITAL":
                raise StructuredProductDraftError("Range accrual coupon rows must be DIGITAL components")
            if row.condition_operator != "BETWEEN":
                raise StructuredProductDraftError("Range accrual coupon rows require a bounded BETWEEN condition")
            if row.condition_lower_level != request.range_lower_level or row.condition_upper_level != request.range_upper_level:
                raise StructuredProductDraftError("Range accrual row bounds must match the range terms")
        if final_redemption_rows != 1:
            raise StructuredProductDraftError("Range accrual requires exactly one FINAL_REDEMPTION action")

    if request.product_subtype == "SUPERTRACKER":
        if request.include_consolation or consolation_rows:
            raise StructuredProductDraftError("Supertracker does not support consolation actions")
        if request.scope != "SINGLE" or len(underlying_ids) != 1:
            raise StructuredProductDraftError("The first supertracker slice requires one underlying with SINGLE scope")
        if request.supertracker_participation_rate is None or request.supertracker_participation_rate <= 0:
            raise StructuredProductDraftError("Supertracker requires a positive supertrackerParticipationRate")
        if request.supertracker_include_cap and request.supertracker_cap_return is None:
            raise StructuredProductDraftError("A capped supertracker requires supertrackerCapReturn")
        if not request.supertracker_include_cap and request.supertracker_cap_return is not None:
            raise StructuredProductDraftError("supertrackerCapReturn is only valid when supertrackerIncludeCap is true")
        option_payoff_rows = [row for row in normalised_rows if row.condition_role == "OPTION_PAYOFF"]
        if len(option_payoff_rows) != (2 if request.supertracker_include_cap else 1):
            raise StructuredProductDraftError("Supertracker requires one upside call and an optional second cap call")
        if any(row.component_kind != "VANILLA_OPTION" or row.option_type != "CALL" for row in option_payoff_rows):
            raise StructuredProductDraftError("Supertracker payoff rows must be vanilla CALL components")
        positive_rows = [row for row in option_payoff_rows if row.participation is not None and row.participation > 0]
        negative_rows = [row for row in option_payoff_rows if row.participation is not None and row.participation < 0]
        if len(positive_rows) != 1:
            raise StructuredProductDraftError("Supertracker requires a positive leveraged upside component")
        if positive_rows[0].strike_percent != Decimal("100"):
            raise StructuredProductDraftError("Supertracker upside call must be struck at 100% of the initial fixing")
        if request.supertracker_include_cap:
            if len(negative_rows) != 1:
                raise StructuredProductDraftError("A capped supertracker requires one negative cap call component")
            if negative_rows[0].participation != -positive_rows[0].participation:
                raise StructuredProductDraftError("Supertracker cap call must use the same absolute participation as the upside call")
            expected_cap_strike = Decimal("100") + (request.supertracker_cap_return or Decimal("0"))
            if negative_rows[0].strike_percent != expected_cap_strike:
                raise StructuredProductDraftError("Supertracker cap call strike must equal 100% plus supertrackerCapReturn")
        elif negative_rows:
            raise StructuredProductDraftError("An uncapped supertracker cannot contain a negative cap call component")
        kip_rows = [row for row in normalised_rows if row.condition_role == "CAPITAL_PROTECTION"]
        if request.include_kip:
            if len(kip_rows) != 1:
                raise StructuredProductDraftError("Supertracker includeKip requires exactly one CAPITAL_PROTECTION PUT component")
            kip_row = kip_rows[0]
            if kip_row.component_kind != "VANILLA_OPTION" or kip_row.option_type != "PUT":
                raise StructuredProductDraftError("Supertracker KIP must be a vanilla PUT component")
        elif kip_rows:
            raise StructuredProductDraftError("A supertracker without includeKip cannot contain a CAPITAL_PROTECTION component")
        if final_redemption_rows != 1:
            raise StructuredProductDraftError("Supertracker requires exactly one FINAL_REDEMPTION action")

    final_payment_treatment = (
        request.final_payment_treatment or "PAY_SEPARATELY"
        if request.memory_mode != "NONE"
        else None
    )

    return request.model_copy(update={
        "include_consolation": include_consolation,
        "underlyings": normalised_underlyings,
        "rows": normalised_rows,
        "first_autocall_observation_date": first_autocall_date,
        "coupon_frequency": request.coupon_frequency or request.frequency,
        "autocall_frequency": request.autocall_frequency or request.frequency,
        "final_payment_treatment": final_payment_treatment,
    })
