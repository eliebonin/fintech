# Yahoo GBP FX backfill — personal research

## Scope and conventions (2026-10-08)

Relevant fiat currencies for the imported S&P 500 / CAC 40 listings are USD and
EUR; GBP is the reporting currency and needs no downloaded GBP/GBP series.
Cryptoassets/stablecoins and synthetic test currencies are not fiat FX and are
outside this import. Direct Yahoo symbols EURGBP=X and USDGBP=X mean **GBP per
unit of foreign currency**; rates are not inverted, triangulated or assumed 1:1.

Three separate FX_SPOT / RATE / RAW series per pair:

- EOD: provider daily close, no named valuation cut. Yahoo's daily bar timestamp
  is retained as supplied; it is not evidence of a London/New York fixing time.
- UK: exact five-minute close from the bar ending at 16:00 Europe/London.
- US: exact five-minute close from the bar ending at 16:00 America/New_York.

Time-zone rules handle DST and differing UK/US changeover dates. A 15:55 bar
ending at 16:00 is eligible; a bar starting at 16:00 is not. Source timestamp and
bar-end economic timestamp are retained separately. No nearest-bar substitution,
carry-forward, interpolation, fabricated holiday rate or current-day close.
Missing source values/cutoff bars remain explicit ingestion rejections.

These are **Yahoo research snapshots, not official benchmark fixings**. They use
dedicated cuts YAHOO_RESEARCH_UK_1600 and YAHOO_RESEARCH_US_1600 and no benchmark
fixing code. Existing synthetic series/policies are untouched.

## Source checks

