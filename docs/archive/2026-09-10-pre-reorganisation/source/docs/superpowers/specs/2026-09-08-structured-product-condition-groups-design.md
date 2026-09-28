# Structured-Product Condition Groups Design

## Goal

Represent a structured product as a versioned contractual graph: parent terms,
typed component occurrences, Boolean condition groups, atomic barrier rules,
and ordered consequences. One logical event must be evaluated and paid once,
even when it tests several underlyings.

## Scope and status

The schema and migration are implemented through Alembic revisions
`20260909_32` through `20260910_40`. The latest revisions make the
multi-underlying reduction explicit and add auditable percentage-strike
anchors/correction revisions. This slice is reference/contract data. It does
not calculate market outcomes, project cashflows, or price an exotic product.

The implementation includes:

* versioned `secm.structured_product_terms`;
* typed `secm.instrument_composition` rows with sequence and terms-version
  ownership;
* `secm.structured_product_component_terms` for component payoff details;
* `secm.structured_product_initial_fixing` for effective fixing values and
  market-data/provider provenance;
* `secm.structured_product_condition_group` with observation and Boolean
  semantics;
* atomic `secm.barrier_rule` members with explicit resolved underlyings and
  persisted lower/upper bound inclusivity;
* `secm.condition_group_action` with exact target composition and payout
  metadata; and
* coupon programmes and periods with eligibility and memory configuration.

The existing development database had records from earlier revisions, so the
hardening migration repairs keys and preserves those records where possible.
The demo loader is idempotent and can reconcile a legacy composition row.

The first UI slice is available at the structured-product onboarding route. It
is a draft/review projection: operations select the parent details, resolve
canonical reference nodes, enter initial fixings and payoff controls, and
generate grouped component rows before submission. It does not create approved
canonical records or price the product. The API stores a pending
`CREATE_STRUCTURED_PRODUCT` proposal; steward approval materialises the graph
in one transaction. The schedule preview groups rows by
observation event: composition rows retain the underlying-specific condition
members, while one aggregate `PAY_COMPONENT` parent action and one
`REDEEM_PARENT` action row are emitted for a best-/worst-of parent condition
group. Independent option-leg groups still target their exact composition.
Parent actions are deliberately not repeated once per underlying. KIP-enabled
drafts create one fresh PUT component per underlying for traceability, while
the group scope determines whether those children feed one aggregate parent
outcome or separate component outcomes. The persisted action records this
cardinality as `ONCE_PER_PARENT`, `PER_UNDERLYING`, or `PER_COMPONENT`.

The schedule review uses progressive disclosure for density. An observation
overview table is always shown first, with one comparison row per date. The
selected observation then shows a compact underlying-component matrix and a
separate parent-action section. A `Show contractual rows` control exposes the
raw component projection only when needed; `Show all observations` is an
explicit power-user action and is not the default. Reference-node UUIDs and
generated row IDs remain behind the `Show reference IDs` control. These are UI
presentation choices only: the generated graph and its stable row identities
are unchanged.

The first draft-editing slice is intentionally narrow. The selected-observation
contractual-row projection can edit condition levels, coupon rates on coupon
components, and component leg sides. The UI displays leg sides as `Long` or
`Short`, while the signed participation/multiplier remains the internal value
used for arithmetic and persistence. The UI wraps generated rows with a
`draftRowId`, `sourceRowId`, `rowState`, and dirty-field list; edits stay in a
client-side overlay and do not mutate generated rows. Draft validation checks
ownership of parent actions and component actions, resolved underlyings, and
numeric condition/payoff values. If a high-level generator input changes while
the draft is dirty, the UI warns and requires an explicit discard action before
using the regenerated baseline.

The current builder supports a maturity consolation action through the
dedicated `AUTOCALL_CONSOLATION` product-archetype choice. The subtype is a
governed taxonomy value below `AUTOCALL`, not a new structural node or
economic-instrument type. It is a parent-level `PAY_CONSOLATION` action with a
bounded condition rather
than a duplicated component for each underlying. When KIP is included, the
lower bound is the KIP barrier and is inclusive; when KIP is omitted, the
operator must provide an independent `consolationLowerBarrier`. The upper
bound is exclusive and is supplied as the explicit `finalPayoffBarrier` draft
field. The default payout is 50% of the configured maximum payoff. An earlier
parent autocall takes precedence and terminates the product, so the consolation
action cannot pay after an early redemption. The persisted action records its
payoff base as `PCT_OF_MAX_PAYOFF`; no capital-protection component is created
when KIP is disabled.

