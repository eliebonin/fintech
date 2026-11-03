# Selected valuation report: task-focused tabs

**Status:** Implemented; frontend verification below  
**Owner:** Valuation / Operations console  
**Last reviewed:** 2026-10-26

## Delivered display

Input form / Results / History remain the workspace navigation. Opening one
result provides a second, final navigation level:

| View | Content |
| --- | --- |
| Breakdown (default) | Exact source contribution report, coverage, securities bridge and scope. |
| Positions & cash | Existing position and cash-account reports, retained inputs/lineage and closable position inspector. |
| Review | Existing amendment requests/decisions, source reassessment, corrected-input recalculation and Ops explanations. |
| Logs | Selected attempt's operational events, correlation ID and expandable JSON/scope evidence. |

Selected strategy/dates/policy/currency, calculation/publication state, total P&L,
known publication blockers, actual omission counts and the existing publication
action remain outside the report tabs. Complete cash has no redundant warning
banner. Source inspection reveals Positions & cash before moving focus. Failed
attempts and History's View logs open Logs; absent results remain explicitly
absent, not calculated zero. Financial tabs explain why no staged result exists.

Panels remain mounted: position search/filter/page/closed-inspector state and
native review drafts survive tab changes. New results default to Breakdown;
refresh retains the currently selected report, including a newer choice made
while the read was pending. An approved amendment's new candidate is a distinct
result; the old immutable financial evidence is not edited.

## Navigation and accessibility

26 October layout follow-up: P&L sources & coverage expands to its full table
height, showing every source row and the included total without an internal
vertical scrollbar. The exception is scoped to this section; other report
tables keep their height limits, and narrow screens retain horizontal table
scrolling for readable columns. A regression reproduced 132px of hidden content
before the fix. Afterward, three isolated browser journeys passed, including
full-height coverage at 1280/760/480px widths, plus 14 focused component tests.
No calculation, source coverage or publication rule changed.

Source row amounts and the included total use green for positive and red for
negative values, based on exact decimal digits rather than rounded displays.
Zero, signed zero and unavailable values remain neutral; numeric signs and exact
value inspection remain available independently of colour.

Position attribution now defaults to 25 rows, with 50 / 100 / All choices and
Previous/Next controls together below the table, showing the visible range and
page count. The position inspector starts closed so the table initially occupies
the full available width; Inspect position opens the selected row's evidence.
Search, source,
attention and ordering apply to the complete already-authorized result before
paging, not just the displayed page. Changing filters or page size resets to the
first page; switching report tabs retains the choice and inspector visibility.
Cash rows remain separate and headline totals remain whole-result totals. All
renders every matching position; it does not merge different listing/economic
buckets or issue another calculation. Large results may consequently render more
slowly when All is chosen. Historical responses without name projections retain
the existing permission-checked lookup, batched at at most 20 IDs per request.

### Instrument-type column and filter follow-up

Position attribution shows a compact **Instrument type** column and a labelled
type selector, defaulting to **All instrument types**. Choices come from the full
already-authorized position population, sorted by human-readable type name, not
just the current page or search matches. Type combines with search, attention,
source and ordering before pagination, resetting to page one when changed.
Switching report tabs retains it; source-coverage inspection clears it alongside
search/attention so a previous filter cannot hide the source's contributors.
Cash-account rows and headline totals remain outside position filtering.

The existing access-checked metadata query now also resolves canonical instrument
types, including a listing's parent instrument. No per-row requests, migrations,
financial calculations or frozen result changes are introduced. This is current
accessible classification for navigation, not historical economic evidence or a
replacement for frozen valuation conventions. Missing/unsupported metadata is
shown and filterable as **Type unavailable**, never inferred from a name or UUID.
DISPLAY-denied results do not resolve or expose this metadata. This small backend
presentation follow-up is separate from the original frontend-only tab delivery.

Verification and local activation for this follow-up are recorded below.

The fragment identifies the selected attempt and report, for example
`#valuationRun=<attempt-id>&report=positions`. It is UI state, not authentication:
every restored attempt is loaded through the same access-checked BFF/API read.
Malformed path-like IDs are rejected locally. Opening a new result or choosing a
report pushes a fragment; refreshing replaces it without duplicate entries.
Direct links, reload and Back/Forward restore the selection while retaining query
parameters. Moving between already loaded report views issues no financial request.

Tabs expose labelled tablists/panels, roving focus and arrow/Home/End navigation.
All panels are immediately available, so automatic keyboard activation does not
wait for financial reads. Narrow tab lists scroll horizontally without wrapping.
The retained position inspector closes to a full-width table and reopens from its
row; exact price/FX comparisons remain beside that selected position.

## Financial/security boundaries and trade-offs

