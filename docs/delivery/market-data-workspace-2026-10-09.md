# Market data workspace — 9 October 2026

## Delivered behavior

`/market-data` is an operational overview. It reads source metadata rather than observation history. Shared navigation connects coverage, the data explorer, sources/access, pricing policies and calendars.

The explorer searches a paginated catalogue of series metadata and one latest accepted, current, display-permitted stored value per series as of the selected date. Empty visible series remain visible. History and provenance load when a reference is opened. Existing reference-history bookmarks redirect to the explorer. Latest stored values do not imply policy-selected valuation inputs.

Coverage uses the existing read-only calendar-aware resolution preview for 1–50 explicitly required listing/reference IDs, a policy, market date and information cutoff. Every required reference remains in the denominator; missing results are unknown. The default table shows exceptions and unknown results, with selected inputs available on demand. Changing context invalidates previous results; tenant changes cannot silently reuse a checked result. Coverage does not save a snapshot or valuation.

## Scope and controls

Coverage is an explicit input check, not automatic complete coverage of a strategy's positions or a universe. Optional strategy selection supplies policy context only. Ingestion monitoring has no established tenant-safe operational API and is visibly unavailable. Source counts are configuration metadata, not feed health or portfolio readiness.

The catalogue reuses tenant/module, node visibility, dataset display-entitlement and current-observation rules. Its latest-value lookup is batched in one SQL statement using a lateral lookup per paginated series. It returns no history arrays or observation counts. Reference search enforces workspace/module access and preserves upstream failures instead of substituting fixtures.

No operating financial/configuration writes, migrations, source downloads, commits or pushes were performed for this delivery. The API was restarted to load the new endpoint; the existing frontend development server was retained.

## Verification

- 36 focused Python tests passed against an isolated disposable database, including catalogue paging/search, constant query count, empty series, visibility and accepted/current observation selection.
- Full frontend regression run: 722 tests passed across 154 files. After final refinements, 10 focused page, coverage and reference-route tests passed, including four newly added checks.
- Final isolated production build and TypeScript compilation passed. Temporary build output was removed and generated next-env bytes preserved.
- OpenAPI export consistency and scoped whitespace checks passed.
- Live HTTP checks returned 200 for overview, explorer, coverage, sources, policies and calendars. Existing history bookmarks and direct history also responded. A live read-only preview preserved a missing requirement without saving any result.
- Read-only operating-database sample: 25 catalogue rows took 597 ms cold and 484 ms warm with a 14,199-byte payload; 100 rows took 495 ms with 56,653 bytes. Both page sizes used 11 SQL statements, including existing rights checks. This is a local API query sample, not a browser loading benchmark or measured comparison to the previous implementation.

Browser automation could not initialize in the Windows sandbox. Rendered layout, hydration and end-to-end interactive acceptance remain unverified; successful HTTP checks and automated tests do not establish browser acceptance.


## Selected-series history correction

Explorer row links now carry both referenceNodeId and seriesId. The API filters the exact series before counting/paging, retaining existing visibility and display rights. Refresh forms and observation pagination preserve seriesId. Reference-only historical bookmarks continue to show the reference's series.

Regression verification: the new frontend tests first failed for the missing link/request selection and the isolated API test first returned three series instead of one. After the correction, six isolated Python tests and twelve focused frontend tests passed; TypeScript and OpenAPI consistency checks passed. The backend was restarted using the repository virtual environment. Live AMZN verification returned three catalogue rows and exactly one raw CLOSE history series, with eight observations. No operating data was modified.


## Full-period charts and price table pages

History requests now opt into compact chartPoints (market date and value) for the complete selected period, independently of observation pagination. Chart requests require an explicit reference/series and both dates. The chart projection reuses the table query's current/accepted/date/display-entitlement filters. Table evidence remains paginated at 25 prices by default, with 50/100 selectable below the chart. Page links preserve date/series/page size; changing the dates or size resets the observation offset. Full-period chart summary/range no longer depend on the visible table page.

Verification includes an isolated 1,010-point fixture, identical complete chart data across 25/50/100 table pages, and suspended entitlement denial. Live AMZN returned 1,255 chart points with 25 evidence rows; the second table page retained identical chart data. Thirteen focused frontend tests, TypeScript and the isolated production build passed. No operating data was modified. Full chart payload/work scales with the selected date range; it is compact but not sampled or capped. Browser visual acceptance remains unverified.


## Interactive history chart

The history chart is now a client component with labelled date and price/currency axes. Calendar spacing preserves gaps between dates. Pointer hover/touch and focused left/right keys expose exact dates/values with a crosshair. Local zoom in/out, earlier/later, start/end sliders and reset controls operate on the already-loaded full-period points and leave table pagination independent. Single and flat points render; unusable observations are disclosed instead of silently plotted. No new package, API change or backend restart was needed.

Twelve focused geometry, component-rendering and history-page tests passed, covering calendar spacing, nearest-point lookup, zoom/pan boundaries, unique short-period ticks, single/flat points, labelled axes and preserved full-period/table separation. TypeScript and an isolated production build passed. Browser-driven hover/keyboard/touch and visual acceptance remain unverified in this environment.


## Overview navigator and quick ranges

The two independent range inputs are replaced with one miniature full-period chart, shaded outside the selected window. Pointer capture supports dragging either boundary or the window; keyboard arrows adjust boundaries or move the window, with Shift stepping ten observations. The prominent 1M/3M/6M/1Y/All controls apply calendar ranges ending at the latest loaded observation. Calendar-month subtraction clamps month-end dates correctly. All/reset restores the loaded period, with no additional API requests and no changes to table pagination.

Thirteen focused chart geometry/component/history tests and TypeScript passed. Coverage includes preset month-end boundaries, existing zoom/pan bounds, overview/control rendering, absence of old range inputs, full-period point counts and independent price pagination. Browser-driven drag/touch/keyboard acceptance remains unverified. This change requires no backend restart or operating data writes.
