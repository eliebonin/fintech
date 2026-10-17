# Valuation results and operational history reports

**Status:** Implemented; local activation and bounded verification below  
**Content type:** Delivery / UI and read-API decision  
**Owner:** Valuation and operations console  
**Last reviewed:** 2026-10-14

## Intent and agreed scope

Retain Input form, Results and History, but stop opening a historical financial
result implicitly on page load. The user approved strategy-first Results, a
date-filtered operational History report, and separate calculation/publication
labels. Filters must apply server-side before pagination and counting. Results
must support readable strategies even if the user cannot calculate on them.

Valuation purposes and descriptive tags are separately [deferred as F57](../product/features/valuation-and-pnl.md#f57-valuation-purpose-and-descriptive-tags).
No NAV/live-price capability, calculation economics or publication lane changed.

## Delivered behavior

- **Input form:** Calculation form retained. Its strategy choices exclude rows
  with `canCalculate=false`; a readable strategy is not implicitly runnable.
  Form drafts and frozen retry keys/payloads survive report navigation.
- **Results:** Initially requires a strategy, closing-valuation date range and
  Find results. Last 14 days is the initial range; Single day sets both boundaries
  to the selected To date. Publication filters include staged, published,
  superseded and cancelled. Rows retain separate recorded attempts and policy
  versions, showing guarded headline P&L/currency without adding overlapping runs.
  Opening a row reveals the existing immutable result/position review. Back to
  results restores the same report/filter state. A calculation response can still
  open its own result directly after the user submits the input strategy.
- **History:** Date/optional readable-strategy, calculation and publication filters;
  table rows include period, policy version, London run time, both statuses and
  recorded failure reason. Includes failed attempts without financial results.
  View logs selects the existing Results detail and expands its operational log.
- **Dates:** Inclusive filters refer to the **closing valuation date**, not run
  start time. Single-day reporting selects results closing on that date, including
  a result whose opening date is earlier; it does not force a zero-length
  calculation. Run timestamps remain separately labelled London time.
- **States:** Completed · Staged — not published; Completed · Published;
  Completed · Superseded; Completed · Cancelled — not published; Failed · No
  result; Running · Calculation in progress. A completed attempt with no recorded
  batch is explicitly labelled No result recorded, never inferred published.
- Editing report filters clears prior rows/counts and invalidates outstanding
  responses. Apply/Find explicitly performs the next query. Pagination retains
  the applied filters; local table slicing is not used for history selection.

## Read-API and security boundary

`GET /v1/valuation/attempts` accepts `strategy_id`, `from_date`, `to_date`,
`calculation_status`, `publication_status`, and `results_only`, alongside existing
limit/offset. A shared SQL relation applies tenant and action-bound strategy READ
scope, filters and one current linked batch per attempt **before** page/count.
The relation also handles a recorded idempotent-reuse batch link. Result metadata
adds actual `batch_id`, `batch_status`, `valuation_date` and recorded failure reason.

Only `results_only=true` returns headline financial fields, after the same current
`assert_batch_display` checks as detail evidence. Restricted rows contain safe
operational metadata and `evidence_access=DENIED`, not financial values. History
does not fetch/release financial summaries. Count visibility remains scoped.
Explicitly guessed or malformed strategy IDs still hit the existing authorization
boundary (403); date/status validation errors are 422. These guards were not relaxed.

Options are scoped to VALUATION_READ, including retained non-active strategy
metadata for historical browsing, and carry separate `canCalculate` flags from
active strategy status and VALUATION_RUN scope. UI convenience checks do not grant
authority. The BFF forwards only the allowed report filters and trusted session
context, not client-provided tenant/actor identity. Existing independent review,
immutable evidence, amendment and publication checks remain authoritative.

## Source-backed presentation rationale

[GOV.UK table guidance](https://design-system.service.gov.uk/components/table/),
checked 14 October 2026, supports scanning/comparing rows, descriptive captions and
semantic headers. It informs these reports; choosing valuation-date filters,
strategy-first navigation, and dual statuses is our project decision. Prior
[tab/accessibility research](valuation-review-workspace-20261013.md#additional-source-backed-decisions)
still applies to the tab shell and preserved drafts.

## Verification and local activation

- Test-first query/BFF/report regressions; final focused verification is recorded
  below. Real handlers are exercised with the repository's persistent-hook state
  driver, not a new DOM runtime. The single-day shortcut regression failed before
  its fix and passed afterwards. Tests also reject stale response reuse and prevent
  restricted headline financial amounts from rendering.
- **24 affected Python tests passed** through
  `scripts/run_isolated_python_tests.py tests/test_valuation_history_api.py tests/test_valuation_history_query.py tests/test_valuation_api.py tests/test_strategy_scopes_api.py -q`.
  The runner created/migrated/seeded and removed its owned disposable database;
  the operating database was not used for tests. One existing Starlette/httpx
  deprecation warning remains. Coverage includes 26 matches over two pages,
  filtered counts, publication-state selection, restricted financial evidence,
  read-without-run options and explicit guessed-strategy denial.
- **58 focused frontend tests passed across 11 files**, including console/tab,
  report, result/review/input workspace, page/BFF, readable failure, price evidence
  and frozen daily request coverage, with `--maxWorkers=2 --testTimeout=15000`.
  `pnpm typecheck:ops-console`, `pnpm contract:check` and `git diff --check` passed.
  OpenAPI and generated TypeScript contracts were refreshed. Repeated generation
  left their TypeScript SHA-256 unchanged. `pnpm contract:generate:check` reports
  a diff against committed HEAD because the intended contract changes (plus
  pre-existing branch changes) are uncommitted; that Git-based gate is not claimed
  passed. No commit/push or full application suite was requested/performed.
- Local API restarted on port 8000 after verifying the old exact Uvicorn process;
  logs: `logs/api-valuation-report-20261014.out.log` / `.err.log`. Frontend hot reload
  picked up the UI. No database migration was required.
- Browser verification used existing Strat Testing runs under the same demo
  operations identity, entered through the normal local context selector without
  grant changes. Initial Results showed no financial detail; strategy/date search
  returned four recorded results with staged/cancelled states; single-day October 7
  returned one result. Open/Back preserved the filter state; filtered failed History
  opened an expanded log with Failed · No result. At 732px viewport, page width
  equalled scroll width. No calculation, amendment or publication was submitted.

## Publication-action follow-up

Current authority follow-up: [explicit self-publication](valuation-self-publication-20261014.md)
adds opt-in/scoped continuity exceptions; the independent path and this delivery's
default-disabled maker behavior remain, without automatic permission grants.

### Prominent publication action — 14 October follow-up

An opened staged result now displays **Publish valuation** near the top, after
its recorded context and before position tables. It opens an inline confirmation
with required review decision, Confirm publication and Cancel. The previously
buried publication disclosure was removed; both use the same existing publish
endpoint and review payload. The maker sees a disabled action and independent
review explanation. Users without review permission, non-staged batches and
restricted DISPLAY evidence receive no active publication control. The server
still enforces strategy permission, real-operator independence, source revision,
pending-amendment and financial reconciliation checks; the button does not assert
that those checks will pass.

Browser acceptance opened and cancelled this form on the existing staged result:
required comment present, focus restored to Publish valuation, status still
Completed · Staged — not published. No publication was submitted. Component
regressions cover visibility, maker/review restrictions, terminal batch states
and opening/cancelling without invoking publication. Implementation:
[publication action](../../apps/ops-console/src/features/valuation/publication-action.tsx),
[state/permission tests](../../apps/ops-console/src/features/valuation/publication-action.test.tsx),
[interaction test](../../apps/ops-console/src/features/valuation/publication-action.interactions.test.tsx).

Follow-up verification: **50 focused frontend tests passed across nine files**;
`pnpm typecheck:ops-console` passed. No API restart, migration or financial write
was needed for this presentation-only follow-up.

## Deliberate limits

- Read reports page 25 rows (API maximum 100, existing offset ceiling 10,000).
  Strategy/policy options retain their existing 500-row bounds. These are reporting
  limits, not trade/position limits in financial calculations.
- Financial headline disclosure currently loads the selected page's batch evidence
  and performs per-batch permission checks. This avoids a browser request per full
  result, but is not a constant-query large-universe analytics endpoint. Batch
  permission-query optimization and representative performance benchmarks remain.
- Labels come from accessible current options, falling back to recorded IDs;
  frozen identity/policy IDs remain authoritative. No new immutable label snapshots.
- Date filters do not filter run-start timestamps; that is separately labelled,
  not a silently interchangeable date basis. URL/deep-linked filters, export,
  custom column management, async calculations and persisted report preferences
  are not delivered here. No full accessibility or financial sign-off is claimed.

## Implementation evidence

- [SQL reporting foundation](../../valuation/history.py), [API](../../apps/reference_api/valuation_routes.py),
  [query tests](../../tests/test_valuation_history_query.py), [API/security tests](../../tests/test_valuation_history_api.py).
- [Console](../../apps/ops-console/src/components/valuation-console.tsx),
  [reports/status labels](../../apps/ops-console/src/features/valuation/run-report.tsx),
  [report interactions](../../apps/ops-console/src/features/valuation/run-report.test.tsx),
  [tab/draft regressions](../../apps/ops-console/src/components/valuation-tabs.test.tsx).
- [BFF](../../apps/ops-console/src/app/api/valuation/%5B...segments%5D/route.ts),
  [BFF allowlist tests](../../apps/ops-console/src/app/api/valuation/%5B...segments%5D/route.test.ts),
  [styles](../../apps/ops-console/src/app/valuation-workspace.css).
