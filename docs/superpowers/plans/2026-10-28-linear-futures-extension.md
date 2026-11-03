# Linear futures extension implementation plan

> Execute sequentially with superpowers:executing-plans and lightweight tests first, as requested by the user. Preserve the dirty checkout; no subagents, automatic commits or pushes. Execution is complete; actual checks and scope rulings are recorded in the ledger below.

**Goal:** Enable the existing linear crypto future families for cash and physical settlement through booking and supplied-price daily P&L, preserving existing index futures.

**Architecture:** Share capability validation below the API, preserve frozen contract economics, and reuse the exact-contract daily-variation adapter and governed publication workflow. Delivery processing remains separate.

**Tech stack:** Python Decimal, Pydantic, SQLAlchemy/PostgreSQL, FastAPI and existing React/Next forms and inspector.

**Spec:** [Design, economics, boundaries and research](../specs/2026-10-28-linear-futures-extension-design.md).

## Global constraints

- Existing family → contract → listing hierarchy stays; no generic or continuous future stands in for an expiry listing.
- Supported forms in this increment: existing INDEX_POINTS/CASH and existing linear crypto UNDERLYING_UNIT/CASH or PHYSICAL. No new commodity/rate/currency-pair reference model, inverse/quanto/perpetual or daily financing-adjustment adapter.
- Multiplier applies once. Preserve signed CONTRACTS, decimals, exact quote/divisor, negative-price permission and execution prices. No fabricated zero, spot-price substitution, automatic expiry or delivery cash/asset posting.
- Source/strategy/tenant authority, calendar, freshness, information cutoff, fingerprint and publication revalidation remain in force.
- Preserve original index snapshots/hash serialization. Do not rewrite historical evidence or grant permissions to make tests pass.
- No schema change is expected from the current model; if an essential evidence field is absent, add it explicitly and document the migration instead of inventing a value.

## Review focus

1. Cash versus physical settlement changes lifecycle, not the compatible linear daily bridge; both must pass native booking/P&L tests.
2. Crypto contract size must not be multiplied twice or confused with spot token quantity.
3. Same-day/new/partial/full/short-crossing trades retain their actual execution contribution, including expiry-day closure.
4. Contract price, economic date, actual observation date, exchange calendar and quote-currency FX remain distinct from the spot asset's data.
5. Current family changes and caches must not alter original economics or bypass per-trade/tenant/licensing checks.

## Task 1 — Shared linear capability and reference checks

**Files:** create `security_master_schema/future_economics.py`; modify `apps/reference_api/product_booking.py`, `security_master_schema/future_valuation.py`; test `tests/test_future_specification_rules.py`, `tests/test_future_specification_api.py`, `tests/test_future_frozen_valuation.py`.

**Interface:** `require_linear_future(convention: FutureConvention) -> None` accepts the supported coherent linear forms, raising ValueError for unsupported quotation/settlement combinations. It does not authorize references or change numeric values.

- [x] Write failing cases for linear UNDERLYING_UNIT/CASH and PHYSICAL acceptance, inconsistent size/divisor/basis rejection and unchanged INDEX_POINTS/CASH behavior.
- [x] Run those nodes to observe the current blanket refusals.
- [x] Implement shared capability validation. Replace crypto/index-only refusal paths, using active visible governed underlying checks appropriate to the family type; keep locking, family/convention/date parity and approval checks.
- [x] Freeze sufficient new-booking facts and preserve historical index JSON/fingerprint behavior. Test changed current family economics and corrupted cached/uncached trades cannot reprice or bypass validation.
- [x] Run affected pure rule/frozen tests, then native reference/booking cases through the disposable runner.

## Task 2 — Reconstruction and exact-contract price selection

**Files:** modify `positions/future.py`, `valuation/futures_pnl.py`, `valuation/service.py`; extend `tests/test_future_frozen_valuation.py`, `tests/test_futures_pnl.py`, `tests/test_futures_pnl_integration.py`.

**Interfaces:** preserve `normalize_booking(c, row, snapshot, *, identity_cache)` and `future_mark_context(projection, subject, cutoff)`; the latter returns the actual frozen FUTURE_PRICE_BASIS rather than hard-coded INDEX_POINTS, plus its compatible convention.

- [x] Add failing native booking→reconstruction→price-selection cases for cash and physical crypto contracts with separate dated listings.
- [x] Reuse the shared capability check and existing historical identity recovery. Bind selected series to exact contract, actual quotation basis/divisor and quote currency.
- [x] Reject spot/other-expiry/wrong-basis/wrong-currency inputs. Verify current source rights, inverse-FX permission, separate exchange calendars and unavailable observations still behave as before.
- [x] Keep trading cutoff versus final price boundary separate; test valid final-day marks/closure and explicit unclosed exposure after final settlement. Assert no synthetic close, token holding or cash write.

## Task 3 — Numerical and governed financial acceptance

**Files:** reuse `valuation/futures_pnl.py`, `valuation/position_storage.py`, `valuation/storage.py`; extend `tests/test_futures_pnl.py`, `tests/test_futures_pnl_integration.py`.

