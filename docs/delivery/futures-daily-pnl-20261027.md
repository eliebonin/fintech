# Futures daily economic P&L

**Status:** Implemented for the existing cash-settled index booking slice  
**Content type:** Delivery/reference  
**Owner:** Valuation and operations engineering  
**Last reviewed:** 2026-10-27

28 October follow-up: [linear crypto cash/physical booking and P&L extension](linear-futures-extension-20261028.md). That later delivery expands native booking/P&L. The scope and creation-only restrictions below describe the original 27 October increment; index-only monetary-preview limits remain current.

## Scope and economics

The live valuation engine now accepts the linear cash-settled INDEX_POINTS
futures already supported by booking. Physical/crypto futures remain creation-only.
It uses supplied governed exact-contract prices, not an underlying index price
or continuous-futures history. No model price, margin cash posting, automatic
expiry closure or contract-MTM value is generated.

For one economic day, signed opening/closing contracts are Q0/Q1, compatible
contract prices P0/P1, period executions qi/pi, monetary multiplier M and quote
divisor D:

```
native variation = (Q1 × P1 − Q0 × P0 − sum(qi × pi)) × M / D
reporting P&L = native variation × economic-day closing FX
```

The multiplier comes from the original booked contract convention and applies
once. Listing multipliers do not multiply it again. Shorts and decreases retain
their signs. New trades use execution prices; full closes and same-period round
trips retain their P&L on T. A zero boundary requires no price for that boundary.
Zero prices are supported; negative prices require the frozen explicit permission.

Example: 2 contracts, multiplier 50, previous price 6,000, current price 6,010
give 1,000 in the price currency. At closing FX 0.8 GBP per price-currency unit,
the P&L is 800 GBP. An unchanged futures price produces no futures P&L merely
because FX moved. Actual opening margin cash has its own existing cash-FX path.

Foreign multi-day calculations sum each day's variation at that day's closing
FX, rather than applying one final FX to every day's gain. This is the documented
economic attribution convention, not transaction-time margin accounting.

## Reconciliation and retained evidence

Futures gross market notional is neither an investment asset value nor a proven
contract MTM. Its per-position `openingValue`, `closingValue` and `executionValue`
are therefore retained as null, with `PRICE_VARIATION_NOT_CONTRACT_MTM` basis.
Futures P&L contributes to PRICE; its separate position-FX and cross components
are zero under the daily-variation convention.

The batch bridge is extended explicitly:

```
market P&L = non-futures closing value − opening value − execution value
             + futuresVariationPnl + retained storage-rounding adjustment
```

`investmentValueScope` identifies the exclusion of futures notional/unassessed
MTM. No synthetic execution/cash amount is invented to force the old asset bridge
to fit. Publication verifies futures variation against the immutable selected
line evidence before accepting that batch term. Existing typed result ownership,
component reconciliation, source-display permissions, independent review,
amendments and source-reassessment controls remain applicable.

Original booking snapshots already contain convention, execution economics and
context fingerprints. `positions/future.py` uniquely recovers historical version
IDs whose original context hash matches; it does not substitute today's multiplier
or rewrite trades. A request-scoped identity cache avoids repeating the lookup for
the same context; every trade still validates quantity, price, currency, venue,
amount and frozen trading dates. Ambiguous/changed evidence fails closed.

Policy-selected CLOSE/OFFICIAL_CLOSE/SETTLEMENT inputs must have native RAW price
semantics, eligible rights, sealed calendar/freshness proof and matching
CONTRACT_INSTRUMENT_ID, FUTURE_PRICE_BASIS and QUOTE_FACTOR dimensions. Nonzero
boundaries after final settlement require recorded Ops closure; no automatic
zero is assumed. An opening boundary does not validate a later trade's convention
before that convention becomes effective.

## Ops display and schema

The ordinary valuation results include futures rows and product classification.
Inspection leads with signed contracts, prices/actual dates, multiplier, divisor,
native variation, closing FX/actual date, reporting P&L and linked execution
prices. It explains that margin cash and contract MTM are separate. Displays read
retained values and perform no browser financial calculation.

The current attribution/evidence schema supports this extension: **no migration**
or operating data rewrite is needed. Existing monetary-preview market value stays
unavailable without settlement/clearing evidence; enabling P&L does not turn
notional into a NAV asset. Request identity versions the new execution contract.

## Verification and activation

Pure numerical tests were first observed failing on unsupported FUTURE units,
then passed after implementation. Additional RED→GREEN cases cover cached-identity
venue validation, later-effective conventions and calculation-level explanations.
Disposable integration covers real approved old-format bookings, exact-contract
selection, wrong expiry/divisor/basis rejection, staging, current evidence-display
checks and independent publication alongside adjacent existing-product tests.

Focused frontend tests cover the manual-check view and existing position/coverage
views. Isolated browser acceptance checks the normal result inspector, actual
input dates, linked trade, dismiss behavior and mobile overflow. TypeScript and
OpenAPI parity checks are included. Final counts are recorded in the linked
execution ledger; no full Python suite was run for this bounded extension.

Main focused backend/database run: **60 passed**. Final futures integration
including controlled fee amendment and independent publication: **5 passed**.
Final offline numerical/frozen/adjacent checks: **85 passed**. Focused frontend:
**35 passed**. Isolated browser: **3 passed**, with a final actual-date futures
case rerun **1 passed**. TypeScript/OpenAPI parity passed. These runs overlap;
their counts are not presented as unique test totals or full-suite coverage.

No operating trades, prices, rights, balances or published valuations were changed.
Docker/PostgreSQL were started for disposable verification. No operating app
restart/valuation or Git commit/push is claimed by this delivery.

## Source and implementation map

[CME money-calculation guidance, updated 11 June 2015](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf),
reviewed 27 October 2026, describes opening-position and execution-to-settlement
variation. Its clearing-specific rounding rules are distinct from this project's
exact economic attribution and explicit 12-place storage. This is not a claim of
broker statement reconciliation to currency minor units.

- [Plan/verification ledger](../superpowers/plans/2026-10-27-futures-pnl.md).
- [Frozen economics](../../security_master_schema/future_valuation.py),
  [historical adapter](../../positions/future.py), [numerical bridge](../../valuation/futures_pnl.py).
- [Service](../../valuation/service.py), [position storage](../../valuation/position_storage.py),
  [publication](../../valuation/storage.py), [rules](../../valuation/decisions.py).
- [Pure bridge tests](../../tests/test_futures_pnl.py), [frozen tests](../../tests/test_future_frozen_valuation.py),
  [database integration](../../tests/test_futures_pnl_integration.py).
- [Inspector](../../apps/ops-console/src/features/valuation/futures-pnl-inspection.tsx),
  [component tests](../../apps/ops-console/src/features/valuation/futures-pnl-inspection.test.tsx),
  [browser acceptance](../../apps/ops-console/browser-tests/futures-pnl.spec.ts).
