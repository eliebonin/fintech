# Booking consolidation acceptance

**Status:** Accepted for the scoped booking consolidation; not production-readiness sign-off

**Review:** Sequential author self-review, not independent approval

**Baseline:** `87f097c`, branch `codex/enriched-trade-booking`

## Scope review

Compared all changed writers, frontend consumers and new helpers against the approved [design](../../superpowers/specs/2026-10-05-booking-consolidation-design.md). Authorization precedes replay in each public writer; active strategy checks are new-write-only; each writer owns a savepoint; helpers do not commit; product normalization/snapshot construction remains in its original adapter. Existing errors remain import-compatible through repository re-exports. BFF guards use server-selected identity, retain the explicit legacy cash exception, and do not change proposal semantics. Exact arithmetic retains separate product formulas and frozen envelopes retain retry identity.

No Critical/Important issue was identified in this author review. This is weaker assurance than an independent reviewer and does not certify authentication, all concurrency combinations, valuation or lifecycle correctness.

Deferred minor findings: the proposal-only tail of `product-booking-bff` still contains unreachable booking conditions after the new early booking branch; older compact formatting and unused imports are retained to avoid unrelated cleanup. Scientific zero/negative-zero in historical detail is a display issue, not altered economics; it remains outside this mechanics refactor. Broader cross-resource concurrency coverage is a known limitation, not a proof supplied by the new organization-order regression.

## Commands and observed results

| Check | Evidence |
|---|---|
| Lightweight booking rules | 64 passed before consolidation |
| Direct denial / cash atomicity RED | 23 failed, 1 compatibility check passed; schema-invalid fixture value corrected before product edits |
| Cash/control GREEN | 28 passed, 32 seed warnings |
| Focused cross-product backend | 208 passed, 12 warnings, 323.97s |
| `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py tests/test_booking_controls.py tests/test_generic_swap_booking_api.py -q --tb=short` | 79 passed, 242.90s; organization deadlock test first failed with SQLSTATE40P01 |
| Exact decimal/product model checks | 59 passed; FX/option scientific values had two RED regressions before GREEN |
| Ticket state/navigation and BFF focused checks | 162 passed |
| `pnpm test:ops-console -- --maxWorkers=2` | Rerun: 435 passed, 98 files, 44.10s. First run: 433 passed and two 15-second import/load timeouts; no assertions failed and no changes intervened |
| `pnpm typecheck:ops-console` | Exit 0 |
| `pnpm build:ops-console` | Exit 0, production routes compiled |
| `pnpm contract:check` and `pnpm contract:generate:check` | Exit 0; generated contract unchanged |
| `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py -q --tb=short` | 723 passed, 479 warnings, 1221.02s (20m21s), exit 0 |
| Browser | Synthetic swap review/edit/confirm/detail/history; cross-tab stale cash tenant refusal passed |

The isolated runner creates and drops only its uniquely named test database, redirecting hard-coded legacy test engine URLs inside that process. It does not run integration tests against operating data. Warnings include existing synthetic-fixture reference insertion, SQLAlchemy `Result.tuples()` deprecations, Starlette 422 constant deprecation and Pydantic field-alias metadata in concurrent API schema generation; Git may also report repository-configured LF/CRLF conversion. No dependency or schema update was accepted to silence warnings. All source/test edits preceded the final full-suite runs; subsequent changes only finalized documentation.

Browser used only the retained synthetic database and ports8003/3003. One additional mock swap was recorded; see [shared controls](../booking-controls.md) for its ID and economics. Stale cash submission was refused before the backend booking call. Temporary tabs and task-owned services were stopped; the retained synthetic database was not deleted. Operating services/data were untouched.

## Decisions and handoff

The [shared-controls reference](../booking-controls.md#execution-rulings) contains execution rulings and their costs. Work stays on the current feature branch, with no merge, push or operating activation in this task. No subagent was dispatched. Product capability and exclusions are maintained in the [matrix](../booking-capability-matrix.md).
