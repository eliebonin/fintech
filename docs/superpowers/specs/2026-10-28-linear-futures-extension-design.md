# Linear futures booking and P&L extension

**Status:** Implemented within the scope below; [delivery and verification](../../delivery/linear-futures-extension-20261028.md).  
**Date:** 28 October 2026.  
**Intent:** Extend the existing family → dated contract → listing → trade → daily P&L flow using actual contract economics. Crypto underlyings and physical delivery do not themselves require different pre-delivery price-variation arithmetic.

## Agreed direction and approach

The user accepted distinguishing daily futures P&L from expiry/delivery processing and asked for an implementation plan. This design proposes extending the existing linear adapter. It does not authorize operating bookings or valuation publication.

Alternatives considered:

- Remove refusal messages only: insufficient, because index-only checks also exist in frozen reconstruction and market-input dimensions.
- Build full delivery, clearing and margin accounting first: unnecessary for the requested supplied-price economic P&L.
- **Recommended:** replace index-only capability checks with shared, explicit linear quotation validation; reuse the existing numerical and governed review workflow. Retain recorded expiry and delivery terms as boundaries, without generating delivery effects.

The first increment covers the modelled family kinds INDEX and CRYPTOASSET. Existing creation supports INDEX_POINTS/CASH and linear UNDERLYING_UNIT crypto with CASH or PHYSICAL settlement. Commodity, currency-pair and interest-rate family/reference models are not already implemented; do not masquerade as an index to support them. They can later use the same numerical adapter once their own reference and quotation contracts exist.

## Economics

For each economic day, with signed opening/closing contracts Q0/Q1, exact-contract prices P0/P1, signed executions qi/pi, frozen monetary multiplier M and divisor D:

```
native variation = (Q1×P1 − Q0×P0 − Σ(qi×pi)) × M / D
reporting P&L = native variation × that day's closing reporting FX
```

M applies once; contract size and listing multiplier must not be applied again. For supported UNDERLYING_UNIT contracts, existing conventions require contract size = M. Native variation is in the recorded price currency. An inverse, quanto, perpetual or separate financing-adjustment contract must not enter this adapter by supplying plausible-looking linear fields.

Acceptance examples: unchanged 2-contract BTC future, size/multiplier 5, prices 100,000→101,000 yields 10,000 USD; closing FX 0.8 GBP/USD yields 8,000 GBP. A synthetic physical-delivery BTC contract with 3 contracts, multiplier 1 and a +500 USD price move yields 1,500 USD before delivery. Both reuse the same bridge.

## Booking and evidence

- Preserve creation, approval, family membership, exact expiry listing, active visible underlying, currencies, contract size, tick, multiplier, divisor, trading cutoff and delivery-date validation.
- Shared capability logic belongs below HTTP adapters and is used by readiness, execution and frozen valuation. Underlying validation remains type-specific; crypto must resolve to an active governed cryptoasset, not an index_terms row.
- Validate governed references and lock relevant records before booking. Convention amendments cannot change approved family economics or canonical delivery dates.
- Preserve every original BOOKED snapshot and fingerprint. Recover existing index facts exactly as today. New bookings retain the convention/identity required for deterministic replay; do not substitute today's family parameters for old economics.
- Use contract-specific CLOSE/SETTLEMENT inputs at the policy cut with native RAW and explicit contract/quotation/divisor dimensions. No spot-crypto or continuous-futures series substitution.
- Use the contract's governed exchange/settlement calendar and economic dates, not a blanket 24/7 calendar inferred from its underlying. Any execution-date versus valuation-date convention remains explicit.
- Preserve source rights, tenant/strategy scope, information cutoff, provider priority, freshness, evidence revalidation and review authority.

## Delivery boundary and scope

Physical delivery does not automatically stop pre-delivery P&L. Trading eligibility and price-boundary eligibility remain distinct: no new trade after the approved trading cutoff; a valid contract mark can still be required at final settlement. Expiry/delivery dates alone must not generate a zero price, remove exposure, create a spot holding or modify cash.

An actual recorded close retains same-day P&L. Unclosed exposure beyond the supported final-settlement boundary remains an explicit Ops exception. Delivery notices/assignment, physical receipts, margin calls, funding and accounting postings are separate work. Any unsupported earlier delivery/assignment requires explicit recorded handling; the system cannot infer that the position survives from a schedule alone.

Futures price variation remains separate from cash-balance FX. Gross notional is not a contract MTM/NAV asset. Keep current null stock-value fields and the explicit futures term in batch reconciliation. Do not broaden the separate monetary-measure preview by implication.

## UI and acceptance

Keep existing booking/results pages. Display exact contract/listing, contracts, price currency, multiplier, price basis, settlement method, delivery dates where applicable, selected input dates, daily native variation and reporting FX. Explain unsupported economics precisely; do not label all crypto futures creation-only.

Focused test-first numerical checks precede disposable native booking/staging/amendment/publication tests and isolated browser checks. Existing index behavior must remain identical. No full Python suite is required for this bounded increment. No operating financial writes, source grants or Git changes beyond documentation are part of planning.

## Source grounding

Checked 28 October 2026:

- [CME money-calculation guidance, 11 June 2015](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf): opening-position and same-day execution variation are the shared foundation. Its clearing-specific rounding and special/inverse/financing methods are not silently substituted for this project's exact economic attribution.
- [CME cryptocurrency futures FAQ](https://www.cmegroup.com/articles/faqs/frequently-asked-questions-cryptocurrency-futures.html): financially settled crypto contracts, product-specific reference rates, special products and exchange trade-date/session conventions exist. Use current contract specifications rather than older educational trading-hour examples.
- [CME grain delivery explanation](https://www.cmegroup.com/education/courses/introduction-to-agriculture/grains-oilseeds/understanding-the-grain-delivery-process): delivery introduces notices, matching and transfer obligations. It is a distinct lifecycle from the supplied-price bridge; many positions are offset before delivery.

The bounded rollout and the project's reporting-FX convention are implementation decisions, not a claim to reproduce all exchange clearing statements.
