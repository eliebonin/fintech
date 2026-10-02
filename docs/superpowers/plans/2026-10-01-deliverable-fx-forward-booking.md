# Deliverable FX-forward Booking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native task-by-task execution, or superpowers:subagent-driven-development if the user explicitly chooses delegation. Steps use checkbox syntax for tracking.

**Goal:** Book one tenant-owned trade directly against an approved deliverable FX-forward instrument, retaining governed annotations and trustworthy history without pretending FX valuation is already supported.

**Architecture:** Introduce an explicit FX booking API alongside the unchanged listing-backed cash endpoint. Resolve instrument economics server-side, reuse annotation/security controls, retain a booking-time economics snapshot in the existing lifecycle event, and add an FX mode to the dedicated ticket. Keep market-data ingestion, discount curves, settlement posting and valuation out of this executable slice.

**Tech Stack:** Existing Python/FastAPI/Pydantic/SQLAlchemy/PostgreSQL, Next.js/React/TypeScript, pytest and Vitest; no new runtime dependencies.

**Spec:** `C:/Users/forte/Documents/ChatGPT/Tech V2/fx-forward-alpha-design-proposal.md` (approved 2026-10-01).

Status: Planning complete; implementation not started. Native execution recommended because the tasks share booking contracts and state handling. Await review before executing.

## Global Constraints

- Initial scope: DELIVERABLE forwards with one already-agreed, resolved settlement/value date. NDF, CASH, FX swaps and split currency dates remain unbookable through this slice.
- Quantity is a positive input amount in base currency. BUY receives base/pays quote; SELL pays base/receives quote. Store signed base quantity using existing trade convention.
- Rate and settlement are read-only inherited terms. API resolves them authoritatively; client values, if echoed for stale-context detection, cannot override terms.
- Require an active governed counterparty for the bilateral forward.
- Do not debit quantity times rate at execution. No automatic settlement postings, fees, cancellation or early termination are introduced in the booking slice.
- Preserve cash API compatibility. Introduce explicit FX request/dispatch semantics rather than making every required cash field optional.
- If any supplied settlement/final/cash date conflicts, reject booking with an enrichment exception. Do not alter historical terms or apply a blanket migration.
- Business-day adjustment rules, unadjusted maturity inputs, split dates and NDF fixing/payment dates are a later confirmation-enrichment slice.
- Booking does not imply supported valuation. Existing P&L must expose an explicit unsupported-FX exception rather than compute quantity times exchange rate as derivative value or quietly omit the position from an apparently complete total.
- Existing dirty checkout belongs to the user. Preserve unrelated changes and record the initial diff. No automatic commit, destructive cleanup, app restart or live-database mutation. Use the previously selected current checkout/feature branch when execution begins, after checking applicable isolation instructions.
- This plan/spec are workspace review artifacts. On execution, add their approved copies to repository documentation using authorized file access; do not claim they are already committed or canonical.
- Read `apps/ops-console/AGENTS.md` and relevant installed Next documentation before frontend implementation.

## Review Focus

1. A changed or retired contract after selection must block a new booking, but an identical already-committed retry must still replay (Task 2).
2. Existing contradictory settlement dates must not be silently replaced by maturity (Tasks 1–2).
3. Small/high-precision notionals and rates must not lose precision or be rounded as currency cash prematurely (Tasks 1, 3–4).
4. Generic visibility must not bypass private-instrument, strategy or governed-counterparty tenant checks (Task 2).
5. A mixed cash/forward strategy must not show a seemingly complete P&L total that omits or misprices forwards (Task 5).

## Task 1: Pure FX economics and eligibility rules

**Files:** Create `security_master_schema/fx_forward_booking.py`; create `tests/test_fx_forward_booking_rules.py`.

**Interfaces:**
- Frozen `FxForwardBookingTerms`: instrument_id/base_currency_id/quote_currency_id UUIDs; base_currency/quote_currency/quote_convention/settlement_type strings; agreed_rate Decimal; maturity_date date; settlement_date/cash_settlement_date/final_settlement_date optional dates.
- `FxForwardBookingError(code: str, field: str, message: str)` represents actionable business exceptions; map to API problems in Task 2.
- `resolve_fx_forward_settlement(terms: FxForwardBookingTerms) -> date`: require maturity and positive rate/distinct currencies; require DELIVERABLE and convention exactly `{QUOTE}_PER_{BASE}`. Explicit dates must equal maturity; absent dates fall back to maturity. No auto calendar adjustment.
- `derive_fx_forward_obligations(terms: FxForwardBookingTerms, side: Literal['BUY','SELL'], quantity: Decimal) -> FxForwardObligations`: frozen result containing signed_base_quantity, receive_currency, receive_amount, pay_currency, pay_amount and settlement_date. Require quantity > 0 and at most 18 integer/12 fractional digits (trade Numeric(30,12)); compute multiplication with sufficient Decimal precision (at least 80), no float conversion or currency rounding.
- `fx_forward_terms_fingerprint(terms: FxForwardBookingTerms) -> str`: SHA-256 of normalized immutable IDs, currencies, rate, convention, dates and settlement type; numerically equal Decimal encodings produce the same digest.

