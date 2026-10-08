# Position Reconstruction Foundation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement sequentially. Implementation and targeted signoff completed 2026-10-08; operating schema activation to revision 70 completed and verified on explicit user instruction. The maintained execution ledger and delivery report are authoritative for outcomes and deviations; the original checklist below is preserved as the planning record.

**Goal:** Establish one cutoff-aware position foundation and move supported valuation/P&L from historical trade ownership to reconstructed positions and period movements.

**Architecture:** A provider-independent `positions/` package reconstructs economic state from immutable ledger evidence. Valuation determines mark requirements and prices the projected buckets; position-owned v2 attribution retains original trade/event lineage and readable v1 history.

**Tech Stack:** Python, Decimal, dataclasses, SQLAlchemy, PostgreSQL, pytest; existing FastAPI/Next.js review surface.

**Spec:** `docs/superpowers/specs/2026-10-08-position-reconstruction-foundation-design.md`

## Global constraints

- Sequential execution; no subagents, full-suite default, automatic commit/push or operating-data mutation.
- No numerical population cap, binary-float financial values, quantity rounding or silent unsupported-event omission.
- Preserve UTC economic/recorded cutoffs, frozen conventions, tenant isolation, corporate-action safety, immutable evidence and current licensing checks.
- Supported valuation scope remains single-currency equity/ETF market-only; cash, income, derivative pricing, settlement and checkpoint storage are excluded.

## Review focus

- Round trip followed by reopening: every period execution contributes, not only the final holding episode (tasks 1/3).
- Mixed subject/convention units: unsafe netting must not hide exposure or omit mark requirements (tasks 1/3).
- Closed intraperiod exposure spanning a corporate action: zero closing quantity must not bypass safety (task 3).
- Late/backdated changes: information cutoff and immutable v1/v2 evidence must stay reproducible (tasks 1/2/4).
- All-flat/empty strategy: valid zero and missing ledger evidence must remain distinguishable through publication/UI (tasks 1/4/5).

## Task 1: Pure position projection

**Files:** Create `positions/__init__.py`, `positions/contracts.py`, `positions/reconstruction.py`, `positions/equity.py`, `tests/test_position_reconstruction.py`.

**Interfaces:** `reconstruct(facts: Iterable[LedgerFact], request: ProjectionRequest) -> PositionProjection`; contracts expose `PositionKey`, `LedgerFact`, `PositionBucket`, `ExecutionEffect`, `ProjectionRequest`, `PositionProjection`. Equity adapter validates frozen product conventions without querying market data. LedgerFact carries ordered event evidence and original booking economics; request contains the fields fixed by the spec. Projection contains buckets, movements, lineage and safety inputs, not prices from a provider.

