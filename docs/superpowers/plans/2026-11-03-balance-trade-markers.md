# Accrued-balance trade markers

**Approved scope:** A Show trades toggle, enabled by default, displays a narrow
date-aligned Buy/Sell event strip below the accrued-balance chart. Group same-day
same-side trades. Hover/keyboard/select details show exact signed nominal, signed
booked accrued interest and currency, counterparty, execution/settlement dates,
and links to the individual trades. Mark the valuation recognition date used by
the balance calculation, not settlement. Preserve Line/Bar, exact table pagination,
unknown/stale source states and all financial data.

**Implementation:** Reuse canonical bond/listing ledger facts and cancellation
rules in a read-only `valuation.balance_trade_events` service, behind a thin
`balance-trades` GET adapter and existing BFF. Require both scoped VALUATION_READ
and TRADE_READ. Load event data independently: permission/source failure never
breaks the balance chart and is not presented as an empty trade population.
Use the shared report with an explicit explorer trade scope; preserve the retained
modal contract. Current
known ledger annotations are distinct from frozen history-build source proof.

Standing preference: current feature checkout, sequential work, no approval gate
or subagents. No migrations, financial writes, grants, commits or pushes.

- [x] Failing domain/API tests: dates, exact signs, same-day events, cancellation,
  selected instrument/strategy, read-only/denied scopes and no arbitrary trade cap.
- [x] Native ledger service, endpoint and BFF transport; preserve source failures.
- [x] Failing timeline grouping/rendering and transport tests, then the toggle,
  aligned strip, accessible selection/details and exact links/values.
- [x] Focused checks, safe API restart and read-only operating browser verification.
- [x] Document capability links, permission/date semantics and limits.

Completed: [delivery, verification and limits](../../delivery/balance-trade-markers-20261103.md).
9 focused backend tests, 34 frontend tests and TypeScript passed. Browser checked
real stored bookings, grouped details, hide/show and an individual trade link;
no operating financial writes. No migration, commit or push was required.
