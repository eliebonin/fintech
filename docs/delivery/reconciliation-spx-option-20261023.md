# Private SPX option reconciliation — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

**Status:** Implemented and locally activated; option valuation not signed off  
**Content type:** Delivery record  
**Owner:** Trading and security-master engineering  
**Last reviewed:** 2026-10-23

## Owner-confirmed economics

Source execution `20260813113427-260b02154d607d4707d3`, instrument `20265`,
`SPX.202612.P.05800000`, incorrectly embeds the option multiplier in quantity.
The owner confirmed the correction: **2,000 source units / 100 = 20 contracts**,
premium **23.8 points**, premium multiplier **100**, gross premium **USD 47,600**.
Strike 5,800; expiry 18 December 2026; execution 13 August 2026 at 11:00 UTC;
source premium settlement 14 August. Original CSV bytes/rows stay unchanged.

## Implementation boundaries

[Bounded adapter](../../tooling/reconciliation_csv/reconciliation_option.py) and local operator
flag `--book-spx-option` use existing option proposal/approval, listing
proposal/approval and native option booking. No direct trade-table inserts,
validator relaxation, automatic cash balance, lifecycle event or valuation run.

The earlier multiplier-one source-normalized placeholder remains retained with
its original terms. It must have no bookings and is made inactive/untradable only
after a properly normalized standard-contract booking succeeds. The new retained
`RECONCILIATION_OPTION_BOOKED` audit is the authoritative source-instrument mapping
for subsequent market-price import; the older creation audit still records the
historical placeholder and must not reactivate or override it.

Canonical contract and listing use premium multiplier/deliverable units 100,
quote divisor 1, USD premiums. Quantity normalization is exact and rejects
fractional contracts; premium is unchanged, never divided/multiplied by 100 again.
Native premium must equal original source units × source premium. Source identity,
normalization, old/new instrument IDs, listing, original execution row and both
file receipts remain retained. Source-scoped idempotency and the native writer
prevent duplicate trades. Current tenant/strategy/reference authority is checked
before preparation and replay; source files must match retained hashes.

## Reference conventions and disclosed assumptions

Reviewed on 23 October 2026:

- [Cboe SPX specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications):
  multiplier 100, European exercise, cash settlement and standard monthly
  expiration trading cutoff on the preceding business day, ordinarily Thursday,
  at 17:00 New York time. For this dated seed, 17 December 2026 at 22:00 UTC.
- [Cboe venue codes](https://www.cboe.com/markets/us/options/trading/codes):
  **XCBO** is Cboe Options, not the preexisting BATS equities venue. A missing XCBO
  reference is added with source audit; no exchange calendar is fabricated or
  borrowed from an equities venue. Venue/session valuation readiness is separate.

Standard monthly **AM settlement is inferred** from the SPX label and third-Friday
expiry, not independently broker-confirmed. OPEN is inferred from the sole
supplied option execution, not a comprehensive account-position reconstruction.
XCBO is the contract venue; the export does not independently certify the actual
execution venue. The source label is an internal listing symbol, not a verified
OCC/provider alias. These are disclosed journey-test assumptions, not certified
contract master or accounting acceptance. No production authentication is implied.

## Verification and activation

[Tests](../../tooling/reconciliation_csv/tests/test_reconciliation_option.py) exercise exact premium
preservation, integer contract rejection, superseded placeholder retention,
approved native listing/booking, replay and denied cross-tenant use. Final local
activation and readback evidence follow.

**19 focused tests passed in 10.88 seconds** (adapter, existing product mapping,
option rules and repository neutrality). Final two-test adapter rerun passed
**2 tests in 4.53 seconds**, retained
in `logs/reconciliation-option-final-tests.log`; broader focused evidence is
`logs/reconciliation-option-tests.log`. No full suite or browser acceptance.

Operating activation:

- Trade: `fd7e197c-3799-45ca-aa75-6d81c1907ab0`.
- Correct canonical option: `01a168c7-7441-7c86-9bd9-8279e37a919c`.
- Approved listing: `01a168c7-7629-7b76-bdc5-275497ff74a9`.
- BUY / OPEN, 20 CONTRACTS, 23.8 premium points, multiplier 100, USD 47,600 PAY.
- Original 2,000.0 source quantity and complete source row match retained audit;
  old mockup retains multiplier-one terms but is now inactive and untradable.
- Replay returns the same trade; one source posting audit exists. FCAGF now has
  **78 investment trades**, matching all 78 supplied investment executions.
- Native frozen option economics were independently read back and checked.
  No migration or API restart required; API health remained OK.

Evidence: `logs/reconciliation-option-apply.log` and
`logs/reconciliation-option-replay.log`. The source price series, when imported,
remains in premium points: do not divide prices by 100 after quantity conversion.

Option booking support does not imply daily option P&L, exercise processing,
Greeks or full portfolio valuation coverage. Market-price import remains separate.
