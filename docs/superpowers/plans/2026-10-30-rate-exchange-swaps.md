# Native rate-exchange swaps

**Intent:** Keep each two-leg component as its own SWAP instrument, trade, issuer
price series, RESET attribution and P&L. Add the missing floating-versus-floating
variant, then finish the four pending FCPGF investment entries through native
approval and booking. Do not consolidate the two priced components.

## Design and rulings

- A domain-owned `RateSwapTerms` variant has two explicit opposing floating legs:
  governed rate reference, currency, positive contractual notional, signed spread,
  day count, observation/calculation evidence and reset/payment frequencies.
  Shared quotation, quantity basis, effective/maturity and source facts remain
  explicit. Partial bookings scale contract notionals; signed trade quantity is
  applied once. The current performance terms retain their original JSON shape.
- Existing `swap_definition_version` JSON and `swap_terms` support the variant;
  canonical `swap_leg` FUNDING rows represent both floating funding streams.
  CROSS_CURRENCY/INTEREST_RATE are existing categories. No schema migration or
  invented performance-return profile is necessary.
- Approval revalidates active visible references, currencies and day counts in
  deterministic lock order. Booking compares materialized legs with the approved
  variant and freezes complete terms. Whole-contract mark P&L reuses the existing
  quantity/quote/FX bridge; the legs are not repriced or multiplied again.
- Existing non-tradable private swap identities already own prices and RESET
  references. Provide guarded first-time completion through proposal approval:
  require the expected current definition, tenant ownership, SWAP type, no
  bookable terms/convention and no position executions. Append the approved
  definition and activate that identity, preserving earlier evidence. Never
  replace identities or rewrite price/RESET records merely to complete this import.
- Source-specific pairing and inference stay under optional reconciliation
  tooling. The exported USD companion quantities provide evidence for each
  USD-leg amount; source GBP quantities supply the booked basis. Retain separate
  source marks and disclose inferred scheduling/principal conventions. No
  automatic cash, income, principal exchange or curve-based pricer is added.
- The user describes the bond-side flow as income. Review the existing source
  completion assumptions and disclose the distinction; never rewrite old BOOKED
  evidence or treat income-only as confirmed total-return exposure.

## Execution

- [x] Pin terms, exact decimals, opposing legs, native creation/completion,
  approval revalidation, booking/retry/cancellation and whole-mark valuation with
  lightweight tests before implementation.
- [x] Add native terms and reference/materialization helpers below HTTP; adapt
  proposal, inspection, shared booking and immutable valuation parsing.
- [x] Add a rate-exchange choice on swap creation and readable two-leg terms on
  review/booking/detail. Preserve context transport and retained retry navigation.
- [x] Run focused backend/frontend regressions and contract generation/type-checks;
  verify independent component marks and tenant/authority boundaries.
- [x] Complete and book the four source contracts using native commands; reconcile
  all 383 position and 1,002 RESET rows. Preserve all existing series/flow identities.
- [x] Update capability records/register/map and delivery evidence; restart local
  API. No operating valuation publication, migration, commit or push is requested.

## Evidence and scope

See the [delivery and acceptance record](../../delivery/rate-exchange-swaps-20261030.md)
for focused test evidence, live posting counts, retained fingerprints and limits.

The [OpenGamma swap model](https://strata.opengamma.io/swap/) and
[swap loader conventions](https://strata.opengamma.io/trade_loader_swap/), reviewed
30 October 2026, separate legs, directions, currency/notional, payment schedules
and product versus trade. These support explicit two-leg terms; they do not
establish the missing contractual facts in the source export. Our bounded
supplied-mark workflow remains distinct from a rate-curve valuation engine.
