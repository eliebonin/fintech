# Local production frontend comparison — 12 November 2026

The user requested a production-mode app run to compare responsiveness with development. The frontend is built with the installed Next.js16.4.3/Turbopack and served through `next start`; the existing local API/database and identity safeguards are retained.

| Component | Address / mode |
| --- | --- |
| Production frontend | Comparison used `http://localhost:3008/select-context` · subsequently stopped at user request |
| Development frontend | `http://localhost:3001/select-context` · retained for comparison |
| API | Existing port8000 · unchanged |
| Database | Existing project PostgreSQL port15432 · unchanged |

Build output is isolated under ignored `apps/ops-console/.next-production-20261112/`; it does not share the dev compiler/cache. Compilation and build TypeScript checks passed. The two generated type imports and TypeScript includes that Next modified during the build were restored exactly to their pre-build content after validating those were the only deltas. No product source or financial/configuration data was changed.

## Local launch

From the repository root, use the existing local server configuration; do not replace `APP_ENV` with a production trust mode merely to select the optimised JavaScript build. `NODE_ENV` describes the frontend build; `APP_ENV` governs the separate local identity safeguard. The local context selector remains a local testing tool, not a deployed production login.

```powershell
$env:NEXT_DIST_DIR='.next-production-20261112'
pnpm --dir apps/ops-console exec next build
pnpm --dir apps/ops-console exec next start -p 3008 -H 127.0.0.1
```

The active process was launched hidden with unchanged private local server environment values. PID, port and output path are retained under `productionFrontend` in ignored `.superpowers/sdd/2026-11-11-local-port-recovery/app-processes.json`; private task logs and comparison artifacts are in ignored `.superpowers/sdd/2026-11-12-production-frontend/`. Verify PID/command ownership before stopping either app. Toolhive is untouched. Subsequent code changes require a rebuild to appear in this production frontend.

## Verification and measurement boundary

Production `/select-context` returned200 and its script policy does not include development `unsafe-eval`. Both frontend origins passed a live authenticated, read-only Lifecycle request against the same API. Warm HTML-response timings and full production browser hydration checks are recorded in the local comparison evidence when complete; these must not be described as full interaction speedups or as changes to database calculation speed. One initial comparison attempt stopped at an unclassified non-200 Lifecycle warm-up; the following diagnostic returned200 on both origins. Temporary verification sessions are revoked in `finally` blocks. No operating trades, permissions, strategy calendars or valuations are written by these checks.

## Completed comparison

Warm HTTP medians, alternating request order against the same tenant/user/API/database:

| Read | Dev3001 | Production3008 |
| --- | ---: | ---: |
| Workspace selector HTML | 120.95 ms | 24.59 ms |
| Lifecycle HTML | 306.20 ms | 126.49 ms |
| Structured Lifecycle data,270 events | 6084.00 ms | 4987.56 ms |

HTML uses5 measured samples per origin after an excluded warm-up; data uses3 samples after warm-up. These are complete HTTP response times, not first paint/full-interaction measurements or database-only execution time. The data samples varied around4.4–6.3seconds across both frontends; API/database work is unchanged, so the difference is not attributed solely to frontend production mode. The earlier lifecycle batch timings describe a different run and measurement boundary, not this current shared-load sample.

A fresh isolated Edge context verified that production tenant choices hydrated and the authenticated Lifecycle report loaded with no JavaScript page errors. Temporary verification session cleanup succeeded. The built script policy retained production restrictions without development unsafe-eval. Production frontend was subsequently stopped at the user’s request on12 November; dev3001/API8000 were verified healthy at that checkpoint. A later request authorises stopping development/API and the project PostgreSQL container after commit/push. Runtime status is tracked in the ignored owned-process inventory; the persistent database volume is retained. Toolhive services are outside that shutdown scope. No test suite was rerun: this task used the production build/typecheck, live read comparisons and production browser smoke check.
