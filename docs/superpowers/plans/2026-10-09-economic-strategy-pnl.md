# Economic Strategy P&L Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, sequentially, task-by-task.
> No subagents. Steps use checkbox tracking. Status: planning only; no migration
> or financial calculation behaviour changed by writing this plan.

**Goal:** Deliver reproducible strategy P&L with price/FX attribution, instrument-linked
income and daily interest accrual, followed by staged amendments and reviewed publication.

**Execution update (2026-10-09):** Bounded implementation is documented in
[the delivery report](../../delivery/economic-pnl-implementation-2026-10-09.md).
The original checklist below records programme intent; cash-stock/maturity
handlers, actual Yahoo proof, operating activation and browser sign-off are not
claimed complete. See the execution ledger for verified scope and deliberate gates.

**Architecture:** Extend the existing position reconstruction, resolver and `nav`
attribution/review tables. Keep input selection, pure Decimal calculations, economic
flow recognition and operational review separate. Positions own market results;
real flow trades and accrual records supply linked economic components, not synthetic
executions. Never replace published evidence with mutable calculations.

**Tech Stack:** Existing Python/SQLAlchemy/PostgreSQL/Alembic, Decimal, FastAPI,
Next.js/TypeScript and generated API contracts; no new grid or financial library.

**Spec:** ../../delivery/economic-pnl-agreed-foundation-2026-10-09.md
**Price-basis dependency:** 2026-10-09-valuation-price-basis.md and its referenced spec.

## Global Constraints

- Sequential implementation; current feature checkout; preserve unrelated changes.
- Focused lightweight tests first, followed by broader relevant regression tests;
  disposable databases only for test mutations; no full suite by default.
- No commit/push or operating-data financial writes unless specifically authorized.
- Preserve original trades, observation values, policy versions and published results.
- No automatic settlement, general ledger, full fund NAV or GIPS-compliance claim.
- Ops can supply flows and accruals; do not require a comprehensive bond accrual calculator.
- Never infer missing inputs as zero or treat permission failures as provider fallback.
- Price, NAV and FX dates are independent and frozen with source/information-cut evidence.
- Daily earned interest alone enters the ACCRUAL income component; accumulated balance
  is a valuation/reconciliation input, not a second income component.
- Allocate additive migration revisions at implementation; document activation/rollback.
- Keep technical failure logs separate from financial candidates; always retain correlation IDs.

## Delivery boundaries

This is a programme of independently testable increments, not one all-product release.
Tasks 1–2 deliver cross-currency market P&L; 3–5 add economic inputs; 6 delivers
amendment controls; 7 delivers the operational UI; 8 validates and activates supported scope.
Full bond, fund, derivative and cash capabilities require their own explicit readiness
tests. Booking support does not imply valuation support. Unsupported contracts remain blocked.

## Review Focus

1. FX orientation, duplicate paths and price/trade-currency mismatches must never
   produce plausible but inverted valuations: Task 2.
2. Fully closed positions, flow-only strategies and multiple executions must not
   disappear from selection or acquire fictitious opening marks: Tasks 2 and 4.
3. Coupon dates, weekend accruals and multiple listing buckets for one bond must
   not duplicate daily income or turn a balance reset into negative interest: Task 3.
4. Amendments racing publication or source corrections must not publish stale
   candidates or overwrite history: Task 6.
5. Fund NAV lag must follow its calendar without dragging FX backward or leaking
   later-published knowledge into an old information cutoff: Task 5.

## Ownership and file boundaries

- `market_data/price_basis.py`, proof storage and resolver changes: use the existing
  separate price-basis plan; avoid a second normalization implementation.
- New `valuation/fx.py`: policy-based FX selection and immutable conversion evidence.
- `valuation/position_calculation.py`: pure market bridge and reconciled PRICE/FX/CROSS.
- New `valuation/accruals.py`: source-neutral daily earned/balance side-input validation.
- New `valuation/flows.py`: selection and classification of real booked economic flows.
- New `valuation/product_inputs.py`: explicit product capabilities and input semantics.
- New `valuation/amendments.py`: component-request state machine and candidate versioning.
- `valuation/service.py`, `position_storage.py`, `storage.py`, `tables.py`,
  `evidence_access.py`: orchestration, persistence and existing review boundary.
- New `apps/reference_api/valuation_input_routes.py`, `valuation_amendment_routes.py`
  and their contract modules: authenticated input/review APIs, not calculation logic.
- New `apps/ops-console/src/features/valuation/`: review workspace and focused components;
  retain existing valuation route and failure-summary/price-evidence components.

