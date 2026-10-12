# Instrument-specific creation and booking — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Trading/reference engineering  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). [Shared booking controls](../../delivery/booking-controls.md) apply across these paths. Creation, listing, booking, contractual lifecycle and valuation are separate capabilities.

## F12 Plain listed cash

- **Desired:** Book eligible generic or tenant-private listed cash instruments from the dedicated booking page.
- **Status / backend / frontend:** ALPHA. Approved listing/definition/date/factor validation and frozen BOOKED economics; cash ticket with strategy, side, quantity, price/currency and settlement.
- **Cuts/trade-offs:** Explicit eligible product allowlist; derivatives and bonds use separate tickets. Default T+2 business days is a convenience, not exchange-specific settlement certification.
- **Weaknesses:** Advisory search does not cover every execution constraint; legacy records can lack frozen conventions.
- **Remaining:** Broader cash-currency inventory support, robust market-specific settlement conventions and acceptance for new eligible subtypes. Legacy unproved records are cancel-only, not silently upgraded.
- **Evidence:** [Enriched cash](../../delivery/enriched-trade-booking-alpha.md), [integrity](../../delivery/quality-reviews/2026-10-05-cash-and-approval-integrity.md), [writer eligibility](../../../apps/reference_api/cash_booking_integrity.py).

## F13 Deliverable FX forwards

- **Desired:** One execution with base-currency amount and quote/base agreed rate; contract currencies/maturity are instrument terms.
- **Status / backend / frontend:** ALPHA. Typed approved terms, currency/rate/notional/date validation, term-derived settlement and immutable snapshot; dedicated FX ticket and history.
- **Cuts/trade-offs:** No requirement for users to manually book two offsetting trades. Delivery is not an opposite market execution.
- **Weaknesses:** No NDF support, derivative daily valuation or completed contractual delivery acceptance; maturity alone does not extinguish exposure.
- **Remaining:** Explicit delivered/closed exposure semantics and final marks when lifecycle/valuation is resumed; retain F24's parked status.
- **Evidence:** [FX booking](../../delivery/fx-forward-booking-alpha.md), [review](../../delivery/quality-reviews/2026-10-01-fx-forward-booking-alpha.md), [delivery slice](../../delivery/fx-delivery-lifecycle-alpha.md).

## F14 Listed options

- **Desired:** Canonical option/listing creation and premium booking with explicit opening/closing intent.
- **Status / backend / frontend:** ALPHA. Supported fixed deliverable/underlying and quotation conventions, integer contract quantity, premium factors and saved snapshots; option creation/review/ticket/detail.
- **Cuts/trade-offs:** OPEN/CLOSE records trader intent; it does not prove available inventory or identify lots. Dynamic strike/reference modelling is not universal booking support.
- **Weaknesses:** No inventory allocation, exercise/assignment, expiry obligations, automatic premium settlement or option valuation.
- **Remaining:** Lot/position validation and independently scoped contractual event/valuation handling; general OTC options require a new slice.
- **Evidence:** [Option delivery](../../delivery/listed-option-booking-alpha.md), [quality review](../../delivery/quality-reviews/2026-10-01-option-booking-alpha.md), [rules](../../../security_master_schema/option_booking.py).

## F15 Structured securities

- **Desired:** Book funded structured securities through listed or OTC routes, including OTC reference autocalls used by swaps.
- **Status / backend / frontend:** ALPHA. Governed product/parent-component terms and approved unit/nominal convention; listed route or OTC ticket with counterparty. Creation templates cover bounded autocall/composed-option/range-accrual/supertracker shapes.
- **Cuts/trade-offs:** ISIN presence does not determine listed versus OTC execution. Security booking is not a direct payoff-swap abstraction; a swap references an economic instrument (F18).
- **Weaknesses:** Complex payoff/event modelling is not complete valuation, distribution or automated autocall/redemption operations.
- **Remaining:** Template-specific lifecycle/payoff evaluation, maturity/final marks, model inputs and acceptance before valuation support.
- **Evidence:** [Booking delivery](../../delivery/structured-security-and-futures-booking-alpha.md), [terms research](../../../security-master-notes/27-structured-product-terms-and-coupon-memory.md), [draft/terms scope](../../../apps/reference_api/structured_product_contracts.py).

