# Listed option supplied-premium P&L — 23 October 2026

**Status:** Implemented bounded calculation support; not full option lifecycle or portfolio sign-off.

## Economics

For an unchanged position:

`signed contracts × frozen premium multiplier ÷ quote factor × (premium T × FX T − premium T−1 × FX T−1)`.

The shared signed execution bridge handles new trades and partial/full closures
using actual execution premiums and economic-day FX. Multipliers already embedded
in a source quantity must first be normalized at import, not applied twice. The
FCAGF SPX example is **20 contracts × multiplier 100**, not 2,000 contracts:
23.8 to 28 gives **8,400 USD** before reporting FX. No underlying index price,
strike or deliverable multiplier is multiplied into this premium P&L.

Zero is an allowed **supplied** entry/closing premium. Negative premiums and
fractional contract bookings are rejected; missing prices remain missing.
Equity positive-price guards and swap signed-mark behaviour remain unchanged.

## Evidence, price identity and controls

- [Premium conventions](../../security_master_schema/option_valuation.py) validate
  the original booking fingerprint, listed/canonical identities, frozen multiplier,
  quote factor, integer contract quantity, currency, gross premium and direction.
- [Native writer](../../apps/reference_api/option_booking.py) now retains compact
  definition, listing-definition and option-terms identities with valuation units.
  No API response contract or database schema changed.
- [Older-booking adapter](../../positions/option.py) recovers a **unique exact
  fingerprint match** among retained definition IDs. It never substitutes the
  current multiplier or rewrites an old BOOKED event. Conflicting explicit
  valuation metadata blocks; it is not ignored in favour of legacy recovery.
- Definition identity is established by the original hash, not by ordering an
  application approval timestamp against a DB transaction-start recorded time.
  The same-transaction import regression covers this distinction.
- This bounded slice uses the **canonical option contract's premium series**;
  ledger/result ownership remains the exact booked listing. It does not substitute
  underlying levels or infer a venue-specific best price. Native RAW CLOSE, MARK
  or SETTLEMENT premiums require matching `OPTION_PRICE_BASIS=PREMIUM_POINTS`,
  `PREMIUM_MULTIPLIER`, `QUOTE_FACTOR` and `QUANTITY_UNIT=CONTRACTS` dimensions.
  Contradictory dimensions block. Venue-specific cross-listing price selection is
  not added by this slice.
- Normal tenant/strategy authority, licensing, policy/provider ranking, price/FX
  dates, sealed calendar, information cutoff and freshness controls still apply.
  Contract-level premiums can use an explicit governed pricing cut; no exchange
  closing session or source publication time is fabricated.
- Staged lines retain `OPTION_CONTRACT_PREMIUM`, T/T−1 selected observations,
  multiplier/divisor and the shared value bridge. Staging does not publish.

## Lifecycle and remaining limits

No Black–Scholes/model price, Greeks, option monetary-measure preview,
inventory allocation, exercise/assignment, expiry closure or settlement/cash
posting is implemented here. Open exposure after expiry blocks pending Ops
lifecycle handling. An explicit expiry-day premium is not an automatic expiry
booking, and zero is never assumed because the date has passed.

This removes the listed-option calculation gap for the imported contract, not
the portfolio's separate market-data eligibility/policy/calendar work. No
operating source rights, trades, cash balances or policy versions were changed.

## Verification

[Arithmetic tests](../../tests/test_option_valuation.py) cover long/short, reporting
FX, new entries, full closures, zero/missing/negative premiums, divisor once,
integer contracts and post-expiry blocking.
[Frozen-evidence tests](../../tests/test_option_frozen_valuation.py) reject tampered
units, multipliers, identities, currency, gross amounts and position intent.
[Disposable PostgreSQL integration](../../tests/test_option_valuation_integration.py)
uses native booking, real policy resolution, new/older evidence formats and
retained staged results, including a zero premium and same-transaction import.
No full regression suite or independent financial/browser publication acceptance
is implied. No migration is required.

Verification results: **92 tests passed** in the final bounded disposable-DB run,
including existing BUY/SELL, zero/minor-unit quotation, historical booking and
snapshot replay checks plus swap regressions. A subsequent **25-test pure run**
also passed, including the additional hand-calculated partial-close case.
**Two repository neutrality checks** passed separately. The existing FCAGF SPX
trade was verified read-only as **20 contracts, multiplier 100, quote factor 1**,
with its original fingerprint matching. No event/trade payload was changed.

Local activation: API port **8001** restarted and `/health` returned `status: ok`.
No migration, operating valuation/publication or frontend restart was performed.
