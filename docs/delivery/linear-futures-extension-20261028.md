# Linear crypto futures booking and daily P&L

**Status:** Implemented; verification and local activation recorded below.  
**Reviewed:** 28 October 2026.  
**Capabilities:** F16, F37, F39.  
**Scope:** Existing index futures plus dated linear crypto futures, CASH or PHYSICAL, using approved exact-expiry listings and supplied contract marks.

## Behavior and reusable economics

The existing family → dated contract → venue listing → booking flow now accepts
the modelled linear crypto families. UNDERLYING_UNIT means a quote per underlying
unit and a sourced contract size equal to the monetary multiplier. Booked quantity
counts whole contracts. INDEX_POINTS/CASH remains unchanged.

```
native daily variation = (Q1×P1 − Q0×P0 − Σ(signed execution quantity×price)) × M/D
reporting daily P&L = native variation × that economic day's closing FX
```

Apply the frozen multiplier once, not again through contract size or listing
metadata. Two unchanged contracts of 5 BTC, prices 100,000→101,000 USD/BTC,
produce 10,000 USD; at 0.8 GBP/USD the result is 8,000 GBP. The same bridge applies
before physical delivery. New, partial/full closing, short and cross-through-zero
trades retain their actual execution contribution. Zero boundaries need no mark;
supplied zero marks are valid. Negative prices still require explicit frozen
permission. Foreign multi-day requests retain daily variation/FX aggregation.

Futures variation remains an explicit batch-reconciliation term. Gross notional
is not an asset value, and contract MTM remains unassessed. No margin/cash or
underlying position is generated; the independent cash-balance FX path is unchanged.

## Booking, history and source controls

- [Shared capability](../../security_master_schema/future_economics.py) validates
  supported coherent linear conventions below HTTP. The reference adapter checks
  crypto against active governed crypto/currency roles, instead of index_terms.
- Family economics, underlying, contract currency, delivery windows, approved
  convention and canonical dates must agree at readiness and execution. Currency,
  reference and identity records remain locked/revalidated for posting. The common
  currency phase locks quote and asset roles in UUID order to avoid reversed-pair
  lock ordering; a changed role is refused before acquiring a late currency lock.
- Original BOOKED JSON and its context hash are preserved. Historical index
  recovery is unchanged. New asset-unit bookings pass through the same exact
  original-version recovery; changed current family parameters cannot reprice them.
- Selected native RAW CLOSE/official close/SETTLEMENT series bind the dated
  contract, actual price basis, divisor and trade-price currency. Spot token,
  continuous-futures, wrong expiry/basis/currency and unlicensed data are not
  substitutes. No currency peg or inferred conversion is introduced.
- The contract's governed sealed calendar/cut applies. Weekend trading, settlement
  and economic dates follow that contract/policy, not a blanket calendar inferred
  from the spot asset. Information-cutoff and freshness checks remain mandatory.
- Tenant/strategy authority, idempotency, review, amendments, current source rights
  and stale-input publication revalidation are reused.

## Trading and delivery boundary

No new execution is accepted after the approved last-trading instant. A contract
can still need a final mark after trading has stopped. The supported final
settlement boundary and physical delivery window remain explicit. Open exposure
after final settlement requires recorded Ops handling; dates alone never erase
the position or invent a zero final price.

An ordinary closing execution before the trading cutoff preserves same-day P&L.
Actual delivery/assignment and any resulting cash or underlying receipt remain
separate work. This extension does not provide a futures delivery-closure booking
after last trading, a delivery notification dashboard or automated expiry posting.

## Ops UI

Creation/review/booking text now distinguishes supported linear booking from
unimplemented delivery processing. The convention editor preserves the approved
actual price basis, size, currency, settlement method and delivery dates; it no
longer rebuilds crypto terms as INDEX_POINTS. Source/effective-version details
can be proposed through the existing approval workflow. Contract economics and
existing canonical dates are read-only.

The editor has a scoped responsive layout and normal-sized checkboxes. The P&L
inspector retains the original convention alongside exact contracts, prices,
multiplier/divisor, native variation, reporting FX and source dates. It displays
cash/physical settlement and delivery dates without implying a cash/token posting.
No browser pricer is added.

## Verification and activation

Lightweight RED→GREEN cases preceded changes, including index-only refusal,
asset-unit execution amount, native booking and amendment refusal, retained
convention display and quote/asset lock ordering. All financial test data uses
owned disposable databases; browser acceptance uses isolated fixture servers.

Final checks: **80** offline numerical/frozen/rule/architecture/neutrality tests,
**70** disposable database tests, **48** frontend tests and TypeScript passed.
**Four** new isolated Edge journeys passed; an existing index inspection journey
also passed. The physical inspector screenshot was inspected. A separate corrected
calendar/readiness run passed **four** cases. These runs overlap. No full Python
suite or independent real-portfolio reconciliation was performed.

Operating schema **20261028_102** was verified read-only, API **8001** reloaded,
and its health endpoint returned OK. No new schema is needed. The frontend was
not started/restarted; browser checks used isolated fixture servers. Details,
intermediate fixture failures and scope rulings are in the
[execution ledger](../superpowers/plans/2026-10-28-linear-futures-extension.md).
No operating trades, source rights, permissions, cash
balances or valuations are created or changed by this work. No full Python suite,
commit or push is part of this delivery.

## Remaining scope and trade-offs

The family model currently covers INDEX and CRYPTOASSET. Commodity, currency-pair
and interest-rate reference/quotation models need their own extensions; they must
not be relabelled as an index to enter this adapter. Inverse/quanto/perpetual and
daily financing-adjustment products need appropriate economics. No margin
accounting, delivery/assignment automation, clearing-statement rounding emulation
or new crypto futures monetary-measure preview is provided. Existing index
monetary exposure remains supported; contract MTM is unavailable without its own
clearing evidence. Real broker/custodian reconciliation and scale acceptance
remain separate from synthetic workflow tests.

Sources rechecked 28 October: [CME variation guidance, 11 June 2015](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf),
[current crypto FAQ](https://www.cmegroup.com/articles/faqs/frequently-asked-questions-cryptocurrency-futures.html),
[physical-delivery explanation](https://www.cmegroup.com/education/courses/introduction-to-agriculture/grains-oilseeds/understanding-the-grain-delivery-process).
Special/inverse/financing and clearing-rounding conventions are not implicitly
covered by the common exact economic bridge. See the
[design](../superpowers/specs/2026-10-28-linear-futures-extension-design.md)
for source applicability and project decisions.

Implementation: [booking](../../apps/reference_api/product_booking.py),
[frozen normalization](../../security_master_schema/future_valuation.py),
[historical adapter](../../positions/future.py),
[variation and input context](../../valuation/futures_pnl.py).
Evidence: [pure cases](../../tests/test_linear_future_economics.py),
[native booking](../../tests/test_linear_futures_api.py),
[calculation/review](../../tests/test_linear_futures_pnl_integration.py),
[browser journeys](../../apps/ops-console/browser-tests/linear-futures.spec.ts).
