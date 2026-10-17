# Yahoo equity EoD refresh — 13 October 2026

**Scope:** Owner-directed refresh of the existing 543 mapped S&P 500/CAC 40
listings, local personal-project dataset. No new provider/licensing clearance,
universe changes, trade changes or policy changes.

Used the existing operator ingestor with `--days 7 --limit 543
--request-spacing-seconds 1 --apply --acknowledge-personal-access`. Requested
**2026-10-06 through 2026-10-12**, conservatively excluding the current market day.
Rollback preview confirmed active recorded PERSONAL_DECLARATION and
PERSONAL_RESEARCH_EXCEPTION acquisition evidence before network use. Requests are
serial; existing exponential 429 retry/stop behavior and per-delivery provenance,
deduplication and revision handling remain unchanged.

Dataset: `01a11302-d25d-7093-9827-3893ed3c6d86`. Source ingestion job:
`01a1353a-f239-76bc-be62-35ab7c1db3e1`. Operator output:
`logs/yahoo-equity-refresh-20261013.log`.

The operator stores provider Close / split-adjusted and Adjusted Close /
vendor-adjusted separately, then assesses derived RAW against retained split
coverage. Acquisition completion alone is not RAW readiness, session completeness,
valuation success or commercial rights.

## Results

All 543 source requests completed without HTTP failures or rate-limit backoffs.
The source job is **PARTIAL**, honestly reflecting missing Yahoo values rather
than a failed whole-universe download:

- 3,201 accepted provider observations/revisions; 2,149 duplicate points.
- 80 rejected values: Close and Adjusted Close on 2026-10-12 for all 40 CAC listings.
- All 543 listings have both provider price fields for October 8 and 9.
- All 503 US listings have both fields for October 12. The 40 CAC listings' latest
  usable day in this refresh is October 9. A bounded October-12-only TTE retry
  still returned no usable close (malformed/missing close collection); nothing was
  inserted from that diagnostic. No prior-day fill or invented prices.

Initial RAW normalization created 1,509 observations for the 503 US listings.
European source snapshots referenced October 13, beyond the requested price
window, so 40 new deliveries initially lacked split coverage for that day. Used
the existing `apps.market_data_ingestor.yahoo_raw_prices --apply --fill-gaps`
command for exactly those 40 symbols, with one-second serial spacing. Event-only
responses retain split lineage and do **not** publish incomplete current-day bars.
The follow-up completed with zero blocked assessments and created 80 RAW points
for the European October 8–9 closes. Total newly derived RAW points: **1,589**.

RAW follow-up job: `01a1354b-ea0d-79d4-93d7-76c9adceb92b`.
Event-coverage/normalization log:
`logs/yahoo-equity-refresh-20261013-split-coverage.log`.
Read-only current-observation coverage/proof checks are the final verification;
no implementation changes or test-suite run were needed for this operator task.
Final checks confirmed RAW, split-adjusted Close and vendor-adjusted Close for all
543 listings on October 8–9 and 503 listings on October 12. **Zero current RAW
observations in that window are missing their price-basis proof.**

Related: [ingestor delivery and rights](yahoo-market-data-alpha.md),
[ingestion boundary](market-data-ingestion-boundary.md).
