# Frontend loading and recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Implement sequentially; no subagents.

**Goal:** Make workspace pages load progressively and recover correctly from session, authorization and upstream failures.

**Architecture:** Preserve routes and financial workflows. Introduce focused server transport/workspace access modules and shared recovery UI; give the instrument catalogue an isolated source-aware client wrapper. Keep migrations small and retain permission enforcement at every server boundary.

**Tech Stack:** Next.js 16.3.4, React 19, MUI 9.4.0, TypeScript, Vitest.

**Spec:** docs/superpowers/specs/2026-10-08-frontend-loading-recovery.md

## Global constraints
- Work sequentially without subagents or operating financial writes.
- Preserve the existing next-env.d.ts change.
- No dependency upgrades, migrations, publishing or git push.
- Never retry writes automatically; retain write deadlines and idempotency.
- No persistent authorization caching or weakened production cookie-secret requirements.

## Review focus
- Valid session plus workspace outage: show unavailable state, not tenant selection (Task 1).
- Upstream 401/403: never substitute fixtures (Tasks 1 and 2).
- Tenant change: no old workspace grants or old catalogue results (Tasks 2 and 3).
- Slow/cancelled request: bound reads and suppress stale state while preserving write outcomes (Tasks 1 and 2).
- Production runtime: cookie-secret requirement and production build must remain valid (Task 3).

## Task 1: Shared read deadlines and workspace failures
**Files:** Create src/lib/server/api-read.ts, src/lib/server/workspace-access.ts and tests; modify src/lib/tenant-session.ts, src/lib/mvp-api-client.ts, src/lib/reference-api-client.ts, src/lib/reference-fetch.ts and src/app/api/session/active-tenant/route.ts. Add src/components/workspace-unavailable.tsx and tests.
**Interfaces:** apiRead(input, init?, fetchImpl?) returns Promise<Response>, preserving caller abort and applying the configured read deadline. resolveWorkspaceAccess() returns a discriminated result (ready with context/workspace, session-required, forbidden, unavailable). WorkspaceUnavailable renders accessible retry/select-tenant options without financial forms.
- [x] Add tests: valid-cookie/upstream-503 produces unavailable; absent or invalid cookie produces session-required; upstream-403 produces forbidden; aborted caller stays aborted; hanging GET times out; POST retains 35-second policy and is not retried.
- [x] Run these tests and confirm they fail for missing behavior.
- [x] Implement focused helpers and replace unbounded session/MVP reads. Return accurate BFF status for upstream failures.
- [x] Run the focused tests and existing tenant, transport and permission tests; confirm no authorization regression.

## Task 2: Reliable, source-aware instrument catalogue
**Files:** Modify src/app/instruments/page.tsx, src/app/api/instruments/search/route.ts and src/components/instrument-catalogue.tsx. Create src/features/instruments/catalogue-workspace.tsx, fixture-search.ts and catalogue-types.ts with colocated tests; add page/BFF regressions.
**Interfaces:** fixtureSearch(query, filters) returns filtered/paginated data with total and explicit synthetic provenance. CatalogueWorkspace receives verified workspace and initial catalogue state; InstrumentCatalogue reports current source/error/loading through a typed callback. catalogue-types exports the complete contract-supported filter values.
- [x] Add failing tests: production with fallback disabled and API-403 renders no fixture rows; development-403 remains denied; fallback requires explicit opt-in; fixture BOND/status/offset/limit query returns the correct slice/total; source label updates after subsequent responses.
- [x] Add controlled asynchronous search tests: response arriving during the next debounce cannot overwrite results; cleanup aborts on unmount; stale errors/finally cannot overwrite current request state; available type choices do not depend on the first 25 results.
- [x] Run the tests and confirm each failure matches the reviewed issue.
- [x] Implement common fixture policy and source-aware wrapper. Retain initial live server results and server-supplied permission context.
- [x] Run catalogue, pagination, BFF, session and permission regressions.

## Task 3: Progressive loading and consistent route recovery
**Files:** Modify affected page.tsx files under instruments, operations, strategies, trades, market-data and valuation; add route loading.tsx/error.tsx and app/global-error.tsx as needed. Extract src/features/instruments/catalogue-results.tsx as an async boundary. Reuse Task 1 helpers and recovery UI; update affected tests and docs/delivery/README.md with a delivery note.
**Interfaces:** CatalogueResults receives validated context/workspace and awaits the catalogue under Suspense. Routes consume resolveWorkspaceAccess() and render explicit failure states; only session-required redirects. No new financial interfaces.
- [x] Add failing route regressions for delayed catalogue loading, service outage with valid tenant, forbidden access, valuation workspace outage and unavailable strategies. Assert retry UI and absence of write forms where permissions are unknown.
- [x] Add tenant-switch regression showing no previous-tenant rows or grants. Preserve existing page permission and server/browser boundary tests.
- [x] Add route boundaries and migrate repeated catch-and-redirect logic. Ensure every awaited boundary is covered by loading/error UI; avoid hiding workspace waits above all loading boundaries.
- [x] Run node node_modules/vitest/vitest.mjs run from apps/ops-console (full frontend suite), followed by node node_modules/typescript/bin/tsc --noEmit --incremental false and pnpm --filter ops-console build from repository root. Report all failures.
- [x] Run production-mode read-only/browser checks with a disposable secret and isolated/mock API; capture cold/warm timings and failure/retry/tenant-switch behavior. If browser tooling is unavailable, report the precise gap instead of claiming acceptance.
- [x] Review diff for accidental generated-file changes, permission weakening and changes to write/retry behavior. Preserve original next-env.d.ts bytes and document results.

## Execution
The user selected sequential execution in this chat. Review this specification and plan before implementation. Use the current checkout if the user confirms that choice; create an isolated worktree only if requested. Keep changes uncommitted for review unless the user asks otherwise.

## Delivery evidence

See docs/delivery/frontend-loading-recovery-2026-10-08.md. All automated checks and isolated HTTP acceptance passed; interactive browser acceptance remains unverified because the browser tool failed during sandbox setup. Changes are intentionally uncommitted.
