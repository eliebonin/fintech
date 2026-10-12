# Frontend presentation review — 8 October 2026

## Scope and findings

Reviewed the source and styling of all 37 page routes, grouped into tenant selection/profile/configuration, operations and reviews, strategies, instrument catalogue/detail/creation, market data, trade booking/history/detail, valuation, and the retired P&L route. This was a source audit, not browser acceptance.

The Material UI catalogue, creation hub and review surfaces already establish the console design. Native HTML pages had inconsistent headings, raw calendar/pricing controls, unframed valuation evidence, and forms whose single fieldset occupied one column of an inline strategy grid. Global HTML table rules also leaked into Material UI tables and changed the first native table cell to a grid.

## Changes

- Added one shared `native-workspace.css` presentation layer, imported once from the root layout after the existing stylesheet. It scopes native controls to legacy workspace pages and excludes Material UI controls. Existing component-specific danger, selection and validation styles retain their specificity.
- Aligned native page spacing, heading scale, panel borders, shadows, form controls and links with the current console design.
- Added a reusable `WorkspacePageHeader` with return navigation to futures, options, swaps and booking-convention pages, including their existing service-error branches.
- Corrected fieldset layout in product conventions, listed-option creation and valuation. Kept enriched trade ticket sections under their existing layout rules.
- Framed valuation calculation/history/evidence sections; contained the run table in a horizontal scroll region; styled summary values, disclosures, JSON evidence and review forms.
- Improved calendar/pricing forms and small-screen grid sizing; styled the previously undefined configuration eligible-preview class.
- Scoped old generic table selectors to native workspace tables, excluded Material UI cells, and retained native table-cell layout.
- Added visible keyboard focus and native disabled/checkbox/radio treatment. No loading pages or new dependencies were introduced.

No API permissions, financial calculations, approval flows, request payloads or mutation handlers changed. No operating financial writes, migrations or seed operations were performed for this task. Existing concurrent workspace edits were preserved; the build restored the starting `next-env.d.ts` bytes.

## Guidance checked

The installed Next.js 16.3.4 CSS guide was read before editing. Shared CSS is imported at the root in a stable order and uses scoped selectors to avoid cross-route conflicts.

The requested best-practice skill was applied against W3C primary sources: [visible keyboard focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html) and [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html). These changes improve focus visibility and allow forms to reflow while tables keep their own scrolling region. This is not a claim of complete WCAG conformance.

## Verification and limitations

- TypeScript: passed.
- Frontend tests: 145 files, 682 tests passed with two workers. The first default-worker run had three import-time timeouts; the reduced-worker rerun passed every test without changing assertions or increasing timeouts.
- Next production build: passed.
- Whitespace check: passed.
- Rebuilt console restarted on port 3000. A temporary verification-only cookie session used an existing membership. GET checks returned HTTP 200 for 28 static/main routes, including all primary menu sections and the product creation pages. Updated header/panel markup was checked in served HTML.
- Detail routes requiring existing entity IDs were source-reviewed; they were not all exercised through HTTP.
- Browser automation repeatedly failed during Windows sandbox initialization. No rendered screenshot review, hydration/interaction acceptance or browser accessibility audit is claimed. HTTP success establishes server response availability only.

Refresh localhost:3000 to view the update. A process-only cookie signing key is generated at console restart when no configured key exists; tenant reselection may be required.
