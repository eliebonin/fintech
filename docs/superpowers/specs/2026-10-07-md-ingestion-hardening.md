# Market-data ingestion hardening

## Intent and scope

Harden the existing local, personal, EOD ingestion flow after the 543-listing backfill. Keep ingestion segregated, execute sequentially in the current feature checkout, preserve existing work and prices, and do not introduce valuation/P&L, a scheduler, a microservice or automatic historical alias guesses. The owner has instructed execution without another plan-approval stop.

## Design

Use small modules and additive operational tables rather than a workflow platform. A job records its exact selection/window, tenant/actor and lifecycle. Attempts are committed before HTTP and finalized after publication or failure; finalized evidence is immutable. Forced process termination leaves RUNNING evidence explicitly unresolved, not silently COMPLETE. Explicit operator recovery may mark it ABORTED, never publish data or reassign a live job automatically.

Outcomes: COMPLETE when all selected delivery results are successful, PARTIAL for retained rejections or mixed success/failure, FAILED when no successful work exists, BLOCKED for rights or provider access denial, ABORTED for interruption. Exit codes: 0 COMPLETE, 3 PARTIAL, 1 FAILED/BLOCKED/ABORTED; argparse keeps 2. These are delivery outcomes, separate from calendar quality/continuity certification. Resumed partial deliveries remain PARTIAL. --retry-gaps retries only explicit rejected dates inside the exact original request, using bounded contiguous spans and normal rights/publication. It never invents omitted sessions or retries permanent identity failures as prices.

Calendar audit compares actual current points with versioned pandas-market-calendars schedules for explicit supported MICs. Report missing internal/trailing sessions, unexpected dates and unavailable leading history separately. Do not treat first source date as proof of listing inception. Unknown calendars yield NOT_ASSESSED, never weekday completeness. Read-only --audit-only needs DISPLAY rights and no Yahoo HTTP. Calendar metadata/version and interpretation accompany every report; no calendar feed is claimed authoritative.

Historical mapping reviews record inclusive market-date coverage, attributed actor and evidence; default REVIEW_REQUIRED does not claim continuity or rewrite old observations. Current review intervals cannot overlap; rejected history blocks new publication within the rejected period. One exact symbol/current venue match is still not an issuer-history certification. Audit surfaces REVIEW_REQUIRED until a reviewed interval covers the request. No review records are fabricated for the imported universe.

Generic ingestion validates normalized finite positive PRICE values, timezone-aware timestamps, exact window/series declarations and stable per-series source-field/value-basis/timestamp dimensions. Source alias changes must not create two current marks for one series/date. Preserve source keys and append-only revisions. Full layered acquisition evidence remains on the retained delivery; choose the observation's single legacy acquisition licence deterministically, document that it is not the complete layered permission proof.

## Acceptance

- Same partial outcome/exit on fresh, replayed and resumed deliveries; duplicate-only rejection is partial, not complete.
- Exact-window bounded gap planning ignores permanent errors and never expands original dates.
- Persist successful, failed, denied, replayed and interrupted attempts; terminal records cannot be rewritten.
- Holidays are not gaps; omitted open sessions are gaps; short history and uncertain continuity remain separate.
- Wrong semantic dimensions/invalid normalized points are retained as rejections before publication.
- Changes do not mutate existing financial records or source prices; focused tests first, full disposable-database suite last.

## Research basis (opened 2026-10-07)

- [OpenLineage run cycle, documentation 1.53.0](https://openlineage.io/docs/spec/run-cycle/): separate lifecycle events and terminal states. Our PARTIAL/BLOCKED are local operational extensions, not claims of OpenLineage conformance.
- [AWS Builders' Library: safe idempotent retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): stable request identity and equivalent retry semantics. Apply to retained deliveries and exact gap spans, without AWS infrastructure.
- [pandas-market-calendars documentation](https://pandas-market-calendars.readthedocs.io/en/stable/), [5.5.0 release, 5 October 2026](https://pypi.org/project/pandas-market-calendars/): versioned schedules distinguish exchange sessions/holidays; local package rules require updates and are not live feeds.
- [PostgreSQL 18 explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html): row locks last until transaction end. Keep them around publication/state transitions, not HTTP/backoff. Retain dataset serialization for the alpha, not premature concurrent workers.

Choice: small durable ledger plus read-only audit is more proportionate than a queue/orchestrator and more reliable than adding log parsing alone. Trade-off: source continuity still requires real review evidence; software cannot manufacture it.
