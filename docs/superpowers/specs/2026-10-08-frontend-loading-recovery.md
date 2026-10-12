# Frontend loading and failure recovery

## Objective
Fix the failures identified in the frontend review, starting with /instruments. Give users immediate loading feedback, accurate data provenance, and recoverable service errors. Work sequentially without subagents or operating financial writes. Preserve the existing next-env.d.ts change.

## Design
Keep Next.js 16.3.4, React 19 and MUI 9.4.0. Preserve public URLs and existing server authorization. Consolidate session/error/deadline behavior before moving broad sets of files. A full feature-folder migration is deferred until its benefit is demonstrated; this delivery extracts focused modules where the fixes need them.

1. Distinguish missing/invalid active-tenant cookies, forbidden workspace access and upstream unavailability. Redirect only missing/invalid sessions to tenant selection. Preserve 401/403 from upstream; show service failure with retry for network errors and 5xx. Configuration errors must not become session redirects.
2. Apply bounded reads across tenant-session, MVP and reference clients. Use a 10-second read deadline as an initial configurable budget (REFERENCE_API_READ_TIMEOUT_MS, positive integer, default 10000). Preserve caller cancellation. Keep existing 35-second write deadlines, idempotency and uncertain-write behavior; never retry writes automatically.
3. Replace the initial instruments fixture fallback with explicit unavailable/forbidden states. Synthetic development data is allowed only by an explicit ALLOW_SYNTHETIC_FALLBACK=true setting, outside NODE_ENV=production and APP_ENV=production, and only for upstream connectivity/timeouts or 5xx. The same policy applies to the search BFF. Fixtures honor query, type, asset class, status and pagination, report total, and remain visibly labeled after every search.
4. Stream catalogue loading independently of the verified workspace shell. Add loading and error boundaries to the affected routes, with appropriate root/global recovery. Resolve tenant identity first, then start independent permitted reads without serial waterfalls. Avoid persistent authorization caching. Share session resolution within a request where needed.
5. Cancel active searches on dependency changes and unmount, and suppress every stale success/error/finally update. Keep a stable complete instrument-type list from contract-supported values rather than deriving choices from the current result page. Supply source status to the shell through a focused client wrapper, avoiding another workspace request for server-verified pages.
6. Reuse a workspace access result, service error panel and API transport helpers across instruments, operations, strategies, trades, market data and valuation. Retain existing permission checks in routes and mutations. Extend shared handling to other workspace pages discovered during implementation without changing their financial behavior.

## Alternatives
- Recommended: repair shared data access and failure semantics, then introduce focused modules and route boundaries. This targets demonstrated failures and limits migration risk.
- Move every route into a shared workspace layout immediately: reduces shell duplication but risks stale tenant context and broad permission regressions. Defer until the corrected flows have browser evidence.
- Change frontend framework or component library: unsupported by the evidence and unnecessarily disruptive.

## Verification and acceptance
Add failing regression tests for the observed outage redirect, production fixture substitution, development authorization fallback, ignored fixture filters and stale search responses. Cover timeout expiry and caller cancellation; write requests retain existing behavior. Run focused tests first, then the ops-console suite, TypeScript and a fresh production build. Browser acceptance uses isolated/mock upstream dependencies and read-only navigation: cold/warm /instruments, filtering, pagination, permission denial, delayed API, service outage, retry, tenant switching and source labels. Record measured timings if available; do not claim a performance improvement from unit tests alone.

No database migrations, operating data writes, dependency upgrades, publishing, or git push are included. Production runtime requires ACTIVE_TENANT_COOKIE_SECRET; validation must supply a disposable test secret rather than weaken the production requirement.
