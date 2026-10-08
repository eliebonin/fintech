# Historical Booking and Record Corrections Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans sequentially, as requested by the user. Steps use checkbox syntax for tracking.

**Goal:** Consistent historical execution eligibility and auditable cancel/replace workflows across supported booking paths.

**Architecture:** Add a shared UTC date rule without moving product economics. Reuse append-only events and existing savepoints/replay; carry an optional correction envelope into existing writers and finalize both linked records atomically. Add tenant-protected detail actions and a shared correction gate around normal tickets.

**Tech Stack:** Python, FastAPI/Pydantic, SQLAlchemy/PostgreSQL, Next.js/React/TypeScript/Vitest.

**Spec:** [Historical booking and corrections](../specs/2026-10-05-historical-booking-and-corrections.md).

## Global Constraints

No valuation/P&L engine, positions, settlements/cash postings, dependencies, new database tables, pushes, operating restart or operating-data writes. Preserve old fingerprints when correction is absent. Use current checkout/feature branch, preserve existing dirty work, run database tests only in isolated databases. User waived further design approvals and requested sequential execution; no subagents or automatic commits.

## Review Focus

- UTC boundary offsets: settlement/reference dates use normalized execution date.
- Retired configuration and replay: exact authorized retry works, new historical writes do not bypass current visibility.
- Concurrent cancel/replace: exactly one winner, sequence conflict for the loser, no orphan replacement.
- Unknown/legacy lifecycle evidence: fail closed rather than invent BOOKED history.
- Uncertain UI result and tenant switch: retain identical reviewed envelope; stale tenant cannot mutate another tenant.

### Task 1: Historical date controls

Files: `apps/reference_api/booking_controls.py`, `contracts.py`, all four writer adapters; option/FX read routes and frontend search clients/tickets. Tests: `tests/test_historical_booking.py`, option/FX API regressions and ticket tests.

Interfaces: `validate_execution_date(execution: datetime, *, today: date | None = None) -> date`; date-aware FX/option read/load functions default to UTC today, optional `asOfDate` query.

- [x] Add lightweight RED tests for timezone conversion, future UTC date refusal and UTC settlement ordering.
- [x] Implement guard after replay, before new-write reference lookup in all seven paths.
- [x] Add RED API tests for execution-date option/FX eligibility; use dated effective bounds and contract-unit selection, no retired-definition fallback.
- [x] Implement optional as-of read parameters and search date controls with invalidation; keep normal snapshot fingerprints stable.
- [x] Run focused isolated API and frontend tests. Historical fingerprint golden test unchanged.

### Task 2: Append-only cancellation and atomic replacement

Files: new `apps/reference_api/trade_corrections.py`, additive contracts, four writers and detail view. Existing schema only. Tests: new `tests/test_trade_corrections.py`.

Interfaces: `prepare_correction(connection, tenant, request, kind)`, `complete_correction(connection, tenant, actor, request, new_trade_id)`, `cancel_booking(...) -> TradeDetailResponse`; optional correction envelope `{tradeId, expectedSequenceNo, reason}`; cancellation request `{expectedSequenceNo, reason}`.

- [x] Add RED tests for cancellation retaining economics/BOOKED, opaque foreign IDs, stale sequence, mandatory reason and absent/unsupported evidence.
- [x] Implement current authorization, scoped replay, trade-row locking, append-only event and status projection.
- [x] Add RED tests for cash atomic replacement, invalid new ticket rollback, reciprocal links, unchanged fingerprints and repeated correction chain.
- [x] Wire replacement preparation/finalization through all product paths; reuse existing product/annotation validators and savepoints.
- [x] Add concurrency, revoked writer, after-retirement replay and immutable-trigger regressions. Final full-suite result pending below.
- [x] Prevent existing P&L from claiming a historical result when corrections in that strategy need replay; no pricing implementation.

### Task 3: Detail actions and normal-ticket correction gate

Files: new client correction controls/gate, detail page, booking page, four ticket components, cancel BFF/client and generated contracts.

Interfaces: `CorrectionBookingGate` clones the selected ticket with a confirmed correction prop; each ticket uses the shared `withBookingCorrection` payload decorator. Ordinary payloads stay unchanged. Original summary, reason and same-strategy ticket are visible; links retain predecessor/successor IDs. Prop injection avoids introducing a React context dependency into the established shallow component test harness.

- [x] Add RED component/BFF tests for explicit confirmation/reason, frozen cancellation retry, tenant header refusal and correction payload/links.
- [x] Read installed Next.js route/client documentation; implement accessible record-cancellation review and correction gate. No product switching in a replacement ticket; re-entry explicit, no stale annotation copies.
- [x] Regenerate API contracts; run frontend/type/contract checks. OpenAPI check passes; TypeScript regeneration is byte-identical. Stock Git-diff-based generate check reports intentional uncommitted changes, not a clean HEAD.

### Task 4: Verification and delivery record

- [x] Author review against spec and review focus; reproduce/fix material findings test-first.
- [x] Run complete isolated Python suite, frontend suite, typecheck and contract checks; report failures rather than hiding them. Final Python rerun: 830 passed. Frontend: 477 passed. Build/types/OpenAPI check passed; see the delivery record for initial fixture failures and the Git-diff-based generation-check limitation.
- [x] Attempt isolated synthetic browser walkthrough; partial observations only, interrupted and then policy-blocked. No end-to-end browser acceptance claim or operating-data edits. See delivery record.
- [x] Document actual behavior, source applicability, evidence, deferred lifecycle work and activation status in delivery index/matrix. Final suite result recorded. No push or operating restart.

Self-review: interfaces agree, all requirements have tests/work steps, optional correction removal preserves legacy hashes. Conservative historical rules and cancelled-record semantics are explicit. This plan's implementation ledger is the delivery record; no separate scratch shell scripts/commits required in the shared dirty Windows checkout.

Execution record: [historical booking and corrections alpha](../../delivery/historical-booking-and-record-corrections-alpha.md). Later typed contractual lifecycle remains planned, not delivered by this record-correction slice. Browser security policy was respected without alternate access paths. Disposable preview services/data were cleaned up; interrupted Python verification was restarted with a durable report.
