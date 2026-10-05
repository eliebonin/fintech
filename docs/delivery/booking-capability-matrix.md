# Instrument creation and trade booking capability matrix

**Status:** Current alpha capability reference

**Owner:** Engineering delivery team

**Last reviewed:** 2026-10-05

Creation, listing and booking are separate capabilities. An approved instrument is not automatically bookable. This matrix supersedes scattered historical scope summaries for navigation; product delivery records still supply detailed evidence and restrictions.

| Product | Creation / reference setup | Listing | Booking alpha |
|---|---|---|---|
| Listed cash | Governed canonical instruments, including tenant-private requests | Separate listing attached to canonical instrument | Eligible listing-backed cash executions; derivatives/bonds use dedicated tickets |
| Deliverable FX forward | Currency pair and contract dates/terms | Not needed by the FX ticket | One trade: base quantity, agreed quote/base rate and term-derived settlement; no NDF support |
| Listed option | Canonical option terms and supported approved quotation conventions | Required | Integer contracts, OPEN/CLOSE intent, premium conversion and immutable option snapshot; supported fixed deliverables/underlyings only |
| Structured security | Governed canonical structured product and approved unit/nominal convention | Listed route requires one; OTC route does not | Listed or OTC security booking; OTC requires counterparty. ISIN does not decide execution route |
| Future | Governed family → canonical expiry; family conventions, month/year encoding, currencies and multiplier facts | Required by current booking alpha | Conventional cash-settled index outright futures, integer contracts, ticks/cutoff and monetary multiplier. Physical/crypto creation does **not** enable physical/crypto booking |
| Bond | Canonical bond terms and approved convention/source evidence | Listed route uses listing; OTC route does not | Nominal, CLEAN/DIRTY basis, signed accrued interest and evidence; dirty consideration includes accrual already |
| Swap | Generic funded/performance reference, optional funding reference, spread/notional/return/leverage/reset/redemption and approved whole-swap quote; legacy supported reference swaps remain readable | Not required; current generic ticket is OTC | Editable booked nominal independent of contractual nominal, signed/zero quote, counterparty and saved terms; no double leverage or automatic cash entry |

Common booking controls apply to all seven paths: current active writer authorization, new-write tenant strategy checks, endpoint-scoped replay, writer-owned atomic savepoint, governed properties/parties, retained reviewed submission and BFF stale-tenant protection. See [shared controls](booking-controls.md) for exact compatibility exceptions and locking limits.

After booking, live tenant-scoped trade history/detail displays saved economics and annotations with append-only BOOKED evidence. OPEN/CLOSE is intent, not inventory or lot validation. No automatic settlement, exercise, expiry, redemption, reset, coupon/dividend, cash posting or correction workflow is implied. Valuation/P&L remains a separate workstream.

## Product references

- [Cash and enriched annotations](enriched-trade-booking-alpha.md)
- [FX forwards](fx-forward-booking-alpha.md)
- [Listed options](listed-option-booking-alpha.md)
- [Structured securities and futures](structured-security-and-futures-booking-alpha.md), [current futures creation conventions](futures-creation-and-contract-conventions-alpha.md)
- [Bonds](bond-booking-alpha.md)
- [Generic swaps](generic-swap-creation-and-booking.md), [legacy swap slice](swap-booking-alpha.md)
- [Trade history](trade-history-alpha.md), [governed configuration](governed-trade-configuration-alpha.md), [agreed lifecycle limits](booking-and-lifecycle-scope.md)

Next hardening should address authoritative instrument amendment/versioning and post-booking corrections/lifecycle boundaries separately. Do not expand this consolidation into valuation or an unrestricted derivative engine.