## Task 1: Compatible price inputs

**Files:** As listed in `2026-10-09-valuation-price-basis.md`; additionally
`tests/test_valuation_price_basis.py` and existing selection/evidence tests.
**Interface:** Resolver source value remains unchanged; normalized valuation value
and proof live in frozen `pricing_evidence.priceBasis`, as that plan specifies.

- [ ] Execute the existing price-basis plan without relabelling Yahoo RAW or official.
- [ ] Watch failures for adjusted 40 with verified factor 0.5 becoming as-traded 80,
  missing proof blocking, dividend-adjusted data rejecting and later evidence excluded.
- [ ] Preserve corporate-action safety; normalization is not position replay.
- [ ] Run focused pure tests, then isolated proof/resolver/valuation tests from that plan.
  Expected: all pass; previously stored evidence stays unchanged.
- [ ] Gate live Yahoo acceptance on actual retained provider proof. If proof cannot be
  established, report that limitation; do not enable factor-1 assumptions.

## Task 2: Frozen FX and market attribution

**Files:** Create `valuation/fx.py`, `tests/test_valuation_fx.py`;
modify `valuation/service.py`, `position_calculation.py`, `position_storage.py`,
`evidence_access.py`, and policy editor/contracts where explicit FX rules need exposure.
**Interfaces:** Define `FxConversion` in `valuation/fx.py` with source/target currency,
Decimal rate, economic date, observation date and frozen source proof.
`resolve_fx(c, request, source_currency_id, target_currency_id, economic_date) -> FxConversion`.
Same currency produces an explicit identity conversion, not a market observation.
`attribute_projection(..., fx_inputs)` consumes resolved boundary/execution conversions.

- [ ] RED: 100 units, prices 75→76 and GBP/EUR rates 0.85→0.86 produce
  PRICE=85, FX=75, CROSS=1, market P&L=161 GBP. Identity FX gives FX=CROSS=0.
- [ ] RED: 100 units booked today at 75 and marked at 76 with FX 0.86 produce
  86 GBP market P&L under the agreed daily end-date FX convention.
- [ ] Implement direct pairs first; permit inverse only when explicitly configured
  and retain reciprocal evidence. Do not silently triangulate. Missing/ambiguous
  pairs, mismatched price currency, denied rights and stale fixings block.
- [ ] Select FX independently using explicit policy timing, freshness and priorities.
  Yahoo cutoff samples are not certified benchmark fixings.
- [ ] For multi-day periods calculate and aggregate daily bridges using each day's
  execution FX convention, rather than assigning period-end FX to every execution.
  Freeze all constituent dates; avoid requeries per trade through currency/date caching.
- [ ] Preserve `closing − opening − signed executions` reconciliation. Handle buys,
  sells and zero closing positions; no market input is required for zero boundaries.
- [ ] Run `scripts/run_isolated_python_tests.py tests/test_valuation_fx.py
  tests/test_position_valuation.py tests/test_valuation_evidence_access.py -q`.
  Expected: green, with no original trade or observation mutations.

## Task 3: Position-level daily bond accrual side inputs

**Files:** Create `valuation/accruals.py`, `tests/test_valuation_accruals.py`,
`apps/reference_api/valuation_input_contracts.py`, `valuation_input_routes.py`;
modify `valuation/tables.py`, service/storage/main registration; add migration.
**Interfaces:** `load_accrual_inputs(c, request, position_projection) -> tuple[AccrualInput,...]`.
Define `AccrualInput` in `valuation/accruals.py` with tenant/strategy/instrument/date/type,
eligible nominal, currency IDs, daily local/base amounts, accumulated local/base
balances, independent conversion evidence, source reference and revision identity.

- [ ] RED: yesterday balance 990, daily earning 10, coupon 1000, closing balance 0
  contributes daily interest 10—not −990 or 1000. At FX 0.86, daily base interest=8.60.
- [ ] Add versioned immutable side-input rows with recorded time and supersession;
  enforce one effective record per scope/date/type at an information cutoff.
  Source amendments create versions, never edit financial history.
- [ ] Accept reviewed Ops/imported accruals first. Reject inconsistent local/base
  conversion, duplicate source keys, wrong strategy/instrument, nonfinite amounts
  and records newer than the information cutoff. Explicit zero earns 0; missing
  required coverage blocks complete economic P&L.
