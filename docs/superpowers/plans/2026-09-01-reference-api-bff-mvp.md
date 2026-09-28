# Reference API and BFF MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the UI's isolated fixture path with a tenant-aware Python reference-data API, a server-only Next.js BFF adapter, an append-only mapping review workflow, and a first work-queue view.

**Architecture:** FastAPI owns PostgreSQL reads and controlled reference-data mutations. The Next.js server route derives a local/Auth0-compatible tenant context, calls FastAPI, and returns view-oriented contracts to the browser. Fixture fallback is permitted only in local development and is always labelled in the response metadata; production fails closed when the API is unavailable.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2, PostgreSQL 18, Next.js 16 App Router, React 19, MUI 9, TypeScript, Vitest, pytest.

**Spec:** `ui/mvp-scope.md`, `ui/data-contracts/instrument-search.md`, `ui/screen-specs/instrument-search.md`, and `ui/workflows/instrument-review.md`.

## Global Constraints

- The browser never connects directly to PostgreSQL and never receives tenant database credentials.
- Tenant scope is derived from trusted session/server context; a client query parameter cannot select a tenant.
- Canonical UUIDs and effective versions remain the identity boundary; provider and client aliases are mappings, not primary keys.
- Mapping changes are proposals and append-only approval decisions; no direct destructive update endpoint is exposed.
- Every API response is view-oriented and includes structured source/tenant metadata without exposing SQL topology.
- Synthetic fallback is local-only, explicit, and never silently replaces a failed production API.

---

### Task 1: Create the Python API boundary and tenant dependency

**Files:**
- Modify: `requirements.txt`
- Create: `apps/reference_api/__init__.py`
- Create: `apps/reference_api/main.py`
- Create: `apps/reference_api/config.py`
- Create: `apps/reference_api/tenant_context.py`
- Create: `tests/test_reference_api_boundary.py`
- Modify: `package.json`

**Interfaces:**
- `GET /health` returns `{ "status": "ok", "service": "reference-api" }`.
- `TenantContext` contains `tenant_id`, `user_account_id`, and `source`.
- `get_tenant_context(x_tenant_id, x_user_account_id)` rejects missing or malformed trusted headers with HTTP 401/400.

- [ ] Write failing tests for health and missing-tenant rejection.
- [ ] Run `pytest tests/test_reference_api_boundary.py -v` and observe the missing-module failure.
- [ ] Add FastAPI/Uvicorn dependencies, app factory, settings, and strict tenant-header dependency.
- [ ] Run the focused tests and the full Python suite.
- [ ] Add `dev:reference-api` and `start:reference-api` workspace scripts.

### Task 2: Implement canonical instrument search/detail read contracts

**Files:**
- Create: `apps/reference_api/contracts.py`
- Create: `apps/reference_api/db.py`
- Create: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Create: `tests/test_reference_api_read.py`
- Modify: `ui/data-contracts/instrument-search.md`

**Interfaces:**
- `GET /v1/instruments/search?q=&limit=&offset=` returns the existing instrument view model plus `meta` (`tenantContext`, `source`, `apiVersion`, `correlationId`).
- `GET /v1/instruments/{instrument_id}` returns one view model or HTTP 404.
- Repository functions accept an injected SQLAlchemy `Connection` so tests can use the seeded PostgreSQL container without global state.

- [ ] Write integration tests for HSBC lookup, OTC bond detail, pagination, and unknown UUID 404.
- [ ] Run the focused tests and confirm they fail before implementation.
- [ ] Implement SQLAlchemy joins across `secm.financial_reference_node`, `secm.instrument`, `secm.listing`, `secm.financial_reference_identifier`, `ing.external_object_mapping`, and `md.market_data_*` tables.
- [ ] Implement Pydantic response models and correlation IDs.
- [ ] Run focused tests, full Python tests, and a live Docker query.

### Task 3: Connect the Next.js BFF and local tenant session