Subsequent presentation follow-up: the [manual-check inspector](position-inspection-manual-check-20261026.md)
shows exact quantities/prices/FX and the stored value bridge first, with sources,
IDs and full proof under a collapsed disclosure. This does not reprice any result
or change the report/tab/publication boundaries recorded here.

No backend endpoint, schema/migration, calculation, numeric rounding, licensing,
authority, immutable input/evidence, amendment or publication rule changed.
Denied DISPLAY still suppresses financial summaries, instrument/cash metadata,
inputs and review controls; selected operational events retain their pre-existing
disclosure boundary. Read-only users can navigate but cannot calculate/amend/publish.
Existing independent/default-off governed self-review paths remain unchanged.

This is presentation organization, not an API payload optimization: selected
attempt events and frozen financial evidence are still loaded through the existing
detail response. No new lazy-data endpoints or client repricing were introduced.
Tab state persists in the URL; native amendment drafts survive tab switching, not
a browser reload. Full print/export and a full assistive-technology audit remain
separate work. No live financial comparison is implied by UI acceptance.

## Verification

Instrument-type follow-up: **1,029 frontend tests in 210 files**, TypeScript,
**12 isolated Edge report journeys** and **17 focused disposable-PostgreSQL
metadata/presentation tests** passed. Regressions cover off-page types, combined
filters, page reset, tab retention, unavailable classification, mobile overflow,
private-parent visibility, DISPLAY boundaries and unchanged financial evidence.
No full Python suite or operating valuation was run. Both previously used app
ports were stopped at activation; the configured local API 8001 and frontend
3001 were started. API `/health` returned `status: ok` and `/select-context`
returned HTTP 200. No migration or operating data changes were required. Reload
the selected result to receive fresh display metadata; no recalculation is needed.

Pagination follow-up: **119 focused frontend tests in 20 files and five isolated
browser journeys passed**, covering 127-row page sizes/boundaries, full-result
filters, retained inspector/tab state, 20-ID label batching and existing Ops
review/navigation. The full frontend/Python suites were not rerun for this change.
The earlier report-tab verification is recorded below.

The subsequent closed-by-default inspector and bottom-pagination adjustment also
passed the 119 focused tests and three browser review/pagination/navigation
journeys. Initial component checks failed for both old layout defaults before
the change; inspector focus return, filters and page choices remain covered.

- **1,017 frontend unit tests passed in 210 files**, including 102 focused report
  tests used during implementation. Initial tests were RED for the absent report
  navigation, history/failure transitions and the late-refresh race.
- **10 isolated Edge browser journeys passed**: optional/strict accrual staging
  and explicit publication; source/price inspection; separate cash review; compact
  corrected-input tickets; three-viewport inspector close/reopen; four-view keyboard
  navigation; preserved filters/draft; direct link, Back/Forward and reload; failed
  History logs; read-only and denied-DISPLAY detail. Synthetic fixture only.
- Browser console errors are asserted absent in the new full navigation journey.
  First pass found duplicate sibling keys (fixed), ambiguous repeated status text
  (qualified log context) and tests targeting an action now in Review (updated).
- Full-suite follow-up found a stale expectation for primary UUID labels. Its
  fixture now supplies a current business name and still checks original trade
  links and position ownership; no product behavior was changed to satisfy it.
- Mobile screenshot inspected; no document-width overflow. Existing browser
  colour-environment warnings remain, not financial failures.
- Final TypeScript/whitespace checks and app availability are recorded in the
  [execution ledger](../superpowers/plans/2026-10-26-valuation-report-tabs.md).
  Normal Next imports are restored after synthetic acceptance-server typegen.
  Both final checks passed; UI 3001 returned HTTP 200 and API 8001 health was OK.
  No service restart or database migration was needed.

Sequential author review, per the user's execution preference, checked all five
plan review-focus cases, source-link focus, race/identity handling and current
financial disclosure. This is not an independent review or financial sign-off.
No operating balance/trade write, calculation, publication or permission change.

## Sources and traceability

The [approved design](../superpowers/specs/2026-10-26-valuation-report-tabs-design.md)
retains the directly checked GOV.UK, Carbon, W3C and NN/g references, their
applicability and the chosen four-view structure. These informed task grouping,
keeping comparisons together, progressive evidence disclosure and accessibility;
they do not prescribe a financial calculation model.

- [Report tabs/panels](../../apps/ops-console/src/features/valuation/report-tabs.tsx)
- [URL boundary](../../apps/ops-console/src/features/valuation/report-navigation.ts)
- [Financial report](../../apps/ops-console/src/features/valuation/result-workspace.tsx)
- [Console integration](../../apps/ops-console/src/components/valuation-console.tsx)
- [Operational log](../../apps/ops-console/src/features/valuation/run-evidence.tsx)
- [Browser acceptance](../../apps/ops-console/browser-tests/pnl-ops.spec.ts)
