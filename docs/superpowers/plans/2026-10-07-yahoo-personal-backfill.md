# Yahoo Personal Backfill Implementation Plan

> Execute sequentially with superpowers:executing-plans, as requested by the owner. Preserve the existing current checkout and unrelated changes; no automatic commit, push or subagent dispatch.

**Goal:** Record the approved personal-research exception and backfill available five-year Yahoo history for 543 mapped listings.

**Architecture:** Keep rights and provider ingestion boundaries. Extend the Yahoo operator's explicit history mode and reuse atomic publication, exact payload retention and mapping validation. Resume by dataset, namespace, symbol and exact requested date window.

**Tech Stack:** Python, HTTPX, SQLAlchemy, PostgreSQL, Alembic, pytest.

**Spec:** ../specs/2026-10-07-yahoo-personal-backfill.md

## Global constraints

- Exception is not CONTRACT evidence; personal tenant and Yahoo dataset only.
- Commercial/other-provider permissions are unchanged.
- Operating writes are limited to the new schema constraint and approved Yahoo source/rights/observation records.
- Database tests run through scripts/run_isolated_python_tests.py only.
- No browser data entry, impersonation, proxies, cookies or silent price repairs.

## Review focus

- Wrong dataset, scope or activity must not accept the exception.
- Repeated activation must not reactivate revoked grants or overwrite reviewed permission.
- Leap years and exact window bounds must not leave calendar gaps.
- Resume must match the exact request and skip successful retained data only.
- Failed identity validation must retain rejection evidence without approving a mapping.

## Task 1: Explicit personal research exception

Files: models.py, migration 63, market_data/rights.py, market_data/providers/yahoo/onboarding.py, rights/onboarding tests.

- [x] Write failing pure rights tests for narrow exception scope.
- [x] Write failing isolated activation tests for auditable evidence, idempotency and revocation.
- [x] Add evidence-basis constraint migration; preserve commercial CONTRACT constraint and restrict exception to PERSONAL ACQUIRE.
- [x] Implement enable_personal_research(c, tenant_id, actor_id, reference) -> dict with explicit attributed record and unchanged existing assignments.
- [x] Run focused pure and isolated database tests.

## Task 2: Resumable five-year history

Files: Yahoo adapter, operator app, tests/test_yahoo_market_data.py, tests/test_yahoo_market_data_cli.py, tests/test_market_data_ingestion.py.

- [x] Write failing tests for explicit five-year request, maximum bound and unchanged daily default.
- [x] Add history ProviderSpec and bounded fetch window; no payload-limit expansion.
- [x] Add explicit --start and --personal-research-exception flags to the local operator, with --apply/acknowledgement guards.
- [x] Resume from stored successful reports for the exact request; content hashes still distinguish later source revisions.
- [x] Run focused and full isolated Python suite, compilation and whitespace checks.

## Task 3: Activate and import

- [x] Snapshot financial counts and rights/mapping state; migrate local database.
- [x] Activate the approved exception and ingest a small representative sample.
- [x] Start full serial 543-ticker backfill; retain per-ticker progress and report gaps.
- [x] Verify final coverage, exception provenance and untouched financial records; document actual results.

## Execution ledger

Ruling: Use a single bounded five-year HTTP delivery per ticker rather than annual HTTP chunks, to avoid multiplying provider calls. Resume/commit granularity remains per ticker. Cost: a failed ticker retries its full five-year window.

Pre-flight: activation produces the scoped dataset used by history mode; both use ordinary rights evaluation. History ProviderSpec and fetch bound must agree. No financial write path is used.

Task 1: complete — 19 pure rights tests and isolated activation/revocation/ingestion checks passed; migration 63 applied and owner exception recorded. No contract was manufactured.

Task 2: history and resume implemented — 60 offline tests and 26 isolated database checks passed. The real three-ticker pilot committed 7,628 observations with zero rejections.

Ruling: Add batched publication after pilot measurements exposed per-point database round trips (1,837 statements for 600 points in the new failing regression). The task-owned full import was stopped after 12 retained ticker results; committed deliveries remain resumable. This changes SQL execution shape, not prices or append-only correction semantics. Cost if wrong: a ticker transaction rolls back; provenance/replay/correction tests gate resumption.

Batching verification: 16 isolated ingestion tests passed in 1.62 seconds, including repeated adapter identities and current-only coverage. Import resumed from retained deliveries with a new log; no financial records were modified.

Sequential author review: reviewed the rights evaluator, activation helper, migration, bounded adapter, operator resume path, coverage query and batched publisher against the review focus. No additional blocker found. Commercial CONTRACT requirements and all ordinary prerequisite layers remain unchanged. Exact-window resume and append-only corrections have direct regression coverage. Operating integrity check during execution confirms 9 trades, 9 lifecycle events, 50 strategies and zero cash accounts/balances, matching the baseline. Final import coverage and fresh full-suite results remain pending; this is not final signoff.

Final code verification: fresh isolated Python suite passed 1,037 tests with 490 warnings in 914.03 seconds. Full-universe acquisition is still running; final data coverage remains pending. The first retained partial delivery is FISV, with missing CLOSE and ADJ_CLOSE on 2025-11-12; 2,506 other observations were accepted without inventing the missing values.

Final execution: all 543 mappings VERIFIED; 1,086 series and 1,346,008 new observations. All series reach 2026-10-06; 530 listings start at 2021-10-07, with 13 shorter available histories documented in docs/delivery/yahoo-five-year-backfill.md. The resumed run fetched 529 tickers and resumed 14 committed windows, with no HTTP errors/backoffs. Its nonzero exit flags the partial FISV delivery, not unprocessed listings. One bounded three-day follow-up reproduced the same gap and inserted no additional prices. Financial counts remained unchanged and missing observation provenance count is zero. Personal acquisition/storage/display allowed; non-display, redistribution and commercial acquisition remain denied. Completion means the authorized available-history backfill and honest gap report are delivered, not that unavailable source data was repaired or calendar completeness certified.
