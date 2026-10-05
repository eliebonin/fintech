# Booking Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans sequentially. No subagents: explicit user preference.

**Goal:** Consolidate shared booking controls without changing product economics or historical replay fingerprints.

**Architecture:** Explicit authorization, strategy, replay and atomicity primitives support existing product writers. Browser decimal and frozen-envelope primitives support existing tickets; no universal booking engine.

**Tech Stack:** Python, SQLAlchemy/PostgreSQL 18, FastAPI, TypeScript/Next.js 16.3.4, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-05-booking-consolidation-design.md`.

## Global Constraints

- Sequential execution in the user-selected existing checkout/feature branch.
- Existing endpoints, fingerprints, saved snapshot shapes and product formulas remain compatible.
- No schema migration, valuation, lifecycle, operating activation, dependencies or push.
- Lightweight tests first; isolated PostgreSQL integration; complete suites at final acceptance.
- User instruction “implement the plan” authorizes execution after preparation of this plan; do not repeat an execution-method question.

## Review Focus

- Direct service callers must not bypass active-actor/membership/module checks, including replay.
- Retired strategy/reference/catalogue must not break an authorized exact retry.
- Caught late persistence errors must leave no partial booking in a usable outer transaction.
- Cash legacy requests without enriched annotations retain their BFF compatibility; stale expected tenant always refuses.
- Decimal exponent values, zero and uncertain retry must not alter economics or frozen payloads.

### Task 1: Characterization and direct-boundary regressions

**Files:** `tests/test_booking_controls.py`, existing booking tests, `apps/reference_api/booking_controls.py`.

**Interfaces:** `authorize_booking(connection, tenant_id, actor_id) -> None`; `lock_booking_strategy(connection, tenant_id, strategy_id) -> UUID`.

- [x] Pin baseline fingerprint/lock hashes and product snapshot behavior before extraction.
- [x] Add direct writer inactive actor/membership refusal tests; run isolated tests and observe refusal missing before implementation.
- [x] Implement shared active actor/tenant writer checks and tenant strategy lock. Reuse from each writer before replay and replace repeated new-write strategy lookups.
- [x] Run focused booking integration tests; commit verified controls.

### Task 2: Replay and atomicity primitives

**Files:** `apps/reference_api/booking_controls.py`, `booking_errors.py`, `repository.py`, `fx_forward_booking.py`, `option_booking.py`, `product_booking.py`; `tests/test_booking_controls.py`.

**Interfaces:** `booking_lock_key(tenant_id, endpoint, key) -> int`; `find_booking_replay(connection, tenant_id, endpoint, key, fingerprint) -> UUID | None`; `record_booking_replay(connection, tenant_id, endpoint, key, fingerprint, trade_id) -> None`. Common errors retain repository re-exports.

- [x] Add hash/namespace and late-annotation failure regressions; observe missing savepoint on cash direct call.
- [x] Extract replay lock/query/check/register without changing normalization adapters. Each writer owns a savepoint; authorized replay precedes current eligibility checks.
- [x] Verify changed request conflict, retired-reference/strategy replay, no partial rows and continued outer transaction; commit.

### Task 3: Shared locking and integrity checks

**Files:** affected booking/reference loaders and existing concurrency tests; `docs/delivery/booking-controls.md`.

**Interfaces:** Explicit documented resource ordering, preserving existing shared-reference UUID acquisition.

- [x] Inventory actual booking and management lock paths; reproduce any conflicting paired orders before fixing.
- [x] Correct only proven conflicting order/visibility paths; preserve authoritative checks. Use existing concurrency schedule tests plus new tests for identified gaps.
- [x] Run focused concurrency/replay integration checks; record concrete order and remaining limitations; commit.

### Task 4: Exact browser arithmetic

**Files:** `apps/ops-console/src/lib/booking-decimal.ts`, its test, four ticket model consumers.

**Interfaces:** `parseBookingDecimal(text, limits?) -> {value: bigint; scale: number} | null`; `formatBookingDecimal(value, scale) -> string`; `exactBookingAmount(factors: string[], divisor?: string) -> string`.

- [x] Add hand-calculated decimal/scientific/zero/negative/overflow/nonexact regressions; observe missing shared implementation.
- [x] Extract bounded exact primitives; product models retain formulas and input-validation restrictions. Preserve baseline preview results; extend API convention exponent support.
- [x] Run all ticket model tests and precision regressions; typecheck; commit.

### Task 5: Frozen envelope and BFF guards

**Files:** `apps/ops-console/src/lib/booking-submission.ts`, `booking-write-guard.ts`, tests and existing ticket/BFF consumers.

**Interfaces:** `freezeBookingSubmission(payload, key, expectedTenantId) -> {payload, key, expectedTenantId}` (retains the existing cash helper argument order); `bookingSubmissionOptions(envelope) -> RequestInit`; booking-write guard returns context/payload/key or controlled response, with explicit legacy-cash expected-tenant mode.

- [x] Add frozen payload mutation and missing/stale tenant/key/JSON tests; pin existing cash legacy behavior.
- [x] Extract freeze/request mechanics, retaining each ticket's UI states/conflict behavior. Reuse BFF guard without modifying proposal rules.
- [x] Run ticket state/navigation and BFF tests plus whole frontend suite; commit.

### Task 6: Acceptance, documentation and self-review

**Files:** `docs/delivery/booking-controls.md`, `booking-capability-matrix.md`, delivery index and execution evidence.

- [x] Run cross-product direct/API tests for denial, replay, rollback, stale terms and saved history; check final diff as separate self-review (no delegated reviewer per user instruction).
- [x] Run `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py -q`, `pnpm test:ops-console -- --maxWorkers=2`, typecheck/build and both contract checks. Read results; repair failures with regressions.
- [x] Exercise synthetic browser booking review/edit/confirmation/history and tenant protection; keep operating services untouched.
- [x] Publish current capability matrix and shared-controls/lock reference; record commands, warnings, rulings and limitations. Mark completed tasks, commit locally, report results without pushing.
