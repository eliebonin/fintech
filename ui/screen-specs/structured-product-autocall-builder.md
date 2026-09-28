# Structured-product / autocall builder

## Purpose

Provide operations with a reviewable way to describe an autocall,
autocall-consolation, Phoenix, or Athena-style product using the canonical
reference-data model. The screen is not a pricing engine and does not approve
or publish a security-master record directly.

## Current MVP flow

1. Enter the parent economic identity and product subtype. The subtype list
   includes `AUTOCALL_CONSOLATION`, a governed child of `AUTOCALL`.
2. Choose issue currency and optional issuer, guarantor, and counterparty
   organisations from DB-backed catalogues.
3. Choose an underlying category and reference level (`ANY`, `ECONOMIC`, or
   `LISTING` where applicable). Search results are canonical reference-node
   IDs, not free-text labels.
4. Add one or more resolved underlyings and enter their initial fixings. For
   the standard autocall template, component sides are generated from the
   payoff convention rather than entered as a generic participation value.
5. Enter observation, payment-lag, coupon, autocall, KIP, scope, observation
   style, and coupon-memory settings. For Phoenix, coupon frequency and
   autocall-observation frequency are independent controls: the operator can
   choose N coupon periods per year and M parent redemption observations per
   year. Coupon eligibility follows the autocall barrier in force by default;
   an explicit switch enables a fixed coupon barrier when the term sheet
   differs. The barrier-floor field appears only when the autocall step is
   non-zero, and the final-payoff barrier appears only for the
   `AUTOCALL_CONSOLATION` subtype. Maturity-consolation controls appear
   only after selecting the governed `AUTOCALL_CONSOLATION` subtype.
   `First autocall observation` expresses the non-call period: coupon rows can
   start earlier, but no early parent redemption is generated before this
   date. `Final coupon treatment` records whether accrued memory is paid
   separately, included in redemption, or forfeited.
   Selecting Athena applies a constant-barrier UI profile (step `0`); selecting
   Phoenix leaves coupon memory at `NONE` until the user explicitly selects a
   memory mode. The final coupon-treatment selector is shown only when memory
   is enabled.
6. Generate a grouped schedule preview. The first view is an observation
   overview table with one compact row per date, showing payment date, scope,
   coupon/autocall barriers, component count, and parent-action status.
7. Select one observation to open its detail card. The detail card presents a
   compact row per underlying, a separate parent-actions table, and the key
   contractual conditions. Parent actions distinguish early `Redeem parent`
   from the contractual `Final redemption` maturity gate. `Show all
   observations` is available for power
   users, but is not the default.
8. Submit the validated draft as a pending proposal for steward review. The
   API stores the draft; approval is the operation that materialises the
   canonical parent, fresh option components, schedules, conditions, actions,
   and initial-fixing provenance.
9. Use `Show contractual rows` when the user needs the full component-level
   projection. This is intentionally secondary to the compact underlying
   matrix, so multiple dates and underlyings remain scannable.

The page-level `Show reference IDs` switch (technical details) is off by default. The business view
keeps canonical names, types, dates, barriers, strikes, outcomes, and scopes
visible while hiding UUIDs and implementation IDs. Turning it on reveals the
reference-node UUID, generated row IDs, and similar technical metadata in
secondary fields. The preference is remembered locally for the current
user/browser; server-side entitlement and tenant filtering remain authoritative.

## Disclosure and density decisions

The schedule follows progressive disclosure rather than rendering every graph
row at once:

* **Always visible:** observation date, payment date, scope, coupon barrier,
  autocall barrier, counts, warnings, and whether a parent action exists.
* **Selected observation:** one compact row per underlying with component role,
  condition, payoff terms, and optional technical IDs.
* **Secondary detail:** the raw contractual component rows are available from
  `Show contractual rows` when operations need to reconcile individual legs.
* **Technical metadata:** UUIDs and generated row IDs are behind `Show
  reference IDs`/the technical-details switch; they never replace business
  labels or contractual fields.

The overview uses an explicit `Open`/`Selected` button for each observation.
The control is keyboard operable and exposes its expanded state and controlled
detail region to assistive technology. We avoid nested observation/underlying/
component accordions: the selected-observation detail plus a compact underlying
matrix is easier to scan and compare. `Show all observations` remains an
explicit escape hatch for review and export workflows.

