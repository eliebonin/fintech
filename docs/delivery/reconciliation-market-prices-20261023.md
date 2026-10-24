# Private reconciliation market prices — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

**Status:** Implemented and locally activated; inspection is not valuation sign-off  
**Content type:** Delivery record  
**Owner:** Market-data engineering and data operations  
**Last reviewed:** 2026-10-23

Subsequent setup: [personal valuation eligibility](reconciliation-valuation-eligibility-20261023.md)
adds a separate owner instruction and FCAGF policy. The original 884 observations
and inspection-only import declaration below remain retained; 24 explicitly
normalized forward-rate observations now coexist for engine-compatible labeling.
This does not constitute upstream/commercial clearance or price-validation sign-off.

## Scope and result

The owner requested import of the supplied FCAGF market-price export. All **884
observations across 42 native references**, on **22 supplied dates from 21 September
through 20 October 2026**, are now stored in tenant one's private dataset:

**FCAGF — imported daily market prices**  
Dataset `01a168e1-2420-7973-a9d4-55ad1e0de59e`.

The [adapter](../../tooling/reconciliation_csv/reconciliation_prices.py) is isolated under tooling/reconciliation_csv,
not the API or generic file parser. The existing guarded local
[operator](../../tooling/reconciliation_csv/seed_reconciliation_bundle.py) adds
`--market-prices --prices-operator <explicit-personal-operator-organisation>`.
This is a bounded reconciliation import, not a new public upload workflow.

## Mapping and normalization

| Source family | Series / measurement | Stored convention |
| --- | --- | --- |
| 10 bonds | CLOSE / PRICE | 211 CLEAN fractional quotes ×100 into percentage of par; divisor 100; nominal quantities unchanged. Source bond metadata declares CLEAN. |
| 1 AMC | CLOSE / PRICE | UNIT_PRICE, divisor 1; no extra denomination or percentage conversion. |
| 13 swaps | MARK / PRICE | Whole-swap MTM per unit or per nominal, explicitly distinguished; negative values retained; no extra leverage multiplication. |
| 1 SPX option | CLOSE / PRICE | Premium points unchanged; multiplier 100, contracts; correct standard-contract canonical node. |
| 2 FX forwards | FORWARD_RATE / FX_RATE | GBP per USD, no inversion; quote currency GBP; outright contract rate, not contract MTM. |
| 13 performance indices | INDEX_LEVEL / INDEX_LEVEL | Supplied index points unchanged, not security prices or automatic percentage returns. |
| SOFR and SONIA | RATE / RATE | Supplied annual percent units unchanged (e.g. 3.9 remains 3.9, not 0.039). |

Native mapping comes from owned, bundle-bound creation/preparation/posting audit
evidence, not coincidental numeric IDs or names. Conflicting, missing, inactive or
other-tenant targets block the whole transaction. Node scope is checked in a batch,
not once per observation. Native product/currency and forward orientation checks
protect quotation identity. The corrected standard-option posting audit overrides
the earlier multiplier-one mockup creation mapping; **no price is attached to the
inactive placeholder**. Series are attached to the mapped canonical reference;
this does not implement future option listing/canonical valuation fallback.

Every selected row was independently compared to the source CSV using Decimal
conversion and truncation toward zero. **Five values needed precision truncation**;
original text, exact converted value, stored value and delta are retained in the
ingestion report. Original CSV bytes, hash and private receipt stay unchanged.
No interpolation, inferred zero, missing-date fill, split adjustment or synthetic
price was introduced. No original source rows were discarded.

## Timing, provenance and rights

The source supplies dates only. Observations use
`SOURCE_DATE_ONLY_EOD_BUCKET` and a 23:59:59.999999 UTC applicability bucket, not an
assertion of real quote/publication time. Named cut, upstream source timestamp and
publication timestamp remain null. Current database receipt time is retained;
historical availability is not backdated. These are not certified exchange closes,
UK/US fixings or official benchmark observations. RAW identifies the provided quote
basis after unit conversion, not independent proof of an upstream vendor's entire
adjustment methodology. ACCEPTED is structural acceptance, not financial validation.

The explicit local personal operator is a delivery/declaration identity, not the
inferred upstream data owner. As with the prior private FX import, retained
PERSONAL_DECLARATION covers **ACQUIRE/STORE/DISPLAY** and tenant-one
INTERNAL_REPORTING only. **No NON_DISPLAY, VALUATION, commercial or redistribution
rights are added**, and no provider priorities or policy versions are changed.
The original manifest's possession-is-not-licensing warning remains intact.
Revoked/changed governance is refused on replay, not silently restored.

The delivery contains original rows and a frozen native-ID map. Exact replay
returns the original ingestion run without duplicate series/observations. A changed
target map for this dataset requires explicit correction, not a second silent
delivery of identical source rows to different contracts. Caller owns the entire
transaction, including evidence and import audit.

## Verification and operational evidence

**15 focused tests passed in 22.87 seconds**, covering the price adapter, existing
FX/private-rights behavior, corrected option mapping, Decimal precision and naming
policy. Final price/option adapter rerun passed **4 tests in 14.65 seconds**, recorded in
`logs/reconciliation-prices-final-tests.log`; earlier evidence is
`logs/reconciliation-prices-tests.log`. Tests use owned disposable databases, never
the operating database. No full suite or browser acceptance is claimed.

Operating results: 884 observations, 42 series, 22 dates; exact normalized-source
match; corrected option target; denied cross-tenant display and no NON_DISPLAY
grant. Series counts: 12 CLOSE, 13 MARK, 13 INDEX_LEVEL, 2 RATE, 2 FORWARD_RATE.
Replay returned `replayed=true`, with the same dataset and counts. The source API
returned the new dataset for tenant one. No migration or restart was necessary.
Evidence: `logs/reconciliation-prices-apply.log` and
`logs/reconciliation-prices-replay.log`.

FCAGF remains at **78 investment trades**. No trades, cash snapshots, accrued
inputs, coupon payments, source FX values or Yahoo prices were changed by this
import; no valuation was run or published. Inspect in existing Market Data
Sources / Explorer. Remaining work includes price validation, appropriate
valuation-use evidence and policy coverage, unresolved RESET references, and
unsupported swap/option daily-valuation behavior. This is complete source-price
storage, not complete portfolio reconciliation or valuation readiness.