## F16 Futures

- **Desired:** Future family → canonical expiry → listing, delivery-month letters/year width, supported months, currencies including crypto and multiplier-aware booking.
- **Status / backend / frontend:** ALPHA. Family/expiry conventions, symbol previews, delivery terms, multipliers and governed listing workflow; grouped family/expiry creation and future ticket.
- **Cuts/trade-offs:** Booking supports conventional cash-settled index outright futures, integer contracts, tick/cutoff and monetary multiplier. Physical/crypto terms are creation-only. Frozen unit/quote/monetary conventions prevent applying the contract multiplier twice.
- **Weaknesses:** No physical/crypto booking, rolling, variation margin, expiry delivery, commodity-specific workflows or futures valuation.
- **Remaining:** Separate physical/crypto and settlement/valuation slices; exchange calendar/tick and contract-symbol maintenance; do not interpret a listing multiplier of one as missing the frozen family monetary multiplier.
- **Evidence:** [Family/contract conventions](../../delivery/futures-creation-and-contract-conventions-alpha.md), [booking slice](../../delivery/structured-security-and-futures-booking-alpha.md), [product rules](../../../security_master_schema/product_booking.py).

## F17 Bonds

- **Desired:** Listed/OTC nominal booking with unambiguous CLEAN or DIRTY quotes and accrued interest.
- **Status / backend / frontend:** ALPHA. Approved bond quotation/source conventions, signed accrued amounts and frozen clean/dirty settlement bridge; bond terms creation and dedicated ticket.
- **Cuts/trade-offs:** CLEAN adds the supplied accrual to consideration; DIRTY already includes it and does not add it again. The separate accrual evidence explains the bridge. Trade settlement accrual is not daily P&L accrual.
- **Weaknesses:** No automatic accrual schedule calculation, coupon/redemption ledger or full maturity handling. Some sparse terms require enrichment before approval/booking.
- **Remaining:** Automated accrued inputs and coupon/redemption when scoped; dirty market-mark normalization needs its own assessed per-nominal evidence, not a reused trade accrued amount.
- **Evidence:** [Bond booking](../../delivery/bond-booking-alpha.md), [economic inputs](../../delivery/economic-pnl-implementation-2026-10-09.md), [valuation capability checks](../../../valuation/product_inputs.py).

## F18 Generic swaps

- **Desired:** Performance/funded reference, optional funding index, spread, contractual notional/currency, total/excess return, leverage and reset/termination terms; flexible booked notional and whole-swap quote.
- **Status / backend / frontend:** ALPHA. Typed governed terms/legs, reference revalidation, contractual and booked nominal retained separately, counterparty and immutable quote-factor snapshot; generic creation and OTC booking ticket.
- **Cuts/trade-offs:** Swaps reference economic instruments, including OTC autocalls. Funding economics stay in terms. User may book zero or a compatible price; no automatic upfront cash entry or duplicate leverage multiplication.
- **Weaknesses:** No universal swap payoff engine, automatic funding/reset postings, final marks, settlement or valuation. A separate operational cost/upfront cash booking is not generated merely because a quote was entered.
- **Remaining:** Controlled lifecycle/reset/final valuation and cash-flow reconciliation when resumed. Quote and received market marks must use the same whole-swap dimensions/quote factor.
- **Evidence:** [Generic swap delivery](../../delivery/generic-swap-creation-and-booking.md), [legacy supported slice](../../delivery/swap-booking-alpha.md), [creation](../../../apps/reference_api/swap_creation.py), [booking](../../../apps/reference_api/generic_swap_booking.py).