- [yfinance maintainer documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.functions.html)
  gives a general 60-day intraday limit. The
  [maintainer's implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py)
  distinguishes hourly data (730 days) from five-minute data (60 days); live probes
  confirmed hourly availability. Five years of daily FX history can be requested,
  but five years of cutoff history cannot be reconstructed from daily closes.
  Five-minute cutoffs start 59 days before receipt; hourly cutoffs start 729 days
  before receipt to stay within the rolling retention boundary.
- [LSEG WMR FX benchmarks](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks)
  describes London 4pm benchmark rates as validated market-transaction benchmarks.
  A Yahoo five-minute sample is not that product or its methodology.
- A live Yahoo probe returned CURRENCY / CCY / GBP / Europe/London metadata and
  daily/five-minute bars for EURGBP=X. Every subsequent delivery independently
  validates its exact symbol, quote currency, type, timezone and interval.

## Storage, permissions and operation

New provider product PUBLIC_CHART_FX and dataset YAHOO_PERSONAL_FX_GBP; same Yahoo
personal provider, separate source namespace and shared non-tradable FX pair
references. Base/quote currencies and sampling semantics are explicit dimensions.
The recorded personal declaration/research exception is reused via dataset-specific
assignments, not misrepresented as Yahoo consent or a commercial licence.
Only ACQUIRE, STORE and DISPLAY evidence is copied; tenant purpose remains
INTERNAL_REPORTING. No VALUATION, NON_DISPLAY, redistribution or commercial access.
An inactive/revoked profile is not automatically reactivated.

FX publishing is separate from the equity PRICE publisher. Both use retained raw
payloads and rights evidence, serialized dataset writes, immutable observations,
idempotent replays and linked corrections. The existing fetcher supplies the same
headers, size/timeout limits and bounded exponential 429 retries. No transaction
is held while fetching, spacing requests or backing off. Jobs and attempts are
committed independently, including failure/partial results.

```powershell
.venv/Scripts/python.exe scripts/ingest_yahoo_fx.py --apply --acknowledge-personal-access --start 2021-10-08 --through 2026-10-07
```

Without --apply catalogue changes roll back and no Yahoo requests are made.
The command is restricted to the local personal fortem_secm database on port 54329.
Requests are serial, spaced five seconds by default. Partial source coverage has
a nonzero exit code and must not be described as complete valuation-ready data.

## Verification / execution

Completed on 2026-10-08: **2,770 accepted current observations** in six series.

| Pair (GBP per foreign unit) | Provider EOD | UK 16:00 snapshot | US 16:00 snapshot |
| --- | ---: | ---: | ---: |
| EUR/GBP | 1,299 | 43 | 43 |
| USD/GBP | 1,299 | 43 | 43 |

EOD spans 2021-10-08 through 2026-10-07. Cutoff snapshots span 2026-08-10 through
2026-10-07. All 12 pair/series/date combinations for October 6 and 7 were verified
in the operating database. Every observation has retained source-payload evidence.

Yahoo returned null daily values for both pairs on 2025-01-01, 2025-04-18,
2025-04-21, 2025-12-25 and 2026-01-01. Those ten source gaps are retained as
rejections, not invented/forward-filled values; daily jobs therefore remain PARTIAL.
This is not an independently certified FX holiday calendar or coverage signoff.
Both cutoff jobs returned COMPLETE for all 43 weekdays in the requested interval.

The USD daily request returned Yahoo's canonical GBP=X alias, with longName
USD/GBP and quote currency GBP. A regression test requires that exact combination;
reversed pairs are rejected. The retained failed USD delivery was reprocessed
under normalizer v1, preserving the original rejection/run and linking the new
operational attempt to it. No second USD-history download was needed.

Dataset UUID: `01a11cdb-8a1b-7dfd-ac86-2e0a4b4c31cd`. The signed-session metadata
endpoint confirmed six FX_SPOT/RAW series, INTERNAL_REPORTING only, and no
NON_DISPLAY or valuation-use coverage. API restarted to load the FX rights scope.

57 focused tests passed across FX normalization/publishing, existing Yahoo
fetching/normalization and layered rights. Tests cover the cutoff/look-ahead
boundary, missing bars, DST divergence, wrong direction/type/currency, canonical
alias, permission limits, repeated setup/delivery and immutable corrections.
The additional hourly test checks the bar ending at the cutoff and separate
hourly/five-minute series identities, preventing overwrite of existing definitions.
Python compilation passed. No full suite or browser click-through was performed.

This does **not** implement FX conversion in valuation, authorize valuation use,
certify prices/benchmarks or change saved policies. Cryptoassets/stablecoins are
excluded explicitly, not substituted by pegged fiat rates.

## Two-year cutoff extension

On the user's subsequent request for two years, the hourly Yahoo feed was probed
successfully and an hourly-sampled UK/US backfill was completed. It uses the same
16:00 local business cuts but separate immutable series, identified by
EXACT_COMPLETED_1H_BAR_AT_LOCAL_CUTOFF and SAMPLING_INTERVAL=1h. Existing
EXACT_COMPLETED_5M_BAR_AT_LOCAL_CUTOFF series remain unchanged. Select an explicit
series when configuring a later policy; do not assume different sampling intervals
are identical simply because their business cutoff matches.

```powershell
.venv/Scripts/python.exe scripts/ingest_yahoo_fx.py --apply --acknowledge-personal-access --cutoff-only --cutoff-interval 1h --start 2024-10-08 --through 2026-10-07
```

The effective hourly request starts 2024-10-09 due to Yahoo's rolling 730-day limit
and ends 2026-10-07. Daily data already covers 2024-10-08 through 2026-10-07.

| Pair | EOD closes in requested two-year window | UK hourly cutoff | US hourly cutoff |
| --- | ---: | ---: | ---: |
| EUR/GBP | 517 | 518 | 519 |
| USD/GBP | 517 | 517 | 518 |

2,072 additional hourly-sampled cutoff observations were stored; total FX dataset
is now 4,842 current observations in ten series, including older daily history
and the original recent five-minute snapshots. No existing observations were removed.
The hourly job is PARTIAL because 12 pair/cut/date slots have no exact source bar:

- EUR/GBP: UK+US on 2024-12-25, UK on 2025-01-01, UK+US on 2026-01-01.
- USD/GBP: UK+US on 2024-12-25, UK on 2025-01-01, UK+US on 2025-12-25,
  UK+US on 2026-01-01.

These gaps are retained in immutable delivery reports, not filled with another
cutoff or prior day. They fall on holiday dates, but this importer does not itself
certify those dates as no-valuation days. The calendar/price-validation workflow
must explicitly decide that. Final SQL verification confirmed all ten series'
counts and ranges. Existing five-minute series and their original values remain.
An actual October 7 hourly re-import accepted zero new observations and reported
two duplicates per pair; dataset counts remained 4,842. The signed-session BFF
metadata endpoint exposed ten RAW FX series with unchanged INTERNAL_REPORTING
permissions. All FX jobs were terminal (zero RUNNING jobs) at handoff.
