# Expanded FCAGF / FCPGF accrued-balance history

**Date:** 3 November 2026  
**Status:** Committed and independently verified for both strategies  
**Scope:** Owner-requested local reconciliation data operation; no product schema
or application changes, trades, cash-payment confirmations or valuation publications.

## Method and authority

After the [daily CSV refresh](daily-accrual-csv-refresh-20261103.md), the owner
requested updating the accumulated-balance history. This extends the earlier
[provisional zero-opening operation](provisional-accrued-balances-20261101.md),
using the already agreed zero-opening assumption at the earlier source boundary:

- FCAGF: provisional closing zero on **19 May 2026**, history from 20 May.
- FCPGF: provisional closing zero on **1 January 2026**, history from 2 January.
- Both end on **20 October 2026**.

Assessments accumulate supplied value-dated earned flows plus known frozen trade
accrual movements. Source amounts are not divided or redistributed across weekend
days. Missing daily inputs remain missing in native history; assessments are
retained on supplied dates and explicit reset/previous-assessment dates, without
generating new daily-interest rows.

The owner previously instructed using coupon schedules for economic balance
resets while deferring payment accounting. Known scheduled coupon dates therefore
clear the preceding accumulated stock **before** adding that day's supplied flow
and trade movements, preserving newly recognized interest. The reset is a
reasoned provisional stock assessment, not a coupon-payment confirmation or new
income. An unallocated source bucket remains attributed to its supplied value
date; this does not establish a separately verified calendar-day earning split.

## Revisions and protected assessments

Original inputs and history builds remain immutable. The operation supersedes
only its older provisional assessments where amounts differ, appends earlier
assessments and calls the existing explicit native history refresh. Existing
independent assessments remain authoritative, including **all 12 reviewed FCPGF
closing balances on 20 October**. The reconstructed bridge may differ from these
curated closing stocks; native anchor-difference evidence remains available for
Ops reconciliation rather than overwriting their decisions.

No daily Ops review or balance-review receipt is fabricated. Existing source
freshness and publication-reassessment checks still apply after source changes.
No previously staged or published financial result is rewritten.

## Coupon-data qualifications

The retained schedules supply two reset dates in FCAGF and twelve in FCPGF across
their history windows. Two FCPGF bonds have no coupon rows in their long 2026
input window: **TII 0 1/2 01/15/28** and **UKTI 0 1/8 08/10/28**. No dates are
invented for these gaps; their cumulative assessments remain qualified and need
schedule reconciliation. Bekarys has a separately supplied 20 October daily input
and reviewed closing balance, but no retained coupon schedule. Unsupported fund
share-class accruals remain deferred as instructed.

All resulting stocks remain **provisional**, not custodian-reconciled balances.
They depend on the owner-zero starting assumption, supplied-flow recognition,
existing execution-accrual evidence and available schedule coverage. CURRENT
source status means fresh retained sources, not financial certification.

## Execution and verification

The ignored private operator is `logs/operations/expand_balances_20261103.py`;
the retained report is its adjacent JSON file. The operator checks its explicit
local database target, scoped authority and current sources; native commands
serialize revisions and audit inside one transaction per strategy. It verifies
exact materialized closings against every new/revised assessment, preserves
independent stocks, checks source freshness and confirms unchanged daily-input
identities. It refuses accidental repeat apply after writing its retained report.

Private arithmetic checks cover reset ordering, new-period income, independent
anchors and unknown trade movements. Twelve focused native history/API tests
passed in an owned disposable database. No whole-project regression was run.

| Strategy | New stock revisions | Superseded provisional stocks | Maintained history rows | Known closings | Unassessed closings |
| --- | ---: | ---: | ---: | ---: | ---: |
| FCAGF | 129 | 86 | 462 | 359 | 103 |
| FCPGF | 1,373 | 462 | 3,504 | 2,367 | 1,137 |

FCAGF also retains 15 unchanged provisional assessments. The FCPGF source
population now includes one additional manually supplied daily input beyond the
1,830 CSV bond/date inputs; all 1,831 daily-input identities were preserved.
All latest maintained rows reread with CURRENT source signatures, and all twelve
independent closing assessments retained their exact amounts.

Browser acceptance for **T 2 1/4 08/15/27** showed 292 stored dates from 2 January
to 20 October, including 201 assessed closings and 91 unassessed days. Its first
closing is exactly USD 3,668.48; its preserved 20 October closing is USD 111,888.59.
The full-range chart and 25-row paginated table display the earlier dates without
a stale-source banner; no browser warnings/errors were observed. Missing calendar
days remain unassessed, including weekends covered by a later source flow.

The [balance explorer](accrued-balance-explorer-20261103.md) reads these maintained
records; extending its range alone never performs this data-maintenance operation.
