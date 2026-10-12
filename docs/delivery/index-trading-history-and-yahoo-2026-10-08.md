# Public-universe booking history and October 7 Yahoo update

## Scope and decision

Requested: import October 7, 2026 Yahoo EoD observations for the seeded S&P 500
and CAC 40 universe, and remove the artificial October 6 onboarding boundary
for historical trade booking using assessed trading-start dates. Reference-only
maintenance: no operating trades, cancellations or valuation runs are created.

The universe remains the **October 6 constituent snapshot**, not a claim of
historical index membership. It contains 503 S&P equity share classes and 40
CAC listings (543 instruments and 543 listings), shared across tenants.

## Research and uncertainty

Yahoo `firstTradeDate` from already-retained five-year chart responses is
available for every listing. It is a **provider-history estimate**, not a verified
IPO date and not evidence of uninterrupted current ISIN, ticker or venue
identity. Shorter/truncated histories can give conservative dates later than
actual inception. Examples: TotalEnergies starts at 2000-01-03 in provider
metadata; URW starts at 2023-04-14. These are not asserted to be their IPO dates.
Do not invent an earlier date merely because the corporate entity is older.

Recent spin-offs demonstrate why first provider trading date is not always
the start of the ordinary listing. Primary issuer/exchange/SEC evidence is
used for these regular-way overrides, excluding preceding when-issued trading:

