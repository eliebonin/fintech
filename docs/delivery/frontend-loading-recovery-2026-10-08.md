# Frontend loading and failure recovery

**Status:** Implemented; automated and isolated HTTP verification passed. Interactive browser acceptance remains outstanding.  
**Content type:** Delivery evidence  
**Last reviewed:** 2026-10-08

## Result
The instrument catalogue streams a loading shell while results are fetched. Workspace outages preserve the selected tenant and offer retry rather than redirecting to tenant selection. Explicit session, forbidden-access and unavailable-service states are shared across instrument pages, operations, strategies, trade history/booking, market data/valuation and tenant settings. Root and section loading/error boundaries cover server waits and unexpected exceptions.

Upstream reads have a configurable deadline: `REFERENCE_API_READ_TIMEOUT_MS`, positive integer milliseconds, default 10000. Reference mutations keep their existing 35000 ms deadlines and uncertain-write/idempotency behavior; no automatic write retry was added. Production still requires `ACTIVE_TENANT_COOKIE_SECRET`.

Both initial catalogue loading and its search BFF share the same synthetic-data policy. Fallback requires explicit `ALLOW_SYNTHETIC_FALLBACK=true`, is disabled in NODE_ENV or APP_ENV production, and applies only to connectivity/timeouts or 5xx. Authorization and invalid-query failures retain their errors. Fixture query/type/asset-class/status filters, pagination and total counts are applied consistently. Data source labels update after each search.

Search requests abort on filter changes and unmount; late success/error/finally callbacks are ignored. Initial server results are reused without an immediate duplicate client request, including React Strict Mode. Filter choices cover all 30 canonical seed types and observed custom types instead of just the current result page. Tenant-keyed catalogue instances discard old tenant state.

Tenant selection handles failed requests, restores enabled controls, allows list retry and distinguishes an empty membership list from loading. Membership and active-tenant BFFs preserve service/permission statuses and never set a cookie after a failed selection.

## Organisation
Focused modules now live under `src/features/instruments` for catalogue loading, fixture filtering, type choices, streaming results and source-aware client presentation. `src/lib/server` owns read budgets and workspace access/error types. Shared loading/recovery components serve the existing routes. Public URLs and financial interfaces are preserved. Broad route-group/file migration is deferred; it was not necessary to repair the demonstrated failures.

Workspace verification remains a dependency before rendering permission-sensitive content. Independent trade/strategy-option reads remain parallel where already supported. This delivery improves feedback and bounds upstream waits; it does not claim faster operating-database queries.

## Verification
- Full frontend suite: **140 files, 667 tests passed**, using `node node_modules/vitest/vitest.mjs run --maxWorkers=4`. Default high worker concurrency produced dynamic-import contention on this Windows host; deadlines were not increased.
- TypeScript: `node node_modules/typescript/bin/tsc --noEmit --incremental false` passed.
- Fresh Next.js production build passed; installed Next.js version 16.3.4.
- Eleven isolated production HTTP cases passed against a mock API: missing-session redirect, first/warm authenticated loads, type filtering/pagination, tenant isolation, catalogue 403/503, workspace 403/503, bounded slow read, and recovery.
- First authenticated HTTP response: TTFB 40 ms / complete response 116 ms. Warm: 13 ms / 38 ms.
- With a simulated two-second catalogue delay and a **1000 ms test-only deadline**, TTFB was 11 ms and the recoverable timeout response completed in 1054 ms. The default production read budget remains 10000 ms.

These are mock-backed HTTP timings, not browser rendering metrics or an operating-environment before/after benchmark. The browser automation tool failed during Windows sandbox setup, so hydration, visual layout, actual client navigation/tenant switching and mobile acceptance must not be inferred from these results. Component event/cancellation tests supplement the HTTP checks. No independent reviewer/subagents were used, per user instruction; the final diff was self-reviewed.

## Scope and remaining acceptance
No operating database writes, migrations, financial API mutations, dependency upgrades, deployment, commits or push. Temporary mock API/console processes were stopped. The original uncommitted next-env.d.ts bytes were restored after Next build regenerated that file.

To check the operating local console, run the reference API and `pnpm dev:ops-console` from the repository root; for representative performance use a production build/start with the required private cookie secret. Browser acceptance still needs first/warm /instruments, filters/paging, slow-service feedback, retry and switching tenants in the same browser session.

