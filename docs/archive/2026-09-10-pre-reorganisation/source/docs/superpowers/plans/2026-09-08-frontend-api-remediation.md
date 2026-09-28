# Frontend/API Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the operations console use one explicit browser-to-BFF boundary,
live canonical detail data, consistent errors, and actionable proposal review
without expanding the product scope.

**Architecture:** Server-rendered pages may call the Python API server-side.
Interactive browser components call only same-origin Next.js BFF routes. The BFF
owns tenant context, correlation IDs and the common error envelope. A generic
proposal-review route exposes submitted evidence and dispatches decisions to the
existing type-specific approval services.

**Tech Stack:** Next.js App Router, React 19, TypeScript, MUI 9, Vitest,
FastAPI, Pydantic, SQLAlchemy.

**Spec:** `docs/architecture/frontend-api-state-and-quality-review-2026-09-08.md`

## Global Constraints

- Do not expose tenant database credentials or trusted tenant headers to browser code.
- Keep FastAPI authoritative for validation, permissions, lifecycle and materialisation.
- Preserve explicit synthetic fallback only in local development.
- Do not rerun the complete Python or frontend test suites unless explicitly requested.
- Preserve the existing server-first rendering model.
- Every mutation remains proposal-first and carries a retry-stable idempotency key once the first submit is made.

---

### Task 1: Create a browser-safe BFF client and stable error envelope

**Files:**
- Create: `apps/ops-console/src/lib/api-errors.ts`
- Create: `apps/ops-console/src/lib/browser-api-client.ts`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Test: `apps/ops-console/src/lib/browser-api-client.test.ts`

**Interfaces:**
- `BffApiError { status: number; code: string; message: string; correlationId?: string; fieldErrors?: Record<string, string[]> }`.
- `bffGet<T>(path, fetchImpl?)` and `bffPost<T>(path, payload, idempotencyKey, fetchImpl?)`.
- Browser wrappers for catalogue reads and all currently interactive proposal/review mutations.

- [x] Add focused tests proving BFF errors preserve status/metadata and browser posts send `Idempotency-Key` without tenant headers.
- [x] Implement the typed error parser and browser-safe request helpers.
- [x] Move client-component imports to the browser-safe module and provide BFF wrappers for bond and index submissions.
- [x] Run the focused browser-client test; it passes.

### Task 2: Enforce server-only direct API usage and remove browser direct calls

**Files:**
- Create: `apps/ops-console/src/lib/tenant-types.ts`
- Modify: `apps/ops-console/src/lib/tenant-context.ts`
- Modify: `apps/ops-console/src/lib/mvp-api-client.ts`
- Modify: server pages and BFF routes currently using direct clients
- Modify: client forms under `apps/ops-console/src/app/instruments/**`
- Test: `apps/ops-console/src/lib/server-boundary.test.ts`

**Interfaces:**
- `tenant-types.ts` exports only `TenantContext`.
- `tenant-context.ts` remains the server-side resolver.
- `mvp-api-client.ts` is server-only and is never imported by a client component.

- [x] Add a source-boundary test that client components do not import direct API clients or tenant context.
- [x] Add `server-only` to direct API modules and update type-only imports to `tenant-types.ts`.
- [x] Change bond, index, listing and other client forms to call same-origin BFF wrappers.
- [x] Keep server-rendered pages and BFF handlers on direct server clients.
- [x] Run the boundary test and TypeScript typecheck.

### Task 3: Make standalone instrument detail use the live API

**Files:**
- Modify: `apps/ops-console/src/lib/mvp-api-client.ts`
- Modify: `apps/ops-console/src/app/instruments/[instrumentId]/page.tsx`
- Modify: `apps/ops-console/src/components/instrument-detail.tsx`
- Test: `apps/ops-console/src/lib/mvp-api-client.test.ts`

**Interfaces:**
- `getInstrument(context, instrumentId): Promise<InstrumentDetailPayload>`.
- The page renders the same view-oriented `InstrumentRecord` shape as search.

