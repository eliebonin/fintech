# Structured-product terms, components, and coupon memory

This note describes the implemented contractual-data slice for autocalls,
Phoenix/Athena products, range accruals, trackers, and similar structured
products. It is intentionally not a pricing or payoff-calculation engine.

## Versioned parent terms

`secm.structured_product_terms` is one effective-dated version of the parent
structured-product contract. Its primary key is `structured_product_terms_id`;
`instrument_node_id` remains the stable economic instrument identity and is
unique with `version_no`. `is_current`, effective dates, and
`supersedes_terms_id` make the current and historical versions easy to query.
A correction or legal amendment creates a new version and a new contractual
graph. It does not edit a graph already used by a trade or valuation snapshot.

The terms row carries the product subtype, optional description, and the
default `underlying_scope` (`SINGLE`, `BEST_OF`, `WORST_OF`, `BASKET`, or
`EACH_UNDERLYING`). Condition groups may override that default for a particular
observation. Source-payload lineage is retained through `source_payload_id`.
The common `secm.instrument_dates` row remains the authority for singular
effective, maturity, expiry, and settlement dates; recurring observations and
payments use schedule tables. The onboarding form's terms-effective date is
therefore distinct from the first observation date. It is the effective date
of this terms version, not an instruction to move the observation schedule.
The first fixing date is stored separately on each
`structured_product_initial_fixing` row, and each coupon/action may carry its
own payment or settlement date.

## Composition semantics

`secm.instrument_composition` describes the parent-to-child contractual graph.
Each row is an occurrence of a child component and has:

* `component_sequence`, unique within the parent terms version;
* `composition_value`, a numeric signed value;
* `composition_value_kind`: `SIGNED_MULTIPLIER`, `PERCENT_WEIGHT`, `QUANTITY`,
  or `NOTIONAL_AMOUNT`;
* effective validity and optional terms/source lineage.

`SIGNED_MULTIPLIER` is the normal option-package meaning: `+1` is long, `-1`
is short, and a magnitude such as `1.2` is leverage/participation. It replaces
the ambiguous legacy `composition_rate` name. `PERCENT_WEIGHT` is for a
weighted basket where the stored value is percentage points (for example, 25
means 25%). The kind tells downstream services how to interpret the number;
the database does not infer semantics from magnitude.

`secm.structured_product_component_terms` supplies payoff details for one
composition occurrence: component kind/style, payout amount or rate, payout
currency/basis, payment timing, schedule, and source lineage. It is suitable
for digital coupon options, calls, puts, caps, KIPs, and other explicitly
contractual children without creating a separate daily instrument for every
observation.

## First composed-option templates in the onboarding UI

The first composed-option slice uses the same parent graph rather than adding
new structural node types. Each submission creates one structured-product
parent and a fresh, non-tradable child option identity for every component row.
The UI currently exposes three governed archetype/template values:

| Template | Payoff components | Required shape |
|---|---|---|
| `VANILLA_SPREAD_KIP` | Two vanilla option legs plus one KIP leg | Exactly two `OPTION_PAYOFF` rows, normally signed `+1` long and `-1` short, plus a `CAPITAL_PROTECTION` row. |
| `VANILLA_KIP` | One vanilla option leg plus one KIP leg | One `OPTION_PAYOFF` row (`CALL` or `PUT`) plus a `CAPITAL_PROTECTION` row. |
| `DIGITAL_KIP` | One digital cash payout plus one KIP leg | One `OPTION_PAYOFF` row with `component_kind = DIGITAL` and a payout rate, plus a `CAPITAL_PROTECTION` row. |

The onboarding validator fails closed on the template shape: a spread must have
one positive and one negative signed leg using the same vanilla option type;
the digital template must supply a payout rate between 0 and 100 percentage
points; and a `SINGLE` scope cannot contain multiple underlying references.
These are shape checks, not a pricing or suitability decision.

The spread's signed multipliers are composition values, not buy/sell trade
directions. A magnitude such as `1.5` remains available for future ratio or
leveraged variants. The digital component is not treated as a new vanilla
`option_type`: its child option record remains `CALL`/`PUT` for the current
option contract vocabulary, while `structured_product_component_terms` marks
`component_kind = DIGITAL`, `payoff_style = RATE_OF_NOTIONAL`, and the explicit
cash payout rate. This keeps digital semantics out of the vanilla option type.

