# Non-ETF ETP and spot-crypto P&L — 28 October 2026

**Status:** Implemented and locally activated; focused acceptance passed.  
**Capabilities:** F12, F36, F37, F38, F39.  
**Order:** Exchange-traded wrappers first, then spot digital assets.

## Delivered

The existing security value/execution/FX bridge now accepts ETC, ETN, ETV, ETI,
EXCHANGE_TRADED_VEHICLE, EXCHANGE_TRADED_CERTIFICATE and spot DIGITAL_ASSET.
Product identity is preserved; these products are not relabelled as equities or
ETFs to bypass capability checks. This is supplied-price economic attribution,
not an underlying payoff model, fund NAV or accounting service.

For each compatible position and daily bridge:

```
boundary value = signed units × frozen listing multiplier / quote divisor
                 × the security/token's own quoted price × reporting FX

price/FX P&L = closing value − opening value − signed period execution value
```

The existing price/FX/cross decomposition, trade-date recognition, original
execution prices, foreign daily aggregation and exact Decimal calculations are
reused. New, long, short, partial/full closing and cross-through-zero trades keep
their actual economics. A zero closing position needs no invented terminal mark.

For wrappers, the quote is for the whole listed security. Do not multiply the
commodity entitlement, reference index return, embedded leverage or fees again.
An exchange quote and an issuer's indicative value are distinct observations;
the policy must select the intended licensed source/price family. No hidden
underlying substitution, clean/dirty relabelling or fee model is introduced.
Percentage/clean-price debt conventions belong to the separately governed
bond/structured-note path, not an undocumented reinterpretation of cash units.

## Product and unit evidence

[Shared classification](../../security_master_schema/cash_products.py) defines
the cash-product boundary below HTTP adapters. A generic ETP requires one
effective concrete terms version (ETF/ETC/ETN/ETV/ETI). It is not automatically an
ETF. New generic bookings pin the term ID and product kind. Original concrete
definitions retain their type; legacy generic records need unambiguous effective
history. Conflicting/missing classification fails explicitly.

Canonical generic ETP identity remains ETP for instrument, policy and licensing
scope. Concrete terms select the economic adapter; they do not silently grant
subtype market-data rights or alter the security master.

New wrapper and spot bookings use UNITS. Older generic cash tickets used SHARES
for these same counts. Position/holdings adapters normalize that label to UNITS
without rescaling quantity, price or factors, retaining the original ledger and
normalization evidence. A new sale therefore offsets an old purchase. The same
unit correction preserves the existing fund NAV path; native fund bookings need
UNITS rather than the old generic cash ticket's SHARES default. Equity/ETF
bookings retain their existing labels and monetary conventions.

Quantity-only strategy views and financial reconstruction share generic ETP
classification. Existing wrapper monetary previews retain their formulas under
the real subtype. Crypto monetary-measure previews remain outside this slice.

Reviewed same-security ratios extend to wrapper units, with the existing exact
source/review/order/fraction safeguards. They do not authorize token forks,
migrations, rebases or automatic new-security entitlements.

## Spot crypto and market data

- Fractional token quantities retain the platform's existing decimal precision.
  Each exchange listing stays a separate subject; no cross-venue netting or
  automatic price borrowing occurs.
- Convert the **trade quote currency** to reporting currency. The asset's native
  currency role is not another conversion leg. BTC quoted in USD uses USD→GBP,
  not an extra BTC→USD multiplication.
- USDC/USDT or other stablecoin quotation currencies require actual eligible
  conversion evidence when reporting differs. No USD peg is assumed. A supplied
  stablecoin asset price move is genuine price P&L under the same bridge.
- Use native RAW CLOSE/official-designated close or explicitly selected MARK
  prices at the configured governed cut. Native RAW is compatible with an
  AS_TRADED policy; stock-split conversion is not token-unit evidence.
- The sealed pricing calendar must explicitly assess each requested crypto
  price boundary as open. A closed Saturday cannot silently become Friday's
  unchanged price. Weekday-only requests still work with covered weekdays;
  weekend requests need continuous calendar coverage. Explicit lag/prior-price
  and bounded freshness remain supported on that calendar.
- Confirmed zero marks remain zero. The common AS_TRADED normalizer now permits
  a supplied zero while rejecting negative/nonfinite prices, invalid ratios and
  positive values that would silently underflow to zero. Source observations
  remain unchanged.

No provider acquisition, automatic source grants, reference-calendar seeding,
staking/fork income, network balances, perpetuals, borrowing or margin posting
is added. Missing required prices/FX still block calculation. Crypto prices
are not a substitute for FX-rate measurement semantics.

## Income, review and UI

Existing economic-flow APIs allow explicit wrapper COUPON income and later
PAYMENT_ONLY records, with frozen type/hash evidence. The bond coupon
payment-only safeguard remains. Distributions/costs are recorded separately;
no distribution schedule, entitlement or payment is inferred from a quote.

The existing stage → amendment → governed publication workflow is reused,
including current source permissions, strategy scopes and independent review.
The inspector explains wrapper whole-price versus underlying exposure and
crypto listing/quote/peg boundaries beside the frozen manual calculation.
Applied rules retain product and historical unit-label decisions. The generic
ETP frontend filter remains advisory; backend readiness requires valid terms.

## Verification and activation

- **117** focused offline numerical, normalization, architecture and repository-
  neutrality checks passed. OpenAPI export check passed.
- **31** native ETP/crypto integration cases passed in the final disposable
  database run, including real bookings, old/new unit-label netting, partial/full
  and short closures, source rights, tenant isolation, FX, review and publication.
- Adjacent disposable regression runs passed **62**, **31** and **10** cases
  covering price basis, booking integrity, flows, notes, AMC measures, holdings
  and selected boundary checks. These runs overlap; counts are not additive.
- **40** focused frontend tests and TypeScript passed. **Two** isolated Edge
  browser journeys passed with console checks, narrow-screen coverage and
  inspector close. The resulting screenshot was inspected.

All financial fixtures were synthetic and used owned disposable databases. No
operating trades, rights or valuations were created or changed. No new migration
is required; operating schema **20261028_102** was verified read-only. API
**8001** was reloaded and its health endpoint returned OK. The frontend was not
restarted; browser acceptance used isolated fixture servers. No full Python
suite, commit or push was performed.

Evidence: [plan/ledger](../superpowers/plans/2026-10-28-etp-spot-crypto-pnl.md),
[pure numerical cases](../../tests/test_cash_product_pnl.py),
[native booking and publication cases](../../tests/test_cash_product_pnl_integration.py),
[browser checks](../../apps/ops-console/browser-tests/cash-product-pnl.spec.ts).

## Remaining scope

Independent real-portfolio/source reconciliation and production scale/operations
remain separate acceptance. New product support does not generate distributions,
redemptions or token lifecycle events. Broader futures, floating/indexed/amortising
bonds and standalone OTC/exotic options remain subsequent product increments.

Research checked 28 October: [SEC ETN bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-50)
distinguishes ETN legal identity and market/indicative values; [CME/CF benchmark
guidance](https://www.cmegroup.com/articles/faqs/cme-cf-cryptocurrency-benchmarks-faq.html)
documents distinct regional daily crypto references. Reusing the supplied-price
bridge with explicit source/cut/calendar semantics is the project's implementation
choice, not a claim that all products share one valuation/accounting standard.
