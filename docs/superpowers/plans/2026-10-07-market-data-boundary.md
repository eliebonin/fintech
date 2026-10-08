# Market data boundary implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. User requested implementation without another plan approval and work in the current checkout; no subagents or commits.

**Goal:** Isolate market-data ingestion from the API and Yahoo-specific publication logic.

**Architecture:** A `market_data` package contains provider-neutral contracts, ingestion, storage and shared rights. An operator app composes the Yahoo adapter; the old script remains a wrapper.

**Tech Stack:** Existing Python, SQLAlchemy, HTTPx and pytest; no new dependencies.

**Spec:** [Market data boundary](../specs/2026-10-07-market-data-boundary.md).

## Global constraints

- Preserve EoD behaviour, source/series identities, licensing gates and caller-owned transactions.
- No schema changes, operating data writes, Yahoo calls, valuation or live-price work.
- Preserve unrelated dirty checkout changes; no commits, push or new worktree.
- Database verification uses `scripts/run_isolated_python_tests.py` exclusively.

## Review focus

- Indirect API imports through onboarding/settings must fail runtime boundary checks.
- A different provider/source field must publish without Yahoo-specific branching.
- Rejected source identities must still retain raw evidence without verifying mappings.
- Both CLI entry points must reject nonlocal targets before connection/network access.
- Shared rights imports must not introduce fetching or API dependencies into readers/resolver.

### Task 1: Isolate the existing flow

**Files:** Create `market_data/{contracts,ingestion,storage,rights}.py`, `market_data/providers/yahoo/{adapter,onboarding}.py`, `apps/market_data_ingestor/{config,yahoo}.py`, package initializers, and `tests/test_market_data_boundaries.py`. Move existing implementation, update its consumers/tests, and reduce the legacy script to a wrapper.

**Interfaces:** `ingest_delivery(connection, *, provider, parser, dataset_id, namespace_id, symbol, raw_payload, delivery_key, received_at, start, end)` consumes immutable `ProviderSpec`, `ListingContext`, `DailyPoint`, `ParsedDelivery` and a callable parser. The Yahoo composition exposes `ingest_chart` with the former keyword arguments. Shared rights signatures and CLI flags remain unchanged.

- [x] Write blocked-import/runtime and dependency-contract tests; run them RED against missing boundaries.
- [x] Write a non-Yahoo parser/publication regression; run it RED before adding normalized publication.
- [x] Move/split the implementation and update imports without changing existing data semantics.
- [x] Run boundary and existing pure parser/rights/CLI tests GREEN.
- [x] Run focused isolated PostgreSQL regressions GREEN.

### Task 2: Verify and document

**Files:** Create `docs/delivery/market-data-ingestion-boundary.md`; update delivery/architecture/research indices, Yahoo report and CI compile coverage for the new package.

**Interfaces:** Uses Task 1's new module paths and unchanged script flags. Documents the flow, extension point, compatibility and source-access blocker.

- [x] Run the full isolated Python suite and OpenAPI freshness check.
- [x] Self-review imports, transaction ordering and raw/normalized data paths; user requires sequential work, not independent agents.
- [x] Record online evidence, actual results and remaining scope; run `git diff --check`.

## Execution ledger

Pre-flight: Task 2 consumes Task 1's paths and unchanged CLI; no interface conflicts.

Ruling: Existing current-checkout, sequential-execution and no-extra-approval instructions override skill worktree, approval, subagent and commit defaults. Preserve the working state and document self-review, not independent sign-off.

Task 1 progress: Four architecture/runtime tests failed before implementation; the existing pure baseline passed 31 tests. The new synthetic-provider regression failed before implementation. After extraction, 37 pure tests and 65 focused isolated regressions passed. Review added an undeclared-series regression: RED (accepted 1 instead of rejection) before validating the normalized contract. Adapter metadata is explicit, with no Yahoo adjustment/timestamp defaults in the shared contract.

Task 1: complete (no commits per user preference). Fresh final focused isolated run: 66 passed in 21.05s. OpenAPI freshness and whitespace checks pass. Full isolated suite is running with output retained in `logs/market-data-boundary-full-python.log`.

Final review: self-review per user's sequential/no-subagent instruction. Checked all moved code and actual reader/resolver import changes, caller-owned transactions, rights-before-retention, replay-before-new-payload, mapping verification only after accepted normalized output, raw text retention, explicit adjustment/timestamp metadata and unchanged Yahoo observation identities. No unresolved critical/important finding in this refactor. The normalized series guard is verified RED→GREEN. Operating activation/source permissions remain untouched.

Task 2: complete. Full isolated suite: 1,009 passed, 491 warnings, 759.01s, exit zero. Fresh final focused run: 66 passed. OpenAPI freshness, new-package compilation and whitespace checks passed. Published the researched delivery report and linked it from root README, delivery/architecture/research indices and the original Yahoo record. No schema, financial data, acquisition permission, frontend or generated-contract changes; no Yahoo requests, commits, merge or push. Warning cleanup and real-source acceptance remain separate work.

