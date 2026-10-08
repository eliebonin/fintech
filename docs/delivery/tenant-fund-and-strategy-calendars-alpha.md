# Tenant fund and strategy calendars — alpha delivery

Date: 2026-10-07. Scope: governed calendar configuration and market-data input selection; not valuation/P&L, cash accounting or settlement execution.

## Outcome

The tenant can maintain a fund/strategy schedule independently of exchange trading calendars. Open **Market data → Fund and strategy calendars** (`/market-data/calendars`). Reference calendars remain platform-owned; tenants publish separate versions, not edits to shared exchange holidays.

Available schedule modes:

- Specified weekdays, with documented dated exceptions.
- ALL_OPEN: all selected reference calendars must be open; one closure prevents operation.
- ANY_OPEN: one selected open reference calendar is sufficient.
- EXPLICIT: administrator-provided dated decisions; omitted dates remain UNKNOWN.

Each version declares purpose (VALUATION, DEALING or SETTLEMENT), IANA timezone, local decision time, inclusive coverage (up to 1,100 dates), source and exception reasons. An Irish/UK/US combination uses explicit selected calendar definitions, never inferred domicile/country/currency. Missing reference coverage remains UNKNOWN. Holiday-only reference entries establish closure, not that other dates are open. Holiday/session conflicts are unresolved rather than silently choosing one.

Users can add CLOSED or exceptional OPEN dates, remove draft exceptions, or paste a dated schedule using `YYYY-MM-DD | OPEN or CLOSED | reason | source`. Import replaces only unsaved draft dates. Removing a published holiday is a new-version decision, never deletion of reference/history records. Browser import validates real dates, duplicates and required evidence; API independently validates bounded dates, IANA timezone and DST decision-time validity.

## Version and assignment governance

Publication is administrator-attributed, atomic and idempotent. Exact retry preserves the same version; changed-payload key reuse is 409. A new submission for the same calendar code creates a new version. Component/day evidence is frozen during publication, so subsequent reference edits cannot rewrite that version. Published calendar definitions, dated sessions/holidays and assignment records have database immutability protection.

Assign an exact tenant version to a strategy or a visible active canonical fund, fund share class or ETP reference. Assignments retain purpose, effective dates, actor, reason and recording time. A fund-level assignment is inherited by its share classes for NAV selection; an exact share-class assignment takes precedence. No automatic assignment or automatic upgrade to the newest version.

Reassignment for the same target/purpose/effective interval appends a new decision. Overlapping unequal intervals are rejected to avoid ambiguity; adjacent intervals may use different versions. Resolution selects the latest decision known at its information cutoff. Assignment dates must be covered by the version. Tenant version IDs are hidden from other tenants in calendar APIs and existing pricing-policy options.

MARKET_DATA members may inspect/preview. Publication and assignment require MARKET_DATA plus TENANT_ADMIN. The UI derives tenant/actor context server-side; no demo fallback. List responses contain configuration summaries rather than duplicating full schedules; exact detail provides the configuration.

## Market-data behaviour

A closed strategy VALUATION calendar returns `NOT_EXPECTED / STRATEGY_VALUATION_CLOSED`, even if no pricing rule matches. A closed assigned fund calendar returns `NOT_EXPECTED / FUND_VALUATION_CLOSED` for NAV series only. It does not close a fund's listed market price or modify an underlying equity's exchange schedule. Unknown assigned coverage is `MISSING / CALENDAR_NOT_ASSESSED`, not a valid open day or a fabricated price.

Open decisions and closure/unknown decisions are captured in new snapshot `pricingEvidence.calendarDecisions`. Historical snapshots keep their exact frozen values/evidence through reassignment. Legacy snapshots and fingerprint serialization are preserved; the resolver version is now v3. A not-expected input is distinguishable from a missing expected input; it is not a valuation-ready input and the existing snapshot aggregate remains PARTIAL unless every input is selected.

For holiday-aware NAV lag and staleness, create a pricing-policy version using **Fund NAV valuation dates (`NAV_DATE`)**, a NAV series type such as `OFFICIAL_NAV`, and an explicit published tenant VALUATION calendar. This pricing rule pins its schedule version. Existing LEGACY NAV policies deliberately retain weekday arithmetic until revised; assigning an expectation calendar does not silently rewrite pricing arithmetic. Exchange/fixing conventions cannot borrow tenant fund calendars. Their separate exchange/benchmark calendars continue to govern price targets.

