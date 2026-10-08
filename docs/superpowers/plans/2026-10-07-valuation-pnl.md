# Valuation and P&L implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. No subagents, automatic commits or pushes; preserve existing checkout changes.

**Goal:** Deliver an auditable listed-equities/ETF valuation and economic P&L alpha inspired by Fortem-core attribution review.
**Architecture:** Pure Decimal economics and historical replay feed frozen-input calculation. Transaction-bound immutable results feed separately persisted operational attempts and staged review/publication.
**Tech stack:** Python, Decimal, SQLAlchemy, PostgreSQL, FastAPI, Next.js; existing resolver and permissions.
**Spec:** [valuation/P&L design](../specs/2026-10-07-valuation-pnl-design.md).

## Global constraints

- Existing feature checkout; sequential execution; no runtime legacy dependency.
- No settlement/accounting/full-NAV/return-performance claims, permission bypass or unsupported-product fallback.
- Exact decimal serialization; tenant scope; separate economic and information cutoffs.
- Lightweight RED/GREEN tests before product code; isolated DB verification before broad suites.

## Review focus

Same-day round trips; late-recorded cancellations; unsupported lifecycle events; large/high-precision decimal inputs; stale publication after another batch changes the official population.

### Task 1: Decimal attribution kernel

Files: `valuation/economics.py`, `valuation/__init__.py`, `tests/test_valuation_economics.py`.
Interface: `MarketInputs` -> `attribute_market(inputs) -> MarketAttribution`; `validate_totals(components, market, gross, net)`; deterministic `evidence_hash(payload)`.

