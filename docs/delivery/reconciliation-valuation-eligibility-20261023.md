# Imported reconciliation-data valuation eligibility — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

**Status:** Implemented and applied locally; market-data preflight passed, portfolio financial sign-off remains incomplete.

## Outcome and scope

Tenant one's FCAGF imported price and FX datasets now have explicit **PERSONAL
NON_DISPLAY** permission records and **VALUATION** coverage for present-day
reconciliation calculations of their historical dates. This records the owner's
project-chat instruction. It is **not** a provider contract, upstream ownership
assertion, commercial clearance, client-reporting or redistribution permission.
Unresolved upstream requirements remain conjunctive blockers. The original
inspection declarations and source observations were not rewritten.

The new strategy-specific policy is:

**Imported EoD — source date only (personal reconciliation) · v1**

- Policy: `01a16938-ecc5-72a6-9896-0dfba51ce0a5`.
- Code: `RECON_EOD_7d0ff97c3f144a4fb8043518813627a7`.
- Cut: `01a16938-ec90-7402-9b9d-1dab12ee5316`.
- Published calendar: `be50b010-d13f-44ab-9f2b-bfe9f77ca7f9`.
- Strategy: `7d0ff97c-3f14-4a4f-b804-3518813627a7`.

No existing DEFAULT_EOD/flexible policy, permission group, trade, cash balance,
accrual input or published valuation was changed. The API already reads current
configuration; no migration or service restart was required. Its valuation policy
choice endpoint returns the named version for the scoped strategy.

## Rules and timing

Six **STRICT**, dataset-bound rules select:

| Product scope | Price family | Dataset |
| --- | --- | --- |
| BOND | CLOSE / RAW, existing CLEAN quotation | Imported prices |
| ACTIVELY_MANAGED_CERTIFICATE | CLOSE / RAW with its explicit quote basis | Imported prices |
| OPTION | CLOSE / RAW contract premium with multiplier dimensions | Imported prices |
| SWAP | MARK / RAW whole-swap quotation | Imported prices |
| FX_FORWARD | FX_FORWARD / RAW, contract-specific outright rate | Imported prices, normalized label |
| FX_PAIR | FX_SPOT / RAW, declared base/quote direction | Imported FX |

Scopes matter: a broad first CLOSE rule would match swaps/forwards too and block
before their later rules. No broad unscoped pricing rule was used here.
Every rule uses SAME_DAY, zero permitted staleness and FAIL on missing data;
there is no inverse/spot substitution, carry-forward, fallback or invented zero.

The source supplies dates only. Its stored `23:59:59.999999 UTC` applicability
bucket and null publication/source-fixing times remain unchanged. The new cut
explicitly selects that **source-date EoD bucket**, not London/New York close or
an official benchmark. A separately published **UTC daily date-partition** calendar
covers every date in 2026, including weekends. It is not an exchange/holiday
calendar and is not assigned to any venue. Since every date is an available
bucket, an absent requested-date observation fails rather than masquerading as a
holiday and carrying a prior mark. Existing real exchange/fund calendars remain
untouched. Full source-time/publication certainty is still unavailable.

New permission declarations are recorded/effective now. Historical **economic-date
coverage** starts at the supplied observations, 21 September 2026; this is not a
claim that permission or information was held at that earlier date. Information
cutoffs still cannot see data before its actual recorded receipt.

## Forward-rate metadata normalization

The original import used `FORWARD_RATE`/`CONTRACT_OUTRIGHT_RATE`; the established
valuation contract uses `FX_FORWARD`, `RATE_BASIS=FORWARD_OUTRIGHT` and an explicit
maturity. Two normalized series retain **24 identical scalar observations**,
correct base USD / quote GBP, and maturity from validated frozen bookings.
No agreed/execution rate, quantity, sign, currency direction or source numeric
value was changed. These are identity quotation-label normalizations, not a
new pricing model or replacement by spot FX.

Original series/observations remain available. New ingestion evidence links every
normalized observation to its original ID and records normalization availability
now, without manufacturing a vendor publication timestamp. The private price
dataset therefore has **884 original + 24 normalized observations = 908**, across
44 series on the same original 42 references. FX remains **4,620 observations**
and 210 directed-pair series. A changed source history requires an explicit
normalization revision; rerunning does not silently overwrite it.

## Implementation and replay controls

[Source-workflow orchestration](../../tooling/reconciliation_csv/reconciliation_eligibility.py)
reuses native policy creation, calendar publication and market-data retention.
It lives outside the isolated ingestion core; no HTTP dependency was added under
`market_data`. [Local operator](../../tooling/reconciliation_csv/prepare_reconciliation_valuation.py)
requires explicit tenant/actors/source/strategy/dataset IDs and attributable
personal instruction. It defaults to transaction rollback; `--apply` is explicit
and restricted to the named local workspace database.

Authority and provenance checks include tenant/strategy write/run permissions,
platform calendar-publication authority, verified source ownership, matching
retained import audit, private provider ownership, personal dataset profile and
current acquire/store/display rights. Declaration/rights/policy changes and audit
are in the caller's transaction. Replay validates rather than recreating revoked
grants, missing declarations, removed normalized inputs or inactive policy/cut/
calendar records. It never grants commercial or redistribution use or changes
provider ranking to force selection.

## Verification and next blocker

**43 focused disposable-DB tests passed**: eligibility, original imports/replay,
source precision, layered rights and derivative arithmetic. **11 boundary tests**
passed, preserving ingestion isolation and below-HTTP financial contracts.
[New tests](../../tooling/reconciliation_csv/tests/test_reconciliation_eligibility.py) exercise actual native
imports, policy resolution, forward-rate selection, original-row preservation,
denied other-tenant/commercial/redistribution use, unresolved upstream layers,
revocation-safe replay and changed-source refusal. No full suite was run.

The first operating-database rehearsal rolled back all setup. A second rollback
preflight for **19–20 October 2026** passed the price and FX selection stages,
then stopped at:

`Missing assessed daily accrued-interest input for UKTB 0 03/01/27 on 2026-10-20`.

Subsequent owner clarification: assessed accrual is not universally mandatory.
[Optional-accrual delivery](optional-bond-accruals-20261023.md) removes this blanket
blocker for new default requests, retaining an explicit omission warning and
strict-coverage opt-in. The preflight above is historical evidence, not a claim
that new default calculations still require this input.

Bond `01a167f6-aca0-7627-b667-61a963218032` / source `20484` is the next separate
financial-input issue. No zero daily income was invented to bypass it; its
zero-coupon/discount-accretion convention and source coverage need review before
completing the strategy reconciliation. Nothing was staged or published by the
preflight. The subsequently committed setup was checked read-only: personal
NON_DISPLAY allowed, commercial/redistribution denied, and the policy visible
through the API. Independent numerical/financial acceptance remains outstanding.
