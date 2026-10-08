# MD Ingestion Hardening Implementation Plan

> Execute inline using executing-plans and TDD. User overrides: current feature checkout, no subagents, no automatic commit/push, no further plan-approval stop.

**Goal:** Consistent resumable outcomes, durable operational evidence, honest coverage/continuity audit and stronger publication contracts.

**Architecture:** Extend the current publisher/operator with focused outcomes, jobs and coverage modules. Add migration 64 for jobs, attempts and historical mapping reviews; preserve immutable delivery records and imported observations.

**Tech Stack:** Python, SQLAlchemy/PostgreSQL 18, HTTPX, Alembic, pytest; versioned calendar package.

**Spec:** ../specs/2026-10-07-md-ingestion-hardening.md

## Global constraints

Personal rights unchanged; no financial mutations, automatic gap fills or guessed historical aliases. All DB tests use scripts/run_isolated_python_tests.py. No production activation. Existing dirty changes preserved.

## Review focus

Partial replay/resume and duplicate-only rejection must retain outcome. Network/SQL errors must not leave falsely successful attempts. Unknown/empty calendars must not certify completeness. Review evidence must be attributed and non-overlapping. Changed basis/alias must not silently produce ambiguous current marks.

## Tasks

1. [x] Outcomes and gap planning: create market_data/outcomes.py; tests/test_market_data_outcomes.py. RED/GREEN table-driven outcomes, exact rejected-date spans and invalid boundaries; expose --retry-gaps with history only.
2. [x] Durable ledger and continuity governance: models.py, migration 64, market_data/jobs.py, market_data/history.py, tests/test_market_data_jobs.py. RED/GREEN job/attempt lifecycle, independent attempt commits, terminal immutability, explicit interrupted recovery, attributed history reviews and overlap denial.
3. [x] Semantic publication boundary: ingestion.py/storage.py and tests/test_market_data_ingestion.py. RED/GREEN malformed normalized points, stable dimensions, deterministic legacy licence and same-date alias correction; keep batched inserts.
4. [x] Calendar/current-data audit: market_data/coverage.py, calendar dependencies and tests/test_market_data_coverage.py. RED/GREEN omitted sessions/holidays, unknown calendars, short history and continuity coverage; CLI --audit-only.
5. [x] Integrate operator job/attempt outcomes and retry/audit flags; tests/test_yahoo_market_data_cli.py and isolated operator integration tests with HTTP boundary substitutes. Verify denial, publication failure, resume, retries, counters and no network in audit.
6. [x] Focused/full isolated tests, local additive migration and read-only universe audit. Document actual gaps/limits and verify unchanged financial/observation counts; separate author review.

## Ledger

Pre-flight: outcome/gap helpers feed attempts and operator; history review feeds ingestion and coverage; calendar audit reads current accepted observations and never mutates prices. No shared interface conflict found.

Ruling: keep dataset-wide publication serialization — correctness over premature workers; cost is limited same-dataset concurrency, not a network lock.

Ruling: historical continuity is flagged and governed, not inferred — current source metadata cannot prove five-year issuer continuity; cost is an explicit review backlog.

Tasks 1–5 implemented; verification in progress. Outcome helpers: 14 pure tests GREEN after missing-interface RED. Ledger/history: 2 isolated tests GREEN after missing-interface RED and correcting the new migration's user-account schema to secm. Semantic regressions reproduced six failures (basis drift, invalid points, alias double-counting); 24 combined isolated tests passed after shared validation and series/date identity. Calendar tests: 3 GREEN after missing-interface RED. Initial integration: 44 passed; expanded integration: 59 passed. Resume rights regression proved revoked STORE was ignored on resume, then fixed with a pre-resume rights check. Inclusive bound and sub-storage-precision regressions both reproduced failures and were fixed. Append-only review correction reproduced missing supersedes interface; now implemented and awaiting final verification.

Ruling: latest per-symbol assessment determines job outcome after targeted retries — all intermediate attempts remain retained; cost if assessment is wrong is a misleading summary, covered by failure/success retry regressions and immutable original reports.

Calendar dependency: pandas-market-calendars 5.5.0 pinned in requirements.in and hashed requirements.lock regenerated, preserving existing pinned direct dependencies. Loaded lazily by the read-only audit, not HTTP or API core imports. Local schedules are versioned comparison evidence, not governed sessions imported into cal tables.

Final focused run: 122 passed in 70.13 seconds. Additional operator/publication-driver-failure run: 4 passed in 48.20 seconds. The synthetic CLI fixture now isolates commits with savepoints; this prevents permission-state leakage into subsequent onboarding tests. Exact attempt-to-delivery scope regression is GREEN.

Local migration 64 applied; full-universe read-only audit completed. 1,056 series match versioned schedules, 26 have short leading histories, 2 retain the FISV 2025-11-12 gap, and 2 CBOE/BATS series are NOT_ASSESSED. All histories remain REVIEW_REQUIRED; no evidence was fabricated. No ambiguous current or unexpected dates found. Financial/observation counts and personal-only rights unchanged. Author review and dependency/compilation/whitespace checks completed; full isolated Python suite still running.

First full suite: 1,071 passed, one mandatory schema-description failure, 489 warnings, 798.38 seconds. Reproduced the failure in the 25-test metadata suite; fixed all 30 column descriptions and added comments-only migration 65 rather than modifying the applied migration 64. Database/model parity and operator follow-up: 34 passed in 49.29 seconds. Migration 65 applied locally and all 30 descriptions verified; financial counts unchanged. Fresh full-suite verification is in progress.

Completed: final full disposable-database suite passed 1,073 tests, zero failures, 488 warnings in 797.71 seconds (13:17); logs/md-hardening-full-python-final.log. The earlier progress entries are historical, superseded by this result. All six tasks are complete for the defined alpha scope. Local head is 65; existing prices/financial records and personal-only permissions remain unchanged. No fabricated continuity approvals, automatic source-gap repairs, new frontend dashboard, valuation/P&L, Git commit or push were performed. Delivery report and architecture/index links updated.
