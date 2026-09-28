# Frontend/API remediation status

**Date:** 8 September 2026  
**Baseline:** [Frontend and API state and quality review](./frontend-api-state-and-quality-review-2026-09-08.md)

## Outcome

The highest-risk inconsistencies identified in the review have been addressed
for the current Operations Console workflows:

- browser components use a same-origin Next.js BFF boundary;
- direct FastAPI clients and tenant-context helpers are server-only;
- BFF errors use one correlation-aware envelope;
- unknown server exceptions are mapped to safe fallback text;
- standalone instrument detail reads the live API;
- pending reference-data proposals have a generic, tenant-scoped review and
  decision route/page;
- queue records link to that review page for supported proposal types;
- browser mutations carry a stable per-submit/draft idempotency key;
- queue navigation, keyboard interaction, and narrow-window layout defects were
  corrected;
- live data pages distinguish successful demo data reads from API-unavailable
  states, and portfolio aliases resolve to canonical portfolio codes.

The detailed implementation ledger and before/after findings are maintained in
the linked review document rather than duplicated here.

## Changed implementation areas

| Area | Implementation |
|---|---|
| Browser transport | `apps/ops-console/src/lib/browser-api-client.ts`, `api-errors.ts` |
| Server boundary | `tenant-context.ts`, `reference-api-client.ts`, `mvp-api-client.ts` marked `server-only` |
| BFF errors | `apps/ops-console/src/lib/bff-error.ts` and current `/api/*` routes |
| Live detail | `apps/ops-console/src/app/instruments/[instrumentId]/page.tsx` |
| Generic proposal API | `apps/reference_api/contracts.py`, `repository.py`, `main.py` |
| Generic proposal UI | `apps/ops-console/src/app/reference-data/review/[proposalId]/` |
| Queue links | `apps/reference_api/repository.py` work-queue projection |
| Type contracts | `apps/ops-console/src/lib/reference-api-types.ts` |

## Verification

Only focused checks were run; the complete Python and frontend suites were not
run because broad test execution was explicitly deferred.

- `.venv\\Scripts\\python.exe -m pytest tests/test_reference_api_proposal_review.py -q` — **2 passed**
- Related crypto/onboarding, queue and mapping API tests — **8 passed**
- `pnpm --filter ops-console test --` eight focused Vitest files — **25 passed**
- `pnpm --filter ops-console typecheck` — **passed**
- `pnpm --filter ops-console build` — **passed**; generic review route and BFF
  route were included in the generated route manifest

## Deliberately deferred

The following require a separate backend/security milestone and were not
pretended to be solved by UI code:

1. Auth0/session-derived tenant registry and production identity propagation.
2. OpenAPI-generated TypeScript contracts and runtime validation at the BFF.
3. Durable API-side idempotency/replay records for manual browser commands.
4. Historic entitlement/vintage-aware market-data resolution and frozen NAV/P&L
   input evidence.
5. Rendered component, Playwright, SSR/hydration-console, and automated
   accessibility suites.