This choice is based on progressive-disclosure guidance from Nielsen Norman
Group and GOV.UK, expandable-table guidance from Carbon, and the WAI-ARIA
disclosure pattern. It also follows Material table guidance to keep filters and
display controls near the table and to use horizontal overflow rather than
compressing important values into unreadable columns.

## First draft-editing slice

The first editing slice is deliberately smaller than a full editable grid.
`Edit selected observation` opens the contractual component-row projection and
allows operations to edit:

* condition level;
* coupon rate on coupon components; and
* leg side on component rows, displayed as `Long` or `Short` (the signed
  composition multiplier remains an internal value for persistence and
  arithmetic); and
* settlement/payment date for each component or parent outcome row. The
  generated lag-based date is a default; an edited action date is retained on
  that action and takes precedence over the schedule event default.

The underlying picker does not expose a participation input for standard
autocalls: coupon digital components are generated `Long`, maturity
capital-protection puts are generated `Short`, and parent redemption actions
have no leg side. `Buy`/`Sell` is intentionally not used because these rows
are payoff components, not trade executions.

## Maturity consolation branch

The MVP supports a maturity-only consolation branch. When the
`AUTOCALL_CONSOLATION` subtype is selected, the
schedule creates a distinct parent action rather than another component row
per underlying:

* an earlier `REDEEM_PARENT` event terminates the product and prevents
  consolation;
* at maturity, final performance must be at or above the KIP barrier and
  strictly below the explicit final payoff barrier;
* the action pays a configurable percentage of the defined maximum payoff,
  defaulting to 50%; and
* performance below the KIP barrier remains in the capital-protection/KIP
  branch.

`AUTOCALL_CONSOLATION` is the dedicated product-archetype choice for this
branch. It turns the consolation branch on, shows the consolation rate field,
and prevents an apparently ordinary autocall from being submitted with a
hidden consolation branch. The API still accepts the legacy explicit flag for
older integrations, but the current UI does not expose that path.

The range is represented explicitly as a lower and upper bound, with the
lower bound inclusive and upper bound exclusive. The form requires a separate
final payoff barrier input and writes it to the parent action row; the server
validates that the row upper level matches it. The canonical `barrier_rule`
stores both inclusivity flags.

Edits are held in a client-side draft overlay. Every generated row receives a
stable `draftRowId`, retains its `sourceRowId`, and is marked `GENERATED` or
`EDITED`. The generated schedule is never mutated. The draft validator checks
parent-action ownership, component-action ownership, resolved underlyings, and
numeric condition/payoff values. If high-level schedule inputs change while
manual edits exist, the page warns the user rather than silently replacing the
draft; the current MVP offers an explicit `Discard manual changes` action.

This slice intentionally does not yet add rows, delete rows, reorder rows, or
persist a long-lived client-side draft. Submission is implemented as a
server-side pending proposal and is separate from approval; the proposal is
visible through the generic reference-data work queue and review/decision page.
A dedicated structured-product approval view and the remaining row operations
need domain commands and server-side validation before they become editable
controls. AG Grid remains an
implementation option for the next editor iteration; the draft boundary is
independent of the table component.

## Mapping to the security-master model

| UI concept | Canonical model |
| --- | --- |
| Parent product | economic instrument + versioned `structured_product_terms` |
| Underlying selection | `financial_reference_node` (economic node or listing) |
| Coupon/KIP rows | `instrument_composition` occurrences plus component terms |
| Coupon/autocall conditions | condition group, barrier rules, and actions |
| Observation/payment dates | dated instrument row plus recurring schedule rows; action-level settlement overrides are retained on outcome actions |
| Coupon memory | coupon programme/period configuration, not a label-only field |
| Issuer/guarantor/counterparty | governed organisation/party relationships |

### Product profiles

Athena and Phoenix are governed subtype/taxonomy choices over the shared
structured-product graph. Athena's builder profile sets the autocall barrier
step to zero and makes the field read-only while Athena is selected. Phoenix's
profile starts the coupon programme memory mode at `NONE`; the operator opts
into `CONDITIONAL_CATCH_UP` or `ACCUMULATE_TO_REDEMPTION` when the term sheet
requires it. These are entry safeguards and explanations;
the submitted payload still carries explicit barrier and `memoryMode` values.
No separate subtype-specific terms table is required.