An `OPTION_PAYOFF` row is an unconditional final payoff component. It belongs
to a `FINAL_VALUATION` schedule and a condition group with `logical_operator =
NONE`; no dummy barrier rule is created for it. A KIP is a distinct component
with its own child option terms and a `CAPITAL_PROTECTION` barrier rule. Its
underlying is the child option's exact underlying reference, and the group may
be `CONTINUOUS` (the UI default) or `FINAL_ONLY` (European/maturity-only). A
continuous KIP has no schedule event; the later outcome service must evaluate
the barrier path and record the trigger state. The settlement date remains an
action/component value and may differ from the observation date.

This separation follows the market vocabulary: CME describes a call spread as
a long call at one strike and a short call at another; Investor.gov describes
a binary option as a yes/no cash-or-nothing payoff with no right to buy or
sell the underlying; and ISDA's barrier documentation defines knock-in options
as becoming effective after a specified barrier event. See [CME's options
strategy guide](https://www.cmegroup.com/articles/files/2022/25-proven-strategies.pdf),
[Investor.gov's binary-options glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/binary-options),
and [ISDA's barrier-option supplement overview](https://www.isda.org/book/supplements-to-the-1998-fx-and-currency-option-definitions/).

An SEC-filed structured-products discussion provides a useful implementation
cross-check: one RCN example is described from the investor perspective as a
par-bond component plus a short European knock-in put. That is consistent with
keeping the KIP as a separate signed component and not hiding its barrier inside
the vanilla option's ordinary strike/type fields. See the [SEC proceeding and
embedded-option discussion](https://www.sec.gov/file/34-78958pdf).

The current slice intentionally does not price the payoff, calculate barrier
crossings, or generate a monitoring calendar for continuous KIP. Those remain
lifecycle/outcome concerns. It also does not model a note wrapper as a
separate bond component unless the legal term sheet explicitly supplies one;
the parent structured-product instrument remains the booked economic product.

For this onboarding slice, generated child options use
`strike_basis = PERCENT_OF_INITIAL`. The numeric `strike_value` is stored in
percentage points (`100` means 100% of the selected initial fixing), and
`option_terms.strike_reference_initial_fixing_id` points to the immutable
accepted fixing that supplies the anchor. This makes a child option's strike
traceable without copying a resolved absolute price into the child terms. A
non-structured option may continue to use `ABSOLUTE`, `INDEX_POINTS`,
`FX_RATE`, or `PERCENT_OF_SPOT` as appropriate.

When a stock split, reverse split, bonus issue, special dividend, or similar
corporate action changes an option's contractual strike, the terms row is not
edited in place. The lifecycle/corporate-action process adds
one `secm.option_strike_adjustment` row with the affected option-terms version,
corporate-action event, effective date, pre/post strike values, multiplicative
factor, optional adjusted fixing, correction revision, status, and
source-payload lineage. A corrected factor supersedes the previous adjustment through
`supersedes_adjustment_id`. The table is an audit/correction hook: it does not
yet apply factors automatically or rewrite historical market-data observations.
If a corporate action also changes the deliverable quantity, the existing
versioned `instrument_contract_unit_terms` record must be corrected in the same
controlled lifecycle workflow.

## Condition groups and barriers

Condition groups, atomic rules, and actions are defined in the authoritative
[condition-group note](26-structured-product-condition-groups.md). Groups,
rules, and actions all resolve through a specific parent terms version.
Component barriers belong to the component owner; parent lifecycle barriers
such as autocall redemption belong to the parent. A pure autocall event does
not require a dummy option instrument.

Actions can target an exact `instrument_composition_id` and can carry payout
amount/rate/currency, payout basis, payment timing, and payment schedule. An
aggregate best-/worst-of coupon or KIP action instead targets the parent and
is emitted once; the underlying-specific child rows remain condition members,
not duplicate payments. `condition_group_action.payout_multiplicity` records
whether the action is `ONCE_PER_PARENT`, `PER_UNDERLYING`, or
`PER_COMPONENT`. KIP-enabled drafts contain one fresh PUT child per
underlying; scope/aggregation determines whether those children feed one
aggregate outcome or separate component outcomes. This makes “pay this
coupon/KIP result” distinct from “redeem the parent” and avoids applying a
single event once per underlying by accident.

## Coupon programme and periods

`secm.structured_product_coupon_programme` defines the product-level coupon
behaviour for one terms version:

* `payment_mode`: `PERIODIC`, `ON_AUTOCALL`, or `ON_MATURITY`;
* `memory_mode`: `NONE`, `CONDITIONAL_CATCH_UP`, or
  `ACCUMULATE_TO_REDEMPTION`;
* default rate or amount (mutually exclusive), currency, payout basis,
  payment schedule, optional default eligibility group, and final-payment
  treatment. `final_payment_treatment` is governed as `PAY_SEPARATELY`,
  `INCLUDE_IN_REDEMPTION`, or `FORFEIT`; it describes accrued-memory treatment
  at maturity and is not a barrier-level flag. It is applicable only when
  `memory_mode` is not `NONE`; otherwise the API and database store `NULL`.

`secm.structured_product_coupon_period` contains ordered period-specific
observation/payment information. A period may override the programme default
rate or amount and may point to its own eligibility condition group. Its
`memory_eligible` flag describes whether a missed coupon can be remembered;
it does not itself perform catch-up. A stored `coupon_rate` uses percentage
points: `5` means 5%, not `0.05`.

Examples:

* Phoenix: periodic coupon programme, usually
  `CONDITIONAL_CATCH_UP`, with one eligibility group per coupon observation
  period. Coupon and autocall schedules may have different frequencies.
* Athena: premium/coupon programme commonly uses
  `ACCUMULATE_TO_REDEMPTION`; the autocall action pays the accumulated amount.
* Range accrual: a period references a range condition group; the later
  calculation service derives the in-range observation proportion.

The onboarding UI treats these as profiles, not new economic-instrument
tables. Athena defaults to a zero autocall-barrier step (constant barrier)
and Phoenix starts with memory `NONE`; the operator must opt into
`CONDITIONAL_CATCH_UP` or `ACCUMULATE_TO_REDEMPTION` when the legal term sheet
provides it. The profile does not replace the persisted coupon programme,
periods, condition groups, or actions; those remain the contractual source of
truth.

### Phoenix research basis

The subtype/profile decision is based on the following reviewed sources:

* [SG Forge Phoenix](https://www.sgforge.com/product-structured-products-phoenix/)
  separates the conditional coupon barrier, autocall barrier, and maturity
  protection barrier and illustrates coupon payment before redemption.
* [RBC Phoenix AutoCallable memory supplement](https://www.sec.gov/Archives/edgar/data/1000275/000095010325003216/dp226084_424b2-jpmeln565.htm)
  defines a memory feature in which an unpaid coupon may be paid once on a
  later eligible coupon date or at maturity/early redemption.
* [SSPA Lab](https://sspa.ch/en/lab/) describes an autocall trigger that
  requires all underlyings to meet the condition, supporting `ALL` Boolean
  groups for worst-of products.
* [Rothschild glossary](https://www.rothschildandco.com/fr-fr/banque-privee/gestion-financiere/produits-structures/glossaire-produits-structures/)
  defines Phoenix by its conditional coupons during the life of the product,
  not by mandatory memory.

These sources also show that non-call periods, separate coupon/call dates,
averaging, and physical settlement can be contractual variations. They remain
explicit future terms rather than hidden subtype assumptions. A later outcome
service must maintain coupon arrears so a remembered coupon cannot be paid
twice.

### Independent coupon and autocall schedules

The onboarding/API contract accepts the legacy single `frequency` plus optional
`couponFrequency` and `autocallFrequency`. Missing new fields inherit the
legacy value. The Phoenix UI presents these as explicit yearly cadences (for
example, `12 / year · Monthly` coupons and `4 / year · Quarterly` autocall
observations).

The schedule projection takes the union of both date sets. Coupon digital
components exist only on coupon dates; parent redemption actions and their
step-down sequence exist only on autocall dates. Coupon eligibility inherits
the autocall barrier in force at each coupon date by default; an explicit
`couponBarrierFollowsAutocall=false` term permits a fixed coupon barrier.
Approval materialises these
as separate `COUPON_OBSERVATION` and `AUTOCALL_OBSERVATION` schedules and
stores a `MAIN_COUPON` programme with dated coupon periods. KIP and maturity
consolation remain attached to the maturity/autocall schedule. This is a
schedule distinction, not a new instrument subtype.

The onboarding form treats the autocall floor as a step-down-generation
parameter: it is shown only when the step is non-zero. The final payoff barrier
is shown only for `AUTOCALL_CONSOLATION`, where it defines the exclusive upper
bound of the maturity consolation range. If KIP is included, its barrier is the
inclusive lower bound. If KIP is omitted, the operator must provide the
independent `consolationLowerBarrier`; this creates the parent range without
inventing a capital-protection component.

The Phoenix contract stores `structured_product_terms.first_autocall_observation_date`.
This is a
non-call boundary for early parent redemption, not a global observation start:
coupon periods before that date remain valid. Early parent calls use
`REDEEM_PARENT`; maturity uses a separate `FINAL_REDEMPTION` action. The latter
is persisted as `condition_group_action.action_type = TERMINATE_PARENT` with a
`NONE` condition group and no `barrier_rule`; the lifecycle service must execute
it only when no earlier parent redemption and no mutually exclusive maturity
branch (such as consolation) has terminated or paid out the product.
This belongs on the structured-product terms version rather than the generic
instrument-date row because it is a payoff-specific eligibility boundary.

Each generated row receives a lag-based payment date. A manually edited outcome
date is retained on the specific coupon period or condition-group action via
`payment_date`; it overrides the schedule event's default payment date. This
keeps one shared observation schedule while allowing contractual settlement
exceptions per outcome.

## Lifecycle boundary and intentional deferrals

The schema now captures enough terms to validate and display a contractual
graph, but it does not yet store calculated coupon ledgers, condition outcomes,
cashflow projections, or pricing-engine state. Those belong in a future
valuation/outcome domain with market-data snapshots and calculation-version
lineage. This is deliberately outside the instrument-creation workflow: the
creation process records what the contract says, while the lifecycle process
later records what happened for each approved terms version and observation.
Terms amendments will require a controlled graph validation and replay policy
before becoming active.

The lifecycle service will be responsible for condition evaluation, coupon
arrears, early termination, settlement cashflows, and reconciliation. It must
create new outcome versions for corrections rather than editing historical
outcomes or contractual terms.

## Range accrual and supertracker implementation slice

The first onboarding UI slice now has focused terms rows for the two remaining
archetypes. This keeps product-specific economics out of free-text labels while
avoiding a new pricing engine.

### Range accrual

`secm.structured_product_range_accrual_terms` stores the annualised coupon
rate, lower/upper percentage-of-initial range, observation frequency,
accrual denominator (`OBSERVATION_COUNT` or `CALENDAR_DAYS`), and the explicit
non-business-day rule. The parent graph still uses coupon periods and bounded
`COUPON_ELIGIBILITY` condition groups. The UI deliberately renders one row per
coupon period; it does not create a child digital instrument per daily fixing.
The generic coupon-programme and coupon-period `coupon_rate` fields remain
NULL for this subtype because those fields mean a per-period rate; the
annualised rate is read only from the focused range-terms row. The later
lifecycle service may materialise detailed observation events and must apply
the stored convention when calculating the qualifying fraction.

This follows the `N / D` convention in the [SEC range-accrual supplement](https://www.sec.gov/Archives/edgar/data/9631/000119312512090184/d300603dsuppl.htm),
which also demonstrates that non-business-day and ending-fixing rules are
contractual terms rather than safe defaults.

### Supertracker

`secm.structured_product_supertracker_terms` stores the positive participation
multiplier and optional underlying-return cap. The graph contains a long final
call payoff and, when capped, a short call at `100% + cap return` with the same
absolute multiplier. An optional KIP/downside component remains separate, and
principal is represented by a parent `FINAL_REDEMPTION` action. The first UI
slice requires `SINGLE` scope; a true worst-of or basket payoff needs a
dedicated reference basket/payoff node rather than silently paying one option
per underlying.

The shape is consistent with [Barclays' Barrier Supertrack filing](https://www.sec.gov/Archives/edgar/data/312070/000191870426015925/form424b2.htm)
and its [earlier Supertrack term sheet](https://www.sec.gov/Archives/edgar/data/312070/000148105724008934/formfwp.htm),
which state the final underlying test, leverage factor, barrier branch, and
principal settlement separately. The [SEC investor bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-76)
also describes participation and capped maximum returns as independent
contractual features.

The UI/API validators fail closed on missing range conventions, invalid bounds,
missing final redemption, or an incomplete capped call pair. Pricing, averaging,
lookback, issuer-call, market-disruption, and full daily outcome calculations
remain deferred.
