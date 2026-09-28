# Fund, Future, Swap, and Option Onboarding UI — Design

**Date:** 2026-09-10  
**Status:** Proposed design, approved direction pending written-spec review  
**Scope:** Operations-console onboarding for funds/share classes, futures, swaps,
and vanilla/composed options

## Purpose

The current console can propose equities, bonds, indices, index families, ETPs,
FX forwards, cryptoassets, listings, and structured products. The database has
terms tables for funds, futures, swaps, and options, but the API and frontend do
not yet expose complete controlled creation workflows for them.

This design adds those workflows without changing the canonical identity model:

* `financial_reference_node` remains the stable UUID identity;
* an economic instrument remains separate from a venue listing;
* terms, schedules, legs, and compositions carry contractual economics;
* the browser submits a pending proposal through the BFF;
* Operations reviews and approves the proposal before canonical materialisation.

The first release is an onboarding and review surface. It is not a pricing
engine, a fund-accounting engine, a generic payoff interpreter, or a custody
system.

## Current repository baseline

### Existing UI routes

The operations console currently contains pages for:

* equities, bonds, ETPs, FX forwards, indices, index families, cryptoassets,
  listings, and structured-product/autocall workflows;
* market-data history, trades, P&L, instrument search, and the work queue.

There are no complete dedicated routes for fund/share-class, future-family,
future-contract, swap, vanilla-option, or composed-option proposals.

### Existing API routes

The API has proposal/decision routes for the existing onboarding workflows, but
not for funds, future families/contracts, swaps, or options. The new routes must
follow the existing proposal lifecycle instead of writing directly from the UI.

### Existing database terms

The relevant tables already exist:

| Product | Existing canonical tables |
|---|---|
| Fund/share class | `secm.financial_reference_node`, `secm.fund`, `secm.instrument`, `secm.fund_share_class_terms` |
| Futures | `secm.future_family`, `secm.future_terms`, `secm.instrument_dates`, `secm.instrument_contract_unit_terms`, `secm.listing`, `secm.listing_quotation_terms` |
| Swaps | `secm.swap_terms`, `secm.swap_leg`, `secm.instrument_dates`, optional `secm.schedule` / `secm.schedule_event` |
| Vanilla option | `secm.option_terms`, `secm.instrument_dates`, `secm.instrument_contract_unit_terms`, optional listing and strike-reset tables |
| Composed option | `secm.instrument_composition`, child `secm.option_terms`, `secm.structured_product_component_terms`, optional condition/barrier tables |

No new top-level instrument table is required for this UI slice.

## Research conclusions

The research was used to choose the minimum fields and the UI boundaries, not to
copy any provider's interchange format.

| Area | Sourced conclusion | UI consequence |
|---|---|---|
| Fund share classes | Share classes can have different expenses, distribution rules, sales charges, and NAVs even when they invest in the same portfolio. | Create the fund first, then create a separate share-class instrument with class-specific terms and fees. |
| UCITS/share-class selection | The appropriate representative share class depends on the characteristics and differences between available classes. | Keep class code, currency, income treatment, and dealing/NAV rules visible and selectable; do not infer them from the parent fund. |
| Futures | Contract specifications include contract size/unit, tick size, contract months, trading hours, expiry, delivery, and settlement. | Separate a reusable non-tradeable family from each expiry-level contract and its listing; make provider enrichment optional. |
| Swaps | ISDA definitions and CDM represent a transaction as contractual product terms plus lifecycle events and legs. | Use an editable leg editor instead of a fixed `funded_instrument_id`/`funding_instrument_id` pair. |
| Options | Exercise style, strike, contract size/multiplier, deliverable, settlement, and exercise/assignment rules are independent dimensions. | Do not overload `option_type`; expose explicit strike, exercise, settlement, multiplier, and optional schedule fields. |

Sources:

