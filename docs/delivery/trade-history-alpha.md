# Tenant trade history alpha

**Status:** Implemented alpha  
**Content type:** Reference  
**Owner:** Product and platform team  
**Last reviewed:** 2026-09-30

Implemented 30 September 2026. `/trades` is a live, tenant-scoped read view,
not an order blotter, a position calculation, or a settlement dashboard.

## User flow

Use **Trades** in the workspace menu. The page shows newest economic trade
events first, one row per trade, with trade time (UTC), instrument/listing,
strategy, side, absolute quantity and unit, price/currency, settlement date,
and recorded lifecycle status. **Book trade** opens the dedicated booking page.
Open the instrument name in a row to inspect the trade's booking metadata,
parties, fees, source identifiers, and existing append-only lifecycle events.
The back link restores the originating search, filters, page size, and page.

Search matches instrument/subject name, listing symbol, or trade UUID using
case-insensitive literal substring matching. `%` and `_` are literal input,
not SQL wildcards. Search is submitted with **Apply filters** (or Enter),
not a multi-second debounce. Strategy choices are loaded from the selected
tenant's actual strategy register, including inactive/archived strategies.
Optional filters are strategy, inclusive UTC trade dates, BUY/SELL, and status.
All statuses are included by default. The initial date window is the last 14
inclusive UTC calendar dates (today and the preceding 13 dates), using trade
date, not booking or settlement date. For 30 September 2026 that is 17–30
September. Quick links offer Last 14 days, Last 30 days, and All history;
Custom focuses the date form. The active dates are displayed explicitly.
Quick links preserve other filters and reset pagination. Clear filters restores
the 14-day default; All history explicitly removes date bounds. Editing and
submitting the date form selects a custom range; blank custom bounds mean all
history, and a single bound supports an open-ended range. No trade data is
deleted or made inaccessible by this default.

Pagination is server-side, defaults to 25 records, and offers 25/50/100.
It reports the current range and the true filtered total, with previous/next
and direct page entry. Applying filters/page size resets to page 1. An
out-of-range URL redirects to the last available page with filters preserved.
Pagination/filter state lives in the URL; no tenant identifier is accepted
from it. The signed server-side tenant session supplies the API context.
Loading, empty tenant history, zero matches, API errors and retry are separate
states. Failure to load strategy choices does not suppress trade results or
discard the selected strategy filter.
Preset dates are materialized in pagination/detail links so the range does not
shift if navigation crosses UTC midnight. Opening the plain `/trades` route or
choosing a quick preset recalculates against the current UTC day. An empty
default window says “No trades in the last 14 days” and offers View all history,
rather than claiming the tenant has no recorded trades.

## API and history semantics

`GET /v1/trades` retains `portfolioCode`, `fromDate`, `toDate`, `limit`, and
`offset`; adds `q` (at most 200 characters), `side` (BUY/SELL), and
`lifecycleStatus` (at most 30 characters). `portfolioCode` is the existing
wire name for strategy code, not a separate portfolio entity.

- Membership checks remain at the API boundary; ownership is enforced through
  the trade's strategy tenant. Another tenant cannot read its detail.
- History includes inactive strategies and non-BOOKED statuses. This fixes
  previous behavior that silently hid historical records after archival or
  cancellation. The detail route uses the same ownership rules.
- `meta.total` counts all matching records before limit/offset, not page length.
- Date boundaries are UTC midnight inclusive through next-day midnight
  exclusive. Reversed ranges fail validation.
- Ordering is `trade_datetime_utc DESC, trade_id DESC` to resolve timestamp ties.
- Venue MIC comes from one deterministic primary ISO MIC identifier, avoiding
  duplicate trade rows/counts when a venue has multiple identifier schemes.
- List filters are applied in PostgreSQL before paging, not to browser rows.
- This change does not mutate trade records, add lifecycle commands, change
  booking eligibility, or change the P&L calculation's status handling.