| Symbol | Regular-way start | Primary evidence |
| --- | --- | --- |
| CEG | 2022-02-02 | [Constellation launch](https://www.constellationenergy.com/news/2022/constellation-launches-as-largest-u-s--clean-energy-company-afte.html) |
| GEHC | 2023-01-04 | [SEC annual report](https://www.sec.gov/Archives/edgar/data/1932393/000193239323000025/gehc-20221231.htm) |
| GEV | 2024-04-02 | [GE Vernova stock information](https://www.gevernova.com/investors/stock) |
| SOLV | 2024-04-01 | [Solventum distribution terms](https://www.solventum.com/en-au/home/our-company/newsroom/press-releases/2024-03-08-3m-board-of-directors-approves-spin-off-of-solventum/) |
| SNDK | 2025-02-24 | [Nasdaq corporate action](https://beta.nasdaqtrader.com/TraderNews.aspx?id=ECA2025-38) |
| Q | 2025-11-03 | [SEC financial statement note](https://www.sec.gov/Archives/edgar/data/2058873/000205887326000015/R8.htm) |
| FDXF | 2026-06-01 | [Issuer annual report, item 5](https://ir.fedexfreight.com/financial-information/sec-filings/content/0001628280-26-053359/0001628280-26-053359.pdf) |
| HONA | 2026-06-29 | [Issuer completed spin-off](https://www.honeywellaerospace.com/us/en/company/newsroom/2026/06/honeywell-aerospace-spin-off-begins-trading-nasdaq) |
| VYLR | 2026-10-01 | [SEC distribution filing](https://www.sec.gov/Archives/edgar/data/2128626/000119312526409909/d115079d8k.htm) |

Additional spot checks found nine older when-issued/predecessor histories. A
separate, retained **lifecycle restriction** bundle excludes them:

| Symbol | Ordinary listing start | Primary evidence |
| --- | --- | --- |
| GOOG | 2014-04-03 | [SEC share-class history](https://www.sec.gov/Archives/edgar/data/1288776/000128877615000008/goog2014123110-k.htm): earlier GOOG quotes were Class A, not current Class C |
| DELL | 2018-12-28 | [Issuer stock information](https://investors.delltechnologies.com/stock-information): Class C replaces Class V tracking shares |
| CARR | 2020-04-03 | [SEC separation report](https://www.sec.gov/Archives/edgar/data/1783180/000178318021000011/carr-20201231.htm) |
| OTIS | 2020-04-03 | [Issuer launch release](https://www.prnewswire.com/news-releases/otis-common-stock-begins-trading-on-new-york-stock-exchange-301034586.html) |
| DOW | 2019-04-02 | [Issuer separation release](https://investors.dow.com/en/news/news-details/2019/Dow-completes-separation-from-DowDuPont/default.aspx) |
| NWS / NWSA | 2013-07-01 | [Issuer launch release](https://newscorp.com/2013/06/28/the-new-news-corp-launches-as-global-media-and-information-services-company/) |
| FOX / FOXA | 2019-03-19 | [Issuer regular-trading release](https://www.foxcorporation.com/news/corp-press-releases/2019/fox-corporation-announces-first-day-as-standalone/) |

The first evidence file was already retained when these additional checks
completed, so neither it nor its immutable approvals are edited. Instead, the
utility narrows the mutable lifecycle start for these nine canonical instruments
and nine listings; both the lifecycle and historical approval must cover a trade.
The supplementary evidence is retained with a separate checksum/source-payload
locator. It can restrict existing coverage, never expand it beyond an approval.
Fresh seeds and reruns apply the same restrictions automatically.

These sources support specific date overrides. Our engineering inference is to
retain this distinction explicitly and preserve the original onboarding
approval rather than overwrite it. **525 dates remain estimates; 18 have
primary regular-way/share-class evidence.** This alpha assessment is not production-quality
historical security-master certification.

## Implementation

1. Export a separate reviewed evidence bundle from retained Yahoo responses.
   Validate symbol, venue, timezone, currency, equity type, epoch/date bounds
   and original payload checksum. Negative Unix epochs work on Windows.
2. Keep current October 6 version-1 APPROVED definitions immutable.
3. Append version-2 **non-current APPROVED historical** definitions covering
   assessed start through October 5, with identical economics, approval actor,
   actual approval timestamp and the retained evidence-bundle source payload.
   Sequence numbers represent append order, not business-date chronology.
4. Extend instrument/listing lifecycle projections to the assessed start.
   An instrument's lifecycle interval is separate from a version's interval.
5. Cash booking requires exactly one current operational approval, then selects
   exactly one approved definition valid on the execution date. Gaps, overlapping
   approvals, lifecycle exclusions and changed historical economics fail closed.
   The chosen historical IDs are frozen in BOOKED evidence.
6. Restrict the utility to local `fortem_secm` on port 54329. It defaults to a
   rollback preview, verifies shared seed identities/economics, takes the seed
   advisory lock, and commits all references atomically with `--apply`.

No migration, trigger bypass, approved-definition update/delete, identifier
backdating, index-membership backdating or tenant permission expansion is used.
Existing trades and their frozen definition IDs remain untouched. The original
universe manifest and its retained checksum remain unchanged.

## Reproduction

From the repository root, with the existing seeded reference catalogue:

```powershell
# Generate once from retained operating Yahoo history; refuses file overwrite.
.venv/Scripts/python.exe scripts/seed_index_trading_history.py --export
# Inspect the maintained bundle, then preview/apply its reference-only changes.
.venv/Scripts/python.exe scripts/seed_index_trading_history.py
.venv/Scripts/python.exe scripts/seed_index_trading_history.py --apply
```

Fresh local seed order: base demo/reference catalogues, then
`scripts/seed_index_universe.py --apply`, then the historical utility above.
The reviewed offline bundle is usable on a fresh reference database without
copying market observations. Where original retained source deliveries exist,
their metadata and checksum are cross-checked. Reruns must append zero rows and
refuse any unexpected definitions or modified projections.

Maintained bundles: `security_master_schema/data/index_trading_starts_2026_10_08.json`
and `security_master_schema/data/index_regular_way_bounds_2026_10_08.json`.
Includes per-listing effective date, evidence basis, source URL(s), provider
metadata, original source-payload ID and checksum. Do not edit it after it has
been retained by an operating seed; a correction needs a new evidence/version
workflow, not a silent rerun with changed bytes.

## October 7 data import

Existing ingestor and acquisition/storage licensing checks are retained:

```powershell
.venv/Scripts/python.exe -u -m apps.market_data_ingestor.yahoo --apply --acknowledge-personal-access --declaration 'Owner requested 2026-10-07 EoD update for personal research; existing acquisition rights remain enforced' --start 2026-10-07 --through 2026-10-07 --limit 543
```

Job `01a11b2f-6f5b-7ae1-b5b1-e3e67598cbb2`; log
`logs/yahoo-eod-2026-10-07.log`. Serial requests are spaced five seconds;
429 retries use exponential backoff plus Retry-After. Publication and attempt
evidence commit per symbol, so progress is durable and exact-window recovery
skips already completed symbols. A rejected/missing response is not success.

This does **not** certify historical mapping continuity, convert Yahoo Close
into a RAW official exchange close, create a pricing-policy rule, provide FX
conversion, or extend personal licensing to commercial use. The reported
`NO_MATCHING_POLICY_RULE` and EUR-position/GBP-reporting limitations remain
separate valuation configuration/scope issues.

## Verification and activation

Initial lightweight regressions: **17 passed** (date selection, ambiguity, missing
current approval, gaps, when-issued overrides, negative epoch, invalid provider
identity/date). Focused isolated verification: **62 passed in 201.83 seconds**,
including all 543 start/prior/current boundaries, real synthetic historical
booking and frozen IDs, unchanged current approvals/financial tables, repeat
history and original seed, and existing cash integrity controls. No full suite.

Operating application on October 8: **1,086 historical approvals appended**;
evidence payload `01a11b41-b4aa-7402-9ef9-54e6f7029cdb`. Only the API was restarted
(port 8000), leaving the console and ingestor running. Independent READ ONLY
verification found 543 assessed starts READY, all 543 preceding dates refused,
and all 543 current dates READY. HTTP health 200; the reported TotalEnergies
listing is READY for both 2026-05-08 and 2026-07-08. No operating booking or
valuation was created. Logs: `logs/index-trading-history-tests.log`,
`logs/index-history-operating-verification.log`, `logs/index-history-api.err.log`.

Adjacent cash readiness regressions: **7 isolated tests passed in 8.32 seconds**.
After adding configurable request pacing and the additional share-class lifecycle
boundaries, **68 lightweight tests passed in 9.48 seconds**. Final isolated seed
verification: **4 tests passed in 99.89 seconds**, including all 543 final
ordinary-listing starts and preceding-day refusals. Final pure date regressions:
**26 passed in 0.48 seconds**. Whitespace diff checks passed; no full suite.

The nine additional lifecycle restrictions adjusted 18 projection rows, appended
zero further definitions, and retained evidence payload
`01a11b51-3156-70d1-a945-1fdf2cdf65c1`. A subsequent operating preview appended
zero definitions and changed zero lifecycle bounds. Independent operating
READ ONLY verification again confirmed all 543 final start/prior/current
boundaries, API health 200, and the two reported TotalEnergies historical dates
READY. Log: `logs/index-history-operating-verification-final.log`.

## Completed import and owner-requested speed-up

At the owner's request to speed up, the old ingestor process was confirmed and
stopped, and its job explicitly recorded ABORTED with the interruption reason.
Already-published observations were not removed. A new exact-window job,
`01a11b4b-16db-7ce6-877b-b4aedc7e88d6`, used **one-second serial spacing**, reused
345 successful symbol deliveries and fetched the remaining 198. The bounded
`--request-spacing-seconds` CLI setting accepts 1..60 seconds; default remains
five seconds, and provider Retry-After/exponential backoff is unchanged. This
is an operator pacing choice, not a claim of an officially licensed rate limit.

The resumed job completed all **543 listings**, without rejected observations.
Independent stored-data verification found exactly **543 active CLOSE and 543
active ADJUSTED_CLOSE observations dated 2026-10-07**, one of each per listing.
Log: `logs/yahoo-eod-2026-10-07-fast.log`. Historical continuity remains
REVIEW_REQUIRED; the importer did not grant or certify valuation/display rights.
