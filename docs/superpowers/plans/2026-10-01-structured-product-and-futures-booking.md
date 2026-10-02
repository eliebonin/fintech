# Structured product and futures booking plan

**Status:** Implemented bounded alpha with linked verification and manual limits
**Content type:** Implementation plan and research  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-01

Extend the dedicated trade-booking workspace with structured securities and futures, retaining tenant isolation, governed properties, review, replay safety and immutable booking snapshots. Start with fully funded structured notes/certificates, whether listed or OTC, followed by conventional cash-settled index futures. Bilateral structured derivatives need a separate confirmation-led slice; they must not be treated as purchases of funded securities.

This plan was reviewed and approved for bounded implementation on 2026-10-01. Implementation and verification are recorded in [structured security and futures delivery](../../delivery/structured-security-and-futures-booking-alpha.md). It is not an approved valuation design. Booking records an executed transaction; it does not route an order, confirm settlement, calculate positions or post margin. The existing [booking and lifecycle boundary](../../delivery/booking-and-lifecycle-scope.md) continues to apply.

## Research findings and applicability

Sources were opened and checked on 2026-10-01. The following distinctions are evidence-backed; the delivery restrictions below are project choices, not universal market rules.

| Primary source | Finding and applicability | Proposed consequence |
| --- | --- | --- |
| [ANNA DSB](https://www.anna-dsb.com/) | DSB issues ISINs for OTC derivatives. An ISIN therefore does not establish exchange listing or execution venue. Live service page; no regulatory reporting implementation is implied. | Keep identifiers, listing and execution route separate. Permit an OTC instrument with an ISIN and one without it. |
| [SIX off order book trading guide](https://www.six-group.com/dam/download/the-swiss-stock-exchange/trading/trading-provisions/regulation/trading-guides/swxess-off-order-book.pdf) | The published guide distinguishes unit quantities/unit prices from nominal quantities/percentage prices for structured-product bonds. Its sections carry 2018–2021 effective dates. This is a concrete venue convention, not a current worldwide rule. | Source each product's quantity and quotation convention; do not universally assume shares or monetary unit prices. Do not import the historical settlement defaults. |
| [CME Micro E-mini specifications](https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html) | The displayed MES economics specify USD 5 per index point and a 0.25-point minimum tick. These are product-specific facts, not defaults for all futures. | Govern multiplier, price unit and permitted increments per contract/listing. |
| [CME Micro E-mini FAQ](https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html) | Contracts have expiry series; daily and final settlement are distinct. Outright and spread increments can differ. Some illustrative values are explicitly dated February 2023. | Select an exact expiry, not a continuous/front-month alias. Initially support outright executions, not spreads or automatic rolls. Source dates/cutoffs rather than calculating them from the FAQ. |
| [CME futures margin explanation](https://www.cmegroup.com/education/courses/understanding-the-benefits-of-futures/the-benefits-of-futures-margins) | Futures margin is a deposit, not a down payment for the underlying. The page does not prescribe our internal ledger schema. | Do not label contract value as gross purchase consideration or generate a principal payment on booking. Margin processing remains deferred. |
| [CME clearing advisory 20-160](https://www.cmegroup.com/notices/clearing/2020/04/Chadv20-160.pdf) | The 15 April 2020 advisory documents system support for zero/negative futures prices, including affected energy products. This is historical evidence, not permission to use negative prices for every contract. | Do not inherit a universal positive-price validator. Apply sourced contract eligibility and price constraints. |

The legacy FIX field link redirected to a catalogue without the requested field content; a related equity-swaps PDF was a 2016 release candidate. Neither is used to assert a current mandatory futures OPEN/CLOSE rule. An FpML page returned HTTP 403 and is not relied upon. No inaccessible source or search snippet establishes a decision here.

## Existing foundations and gaps

Inspected implementation:

- `security_master_schema/models.py` already defines the parent structured-product terms graph, observations, coupons and component relationships; `future_family`, expiry-level `future_terms`, effective-dated `instrument_contract_unit_terms` and `listing_quotation_terms` also exist.
- `apps/reference_api/structured_product_contracts.py`, `main.py` and `repository.py` already support structured-product proposals and approval. The current draft is an autocall builder, not an arbitrary structured-contract booking endpoint.
- `apps/ops-console/src/lib/instrument-create-options.ts` exposes structured-product creation under the OTC group, even though a structured security can have a listing. No futures creation choice is present.
- The cash, FX-forward and option implementations provide reusable tenant context, parties, tags, governed properties, references, transactional persistence and history. Product-specific economics must remain separate.
- The cash writer in `repository.py` rejects OPTION, FX_FORWARD, FUTURE and SWAP, but not STRUCTURED_PRODUCT. Accepted cash trades receive `quantity_unit=SHARES` and `price_basis=UNIT_PRICE`. That is not sufficient structured-product support.
- The current cash request requires a listing, a positive price and a settlement date. The option request inherits it. Futures must not inherit premium/security-settlement requirements merely for code reuse.
- Existing P&L guards reject FX forwards and options; there is no equivalent explicit structured-product/futures guard in the inspected calculation. Add protection before enabling these bookings, without implementing valuation.

Existing tables reduce new work; they do not establish booking readiness. Do not interpret the structured terms' ambiguous `notional_amount` field as denomination, total issuance and trade notional simultaneously. Resolve its meaning and introduce explicit terms where necessary, preserving existing records.

## Product identity and booking routes

| Economic form | Selection | Initial scope |
| --- | --- | --- |
| Funded structured note or certificate with a listing | Canonical instrument plus selected approved listing | Included |
| Funded structured note or certificate traded OTC | Approved canonical instrument; no invented listing; optional ISIN | Included |
| Listed structured security executed off exchange | Canonical instrument with explicit approved OTC convention; no reference listing on this alpha ticket | Included without reference-listing capture; that extension is deferred |
| Bilateral structured derivative | Exact approved contract plus legal counterparty and confirmation reference | Separate later booking slice |
| Exchange future | Approved family, exact expiry-level instrument and listing | Cash-settled index outright contracts first |

Reviewed request design: an explicit LISTED/OTC route, with listing required for listed execution and no reference listing for OTC execution in this first slice. This deliberately avoids conflating a reference listing with an execution venue. Optional reference-listing capture can be added later with separate provenance. Never derive the execution venue simply from an ISIN. Instruments with no listing are not automatically OTC; an explicit eligible booking route is required.

Book the structured parent once. Its option/coupon components describe its economics and must not become independent duplicate trades. Instrument terms carry the payoff, underlyings, barriers and schedules; the ticket captures the executed quantity, price, parties and dates.

## Structured security ticket

### Governed instrument facts

Before booking eligibility, require an approved economic form/funding classification, issue currency, issuer, maturity, quantity convention, quotation convention, denomination where relevant, and minimum quantity/increment. Use sourced terms and a retained document/reference. Version facts that affect booking and include them in the review fingerprint.

Do not infer funding from the existing autocall subtype, presence of an ISIN, absence of a listing, or a non-null notional. Missing conventions block booking with a specific explanation. OTC quotation terms require instrument-level provenance rather than fabricated venue data. Separate the percent-price divisor from denomination and from minor-currency conversion; never apply one factor twice.

### Execution fields and calculation

Reuse strategy, BUY/SELL, execution timestamp, purpose, primary/secondary activity, counterparty, executing broker, trader, custom properties, tags, references and comments. Capture quantity in the approved convention, executed quote, price/trade currency, and explicit security settlement date. No universal T+2 assumption and no use of maturity as the purchase settlement date.

Project calculation choices for supported conventions:

- Monetary price per unit: `units × monetary price`, after an explicitly sourced minor-unit conversion if applicable.
- Percent of nominal: `nominal × quoted percent / 100`.
- Units quoted as percent of denomination: first derive `nominal = units × denomination`, then apply the percent formula once.

For example, buying USD 100,000 nominal at 98.5 percent gives USD 98,500 before accrued interest and fees. Buying 100 notes of USD 1,000 denomination at the same percent gives the same amount; it is not `100 × 98.5` dollars. These are illustrative calculations, not current product facts.

Initial support should require either an explicit no-accrual convention or a dirty/all-in quote. Defer clean-price products until separately supplied accrued interest can be recorded and reconciled without guessing. Do not infer accrued interest from a complex coupon graph. If fees are captured, store them separately with currency and amount; never silently blend them into execution price. Label the calculated amount as contractual consideration, not proof of payment. Initially require supported price/settlement currency alignment; cross-currency settlement needs explicit agreed conversion facts in a later slice.

### OTC bilateral derivatives

Do not expose these through the funded-security ticket. A subsequent design must classify funded/unfunded/partially funded economics from the actual confirmation, distinguish trade notional from cash exchanged, capture any explicit upfront amount and its direction/date, identify legal parties, and define supported contract types. There is no proposed universal `notional × price` cash formula for this group. One anonymised representative confirmation is a design input, not a prerequisite for implementing funded OTC notes.

## Futures ticket

### Governed instrument facts

Reuse the family and expiry-level schema. Add governed onboarding, approval and inspection for the actual contract: underlying, exchange/product symbol, contract month, exact last-trading instant/timezone, expiry/final settlement facts, settlement method/currency, price unit, economically dimensioned multiplier, quotation factor and applicable quantity/price increments. Do not silently accept the existing multiplier default of one as evidence. Resolve the as-of version of each fact.

Start with conventional cash-settled linear index futures. Reject physical-delivery contracts, bond/fractional quoting, spread packages, financing-adjusted/spot-quoted products and unsupported variable tick schedules with clear reasons. This is an alpha restriction, not a claim that they cannot eventually be booked.

### Execution capture

Require strategy, BUY/SELL, positive integer contract count, exact execution timestamp, executed quoted price and governed currency. Capture OPEN/CLOSE using the existing shared position-effect field as a project consistency choice, with the same warning as options: it records intent, not verified holdings. Mixed intent can be entered as separate explicit bookings; no automatic lot allocation.

Reuse properties and existing party roles. Keep executing broker, clearing broker/account and legal counterparty semantically distinct. Add governed clearing-role capture if needed; do not silently designate the exchange or CCP as the executing counterparty. Booking must not claim a clearing acknowledgement has occurred.

Do not require a cash-security settlement date or apply the cash ticket's T+2 default. Display sourced final-settlement information read-only, separately from daily settlement; neither is a booking-time payment. Any downstream mandatory `settlement_date` contract must be rationalised explicitly rather than filled with a fabricated date.

For the initial linear model, display `contracts × quoted price × monetary value per price unit`, with quote conversion applied once, as a reference contract value only. For example, two MES contracts at 6,000 points with USD 5 per point correspond to USD 60,000 reference value, not a USD 60,000 purchase payment. No premium is invented. No initial/variation margin or daily cash movement is created by booking.

Use decimal arithmetic. Support zero/negative prices only where approved contract rules permit them. Validate the applicable increment for individual outright fills; reject unsupported package pricing. An average price from multiple fills can be off tick, so do not enforce single-fill tick rules on an aggregated booking. Initially support single fills; average-price capture needs an explicit provenance/mode in a subsequent extension.

## Delivery sequence

1. **Eligibility and conventions.** Agree the first supported products. Define explicit funding, quantity and quotation semantics; add missing effective-dated facts and approval controls. Block structured/futures misuse of the generic cash writer and add unsupported-product P&L guards. Audit existing affected rows; do not silently recalculate or rewrite them.
2. **Structured securities end to end.** Extend the existing structured creation workflow rather than create another competing master. Rationalise creation categories; implement listed and OTC search, eligibility/context endpoint, dedicated request/writer, review, immutable snapshot and history. Keep canonical terms read-only on the ticket.
3. **Futures end to end.** Implement governed family/expiry onboarding and listings, dedicated search/context, request/writer, contract-count ticket, review, immutable snapshot and history. Reuse UI infrastructure, not cash settlement semantics.
4. **Robust regression and acceptance.** After lightweight economics/model tests, run integration, migration, replay/concurrency, tenant/security and browser tests. Perform an operator walkthrough before calling either slice signed off.
5. **Broader conventions later.** Use representative confirmations/specifications to design bilateral structured derivatives, average-price executions, additional futures families and packages. Settlement, positions, lifecycle, valuation and margin remain separate modules requiring approval.

For both writers, require server-authoritative eligibility and as-of terms fingerprints, lock relevant records, persist annotations transactionally, retain tenant/endpoint idempotency, and store a versioned BOOKED snapshot. Retries use the frozen reviewed payload. Later master-data changes must not change the booked economics or history presentation. Source document access must respect tenant visibility.

## Acceptance criteria

- Book a listed structured note, an OTC funded note with an ISIN, and one without it; preserve route and counterparty and avoid artificial listings.
- Verify monetary unit quotes, nominal percentage quotes and units/denomination percentage quotes, including minor-unit conversion, allowed quantity increments and dirty/no-accrual conventions. Reject missing/unsupported terms rather than estimate.
- Book BUY/OPEN and SELL/CLOSE futures with exact expiry, contracts, multiplier and quote units; show reference value without a principal/premium payment or T+2 date.
- Verify valid/invalid ticks for supported single fills, signed-price eligibility, expiry cutoffs and explicit rejection of unsupported delivery/package conventions.
- Preserve custom zero, false and choice values, tags, parties and references through review/edit/retry and persisted history for both products.
- Reject hidden tenant references, missing module/write rights, stale terms and duplicate/conflicting retries; concurrent replay creates one trade. Test atomic rollback on invalid annotations.
- Confirm history survives changes in current terms, and a structured parent does not also book its component instruments.
- Test additive migrations against old data; run focused tests first, then the full Python/frontend suites, contract checks, typecheck/build and browser regressions. Document failures and manual-check limitations honestly.
- Existing cash/FX/option booking remains unchanged except explicit eligibility safety gates. Unsupported structured/futures strategies receive no misleading partial cash-only P&L total.

## Outstanding decisions

The user approved review, simplification and implementation on 2026-10-01. Review found the economic distinctions necessary, but a general product DSL, clearing engine and new structured payoff master would overdo this slice. Implement one narrowly typed, append-only booking-convention record attached to the existing canonical instrument, approved through the existing operations queue. It records explicit execution units/quotation facts and source evidence, not a second payoff graph. Existing structured instruments receive conventions through a separate configuration proposal; the complex autocall builder is not duplicated. Futures creation reuses governed proposal/approval and family/expiry tables.

The accepted first slice remains funded notes/certificates with unit or nominal quoting and no-accrual/dirty pricing, listed or OTC; then cash-settled conventional index futures. Before expanding scope, obtain representative terms for clean-priced structured securities and a bilateral structured derivative. No valuation inputs or discount curves are needed to implement this bounded booking plan. Clearing broker/account can use existing governed annotations for now; no mandatory clearing-account master or acknowledgement workflow is introduced. Keep single-fill futures explicit rather than building average-price allocation.

The preceding option cleanup is activated locally and has documented automated and synthetic booking evidence. Its cross-product native discard-dialog browser check remains a manual verification limitation, not a passed check; see [option delivery](../../delivery/listed-option-booking-alpha.md). This proposal does not change that status.