**Files:**
- Create: `apps/ops-console/src/lib/tenant-context.ts`
- Create: `apps/ops-console/src/lib/reference-api-client.ts`
- Modify: `apps/ops-console/src/app/api/instruments/search/route.ts`
- Modify: `apps/ops-console/src/app/page.tsx`
- Modify: `apps/ops-console/src/components/operations-console.tsx`
- Create: `apps/ops-console/src/lib/reference-api-client.test.ts`
- Modify: `.env.example`

**Interfaces:**
- `resolveLocalTenantContext()` returns the demo tenant/user UUIDs in local mode and is the seam for Auth0 claims later.
- `searchReferenceInstruments(query, context)` calls FastAPI server-to-server with `X-Tenant-Id` and `X-User-Account-Id`.
- BFF metadata identifies `live-reference-api`, `synthetic-fixture`, or `synthetic-fixture-fallback`.

- [ ] Write failing client tests for URL construction, tenant headers, and live response pass-through.
- [ ] Run the focused Vitest test and observe the missing-module failure.
- [ ] Implement the server-only API client and BFF fallback policy.
- [ ] Run frontend typecheck/tests/build and an API-backed route smoke test.

### Task 4: Add append-only mapping proposal and steward decision endpoints

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Modify: `security_master_schema/demo_data.py`
- Create: `tests/test_reference_mapping_workflow.py`
- Create: `ui/workflows/mapping-review.md`

**Interfaces:**
- `POST /v1/reference-mapping-proposals` accepts namespace, external object type/value, target type/UUID, venue context, validity date, and reason; it creates a `secm.reference_data_proposal` row with `proposal_type=IDENTIFIER_MAPPING` and status `PENDING`.
- `POST /v1/reference-mapping-proposals/{proposal_id}/decision` accepts `APPROVED` or `REJECTED`, actor context, and reason; it writes `secm.reference_data_approval` and, for approval, creates the corresponding `ing.external_object_mapping` row as `VERIFIED` without mutating prior mappings.
- A proposal cannot be decided twice.

- [ ] Write integration tests for proposal creation, approval, rejection, duplicate decision rejection, and tenant actor validation.
- [ ] Run focused tests and confirm they fail before implementation.
- [ ] Add a deterministic demo user account and implement transactional repository methods.
- [ ] Run focused tests, full Python suite, and inspect resulting rows read-only.

### Task 5: Expose and render the work queue

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Create: `apps/ops-console/src/app/api/work-queue/route.ts`
- Create: `apps/ops-console/src/lib/work-queue.ts`
- Modify: `apps/ops-console/src/components/operations-console.tsx`
- Create: `apps/ops-console/src/lib/work-queue.test.ts`
- Create: `ui/screen-specs/work-queue.md`

**Interfaces:**
- `GET /v1/work-queue` returns pending mapping proposals, market-data exceptions, NAV runs awaiting review, counts, and source metadata for the trusted tenant.
- The BFF exposes `/api/work-queue` with the same view contract and local fixture fallback.
- The console renders a compact queue summary above search and preserves explicit empty/error states.

- [ ] Write failing tests for queue grouping and empty states.
- [ ] Run focused tests and observe the expected failure.
- [ ] Implement read-only queue queries and BFF/UI rendering.
- [ ] Run all frontend/Python tests, production build, and API/UI smoke tests.

### Task 6: Document operations and verification commands

**Files:**
- Modify: `apps/reference_api/README.md`
- Modify: `apps/ops-console/README.md`
- Modify: `ui/README.md`
- Create: `docs/superpowers/plans/2026-09-01-reference-api-bff-mvp.md` (this plan)

- [ ] Document local startup order, environment variables, fixture fallback, and production fail-closed behaviour.
- [ ] Run `docker compose up -d`, the demo loader, `pnpm run typecheck:ops-console`, `pnpm run test:ops-console`, `pnpm run build:ops-console`, and `pytest -q`.
- [ ] Smoke-test `/health`, live search/detail, mapping proposal/decision, and `/v1/work-queue` against Docker.