- [ ] Write failing assertions: old +5/-5 excluded from period result; current +2@100/-2@110 gives zero closing position and both movements; subsequent +4 remains a separate movement; -3/+5 yields closing +2; quantity 0.001 remains nonzero; cutoff equality follows <= opening and (opening, closing]; different currencies/factors/subjects are not netted.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_position_reconstruction.py -q -p no:cacheprovider`; confirm failures arise from absent behavior.
- [ ] Implement typed pure reconstruction, exact arithmetic, deterministic lineage, dual-cutoff lifecycle validation and valid empty results; unsupported economics return typed blocking diagnostics, never partial success.
- [ ] Add historical correction, unknown effect, missing/duplicate sequence, same-time permutation, sign reversal, and definition-ID-only-change tests. Verify expected buckets/movements and input hashes are deterministic.
- [ ] Run the same focused command; all tests pass. Self-review contract and edge cases.

## Task 2: Scoped ledger reader

**Files:** Create `positions/repository.py`, `tests/test_position_repository.py`; modify `valuation/service.py` only to introduce its adapter boundary, not activate v2 yet.

**Interfaces:** `iter_ledger_facts(connection, request: ProjectionRequest) -> Iterator[LedgerFact]`. Enforce tenant-strategy ownership, use the caller's stable transaction and deterministic chunked reads without a result cap or unbounded IN lists. Load frozen booking/lifecycle metadata in batches; incomplete evidence blocks.

- [ ] Write disposable DB tests for 1,002+ bookings, multiple read chunks with no duplication/skipping, two tenants, late-known events, and missing BOOKED evidence; exact expected IDs and totals are asserted.
- [ ] Run with `scripts/run_isolated_python_tests.py tests/test_position_repository.py -q`; observe expected initial failures.
- [ ] Implement scoped batched reads and metadata decoding; do not consult present-day active flags or mutable multipliers to reconstruct historical economics.
- [ ] Add concurrent-read snapshot control and bounded-query-per-chunk assertions. Run the disposable command to green and record scanned-fact counts.

## Task 3: Position-based valuation and bridge

**Files:** Create `valuation/position_calculation.py`, `tests/test_position_valuation.py`; modify `valuation/service.py`, `valuation/corporate_actions.py`, `valuation/economics.py`.

**Interfaces:** `required_marks(projection: PositionProjection) -> tuple[MarkRequirement, ...]`; `attribute_projection(projection: PositionProjection, marks: Mapping[MarkKey, Decimal]) -> PositionPeriodAttribution`. MarkKey identifies subject and opening/closing cutoff. Typed result contains position lines, execution lineage and exact opening/closing/execution values. Mark types live in `valuation/position_calculation.py`, not the position foundation.

- [ ] Write failing pure tests: opening 0/buy2@100/sell2@110/close0 => P&L20 and no mark requests; +4 remaining => closing mark required; flat pre-opening bucket => no line or marks; opening exposure => opening mark required; exact total bridge in all cases.
- [ ] Implement the v2 single-currency bridge and PRICE decomposition using bucket-specific frozen normalisation. Preserve missing-required-price blocking and Decimal precision checks.
- [ ] Extend conservative corporate-action checks to projected relevant exposure intervals, including closed period positions; missing/ambiguous dates and unsupported effects block before net-zero shortcuts. Do not claim corporate-action replay.
- [ ] Run `tests/test_position_valuation.py`, `tests/test_valuation_economics.py`, and `tests/test_valuation_corporate_actions.py` focused; add disposable tests proving no resolver calls for zero opening/closing exposure and retained safety blocking on a closed round trip.

## Task 4: Immutable position-owned results

**Files:** Modify `valuation/tables.py`, `valuation/storage.py`, `valuation/evidence_access.py`; create a new additive Alembic revision under the repository's existing migration directory and `tests/test_position_attribution_storage.py`.

**Interfaces:** Add typed position attribution and lineage storage consumed by `stage_position_result(connection, attempt_id, result: PositionPeriodAttribution) -> UUID`. Position identity and full period/cutoffs/method participate in result identity; linked source trade/event IDs are not fabricated owners. Review batch format explicitly discriminates v1 trade-owned and v2 position-owned results.

- [ ] Write failing disposable tests for immutable v2 rows/lineage, exact totals, zero-result batches, idempotent repeats, changed cutoffs/conventions, and readable existing v1 history.
- [ ] Add schema constraints/immutability enforcement and storage adapters; keep existing v1 rows untouched. Extend permission checks to v2 source selections; empty selections are allowed only for evidenced no-mark v2 results, not arbitrary malformed financial evidence.
- [ ] Test AUTHORITATIVE v2 publication replaces the complete official population, including removal of prior v1 items, atomically; stale review and self-publication protections still apply. Test rights revocation and safe redaction.
- [ ] Run the isolated storage/API regression bundle. Review additive migration and fresh/disposable upgrade; do not migrate the operating database during this task.

## Task 5: Runner/API and review presentation

**Files:** Modify `valuation/runner.py`, `apps/reference_api/valuation_routes.py`, `apps/ops-console/src/components/valuation-console.tsx`, their existing tests; create `tests/test_position_valuation_acceptance.py`.

**Interfaces:** Current request endpoint dispatches the versioned position calculation; result DTO distinguishes position lines from legacy trade lines. Display original trade lineage separately. Do not imply market-only P&L is complete NAV or realised accounting P&L.

- [ ] Write failing acceptance tests for both formats, position labels, period execution links, valid zero results, permissions, duplicate retries and unchanged API input constraints.
- [ ] Wire v2 through existing stable transaction/idempotency/review pipeline; add operational counts for facts scanned, buckets retained, executions, mark requests and stage timings, without exposing provider prices in safe logs.
- [ ] Update UI rendering after reading frontend AGENTS/bundled Next.js guidance. Preserve permission-aware messaging and make flat-position period P&L visible.
- [ ] Run scoped API/runner/acceptance tests on a disposable DB, focused UI tests and TypeScript checks. Confirm no operating-data writes.

## Task 6: Equivalence, performance evidence and cutover

**Files:** Extend `tests/test_position_valuation_acceptance.py`; update `docs/delivery/valuation-market-pnl-alpha.md`; create `docs/delivery/position-reconstruction-foundation.md`; remove the superseded v1 execution code from `valuation/service.py` and `valuation/positions.py` once no live caller remains.

- [ ] Compare independently expected v2 totals with v1 on simple compatible scenarios. For flat/reopened and missing-unnecessary-mark scenarios, assert the new specification directly rather than treating v1 as the oracle.
- [ ] Benchmark increasing synthetic historical populations with mostly closed episodes; report reads, elapsed time, memory, priced buckets and mark calls. No unmeasured speed or bounded historical-I/O claims.
- [ ] Verify old full replay execution has no production caller; retain historical v1 result readers. Record method-version cutover and remaining checkpoint/correction/lifecycle limitations.
- [ ] Run a targeted position/valuation/permissions/review regression bundle, record exact commands/results and review the diff. Full suite only for a later deliberate broad signoff.

## Later, separate work

Persisted reconstruction checkpoints need immutable versions, information-cut compatibility and backdated-event invalidation. Do not add them before reference reconstruction is accepted. Additional instrument adapters, corporate-action replay, correction economics, settlement/accounting and multi-currency P&L each need their own defined contracts and acceptance work.
