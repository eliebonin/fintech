# Trade markers on accrued-balance history

**Status:** Implemented alpha · 3 November 2026 · F38/F39  
**Scope:** Read-only annotations in the accrued-balance explorer.

## Display and dates

**Show trades** is checked by default below the closing-balance chart. A narrow
strip uses the same date coordinates as the Line/Bar chart, with green upward Buy
markers and red downward Sell markers on separate rows. Same-day same-side trades
are grouped with a count; buys and sells are never netted. The full requested
event window is independent of balance-table pagination.

Markers use the **valuation recognition date** that the accrued-balance engine
uses for booked accrual movements, falling back to UTC execution date for native
legacy recognition. They do not use settlement date. Hover, keyboard focus or
selection reveals the group's individual trades: exact signed nominal and unit,
signed booked accrued amount and its original currency, counterparty, execution
timestamp, settlement date, balance-impact date and a link to each trade. Missing
accrued or party information remains not recorded, never zero or invented.

Hiding trades removes the strip/details and aborts its outstanding read. The
balance chart, selected Line/Bar mode, monetary values and table page remain.
Failure or denied trade access is a local timeline warning, not an empty event
population or a failure of the balance report. The retained modal viewer keeps
its existing contract; the explorer explicitly supplies the annotation scope.

## Authority and implementation

- [Domain service](../../valuation/balance_trade_events.py) requires both scoped
  `VALUATION_READ` and `TRADE_READ`. The existing tenant modules and HTTP context
  still apply. No user/group grants or calculation permission are introduced.
- The service reuses native immutable ledger reads, frozen booking/recognition
  validation and the accrued-balance fact-selection rules. Canonical bond and its
  visible listings are included; cancellations and superseded erroneous bookings
  follow the ledger's selected-To-date/latest-information semantics. Fully closed
  positions retain their in-window trades. Historical inactive visible bonds
  remain inspectable.
- Keyset ledger reads have no arbitrary total trade cap. Selected metadata and
  counterparty enrichment use bounded batches. Decimal strings and sign changes
  retain exact precision; current display names do not rewrite booking evidence.
- [Thin API adapter](../../apps/reference_api/balance_history_routes.py) exposes
  `GET /v1/valuation/balance-trades`, with workload admission. The
  [BFF](../../apps/ops-console/src/app/api/valuation/%5B...segments%5D/route.ts)
  allows only the explicit strategy/instrument/date filters and verified context.
- [Timeline component](../../apps/ops-console/src/features/valuation/balance-trade-timeline.tsx)
  independently loads the complete scope, rejects partial/wrong-scope/duplicate
  or float-valued responses and uses native checkbox plus keyboard-selectable
  SVG markers. Exact individual details and links remain available outside SVG.

## Interpretation and limits

Markers are ledger annotations known when loaded at the selected To date, not
the frozen source catalogue of a particular historical balance build. Current
party labels may have changed since booking. Stored balance source/staleness
warnings remain applicable; the About trade history disclosure explains this.

This is the existing canonical-bond accrued-balance workflow, not an all-product
trading dashboard, settlement confirmation or cash-flow timeline. It does not
recalculate accrued balances, generate coupons, modify trades or publish P&L.
Dense daily event populations may need further layout refinement; same-day
groups retain every trade without truncation.

## Verification

[Disposable backend tests](../../tests/test_balance_trade_events.py) cover signed
accrual/nominal, frozen next-day recognition, cancellation, full keyset traversal,
flat-position trades, historical inactive instruments, selected-strategy scopes
and separate valuation-only access. Existing full-series and workload regressions
are also checked. [Frontend tests](../../apps/ops-console/src/features/valuation/balance-trade-timeline.test.tsx)
cover grouping, exact values, default-on/keyboard markers, error versus empty,
complete-scope validation and protected BFF filtering.

Final checks: **9 focused backend tests**, **34 frontend tests** and TypeScript
`--noEmit` passed. API 8000 was restarted after confirming no running valuation.
No operating financial data, permissions or review decisions were changed.

Browser acceptance used FCPGF's 3.75% Treasury Gilt 2027, showing five bookings as
four date/side markers: 7 April buy, two 17 April buys, 28 April buy and 28 September
sell. Selecting the grouped buys showed both exact nominal/accrued values and
individual links; one link opened the correct native trade detail. Hiding markers
kept the chart and the 1–25-of-292 table page intact. Restoring markers worked;
no console warning/error was observed. The initially inspected USD Treasury had
no bookings within the selected 2026 window and correctly showed an empty strip.

See [plan](../superpowers/plans/2026-11-03-balance-trade-markers.md) and
[balance explorer](accrued-balance-explorer-20261103.md).
