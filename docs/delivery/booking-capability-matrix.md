# Instrument creation and trade booking capability matrix

**Status:** Current alpha capability reference

**Content type:** Capability reference

**Owner:** Engineering delivery team

**Last reviewed:** 2026-10-12

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

Booking searches now share a ready-first view, Show unavailable, backend refusal reasons and inspection links. Cash has read-only search/detail eligibility using the same validator as its writer. This is advisory instrument readiness, not a promise of execution eligibility; raw pagination and selected-date checks remain bounded by each product's existing support. See [readiness delivery and acceptance](booking-readiness-alpha.md).

After booking, live tenant-scoped trade history/detail displays saved economics and annotations with append-only BOOKED evidence. Supported alpha records can be cancelled or atomically replaced as record corrections, with mandatory reason, concurrency/replay controls and retained lineage. Unproved legacy records have cancel-only recovery. Historical writes use UTC dates, a built-in optional effective valuation date and current governance. See [trade operations](../product/features/trade-operations.md). OPEN/CLOSE is intent, not inventory/lot validation. No automatic settlement, exercise, expiry, redemption or income/cash posting is implied. A separate assessed economic-flow/accrual workflow now exists; it does not make every booked product valuation-ready. Current position reconstruction handles supported history conservatively; in-period correction economics and unsupported transformations remain blocking. See [current valuation scope](../product/features/valuation-and-pnl.md).

## Product references

- [Cash and enriched annotations](enriched-trade-booking-alpha.md)
- [FX forwards](fx-forward-booking-alpha.md)
- [Listed options](listed-option-booking-alpha.md)
- [Structured securities and futures](structured-security-and-futures-booking-alpha.md), [current futures creation conventions](futures-creation-and-contract-conventions-alpha.md)
- [Bonds](bond-booking-alpha.md)
- [Generic swaps](generic-swap-creation-and-booking.md), [legacy swap slice](swap-booking-alpha.md)
- [Trade history](trade-history-alpha.md), [governed configuration](governed-trade-configuration-alpha.md), [agreed lifecycle limits](booking-and-lifecycle-scope.md)

The [instrument integrity review](quality-reviews/2026-10-05-instrument-integrity.md) identified cash visibility/approval gaps, FX inactive-scope enforcement and older approval dependency revalidation. [FX active-scope checks](quality-reviews/2026-10-05-fx-scope-hardening.md) and [cash integrity plus FX/bond/ETP approval revalidation](quality-reviews/2026-10-05-cash-and-approval-integrity.md) are implemented; follow their delivery records for verification evidence and limits. Safe instrument amendments/versioning and contractual lifecycle remain separate; record corrections now have the bounded workflow linked above. Cash uses an explicit product allowlist, approved-date/factor checks and saved BOOKED definition/factor evidence. The shared controls do not imply universal instrument eligibility or production-readiness. Do not expand this hardening into valuation or an unrestricted derivative engine.
