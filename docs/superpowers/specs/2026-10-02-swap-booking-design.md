# Swap booking: agreed model and proposed alpha design

**Date:** 2026-10-02  
**Status:** Approved; booking implementation delivered and verified in an isolated environment. See the [delivery record](../../delivery/swap-booking-alpha.md).  
**Scope:** Booking OTC swaps referencing an existing economic instrument, starting with autocalls. Valuation remains deferred.

## Intent and final decisions

The tenant must be able to book a swap against a strategy with existing parties, governed properties, tags and references. The swap references a separately defined autocall economic instrument. That reference can represent an actual security or an OTC payoff definition; an ISIN, listing, funded issuance or independent position must not be fabricated merely to create the reference.

The autocall definition holds underlyings, barriers, coupons, observation dates and payoff/redemption rules. The swap holds its reference, contractual performance treatment, funding benchmark/spread/schedule and dates. Funding terms are not re-entered or overridden on the trade.

The final price decision supersedes the earlier upfront-only explanation: the swap quote expresses the value of the **swap itself per notional**, in its governed quote convention. It is not the price of the referenced autocall, a funding rate, an absolute contract MTM amount or an automatically generated cash payment.

Using the existing divisor convention:

`reference value = signed trade notional * swap quote / quote_factor`

Examples for positive GBP 1,000,000 notional:

| Quote | Factor | Reference value |
| --- | --- | --- |
| 2 | 100 | GBP 20,000 |
| -1.5 | 100 | GBP -15,000 |
| 0.02 | 1 | GBP 20,000 |
| 0 | 100 | GBP 0 |

The factor normalises scale, not economic meaning. Booking and future market-data quotes must use the same swap-value meaning, currency and holder-perspective sign convention. A provider using a different scale needs an explicit conversion; an absolute MTM or underlying quote cannot be accepted merely by changing a divisor. No market-data ingestion or pricing implementation is authorised by this design.

The tenant may record zero or a nonzero quote. A deliberate zero with an upfront recorded separately is a recorded entry basis, not proof of a genuinely zero-cost transaction. Later valuation must define treatment before producing totals. Do not claim a zero quote implies zero exposure or an upfront implies immediate P&L loss.

## Storage and retired alternatives

| Fact | Storage |
| --- | --- |
| Autocall payoff definition | Existing structured-product instrument graph |
| Swap category and contractual legs | Existing `secm.swap_terms`, `secm.swap_leg` and schedules/dates |
| Governed quote convention | Versioned `secm.instrument_booking_convention`, extended with SWAP |
| Executed notional, quote, strategy and attribution | One existing `trd.trade` row, subject the swap canonical instrument |
| Exact terms, leg orientation, quote convention and calculated entry reference value | Immutable `BOOKED` payload in `trd.trade_lifecycle_event` |
| Optional independently booked upfront/cost cash event | Separate `trd.trade` cash row referencing the swap through `reference_instrument_node_id`, when that cash workflow supports it |

There is **no automatic cash trade**, no generated obligation, no new `trade_payment`/`cash_payment` table, and no settlement subsystem in this slice. A separate cash entry is optional, tenant-directed and not implied by the swap quote. Its label alone is not enough to establish accounting or duplicate-removal rules. The existing schema vocabulary for CASH_FLOW does not establish a delivered cash-event UI; that capability is a separately tracked gap, not silently included here.

Earlier proposals to require an upfront percentage, generate linked cash/payment records atomically, or require payment dates on the swap ticket are retired. Discussion of dividends, recognition and reset payments supplies future lifecycle context only. It does not expand this booking project into dividend entitlement, accounting, reset calculation or settlement.

## Proposed first delivery boundary

Start with approved OTC TOTAL_RETURN swaps with exactly one PERFORMANCE leg referencing a visible approved STRUCTURED_PRODUCT autocall and one FUNDING leg referencing a visible rate index. Require explicit currencies, leg direction, return treatment and schedule references. Do not infer total-return treatment solely from the referenced product's name. A term set the current schema cannot describe accurately is ineligible, not defaulted.

This first slice books existing governed swap definitions, including isolated synthetic fixtures. It does not add a general swap-creation wizard. Tenant creation/approval UX for swap terms is the next reference-data slice; absence of that UI must remain visible in the delivery report. It also does not make an unfunded OTC payoff eligible for the funded structured-security booking path.

