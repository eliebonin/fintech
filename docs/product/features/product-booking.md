# Instrument-specific creation and booking — capability records

23 October F14: [private standard SPX source import](../../delivery/reconciliation-spx-option-20261023.md)
converts owner-confirmed embedded-multiplier quantities into actual contracts,
preserves premium economics, approves an XCBO listing and uses native option
booking/replay. Old mockup terms remain retained and untradable. This does not
add a public option-upload template or exercise handling. The subsequent
[supplied-premium P&L extension](../../delivery/option-premium-pnl-20261023.md)
supports daily marks with the frozen contract multiplier applied once.

23 October: [native AMC onboarding](../../delivery/amc-onboarding-20261023.md)
adds creation/approval, inspection and listed/OTC funded booking with explicit
certificate identity. Unit and percentage-quoted daily processing and the three
monetary measures use explicit quotation factors. Fee modelling, look-through,
redemption and dedicated convention-amendment UI remain deferred.

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Trading/reference engineering  
**Last reviewed:** 2026-10-28 (structured-note quote/accrued follow-up; other evidence remains dated)

[Feature register](../feature-register.md). [Shared booking controls](../../delivery/booking-controls.md) apply across these paths. Creation, listing, booking, contractual lifecycle and valuation are separate capabilities.

October 16 approved internal cleanup for F16/F18: shared futures conventions and
generic swap terms now live below the API layer. Legacy API imports re-export the
same classes; validation, frozen JSON, OpenAPI and financial formulas are unchanged.
See [compatibility evidence and remaining boundaries](../../delivery/quality-reviews/2026-10-16-backend-remediation.md#shared-term-model-follow-up).
This does not expand booking or valuation product coverage.

## F12 Plain listed cash

30 October [typed fund-unit movements](../../delivery/fund-unit-movements-20261030.md)
add internal TRANSFER/REINVESTMENT booking with frozen unit/type proof, existing
authority and audited retries. Ordinary purchases still require positive prices.
Movements generate neither cash nor income; native daily valuation separates
principal from returns. Existing erroneous-record cancellation is available;
movement entry UI, upload templates and purchase-ticket replacements are absent.

28 October [cash-product P&L follow-up](../../delivery/etp-spot-crypto-pnl-20261028.md):
generic ETP readiness now requires effective concrete terms and pins the selected
term/kind. Native wrapper, token and fund bookings use UNITS; original SHARES
labels are retained in ledger evidence and normalized only in the projections.
Equity/ETF labels and cash booking authority/precision remain unchanged.

- **Desired:** Book eligible generic or tenant-private listed cash instruments from the dedicated booking page.
- **Status / backend / frontend:** ALPHA. Approved listing/definition/date/factor validation and frozen BOOKED economics; cash ticket with strategy, side, quantity, price/currency and settlement.
- **Cuts/trade-offs:** Explicit eligible product allowlist; derivatives and bonds use separate tickets. Default T+2 business days is a convenience, not exchange-specific settlement certification.
- **Weaknesses:** Advisory search does not cover every execution constraint; legacy records can lack frozen conventions.
- **Remaining:** Broader cash-currency inventory support, robust market-specific settlement conventions and acceptance for new eligible subtypes. Legacy unproved records are cancel-only, not silently upgraded.
- **Implementation boundary:** [29 October cash extraction](../../delivery/cash-booking-service-extraction-20261029.md) shares `trading.booking` between HTTP and file confirmation; its command models/store and required validators are independent of the API. Product scope, dates, frozen conventions and financial semantics are unchanged.
- **Evidence:** [Enriched cash](../../delivery/enriched-trade-booking-alpha.md), [integrity](../../delivery/quality-reviews/2026-10-05-cash-and-approval-integrity.md), [writer eligibility](../../../trading/cash_reference.py), [native/API/file parity](../../../tests/test_trading_cash_booking.py).

## F13 Deliverable FX forwards

- **Desired:** One execution with base-currency amount and quote/base agreed rate; contract currencies/maturity are instrument terms.
- **Status / backend / frontend:** ALPHA. Typed approved terms, currency/rate/notional/date validation, term-derived settlement and immutable snapshot; dedicated FX ticket and history.
- **Cuts/trade-offs:** No requirement for users to manually book two offsetting trades. Delivery is not an opposite market execution.
- **Weaknesses:** No NDF support, discounted model MTM or completed contractual delivery acceptance. [Rate-based daily P&L](../../delivery/fx-forward-rate-pnl-20261014.md) requires explicit contract-rate source semantics and governed reporting FX.
- **Remaining:** Actual delivery/payment, provider reconciliation and discounted-model support. [Deliverable maturity exposure closure](../../delivery/fx-forward-maturity-20261014.md) contributes its actual booked closing rate to rate-based P&L; it does not sign off the parked delivery prototype.
- **Evidence:** [FX booking](../../delivery/fx-forward-booking-alpha.md), [review](../../delivery/quality-reviews/2026-10-01-fx-forward-booking-alpha.md), [delivery slice](../../delivery/fx-delivery-lifecycle-alpha.md).

## F14 Listed options

- **Desired:** Canonical option/listing creation and premium booking with explicit opening/closing intent.
- **Status / backend / frontend:** ALPHA. Supported fixed deliverable/underlying and quotation conventions, integer contract quantity, premium factors and saved snapshots; option creation/review/ticket/detail.
- **Cuts/trade-offs:** OPEN/CLOSE records trader intent; it does not prove available inventory or identify lots. Dynamic strike/reference modelling is not universal booking support.
- **Weaknesses:** No inventory allocation, exercise/assignment, expiry obligations, automatic premium settlement or option-pricing model. [Supplied-premium P&L](../../delivery/option-premium-pnl-20261023.md) uses actual contract counts and the frozen premium multiplier once; it does not add Greeks or monetary measures.
- **Remaining:** Lot/position validation and independently scoped contractual event/valuation handling; general OTC options require a new slice.
- **Evidence:** [Option delivery](../../delivery/listed-option-booking-alpha.md), [quality review](../../delivery/quality-reviews/2026-10-01-option-booking-alpha.md), [rules](../../../security_master_schema/option_booking.py).

## F15 Structured securities

October 16 [intake hardening](../../delivery/quality-reviews/2026-10-16-backend-remediation.md):
strict finite draft terms, reconciled variable coupons/barrier summaries, nested
source/observation scope and current-rights checks, plus published contractual
calendar generation/revalidation. Edited UI schedules retain an explicit reason;
legacy EXPLICIT API requests remain compatible. This is not payoff valuation or
automated termsheet acceptance. F15 remains ALPHA.

[Six seeded PDF notes](../../delivery/termsheet-note-booking-readiness-2026-10-14.md) now have
approved conventions and report READY on the structured-security OTC ticket.
The listed-cash ticket intentionally excludes structured products.

- **Desired:** Book funded structured securities through listed or OTC routes, including OTC reference autocalls used by swaps.
- **Status / backend / frontend:** ALPHA. Governed product/parent-component terms and approved unit/nominal convention; listed route or OTC ticket with counterparty. Creation templates cover bounded autocall/composed-option/range-accrual/supertracker shapes.
- **Cuts/trade-offs:** ISIN presence does not determine listed versus OTC execution. Security booking is not a direct payoff-swap abstraction; a swap references an economic instrument (F18).
- **Weaknesses:** Complex payoff/event modelling is not complete valuation, distribution or automated autocall/redemption operations.
- **Remaining:** Template-specific lifecycle/payoff evaluation, generated maturity/redemption and model pricing. [Supplied whole-note P&L](../../delivery/structured-note-pnl-20261028.md) is supported with matching frozen CLEAN/DIRTY/NONE quotations, optional assessed CLEAN interest and explicit economic income; it does not require or implement a payoff-pricing engine. Existing booking maturity limits remain.
- **Evidence:** [Booking delivery](../../delivery/structured-security-and-futures-booking-alpha.md), [terms research](../../../security-master-notes/27-structured-product-terms-and-coupon-memory.md), [draft/terms scope](../../../apps/reference_api/structured_product_contracts.py).

## F16 Futures

28 October [linear crypto extension](../../delivery/linear-futures-extension-20261028.md)
adds native UNDERLYING_UNIT booking and supplied-contract daily P&L for approved
cash/physical crypto families. Original conventions and quote/asset role checks
remain authoritative. Physical delivery processing is separate; the index-only
monetary-preview scope below is not expanded.

27 October [daily economic P&L](../../delivery/futures-daily-pnl-20261027.md)
now supports the existing cash-settled index slice, with multiplier-once price
variation and daily closing FX, original-booking evidence and staged publication.
That initial increment did not expand crypto booking or prove contract MTM;
the subsequent 28 October extension adds the bounded crypto booking/P&L scope.

October 15 [monetary-measures follow-up](../../delivery/future-position-measures-20261015.md)
adds governed current notional/exposure for the cash-settled index slice, not
contract MTM, futures P&L, margin or physical/crypto booking.

- **Desired:** Future family → canonical expiry → listing, delivery-month letters/year width, supported months, currencies including crypto and multiplier-aware booking.
- **Status / backend / frontend:** ALPHA. Family/expiry conventions, symbol previews, delivery terms, multipliers and governed listing workflow; grouped family/expiry creation and future ticket.
- **Cuts/trade-offs:** Booking supports dated linear index/crypto outright futures, integer contracts and explicit tick/cutoff/multiplier. Crypto UNDERLYING_UNIT supports CASH or PHYSICAL settlement terms; no delivery entries are generated. Frozen unit/quote/monetary conventions prevent applying the contract multiplier twice.
- **Weaknesses:** No rolling, margin accounting, automatic expiry/delivery, inverse/quanto/perpetual/financing adapter or commodity/rate/currency-pair family models. Contract MTM remains unassessed; daily price variation is supported. Existing monetary exposure remains index-only. Exact-contract pricing/quote metadata and eligible policy/source coverage are required.
- **Remaining:** Delivery/assignment and post-trading-cutoff lifecycle closure; additional family/reference/quotation models, clearing acceptance, exchange calendars/ticks and symbols; do not interpret a listing multiplier of one as missing the frozen family monetary multiplier.
- **Evidence:** [Family/contract conventions](../../delivery/futures-creation-and-contract-conventions-alpha.md), [booking slice](../../delivery/structured-security-and-futures-booking-alpha.md), [product rules](../../../security_master_schema/product_booking.py).

## F17 Bonds

23 October: [private source bond-import delivery](../../delivery/reconciliation-bond-bookings-20261023.md)
maps owner-confirmed CLEAN fraction-of-par execution prices into native nominal
booking with separately translated settlement accrual, retained originals and
replay identities. Historical pre-issue executions retain their actual issue and
settlement dates. Activation/test status is recorded in the delivery; this is not
a public bond-upload template or automatic coupon/cash workflow.

- **Desired:** Listed/OTC nominal booking with unambiguous CLEAN or DIRTY quotes and accrued interest.
- **Status / backend / frontend:** ALPHA. Approved bond quotation/source conventions, signed accrued amounts and frozen clean/dirty settlement bridge; bond terms creation and dedicated ticket.
- **Cuts/trade-offs:** CLEAN adds the supplied accrual to consideration; DIRTY already includes it and does not add it again. The separate accrual evidence explains the bridge. Trade settlement accrual is not daily P&L accrual.
- **Weaknesses:** No automatic accrual schedule or coupon generation. [Ops-triggered full plain-bond principal redemption](../../delivery/plain-bond-redemption-20261014.md) is supported; partial/amortising/indexed/defaulted maturity and final-interest automation are not. Some sparse terms require enrichment before approval/booking.
- **Remaining:** Automated accrued inputs and broader coupon/redemption when scoped. [DIRTY market normalization](../../delivery/bond-dirty-to-clean-20261028.md) now consumes exact source quoted accrual per 100; it never reuses trade accrued or generates missing provider inputs.
- **Evidence:** [Bond booking](../../delivery/bond-booking-alpha.md), [economic inputs](../../delivery/economic-pnl-implementation-2026-10-09.md), [valuation capability checks](../../../valuation/product_inputs.py).

## F18 Generic swaps

30 October [rate-exchange extension](../../delivery/rate-exchange-swaps-20261030.md)
adds a separate two-floating-leg variant, current reference revalidation and
guarded first-time completion of sourced non-tradable identities. Each component
keeps its own trade, bank marks and P&L. The creation page offers both structures;
booking/detail inspection renders explicit rate-leg facts. No curves, generated
cashflows, general term amendments or rate-swap monetary measures are supplied.

- **Desired:** Performance/funded reference, optional funding index, spread, contractual notional/currency, total/excess return, leverage and reset/termination terms; flexible booked notional and whole-swap quote.
- **Status / backend / frontend:** ALPHA. Typed governed terms/legs, reference revalidation, contractual and booked nominal retained separately; optional unit-based contracts retain units plus exact reference notional/unit and derived booked notional. Counterparty and immutable quote-factor snapshot; generic creation and OTC booking ticket, unit-aware history/details. See [unit swap extension and seeded examples](../../delivery/mock-unit-swaps-20261015.md).
- **Cuts/trade-offs:** Swaps reference economic instruments, including OTC autocalls. Funding economics stay in terms. User may book zero or a compatible price; no automatic upfront cash entry or duplicate leverage multiplication.
- **Weaknesses:** No universal swap payoff engine, automatic funding/reset postings, generated final marks or settlement. [Supplied whole-swap mark P&L](../../delivery/swap-supplied-mark-pnl-20261023.md) is now supported with compatible native unit/nominal quotes and frozen evidence; it does not model the payoff or infer funding. A separate operational cost/upfront cash booking is not generated merely because a quote was entered.
- **Remaining:** Controlled lifecycle/reset/final valuation and cash-flow reconciliation when resumed. Quote and received market marks must use the same whole-swap dimensions/quote factor.
- **Evidence:** [Generic swap delivery](../../delivery/generic-swap-creation-and-booking.md), [legacy supported slice](../../delivery/swap-booking-alpha.md), [creation](../../../apps/reference_api/swap_creation.py), [booking](../../../apps/reference_api/generic_swap_booking.py).

## Read-only contractual inspection — 14 October 2026

F15/F43 now expose approved structured-product Terms & Schedule and swap-reference look-through from instrument details. Note/share layers retain distinct dates; missing swap dates remain explicit. See [delivery and verification](../../delivery/instrument-terms-schedule-2026-10-14.md). Current lifecycle/valuation capability status is unchanged.