## Endpoints and schema

- `GET /v1/market-data/calendars/options`
- `GET /v1/market-data/calendars/{calendar_id}`
- `GET /v1/market-data/calendars/{calendar_id}/days?fromDate=...&toDate=...`
- `POST /v1/market-data/calendars` — immutable publication, stable Idempotency-Key.
- `POST /v1/market-data/calendars/assignments` — append-only pinned assignment, stable Idempotency-Key.

Migration68 extends the existing `cal.market_calendar` and adds `cal.calendar_assignment`. No new disconnected calendar engine. New fields and constraints have metadata descriptions. The migration is additive, explicitly frozen (not derived from mutable application metadata), forward-only to preserve evidence.

## Evidence and remaining limits

Lightweight composition: 6 tests RED missing module → GREEN. Real isolated API tests first failed for missing endpoints. Further RED→GREEN coverage includes NAV session lag, reference holiday conflicts, payload bounds and closed-strategy rule ordering. Tests exercise version replay/conflict, readonly authority, foreign-calendar hiding, component freeze, immutable publication/assignments, purpose separation, historical information cutoff and unchanged snapshot replay. Browser acceptance is read-only; no operating calendar publication/assignment is seeded by this implementation.

Final verification:

| Check | Result | Evidence |
| --- | --- | --- |
| Focused calendar/API, composite resolver and rights/schema regressions | 73 passed, 20.76s | `logs/tenant-calendar-review-green.log` |
| Full frontend suite | 127 files / 600 tests passed, 9.92s | `logs/tenant-calendar-frontend-final.log` |
| Ops-console and generated contract typechecks | Passed | `logs/tenant-calendar-types-final.log` |
| OpenAPI consistency / Git whitespace | Passed | Final export `--check` and `git diff --check`, exit0 |
| Full isolated Python suite | 1,118 passed, 490 warnings, 857.85s; exit0 | `logs/tenant-calendar-full-python.log` |

The disposable-database runner exited successfully and cleaned up its owned test database. Warnings include SQLAlchemy deprecations and Pydantic field-metadata warnings; this is not a warning-free-code claim.

Local activation is migration `20261007_68`. Before/after counts: trades9; strategies50; observations1,358,477; calendars4; assignments0. No operating reference holiday imports, calendar publication/assignment, financial records or licence grants were created or modified. The already-running API reloaded the implementation; no restart was needed.

Read-only browser acceptance in the selected Fortem Demo Tenant loaded the editor, reference options and date-range preview. The London synthetic reference returned UNKNOWN / NO_REFERENCE_COVERAGE for 2026-08-28 through 2026-08-31; native date controls and the preview retained the requested range. No warning/error console entries were captured. This confirms honest missing-coverage display, not authoritative London holiday coverage. Publication and assignment writes were exercised through real HTTP in disposable test databases rather than operator data.

Reference bank/calendar feeds are not automatically onboarded or certified. Existing reference-calendar coverage may be incomplete; the UI shows UNKNOWN honestly. Administrators can use an explicit published schedule or a weekday schedule plus sourced exceptions immediately. Automated provider schedule ingestion, four-eyes approval and searchable fund pickers remain future enhancements. Fund UUID assignment is the current alpha UI. Dealing/settlement calendars are configurable but do not implement dealing or settlement workflows.

Review is a separate author self-review under the requested sequential/no-subagent workflow, not independent signoff. No automatic Git commit or push.

## Source-backed design

[BlackRock's 2026 schedule](https://www.blackrock.com/uk/literature/shareholder-letters/bfm-schedule-of-non-business-days-2026.pdf), read 2026-10-07, publishes fund-specific non-dealing exclusions and notes that the day before a market closure may be affected. This supports explicit fund exceptions; it does not establish an identical NAV calendar. [QuantLib's joint-calendar source](https://raw.githubusercontent.com/lballabio/QuantLib/master/ql/time/calendars/jointcalendar.hpp), read 2026-10-07, distinguishes joining holidays from joining business days. ALL_OPEN / ANY_OPEN exposes that distinction clearly. Immutable tenant schedules, recorded-time selection and coverage checks are our design inference for this platform, not a universal regulatory requirement.

See [spec](../superpowers/specs/2026-10-07-tenant-calendars.md) and [execution ledger](../superpowers/plans/2026-10-07-tenant-calendars.md).