Reuse approved tenant-private booking conventions and existing permissions/proposal approval. `SwapConvention` defines kind SWAP, quantity unit NOMINAL, price basis SWAP_VALUE_PER_NOTIONAL, positive finite quoteFactor, priceCurrencyId, positive minimum/increment, sourceReference, effectiveFrom and OTC eligibility. Prices may be finite, signed or zero, within existing decimal storage limits. Price currency must match canonical swap base currency for this alpha. No invented default factor.

Canonical quote orientation is the holder perspective recorded in swap legs. BUY records positive notional in that orientation; SELL records negative notional and reverses exposure. Do not also negate the entered quote. Show the inherited PAY/RECEIVE leg orientation and the effect of side in review. OPEN/CLOSE remains optional execution intent, not contractual termination or position verification.

Required execution facts: active tenant strategy, swap, BUY/SELL, positive entered nominal in governed increments, explicitly entered quote (zero allowed), offset-aware execution timestamp, legal counterparty and required tenant properties. Retain existing optional parties, tags, references and comments. No listing, cash-security settlement date, maturity-derived settlement date or T+2 default. Reject settlementDate, bond accrual fields and incompatible route inputs on the swap endpoint rather than silently ignoring them.

Display **Swap price**, its scale and currency, inherited terms and **Entry reference value — not a payment or independently verified valuation**. Percentage-point conventions show `Swap price (% of notional)` when quoteFactor is 100. Factor 1 shows decimal value per notional; other factors show the actual divisor explicitly rather than being mislabeled as percent.

## Integration and safety

Add SWAP to product search/context and a dedicated POST `/v1/trades/swaps`, reusing product booking persistence, idempotency, annotations and error contracts. Keep swap-specific validation and context assembly in a focused module. Recheck authoritative approved terms and all referenced nodes at submit. Fingerprints must include exact leg facts, schedules, reference-definition versions, quote convention and relevant dates; stale review cannot produce a trade.

Snapshot amount kind is ENTRY_REFERENCE_VALUE with no PAY/RECEIVE payment direction. Store the entered quote unchanged and the signed notional separately. Creating the trade and BOOKED snapshot is transactional. Old product replay fingerprints must remain compatible.

Trade history/detail must identify nominal units, signed swap quote, entry reference value and immutable source terms. A changed current reference definition must not rewrite historical evidence. Existing cash-oriented P&L must fail closed for strategies containing these swap bookings; no partial strategy totals. Daily pricing, P&L, discounting, funding accrual, resets, dividends and optional cash-event reconciliation remain deferred.

## Acceptance

Lightweight Decimal tests first: factor 100 and 1, positive/zero/negative quotes, BUY/SELL orientation, exact precision, invalid factor and quantity increments. Then PostgreSQL/API tests for eligibility, missing funding facts, visibility, stale terms, concurrent replay, atomic rollback, required properties, and no generated cash rows. Frontend tests prove zero is not treated as blank, negative quotes survive review, funding is read-only, no settlement field is emitted and tenant switching invalidates the draft. Finish with isolated browser booking and full regression; never create synthetic trades in the operating tenant.

## Research register

Sources opened during discussion on 2026-10-02; modelling references, not requirements for regulatory compliance:

- [ISDA/FpML submission to the SEC, 2016](https://www.sec.gov/comments/s7-26-15/s72615-8.pdf): distinguishes quote notation, notional and upfront payments; a single ambiguous price field cannot express every derivative's economics.
- [CME FpML swaption message example, 2016](https://www.cmegroup.com/tools-information/lookups/advisories/cme-stp/files/swaptionssamplemessage21816.pdf): illustrates explicit payment currency, amount, parties and dates. Different product; does not mandate cash generation for autocall swaps.
- [FINOS CDM event model, 7.0.0](https://cdm.finos.org/docs/event-model/): separates resets and transfers; neither implies a one-to-one cash movement. Useful for future lifecycle separation, not a prescribed storage schema.
- [FINOS CDM design principles, 5.13.0](https://cdm.finos.org/docs/5.13.0/design-principles/): explicit units for prices and quantities and reuse of common components. Historical, no longer maintained documentation; used only for this enduring modelling principle, not current interface compatibility.
- [MSCI dividend-points methodology](https://www.msci.com/indexes/factor-indexes/dividend-points-indexes): distinguishes the economic ex-date treatment of dividends in total returns from later cash payment. Not adopted as a fund-accounting policy or dividend implementation here.

FpML specification URLs attempted during research returned access errors. Search snippets from those pages are not treated as opened evidence. The per-notional MTM convention, optional manual cash-entry policy and alpha restrictions are project decisions, not universal market conventions.
