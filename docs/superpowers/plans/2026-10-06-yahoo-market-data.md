# Yahoo market data implementation plan

The paths in the original execution record below are historical. The subsequent
[7 October boundary refactor](../../delivery/market-data-ingestion-boundary.md)
relocates the implementation into `market_data` and `apps/market_data_ingestor`,
preserving the script command and data semantics.

> **For agentic workers:** Use superpowers:executing-plans sequentially. The user explicitly requested no subagents, no further plan approval and the current feature checkout.

**Goal:** Import inspectable Yahoo daily equity history into the existing market-data model with layered, auditable use rights.

**Architecture:** Add small rights and ingestion modules, additive schema tables and an operator CLI. Preserve the existing catalogue and observation infrastructure. No commercial activation or valuation changes.

**Tech Stack:** Python, SQLAlchemy Core, PostgreSQL, Alembic, existing httpx dependency.

**Spec:** ../specs/2026-10-06-yahoo-market-data.md

## Global constraints

- Sequential execution in codex/enriched-trade-booking; preserve all existing dirty work.
- No commits or push unless requested. This maintained plan is also the progress ledger.
- Database integration tests use scripts/run_isolated_python_tests.py only.
- Personal declaration is not legal clearance. No commercial or redistribution grants.
- No access-control bypass, fabricated times, forward filling or destructive financial writes.

## Review focus

- Another dataset or licensee's grant cannot satisfy a prerequisite.
- Different content cannot silently reuse an idempotency key.
- Historical revision remains retained but does not double-count current display.
- Wrong venue or currency cannot produce an apparently successful mapping.
- Personal observations cannot leak to a second simulated tenant or commercial workflow.

### Task 1 Rights and schema

- [x] Write and run failing lightweight tests for evaluate_rights(profile, requirements, grants, activity, on_date, scope).
- [x] Implement security_master_schema/market_data_rights.py and additive access profile, required activity grant and ingestion-record tables in models.py plus revision 20261006_62.
- [x] Verify lightweight tests and isolated migration constraints.

### Task 2 Yahoo parser and append-only importer

- [x] Write and run failing parser tests against realistic chart fixtures; implement apps/reference_api/yahoo_market_data.py with parse_chart and bounded fetch_chart.
- [x] Write and run failing PostgreSQL tests; implement security_master_schema/market_data_ingestion.py with ingest_chart, stable identities, exact mapping, linked vintages and payload retention.
- [x] Verify duplicates, conflicts, revisions, rejected payloads, frozen evidence and rollback.

### Task 3 Local onboarding and inspection rights

- [x] Write failing operator and API tests; implement scripts/ingest_yahoo_market_data.py and local personal onboarding against the seeded universe.
- [x] Enforce access profiles on discovery and actual observation datasets and existing node visibility in repository.py.
- [x] Verify local-only execution, no unapproved commercial rights, cross-tenant isolation and current revisions.

### Task 4 Activation and handoff

- [x] Apply the reviewed additive migration locally; activate the personal profile without rewriting existing data.
- [x] Attempt a small real-data smoke test and report provider failure explicitly; widening is blocked pending successful acquisition.
- [x] Run relevant regressions, full isolated Python suite and diff checks.
- [x] Self-review the task diff, document commands, actual counts, rights limitations and deferred calendars/valuation work in docs/delivery/yahoo-market-data-alpha.md.

## Execution ledger

Design and best-practice plan reviewed inline, implemented sequentially. User instructions override approval/commit/subagent defaults. Baseline from the previous task: 949 Python tests passed. Fresh targeted runs passed 84 tests, then 28 integrity/API/workspace regressions and 3 personal-onboarding tests after hardening. Full isolated Python verification is in progress.

Frontend: 583 tests passed using two workers and a 30-second test budget; three default-concurrency import timeouts were diagnosed rather than changing assertions. Browser acceptance caught a literal entity in the catalogue heading; its new failing assertion was fixed, and all 4 market-data frontend tests plus TypeScript validation passed again. OpenAPI export check passed. Generated TypeScript regeneration is byte-for-byte stable; the existing generate:check script compares against Git HEAD and therefore reports the intentionally uncommitted contract changes, not generation drift. git diff --check passed.

Local activation: reviewed revision 20261006_62 is installed. Rollback preview made no network request. Personal configuration created dataset 01a11302-d25d-7093-9827-3893ed3c6d86 with 543 PROPOSED mappings and a missing MARKET_DATA module grant. Owner-declared personal scope is recorded separately from contractual rights. The AAPL/AIR.PA/MT.AS smoke run stopped on AAPL HTTP 429; the other two were not attempted. No automatic retry/bypass, no Yahoo observations or retained price deliveries, and no wider import. Existing counts remain trades 9, lifecycle events 9, observations 12,469, cash balances 0.

The updated local API/frontend run on 8000/3000. Browser checks confirmed tenant selection, rolling default dates, explicit empty-window behavior and synthetic historical catalogue results (24 visible series, paginated 12 per page). No trades or reference approvals were performed during browser acceptance.

Final review adjustment: current Yahoo UK-applicable terms were read directly in the browser (updated 8 July 2026; section 2(d)(ix)), confirming that automated-access permission is separate from personal intent. The reserved AUTOMATED_SOURCE_ACCESS acquisition prerequisite now starts unassigned and requires reviewed CONTRACT-basis access evidence, not an owner declaration or commercial activation. Existing reviewed assignments are preserved on rerun. Local preflight returns RIGHTS_BLOCKED without a request. The prior HTTP 429 remains observed evidence, not a successful source acceptance check.

Final fresh task regression: 58 Python tests passed after this adjustment, including layered source permission, rights denial, series identity, revisions, immutable receipts, personal setup, CLI boundaries and inspection. The full Python run started before the last access-layer hardening; this fresh targeted run verifies those final changes. Final frontend verification: 584 tests and TypeScript passed. Browser acceptance also verified the second tenant's ACCESS RESTRICTED message, then restored the personal-project tenant.

Full-suite completion: 998 Python tests passed, 489 warnings, 1549.82 seconds (25m49s). Disposable test databases were cleaned up by the isolated runner. Final focused execution covers the three cases added after collection and final code changes. No merge, commit or push. Implementation/local verification are complete; real-source sign-off remains externally blocked. Next permitted acquisition requires reviewed provider permission, then a successful sample (the prior 429 remains a second observed source restriction), before any wider import. No valuation/P&L or commercial activation has been performed.