- [ ] Write failing parameterized tests: `test_buy_sell_obligations` asserts BUY EUR 1000000 at 1.10 receives EUR 1000000/pays USD 1100000; SELL reverses; `test_precision_preserved` asserts 0.000001 × 1.123456789012 = 0.000001123456789012; `test_settlement_inherited` asserts maturity 2026-12-15 with no explicit settlement resolves to that date.
- [ ] Add failing `test_conflicting_dates_rejected`, `test_unsupported_settlement_and_quote_rejected`, `test_invalid_quantity_and_rate_rejected` and `test_fingerprint_numeric_normalization`; require stable exception codes `fx_forward.date_conflict`, `fx_forward.unsupported_settlement`, `fx_forward.unsupported_quote`, `fx_forward.invalid_terms`.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_fx_forward_booking_rules.py -q`; confirm expected missing implementation failures, not unrelated setup failures.
- [ ] Implement the interfaces above and run the same tests to PASS. Keep this pure module independent of DB, provider market data and UI.

## Task 2: Explicit FX booking API, search and immutable storage

**Files:** Create `apps/reference_api/fx_forward_booking.py`; modify `apps/reference_api/contracts.py`, `apps/reference_api/main.py`, `apps/reference_api/trade_properties.py`, `apps/reference_api/repository.py`; create `tests/test_fx_forward_booking_api.py`. Regenerate `packages/api-contracts/openapi/reference-data-api.v1.json` and `packages/api-contracts/src/generated.ts` using existing scripts.

**Interfaces:**
- `FxForwardBookingRequest`: instrumentId UUID, strategyId UUID, side BUY/SELL, quantity Decimal with Task 1 limits, tradeDatetime timezone-aware datetime, counterpartyOrganisationId required UUID, expectedTermsFingerprint required 64-hex string. Same optional trader/broker/purpose/comment/tags/properties/structured references and validation as current TradeBookingRequest. No listingId, executionPrice, settlementDate or marketActivity override. Extra fields forbidden. Shared validation may be extracted; do not weaken the cash request.
- `FxForwardBookingInstrumentView`: instrumentId, name, baseCurrency, quoteCurrency, quoteConvention, agreedRate (decimal string), maturityDate, settlementDate (nullable for ineligible), settlementType, termsFingerprint (nullable for ineligible), bookingEligible bool, ineligibilityCode/message optional. Exclude invisible instruments; retain visible incomplete contracts with actionable reasons.
- `GET /v1/trades/fx-forward-instruments?q=&limit=25&offset=0`: bounded 1–100 limit, nonnegative offset, query max 250; tenant membership and TRADE_WRITE required; deterministic ordering and total metadata. Use existing visible-node scope logic and FX_FORWARD instrument type, not venue/listing search. No arbitrary currency/instrument type returned.
- `GET /v1/trades/fx-forward-instruments/{instrumentId}`: one view with authoritative terms; invisible/missing => 404 without disclosure.
- `POST /v1/trades/fx-forwards`: returns existing TradeDetailResponse, status 201; same Idempotency-Key header and tenant permission rules as cash.
- `load_fx_forward_booking_terms(connection: Connection, tenant_id: UUID, instrument_id: UUID, *, for_update: bool = False) -> FxForwardBookingTerms`: validate visibility, active node/instrument/currencies and effective instrument date; missing eligible terms => explicit error, never manufacture a rate/date. Route-level view loader translates business failures into ineligibility while booking rejects them.
- `book_fx_forward_trade(connection: Connection, tenant_id: UUID, actor_id: UUID, request: FxForwardBookingRequest, idempotency_key: str, request_id: str) -> TradeDetailResponse`.
- `FxForwardTradeEconomicsView`: baseCurrency, quoteCurrency, quoteConvention, agreedRate, settlementDate, receiveCurrency, receiveAmount, payCurrency, payAmount, termsFingerprint, source literal BOOKING_SNAPSHOT. Add optional `fxForwardEconomics` to TradeView for API history/detail; legacy rows without snapshot return null, never invent historical terms.

- [ ] Write minimal failing API tests for BUY, SELL, missing counterparty, forbidden overrides, no timezone and execution UTC date after settlement. Quantities remain exact decimal strings in output. Validate settlement against UTC execution date consistently.
- [ ] Run them with `.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_fx_forward_booking_api.py -q`; confirm expected failures on the new routes/contracts.
- [ ] Add routes/request/search and storage. Use shared annotation validation and persistence, extracting only the common portions of cash persistence if necessary. Preserve cash fingerprint/replay behavior.
- [ ] Make FX idempotency locks and rows endpoint-scoped to `/v1/trades/fx-forwards`. Hash canonical request values, including expectedTermsFingerprint, not mutable catalogue labels. Check existing committed replay before revalidating active terms; changed request/same key => 409. New booking locks/resolves terms and compares fingerprint => 409 `fx_forward.terms_changed` when stale.
- [ ] Atomically insert ONE trd.trade with instrument subject/reference, signed base quantity, CURRENCY_AMOUNT, RATE, inherited agreed rate/quote currency/settlement, null venue/marketActivity; insert parties/annotations/references, lifecycle BOOKED and idempotency row. No cash-flow trade or settlement row.
- [ ] Persist versioned JSON in BOOKED event_payload: schemaVersion=1, kind=FX_FORWARD_BOOKING, base/quote IDs and codes, quoteConvention, agreedRate, settlementDate, termsFingerprint and string receive/pay amounts. Add `load_fx_forward_trade_economics(connection: Connection, trade_ids: Sequence[UUID]) -> dict[UUID, FxForwardTradeEconomicsView]`; batch decode immutable snapshots for tenant-filtered trade IDs in list/detail rather than N+1 current-term queries. Preserve historical rows after instrument retirement.
- [ ] Re-run focused tests to PASS, then export/generate/check contracts: `pnpm contract:export`, `pnpm contract:generate`, `pnpm contract:check`, `pnpm contract:generate:check`. Generated artifacts are mechanical, not handwritten.

## Task 3: Browser API boundary and FX ticket model

**Files:** Create `apps/ops-console/src/app/api/trades/fx-forwards/route.ts`, `apps/ops-console/src/app/api/trades/fx-forward-instruments/route.ts`, `apps/ops-console/src/app/api/trades/fx-forward-instruments/[instrumentId]/route.ts`, their `route.test.ts` files; modify `apps/ops-console/src/lib/browser-api-client.ts`, `apps/ops-console/src/lib/reference-api-client.ts`; create `apps/ops-console/src/app/trades/new/fx-forward-ticket-model.ts` and `.test.ts`.

**Interfaces:**
- Export generated request/instrument/economics types, not parallel handwritten contracts.
- Server client `bookFxForwardTrade(payload: FxForwardBookingRequest, options: EquityProposalOptions, idempotencyKey: string) -> Promise<TradeDetailPayload>`; corresponding list/detail clients reuse existing tenant/server configuration.
- Browser helpers `searchFxForwardBookingInstrumentsFromBff(query: string, offset?: number)`, `getFxForwardBookingInstrumentFromBff(instrumentId: string)`, `submitFxForwardTradeFromBff(payload: FxForwardBookingRequest, idempotencyKey: string, expectedTenantId: string)` return typed API payloads.
- `FxForwardTicketDraft`: strategyId, side, quantity, tradeDatetime, required counterpartyOrganisationId plus existing enriched annotations. No editable rate/settlement fields.
- `buildFxForwardTicketPayload(instrument: FxForwardBookingInstrumentView, draft: FxForwardTicketDraft) -> FxForwardBookingRequest`; `validateFxForwardTicketDraft(instrument, draft, context: TradeBookingContext) -> TicketError[]`. Extract shared annotation validation from existing ticket-model without altering cash behavior.
- `previewFxForwardObligations(instrument, side, quantity)` returns string receive/pay currencies and amounts; adapt existing BigInt decimal multiplication, not Number arithmetic. Date/rate/convention read from instrument only.

- [ ] Write failing BFF tests: absent idempotency => 400; missing expected tenant => 400 for all FX submissions; changed tenant => 409; forward current server tenant headers; preserve field errors/409 vs transport failure. Client-controlled tenant headers cannot select upstream tenant.
- [ ] Write model tests for the Task 1 BUY/SELL and precision examples; inherit terms/fingerprint; ensure payload lacks listingId/executionPrice/settlementDate/marketActivity; reject zero, excessive precision, inactive eligibility and missing counterparty.
- [ ] Run `pnpm --filter ops-console test src/app/trades/new/fx-forward-ticket-model.test.ts src/app/api/trades/fx-forwards/route.test.ts` to establish expected failures.
- [ ] Implement interfaces/routes with existing bffErrorResponse, tenant-session and frozen-retry conventions. Freeze payload/key/expected tenant together; same submission retry never recalculates from edited state. Then run all new model/BFF tests and `pnpm typecheck:ops-console` to PASS.

## Task 4: Dedicated FX ticket, review and mode selection

**Files:** Create `apps/ops-console/src/app/trades/new/fx-forward-ticket.tsx` and `.test.tsx`; modify `apps/ops-console/src/app/trades/new/page.tsx`, `trade-ticket.tsx`, `booking-review.tsx` and corresponding tests; reuse `party-fields.tsx`, `property-fields.tsx` and `governed-selector.tsx` without unrelated UX redesign.

**Interfaces:**
- Existing `/trades/new` defaults to listed cash. Add mode selection linking `/trades/new?product=FX_FORWARD`; keep existing listingId cash context compatible. FX selection is ticket search, not instrument/listing detail booking links.
- `FxForwardTicket({strategies, context})` receives the same strategy/governed context shape as cash, uses Task 3 helpers and existing booking states/focus/error behavior.
- Separate typed FX review props from listing-backed review props. Display headings 'Base-currency amount', 'Agreed forward rate', 'Contract settlement date', 'Receive at settlement', 'Pay at settlement'. Show units explicitly, OTC/no venue and counterparty. Rate/date are read-only text, not disabled inputs relied on for submission.

- [ ] Write failing component tests for mode choice, FX search/selection, visible ineligible reasons, required counterparty, inherited rate/date and BUY/SELL review amounts. No T+2 cash hint appears in FX mode; changing execution datetime never changes settlement.
- [ ] Add failing state tests: failed load does not present empty success; stale terms require reopening/reselecting; back-to-edit preserves custom values; repeated submit disabled; ambiguous transport failure retries frozen payload; tenant switch invalidates selection/retry context. Cash mode regressions remain unchanged.
- [ ] Run new tests to verify expected failures, then implement. Keep any changes to common form components limited to a tested required-counterparty capability and shared annotations.
- [ ] Run `pnpm --filter ops-console test src/app/trades/new` and `pnpm typecheck:ops-console` to PASS.

## Task 5: Historical economics and fail-closed P&L boundary

**Files:** Modify `apps/ops-console/src/lib/trades.ts`, `apps/ops-console/src/lib/trade-history.ts`, `apps/ops-console/src/app/trades/page.tsx`, `apps/ops-console/src/app/trades/[tradeId]/page.tsx`, `apps/reference_api/repository.py::portfolio_pnl`, `apps/reference_api/main.py`, `apps/ops-console/src/app/pnl/[portfolio]/page.tsx`; create `tests/test_fx_forward_history.py`, `tests/test_fx_forward_pnl_boundary.py`; extend `trade-history.test.ts`, `trade-history-page.test.tsx`; create FX detail and P&L page tests alongside their pages.

**Interfaces:**
- Use optional TradeView.fxForwardEconomics from Task 2. FX history labels 'Rate' and 'Base amount' (or explicit per-row units) rather than shares/gross consideration. Null venue renders OTC, not incomplete listing. Detail presents booking snapshot obligations and both currencies; base precision remains visible.
- `FxForwardValuationUnsupported(trade_ids: tuple[UUID,...])` in `apps/reference_api/fx_forward_booking.py`; portfolio_pnl raises it if any booked FX_FORWARD affects the queried as-of strategy, before selecting scalar prices/calculating a total. API maps to 422 ApiProblem code `valuation.fx_forward_unsupported`, message 'This strategy contains FX forwards. FX-forward valuation is not supported yet.' No partial authoritative total; cash-only responses unchanged.
- P&L page distinguishes this known domain exception from API outage and presents explicit unsupported valuation text without a numerical total.

- [ ] Write failing history tests: FX with no listing appears under existing tenant pagination/filtering; snapshot survives retirement/current-term changes; decimal quantities/rates preserved; other tenants cannot read its detail.
- [ ] Write failing P&L tests for forward-only and mixed strategies, with and without apparently usable scalar rates. Both must return the explicit exception, never zero or quantity times rate. Cash-only baseline unchanged; cancelled or future-execution FX follows current as-of/lifecycle filtering.
- [ ] Run isolated focused Python tests and new frontend history/detail/P&L tests to establish failures. Implement the interfaces and batch history snapshot enrichment. Ensure no current-term lookup rewrites booked history.
- [ ] Re-run focused tests and contract export/generation/checks to PASS.

## Task 6: Robust acceptance and delivery documentation

**Files:** Extend `tests/test_fx_forward_booking_api.py`, `tests/test_fx_forward_history.py`, new frontend tests from Tasks 3–5; create `scripts/browser_fx_forward_booking_cycle.mjs`, `docs/delivery/fx-forward-booking-alpha.md`, `docs/delivery/quality-reviews/2026-10-01-fx-forward-booking-alpha.md`; update `docs/delivery/README.md`, `docs/architecture/fx-forward-onboarding-2026-09-08.md` and `docs/research/evidence-register.md`. Quality review date changes to actual execution date if later.

- [ ] Add robust tests: shared/private instrument visibility, forged tenant strategy/counterparty IDs, missing membership/TRADE_WRITE, inactive currencies/instrument, absent terms, conflicted dates, NDF/CASH/reverse convention rejection, retired references, rollback on annotation/reference failure, same-key concurrent submission, replay after reference retirement, changed request key conflict and stale fingerprint rejection. Each asserts no extra trade/cash rows after failure/replay.
- [ ] Run isolated Python regression: `.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_fx_forward_booking_rules.py tests/test_fx_forward_booking_api.py tests/test_fx_forward_history.py tests/test_fx_forward_pnl_boundary.py tests/test_fx_forward_onboarding.py tests/test_trade_booking.py tests/test_trade_booking_api.py tests/test_trade_booking_context.py tests/test_trade_booking_enrichment.py tests/test_trade_history.py tests/test_trade_history_api.py tests/test_governed_trade_configuration.py -q`. Any skips are reported, not counted as passing evidence.
- [ ] Run broader checks after focused PASS: `pnpm test:ops-console`, `pnpm typecheck:ops-console`, `pnpm build:ops-console`, contract checks, then `.venv/Scripts/python.exe scripts/run_isolated_python_tests.py -q`. Record baseline unrelated failures separately; never report the full suite green without successful output.
- [ ] Run a browser acceptance cycle on an isolated synthetic tenant/database (not the operator's trades): approved eligible EUR/USD instrument -> dedicated page -> BUY with custom numeric/reference fields -> review/back/edit -> book -> retry -> history/detail; repeat SELL and tenant switch/ineligible contract; verify cash ticket and explicit mixed-strategy P&L exception. Reuse existing isolated browser harness patterns. Capture evidence and exact counts.
- [ ] Document APIs, field semantics, inherited-date restriction, required counterparty, precision, idempotency, errors and supported/deferred scope. Add approved spec/plan copies to repository documentation under authorized access. Include source links from the spec and applicability caveats in the evidence register; no claim of universal curve/collateral conventions.
- [ ] Review only task-owned diffs against initial dirty-worktree snapshot. Keep unrelated edits intact. No automatic Git commits or app restarts; report actual verification and any genuine blockers.

## Subsequent work, not implementation tasks in this plan

Provider feed interpretation and mappings, curve datasets/valuation policies, exact-maturity interpolation, clean MTM calculation, reporting-currency P&L, settlement accounting and correction/termination each need a subsequent approved design. In particular, a provider rate reconciling to custodian P&L is not sufficient proof of embedded discounting. Unknown quote semantics remain an explicit exception; no guessed curve or silent DF=1 fallback.

## Self-review

Scope coverage: instrument/date/precision rules Task 1; tenant controls/authoritative booking/replay/snapshots Task 2; typed BFF/model Task 3; ticket/review Task 4; history/P&L protection Task 5; strong verification and evidence Task 6. The five Review Focus cases have explicit tests in their owning tasks. No valuation-engine task is hidden in booking. Existing schema has the required trade/lifecycle fields, so no migration is planned unless execution discovers a concrete missing invariant; report that discovery before expanding scope.

## Execution handoff

Please review this plan and confirm it captures the approved design. Recommended method is native execution in this session; the user may instead explicitly choose subagent-driven execution. Implementation begins after plan review, not merely because this document exists.