- [ ] Store accrued balances in addition to earned amounts; translate balances at
  their valuation FX and earned income at its recognition-date FX. Track FX on
  pre-existing accrued receivables separately from daily interest income; require
  the relevant balance/movement evidence instead of guessing from balance differences.
- [ ] Default to canonical instrument-level input; reconcile/allocate once across
  compatible listing/convention buckets, never add the same input to every listing.
  Preserve trade-specific detail for yield-dependent inputs when supplied.
- [ ] Cover weekend/holiday earnings across a valuation interval and partial
  acquisitions/disposals using the supplied eligible nominal/source convention.
  Do not hardcode settlement versus trade-date accrual eligibility.
- [ ] Run isolated `tests/test_valuation_accruals.py` plus evidence-access/storage tests.
  Expected: exact daily sum, no duplicate coupon income, revision replay preserved.

## Task 4: Booked dividend/reset/coupon flows and reconciled economic totals

**Files:** Create `valuation/flows.py`, `tests/test_valuation_flows.py`;
modify position input selection/service, economics, storage and API contracts.
**Interfaces:** `load_economic_flows(c, request) -> tuple[EconomicFlow,...]` defined in
`valuation/flows.py`; flow includes real trade/event IDs, economic instrument,
recognition/payment dates, signed local amount/currency, classification and FX evidence.

- [ ] RED: zero market P&L plus a 100 EUR dividend at 0.86 yields DIVIDEND=86 GBP;
  payment on a later date contributes no second income entry.
- [ ] Read actual BOOKED, noncancelled cash-flow economics from existing booking
  records and corrections. Do not treat them as share positions or multiply an
  already monetary CASH_AMOUNT twice. Verify current frozen booking conventions.
- [ ] Include flow-only strategies, linked instruments with no surviving position,
  and flow trades corrected/cancelled before the information cutoff.
- [ ] Preserve Ops economic-date responsibility. Distinguish income recognition
  from receipt of already accrued coupon interest; payment-only flows do not add income.
  Require explicit supported classification, not guessed text/tag matching.
- [ ] Introduce typed component families: market=PRICE+FX+CROSS;
  gross=market+CARRY+ACCRUAL+CASHFLOW+DIVIDEND+RESET;
  net=gross+FEE+ADJUSTMENT+OTHER. Names alone never decide whether a receipt is new income.
- [ ] Keep reset flow and mark movement as separate linked evidence; do not
  synthesize a reset or settlement transaction. Ops supplies the correct booked flow.
- [ ] Run isolated `tests/test_valuation_flows.py tests/test_position_repository.py
  tests/test_position_attribution_storage.py -q`. Expected: reconciling totals,
  cancellation/replacement inclusion correct, no duplicate recognition.

## Task 5: Product input conventions and supported-scope gates

**Files:** Create `valuation/product_inputs.py`, `tests/test_valuation_product_inputs.py`;
modify service, policy compatibility and component evidence views.
**Interface:** `prepare_product_inputs(c, request, position, selected_inputs) -> ProductInputs`,
defined in the new module; carries canonical mark basis, output currency, economic
multipliers, accrual treatment and explicitly supported lifecycle interpretation.

- [ ] Funds: RED for T+1 sign-off policy selecting NAV(T-1)/NAV(T-2) over a holiday
  using the fund calendar, with FX(T)/FX(T-1) independent. Publication/as-of evidence
  must be available at the request cutoff; no global one-day fund assumption.
- [ ] Bonds: normalize clean/dirty inputs and quote factors without double-counting
  separate daily earnings. Purchased/sold settlement accrued is not today's earned income.
- [ ] Cash balances: unit mark 1, FX-only market P&L; distinguish stock cash balances
  from monetary dividend/reset/fee flows. Do not equate every CASH_AMOUNT trade with a balance.
- [ ] Maturity: define supported bond redemption and FX-forward termination from
  recorded terms and lifecycle events; never copy `trade_date == maturity_date` or
  freeze marks as a generic maturity rule. No physical settlement/accounting automation.
- [ ] Keep options, futures, swaps, structured payoffs and unsupported FX-forward
  rate/discounting conventions blocked until their unit economics and final-mark
  tests are specified. Provider MTM input support is not a new pricing model.
- [ ] Run isolated product-input, corporate-action, calendar and booking-convention
  regression tests. Expected: supported cases green; unsupported cases explicit.

## Task 6: Staged amendment requests and publication integrity

