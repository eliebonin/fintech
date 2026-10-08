# Yahoo personal-research backfill

Owner approved an explicitly recorded personal-research exception on 7 October 2026, followed by five years of Yahoo daily history for the 543 mapped current S&P 500/CAC 40 listings. This is not provider contractual permission, commercial clearance or a historical constituent reconstruction.

## Boundaries

- Add PERSONAL_RESEARCH_EXCEPTION as an auditable evidence basis, valid only for PERSONAL ACQUIRE. Only the Yahoo personal dataset with a declared tenant may use it to satisfy AUTOMATED_SOURCE_ACCESS. Other layers remain conjunctive; COMMERCIAL continues to require CONTRACT.
- Activation is an explicit local operator action attributed to an active tenant administrator. Never overwrite an existing separately reviewed assignment, suspended grant or different tenant profile.
- Keep the honest PersonalPriceResearch/1.0 request identifier, JSON Accept header, 4 MiB payload limit, serial five-second pacing, bounded 429 retries and immediate stop on 401/403.
- History mode permits an explicit start/end range of at most 1,830 calendar days. Daily mode retains its existing bounded default. A five-year delivery per ticker reduces calls versus annual HTTP chunks; commits and resumption are per ticker.
- Retain exact responses, actual receipt times and exception evidence with normal ingestion records. Preserve separate Close/Adjusted Close series and append-only revisions. No invented missing data, historical aliases, venue equivalence or prices.
- Resume from stored successful request reports without re-fetching those windows; do not skip failed/empty requests. A partial success is retained and reported, not described as complete coverage.
- Final coverage is provider coverage, not exchange-calendar certified completeness. Report short histories, failed identities, missing bars, request failures and remaining proposed mappings. Leave trades, cash, strategies, valuations and accounting untouched.

Window: 2021-10-07 through 2026-10-06 inclusive.
