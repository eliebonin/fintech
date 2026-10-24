# Private reconciliation FX import — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

Subsequent setup: [personal valuation eligibility](reconciliation-valuation-eligibility-20261023.md)
records a separate local personal-use instruction and strategy policy. The
original inspection declaration and all 4,620 rates remain unchanged. No real
UK/US fixing, provider contract or commercial clearance is asserted.

**Status:** Implemented; local activation evidence below. No full valuation sign-off.

## Scope

The owner requested 10–15 likely currencies from the supplied FX export, added
to the existing datasets. The file contains 16 fiat currencies and XAU, with a
complete dated matrix on 22 supplied dates, 21 September–20 October 2026.

Selected 15: **GBP, USD, EUR, JPY, CHF, CAD, AUD, NZD, SEK, NOK, DKK, SGD, HKD,
INR, KRW**. These retain the strategy's actual GBP/USD/EUR/SGD currencies plus
the available major developed-market currencies and Asian crosses. This is an
operator relevance choice, not a claim of a globally ranked turnover universe.
XAU and ILS are excluded from this batch, not deleted from the original file.

210 directed non-identity pairs × 22 dates = **4,620 source observations**.
All 14 selected currencies versus GBP supply 308 of those observations.
Identity rates are checked to equal one and omitted; same-currency conversion
already uses identity. No inversion, triangulation, synthetic fill, missing-date
zero, interpolation or carry-forward. Both directions retain their own supplied
rounded rates; they need not be exact reciprocals.

## Storage, evidence and timing

- [Adapter](../../tooling/reconciliation_csv/reconciliation_fx.py) is isolated under tooling/reconciliation_csv;
  [guarded local operator](../../tooling/reconciliation_csv/seed_reconciliation_bundle.py) adds
  `--fx-rates --fx-operator <explicit-personal-operator-organisation>`.
- A separate tenant-private FILE provider/product/dataset is labelled
  **FCAGF — imported daily FX (15 currencies)**. Public currency-pair identities
  are reused rather than duplicated. New fiat references fill only the missing
  NZD, SEK, NOK and DKK entries. Existing Yahoo series/observations are unchanged.
- Original CSV bytes/hash/source receipt remain retained. A finalized ingestion
  run holds the exact selected-row JSON delivery, original receipt/hash, selected
  currencies and any authorized precision transformations. All selected actual
  source rates fit native precision without truncation.
- FX_SPOT/RATE/RAW series retain BASE_CURRENCY and QUOTE_CURRENCY explicitly:
  a rate converts one base unit into quote units. Source currency IDs, where
  supplied, must agree with the original source currency catalogue.
- The export supplies **dates only**, not a fixing or publication timestamp.
  `TIMESTAMP_SEMANTICS=SOURCE_DATE_ONLY_EOD_BUCKET`; observed_at is a conservative
  23:59:59.999999 UTC applicability bucket, not an assertion of actual quote time.
  Named cut, upstream source timestamp and source publication time remain null.
  Receipt time is the current database time, never a historical market date.
  These are not invented London-close, New York-close, official or benchmark rates.
- Positive/finite/range/precision and duplicate pair/date checks precede writes.
  Publication is one transaction; delivery-key/content replay is immutable.
  Changed or removed governance is refused, not automatically repaired/reactivated.

## Rights boundary

The explicitly selected personal operator is a delivery/declaration identity, not
an inferred upstream content owner. The current owner instruction supports only
a retained **PERSONAL_DECLARATION for local file ACQUIRE/STORE/DISPLAY**, scoped to
tenant one and INTERNAL_REPORTING. It is not a provider contract or verification
of upstream ownership/licensing. No NON_DISPLAY, VALUATION entitlement, commercial
scope, redistribution, client-reporting rights or pricing-policy changes are added.
Normal current licensing and tenant display checks still apply; another tenant
cannot inspect these rates merely because pair references are publicly canonical.

Storage/inspection therefore does **not** establish valuation readiness. Proper
pricing/fixing conventions and any required use evidence remain separate review.

## Compatibility fix

A disposable regression reproduced this sequence: an entitled inverse rate
resolves; adding an inspection-only direct series then incorrectly shadows it
and fails with NO_MATCHING_POLICY_RULE. [FX subject discovery](../../valuation/fx.py)
now considers visible, currently and historically entitled, non-display-permitted
sources before choosing orientation. Eligibility follows each observation's actual
dataset, not the catalogue default. The full resolver still checks policies,
timing, calendar, freshness and explicit inverse permission. If no source is
entitled, normal resolver diagnostics are preserved rather than authorizing it.
This is not permission to substitute another fixing when an applied rule fails.

## Verification and activation

[Focused tests](../../tooling/reconciliation_csv/tests/test_reconciliation_fx.py) cover direct orientation,
identity/exclusion/duplicates, ID/code disagreement, native replay, canonical pair
reuse, denied cross-tenant display, no valuation-use grant, refusal to recreate a
removed display grant, date-only provenance and inverse-source compatibility.
The compatibility test fails against the earlier FX discovery and passes with
the scoped discovery change. Existing FX/rights/display/precision tests are run
in owned disposable databases, never the operating database. No full suite,
browser financial acceptance or complete source reconciliation is implied.

Local activation completed on 23 October 2026. Dataset
`01a168a5-da3a-71ea-a389-21103c718672` contains **210 series and 4,620 observations
on 22 dates**, including **308 GBP-quoted observations**. Independent database
readback compared every selected pair/date/value to the original CSV: exact match,
with no truncation. Replaying the same operator command returned `replayed=true`
and the same retained delivery. Operating read-only checks confirmed tenant-one
display, denied other-tenant display and no NON_DISPLAY permission.

**43 focused tests passed in 32.22 seconds**, covering reconciliation FX, existing
valuation FX, rights/display, precision and repository neutrality. Evidence:
`logs/reconciliation-fx-final.log`, `logs/reconciliation-fx-apply.log` and
`logs/reconciliation-fx-replay.log`. The API on port 8001 was restarted to activate
the compatibility fix and its health check returned OK. No migration was required.
Inspect through the existing market-data sources/explorer pages in tenant one;
no new public upload UI or browser acceptance is claimed.

The private reconciliation ledger remains authoritative for other unposted
prices, investment rows and unresolved RESET references.