Athena and Phoenix use the same graph rather than introducing separate
instrument tables. The builder applies small, visible product profiles:

* `ATHENA` defaults the autocall barrier step to `0` and disables that field
  while selected, making the constant-barrier convention explicit. The
  generated rows still persist ordinary autocall barrier rules, so an Athena
  is queryable as the same economic structured-product model.
* `PHOENIX` leaves coupon memory at `NONE` until the user explicitly selects a
  memory mode from the term sheet. The memory behaviour is explained next to
  the field; the final-payment treatment control is shown only when memory is
  enabled.

Both profiles are UI defaults over `structured_product_coupon_programme`,
`structured_product_coupon_period`, condition groups, and actions. They do
not change the meaning of `composition_value` or create a separate
`athena_terms`/`phoenix_terms` table.

The Phoenix profile was checked against [SG Forge's Phoenix mechanism](https://www.sgforge.com/product-structured-products-phoenix/),
[an SEC-filed Phoenix memory supplement](https://www.sec.gov/Archives/edgar/data/1000275/000095010325003216/dp226084_424b2-jpmeln565.htm),
[SSPA's autocall definition](https://sspa.ch/en/lab/), and the
[Rothschild structured-products glossary](https://www.rothschildandco.com/fr-fr/banque-privee/gestion-financiere/produits-structures/glossaire-produits-structures/).
Those sources support treating memory as optional, keeping coupon/autocall/
capital barriers distinct, and planning for non-call periods and separate
coupon/call dates rather than inferring them from the `PHOENIX` label.

The UI only renders the consolation controls for that subtype. The API keeps
the legacy explicit `includeConsolation` flag for older integrations, but new
UI submissions do not expose an ordinary-autocall consolation branch.

Adding, deleting, and reordering rows and long-lived draft persistence remain
deferred. The generic reference-data work queue and review/decision page now
handle `CREATE_STRUCTURED_PRODUCT` proposals, while a dedicated
structured-product approval view remains deferred. Row operations will use
domain commands and server-side validation;
they are not generic table mutations. AG Grid may be used as the editor adapter
later, but the draft contract is deliberately independent of the grid library.

## Model

### Versioned parent terms

`structured_product_terms` is anchored to the stable parent economic
instrument through `instrument_node_id`, but every contractual graph references
the immutable `structured_product_terms_id`. `version_no`, effective dates,
`is_current`, and `supersedes_terms_id` support legal amendments without
overwriting history. `default_underlying_scope` is one of `SINGLE`, `BEST_OF`,
`WORST_OF`, `BASKET`, or `EACH_UNDERLYING`.

### Composition and component payoff terms

`instrument_composition` has one row per child occurrence. `composition_value`
replaces the ambiguous `composition_rate`, and `composition_value_kind`
declares whether it is a signed multiplier, percentage weight, quantity, or
notional amount. `component_sequence` is unique in a terms version.

`structured_product_component_terms` carries the child occurrence's payoff
style, amount/rate, payout currency/basis, timing, schedule, and source
lineage. It supports digital coupon options, calls, puts, caps, KIPs, and
similar contractual children without manufacturing a separate instrument for
each observation date.

### Condition group

`structured_product_condition_group` represents one logical test for one
observation context. It contains a product-local code, `DISCRETE`,
`CONTINUOUS`, or `FINAL_ONLY` observation style, a schedule event when the
style is date-based, `ALL`, `ANY`, or `NONE`, an `underlying_scope`, and an
evaluation sequence. The group is tied to one parent terms version.

### Atomic rule

`barrier_rule` is a group member and has a positive unique
`condition_sequence`, comparison operator, level basis/bounds, underlying
measure, owner node, and explicit `underlying_reference_node_id`.

The explicit resolved underlying is deliberate audit data. A component rule
is validated against the child option/component terms; a parent rule is
resolved from explicit parent composition/reference entries. The model does
not duplicate an ungoverned business underlying field.

### Group action

`condition_group_action` executes once per satisfied group in
`execution_sequence` order. It supports lifecycle actions such as
`PAY_COMPONENT`, `PAY_CONSOLATION`, `REDEEM_PARENT`, `TERMINATE_PARENT`,
`CANCEL_FUTURE_COMPONENTS`, and `ACTIVATE_CAPITAL_PROTECTION`. It has an
explicit target scope/node and, for a component payment, an optional exact
`target_composition_id`. Optional payout amount/rate/currency, basis, timing,
and schedule make the contractual consequence unambiguous.

Example two-name autocall:

```text
Parent terms v1: WORST_OF
  Group AUTOCALL_OBS_1_AT_100: DISCRETE, aggregation MIN, operator NONE
    Rule 10: HSBC >= 100% of initial
    Rule 20: SAP  >= 100% of initial
    Predicate: min(HSBC, SAP) >= 100% of initial
    Action 10: PAY_COMPONENT -> parent aggregate coupon, rate 5 (5%)
    Action 20: REDEEM_PARENT -> parent
```

The group produces one Boolean result and the two actions occur once.

### Coupons and memory

`structured_product_coupon_programme` belongs to a terms version and defines
payment mode, memory mode, default payout, currency/basis, schedule, optional
eligibility group, and final-payment treatment. Ordered
`structured_product_coupon_period` rows can override the default and point to
period-specific eligibility groups. A period's `memory_eligible` flag is
configuration; it does not calculate catch-up cashflows. Percentage values are
stored as percentage points (`5` means 5%).

## Integrity rules

Database checks enforce allowed enumerations, positive/unique sequences,
schedule/event consistency, comparison-level requirements, ordered bounds,
underlying scopes, and payout value shapes. Application validation enforces
terms-version membership, target-composition membership, and consistency
between a component rule and its child option underlying.

## Migration and verification

Revision `20260909_32` safely repairs the terms primary key and dependent
foreign keys, adds the new columns/tables, backfills composition sequence and
current terms references, and backfills existing component-action payout
metadata where it can be determined. Revision `20260909_33` adds the explicit
`barrier_rule.lower_bound_inclusive` and `upper_bound_inclusive` flags and
enforces operator-compatible scalar semantics. Revisions `20260910_38`,
`20260910_39`, and `20260910_40` add explicit MIN/MAX underlying reduction,
initial-fixing strike anchors, append-only strike-adjustment revisions,
payout-multiplicity semantics, and the associated integrity checks. The full
upgrade/downgrade path is covered by the dedicated migration integration test.

Focused verification currently covers schema metadata, condition-group
contracts, demo scenarios, migrations, API boundary behaviour, and Python
compilation. The full test suite remains intentionally out of scope unless
explicitly requested.

## Explicit deferrals

* count thresholds and nested Boolean groups;
* a general payoff AST or pricing engine;
* condition-outcome, coupon-ledger, and projected-cashflow result tables;
* market-data resolution and valuation snapshots for payoff evaluation; and
* a complete event-sourced correction/replay workflow for amended terms;
* unrestricted editing of every generated schedule field; the current slice
  only permits the reviewed condition/payoff fields in the selected
  observation; and
* adding, deleting, or reordering individual generated schedule rows.

The schedule-editing deferrals are intentional follow-up work, not permission
to mutate approved contractual terms in place. Generated rows already have
stable deterministic `rowId` values. The next UI version should treat them as a
draft row collection with explicit `row_state` values (`GENERATED`, `ADDED`,
`EDITED`, `DELETED`), capture the user and reason for each change, and submit
the resulting graph for validation as a new terms version. A deleted row must
remain represented in the draft/audit payload rather than silently
disappearing from a previously approved graph.

## UX references

The disclosure choices are informed by:

* [Nielsen Norman Group: Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
  for separating high-frequency summary information from specialised detail;
* [GOV.UK Details component](https://design-system.service.gov.uk/components/details/)
  for the rule that information needed by most users should not be hidden;
* [WAI-ARIA Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
  for keyboard-operable controls with `aria-expanded` and `aria-controls`;
* [Carbon expandable data tables](https://carbondesignsystem.com/components/data-table/usage/)
  for compact row expansion and the warning against expanding every row by
  default; and
* [Material data-table guidance](https://m2.material.io/design/components/data-tables.html)
  for table hierarchy, sorting/filter controls, numeric alignment, and
  horizontal overflow when columns are wide.
