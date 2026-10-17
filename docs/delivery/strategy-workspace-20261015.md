# Strategy register, holdings and calendar workspace

**Status:** Local alpha implementation and focused acceptance  
**Reviewed:** 2026-10-15  
**Capability:** [F05](../product/features/access-and-strategies.md#f05-strategies)

## Intent and navigation

The tenant strategy register is now an entry point to a strategy, not a combined
creation form and listing. `/strategies` offers accessible strategies, name/code,
type/status filters and 25-row presentation pages. `/strategies/new` retains the
existing creation API and atomic initial-group access; STRATEGY_CREATE controls
the action. Creation does not grant operational ownership.

`/strategies/{strategyId}` defaults to Positions and offers Overview and Calendars.
Trade history links to the existing history page with the strategy code selected;
it is not a second trade register. Archived strategies remain available through
the register's status filter. No tax, FIFO, prices, financial exposure, market
value or P&L calculation is added by this delivery.

## Holdings semantics

### Contract dates and attention

The compact table now includes maturity/expiry with inline attention text. Dates
come only from retained BOOKED economics (product/option terms or forward valuation
conventions); premium/physical settlement dates and current master dates are not
substituted. Futures explicitly show **Last trading**, not an inferred maturity or
final settlement. No date is manufactured for an equity or perpetual instrument.

Warnings compare the saved date with the selected UTC **as-of date**, not today's
wall clock: an open long or short past its date is flagged; same-day maturity,
expiry or last trading is labelled separately. Flat positions get no open-exposure
warning. Missing/invalid dates on dated instrument types and conflicting dates
across contributing bookings are flagged, with no arbitrary first-date selection.
Legacy cash-booked dated instruments without saved dates therefore show missing
date evidence rather than silently adopting current terms. Missing core BOOKED
evidence still blocks the holdings read under existing rules; this is not a partial
position-health certification or the deferred Ops notification dashboard.

These additions are read-only: maturity does not zero quantities, generate closing
trades or cash, confirm payment, or change valuation/P&L. Missing/conflicting-date
messages refer specifically to frozen contract-date evidence. No last-trade-date
column was added. See [date extraction](../../positions/holdings_repository.py),
[attention projection](../../apps/reference_api/strategy_workspace.py) and
[workspace component](../../apps/ops-console/src/components/strategy-workspace.tsx).

Focused verification: 27 Python quantity/date/chart tests, 12 workspace/chart
component tests, seven isolated holdings HTTP tests and TypeScript passed. HTTP
tests confirm current-reference date changes cannot rewrite the displayed booked
date (one existing Starlette/httpx deprecation warning). API restarted; both live
mock swaps show 2027-10-15 with no premature warnings. No operating records were
modified and no full regression or browser visual acceptance is claimed.

### Grouping, density and quantity semantics

Positions are grouped by booked instrument type (Equities, Bonds, Swaps, etc.),
with groups and instrument names ordered alphabetically on the server **before
pagination**. Each page repeats its applicable group headings; a group may span
pages. Classification uses frozen holdings product basis, with ETF/option aliases
normalized for display; it never infers product type from quantity units. Unknown
legacy types appear as Other instruments. This is grouping, not financial netting.
The compact table hides subject UUIDs and places units beside quantity; original
IDs remain in API evidence and drill-down links. Quantities and separate contracts
are unchanged.

Density follow-up: scoped cell/header padding is 5px vertically, smaller direction
badges and inline quantity units avoid two-line rows. These selectors explicitly
outrank shared table padding and do not affect other tables; links retain a 24px
minimum target height.

Grouping follow-up verification: 15 focused quantity/chart Python tests and 11
workspace/chart component tests passed; six holdings HTTP tests passed in an
owned disposable database (one existing Starlette/httpx deprecation warning).
TypeScript passed. API restarted and live Strat Testing read verified nine
equities followed by two swaps, each alphabetically ordered. No operating records
were changed, no full suite or visual browser acceptance is claimed.

- Default: executed holdings at the end of a selected **UTC** date. Optional
  VALUATION_RECOGNISED uses the existing deferred recognition date, clearly labelled;
  it does not run a valuation or select a pricing policy.
- Net signed quantities, including shorts and nonzero residuals: buys 100 and 50,
  sell 120 leaves 30; buy 100 and sell 150 leaves -50. Nonzero holdings are the
  default; Include closed positions exposes flat histories.
- Complete relevant history is scanned in 500-trade keyset batches. There is no
  1,000-trade cap or recent-trade-window approximation. Aggregation and filtering
  precede server-side position pagination; movement pagination follows a complete
  running-quantity calculation. Decimal strings remain exact.
- The quantity consumer reuses `positions.reconstruction`, lifecycle validation
  and reviewed share-ratio replay with a quantity-only key builder. Existing
  valuation callers keep their original key/price requirements. Zero, absent or
  negative execution prices do not prevent a quantity-only holding.
- Exact booked subject/listing, trade currency, quantity units, product basis
  and compatible frozen unit conventions distinguish positions. No automatic
  cross-listing, lookalike-contract or tax-lot netting. Forward maturity and its
  original contract normalize to the same holdings identity.
- Drill-down retains all contributing buys/sells and reviewed ratio movements,
  including previously flat episodes. It shows signed/running quantity, original
  execution price/rate and trade links; it does not allocate remaining purchase
  lots or calculate cost basis. Same-instant trades have a deterministic ID order,
  not an asserted execution sequence within that instant.
- Cancellations/replacements follow retained lifecycle evidence at the information
  cutoff; a cancellation is not an opposite trade. Stock splits affect projected
  units without rewriting the original trade. Maturity alone does not flatten a
  position: an actual closing booking must exist.
- Source/identity/unit ambiguity, unsupported corporate actions or incomplete
  lifecycle evidence block the holdings response with a readable error rather
  than present incomplete quantities as a zero/complete book. This first pass
  blocks the whole view rather than returning potentially misleading partial rows.
- Positions and movement links retain an information cutoff for consistent
  pagination/drill-down. Applying filters starts a fresh read. This is a live
  ledger view, not an immutable published valuation. Cash-amount flows and the
  separate dated cash-balance snapshots are not security holdings.

## Calendars

CALENDAR_READ is required within the strategy scope. The page displays direct
strategy assignments with purpose, pinned calendar version, timezone, effective
period, coverage, reason, composition and source evidence. It reuses the existing
calendar decision selector to identify the current assignment; prior revisions
are retained and explicitly marked superseded. Closures and unknown dates over
the selected date plus 30 days can be inspected; select another date to inspect
another window. ALL_OPEN/ANY_OPEN have plain-language explanations and component
calendar names. Missing coverage remains UNKNOWN.

Indirect references are separately labelled: calendars from available policy cuts,
rules/rule-specific cuts, and booked venue history. These do not assert a direct
assignment, a policy actually selected for valuation or a rule actually matching a
holding. Venue-use context is shown only with strategy TRADE_READ authority.
No calendar assignment or policy is created or changed by visiting these pages.

## Security and boundaries

The API checks STRATEGY_READ and the appropriate additional scoped action:
TRADE_READ for positions/movements, CALENDAR_READ for calendars. The central
boundary maps the new routes to these actions and resolves the owning strategy.
Direct IDs and pagination do not bypass tenant/group scopes. The UI uses existing
server-side context/session forwarding; no new browser-selected authority headers
or direct database access. Missing rights are reported, not represented as no data.

Read-only routes:

- `GET /v1/strategies/{id}/positions`
- `GET /v1/strategies/{id}/positions/{positionId}/movements`
- `GET /v1/strategies/{id}/calendars`

Implementation: [quantity projection](../../positions/holdings.py),
[batched adapter](../../positions/holdings_repository.py),
[API](../../apps/reference_api/strategy_workspace.py),
[strategy detail](../../apps/ops-console/src/app/strategies/[strategyId]/page.tsx),
[presentation](../../apps/ops-console/src/components/strategy-workspace.tsx).

## Research applied

Checked 15 October 2026; these are design references, not compliance certification.

- [IBM Carbon table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines): filtering/pagination and progressive disclosure; substantial details belong in a dedicated page or panel rather than deeply nested tables. Applied to register → strategy → movement drill-down.
- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): least privilege, deny by default and per-request authorization. Applied to parent strategy and action-specific direct-ID checks.
- [IBKR View Lots](https://www.ibkrguides.com/advisorportal/ug/view-lots.htm), updated 19 May 2026: position-to-lot drill-down is a recognizable navigation pattern. Our movement history is deliberately **not** its tax-lot/cost-basis functionality; no tax-accounting convention was imported.

## Verification and limitations

Focused quantity tests cover exact residual/short/flat/reopened positions,
recognition dates, cancellation cutoffs, incompatible keys, reviewed stock splits,
more than 1,000 executions and frozen derivative unit conventions. HTTP tests
exercise real handlers/PostgreSQL using only an owned disposable database, including
netting before pagination, movement reconciliation, separate permissions,
cross-tenant/strategy denial, cancellation and sourced calendar assignment revisions.
Existing strategy/scoped-access and position/split regressions remain in the check set.

Initial combined run: **68 passed**, with 57 existing framework/seed deprecation
warnings. UI/creation/access checks: **13 passed**. TypeScript and OpenAPI freshness
checks passed, generated TypeScript refreshed. Final holdings/calendar HTTP and
quantity follow-up: **17 passed**, one existing framework deprecation warning.
The calendar revision check confirms one current assignment with superseded
history according to the existing recorded-time/ID selector, not assumed request
chronology. No full suite, independent review,
production build, visual browser acceptance or tax/financial sign-off is claimed.

Running local API restarted; authenticated HTTP checks rendered the register,
creation, mock strategy holdings and calendars successfully. A temporary normal
local session was revoked afterwards; the user's browser context was not changed.
The existing mock strategy showed one 100,000-nominal bond position from two trades.
No migration, permissions, operating trades, cash balances or valuations were changed.

Deliberate alpha trade-offs: scoped strategy register filtering/paging uses the full
existing API list in the browser; holdings aggregation and movement generation are
in memory after batched reads and recompute per request. Calendar references are
unpaged, and per-definition metadata lookup is cached within one request. Large-book
scale testing/caching, per-position partial-error reporting, cross-listing grouping,
custodian reconciliation and richer strategy/vehicle editing remain separate work.

## Position-history chart follow-up — 15 October 2026

A quantity-only chart now appears beneath the position movement table. A step
line holds the cumulative position flat between dated events and extends to the
selected end-of-day UTC cutoff. Positive bookings and negative bookings have
separate bars on one shared quantity axis; reviewed share-ratio changes use
diamond markers, not trade bars. Shorts, flat/reopened histories and original
booking/split semantics are unchanged. There is no tax, FIFO, price, exposure
valuation or P&L computation.

The existing authorized movement response adds a `chart` object with quantity
units, cutoff and complete time-ordered points **before table pagination**.
Same-instant movements are grouped using exact Decimal arithmetic: buy quantity,
sell quantity, resulting holdings, trade count and separate split adjustments.
Both sides remain visible when simultaneous trades net to zero. The same tenant,
strategy, date basis and information cutoff govern table and chart. No new access
path or permission is added.

The console renders native responsive SVG without a chart-library dependency.
Pointer hover, touch selection and keyboard focus expose exact server quantity
strings. Binary numbers are used only for drawing coordinates/tick labels, never
to recalculate holdings. Missing/invalid chart data is reported; paginated table
rows are never used as a substitute full history. Dates without events do not
require daily synthetic observations. Dense event histories may overlap visually;
the full movement table remains the detailed evidence. Zoom, downsampling and
large-history performance acceptance are deferred rather than silently truncating.

Implementation: [exact summaries](../../positions/chart.py),
[SVG component](../../apps/ops-console/src/components/position-history-chart.tsx).
Verification: 20 focused backend tests passed (one existing framework deprecation
warning); final chart/workspace UI checks 10 passed, including integration beneath
the paginated table. TypeScript and OpenAPI freshness passed. Existing access
regressions were also included in the preceding 15-test UI run. API restarted for
activation; no operating trades, cash, calendars, policies or valuations changed.
Live read-only checks confirmed identical full chart points across movement pages
and successful authenticated SVG rendering for the mock bond's 100,000 nominal.
The temporary local HTTP test session was revoked; browser context was untouched.
No full regression, visual-browser acceptance or independent review is claimed.

## Separate monetary-measures preview — 15 October 2026

The strategy workspace also has a separately authorized **Measures** tab. It
selects an explicit date and versioned pricing policy and displays reference
notional, underlying-equivalent exposure and market value, with native/reporting
currencies and input evidence. It does not change the quantity-only Positions or
movement-chart calculations, calculate weights or publish a NAV/P&L result.
See [position monetary measures](position-monetary-measures-20261015.md) for the
bounded equity/fund, bond and index-swap formulas, permissions and data gaps.
