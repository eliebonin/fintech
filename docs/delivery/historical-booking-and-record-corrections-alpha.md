# Historical booking and record corrections alpha

> Historical October 6 delivery checkpoint. Later [trade acceptance](trade-side-acceptance-2026-10-06.md) supplies browser evidence, and [position reconstruction](position-reconstruction-foundation.md) supersedes the blanket correction/P&L refusal described below. Current [F22/F23 scope](../product/features/trade-operations.md#f22-record-corrections) distinguishes removals effective by opening from unsupported in-period removals.

**Status:** Implemented and automated-regression verified alpha; browser acceptance incomplete.  
**Scope:** Ledger recording, not order execution, valuation, settlement or position management.  
**Reviewed:** 2026-10-06.

Design: [research and decisions](../superpowers/specs/2026-10-05-historical-booking-and-corrections.md). Execution: [implementation plan](../superpowers/plans/2026-10-05-historical-booking-and-corrections.md).

## Historical execution rules

All seven supported booking paths share a new-write UTC economic-date guard. A future UTC date cannot be recorded as an executed trade. Today's UTC date is permitted; this is not execution-time or clock-skew certification. Cash settlement ordering and its T+2 weekday convenience default now use the same UTC date as the API. Holidays remain outside that default.

Current active account, tenant membership/module, strategy and tenant-visible reference checks still apply to new historical recordings. Supported approved terms must cover execution; a past date does not authorize retired references, superseded instrument definitions, reconstructed annotation catalogues or unrestricted imports. Existing dated product-convention support remains intact. An expired contract can be back-booked only if its governed reference is still active and the historical execution passes its terms/date checks.

Option and FX-forward search/detail reads now accept `asOfDate`, defaulting to UTC today. Their tickets expose a UTC search date and invalidate results on date changes. This finds supported historical terms; users still enter the actual execution timestamp separately, and writers revalidate against it. No historical-definition fallback was added.

Exact authorized retries are resolved before new-write date/reference/strategy checks, including after reference retirement. Replay still requires current writer authorization. Ordinary payload fingerprints remain unchanged when correction is absent.

## Cancel and replace erroneous booking records

Tenant administrators with current TRADING access can open an eligible trade's detail and choose:

- **Cancel erroneous booking:** reason → review → explicit confirmation. `POST /v1/trades/{tradeId}/cancel-booking` accepts `expectedSequenceNo` and `reason`, with an endpoint-scoped idempotency key. It appends CANCELLED evidence and changes only the record-status projection. Original execution, annotations and BOOKED evidence are retained.
- **Replace erroneous booking:** reason gate → complete normal product ticket → review/confirmation. The original strategy and product category remain fixed. Users re-enter every desired annotation; optional properties, parties, tags and references are not silently copied from old governance. The optional `{tradeId, expectedSequenceNo, reason}` correction envelope is attached to the existing product writer. In one savepoint it creates the replacement, retains its BOOKED snapshot, appends reciprocal CORRECTED/SUPERSEDED lineage and changes the original projection to SUPERSEDED. Failed validation or finalization leaves the original active and no orphan replacement/replay record.

These actions are **record corrections**, not termination of an agreed contract, confirmed delivery, exercise, reversal execution or cash posting. A replacement remains BOOKED; its CORRECTED event records predecessor lineage, not a terminal contractual state. Read booking projections and typed evidence together: the old generic `derive_trade_state` helper, which returns the last event label, is not a correction-aware position/lifecycle replay engine.

Existing fees and any independently maintained downstream records remain attached to their original record; this workflow does not migrate/reverse payments, fees, accounting entries or settled obligations. Consumers must not treat record cancellation as confirmation of those reversals. Typed contractual events and downstream correction authority belong to the later lifecycle/accounting design.

Only supported alpha BOOKED snapshot chains, optionally followed by a valid replacement-origin link, are eligible. Legacy records lacking supported evidence and unexpected/malformed lifecycle chains fail closed. Expected sequence and original-row locking serialize competing changes. Stale cancellation/replacement returns 409; cross-tenant originals are opaque. Cancellation can address an erroneous historic record even if its reference or strategy has since retired; a new replacement must satisfy current new-booking controls.

The BFF derives tenant/actor from the session. Corrections require the expected-tenant header even for otherwise legacy-shaped cash requests. Uncertain cancellation retries retain the identical payload/key/tenant; conflict/access failures require inspecting refreshed history. Link, unload and browser-back guards protect unresolved results. This is in-memory protection, not durable recovery after tab/browser loss.

Audit detail displays correction reason, predecessor/successor links, actor, effective UTC timestamp and recorded UTC timestamp. Correction evidence is effective at the erroneous record's execution time; its recording timestamp identifies when the correction was actually entered. No edit-in-place execution endpoint was introduced.

Trade history still filters/orders by execution date, with its existing default recent-history window. A historical correction does not become a new execution dated today; widen the execution-date filters or follow lineage links to inspect it. A separate correction-activity feed is not included.

## Paused task: booking browser sign-off

**Task status:** RESUMED by the user's 2026-10-06 request to work through the next items, document and implement, without plan-approval checkpoints. Follow [current execution and evidence](booking-signoff-and-lifecycle-execution.md). Automated verification above/below does not constitute browser sign-off.

This is a documented acceptance task. Use an isolated synthetic preview; do not restart or mutate the operating app.

On resumption:

1. Start an agreed app environment and confirm which tenant/data may be used. Prefer isolated synthetic data; do not mutate operating records without authorization. Resolve browser access through supported means, without bypassing the previous security-policy block.
2. Walk through historical booking, erroneous-booking cancellation and replacement across the supported product tickets. Check date/readiness feedback, reason and confirmation steps, and trade-history/detail navigation.
3. Confirm originals and audit evidence remain visible, predecessor/successor links resolve, and replacement economics and annotations match the submitted ticket.
4. Check authorized retries produce no duplicates, stale/conflicting actions are understandable, and failed replacement leaves the original active. Use automated regression evidence for concurrency and rollback cases that cannot be reliably reproduced in a manual walkthrough.
5. Fix any acceptance defects, rerun proportionate checks and document the actual environment, coverage, results and remaining limitations before signing off.

**Exit criteria:** The agreed walkthrough passes, no unresolved blocking booking/correction defects remain, and a dated acceptance report distinguishes browser observations from automated evidence. Until then, browser acceptance remains incomplete; the implementation remains automated-regression verified alpha.

**Excluded:** Contractual settlement, expiry, exercise, redemption, resets, cash posting, valuation and P&L. The later lifecycle sequence below remains separate and is not authorized for implementation by this paused task.

## Lifecycle sequence after this delivery

1. Specify typed contractual events separately from record corrections: FX delivery, option expiry/exercise/assignment, bond redemption/coupons, swap reset/termination and dividends.
2. Define obligations versus confirmed transfers, effective versus recorded dates, partial amounts, failed settlement, trade/holding allocations and reversals. A netted transfer can fulfill several obligations; a corporate action can affect several holdings.
3. Select one authoritative cash/security posting path before implementing those workflows. Do not count both an event movement and an independently entered cash trade as the same payment.
4. Implement and accept bounded product-specific slices; passing a maturity date never automatically proves settlement or closes a record. OPEN/CLOSE remains execution intent, not verified inventory.

These contractual lifecycle workflows are planned, **not implemented** here. No automatic cash entry, settlement, expiry, redemption, reset, dividend or valuation engine was added. As a compatibility safeguard only, the existing alpha P&L refuses strategies containing CANCELLED/SUPERSEDED/CORRECTED events with `valuation.trade_correction_unsupported`: it cannot yet replay corrections at a historical cut and must not silently present misleading totals. This conservative guard applies to all cuts for an affected strategy, not just cuts after correction recording.

## Research and applicability

The `best-practice` review informed the distinction between immutable execution facts, record corrections and contractual events, and reuse of the existing append-only table rather than wholesale event sourcing:

- [FINOS CDM event model](https://cdm.finos.org/docs/event-model/): executions, business events, states and transfers have distinct meaning; lineage is retained.
- [FIX TradeCaptureReportAck](https://fiximate.fixtrading.org/en/FIX.Latest/msg77.html?find=TradeReportID): prior-report references inform explicit correction/cancellation lineage, not a claim of exchange cancellation acceptance.
- [Microsoft event-sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing): immutable compensating evidence, sequence checks and idempotency support auditability; application-wide event sourcing adds complexity and was not adopted.

UTC cutoff, same-strategy/category replacements, administrator access and conservative historical eligibility are project decisions, not regulatory mandates.

## Verification and activation

- Lightweight RED/GREEN checks preceded date controls, historical option/FX eligibility, cancellation/replacement, UI confirmation and payload wiring. Later review reproduced and fixed missing correction-tenant enforcement, cash offset-boundary settlement, malformed predecessor evidence and browser-back protection.
- Focused historical/option/FX suite: 79 passed. Initial cancellation/replacement suite: 11 passed. Expanded seven-product HTTP, replay, conflict, rollback, retirement and concurrency suite: 23 passed; additional immutable-event/malformed-link/same-key concurrency checks are included in the final full run.
- Final isolated historical/shared-control/correction run: **67 passed**, 9 warnings, 27.36s, exit 0. Covers all seven real HTTP replacement paths, cancellation, exact retries, current authorization, tenant ownership, stale sequence, concurrent same-key cancellation, cancel-versus-replace, late-finalization rollback, event immutability, malformed lineage, strategy/product invariance and retirement replay. All four swap contract-boundary cases also pass (6.04s) with an explicit historical test clock; the full run's old future-dated expectation was corrected without loosening production future-date refusal.
- First retained full run: **824 passed, 3 failed**, 490 warnings, 671.53s, exit 1. Failures were the old swap/history tests booking future economic dates and a new legacy test relying on unspecified physical row order after other modules reload demo data. Historical boundary/history tests now use explicit test clocks; the legacy test now constructs its own record with no event evidence. No production booking rule was weakened. All six affected cases pass together (6.58s). A final full rerun includes those fixes and the three late strategy/product/retirement assertions.
- Final full isolated Python suite: **830 passed**, 491 warnings, 644.63s (10m44s), exit 0. Includes all final fixture repairs and late correction assertions. The runner removed its disposable database on exit. Warnings include existing SQLAlchemy tuple deprecations, Pydantic field-alias metadata and Starlette status-name deprecations; this is not warning-free acceptance.
- Final frontend: **477 passed in 108 files**, 32.58s, exit 0; frontend typecheck exit 0. Contract package: **3 passed**, typecheck exit 0; OpenAPI drift check and `git diff --check` exit 0. Generated TypeScript regeneration was byte-identical (SHA256 `00C39707497BECC7BE75611BF671EFADEF490D3E6A96299FD1C9BF999CF86B21`). The stock `generate:check` exits 1 because it compares intentional uncommitted changes against HEAD; it is not reported as passing.
- Production frontend build: exit 0, compiled successfully, TypeScript/static generation completed and both correction routes listed. Built the copied scratch app under ignored `logs/correction-preview/app`, with its own `.next`; the operating app's build directory was not touched. The final source typecheck and frontend suite above ran against the actual checkout, including the late tests.
- Browser acceptance is **incomplete**. In a separate synthetic preview (UI 3005/API 8005), observed the trade-detail correction actions, separate audit dates, replacement-reason gate and historical cash search controls. The interruption stopped that preview. After resuming, browser security policy blocked reconnecting to its tab; no alternate browser path was attempted. End-to-end browser replacement/cancellation success is not claimed. HTTP acceptance covers all seven product paths; component/BFF tests cover UI states and tenant boundaries.
- Sequential author review, not independent subagent sign-off. Review retained the conservative historical boundary and deferred contractual events/durable retry recovery rather than silently expanding scope. No schema migration, new dependencies, GitHub push, operating restart or operating-data write. Only disposable test/preview data was used.
- Preview services were stopped. Both exact correction-preview databases were removed, including the inactive database left by interruption. Their synthetic records are disposable and not retained; source and test fixtures allow recreation. Operating databases were not removed or changed.

Commands: `scripts/run_isolated_python_tests.py -q --tb=short --junitxml=logs/historical-booking-python-final.xml`, `pnpm --filter ops-console test --maxWorkers=2`, frontend and contract `typecheck`, `pnpm contract:check`, deterministic contract regeneration, `git diff --check`. The interrupted full Python run lost its final result when the usage interruption ended the process/session; it is not evidence of acceptance. Retained full runs have separate console/XML reports under ignored `logs/`.