- [x] Add a focused test that the detail client calls `/v1/instruments/{id}` with tenant headers.
- [x] Implement the server client method and replace fixture lookup in the route.
- [x] Render distinct not-found, authorization and service-unavailable states while preserving source metadata.
- [x] Keep a local fixture fallback only when explicitly enabled in development.
- [x] Run the focused client test and typecheck.

### Task 4: Add a generic proposal review/decision path

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Create: `apps/ops-console/src/app/api/reference-data-proposals/[proposalId]/route.ts`
- (GET and POST are combined in the route above.)
- Create: `apps/ops-console/src/app/reference-data/review/[proposalId]/page.tsx`
- Create: `apps/ops-console/src/app/reference-data/review/[proposalId]/form.tsx`
- Modify: `apps/reference_api/repository.py` work-queue review paths
- Test: `tests/test_reference_api_proposal_review.py`

**Interfaces:**
- `GET /v1/reference-data-proposals/{proposal_id}` returns proposal metadata,
  submitted payload, status, reference node and decision evidence.
- `POST /v1/reference-data-proposals/{proposal_id}/decision` accepts
  `{decision, reason}` and dispatches to the existing type-specific decision
  service.
- Pending reference proposals expose `/reference-data/review/{proposalId}`.

- [x] Add API tests for tenant-scoped proposal detail, unknown proposal,
  pending decision and already-decided conflict.
- [x] Implement a typed proposal detail response and repository lookup.
- [x] Dispatch CREATE, CREATE_LISTING, CREATE_BOND, CREATE_CRYPTO_ASSET,
  CREATE_INDEX and CREATE_INDEX_FAMILY to existing approval functions; dispatch
  mapping proposals to the existing mapping decision function.
- [x] Add a minimal review page showing payload/evidence and approve/reject reason.
- [x] Update work-queue review paths for all supported proposal types.
- [x] Run only the new API test module and relevant frontend client test.

### Task 5: Fix navigation, source states and small UI correctness issues

**Files:**
- Modify: `apps/ops-console/src/lib/navigation.ts`
- Modify: `apps/ops-console/src/components/workspace-shell.tsx`
- Modify: `apps/ops-console/src/components/operations-console.tsx`
- Modify: `apps/ops-console/src/app/globals.css`
- Modify: market-data, trade and P&L pages
- Test: `apps/ops-console/src/lib/navigation.test.ts`

**Interfaces:**
- Navigation counts are supplied by live queue data or omitted.
- Source labels distinguish live API, local fixture and unavailable states.
- Queue hash navigation marks the work-queue section active.

- [x] Add tests for hash-aware active navigation and no hard-coded queue counts.
- [x] Remove hard-coded sidebar counts and correct active-section selection.
- [x] Remove the document-wide `min-width: 1120px` constraint.
- [x] Add keyboard semantics to instrument result rows and distinct not-found,
  unauthorized and unavailable messages.
- [x] Ensure market-data/P&L/trade pages distinguish live API demo data from API-unavailable states.
- [x] Run only the navigation and affected component tests.

### Task 6: Update the review record and verification ledger

**Files:**
- Modify: `docs/architecture/frontend-api-state-and-quality-review-2026-09-08.md`
- Create: `docs/architecture/frontend-api-remediation-status-2026-09-08.md`

- [x] Record each implemented item, test command and outcome.
- [x] Mark remaining gaps explicitly: generated OpenAPI contracts, browser E2E,
  authenticated Auth0 sessions, full NAV evidence and backend resolver fixes.
- [x] Document that broad test suites were not run unless specifically requested.

## Spec coverage and deliberate remaining scope

This plan covers the frontend/API findings that can be implemented without
changing the database or valuation model. Backend point-in-time market-data
resolution, immutable lifecycle/version semantics, physical tenant database
routing and complete Soft-NAV are intentionally separate workstreams.
