# Cash booking and approval integrity implementation plan

**Goal:** Close the confirmed cash integrity and FX/bond/ETP stale-approval defects without rewriting saved trades or broadening product support.

**Execution:** Sequential in the user-selected existing feature checkout. The user requested implementation; no additional approval loop or subagents. Preserve earlier uncommitted FX scope work.

**Baseline:** `docs/delivery/quality-reviews/2026-10-05-instrument-integrity.md` and completed FX scope hardening.

## Task 1 — authoritative cash integrity

- [x] Add `tests/test_cash_booking_integrity.py`: foreign/inactive scopes, draft definitions, inactive/nontradable nodes, inactive catalogue dependencies, inconsistent projections, out-of-period execution, unsupported product, atomic refusal and exact replay.
- [x] Observe failures with `scripts/run_isolated_python_tests.py` before production edits.
- [x] Add `apps/reference_api/cash_booking_integrity.py::load_cash_booking_listing(connection, tenant_id, listing_id, execution_date)`; use it in the existing writer after replay. Lock currencies in UUID order, then reference identities/scopes and projections/approved definitions, then shared catalogue dependencies. Reread discovered IDs to refuse changes during acquisition.
- [x] Require active tenant-visible listing and parent, a tradable listing, current parent, exactly one current approved effective definition for each, active types/currencies/venue, and consistent projections. Dates use execution date; legacy null operational start dates defer to the approved definition rather than inventing a date. Existing raw native quotes/factors are retained; factors must be positive and agree with approval.

Execution ruling: the initial parent-tradability test was invalid because the loader-owned canonical equity deliberately has `is_tradable=False`; this means it is not booked directly. Only the listing must be tradable for listing-backed cash. Keep the parent active/current/approved, rather than changing canonical data or weakening those checks.
- [x] Use explicit cash types (equity, cash ETP units, digital asset, fund/share-class units), not an exclusion list. Specialist/unknown types are refused. Preserve fingerprints/replays/history and save approved identifiers/factors with BOOKED evidence.
- [x] Focused cash tests, HTTP and scheduled locking tests; align frontend type filtering if required, without redesigning the ticket.

## Task 2 — approval-time reference checks

- [x] Add `tests/test_approval_reference_integrity.py`: FX base/quote/fixing currencies, bond currency/issuer/day-count, ETP currency/issuer/reference visibility/approval changes; refusals leave proposals pending and no materialized fragments.
- [x] Observe failures, then add focused locked dependency validation before materialization in the three existing paths. Validate optional references only when supplied; retain sparse creation and rejection workflows.
- [x] Lock/revalidate active catalogue rows and ETP reference node/scope/current approved instrument or active index facts. Target configuration types must be active and locked as well.
- [x] Protect direct approval callers with writer-owned savepoints; approval evidence and aggregate creation stay atomic. No schema changes or new universal approval engine.

## Task 3 — verification and record

- [x] Run focused suites and scheduled dependency-change tests, then full Python suite in a disposable database with retained output. Frontend tests only if frontend filtering changes.
- [x] Self-review concurrency order, absent scopes, optional references, date boundaries, exact retries and partial-materialization failure. Do not claim independent review.
- [x] Record results, remaining policy boundaries and deployment status under delivery quality reviews; update capability matrix/indexes. No operating data mutation, migration, restart or push.