* [SEC share-class expense example](https://www.sec.gov/Archives/edgar/data/1139819/000093041316008780/c85581_ex99-28n.htm)
* [ESMA UCITS share-class Q&A](https://www.esma.europa.eu/publications-data/questions-answers/1085)
* [CME contract specifications](https://www.cmegroup.com/education/courses/master-the-trade-futures/expanding-your-futures-knowledge/master-the-trade-contract-specifications.hideSubnav.educationIframe.html?hideAddThisExt=y&hideFooter=y&hideHeader=y&hideRightRail=y)
* [ISDA 2006 Definitions](https://www.isda.org/book/2006-isda-definitions/)
* [ISDA Common Domain Model](https://www.isda.org/isda-solutions-infohub/)
* [OCC Characteristics and Risks of Standardized Options](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document)
* [Options Industry Council exercise guidance](https://www.optionseducation.org/referencelibrary/faq/options-exercise)

## Goals and non-goals

### Goals

* Provide a clear, discoverable route for each product workflow.
* Keep economic identity, terms, and listing data visually distinct.
* Use DB-backed catalogues and reference-node search rather than free-text IDs.
* Show existing related records before submission to reduce duplicates.
* Persist proposals through the existing approval/work-queue lifecycle.
* Keep manual submission as the default and allow provider enrichment afterwards.
* Make warnings visible without blocking reasonable incomplete source data.
* Reuse small, stable form primitives instead of creating a universal dynamic form.

### Non-goals

The first slice does not build:

* pricing, scenario analysis, or a general payoff/rules engine;
* a fund accounting or official NAV calculation engine;
* automatic schedule/calendar generation for every product;
* full ISDA/FpML/ISO 20022 interchange parsing;
* trade packages for listed option strategies;
* custody, collateral, margin, or lifecycle correction processing;
* field-level tenant override precedence or production Auth0 enforcement.

## Design principles

1. **One economic object at a time.** A fund vehicle, share class, future
   contract, swap, vanilla option, and OTC composed option each receive their
   own economic identity. A family or umbrella is not a tradeable contract.
2. **Listings are optional and separate.** Venue, ticker, listing FIGI, quote
   currency, quote factor, and venue product ID belong in a later listing step.
3. **The server owns identity and mapping.** The browser sends selected UUIDs and
   business values; it never invents canonical UUIDs or writes the database.
4. **Proposals are the write boundary.** A successful submit returns a proposal
   ID and review status, not an immediately active instrument.
5. **Warnings are not silent coercions.** Suspicious date order, missing provider
   enrichment, or unusual combinations are displayed as acknowledgable warnings.
   Structural contradictions remain blocking validation errors.
6. **No duplicate semantics.** Contract multipliers belong to
   `instrument_contract_unit_terms`; quote factors and ticks belong to effective
   `listing_quotation_terms`; dates belong to `instrument_dates` or schedules.

## Shared UI architecture

### Route and rendering pattern

Each product has a server page that loads initial catalogues and a client form
for interaction:

```text
server page
  -> DB-backed catalogue/reference-node requests through the server client
  -> client form with deterministic initial date and initial catalogue state
  -> same-origin BFF POST
  -> reference API proposal command
  -> work queue / review route
```

All browser-visible data and POSTs should use the authenticated BFF seam when the
authentication slice is available. Until then, the existing local tenant context
remains an explicit development boundary and must not be presented as production
authentication.

### Shared components

Add small components under `apps/ops-console/src/components/instrument-creation/`
or the nearest existing component boundary:

| Component | Responsibility |
|---|---|
| `IdentityFields` | Canonical name, optional internal code, helper text, and stable identity explanation. |
| `CatalogueSelect` | Loading/error/empty states for currencies, organisations, countries, instrument types, return profiles, and venues. |
| `ReferenceNodePicker` | Search with `ECONOMIC` / `LISTING` filter, selected-record summary, and duplicate-warning context. |
| `DateFields` | Deterministic initial date, shared effective/maturity/settlement controls, and warning presentation. |
| `ListingLinkSection` | Optional listing step with venue, symbol, listing FIGI, quote currency, quote factor, and unit multiplier. |
| `ExistingChildrenTable` | Existing share classes, family contracts, swap legs, or option components shown before submission. |
| `ScheduleEditor` | Small dated event editor for exercise, strike-reset, reset, fixing, or payment schedules; no universal formula engine. |
| `ProposalReviewSummary` | Read-only payload summary with product type, selected IDs, warnings, and proposed terms. |
| `useProposalSubmit` | Common idempotency key, submitting state, API error envelope, and success link to review. |

The shared components must keep labels floated when a native select or date input
has no value. Every field needs a meaningful label and helper text; internal UUIDs
are hidden by default behind the existing advanced-details convention.

### Common submission behaviour

1. The server page loads catalogues and passes an explicit `initialDate` rather
   than evaluating a different `Date()` value during hydration.
2. The form validates obvious required fields locally for fast feedback.
3. The BFF sends a generated `Idempotency-Key` and the tenant/user context.
4. The API validates the selected UUIDs, parent instrument types, duplicate
   candidates, effective dates, and term applicability again.
5. The API returns blocking errors and non-blocking warnings separately.
6. The proposal is visible in the work queue with a product-specific summary.
7. The decision endpoint creates the canonical node, instrument, terms, and any
   explicitly requested listing or child rows in one transaction.

## Product workflow designs

### 1. Funds and share classes

#### Fund vehicle route

Route: `/instruments/funds/new`

The first screen describes the fund vehicle, not a tradeable share class.

Required or strongly recommended fields:

* canonical name;
* optional internal code;
* fund kind: `UMBRELLA`, `SUB_FUND`, `STANDALONE`, `ETF_ISSUER`, or
  `PARTNERSHIP`;
* domicile country;
* legal form.

Optional fields:

* parent/umbrella fund selected from existing active funds;
* fund manager/AIFM organisation;
* fund-level identifiers and source reference.

The page shows a warning when `SUB_FUND` is selected without a parent. It does
not allow a share class to be created until the fund proposal has a canonical
reference that can be selected.

Persistence:

* `financial_reference_node` with structural type `FUND` and `is_tradable=false`;
* `secm.fund` with the fund kind, parent, manager, domicile, legal form, and
  status;
* identifiers through the existing identifier/mapping layer.

#### Share-class route

Route: `/instruments/funds/[fundId]/share-classes/new`

The fund context is shown at the top and is not editable on the share-class
screen. The user enters:

* canonical name and optional internal code;
* share-class code;
* share currency;
* income treatment: accumulation/distribution/income/unknown;
* dealing frequency;
* NAV frequency;
* expected NAV publication lag in business days;
* effective date;
* optional ISIN, FIGI, or other economic identifiers;
* optional “add listing after approval” request.

The page displays existing classes for the selected fund with class code,
currency, income treatment, and status. A likely duplicate is a warning before
submit; an exact duplicate already active in the same fund is a blocking API
error.

Persistence:

* `financial_reference_node` with structural type `INSTRUMENT`;
* `secm.instrument` with type `FUND_SHARE_CLASS`, base currency, and effective
  range;
* `secm.fund_share_class_terms` with class-specific terms;
* optional `secm.listing` only after the economic instrument exists.

The UI must not infer fees from the parent fund. Class-specific fee rules belong
to the generic fee model and can be added in a later fee workflow.

#### Proposed API surface

* `GET /v1/funds` — active fund/umbrella selector and duplicate context;
* `POST /v1/fund-proposals` — create a fund vehicle proposal;
* `GET /v1/fund-proposals/{proposal_id}` — review payload;
* `POST /v1/fund-proposals/{proposal_id}/decision` — approve/reject;
* `GET /v1/funds/{fund_id}/share-classes` — existing class table;
* `POST /v1/fund-share-class-proposals` — create a share-class proposal;
* `POST /v1/fund-share-class-proposals/{proposal_id}/decision` — approve/reject.

### 2. Futures

#### Future-family route

Route: `/instruments/futures/families/new`

The family is explicitly labelled “non-tradeable specification”. Fields:

* canonical family name and optional internal code;
* underlying reference node, with economic/listing selection;
* contract currency;
* expiry-cycle rule, such as quarterly or monthly;
* optional exchange/product description;
* optional provider identifier.

Persistence:

* non-tradeable `FUTURE_FAMILY` reference node;
* `secm.future_family`.

The page shows existing families and prevents a duplicate family code. It does
not create an expiry contract.

#### Future-contract route

Route: `/instruments/futures/new?familyId=...`

The selected family is read-only context. Fields:

* canonical contract name and optional internal code;
* contract month;
* last trade date;
* settlement method: cash, physical, or EFP where applicable;
* delivery start/end dates for physical contracts;
* unit multiplier and unit of measure;
* optional listing request.

The page displays every existing expiry contract in the family. A duplicate
contract month is a blocking API error. Provider-supplied tick size, trading
hours, deliverable grade, price limits, and exchange rule references are optional
enrichment; they are not fabricated when unavailable.

Persistence:

* economic `FUTURE` reference node and `secm.instrument`;
* `secm.future_terms` for family, contract month, last trade date, settlement,
  and delivery window;
* `secm.instrument_dates` for expiry/final settlement dates;
* `secm.instrument_contract_unit_terms` for multiplier and unit;
* optional `secm.listing` and effective `secm.listing_quotation_terms`.

#### Proposed API surface

* `GET /v1/future-families`;
* `POST /v1/future-family-proposals`;
* `POST /v1/future-family-proposals/{proposal_id}/decision`;
* `GET /v1/future-families/{family_id}/contracts`;
* `POST /v1/future-proposals`;
* `POST /v1/future-proposals/{proposal_id}/decision`.

### 3. Swaps

Route: `/instruments/swaps/new`

The first operational workflow targets the existing Fortem use case: a
total-return/performance leg funded by a rate or other funding leg. ABC, XYZ,
and FOO remain business taxonomy labels, not separate swap types.

#### Header fields

* canonical name and optional internal code;
* swap type, initially enabling `TOTAL_RETURN` and `INTEREST_RATE`;
* effective date;
* maturity and final settlement dates;
* optional confirmation/document reference.

#### Leg editor

The form starts with two rows and allows add/remove:

| Field | Meaning |
|---|---|
| Leg role | `PERFORMANCE`, `FUNDING`, `COUPON`, `PROTECTION`, or `FEE`. |
| Pay/receive | Direction from the holder's perspective. |
| Reference | Economic instrument, listing, index, rate, or basket selected through the reference picker. |
| Return profile | Required for performance legs where return semantics apply. |
| Currency | Leg payment/notional currency. |
| Spread | Decimal rate; the UI displays both entered decimal and basis-point interpretation. |
| Schedule | Optional reset/fixing/payment schedule created in the small schedule editor. |

The initial `TOTAL_RETURN` template creates one performance and one funding row.
The user may customise roles and add a fee/protection leg, but the API enforces
the minimum terms for the selected swap type.

Persistence:

* economic `SWAP` reference node and `secm.instrument`;
* `secm.swap_terms` for the governed swap type;
* `secm.swap_leg` for every leg;
* `secm.instrument_dates` for common contract dates;
* `secm.schedule`/`secm.schedule_event` only when dated leg events are supplied.

#### Proposed API surface

* `POST /v1/swap-proposals`;
* `GET /v1/swap-proposals/{proposal_id}`;
* `POST /v1/swaps/{proposal_id}/decision`;
* `GET /v1/return-profiles` and the existing reference-node search are reused.

Cross-currency, inflation, credit, and commodity templates remain catalogue
values but are disabled with an explanation until their additional benchmark,
calendar, and schedule fields are defined.

### 4. Vanilla and composed options

#### Vanilla option route

Route: `/instruments/options/new`

The first section asks whether the underlying is an economic instrument or a
specific listing. This choice is explicit because the same equity may have
multiple venue listings.

Fields:

* canonical name and optional internal code;
* underlying reference node and `ECONOMIC`/`LISTING` level;
* option type: `CALL` or `PUT`;
* exercise style: European, American, or Bermudan;
* strike mode: fixed, forward-start, or reset;
* strike basis and value;
* strike currency when the basis requires it;
* premium currency;
* settlement method and settlement currency;
* effective, expiry, maturity, and settlement dates;
* contract multiplier and unit of measure;
* optional listing request;
* optional exercise or strike-reset schedule.

Conditional fields:

* a dynamic strike requires a strike-reset schedule;
* Bermudan exercise requires an exercise schedule;
* cash settlement requires a settlement currency;
* listing fields appear only when “exchange-traded representation” is selected.

Persistence:

* `secm.option_terms` for static option terms;
* `secm.instrument_dates` for common dates;
* `secm.instrument_contract_unit_terms` for contract multiplier/unit;
* optional listing and effective quotation terms;
* `secm.schedule`, `secm.option_strike_reset_rule`, and fixing rows for dynamic
  strikes.

The UI shows the initial fixing/reference used for percentage strikes when known;
it does not flatten a percentage strike into an unexplained absolute value.

#### Composed option route

Route: `/instruments/composed-options/new`

The parent section creates one OTC `COMPOSED_OPTION` economic instrument. A
component table starts empty and supports add/remove/reorder. Each local row
contains:

* component role and kind;
* CALL/PUT where relevant;
* underlying reference and economic/listing level;
* strike and settlement terms;
* signed composition value and an explicit value-kind label;
* optional barrier/condition reference;
* payment/observation information when the component is digital or conditional.

For the initial OTC mode, each component row represents a fresh child option
identity. The user never selects the same child UUID twice and the API creates
the child `OPTION` nodes and terms during approval. This preserves the rule that
one composed parent has its own child contracts.

“Link existing listed option legs” is intentionally not part of the first
composed-option workflow. That is a different trade-package workflow and should
not be confused with one OTC parent instrument.

Persistence:

* parent `COMPOSED_OPTION` instrument;
* `secm.instrument_composition` rows;
* fresh child `OPTION` instruments and `secm.option_terms` rows;
* `secm.structured_product_component_terms` for component payoff metadata;
* condition/barrier tables only when a component actually needs them.

#### Proposed API surface

* `POST /v1/option-proposals` with `option_kind=VANILLA`;
* `POST /v1/option-proposals` with `option_kind=COMPOSED`;
* `GET /v1/option-proposals/{proposal_id}`;
* `POST /v1/option-proposals/{proposal_id}/decision`.

The API may share persistence helpers with the structured-product proposal
implementation, but the public contract remains option-specific so validation
and review summaries are clear.

## API and BFF contract design

The first vertical slice may use the repository's existing manual Pydantic and
TypeScript contracts, but each new route must have one request/response shape
shared by the API client and BFF. The later OpenAPI-generation slice should be
able to replace those manual types without changing the domain payload.

Every proposal request carries:

* `canonicalName`;
* optional `internalCode`;
* `submissionMode: "MANUAL"` by default;
* product-specific terms;
* selected UUIDs for catalogues and references;
* client-generated idempotency key in the HTTP header, not in business terms.

Every response carries:

* proposal UUID;
* proposal type;
* lifecycle status;
* proposed canonical/instrument IDs when materialised;
* blocking errors or warnings in a structured envelope;
* a correlation ID and review link where available.

The BFF must never fall back to fixtures for a successful production-looking
submission. Fixture mode remains a visible development-only configuration.

## Validation and warning policy

### Blocking validation

The API rejects:

* missing canonical identity or required product terms;
* an unknown, inactive, or tenant-inaccessible UUID;
* a parent node of the wrong structural/economic type;
* duplicate active fund class, family contract month, or listing identity;
* a fixed strike without a strike value;
* a dynamic strike without a reset schedule;
* Bermudan exercise without an exercise schedule;
* cash settlement without a settlement currency;
* a composed option without at least one component;
* a total-return swap without the required performance/funding terms.

### Non-blocking warnings

The API returns warnings that the UI must display and allow the user to
acknowledge:

* settlement or payment dates look unusual relative to maturity;
* a provider enrichment field is absent;
* the selected underlying is a listing and may be venue-specific;
* a family/parent has no existing provider identifier;
* optional fees, schedules, or identifiers are not yet supplied.

The approval screen retains the acknowledged warnings in the proposal evidence.

## UX and accessibility requirements

* Use the existing MUI visual language and native-select loading/error patterns.
* Keep economic identity and listing data in separate cards or steps.
* Show the selected parent/family/fund context at the top of child workflows.
* Display existing child records before the add-row control.
* Keep UUIDs and raw database values hidden by default; expose them in an
  “Advanced details” disclosure for Operations users.
* Provide a summary of unsaved rows before submit.
* Support keyboard navigation, visible focus, labelled controls, and field-level
  errors; test against WCAG 2.2 criteria.
* Preserve user-entered rows after a validation response; never silently reset a
  long leg/component form.

## Testing strategy

Each product slice has focused tests rather than an immediate full-suite run:

### Shared

* catalogue loading, empty, and error states;
* deterministic initial date/hydration behaviour;
* reference-level filtering and duplicate warnings;
* idempotency key reuse after a retry;
* structured API error rendering and warning acknowledgement.

### Funds

* fund before share-class route context;
* class-specific currency/income/dealing/NAV terms;
* duplicate class detection;
* optional listing remains separate.

### Futures

* family non-tradeable flag;
* contract month duplicate detection;
* settlement/delivery conditional fields;
* multiplier and quotation-term mapping.

### Swaps

* minimum performance/funding legs;
* pay/receive and reference-level persistence;
* add/remove/reorder leg rows;
* optional schedule mapping.

### Options

* fixed versus dynamic strike validation;
* exercise-style schedule requirement;
* cash-settlement currency requirement;
* fresh child identities for composed options;
* signed composition value and component ordering.

Add one browser smoke test per workflow after the focused component/API tests:
load catalogues, submit a valid proposal, display a warning, and reach the
review queue. Full end-to-end authentication and tenant-negative tests belong to
the global control slice.

## Delivery sequence

### Slice A — shared onboarding primitives

Create the shared picker, identity, dates, listing, duplicate-context, warning,
review-summary, and submission helpers. Add deterministic server-date handling.

### Slice B — funds and share classes

Implement fund catalogue/listing, fund proposal/review, then share-class
proposal/review. Seed a small umbrella, sub-fund, and two different share classes
with different currencies/income treatments for UI testing.

### Slice C — future families and contracts

Implement family creation, contract creation, existing-contract table, optional
listing step, and synthetic family/expiry fixtures.

### Slice D — total-return swaps

Implement the two-leg template, editable leg table, optional schedule editor,
proposal/review, and a synthetic performance/funding swap fixture.

### Slice E — vanilla then composed options

Implement vanilla option terms and conditional schedules first. Reuse the picker
and row-editor infrastructure for the composed parent/child workflow. Add
synthetic call spread and straddle fixtures.

### Slice F — focused verification and documentation

Run the product-specific tests, frontend typecheck/build, API contract checks,
and migration smoke checks. Update the review queue and this design with the
actual implementation status. Do not run the full repository test suite unless
explicitly requested.

## Deferred choices

The following remain deliberately outside this first UI slice:

* production Auth0/OIDC and tenant-database routing;
* generated OpenAPI/TypeScript clients;
* calendar ownership, holiday data, and DST-aware schedule generation;
* safe current-version promotion for all term tables;
* fee-rule authoring and official fund NAV calculation;
* automatic provider matching/enrichment and raw confirmation parsing;
* listed option strategy trade packages;
* swaption, FRA, cap/floor, cross-currency, inflation, credit, and commodity
  specialised templates;
* custody-grade lifecycle and corporate-action adjustments.

## Acceptance criteria

The design is ready for implementation when:

1. a user can create a fund and then a share class without entering UUIDs;
2. a user can create a future family and an expiry contract while seeing existing
   family contracts;
3. a user can create a total-return swap with explicit performance/funding legs;
4. a user can create a vanilla option with fixed or scheduled strike semantics;
5. a user can create an OTC composed option with fresh child option rows;
6. every proposal reaches the existing review queue and is idempotent on retry;
7. economic and listing fields are visibly distinct;
8. warnings are preserved without silent coercion;
9. focused API/component tests and frontend typecheck pass; and
10. no new product-specific price table or duplicate identity hierarchy is
    introduced.
