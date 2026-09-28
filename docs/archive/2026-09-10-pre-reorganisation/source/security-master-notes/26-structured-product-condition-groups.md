# Structured-product condition groups

Structured-product conditions are modelled as first-class Boolean groups. A
group represents one contractual observation event and produces one result;
its actions therefore execute once, rather than once per underlying. The
tables are contractual reference data only. They do not calculate market
outcomes or cashflows.

## Ownership and versioning

`secm.structured_product_terms` is the versioned contractual anchor. A
condition group belongs to one `structured_product_terms_id`, not merely to a
stable parent instrument. A legal amendment creates a new terms version and a
new condition/composition graph; historical versions remain queryable and are
never overwritten. `structured_product_terms.default_underlying_scope` is a
convenience default (`SINGLE`, `BEST_OF`, `WORST_OF`, `BASKET`, or
`EACH_UNDERLYING`); the group stores its own explicit `underlying_scope` when
the condition differs from the product default.

## Condition group

`secm.structured_product_condition_group` contains one logical test for one
observation context:

* a product-local `group_code`;
* `observation_style`: `DISCRETE`, `CONTINUOUS`, or `FINAL_ONLY`;
* an optional `schedule_event_id`, mandatory for `DISCRETE` and `FINAL_ONLY`;
* `logical_operator`: `ALL`, `ANY`, or `NONE`;
* `underlying_scope` for the contractual scope; and
* `underlying_aggregation`: `SINGLE`, `MIN`, `MAX`, or `NONE`, recording how
  the underlying measurements are reduced before the predicate is applied;
* an `evaluation_sequence` for deterministic ordering when several groups
  apply on the same event; and
* status and source-payload lineage.

`ALL`, `ANY`, and `NONE` are the only implemented operators. `NONE` is used by
the maturity final-redemption gate and by a supported multi-underlying group
whose measurements are reduced to one scalar before its predicate is applied.
For the latter, the lifecycle service must use `underlying_aggregation`; it
must not reinterpret the rows as an `ANY`/`ALL` Boolean fold. The final-redemption
gate still checks that no earlier parent redemption or mutually exclusive
maturity branch has terminated or paid out the product. Count thresholds,
nested Boolean groups, and a general expression tree remain deferred.

For the supported multi-underlying slice, the two fields are deliberately
explicit rather than inferred from a marketing label:

| Scope | Aggregation | Generated operator | Meaning |
|---|---|---|---|
| `SINGLE` | `SINGLE` | `ALL` | Evaluate the one selected underlying. |
| `WORST_OF` | `MIN` | `NONE` | Reduce the normalised performances to the minimum; apply the one shared predicate to that scalar. |
| `BEST_OF` | `MAX` | `NONE` | Reduce the normalised performances to the maximum; apply the one shared predicate to that scalar. |
| unconditional gate | `NONE` | `NONE` | No underlying predicate; the lifecycle state still controls eligibility. |

`logical_operator` remains available for groups that genuinely combine
independent Boolean predicates. For the first-slice multi-underlying groups it
is `NONE`, because the evaluator reduces the selected underlying measurements
once and then applies the shared predicate to that scalar; it must not apply
the predicate once per underlying and then reduce a second time.
`underlying_aggregation` is the authoritative economic selector and makes the
intended reduction visible to downstream services. In this
first slice every underlying in one `MIN`/`MAX` group must share the same
operator, level basis, bounds, and inclusivity. A
draft with per-underlying thresholds is rejected rather than silently changing
the product from a best-/worst-of test into a different payoff. Weighted
`BASKET` and `EACH_UNDERLYING` outcomes remain deferred and are rejected by the
onboarding validator until their weights and outcome semantics are modelled.

For composed-option templates, `OPTION_PAYOFF` is an explicit unconditional
component role. Its group uses `logical_operator = NONE` and has no
`barrier_rule`; the component still has a final valuation schedule and a
`PAY_COMPONENT` action. A KIP remains a normal component condition with a
`CAPITAL_PROTECTION` role and a `LE` barrier rule. Its group-level observation
style is carried from the draft row, so continuous KIP can be represented
without pretending that the maturity schedule is the monitoring schedule.

## Atomic barrier rule

Every `secm.barrier_rule` belongs to exactly one group. It records one
underlying-specific predicate:

* `owner_reference_node_id`: the component or parent supplying the contractual
  context;
* `underlying_reference_node_id`: the resolved node being tested;
* `condition_sequence` within the group;
* comparison semantics (`GE`, `GT`, `LE`, `LT`, `BETWEEN`, or `OUTSIDE`);
* level basis and lower/upper levels;
* `lower_bound_inclusive` and `upper_bound_inclusive` flags (required for
  ranges; scalar checks are validated against their operator);
* the underlying measure; and
* status and source-payload lineage.

