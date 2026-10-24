# AMC measures and percentage-quoted valuation

Owner-approved scope: implement the three-measure preview and percentage-quoted
daily valuation, then resume the existing import. AMC amendment/lifecycle work
remains deferred. Sequential execution, focused tests, current feature checkout;
preserve unrelated edits and all historical financial evidence.

- [x] Research actual issuer quotation examples and SSPA guidance.
- [x] Add shared domain quotation factors: unit price, percentage/certificate with
  explicit denomination, percentage/nominal without applying denomination twice.
- [x] Verify booking freezes compatible factors; percentage and unit P&L retain
  the same native AMC type and use actual execution economics.
- [x] Extend monetary preview with local/reporting-currency values and source/FX
  evidence. Equal measures are the existing funded-security reporting convention,
  not underlying risk look-through or contractual face.
- [x] Require selected AMC price basis to match frozen quotation; missing or
  conflicting evidence blocks rather than guessing from numerical price level.
- [x] Focused numerical, replay, selection/FX and live integration checks; update
  maintained methodology/capability/delivery records and restart local API.
- [x] Resume retained bundle import with scoped identities and normal writers;
  preserve original values, separate RESET flows and dated cash snapshots.

No migration is expected for the AMC extension. New AMC price series require the
explicit `AMC_PRICE_BASIS` dimension (`UNIT_PRICE` or `PCT_OF_PAR`), not a new price
kind or licence category. Existing booked evidence is not retroactively changed.
Old percentage snapshots with incorrect/missing denomination factors remain
blocked and need normal correction, never silent reinterpretation.

Research checked 23 October 2026:
- [SSPA AMC recommendations, April 2025](https://sspa.ch/wp-content/uploads/2025/03/sspa-amc-recommendations_effective-per-april-1_-2025.pdf).
- [Julius Baer AMC final terms, 3 December 2014](https://derivatives.juliusbaer.com/Content/Document/25b65a08-c3d8-47e0-888d-73402c858721/22757086_TS_EN_29990108.pdf):
  concrete currency-per-certificate issue value and portfolio/fees, not a generic
  assumption that all certificates quote in percentages.
- [UBS certificate final terms, 2025 issue](https://keyinvest-ch-en.ubs.com/filedb/deliver/xuuid/g001ef1186983de02a0fec13e86d769bf34f/name/CH1494074110_Termsheet%2Bat%2Bissue%2Bdate_en.pdf):
  denomination USD1000 and percentage quotation; this is a non-AMC certificate
  illustrating quotation dimensions, not authority to assign its payoff to AMC.

Progress: nine pure quotation examples/invalid-input cases passed after an
observed missing-helper failure. Final focused run: 40 passed in 82.36 seconds,
`logs/amc-measures-focused.log`; includes native approved booking, preview and
daily P&L for all three quotation dimensions, missing FX and wrong-basis rejection.
No migration. Documentation updated; restart/import follow-up remains separate.

Owner ruling for the import, 23 October: retain all source decimal text; truncate
only excess digits toward zero at 12 places rather than half-even rounding.
Retain converted exact value, stored value and exact delta beside each posting.
Do not alter generic validators or make unknown market data/FX zero.

Activation and resumed import: API8001 healthy after restart, frontend3001 HTTP200.
64 investment trades, 121 dated cash snapshots in 8 accounts and 99 daily-interest
inputs are posted through native writers. This resumes, but does not complete,
the broader source import. See [current scope/counts and blockers](../../delivery/fcagf-reconciliation-import-20261023.md#latest-committed-readback).
The swap entry-reference helper now retains exact decimal-text products beyond
12 places, with Inexact trapping, rather than restricting valid source inputs;
fixed-scale funded considerations and payment arithmetic remain unchanged.
One AMC quote retains 11 digits to satisfy native consideration precision with
unchanged quantity; material additional truncation is refused. Focused regressions
and source-original/delta evidence are recorded in the delivery ledger.

Final review: sequential self-review (owner requested no subagents), not an
independent audit. Public upload coverage and unsupported SWAP/OPTION daily P&L
were not expanded just for this reconciliation. No Git commit/push or full-suite
run. An unrelated existing documentation trailing-space finding was preserved;
the files touched by this follow-up pass their scoped diff whitespace check.
