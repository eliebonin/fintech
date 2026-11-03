# Accrued-interest balance FX — best-practice review

**Reviewed:** 26 October 2026  
**Status:** Research and recommendation; no calculation or schema change

The user wants FX P&L on the accumulated interest balance at T−1 as well as
today's newly earned interest. Keep the existing EoD attribution convention and
extend balance reconstruction and coverage, rather than adding another calculator.

## Source-backed principles and applicability

- [GIPS Handbook for Firms, November 2020, provision 2.A.10](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/)
  requires accrued fixed-income income in beginning/ending performance values and
  warns against including income again when already embedded in the price. This
  is a requirement for a GIPS compliance claim, not a claim that our partial alpha
  is compliant or must reject every incomplete run.
- [NZ IAS 21, current January 2025 edition, paragraphs 23 and 28](https://standards.xrb.govt.nz/standards-navigator/nz-ias-21/)
  supports closing-rate retranslation of monetary balances and recognition of
  exchange differences, subject to its accounting scope/exceptions. This is
  corroboration for translating a foreign-currency interest receivable. It does
  not prescribe our daily P&L attribution categories or make this an accounting
  implementation. The listed January 2027 version is not yet mandatory.
- [UK DMO gilt conventions](https://www.dmo.gov.uk/responsibilities/gilt-market/about-gilts/)
  show that purchases/sales exchange accrued interest and that ex-dividend accrued
  interest can be negative. Settlement and entitlement matter. These are gilt
  examples, not a universal entitlement rule for every bond.
- [UK DMO payment FAQ](https://www.dmo.gov.uk/help/faqs)
  distinguishes contractual coupon dates from payments shifted by weekends or
  bank holidays. Therefore actual cash-payment dates alone are unsuitable reset
  anchors for every instrument's accrued balance.

All sources above were searched, opened and relevant passages read. The IFRS
Foundation's direct 2024 PDF redirected to subscription access; the current public
standard-setter equivalent above supplied the readable text. An oversized ICMA
book could not be fetched and is not used as verified evidence.

## Recommended daily convention

Let A0/A1 be the position-level local accrued balances at T−1/T, I the daily earned
interest, M the signed non-income balance movements, and f0/f1 the policy-selected
strategy-currency amount per unit of accrued-interest currency.

```text
A1 = A0 + I + M
Daily interest P&L = I × f1
Accrued-interest FX P&L = A0 × (f1 − f0)
```

Movement amounts use closing FX under the existing EoD convention. Consequently
`A1*f1 − A0*f0 − M*f1` equals the two P&L components above. No additional interest/FX
interaction is added: conversion of I at f1 already includes it. These exact
attribution choices are project conventions, not uniquely mandated by IAS 21/GIPS.

For opening USD 1,000, daily earned USD 20 and GBP/USD conversion .75→.76,
interest contributes GBP 15.20 and accrued-balance FX GBP 10.00. The accumulated
USD 1,020 is not itself new daily income. Position-level amounts are not multiplied
by nominal quantity again.

## Reconstruction and boundaries

1. Start from a verified balance anchor, which may be zero at a supported coupon
   boundary, or a supplied opening balance. Sum eligible dated accruals and signed
   movements after that anchor. Reconcile any later supplied balance.
2. Include acquisition/disposal accrued amounts and their proper effective dates.
   These are balance transfers, not newly earned interest. Do not blindly apply a
   settlement-accrual amount on execution day or infer entitlement from current
   holdings alone.
3. Coupon releases/transfers reduce the accrued stock without creating new income.
   An unpaid coupon receivable can remain FX-exposed while a new coupon period has
   started, including after disposal. Do not erase that exposure merely because a
   coupon is scheduled or the security position is flat. Broader receivable state
   and automatic entitlement remain separate unimplemented boundaries.
4. Do not infer a complete opening balance from incomplete daily history. Reuse
   exact supplied anchors where possible. Missing reconstruction should disclose
   **Accrued-interest FX not assessed/partial**, not confirmed zero or complete
   coverage, while retaining the agreed optional-input publication behaviour.
5. Keep clean-price FX, accrued-interest FX and cash FX distinct. When dirty marks
   are supported, reconcile their embedded accrued interest rather than adding the
   same income/FX twice. Freeze selected rates, input revisions and reconstruction
   evidence; later corrections trigger the existing reassessment workflow.

## Current implementation versus recommendation

| Area | Current state | Remaining |
| --- | --- | --- |
| Detailed arithmetic | `accrual_amounts` validates the stock bridge and computes `receivableFx` | Reuse, not replace |
| Daily-only inputs | Earned amount converted using selected daily FX | No automatic accumulated balance reconstruction |
| Attribution | `attach_accruals` adds earnings to ACCRUAL and receivable FX to CARRY once per canonical bond | Preserve signed ownership and avoid duplicate listing allocations |
| Coupon schedule/confirmation | Retained schedule/payment evidence; confirmation creates no income or automatic balance movement | Explicit linking/reconciliation before automatic stock release |
| UI category | Coverage already has **Accrued-interest FX** | Dedicated balance-FX coverage; absent CARRY currently may read No recorded entries despite unassessed balances |

Code inspected: [accruals](../../valuation/accruals.py),
[arithmetic/ownership tests](../../tests/test_valuation_accruals.py),
[source coverage](../../apps/reference_api/valuation_source_coverage.py).
Existing scope: [coupon implementation](../delivery/bond-coupons-20261015.md),
[typed interest](../delivery/typed-daily-interest-20261014.md),
[methodology](../architecture/market-data-and-valuation/valuation-methodology.md).
This is a source-to-code review, not a new regression run or financial sign-off.

## Three-dataset proposal — 27 October 2026

The proposed economic separation is recommended: (1) daily earned interest,
(2) contractual coupon/principal schedule, and (3) accumulated interest balances.
It is sufficient for the scoped daily-interest/balance-FX calculation when linked
to existing trade movements, actual payment confirmations and policy-selected FX.
Standards support the economic principles; they do not prescribe three tables.
The GIPS, current public NZ IAS 21 and DMO sources above were reopened for this check.

- Daily earnings represent income earned for the actual exposure on that date.
  Bought/sold accrued interest changes the stock, not that daily income. A smooth
  series means avoiding spurious payment/trade spikes; genuine exposure changes
  may change the daily amount. Position-level amounts are not multiplied again.
- The instrument-level schedule retains accrual periods, coupon/principal due
  dates, currency and amounts/rates/formulas as available, with sourced versions
  and applicable entitlement dates. Expected payment is distinct from receipt.
- Tenant/strategy/bond/currency/date balances roll forward from confirmed anchors
  using daily earnings and dated non-income movements. Actual coupon settlement
  reduces the amount settled, not automatically the entire balance: USD 1,020
  including USD 20 of new-period accrual becomes USD 20 after a USD 1,000 receipt.
  Unpaid coupons remain owed; payment corrections/reversals retain their effects.
- Derive balances where evidence is complete; accept supplied custodian balances
  as anchors/reconciliation. Retain source revisions and completeness. Missing
  evidence stays unassessed rather than zero, under existing optional-input rules.

Our existing coupon payment records can provide actual-settlement evidence, and
frozen trade evidence provides bought/sold accrued amounts; date/eligibility must
still agree before reuse. No fourth user-maintained upload stream or full general
ledger is implied. Local facts remain authoritative; reporting-currency values
are retained with the valuation's selected FX evidence. No application change was
made for this proposal review.

## Full contractual bond schedule — 27 October 2026

Recommended direction: evolve the existing retained coupon schedule into one
versioned **bond cashflow schedule** covering coupons and principal. Retain a
schedule header and typed payment rows (COUPON or PRINCIPAL). Final coupon and
principal remain separate rows even when their dates coincide. Principal rows
can represent full redemption or contractual partial repayments; broader lifecycle
posting support is not implied by the data shape.

Amounts belong to the instrument (for example per 100 nominal), with the basis
explicit; strategy entitlement is resolved separately. Preserve currency, due
date, contractual amounts or formulas, coupon accrual periods and applicable
record/ex-coupon dates, source and schedule revision. Unknown future amounts must
remain identified as unknown/projected rather than fabricated. One complete
contractual schedule supports the Ops calendar, future DCF inputs and lifecycle
preparation without making an expected payment an actual receipt or new income.

This is an application modelling recommendation, not a universal single-table
standard. [OpenGamma Strata's resolved fixed-coupon bond](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/bond/ResolvedFixedCouponBond.html),
opened/read on 27 October, represents both periodic coupons and nominal payment
within the bond model, using separate structures. It corroborates completeness
and typed distinction, not our particular database arrangement.

Current code remains a coupon-only header/period model plus actual coupon
confirmations; principal closure is handled separately by
[bond redemption](../../lifecycle/bond_redemption.py). Any implementation must
preserve existing schedule/period/payment references and financial evidence.
No schema migration or application behaviour was changed by this recommendation.

Implementation follow-up, 27 October: the subsequently approved
[full bond cashflow schedule](../architecture/trading-and-operations/bond-cashflow-schedules.md)
now extends this former coupon-only model. The research-time statement above is
historical. The subsequent [accrued-stock/FX implementation](../architecture/market-data-and-valuation/accrued-balance-fx.md)
adds source-based derivation with explicit unknowns and retained receivables;
see its delivery record for verified scope and limitations.
