# FX booking scope hardening — 2026-10-05

**Status:** Implemented and verified for the stated scope

**Scope:** Item 2 from the [instrument integrity review](2026-10-05-instrument-integrity.md). Inactive visibility scopes must prevent current FX selection and new booking. Cash integrity and approval-time dependency revalidation remain separate outstanding items.

## Research and applied decisions

Research accessed 2026-10-05, using primary sources:

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): validate authorization on every request, prefer explicit denial, and test authorization boundaries. Applied here by requiring an existing visibility scope to be ACTIVE as well as shared or owned by the requesting tenant. A previously reviewed ticket is not authorization to write against a now-inactive scope.
- [PostgreSQL 18 explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS): row locks protect against concurrent modification/deletion, and transactions waiting for locks must account for changed rows. Version 18 matches the repository's Docker Compose database image. Applied here by separately locking the optional scope row and rerunning the visibility query before deriving terms or persisting a new trade.

These sources support the authorization and transaction principles, not the platform's product-specific policy. Keeping historical trades/exact authorized retries readable and permitting legacy unscoped references are compatibility decisions retained from the existing implementation. No new scope management interface or product support is introduced.

## Changes

- `repository._visible_node_clause` requires ACTIVE for explicitly scoped records. SHARED_CANONICAL and correctly owned TENANT_PRIVATE remain supported; restricted/foreign/non-active scopes are refused. Legacy records without a scope row retain their existing shared visibility treatment.
- Its current-reference callers are instrument detail/search, reference-node search, `_visible_reference_node` and the FX booking contract query. Trade detail/history do not use this predicate and remain tenant-owned historical read models.
- The FX locked loader retains existing instrument/reference-node locks, then locks its scope separately because PostgreSQL cannot lock the nullable side of an outer join. Existing terms/definition/date/currency locks remain. The reference-node lock also conflicts with a concurrent foreign-key check inserting a scope for an unscoped reference.
- After acquiring locks, the loader rereads the filtered query. If visibility disappeared while waiting, it raises the existing not-found error rather than an uncontrolled missing-row exception.
- HTTP new bookings against inaccessible instruments return the existing 404 without disclosing cross-tenant reference details. No API contract, fingerprint, schema or snapshot changes.
- Exact retries still check current writer authorization and then return the original tenant-owned saved trade before current instrument eligibility. Scope retirement cannot create a duplicate trade or erase history.

The new scope lock is held only in the booking transaction, never while the user reviews a form. This is a narrow FX serialization guarantee, not application-wide deadlock freedom. Other approval/booking paths are not silently given new lock protocols.

## Verification

Lightweight RED run, before production changes:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_fx_forward_booking_api.py -q -k 'inactive_scope or lock_scope or legacy_unscoped' --tb=short
```

Result: **4 failed, 2 passed, 33 deselected**. Failures reproduced inactive shared/private visibility, current catalogue exposure and absent scope-lock protection. Saved-history/replay and legacy-unscoped compatibility passed. An earlier draft test run contained a test import typo; it was corrected before this RED run.

Focused GREEN run:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_fx_forward_booking_api.py tests/test_fx_forward_history.py tests/test_fx_forward_booking_rules.py tests/test_fx_forward_onboarding.py -q --tb=short
```

Initial result: **61 passed, 16 existing SQLAlchemy deprecation warnings, 47.09 seconds**. After adding and correcting the two additional boundary tests, the same focused command passed **63 tests, 16 warnings in 24.34 seconds**, exit 0. Final focused output is retained locally in `.superpowers/sdd/2026-10-05-instrument-integrity/fx-scope-focused.log`.

Added safety/compatibility coverage:

- Inactive shared and private scopes disappear from FX selection/search and refuse stale new-booking requests with no trade created.
- Inactive scopes disappear from current instrument detail and governed reference selection.
- Saved trade detail, history and authorized exact replay survive scope retirement.
- Legacy unscoped FX contracts still book.
- A second PostgreSQL connection cannot revoke the scope while locked terms are held (lock timeout SQLSTATE 55P03).
- HTTP refusal creates no trade.
- Scheduled revocation-first ordering: observe the booking transaction waiting via `pg_blocking_pids`, commit revocation, then require a controlled refusal after the scope lock is acquired.

The first additional HTTP/concurrency run had **1 passed, 1 failed**: the scheduled concurrency check passed, while `test_http_refuses_inactive_scope_without_writing_trade` failed during test setup (`StopIteration` locating a lazily included router). The test now overrides the same connection dependency via a directly registered route. No production change was required for that failure. Final verification is the full Python suite:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py -q --tb=short
```

Full-suite result: **731 passed, 481 warnings in 617.26 seconds (10m17s)**, exit 0. Warnings include existing SQLAlchemy `Result.tuples()` deprecations, Pydantic field-attribute warnings and Starlette status-name deprecations. The first full-suite session's final result was unavailable after resuming; no success is claimed for that run. The completed fresh run retains output in `.superpowers/sdd/2026-10-05-instrument-integrity/fx-scope-full-suite.log`. `git diff --check` passed (only Windows line-ending notices). Tests use disposable migrated/seeded databases and never the operating database. No frontend code changed; no frontend suite rerun, restart, deployment, operating migration or GitHub push is included.

Sequential author self-review confirmed the changed predicate's current-reference callers and the separate tenant-owned history path. This is not independent reviewer sign-off or proof of application-wide deadlock freedom.

## Remaining work

Cash writer integrity and older approval dependency revalidation remain open. This delivery does not normalize historical execution-date policy, implement amendments/lifecycle, or change valuation/P&L. Current-reference selection is stricter across callers of the shared predicate; this does not imply every writer has been audited or hardened.
