# Structured-product correction pass (2026-09-10)

This note records the small set of corrections made after reviewing the
autocall/Phoenix/structured-product builder. The changes keep the onboarding
slice contractual and auditable without introducing a payoff or pricing engine.

## Multi-underlying aggregation

The UI exposes only scopes that have an unambiguous first-slice meaning:
`SINGLE`, `BEST_OF`, and `WORST_OF`. The API rejects `BASKET` and
`EACH_UNDERLYING` until their weighting and per-underlying outcome contracts
are added.

Each persisted condition group stores both:

* `underlying_scope`, the business scope selected by the draft; and
* `underlying_aggregation`, the explicit reduction (`SINGLE`, `MAX`, `MIN`,
  or `NONE`).

Generated predicates use `ALL` for `SINGLE`. Multi-underlying groups use
`logical_operator = NONE`: worst-of reduces to the minimum and best-of to the
maximum, then applies the one shared predicate to that scalar. This is
important for downward KIP tests and bounded consolation ranges, where a
Boolean `ANY`/`ALL` shortcut would change the economics. All predicate
rows in one MIN/MAX group must share operator, level basis, bounds, and
inclusivity. A manually divergent row is rejected instead of being interpreted
as a different product.

For aggregate coupon-eligibility and capital-protection groups, the
underlying-specific component rows are condition members. Persistence emits
one parent-level `PAY_COMPONENT` action for a best-/worst-of group, so the
aggregate coupon or KIP result is not multiplied by the number of underlyings.
The graph still creates one fresh KIP PUT child per underlying. A
single-underlying KIP remains component-targeted.

`condition_group_action.payout_multiplicity` records the resulting cardinality
as `ONCE_PER_PARENT`, `PER_UNDERLYING`, or `PER_COMPONENT`. It is derived from
the governed scope/role/action combination. `BEST_OF` and `WORST_OF` reduce
the underlying measurements first and pay once; `EACH_UNDERLYING` is reserved
for a future governed per-name outcome shape. The API requires exactly one KIP
component for every underlying when KIP is enabled and rejects duplicates,
missing children, non-PUT components, or a mismatched scope.

## Maturity consolation without KIP

`AUTOCALL_CONSOLATION` normally uses the KIP barrier as the inclusive lower
bound and the final payoff barrier as the exclusive upper bound. When the
operator turns KIP off, the API requires the independent
`consolationLowerBarrier`. The schedule preview warns before submission and
the server remains authoritative. No capital-protection child is created in
that case; the result is a parent-level bounded action only.

## Dates and provisional schedule output

The terms-effective date is separate from the observation start date. Each
underlying has an explicit initial-fixing date, and each generated component or
parent action has an editable payment/settlement date. The current UI payment
dates are a provisional weekend-only preview. Approval must run the governed
calendar/session resolver and may retain a non-blocking correction warning for
an unusual date rather than silently changing the submitted draft.

## Percentage strikes and corporate actions

Generated structured-product child options use
`option_terms.strike_basis = PERCENT_OF_INITIAL`, with the percentage stored in
percentage points (`100` means 100%) and an FK to the immutable accepted
`structured_product_initial_fixing` row. This provides a direct audit path from
the child strike to the parent terms and its fixing evidence.

Stock splits and related actions do not mutate historical option terms or
fixings. The lifecycle process records an attributable
`secm.option_strike_adjustment` row containing the corporate action, effective
date, pre/post strike, factor, optional adjusted fixing, correction revision,
status, and source payload. A revision number is part of the uniqueness key so
an append-only correction can supersede an earlier row for the same action and
date without overwriting it. An initial-fixing FK is accepted only for
`PERCENT_OF_INITIAL` option terms. Automatic application of the factor and
full payoff/outcome replay remain deferred. If the action also changes the
contract deliverable or units, the lifecycle workflow creates a new
effective-dated `instrument_contract_unit_terms` row rather than mutating the
prior unit multiplier.

## Fields deliberately removed from the onboarding MVP

ISIN, SEDOL, investment wrapper, booking strategy, and other values that were
displayed but not persisted were removed from this page. Identifiers belong in the governed
identifier layer; booking/strategy data belongs in the trade/tenant domain.
Range accrual's annualised rate is stored only in
`structured_product_range_accrual_terms`, not in generic per-period coupon
fields. When coupon memory is `NONE`, final-payment treatment is persisted as
`NULL` because it is not applicable.

## Deferred choices

The following are intentionally not part of this correction pass:

* weighted baskets and explicit per-underlying payoff outcomes beyond the
  reserved `PER_UNDERLYING` contract;
* holiday-aware calendar calculation and date-roll policy in the approval
  service;
* automatic corporate-action strike adjustment and lifecycle payoff replay;
* condition-expression trees, nested groups, and threshold counts; and
* calculated coupon arrears, barrier outcomes, cashflows, and pricing.
