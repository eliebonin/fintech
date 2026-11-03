# FCAGF / FCPGF daily accrual CSV refresh

**Date:** 3 November 2026  
**Status:** Committed and verified for both strategies  
**Classification:** Owner-authorized local reconciliation data operation, not a
supported product CSV workflow or application change.

The owner refreshed the `accrued_interests` files and requested new datapoints.
The read-only comparison found no changes to existing bond/date amounts or
currencies. Existing native inputs remain unchanged; only new bond/date inputs
are appended through the isolated import tooling and native daily-interest writer.

| Strategy | Bond/date inputs already present | New inputs | Resulting supported inputs | Supplied range |
| --- | ---: | ---: | ---: | --- |
| FCAGF | 99 | 128 | 227 | 20 May–20 October 2026 |
| FCPGF | 462 | 1,368 | 1,830 | 2 January–20 October 2026 |

Source trade-level earnings are aggregated once per bond/date/currency. The files
contain 239 FCAGF and 4,452 FCPGF rows; these are not counts of position-level
inputs. All supported aggregates fit the native 12-decimal precision exactly:
no truncation or rounding is needed. Dates absent from the source are not invented.

Subsequent owner instruction: [expand the maintained balance history](expanded-accrued-balance-history-20261103.md)
using the longer source window, provisional zero opening and schedule-based
stock resets while preserving reviewed closing assessments. The original
operation described below remains retained historical evidence.

## Source evidence and safety

Original CSV bytes and new bundle manifests are retained in ignored local
reconciliation logs, with native source-payload receipts. Existing approved bond
definitions and retained reference mappings are reused, including bonds shared
between the two strategies. Owned source and strategy checks remain enforced.
The private incremental operator stays outside product packages and versioned
source; the existing optional tooling and native financial services are unchanged.
Each strategy imports transactionally and compares every supported current amount
and currency against the CSV before commit. The final read-only replay found no
new or differing supported datapoints (227 FCAGF and 1,830 FCPGF matched). The existing posting/replay tests passed in an
owned disposable database (2 tests).

This operation does not validate Ops reviews, rebuild balances, modify trades,
recalculate or publish valuations. Earlier provisional closing-stock assessments
are independent inputs: new earlier earnings do not silently recompute those
assessments. Review/revise those stocks as necessary before rebuilding history;
existing stale-source checks remain applicable.

## Deferred: fund distribution / yield accruals

The refreshed FCPGF file also includes **546 trade-level rows**, aggregated into
**30 fund/date datapoints** (10 per class), for source instruments:

| Source ID | Share class | Currency | Decision |
| --- | --- | --- | --- |
| 1849 | US equity income fund, F GBP distributing hedged | GBP | Not imported |
| 1853 | US equity income fund, F USD distributing non-hedged | USD | Not imported |
| 1856 | US equity income fund, D USD distributing non-hedged | USD | Not imported |

The owner explicitly deferred these for investigation. Raw rows are retained as
evidence but no daily-interest input, distribution, cash flow or zero is generated.
The current native daily-interest service accepts canonical bonds and structured
notes, not fund share classes. Do not relabel them as bonds or cash to force import.

Before implementing fund accrual support, establish what these amounts represent,
their recognition dates and currency, whether NAV already includes the income,
the meaning of negative/reset entries and the distribution/reset relationship.
Determine whether the right representation is daily accrued income, a distribution
event or another economic adjustment; prevent duplicate recognition with NAV moves
and paid distributions. This is an open F38 investigation, not delivered support.

## Retained operation identities

- FCAGF bundle: `7a3881096850df8bab376f15685c0697d714a9f168aef4fac7b787ac4e990adb`
- FCPGF bundle: `1ef000e11a8cfa297b282e737693e7731b7baeb0681989cfd0ffad8d3babc14d`
- Per-strategy private reports: `daily-accrual-refresh-20261103-report.json` within
  the corresponding ignored retained bundle directory.

See [optional import boundary](../../tooling/reconciliation_csv/README.md),
[Ops review](interest-daily-review-20261103.md) and
[previous provisional stocks](provisional-accrued-balances-20261101.md).
