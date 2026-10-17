# Reviewed Paris reference calendar

**Status:** Implemented and activated locally, 2026-10-13  
**Capability:** F33  
**Scope:** Paris cash-equity calendar for 2026; not a universal calendar feed.

## Source and evidence

**Follow-up:** [Major-market calendar delivery](major-exchange-calendars-20261013.md)
records the subsequent Paris version, seven-venue activation and resolution of
the FX blocker below with FLEXIBLE_EOD v3. The original result remains historical.

The source belongs to **each immutable calendar version**. The existing
`market_calendar.definition_json.provenance` stores source kind, source reference,
review date/scope, library name/version, MIC, timezone, coverage, review manifest
and generated schedule SHA256. Each dated session also retains its source URL.
Creator/publication time are recorded by existing calendar columns. No migration
is required. Sealing freezes that version; it does not certify exchange origin.

[Euronext's published calendar](https://www.euronext.com/en/trading/trading-hours-holidays)
was checked for Paris's 2026 weekday closures and half-day dates. The checked
facts and review limits are retained in
[the import review manifest](../../data/xpar-calendar-review-2026.json).
[pandas_market_calendars](https://pandas-market-calendars.readthedocs.io/en/latest/)
5.5.0 generates explicit rows, including weekends, timezone-aware normal sessions
and half-days. The entire year must agree with the review's closure/half-day sets
and time convention; disagreement blocks publication.

This is `REVIEWED_LIBRARY_SCHEDULE`, **not exchange-certified data**. Normal
09:00–17:30 and half-day 09:00–14:05 times are the pinned library's research
convention. The 2026 holiday notice alone does not verify every trading phase or
auction timestamp. The website's historical 2021 half-day-hour paragraph is not
claimed as 2026 hours evidence. Exceptional closures and future years need new
reviews/versions. No automatic annual maintenance or licensed feed is claimed.

## Implementation and operation

[Importer](../../market_data/reference_calendar_import.py) validates/generates
the schedule and publishes through the existing sealed-copy workflow. The shared
publisher now preserves source provenance instead of discarding it when copying.
Resolver evidence includes that provenance. Active platform-administrator
authority is required; a tenant administrator cannot publish shared references.
An identical import fingerprints the source review, package version and schedule
and reuses the existing sealed version; changed evidence creates a new version.

[Local operator command](../../scripts/import_reference_calendar.py):

```powershell
.venv/Scripts/python.exe -B scripts/import_reference_calendar.py --review data/xpar-calendar-review-2026.json --actor 00000000-0000-7000-8000-000000000304
# After reviewing the preview:
.venv/Scripts/python.exe -B scripts/import_reference_calendar.py --review data/xpar-calendar-review-2026.json --actor 00000000-0000-7000-8000-000000000304 --apply --activate-venue
```

Preview does not write or contact a provider. Apply is restricted to local
`platform_secm:54329`. Activation explicitly updates only the unique XPAR venue
default and records actor/old/new calendar IDs in an audit event. Immutable policy
versions with explicit calendar IDs and old calculation evidence are unchanged.
Do not regenerate source evidence at calculation time.

## Activation and verification

- **365 dated sessions** published for 2026-01-01 through 2026-12-31, including
  five weekday closures and two half-days.
- Sealed calendar: `c7b2e3fb-ee10-416c-9e47-cf9c185b3ae5`.
- Activated XPAR venue: `00000000-0000-7000-8000-000000000164`.
- Repeating apply/activation returned the same sealed calendar ID, without another
  venue change. API restarted on port 8000; `/health` returned HTTP 200. Frontend
  stays on port 3000. No trade, tenant-policy or strategy changes were made.
- **41 focused tests passed** in an owned disposable database: reviewed schedule,
  disagreement/source rejection, idempotent import, authority, provenance
  preservation, immutability, calendar resolution and valuation storage regressions.
  Test-first reproduction showed source provenance was lost during publication;
  the new assertions passed after repair. No full Python suite.
- Operating diagnostic reused the last requested October 7–8 period and
  FLEXIBLE_EOD v2 with a **new current information cutoff**. Equity/calendar
  selection passed; calculation advanced to `FX input selection blocked:
  CALENDAR_NOT_ASSESSED`. Diagnostic snapshot writes were rolled back; no attempt,
  staged batch or financial publication was created.

The remaining FX configuration is a separate known blocker: v2 pins a research
calendar covering only October 6–7; its pinned EUR/GBP series also ends October 7.
October 8 therefore needs both a rate and corresponding assessed FX-calendar
coverage. Do not use Paris's exchange holidays as an implicit FX calendar, extend
a sealed two-day sample in place, or invent a London fixing from a Yahoo daily bar.

Other exchange/year calendars remain unpopulated by this change. Tenant fund
schedules remain independently managed; see
[calendar delivery](tenant-fund-and-strategy-calendars-alpha.md).
