# Accrued-balance chart implementation plan

**Goal:** Open a read-only single-bond balance chart from each balance row with its instrument preselected, date controls and the full datapoint table below, paginated 25/50/100/All. The owner requested row context instead of a standalone chart button during implementation.

**Architecture:** Reuse current scoped history reads and exact decimal DTOs. Add an instrument-filtered series GET, a native modal viewer and an SVG chart with visible gaps. Fetch the entire selected series once; table pagination never truncates the chart. Browser numbers are drawing coordinates only. Existing balance maintenance, coupon treatment and valuation arithmetic stay unchanged.

**Execution:** Sequentially in the authorised checkout; preserve unrelated changes. No commit/push, migration, financial write or valuation rerun is part of this task.

- [x] Add failing API tests for full-series reads beyond 25 rows, instrument/date filtering and strategy denial; add chart-gap, precision and pagination tests.
- [x] Add the scoped series GET, SQL instrument predicate and explicit BFF allowlist/query forwarding. Long read ranges remain available; the update command's existing date budget is separate.
- [x] Extract the shared history table/types; implement chart geometry, exact table and 25/50/100/All navigation, plus bond/currency/date controls in a dismissible native dialog.
- [x] Wire row-context viewer actions for readable strategies, preserve close focus/Escape, handle empty/error/stale responses and discard obsolete requests.
- [x] Run focused disposable database/frontend tests and TypeScript, restart only the owned API, and verify the live viewer using read-only existing data.
- [x] Update capability/register/map, page guide and delivery references with scope and limits.

Delivery and final verification: [balance chart](../../delivery/accrued-balance-chart-20261101.md).

Research: [native dialog semantics](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog),
[W3C complex-chart text alternatives](https://www.w3.org/WAI/tutorials/images/complex/).
Use the native modal's focus/inert/Escape behavior and an adjacent exact table.
Do not interpolate missing amounts, imply a scheduled coupon reset was implemented,
mix currencies into one line or compute financial balances in the browser.