The underlying reference is stored explicitly for deterministic evaluation
and audit. For a component barrier it must agree with the underlying in the
child option/component terms (or be rejected by validation). For a parent
barrier it is resolved from the parent's explicit composition/reference
entries. This avoids a duplicated *business* underlying field while retaining
the exact node used by a historical resolver. A rule has no action or
observation-schedule fields.

## Group actions

`secm.condition_group_action` represents one ordered consequence of a
satisfied group. It contains:

* the owning group and positive `execution_sequence`;
* an action type such as `PAY_COMPONENT`, `PAY_CONSOLATION`,
  `REDEEM_PARENT`, `TERMINATE_PARENT`, `CANCEL_FUTURE_COMPONENTS`, or
  `ACTIVATE_CAPITAL_PROTECTION`;
* `target_scope` (`COMPONENT` or `PARENT`);
* an explicit target reference node, and for component actions an optional
  exact `target_composition_id`;
* optional payout amount/rate/currency, payout basis, payment timing, payment
  schedule, and action-specific `payment_date`; and
* status and source-payload lineage.

The target composition link is what makes an independent option-leg payment
unambiguous when a parent contains several similar children. For a
best-/worst-of coupon or KIP group, the child rows are underlying-specific
condition members but the economic payout is one aggregate parent event; its
`PAY_COMPONENT` action therefore targets the parent and carries the
`ONCE_PER_PARENT` multiplicity. A single-underlying KIP remains a
component-targeted action.

`condition_group_action.payout_multiplicity` makes the payout cardinality
machine-readable:

| Value | Meaning |
|---|---|
| `ONCE_PER_PARENT` | One aggregate outcome for the structured-product parent. Used for parent actions and best-/worst-of coupon/KIP groups. |
| `PER_UNDERLYING` | One outcome for each underlying in an explicitly governed per-underlying product shape. |
| `PER_COMPONENT` | One outcome for each explicit composition-targeted action, such as an independent option leg or a single-underlying KIP. |

The API derives this field from the governed condition scope, role, and action
code; it is not a second free-text UI value. A KIP-enabled draft must contain
exactly one fresh `CAPITAL_PROTECTION` PUT component for every draft
underlying, with the same scope as the parent. Duplicate, missing, non-PUT,
or mismatched-scope KIP rows are rejected before persistence. The child rows
keep their individual underlying, strike anchor, and corporate-action
traceability; the condition group controls whether those children are reduced
to one parent result or evaluated separately.

## Component versus parent barriers

The owner determines the scope of the event:

* A **component barrier** controls a child payoff component, for example a
  coupon digital option or a knock-in put. Its resolved underlying comes from
  that child component's option terms.
* A **parent barrier** controls the lifecycle or parent-level payoff, for
  example an autocall redemption, final capital-protection test, or
  cancellation of future components. Its resolved underlying is represented by
  the parent's explicit composition/reference entries.

Do not create a dummy “autocall option” solely to provide a foreign key when
the event has no separate economics. Attach the rule to the parent product and
use an action target of `PARENT`.

The generated maturity row is a distinct `FINAL_REDEMPTION` UI/API action. It
materialises as `TERMINATE_PARENT` on a `NONE` condition group, while early
eligible calls remain `REDEEM_PARENT`. A row-level settlement edit is stored
on `condition_group_action.payment_date` (or the coupon-period equivalent)
and overrides the schedule event's default payment date without changing the
observation calendar.

## Example

For a two-name 100% autocall on an observation date:

```text
Parent terms v1: WORST_OF
  Group AUTOCALL_OBS_1_AT_100: DISCRETE, aggregation MIN, operator NONE, 15 Jun 2027
    Rule 10: HSBC >= 100% of initial
    Rule 20: SAP  >= 100% of initial
    Predicate: min(HSBC, SAP) >= 100% of initial
    Action 10: PAY_COMPONENT, target parent, payment_rate = 5
               (5 percentage points; one aggregate coupon)
    Action 20: REDEEM_PARENT, target parent
```

The group evaluates once. If the aggregate predicate is true, the coupon
action and then the redemption action execute once, irrespective of the
number of names.

## Integrity rules

The schema enforces positive and unique group/member/action sequences, valid
operator and observation-style values, schedule/event consistency, comparison
level requirements, ordered level bounds, valid underlying scopes, and payout
value shapes. Terms-version, composition-membership, and child-option
underlying consistency are cross-table service validations.

## Deliberate deferrals

The model intentionally leaves the following to a later outcome/calculation
slice:

* market-data resolution and evaluated condition outcomes;
* coupon accrual, memory catch-up, and final cashflow calculation;
* count thresholds and nested Boolean expressions;
* a generic payoff graph/pricing engine; and
* full event-sourced correction/replay of contractual amendments.

Coupon programme/period rows, component payoff terms, and action payout
metadata are now stored so those later services have an unambiguous contract;
their calculation results are not stored in these reference tables.
