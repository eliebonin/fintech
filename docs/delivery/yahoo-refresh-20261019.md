# Yahoo missing-data refresh — 19 October 2026

Status: COMPLETE for the recent refresh; one older provider-data gap remains.
Operational data acquisition, not a code change or financial valuation sign-off.

## Scope and method

Owner requested missing Yahoo prices and corporate actions before end-to-end
strategy/trade/valuation checks. Use the existing personal-project dataset,
543 reviewed listing mappings and recorded acquisition/storage rights. No new
licences, permissions, policy versions or mapping continuity approvals are granted.

- Refresh 5–18 October 2026, overlapping existing data to retry missing recent
  rows. The last completed weekday is 16 October; weekends are not price gaps.
- Use the existing serial Yahoo ingestor, one-second equity spacing and bounded
  exponential retries. Retain source payloads, duplicate checks and job evidence.
- Retain split/dividend facts through the normal corporate-action publisher.
  ANNOUNCED source facts are not payment confirmations, reviewed quantity effects
  or newly recognized income.
- Refresh existing EUR/GBP and USD/GBP daily and five-minute-derived London/New
  York cutoff series through the same completed window. These cutoff samples
  are not official benchmark fixings.
- Assess split coverage separately and append reconstructed RAW prices with
  provenance; do not relabel adjusted closes, overwrite source observations or
  alter booked trades/published valuation evidence.

## Historical gap inventory

The existing read-only calendar audit covers 19 October 2021–18 October 2026.
It uses `pandas_market_calendars` 5.5.0 as a non-authoritative cross-check, not as
new sealed platform calendar evidence. Its initial run overlaps the ongoing
refresh and must not be represented as final recent-date coverage.

- One older missing session: FISV, 12 November 2025. A targeted new request still
  failed to supply a usable chart. Earlier retained requests also lacked both
  close variants for this date. No interpolated or substitute price was inserted.
- CBOE's BATS venue is unsupported by this audit helper. Its two series remain
  NOT_ASSESSED, not certified gap-free by this calendar comparison.
- The helper combines source and derived CLOSE bases in its row counts; their
  overlapping dates are not evidence of duplicate observations within one series.

## Evidence

Local logs: `logs/yahoo-refresh-20261019-pilot.log`,
`logs/yahoo-refresh-20261019-universe.log`,
`logs/yahoo-refresh-20261019-fx.log`,
`logs/yahoo-refresh-20261019-historical-gap.log`, and
`logs/yahoo-refresh-20261019-audit.log`. Final coverage/normalization evidence:
`logs/yahoo-refresh-20261019-raw-gaps.log` and
`logs/yahoo-refresh-20261019-audit-final.log`.

### Committed results and readback

| Item | New records | Verified latest market date |
| --- | ---: | --- |
| Yahoo CLOSE / SPLIT_ADJUSTED | 2,212 | 16 October 2026 |
| Yahoo ADJUSTED_CLOSE / VENDOR_ADJUSTED | 2,319 | 16 October 2026 |
| Derived CLOSE / RAW | 2,212 | 16 October 2026 |
| Existing EUR/GBP and USD/GBP FX variants | 26 | 16 October 2026 |
| CASH_DIVIDEND source events | 16 | Source ex-dates retained |

All 543 listings have accepted 16 October observations in each of the three equity
bases above. Zero newly received RAW observations lack normalization lineage.
The two FX references each have daily, London-cutoff and New-York-cutoff points
for 16 October. No new split event was returned in this refresh; this is not a
claim that Yahoo is a complete corporate-action service. All 16 new dividends
remain ANNOUNCED; none was booked as income or confirmed paid.

The source job `01a15370-22fc-76ac-9177-37cf4e84e4ec` completed across 543 symbols
(541 downloads, two resumed pilot deliveries), with no rejected source rows or
HTTP/rate-limit failures. The pilot and this source job together inserted 4,531
source-price observations. Adjusted-close revisions can affect overlapping older
dates; those are retained corrections rather than fabricated new market sessions.

The initial normalizations retained PARTIAL outcomes for the 40 European
current-anchor coverage gaps. The follow-up fetched event-only coverage for
19 October, without publishing unfinished 19 October prices. Its final
normalization job `01a15385-07ab-70ee-b2c6-9424bd108667` completed across the
40 affected symbols with 200 additional RAW prices, zero blocked deliveries and
zero failures. Together with the initial 2,008 RAW prices and four pilot prices,
this reconciles to 2,212 new RAW observations. The earlier PARTIAL reports remain
immutable; the successful follow-up does not rewrite them.

Final source-calendar cross-check: 1,056 series MATCHES_CALENDAR, 26 SHORT_HISTORY
(leading unavailable history, not backfilled before listing), two GAPS (the two
FISV bases on 12 November 2025) and two NOT_ASSESSED (CBOE/BATS). Therefore this
does not assert universal five-year completeness. The FISV retry remains an
explicit FAILED job; no price was estimated. All refresh jobs are terminal.

For a subsequent daily valuation acceptance test, use 15–16 October with a current
information cutoff. These source/normalization receipts occurred on 19 October;
they must not appear in a calculation frozen to earlier knowledge. Data readiness
alone does not verify policy, instrument eligibility, income or financial outputs.

No operating trades, cash balances, valuations or publication actions are created
by this refresh.

## Operational observation

The ordinary equity CLI automatically normalizes the entire retained history
after source acquisition. This makes a small missing-date refresh revisit five
years of source rows/proofs while holding the dataset transaction lock, without
per-symbol progress output in that CLI. Database activity confirmed advancing
queries rather than a stalled download. The separate event-coverage helper must
wait for that transaction; its scope was narrowed to the 40 actual gap symbols
before any helper writes committed. Incremental normalization and useful progress
reporting are follow-up improvements, not changes made during this data run.
