# Mock bond valuation inputs — 15 October 2026

**Status:** User-requested local app data populated; one valuation completed and staged, not published.

This extends the [visible mock strategy/opening trades](mock-bond-strategy-app-seed-20261015.md). No existing real source, shared policy, trade, permission grant, cash balance or published financial result was modified.

## Reproduce in the UI

- Tenant: **Platform Demo Tenant**.
- Strategy: **MOCK — Bond valuation cycle (GBP)**, `07ac7abf-7477-4756-90bc-ff254130febd`.
- Policy: **MOCK bond EOD - synthetic only · MOCK_BOND_PRICES_20261015 · v2**.
- Opening date: **2026-09-29**; closing date: **2026-09-30**; reporting currency: **GBP**.
- Information cutoff: leave blank/use current submission time. Synthetic source, policy and interest evidence were recorded today, not on the historical market dates.
- Result: **500 market P&L + 10 daily interest = 510 gross/net P&L**, closing clean position value 99,000. No coupon is added again and no cash/NAV is inferred.

## Seeded facts and boundaries

[Explicit synthetic artifact](../../data/mock-bond-prices-20261015.json), [preview/apply script](../../scripts/prepare_mock_bond_valuation.py).

| Market date | CLEAN price per 100 nominal, RAW |
| --- | --- |
| 2026-09-29 | 98.50 |
| 2026-09-30 | 99.00 |
| 2026-10-01 | 100.00 |

The last mark is available for a later lifecycle exercise; it does not close the matured holding. No maturity redemption is booked by this setup. Use September 30 for the verified initial valuation. October 1 is not signed off here as a complete maturity/coupon case.

Position-level assessed daily interest of 10 GBP is recorded for September 30 and October 1 using the existing API and immutable revisions/request keys. This is deliberately illustrative, not a generated contractual accrual. Optional accrued-stock balances are not supplied: their reconciliation/receivable-FX assessment remains unassessed, not zero. Coupon schedule/receipt and cash snapshots are not prerequisites for this supported economic-P&L example and are not fabricated.

New provider/product/dataset are explicitly MOCK ONLY, with tenant-one provider ownership and a PERSONAL access profile restricted to that tenant. A self-created synthetic-data declaration covers acquire/store/display/non-display; no third-party permission, commercial clearance, redistribution or user action grants are invented. Both VALUATION and INTERNAL_REPORTING dataset entitlements are local to this new mock dataset. The licence parties are the owning organisation itself, not Yahoo or an exchange. Effective business coverage is historical; the actual source receipt, vintage, payload and declaration evidence are recorded now.

Source payload retains the artifact URI and SHA256; vintage and observations retain payload/licence identities. The series is `CLOSE/RAW`, `BOND_PRICE_TYPE=CLEAN`, `PROVIDER_DEFINED`, not exchange-official. Historical observation instants are explicit simulated 16:30 London marks; publication/receipt are current. The existing sealed `XLON_TRADING_2026` calendar supplies dated business-session coverage; it is not modified or represented as an actual OTC exchange listing.

The strategy-specific STRICT policy names this exact bond/series/dataset, requires AS_TRADED/RAW, has zero permitted staleness, and uses EXPLICIT_TIME with a dedicated London 16:30 cut. No other strategy receives this policy by default.

## Evidence and setup corrections

- Policy v2: `01a13eb7-5f34-73bc-912f-df15dd8df3fa`.
- Dataset: `01a13eb6-678e-7ce7-a5bc-037e3c496258`; series: `01a13eb6-67d1-7ef3-8c46-f4c7fe18145a`.
- Successful attempt: `01a13eb7-b32a-726a-9309-ccca0fc00af3`; staged batch: `01a13eb7-b3fa-7f05-8b61-f18f6aa5a053`.
- Initial setup v1 used SESSION_CLOSE on an OTC canonical bond. The resolver correctly blocked it with `EXPLICIT_PRICING_LISTING_REQUIRED`; failed attempt `01a13eb6-6b41-7658-a173-6e6361e104d9` has no financial batch. V2 corrects that configuration, not the resolver.
- An attempted status retirement of this new v1 was rejected by the managed-policy immutability trigger and rolled back. The script no longer attempts it. V1 remains retained and visible; explicitly select **v2**. No trigger was bypassed, row deleted or historical policy edited.
- Normal valuation API execution and read-back confirmed COMPLETED/STAGED and the hand-calculated financial result. No publication/review bypass or full regression suite was involved in this data-provisioning task.

```powershell
.venv/Scripts/python.exe -B scripts/prepare_mock_bond_valuation.py
.venv/Scripts/python.exe -B scripts/prepare_mock_bond_valuation.py --apply --calculate
```

The script restricts its target to the named local database, uses scoped authority checks, stable keys and conflict rejection for pre-existing differing prices. The staged run is a real retained mock valuation in the app database, unlike the earlier disposable acceptance scenario. Its input dates/prices are invented and must not be used as real market evidence.