### Phoenix research basis

The Phoenix profile follows the distinction in the reviewed issuer and
industry material:

* [SG Forge Phoenix](https://www.sgforge.com/product-structured-products-phoenix/)
  describes separate autocall, conditional-coupon, and maturity-protection
  barriers, with coupons payable while the product continues.
* [RBC's SEC-filed Phoenix memory supplement](https://www.sec.gov/Archives/edgar/data/1000275/000095010325003216/dp226084_424b2-jpmeln565.htm)
  shows that memory is an explicitly selected feature, with unpaid coupons
  paid once on a later eligible date or at maturity/early redemption.
* [SSPA's autocall explanation](https://sspa.ch/en/lab/) supports an `ALL`
  condition for a worst-of autocall when every underlying must meet the
  trigger.

The UI therefore keeps memory off by default for Phoenix and tells the
operator to follow the term sheet when enabling catch-up.
The builder exposes separate coupon/call cadences, an explicit non-call
period, and final-memory treatment. None of these values is inferred by the
server from the marketing subtype; the submitted term sheet remains
authoritative.

### Independent Phoenix cadences

The schedule contract retains `frequency` as a backwards-compatible default
and adds `couponFrequency` and `autocallFrequency`. For Phoenix, the generated
date set is the union of both schedules:

* coupon component rows are created only on coupon dates;
* `REDEEM_PARENT` actions are created only on autocall dates;
* autocall step-down numbering and the derived final payoff barrier advance
  only across autocall dates; and
* coupon barriers inherit the applicable autocall level by default, carrying
  the latest call barrier forward between call dates; and
* maturity KIP/consolation remains a maturity branch, even when the two
  cadences do not coincide.
* the maturity row is a distinct `FINAL_REDEMPTION` action rather than an
  early `REDEEM_PARENT` row; the lifecycle service applies it only when no
  earlier parent redemption and no mutually exclusive maturity branch (such
  as consolation) has terminated or paid out the product.

On approval, the API materialises an `AUTOCALL_OBSERVATION` schedule and a
`COUPON_OBSERVATION` schedule, then persists a `MAIN_COUPON` programme and
one coupon period per coupon observation. Legacy payloads that provide only
`frequency` resolve both new fields to that value. This keeps existing
standard autocalls unchanged while allowing a Phoenix such as “12 coupons per
year / 4 autocall observations per year.”

The payload also persists `firstAutocallObservationDate` (the earliest early
redemption date), `finalPaymentTreatment`, and each row's payment/settlement
date. The schedule-generated date is a default only; a manual row edit is
carried on the corresponding component payment, coupon period, or parent
action.

The preview uses deterministic row IDs derived from the component role,
underlying reference, and observation date. Parent action IDs are derived from
the action role and observation date only, so an action is not duplicated once
per underlying. This keeps the UI stable when a user changes a parameter and
makes later draft reconciliation possible.

## Planned flexible-grid extension

The generated grid is deliberately a first review view. Each displayed cell
must eventually be editable, and operations must be able to add, delete, and
reorder rows for exceptional contractual terms. Implement this as a draft
overlay rather than an in-place update of an approved terms graph:

* keep the generated row as the baseline;
* store cell-level overrides with old/new values, user, timestamp, and reason;
* mark rows `ADDED` or `DELETED` rather than losing provenance;
* validate uniqueness, date ordering, target composition, barrier ownership,
  and parent-action semantics before submission; and
* submit the complete draft for approval, which creates a new versioned
  contractual graph.

Do not allow a free-text row to bypass canonical reference-node selection or
the condition-group/action model.

## Deferred boundaries

* steward approval/rejection UI and proposal detail workflow;
* server-side generation using governed holiday calendars (the current preview
  still uses a deterministic weekend-only business-day approximation);
* full cell editing across every graph level, plus row add/delete/reorder;
* post-approval lifecycle processing: condition outcomes, coupon arrears,
  early termination, settlement cashflows, and payment reconciliation; and
* full contract-document/FpML ingestion.

The creation workflow does not calculate whether a coupon was earned or an
autocall occurred. A separate lifecycle/outcome service will consume the
approved terms version, dated schedules, market-data resolution snapshots, and
trade/position context. It will produce immutable, versioned outcomes and
cashflow instructions without modifying the original contractual graph.
