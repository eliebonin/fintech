# Accrued-balance evolution viewer

**Date:** 1 November 2026  
**Status:** Implemented and locally verified  
**Scope:** F38/F39 read-only display; existing PARTIAL/ALPHA classifications remain.

Each balance row on the Accrued balances tab at `/valuation/interest` has a
**View chart** action. It opens a modal with that row's bond preselected and
independent From/To dates. The former standalone chart button is removed.
The chart shows stored local-currency closing balances day by day, followed by
the exact stored datapoint table. The table defaults to 25 rows with 50, 100 and
All options, Previous/Next and a full filtered record count at the bottom.
Pagination never truncates the plotted series.

## Behavior and boundaries

- Missing calendar dates and null balances break the line; neither becomes zero
  or an interpolated amount. Actual zero and negative balances remain plottable.
- One currency is plotted at a time. If historical rows have different currencies,
  the viewer offers an explicit currency choice rather than combining amounts.
- Chart coordinates use approximate JavaScript numbers; labels, table values and
  evidence retain the server's exact decimal strings. Unplottable numeric ranges
  leave the table available with an explanation.
- Stale sources remain visible with a warning and distinct point styling. Source
  freshness does not imply external reconciliation or complete financial coverage.
- Hover/tap shows an exact value. Keyboard users focus the chart once and use
  left/right arrows, Home or End, rather than tabbing through hundreds of points.
- The native modal supports Escape, an explicitly named close button, focus
  containment and return to the clicked row's button. No edits or publication actions occur
  inside this viewer. Old asynchronous responses cannot overwrite a newer choice.
- Longer read ranges are allowed independently of the maintenance command's
  existing 366-day update budget. The viewer loads all existing rows for one bond;
  there is no first-page/100-row chart cap. All can render a large table and is a
  deliberate user choice; very long histories have not been performance-certified.

This delivery does not rebuild balances, apply coupon-schedule resets, confirm
payment, perform accounting or alter valuation arithmetic. It displays the current
stored history, including the separately documented provisional zero-opening data.

## Implementation

- [Instrument-filtered history query](../../valuation/balance_history.py) applies
  strategy/tenant/reference predicates before selecting latest dated revisions.
- [Series GET](../../apps/reference_api/balance_history_routes.py),
  `/v1/valuation/balance-series`, checks current valuation-read/module/strategy
  authority and returns the full selected instrument/date series. Full build
  source catalogues remain inspectable separately; SQL omits their duplication
  in every returned chart row. Existing history pagination remains unchanged.
- [BFF allowlist](../../apps/ops-console/src/app/api/valuation/[...segments]/route.ts)
  forwards only strategy, instrument and date filters through verified context.
- [Viewer/report](../../apps/ops-console/src/features/valuation/balance-history-chart.tsx),
  [geometry/pagination](../../apps/ops-console/src/features/valuation/balance-chart-model.ts),
  [shared exact table](../../apps/ops-console/src/features/valuation/balance-history-table.tsx),
  [styles](../../apps/ops-console/src/features/valuation/balance-history-chart.module.css).
- Live acceptance exposed an existing nested-correlation defect in the bond-option
  query: one listing trade could cause unrelated visible bonds to appear. Explicit
  correlation now binds the listing and canonical instrument to the selected
  strategy. Visibility and permission checks remain in place.

## Research

[MDN's native dialog guidance](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
informs modal focus, Escape and showModal usage. The component does not add a
tabindex to the dialog itself. [W3C's complex-image guidance](https://www.w3.org/WAI/tutorials/images/complex/)
supports a concise chart description with an adjacent accessible data table.
These presentation choices do not certify economic correctness of source amounts.

## Verification and activation

Focused disposable-PostgreSQL checks (14 passed) cover complete series beyond the loaded page,
exact decimal transport, instrument/date/long-range filtering, read-only access,
scope denial and unrelated-bond exclusion. Frontend checks cover gap geometry,
zero/negative/flat/huge values, default/full pagination, modal markup and allowlisted
transport. Frontend checks cover per-row context selection and suppress chart
actions inside the viewer's own datapoint table. The chart action sits beside
the bond, so it remains visible before the wide monetary columns.

API 8000 was restarted to activate the series read and picker correction. Live
read-only acceptance used FCPGF's existing 61-date USD bond history: 25 rows by
default, 50 rows plus an 11-row second page, and 61 rows for 100/All. The chart
kept all 42 assessed points across every table mode. Keyboard inspection reached
the exact final value, Escape closed the modal and restored focus. After the owner
requested row-based actions, a non-first GBP bond row correctly preselected its
own instrument; the standalone button was absent and all 25 visible rows had
their own actions. The corrected picker had 20 relevant bonds plus its placeholder,
rather than unrelated catalogue entries. No console errors/warnings were observed
in the initial live walkthrough. Final checks passed **38 frontend cases** and
TypeScript `tsc --noEmit`. A clean-page walkthrough confirmed that the non-first
row's instrument was selected automatically and Escape returned focus to that
same row's button. The row-selected 61-date chart still defaulted to 25 table
rows, with no browser console warnings/errors. The separate viewer table has no
nested chart actions. No migration, financial write or valuation rerun was performed.
