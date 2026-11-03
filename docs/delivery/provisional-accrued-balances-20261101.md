# Provisional accrued balances for FCAGF and FCPGF

**Date:** 1 November 2026  
**Status:** Local data population completed; provisional, not independently reconciled  
**Scope:** First tenant, FCAGF/FCPGF only; no application/schema change.

Subsequent owner instruction: [expand the maintained balance history](expanded-accrued-balance-history-20261103.md)
using the longer source window, provisional zero opening and schedule-based
stock resets while preserving reviewed closing assessments. The original
operation described below remains retained historical evidence.

## Authority and convention

The owner instructed: “Do work for now assuming balances were 0.” A sourced
opening stock was unavailable. The operation therefore retains an explicitly
provisional zero closing stock on **20 August 2026**, followed by closing-stock
assessments on supplied accrued-flow dates through **20 October 2026**.

The original source process treats these amounts as booked interest flows between
reporting dates, rather than requiring an observation on every calendar day.
Each assessed closing stock sums supplied posted flows from the authorised zero
baseline, adds known frozen bought/sold accrued and subtracts confirmed receipts.
The original daily-interest records are unchanged. No weekend daily amount,
unknown trade accrual, coupon receipt or missing source stock was fabricated.

Assessment source references and reasons explicitly identify the zero assumption,
source hash and private operation report. These are local reconciliation inputs,
not custodian-certified balances. Subsequent source corrections require reviewing
and revising these provisional assessments; an ordinary history refresh does not
recalculate an independently supplied stock assessment.

## Retained population

| Strategy | Bonds with supplied interest | Original daily inputs | Retained stock inputs | Materialized history rows |
| --- | ---: | ---: | ---: | ---: |
| FCAGF | 3 | 99 | 102 | 183 |
| FCPGF | 11 | 462 | 473 | 732 |

The **575 stock inputs** comprise 14 assumed opening zeros and 561 supplied-date
closing assessments. Two explicit native history builds produced **915 typed
history rows**: 600 known closing stocks and 315 unassessed closings. This is not
915 independent external observations. Missing calendar-day coverage stays
visible; FCPGF's Bekarys Series GBP 2025 has no supplied daily interest and remains
unassessed. No additional zero was assumed for that unsupported bond.

All 14 supported bond/strategy combinations have known closing balances on
**19 and 20 October**, with current source signatures. Examples for FCPGF:

| Bond | Currency | Closing 19 October | Closing 20 October |
| --- | --- | ---: | ---: |
| T 2 1/4 08/15/27 | USD | 110,054.35 | 111,888.59 |
| TII 0 1/2 01/15/28 | USD | 27,829.10 | 28,293.61 |
| TII 0 3/8 01/15/27 | USD | 11,338.54 | 11,527.80 |
| T 2 11/15/26 | USD | 113,152.17 | 115,038.04 |

This table rounds for reading; the database and retained operation report preserve
the exact decimal strings, including source precision tails.

## Execution and verification

An ignored one-off script at `logs/operations/populate_balances_20261101.py` called
the existing scoped `record_balance_input` and `refresh_history` domain commands
under the normal runtime role. Each strategy used an atomic transaction, existing
input-revision serialization, per-input audit and an additional operation audit.
The retained JSON report holds original source IDs/revisions, frozen movement
lineage, source hash, request identities, input IDs and build IDs. It contains no
credentials. The script is excluded from application packages, migrations,
startup, product tests and seeded datasets; it refuses accidental repeat execution
when its retained operation report already exists.

Verification compared every supplied-date materialized closing against the exact
source-flow calculation, confirmed unchanged daily input populations, reread both
strategies' 19–20 October history and checked source freshness. This was a data
operation using previously tested product commands; no full test suite was run.
No trades, market prices, permissions or published valuation amounts were changed.

## Remaining qualifications

No coupon-payment confirmations currently exist for these two strategies.
Scheduled dates alone were not treated as receipts or forced resets; receivables
are not erased. Correct opening stocks and actual receipt evidence are needed
before claiming historical financial reconciliation. The zero assumption can
materially change accrued-stock FX compared with production.

Rerun/stage valuation to consume the new maintained history; prior staged evidence
may require recalculation, while published amounts remain immutable. Inspect the
data in `/valuation/interest`, selecting the strategy and 19–20 October window.
See [maintained workflow](maintained-accrued-balances-20261031.md) and
[economic/storage rules](../architecture/market-data-and-valuation/accrued-balance-fx.md).

## Requested FCPGF rerun

The owner subsequently requested the 20 October FCPGF rerun. The authenticated
native API reused the previous v3 imported-EoD/prior-day-fund-NAV policy, opening
19 October, closing 20 October and GBP reporting currency, with a current source
information cutoff and retained predecessor/recalculation reason.

- Attempt `01a1977c-0306-70cf-9cc4-17af5fd832ef` completed; replacement batch
  `01a1977d-4e26-7052-b4ae-8c8b1e8ce404` is **STAGED**, with 130 attributions.
- Calculated subtotal: GBP **55,819.337421526810**, versus prior subtotal
  **56,849.478719743611**. The exact difference, **−1,030.141298216801**, equals
  the newly included accrued-stock FX component. Market P&L and cash FX P&L
  remained unchanged. This uses the provisional zero-opening assessments above.
- Accrued-stock coverage now includes 11 supplied bonds; Bekarys remains missing.
  Source health is CURRENT, meaning retained inputs are fresh, not that the
  portfolio is economically complete or independently reconciled.
- The same four required-input gaps remain: two forward opening marks for
  19 October and SGD cash conversion for 19/20 October. The result remains a
  partial calculated subtotal; normal publication remains blocked pending
  eligible marks or independently reviewed exact-input overrides and recalculation.
  Existing cash-snapshot and optional-interest warnings also remain.

The one-off script/result/verification are retained under
`logs/operations/rerun_fcpgf_20261020_20261101.*` and excluded from the product.
Every required gap identity matched its predecessor. No publication was requested
or performed; no source data, permissions or calculation code was changed.