**Files:** Create `valuation/amendments.py`, amendment API/contracts modules,
`tests/test_valuation_amendments.py`; modify tables/storage/runner/routes/access;
add additive request/allocation/revision migration.
**Interfaces:** `request_component_change(c, scope, base_id, actor, payload) -> UUID`,
`approve_component_change(c, tenant_id, request_id, actor, comment) -> UUID`,
`reject_component_change(...)`; define in amendments module, using caller transaction.
Input correction uses the existing calculation runner with new versioned source inputs
and explicit predecessor/recalculation reason, not direct edits of stored calculated values.

- [ ] RED: staged net 100 plus approved adjustment −10 produces candidate net 90;
  original market/gross and original attribution remain unchanged. Publication is
  blocked while a request is pending. Identical retry creates no additional amendment.
- [ ] Store PENDING/APPLIED/REJECTED/STALE request state, reason/source/actor,
  exact base attribution(s), candidate population hash and independent approver.
- [ ] Position-level amendments apply directly to the position; no compulsory
  pro-rata trade allocation. Optional genuine trade-target requests retain lineage.
- [ ] Check base versions/population atomically on approval and publication;
  concurrent recalculation or another amendment makes old requests stale.
- [ ] Publish only reconciled, supported and complete reviewed candidates;
  enforce independent review and current evidence permissions server-side.
  Published batches are read-only; later corrections stage a replacement.
- [ ] Run isolated `tests/test_valuation_amendments.py tests/test_valuation_storage.py
  tests/test_valuation_api.py tests/test_valuation_evidence_access.py -q`.
  Expected: rollback, retries, stale population, tenant isolation and four-eyes checks pass.

## Task 7: Review workspace inspired by the existing frontend

**Files:** New feature components `review-workspace.tsx`, `position-summary.tsx`,
`input-evidence.tsx`, `amendment-dialog.tsx`, `request-history.tsx` with colocated tests;
modify existing valuation page/console and contracts, retain failure explanation UI.

- [ ] RED UI tests: strategy/date and exact policy-version selection; labelled
  staged/published batches; readable component totals and original/used price/FX dates;
  daily and accumulated accrual shown independently in local/base currency.
- [ ] Build summary -> position -> trade/event evidence drill-down. Local numerical
  formatting is presentation only; frontend never recalculates authoritative P&L.
- [ ] Provide distinct add-component, explicit adjustment and correct-input/recalculate
  actions, with pending/applied/rejected/stale request history and reasons.
- [ ] Published batches have no edit actions. Explain publication blockers and
  independent-review requirement. Refreshing/changing strategy or batch cannot keep
  stale action targets. Use strategy calendars, not weekend-only date restrictions.
- [ ] Preserve operational log JSON behind details, with readable failures and
  capability labels; never label incomplete input coverage as total economic P&L.
- [ ] Regenerate OpenAPI/types, run focused Vitest files and typecheck. Expected:
  tests/typecheck pass; read-only/evidence-denied users receive no financial leakage.

## Task 8: Robust acceptance, documentation and activation

**Files:** Create `tests/test_economic_pnl_acceptance.py`; add synthetic acceptance
fixtures using existing isolated test helpers; delivery report and maintained index.

- [ ] Run a compact synthetic population: cross-currency equity, lagged fund NAV,
  clean/dirty bond inputs with daily accrual, booked dividend/reset, closed position,
  coupon-payment day, missing input and corrected source revision.
- [ ] Verify staging -> request -> independent approval -> publish -> replacement
  with financial totals and frozen lineage at every step. Two actors are required.
- [ ] Test event-only attribution and exact-zero coverage separately from missing data.
- [ ] Use the disposable Python runner and focused UI/API tests; no full suite unless
  a later risk assessment warrants it and the user requests it.
- [ ] Browser acceptance uses synthetic instruments/trades, isolated app/database;
  do not publish operating financial results as a verification shortcut.
- [ ] Document remaining unsupported products, evidence limitations, migration IDs,
  commands/results, API contracts, source-backed conventions and rollback approach.
  Apply operating migrations/configuration only under explicit activation authority.

## Self-review and handoff

The plan reuses the approved foundation and existing price-basis plan; no second
formula/resolver or legacy dataframe persistence is introduced. Daily income,
balance translation and payment recognition are separate. Tasks 2–5 produce the
frozen inputs/components consumed by Task 6, and Task 7 consumes server-returned
versions/state rather than owning financial mutation logic. All five Review Focus
conditions have named test coverage. Execution remains sequential with focused tests.

Each task ends with a delivery-ledger update and a fresh relevant test result.
Commit/push steps are deliberately omitted in accordance with the user's standing
preference; work stays in the current feature checkout until separately requested.
