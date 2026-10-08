# Yahoo five-year personal-research backfill

Status: available-history backfill completed for all 543 mapped listings; one retained source-date gap and 13 shorter histories. Verified 7 October 2026.

Owner approved an explicitly recorded personal-research acquisition exception on 7 October 2026. This is not provider permission or contractual evidence. The migration adds PERSONAL_RESEARCH_EXCEPTION as a separate basis restricted to PERSONAL ACQUIRE; the rights evaluator accepts it only for AUTOMATED_SOURCE_ACCESS on YAHOO_PERSONAL_EQUITY_DAILY with a declared tenant. Commercial scope still requires CONTRACT. Other providers, activities and prerequisite layers are unchanged.

The exception is attributed to the active tenant administrator and the owner's approval reference. Its record identifies the personal operator as both issuer and beneficiary, not Yahoo as an issuer of permission. Repeated activation preserves the original record and refuses to reactivate suspended permission or replace a previously reviewed assignment. Exact grant evidence is frozen with retained deliveries.

## Scope and operation

- Current seeded S&P 500/CAC 40 universe: 543 distinct listing mappings, not historical constituents.
- Requested inclusive dates: 2021-10-07 through 2026-10-06.
- One explicit, bounded five-year HTTP window per ticker, maximum 1,830 calendar days and 4 MiB; original daily mode remains bounded separately.
- Serial requests with five seconds between tickers and existing exponential 429 retries; no proxies, authentication harvesting or browser impersonation.
- Atomic per-ticker commits; subsequent execution resumes exact successful retained requests. Failed/empty requests are not skipped. Partial deliveries are reported, not called complete.
- Publication caches series identifiers, preloads current source observations and inserts validated points in batches of at most 1,000. Duplicate and correction behavior remains unchanged, including a sequential fallback for repeated identities within one adapter delivery.
- Close and Adjusted Close remain separate with their actual provider adjustment bases and daily-bar timestamps. Missing prices, short histories and identity failures are not repaired.
- Coverage counts current observations only, excluding superseded accepted revisions. Calendar completeness and historical ticker/issuer continuity are not certified.

## Commands

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m apps.market_data_ingestor.yahoo --apply --initialize-only --acknowledge-personal-access --personal-research-exception --declaration "Owner approved local personal research exception; not provider permission"
.venv/Scripts/python.exe -u -m apps.market_data_ingestor.yahoo --apply --acknowledge-personal-access --declaration "Owner approved local personal research" --start 2021-10-07 --through 2026-10-06 --limit 543
```

Rerun the last command to resume the exact requested window. Changing dates is a new request. Retained delivery hashes still distinguish provider revisions. Ordinary daily ingestion continues to refetch and append changed observations rather than blindly resume old marks.

## Verification and execution ledger

- Initial pure rights regression failed because the new exception was denied; narrow-scope rights tests now pass.
- Initial activation regression failed because activation did not exist; isolated activation/revocation and ingestion tests pass.
- Initial history/resume tests failed on missing interfaces; bounds and exact successful-request lookup implemented and verified.
- Current-only coverage regression caught revision double-counting and passed after adding the supersession filter.
- CLI safety test caught the argparse default-value conflict for simultaneous --start and --days 14; absent days now default after parsing and invalid combinations stop before database access.
- Offline rights, adapter, CLI and boundary checks: 60 passed. Isolated activation, ingestion and display checks: 26 passed. Pre-batching full isolated suite: 1,035 passed, 490 warnings in 931.61 seconds; log logs/yahoo-five-year-full-python.log.
- Before operating import: 9 trades, 9 trade lifecycle events, 50 strategies, 0 cash accounts, 0 cash balances, 12,469 preexisting observations.
- Migration 63 applied locally. Pilot log: logs/yahoo-five-year-pilot.log. Pilot passed: AAPL 2,508 observations; AIR.PA 2,560; MT.AS 2,560. All three span 2021-10-07–2026-10-06 with zero rejections in the five-year deliveries. The earlier short European probe's missing last bar was subsequently populated by the provider; no repair was performed.
- Full-universe command started with ordinary rights enforcement and without reactivating/replacing the exception. Initial progress log: logs/yahoo-five-year-universe.log. After 12 committed ticker results, the task-owned job was stopped to replace per-point SQL with tested batching. A killed in-flight ticker transaction rolls back; completed deliveries remain retained.
- Resumed progress log: logs/yahoo-five-year-universe-resumed.log. Batched publication checks: 16 isolated tests passed in 1.62 seconds. Fresh full isolated suite covering the final publisher: 1,037 passed, 490 warnings in 914.03 seconds; log: logs/yahoo-five-year-final-python.log.

## Final operating results

All 543 seeded listing mappings are VERIFIED and have both Close and Adjusted Close series: 1,086 series, 1,346,008 observations (673,004 per field). All series reach 2026-10-06. Of the 543 listings, 530 have observations from the requested 2021-10-07 start; 13 have shorter available Yahoo history below. This is available-history ingestion, not certification that every expected exchange session or historical identity is complete.

The resumed command processed all 543 selected tickers: 529 fetched and 14 resumed from committed deliveries. There were zero HTTP/source errors and zero 429 backoffs. One partial delivery caused the deliberate nonzero exit: FISV returned missing Close and Adjusted Close on 2025-11-12, while its other 2,506 observations were accepted. A single bounded follow-up for 2025-11-11–2025-11-13 returned the same two missing values and four duplicates; no extra prices were inserted and no values were invented. Follow-up log: logs/yahoo-five-year-fisv-followup.log. Treat this as a retained data-quality gap, not an unprocessed ticker or a failed whole-universe import.

The following first available dates apply equally to Close and Adjusted Close. The table records source coverage only, without asserting a cause for unavailable earlier history.

| Listing symbol | First available date | Observations per field |
| --- | --- | ---: |
| CEG | 2022-01-19 | 1,183 |
| FDXF | 2026-05-27 | 92 |
| GEHC | 2022-12-15 | 954 |
| GEV | 2024-03-27 | 634 |
| HONA | 2026-06-15 | 79 |
| KVUE | 2023-05-04 | 859 |
| Q | 2025-10-27 | 237 |
| RDDT | 2024-03-21 | 638 |
| SNDK | 2025-02-13 | 413 |
| SOLV | 2024-03-26 | 635 |
| URW | 2023-04-14 | 889 |
| VLTO | 2023-10-04 | 754 |
| VYLR | 2026-10-01 | 4 |

Final read-only integrity check: 9 trades, 9 trade lifecycle events, 50 strategies, zero cash accounts and zero cash balances, unchanged from baseline. Total database observations are 1,358,477 = 12,469 preexisting + 1,346,008 newly imported Yahoo observations. All imported observations carry source-payload, vintage and acquisition-licence identifiers; missing provenance count is zero.

Final rights check: personal ACQUIRE, STORE and DISPLAY allowed; NON_DISPLAY and REDISTRIBUTE denied; commercial ACQUIRE denied. The acquisition record carries PERSONAL_RESEARCH_EXCEPTION and PERSONAL_DECLARATION, not fabricated CONTRACT evidence. Valuation/P&L is not enabled by this import. Sequential author review covered the rights boundary, exact-window resume, append-only corrections, batched persistence and current-only coverage; no subagents were used.

See [design](../superpowers/specs/2026-10-07-yahoo-personal-backfill.md), [plan](../superpowers/plans/2026-10-07-yahoo-personal-backfill.md), [Yahoo source/rights delivery](yahoo-market-data-alpha.md).
