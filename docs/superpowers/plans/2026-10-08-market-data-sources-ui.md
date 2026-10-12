# Market Data Sources UI Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. User instructions override extra approval prompts, subagent review and full-suite runs.

**Goal:** Provide a real tenant source catalogue and operational priority settings.
**Architecture:** A dedicated source configuration service exposes entitled metadata and immutable priority versions. Selection applies priority after price-semantic eligibility. Next.js uses the existing tenant session/BFF boundary.
**Tech stack:** PostgreSQL, SQLAlchemy, FastAPI/Pydantic, generated OpenAPI contracts, Next.js/React/MUI, pytest/Vitest.
**Spec:** ../specs/2026-10-08-market-data-sources-ui.md

## Global constraints

- Preserve existing feature checkout and unrelated edits; no commits/push unless requested.
- Focused isolated tests only; no operating mock trades or entitlement grants.
- Catalogue/configuration access needs MARKET_DATA; tenant writes need TENANT_ADMIN; platform writes need PLATFORM_ADMIN.
- Source preference never grants activity/coverage rights; configuration is separate from uploads/validation.

## Review focus

- Wrong-tenant datasets and private sources must never be configurable/disclosed.
- Empty override means excluded, not legacy fallback.
- Missing/stale configuration version must conflict rather than overwrite another admin's changes.
- Source ranking must not precede semantic/calendar eligibility.
- Reset to inheritance and idempotent retries must preserve configuration history.

### Task 1: Catalogue and configuration boundary

Files: `apps/reference_api/market_data_sources.py`, `apps/reference_api/market_data_source_contracts.py`, `apps/reference_api/market_data_source_routes.py`, `security_master_schema/models.py`, `alembic/versions/20261008_74_source_priorities.py`, `tests/test_market_data_sources.py`.
Interfaces: `catalogue(c, tenant, actor)`; `save_priority(c, tenant, actor, payload, key)`; immutable priority IDs/order/mode and source metadata.
- [x] Write catalogue, role/tenant, idempotency, concurrency and inheritance tests; observe missing-feature failures.
- [x] Implement additive schema and dedicated catalogue/configuration routes.
- [x] Run focused database/API tests to green.

### Task 2: Selection integration

Files: `market_data/source_priority.py`, `market_data/policy_selection.py`, `security_master_schema/market_data_resolver.py`, `tests/test_source_priority.py`.
Interfaces: load an as-of priority decision and rank eligible same-date rows while retaining evidence.
- [x] Write rank-versus-arrival, exclusion, pinned rule and semantic-eligibility tests; observe failures.
- [x] Integrate priority into composite/legacy selection and freeze evidence.
- [x] Run affected coverage/resolver/valuation tests.

### Task 3: Frontend and handoff

Files: `apps/ops-console/src/app/market-data/sources/page.tsx`, `src/app/api/market-data/sources/route.ts`, `src/components/market-data-sources-console.tsx`, `src/lib/market-data-sources.ts`, navigation and generated API contracts.
- [x] Write frontend rendering/state tests before implementation.
- [x] Build providers/scope cards and type-based priority editor, with accessible move/exclude/add/inherit actions, read-only authority, errors and retry-safe saves.
- [x] Expose navigation; run focused Vitest, typecheck and OpenAPI checks.
- [x] Apply migration 74 after isolated checks, verify local activation where feasible, and document verified behaviour/limits.

Delivery: [implementation and verification](../../delivery/market-data-sources-ui.md). Browser click-through remains pending because the browser runtime could not initialise; HTTP activation verified instead.
