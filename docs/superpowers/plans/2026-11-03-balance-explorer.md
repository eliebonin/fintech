# Accrued-balance explorer implementation plan

**Goal:** Restore independent read-only exploration using the Market Data explorer's
filter → chart → exact datapoint table shape.

**Design:** `/valuation/interest/explorer` selects a readable strategy, a relevant
bond and From/To dates. Explicit Show history applies the whole scope; URL parameters
retain the selection. Render the existing full-series chart and paginated exact
table inline, independently of daily/balance review status. Add an accessible
Explore balances link to both maintenance pages. Reuse the native scoped GETs,
display checks, loading cancellation and 25/50/100/All pagination. No financial
writes, migrations, dependency installs, operating validation or publication.

**Approach:** A standalone page reusing BalanceSeriesReport and balance-series is
smaller and safer than duplicating its chart/table or returning exploration to
the review form. Strategy is required because balances are strategy-owned, unlike
generic market series. Current stored history is shown, with stale/missing states;
this is not historical as-of reconstruction or a maintenance command.

The user's standing preference is continuous sequential implementation in the
current feature checkout, without another approval gate or subagents.

- [x] Add failing navigation, scope-contract and rendering tests.
- [x] Add a thin guarded route, applied filter state and scope-checked read-only
  series rendering, reusing the existing chart/table and permission-filtered options.
- [x] Connect review navigation and contextual page help.
- [x] Run focused UI/TypeScript checks and existing disposable series access tests;
  verify real local history in the browser without saving financial data.
- [x] Reconcile delivery, capability register and implementation links with limits.

Completed: [verification and limits](../../delivery/accrued-balance-explorer-20261103.md).
58 focused frontend tests, TypeScript and 2 disposable-database tests passed.
Browser acceptance verified range application and 25/All pagination on real
stored history without financial writes. No commit or push was requested.