## References
- [Approved design](../superpowers/specs/2026-10-08-frontend-loading-recovery.md)
- [Implementation plan](../superpowers/plans/2026-10-08-frontend-loading-recovery.md)
- [Next.js data fetching and streaming](https://nextjs.org/docs/app/getting-started/fetching-data)
- [Next.js error handling](https://nextjs.org/docs/app/getting-started/error-handling)
- [React effect cleanup](https://react.dev/reference/react/useEffect)


## Operating catalogue follow-up after restart

The user's screenshot exposed an additional live-backend failure that the earlier mock-backed checks did not cover. Local `/instruments` rendered its recovery state because `_load_market_data` exceeded PostgreSQL's statement timeout while hydrating catalogue listings. A read-only reproduction failed after 34.72 seconds. The operating database contains 1,358,477 observations; its query plan performed repeated whole-history correction scans. The nested dataset-profile EXISTS also lost correlation to the outer observation/series, causing a global profile check and suppressing unrelated legacy entitlements.

The follow-up explicitly correlates the dataset-profile check and adds migration `20261008_71`: two non-unique partial B-tree indexes for latest accepted observations per series and accepted correction predecessors. Concurrent index creation avoids excluding operating writes during the build. Financial rows, accepted-observation semantics, tenant scope and profile-specific INTERNAL_REPORTING requirements are preserved. Catalogue hydration still performs repeated detail reads per instrument; this correction addresses the observed timeout without a response-contract redesign.

Verification: **48 focused Python tests passed in a disposable database**, including mixed legacy/profiled entitlement behaviour, rights/tenant controls, catalogue/detail reads, ingestion/corrections, a 100,000-observation synthetic-history case under a 2-second per-statement budget, and index downgrade/upgrade/repeated-upgrade preservation checks. Both new regressions were observed failing before implementation. `git diff --check` passed. No frontend source changed in this follow-up, so the prior frontend build/test evidence still applies; the API was restarted to load the corrected query.

Before local activation, a custom-format `pg_dump` backup was created and its complete archive listing validated: `.superpowers/sdd/2026-10-08-frontend-loading-recovery/fortem_pre_catalogue_indexes_20261008.dump` (69,918,257 bytes). Operating revision was checked as `20261008_70`, then only revision `20261008_71` was applied. Both indexes are valid. Before/after counts remain **1,358,477 observations, 9 trades and 9 lifecycle events**. There were no financial record mutations or seed loads.

Real operating HTTP checks passed for **both tenants** through the API, signed-session BFF, and streamed `/instruments` page, with canonical instrument names present and no catalogue-unavailable message. First tenant: API 1,391 ms, BFF 3,406 ms, page 3,188 ms; second tenant: API 640 ms, BFF 2,750 ms, page 2,766 ms. Each returned 25 instruments; totals were 802 and 551 respectively. These are complete HTTP response timings on the local operating database, not browser paint metrics. Browser visual/hydration acceptance remains unverified. Console and API remain running on ports 3000/8000; Docker's existing operating container remains running on 54329. Changes remain uncommitted.

Applied guidance: matching a B-tree index to ORDER BY/LIMIT avoids sorting/scanning all history ([PostgreSQL 18 index ordering](https://www.postgresql.org/docs/18/indexes-ordering.html)); concurrent builds avoid locks that exclude writes ([PostgreSQL CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)); explicit multi-level correlation retains the outer dataset reference ([SQLAlchemy Select.correlate_except](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.correlate_except)).


## Navigation refinement requested by the user

The user reported that showing “Loading Workspace…” for each menu click made navigation feel abrupt. This request supersedes the earlier full-page loading-fallback design. The root and section loading boundaries (including the older trade-history skeleton) are removed; `/instruments` now awaits its catalogue result before returning the destination view. App Router navigation can retain the current screen while the destination resolves. The sidebar links use Next.js `useLinkStatus` for an absolute-positioned underline: it appears only after 250 ms of pending navigation, causes no layout shift, and honors reduced-motion settings. No forced full-route prefetching, persistent tenant data cache, dependency changes or permission shortcuts were introduced. Existing tenant validation, read deadlines and recoverable service errors remain.

A regression was observed failing before implementation: the catalogue navigation resolved immediately to a Suspense loading fallback while its data remained pending. It now stays pending until live results/error recovery are ready. Focused tests: **41 passed**; full frontend suite: **140 files / 667 tests passed**; final TypeScript and Next production build passed. The final audit also removed the pre-existing trade-history loading boundary, followed by a fresh production build/type check. All **eight operating menu destinations** returned HTTP 200, contained the inline link hint, and contained no full-page workspace/catalogue/trade-loading message. These HTTP checks do not establish browser animation, paint, or hydration behaviour: the browser tool again failed during its Windows runtime initialization.

The local production console was rebuilt and restarted on 3000; API/database remained running. Original uncommitted `next-env.d.ts` bytes were restored after building. The console's process-only cookie key rotated during restart, so existing browser sessions may need tenant selection again. No financial writes or additional database migrations occurred during this navigation refinement. Changes remain uncommitted.

The implementation follows the installed Next.js 16.3.4 guidance; the current public documentation also describes delayed, inline link feedback for dynamic destinations without route loading boundaries ([Next.js useLinkStatus](https://nextjs.org/docs/app/api-reference/functions/use-link-status)). Initial full-document loads now wait for route content rather than showing the removed workspace fallback; this tradeoff implements the user's preference for keeping menu navigation steady.


## Subsequent catalogue optimisation

The user explicitly requested the proposed compact table query. See [lightweight catalogue delivery](instrument-catalogue-performance-2026-10-08.md) for the separate summary API/BFF, three-query budget, compatible full detail/search endpoints, isolated tests and measured live performance. No further database migration or financial writes were made.