- The details return destination is restricted to `/trades` and normalized
  recognized history parameters; external destinations are rejected.

## Best-practice references and project decisions

Sources reviewed 30 September 2026. These are enterprise UX/accessibility
guidelines, not a claim of financial-regulatory compliance. We reuse the
existing console components; no Cloudscape or Carbon dependency was added.

1. [Cloudscape table view](https://cloudscape.design/patterns/resource-management/view/table-view/)
   recommends tables for comparable structured records, column ordering by
   importance, filters, pagination for revisit-able sections, and distinct
   empty/zero-result/error states. Applied to the table-first trade history;
   demo dashboard cards are removed.
2. [Cloudscape view resources](https://cloudscape.design/patterns/resource-management/view/)
   reserves split panels for workflows requiring rapid in-context inspection.
   We retain a dedicated detail route rather than adding a permanent drawer.
3. [Carbon pagination](https://carbondesignsystem.com/components/pagination/usage/)
   describes page-size controls, current range/total, current page, and
   navigation placed below the related table. Applied to the pagination bar.
4. [Carbon data table](https://carbondesignsystem.com/components/data-table/usage/)
   describes visible table search, table navigation and loading skeletons.
   Applied to visible search and the route loading state.
5. [W3C accessible tables](https://www.w3.org/WAI/tutorials/tables/)
   requires structural associations between headers and data cells and
   explains the role of captions. Applied through native table markup,
   column-header scope, caption, labeled controls, and text status/side labels.

The 14-day initial window, 25/50/100 page sizes, explicit submit search, UTC date labels, newest-first
default, and the chosen columns are project decisions, not prescribed values
from these sources. Offset pagination suits the alpha; concurrent insertions
can shift subsequent pages. High-volume snapshot/cursor navigation, query
index tuning, and exact historical reference-data snapshots remain future work.

## Verification and limits

Lightweight regressions were written and observed failing before query/filter
and navigation implementation. Coverage includes totals, archived strategy
detail visibility, tenant isolation, literal search, status and signed side,
API validation, URL normalization, and public client filter forwarding.
Rendered-page tests exercise the real history/detail components and workspace
shell, with only external API/session/navigation boundaries controlled. They
cover real strategy choices, pagination, empty/error states and return links.
Both forms are keyed by normalized URL state so Next client navigation resets
uncontrolled inputs after clearing filters or changing pages. A key-transition
regression and a multi-primary-venue regression cover review-discovered issues.

Live-browser verification used a separate local session: menu entry, the
user's ETP-TEST/STRAT-TEST trade, search, a SELL-only zero-result state, clearing
filters back to default selections, and trade-details navigation with the
preserved search return link. The production build, TypeScript check, all
162 console tests (including the default-range follow-up), OpenAPI export check, and repeatable TypeScript contract
generation passed. An independent read-only review found no remaining
blocking findings after the two regressions above were corrected.
The final full Python rerun passed: **284 tests**, with 398 existing
SQLAlchemy/Starlette deprecation warnings and no failures. The first run's
single failure was an older MVP test assuming the newest trade belonged to a
demo portfolio; it now inspects its known seeded trade while retaining its
fixture and portfolio-filter assertions.
The default-range follow-up changed only console code: the console suite,
TypeScript check, production build, and live HTTP default/all-history views
were rerun successfully. Backend code was unchanged and the Python suite was
not rerun for that follow-up. Date tests cover inclusive 14/30-day windows,
UTC month/year/leap-year boundaries, custom/open-ended ranges, explicit all
history, and pagination after midnight.

Deferred: exports, saved views, configurable columns, amendment/cancellation
commands, settlement confirmation, OTC/derivative booking, positions, valuation,
and P&L integration. A BOOKED trade with a past settlement date is not relabeled
SETTLED. Historical instrument/strategy names are current joined reference
labels, not immutable point-in-time descriptions.