- [x] Pin unchanged 2×5 BTC contracts, prices 100000→101000, to 10000 USD / 8000 GBP at 0.8 FX. Pin synthetic physical 3×1 BTC contracts, +500 price move, to 1500 USD.
- [x] Test new trades, shorts, partial/full closes, round trips and cross-through-zero, zero marks, explicitly permitted negatives, disallowed negatives and missing mandatory price/FX. Confirm no second listing or contract-size multiplier.
- [x] Test foreign multi-day results sum each day's variation at that day's FX; unchanged future prices create no gross-notional FX P&L.
- [x] Stage a mixed index/cash-crypto/physical-crypto portfolio; amend an allowed component and publish under existing independent authority. Verify explicit futures reconciliation, null contract-MTM asset fields, immutable inputs and source-revocation/tenant denials.

## Task 4 — Booking and result UI

**Files:** modify as needed `apps/ops-console/src/app/trades/new/product-ticket.tsx`, its `product-ticket-model.ts` and tests, `apps/ops-console/src/components/product-convention-form.tsx`, `future-family-form.tsx`, `future-expiry-form.tsx` and `apps/ops-console/src/features/valuation/futures-pnl-inspection.tsx`. No new screen is required.

- [x] Add focused display tests for size/multiplier applied once, quote currency, cash/physical settlement and relevant delivery dates; replace blanket crypto/physical creation-only wording with authoritative readiness.
- [x] Preserve existing form context stamps, permission-aware errors, idempotent retries and locked family terms. Do not add per-trade contract economics the family/contract already owns.
- [x] Remove the convention editor's hard-coded INDEX_POINTS assumption for configured crypto families: preserve the approved actual basis, size and delivery terms, without allowing a convention amendment to redefine the family. Retain existing index behavior and test both forms.
- [x] In the inspector show contracts, opening/closing and execution prices, actual dates, multiplier/divisor, native variation and reporting FX. Add a concise physical-delivery boundary explanation without suggesting generated cash/assets.
- [x] Run focused Vitest/type checks and isolated Edge booking/inspection journeys with console, responsive and context-switch checks.

## Task 5 — Documentation, activation and final check

- [x] Update F12/F37/F38/F39 affected records in `docs/product/feature-register.md`, `docs/product/feature-implementation-map.md` and their capability pages; update methodology, futures delivery, guidance and limitations together. Keep monetary-preview coverage distinct.
- [x] Run focused Python numerical/frozen/booking/P&L regressions with disposable databases where needed; run OpenAPI/schema parity and frontend checks affected by actual changes. No full Python suite.
- [x] Record test counts and exact remaining scope; verify documentation links/whitespace. No operating mock bookings or valuation publication.
- [x] If no schema change is needed, reload the owned local API only after passing checks and verify health. Document any new migration rather than applying one implicitly.

## Self-review and execution notes

Every design requirement maps to tasks 1–5; review-focus points map respectively to tasks 1/3, 1/3, 3, 2 and 1/2/3. Existing formulas, governance and UI are reused. This is an adapter/readiness extension, not a new futures engine or a delivery/accounting project.

## Execution ledger — 28 October

- **Tasks 1–3 complete:** shared linear validator, type-specific governed references and ordered quote/asset locks; native booking/retries/amendment validation; frozen reconstruction and actual price-basis dimensions; retained convention; common daily variation and governed financial workflow. No numerical engine rewrite or new schema.
- **Task 4 complete:** convention editor preserves approved actual crypto size/basis/currency/delivery facts, readonly economic/date fields, responsive scoped form and normal checkbox sizing. Booking/creation wording and original-convention P&L inspection updated. No separate screen or browser pricer.
- **Task 5 complete:** capability register/map/methodology and root AGENTS/KNOWLEDGE/FIX reconciled with source. Schema 20261028_102 verified read-only; API 8001 reloaded and health OK. No operating financial writes, source grants, new migration, full suite, commit or push.
- Final offline numerical/frozen/rule/architecture/neutrality run: **80 passed**. OpenAPI export check passed.
- Final disposable native booking, crypto P&L, existing product-booking, index-P&L and readiness regressions: **70 passed** (one existing Pydantic header-alias warning). Separate corrected calendar/readiness run: **4 passed**. Earlier broader run passed 54 cases and rejected two incorrectly timestamped calendar fixtures; corrected fixtures retained the historical information-cutoff check. Counts overlap and are not additive.
- Final frontend run: **48 passed** across eight affected form/model/ticket/inspector files; TypeScript passed. New isolated Edge journeys: **4 passed**, cash/physical convention submission and retained P&L inspection, with desktop/mobile/context-header/console checks. Existing index inspector browser also passed before the final scoped CSS change. Physical inspector screenshot inspected.
- Observed REDs: index-only frozen/mark checks, missing shared helper, asset-unit execution amount, native booking and amendment refusal, retained convention field/UI, lock ordering and mobile form overflow. A JSX escaping typo was corrected and TypeScript/browser checks rerun. No financial/immutability or calendar guards were disabled to make tests pass.
- **Ruling:** keep currency roles in the initial lock phase in UUID order and refuse later role changes — newly locking an underlying after a quote could otherwise give reversed crypto pairs opposite lock order — affected product booking/retry/concurrency regressions passed.
- **Ruling:** retain the separate index-only monetary-preview limits — this plan enables P&L and booking, not generic contract MTM or crypto monetary measures. F16/F37/F39 are the affected capability records; F12/F38 were not broadened.
- **Ruling:** no subagents/automatic commits on the pre-existing dirty feature checkout, following the user's standing sequential-work preference. Final review was an author self-review of changed paths, original evidence/factors, locks, date/currency boundaries and UI serialization, followed by the focused acceptance above; it is not an independent whole-repository audit.

See [delivery and remaining scope](../../delivery/linear-futures-extension-20261028.md).
