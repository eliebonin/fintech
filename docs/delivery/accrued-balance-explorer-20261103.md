# Accrued-balance explorer

**Status:** Implemented alpha · 3 November 2026 · F38/F39

## User workflow

Open `/valuation/interest/explorer`, also available as **Explore balances** from
both interest-review pages. Select a readable strategy, search/select its bond,
choose From/To dates and **Show history**. The selection is retained in the URL;
entering from review preserves the strategy and uses its value date as To date.
The default range is 30 calendar days ending on To date.

The layout follows Market Data exploration: applied instrument/range header,
full-range chart, then the exact datapoint table with 25/50/100/All pagination.
Table pagination does not truncate the chart. Currency histories are separated
when more than one exists. Source evidence is disclosed per row; technical UUIDs
are not the primary selection labels.

**Chart type** defaults to **Line**, with an optional **Bar** view above the chart.
The shared report (including its modal viewer) plots the same closing balances in
either view. Bars start at zero, negative stocks extend below zero, and known zero
stocks have a small marker; missing/unassessed days have no bar. Stale marks retain
their warning colour. Hover/tap and keyboard inspection retain exact amounts.
Switching views leaves table pagination and financial data unchanged; a new report
starts with Line again. Focused chart/explorer/table checks: 17 passed plus TypeScript.
Browser acceptance confirmed default Line, Bar and switching back, with identical
table rows and no console warnings/errors. Edge bars are clipped to the date range
without shifting into adjacent days; missing days do not acquire bars.

The monetary Y axis uses rounded ticks with an explicit, labelled zero reference
in both Line and Bar views. Positive-only series start at zero; negative-only
series end at zero, and mixed-sign series retain both sides with zero labelled
once. An all-zero series gets a non-degenerate zero-based scale. This changes
plot coordinates only, not stored amounts or exact table data.
Zero-axis verification: 18 focused tests and TypeScript passed. The FCPGF browser
chart showed 0 / 100,000 / 200,000 / 300,000 / 400,000 ticks and exactly one zero
reference in both Line and Bar modes, with no console warnings/errors.

Balances belong to a strategy, so strategy selection is mandatory even for the
same instrument. Stored history can be explored before daily/balance review is
validated. This page does not save assessments, rebuild history, confirm coupon
payments or publish P&L. Changed filters are explicitly unapplied until submission;
loading/failure of a new scope never displays an old chart as its result.

The [trade-marker follow-up](balance-trade-markers-20261103.md) adds a default-on
Show trades strip below the chart. Same-day Buy/Sell groups open exact individual
trade details and links; current trade-read scope is enforced independently.

## Reuse and boundaries

- [Thin route](../../apps/ops-console/src/app/valuation/interest/explorer/page.tsx)
  uses the existing guarded
  [server wrapper](../../apps/ops-console/src/features/valuation/interest-ops-page.tsx).
- [Explorer UI](../../apps/ops-console/src/features/valuation/balance-explorer.tsx)
  reuses readable-strategy choices, scoped `interest-options` and the existing
  `balance-series` GET through the verified BFF. Existing module, strategy and
  source-display checks remain. No new API, schema, permissions or dependencies.
- [Response checks](../../apps/ops-console/src/features/valuation/balance-explorer-model.ts)
  reject incomplete series, wrong instruments, dates outside the applied range,
  duplicate row identities and numeric floats replacing retained decimal strings.
  Request cancellation and bounded GET retry reuse the interest transport.
- [Existing chart/table](../../apps/ops-console/src/features/valuation/balance-history-chart.tsx)
  keeps the full series and exact amounts. Missing/unassessed dates break the
  line and never become zero; stale sources remain visibly flagged. SVG coordinates
  are approximate; exact values and lineage remain available in the table.
- Contextual page help explains selection, source states and read-only impact.

## Limits

This initial explorer covers the existing canonical-bond maintained histories,
not generic market prices or every future interest-bearing product. It shows
the latest stored revision per date with current source checks, not a historical
information-cutoff reconstruction. It does not fabricate missing dates or rebuild
stale balances. The complete single-instrument series is fetched for the chart;
table pagination is client-side. Extremely long histories may eventually need
a bounded chart-sampling contract while preserving exact paginated data.

## Verification

58 focused UI/model/navigation/chart/table/transport/help/BFF tests passed;
TypeScript `--noEmit` passed. Both disposable-database tests in
`test_balance_series_api.py` passed, covering complete 35-day history, exact
precision, range filtering, unrelated instruments, readable-only access and
foreign-strategy denial. Browser acceptance used FCAGF stored history: 33 datapoints
plotted with 25 + 8 paginated rows and all 33 with All; changing the applied range
to 1–20 October refreshed both chart and table to 20 datapoints. Unapplied edits
kept the old report labelled correctly. A date-input event issue discovered in
browser testing was corrected: the form reads submitted native field values and
updates its draft on input as well as change. After frontend restart, a fresh
load/range change produced no browser warnings/errors. No financial data writes or
operating validations were performed. No backend restart or migration was needed.

See [implementation plan](../superpowers/plans/2026-11-03-balance-explorer.md) and
[two-stage maintenance](interest-daily-review-20261103.md). The Market Data page
is an existing product consistency reference, not a shared financial source.