- [x] Tests first: unchanged lot 10, prices 100/110, FX 1/1.2 yields PRICE100, FX200, CROSS20, total320; short signs; execution-to-close; precision/invalid values; input hash order independence.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_valuation_economics.py -q` and confirm missing feature failure.
- [x] Implement finite Decimal-only arithmetic, positive factors/FX and canonical string serialization; no floats.
- [x] Verify lightweight suite and record evidence.

### Task 2: Historical positions and period bridge

Files: `valuation/positions.py`, `tests/test_valuation_positions.py`.
Interface: immutable `BookingEvent`, `replay_bookings(events, economic_cutoff, information_cutoff)` returns active booked lots plus retained event evidence. `attribute_period` values opening lots and executions using explicit marks.

- [x] Tests first for opening holdings, period buys/sales, round trip zero holdings, late cancellation, superseded originals/replacement, unknown event and naive time rejection.
- [x] Observe RED, implement pure replay with explicit evidence and no current-status lookup; observe GREEN.
- [x] Preserve trade-level period contributions even when net closing quantity is zero.

### Task 3: Frozen resolver orchestration and readiness

Files: `valuation/service.py`, isolated `tests/test_valuation_service.py`.
Consumes Task1/2; loads tenant-scoped BOOKED snapshots and two date input packages from existing resolver. Rejects unsupported products/series basis/events and preserves selected input identities. Persist resolver snapshots and frozen replay evidence in immutable attribution; standalone full position/NAV snapshots are deferred. No inferred rights.

- [x] Add isolated tests for valid single-currency equities, denial/missing/stale/unknown calendars, unsupported products, correction history and transaction rollback.
- [x] Implement explicit readiness and product allowlist; no partial complete total.
- [x] Verify isolated suite and record limits.

### Task 4: Durable attempts, immutable attribution and review batches

Files: `valuation/storage.py`, `security_master_schema/models.py`, additive Alembic migration, `tests/test_valuation_storage.py`.
Consumes immutable calculated results. Produces attempt/event records independent of financial rollback; complete immutable attribution versions/components; tenant/strategy/date authoritative staged batches. Incremental supplementation is explicitly rejected until its complete-population bridge is implemented.

- [x] Tests first for retry idempotency, immutable financial evidence, tenant isolation, failure evidence, stale population, unresolved breaks and independent reviewer.
- [x] Implement scoped transactions, typed subject FKs, canonical hashes, atomic publication and append-only decision evidence.
- [x] Verify migration round trip and isolated PostgreSQL behaviour. Do not migrate operating DB before isolated verification.

### Task 5: Tenant API and review UI

Files: dedicated `apps/reference_api/valuation_routes.py` and contracts; `/valuation` page and BFF routes; focused API/frontend tests.
Consumes Tasks3/4; exposes start run with fail-closed readiness validation, inspect run/inputs/components/logs, Ops explanation, review/publish. A separate preflight-preview endpoint is deferred. Read/write/review authority enforced server-side, no browser arithmetic.

- [x] Tests first for context/permissions/errors, incomplete and NOT_COMPARED states, safe logs, duplicate submission and stale reviews.
- [x] Implement bounded paginated reads and idempotent writes; regenerate contracts.
- [x] Verify frontend tests/types, isolated API suite and synthetic acceptance only.

### Task 6: Final verification and delivery record

- [x] Self-review sequentially against spec and all five review-focus cases; no subagents per user instruction.
- [x] Run full disposable Python suite, frontend suite, type/contract and whitespace checks; report actual failures/warnings.
- [x] Update architecture index and delivery evidence with exact supported scope and deferred product/income/manual-adjustment workflows.
- [x] Activate additive local changes only after checks; no automatic permission grant, commit or push.

## Execution ledger

2026-10-07: Plan/spec written before implementation. User's standing no-plan-approval instruction overrides skill approval checkpoints. Current feature checkout retained because it contains approved prerequisite changes. Native sequential execution; commits/reviewer delegation omitted by user preference.

Tasks 1-5 implemented and focused checks verified. Pure Decimal/replay tests observed missing-feature RED before implementation. Service/storage/API tests use owned disposable PostgreSQL. Some frontend transport/rendering tests were added after implementation, not claimed as strict RED/GREEN. Final review regressions observed RED for negative-zero identity, evidence timestamp ordering, module-aware navigation, economic-cutoff/session ordering and publication-summary mismatch, then received fixes.

Refinements: six tables in existing `nav`; real TRADE FK only; component JSON with database reconciliation instead of a separate component table; broader typed subjects, standalone NAV snapshots, incremental updates, external-comparison ingestion and manual adjustments deferred. No unsupported capability or rights inferred. VALUATION + MARKET_DATA modules are required. Author self-review is not independent signoff.

Evidence so far: final combined 78 focused Python checks including migration round trip and publication guard; 607 frontend tests/129 files with two workers; TypeScript and OpenAPI consistency passed. One unconstrained frontend run hit an existing trade-history test's five-second timeout and passed on the lower-concurrency full rerun. Contract regeneration is deterministic; the Git-HEAD generation check flags expected uncommitted content. Full disposable Python regression and local activation are still being finalized.

Full regression initially returned 11 failures/1,151 passes/482 warnings in 1,099.40s. All failures were valuation fixtures assuming a clean shared demo strategy; earlier product-booking tests correctly left real unsupported-family BOOKED evidence there. Ruling: retain production fail-closed guards and give each valuation fixture a separate committed synthetic strategy parent in the owned disposable database. Financial fixture rows remain rollback-scoped. Cost if wrong: fixture lifetime/cleanup; the owned runner drops its complete database, and an explicit database-name guard prevents this setup running on operating data. The owner paused the first targeted rerun; after resume the swap-booking→valuation order regression passed 43 tests/1 warning in 49.18s. Full-suite rerun now in progress.

Task 6 complete: full isolated Python rerun passed 1,167 tests/482 warnings in 1,855.44s; runner exit0 and owned database cleanup (`logs/valuation-python-full-final.log`). Final frontend passed 607 tests/129 files in 159.83s with one worker/15-second cold-import allowance; unchanged assertions and application code. TypeScript, exported OpenAPI consistency, deterministic generated TypeScript and whitespace checks passed. Additional successful HTTP acceptance passed on an independently owned child database. Existing SQLAlchemy/Pydantic warnings remain, not a warning-free claim.

Local activation: operating revision verified 68→69 after checks. Browser opened `/valuation` for the existing demo tenant, showing MARKET-ONLY ALPHA, calculation/staging controls and run history. Restricted-tenant access messaging was verified earlier. No operating financial run, publication, trade, price or rights grant was performed. Implementation and documentation complete for the bounded scope; broader pricing, income/cash, full NAV, external comparisons, adjustment workflows and independent signoff remain deferred. No commit or push.
