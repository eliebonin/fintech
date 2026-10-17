# Deliverable FX-forward position measures

**Status:** Implemented bounded preview; API restarted/healthy, browser and financial acceptance separate  
**Content type:** Delivery reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-15

## Economics and interface

Strategy → Measures now supports deliverable FX forwards. It is a read-only stock
preview, not a new P&L method, published valuation, risk weight or cash booking.

- Reference notional is the signed outstanding **base-currency** amount.
- Exposure has two **undiscounted contractual currency legs**: base `N` and quote
  `−N × K`, where K is the frozen agreed quote-per-base rate, not today's forward.
- Each leg has its own native currency and independently selected strategy-FX
  equivalent. They are not netted into a headline exposure number.
- Market value remains unavailable: contract rates alone do not provide a
  supported discounted MTM. No discount factor of one is assumed.

Buying EUR 1,000,000 at 1.10 USD/EUR therefore records +EUR 1,000,000 and
−USD 1,100,000. In a GBP strategy each amount needs its own eligible conversion.
These are amounts to receive/deliver, **not** cash balances, discounted currency
exposure or delta. Sell reverses the signs.

The additive `economicExposure` representation is `CONTRACTUAL_CURRENCY_LEGS`,
status `MULTI_CURRENCY`, with null scalar amounts and a `legs` array. Each BASE/
QUOTE leg has local amount/currency, strategy amount/currency and AVAILABLE or
LOCAL_ONLY status. Existing scalar products retain their original response shape.
The component renders legs before testing for a null scalar; no financial math
or precision-losing Number conversion is performed in presentation code.

## Safety, lifecycle and evidence

[Forward adapter](../../valuation/forward_measures.py), `contractual_legs`, reloads
only the projected bucket's retained trades/BOOKED events at the frozen information
cutoff and within strategy scope. It reuses
[`normalize_booking`](../../positions/fx_forward.py), including the existing exact-
fingerprint legacy path; no second legacy policy was introduced. Currency direction,
amounts, units, agreed rate and maturity evidence must agree. Decimal scale alone
does not make numerically equal rates different agreements. Query ordering keeps
retained booking evidence deterministic.

Multiple compatible fills and signed partial closes contribute once. Cancelled/
superseded records are removed by shared reconstruction. A retained maturity close
extinguishes obligations using the contractual rate for these legs, **not** the
closing execution rate used separately by P&L. It creates no cash movements.
Unclosed past-maturity obligations remain visible with an Ops closure warning.

Mixed frozen agreements within one canonical position are unavailable, not netted
at a sampled rate. The Measures route checks even base-flat forward buckets before
filtering/pagination: incompatible agreements cannot disappear as supposedly closed
when quote obligations may remain. Valid closure of both legs is filtered normally.
This is a preview guard, not a redesign of generic quantity-only holdings or an
automatic split of mixed agreements into new instruments/lots.

Reporting FX retains existing governed direct/explicitly permitted inverse rules,
date/calendar/freshness and use/display rights. Missing conversion leaves that leg's
local amount available without an invented rate. Display denial remains a permission
failure, not a downgraded missing-data row. Evidence includes frozen conventions,
booking hashes/IDs, FX selections, projection hash and readable limitations.

## Verification and activation

Focused pure, disposable-database and UI checks are recorded in the
[cross-measure review](quality-reviews/2026-10-15-position-measures-review.md#verification).
The integration scenarios cover signs, separate native/reporting currencies, two
independent conversions into a third currency, missing FX, fills/cancellation,
mixed agreements, base-flat residual safety, closure/reopening and overdue exposure.
No migration, operating booking, source grant or policy change is required/performed.
Browser walkthrough and independent financial/provider reconciliation are not implied.
Local API restarted after the checks; `/health` returned HTTP 200 and startup
completed without errors. This verifies activation, not an operating forward's
financial reconciliation. Parent process 68676, server child 37636; retained logs
use the local temp prefix `platform-forward-measures-20261015`.

## Deliberate limits

NDFs, FX swaps, automatic currency delivery, discount curves, sourced monetary MTM,
Greek sensitivities, triangulation, weights and accounting remain excluded. Existing
[rate-difference P&L](fx-forward-rate-pnl-20261014.md) is unchanged. Compatible proof
for true MTM is a separate follow-up, not an excuse to relabel its undiscounted value.

Research and the review of all three measures are retained in the
[cross-measure report](quality-reviews/2026-10-15-position-measures-review.md).
