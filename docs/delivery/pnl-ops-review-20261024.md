# Daily P&L review and publication workspace

**Status:** Implemented; focused verification and local activation below
**Content type:** Delivery record
**Owner:** Valuation / operations console
**Last reviewed:** 2026-10-26

## Intent

Help Ops review and explicitly publish daily trading P&L. This is not an external
reconciliation module, a new calculator or complete fund NAV. The approved
[plan and source research](../superpowers/plans/2026-10-24-pnl-ops-review.md)
retains Input form, Results and History and the original authority boundaries.

## Delivered behavior

- Readable strategy/code, policy/version, currency, instrument/code/venue,
  dataset/provider and rule labels replace primary UUID text. Full IDs remain in
  technical disclosures with copy controls. Missing names are explicitly unavailable.
- Batch presentation resolves the entire retained position population, using
  bounded 500-ID SQL chunks, rather than the visible 20 positions. Amendment
  choices share these labels. Report contexts can resolve inactive policy versions.
  No per-position browser label requests are needed for new API responses.
- Current accessible labels are **not** historical economic terms. They live in
  response-only `presentation` / `display` fields, outside result evidence/hashes.
  Listing venue/currency and frozen unit/multiplier/factor captions distinguish
  similar names and compatible-position buckets; no cross-listing netting is added.
- Whole-result headline amounts: total recorded P&L, price/FX P&L, supplied
  interest and other components. Gross/net/market exact amounts remain separately
  inspectable. Interest and other rollups group stored components with Decimal on
  the server; no financial calculation or trade allocation happens in JavaScript.
- Compact full-width position report with full-population name search,
  attention-only filtering and exact signed-decimal P&L sorting before pagination.
  Headlines always cover the whole selected result, not the visible/filtered page.
- Selected position shows frozen boundary quantities, conventions and period
  executions. A compact price/FX table compares exact used values, requested and
  actual market dates, freshness and named sources/rules. Source/normalization
  proof, applied rules, source IDs, lineage and JSON remain available on demand.
- The position inspector has **Close details**. Closing returns keyboard focus
  to its row (or the position heading for the initially shown inspector) and
  expands the position table to the full available report width. **Inspect
  position** reopens it for that row; filters, sorting and pagination remain.
  No visibility preference is persisted across separate results. At narrow
  widths the detail remains stacked rather than becoming a modal.
- Known stale-source / pending-amendment blockers are separate from optional
  interest warnings and external-comparison information. Missing interest is not
  a sourced zero and remains publishable in optional mode, subject to other checks.
- Publication confirmation repeats the selected strategy, dates, policy, currency,
  total, review mode and warnings, and still requires a decision comment. Existing
  independent and explicitly authorised self-review paths are unchanged.
- Refresh selected result reloads review metadata. Successful amendment changes
  also refresh the selected result's pending-request count. Neither client state nor
  a displayed warning summary is a publication attestation.

## Preserved boundaries

26 October: the inspector-close increment is followed by the implemented
[selected report tabs](valuation-report-tabs-20261026.md): Breakdown, Positions &
cash, Review and Logs. Shared financial context, actual input warnings and
publication controls remain visible; no calculation or authority change.

Financial projections are attached only after the existing batch DISPLAY check.
Denied detail never gains presentation labels, line items or monetary rollups.
Report labels use tenant and action-bound strategy scope; instrument labels reuse
the subject/private-parent visibility predicate. Dataset provider ownership, rule
policy scope and user tenant membership constrain metadata reads. No public or
client-supplied-ID metadata endpoint, new permission or rights grant was added.

The valuation engine, persisted attribution values, revisions, hashes, audit
events, request identities and publication implementation are unchanged. Existing
server checks still decide current access, source revisions, pending amendments,
financial reconciliation and real-operator independence. No database migration.

## Verification

- Lightweight exact-grouping / missing-interest tests were written first.
  UI test-first checks cover report behavior, full-result search, exact decimal
  ordering, frozen-bucket disambiguation, compact inputs and accessible exact totals.
- 51 focused isolated PostgreSQL regressions passed, covering presentation,
  history/API, staging, amendments, strategy scope and self-publication. A follow-up
  15-test isolated run also passed for the final presentation/history/reassessment
  changes (overlapping coverage, not 66 unique tests).
- Native staged-result comparison asserts summary, component amounts, net amounts
  and complete frozen evidence remain identical before/after decoration. Additional
  checks cover 27 distinct references beyond the first page, duplicate names,
  foreign-private parent denial and restricted financial disclosure.
- Four isolated Edge browser journeys passed: optional and strict accrual ticket
  staging/publication, legacy bounded-label fallback, and the new Ops review flow.
  The latter searches position 27, uses attention filtering, inspects named sources
  and exact prices, explicitly opens a technical ID and publishes synthetic data
  only after the required comment. Narrow-screen document overflow check passed.
- Visual inspection of the synthetic narrow-screen result led to the compact
  input table and removal of a duplicate interest warning.
- Final focused frontend verification: **67 tests passed across 13 files**;
  TypeScript, deterministic OpenAPI check and whitespace checks passed.
  The full Python suite and complete manual assistive-technology audit were not run.
- Verification emitted existing Starlette/httpx and browser colour-environment
  warnings; these are not financial failures and were not hidden.

## Local activation and missing-name investigation

While implementation was in progress, the frontend hot-reloaded against the old
API, so its compatibility path could not label every position. The API on port
8001 was restarted using the verified existing local database. Health returned
200; read-only inspection of the existing FCAGF result confirmed all **27 of 27**
position references resolved. UI remains on port 3001. No recalculation,
publication, trade edit, seed, rights change or operating database migration was
performed during activation. Refresh/reopen an already loaded result to receive
the new metadata.

## Deliberate limitations

Subsequent approved [source coverage widget](pnl-source-coverage-20261024.md)
adds a complete source vocabulary, exact stored-component reconciliation and
explicit cash FX exclusion. It does not change the calculation limitations below.

- Metadata describes current accessible names, not name snapshots at calculation.
  Retired/inaccessible references may remain unavailable; UUID evidence is retained.
- Old/alternate API responses use the previous bounded label fallback and cannot
  supply new server component rollups. They explicitly show unavailable metadata,
  not invented amounts. The active API enriches older stored results at read time.
- Historical result formats missing quantities, selections or economic evidence
  say Not recorded. No retrospective reconstruction in the browser.
- Pending counts/source health are snapshots when read. Refresh is available;
  publication always rechecks server-side. Unperformed checks are not green badges.
- Search/order operate over the already-authorized full result response. This
  introduces no calculation cap but does not solve very large-result payloads or
  asynchronous processing. History filtering/paging remains server-side.
- Narrow reports use horizontal table scrolling, not a spreadsheet/grid library.
  No thresholds for "unusual P&L", automatic sign-off, exports, tags, weights,
  external comparisons, cash P&L or full NAV were added.
- Implementation/review was sequential as requested. Final review was an author
  self-review, not independent code-review or production financial sign-off.

## Source-backed design choices

The plan retains the direct sources, review date and applicability. GOV.UK tables
informed numeric alignment and semantic comparison; GOV.UK details informed
secondary evidence disclosure, not hiding warnings. Carbon's table guidance
(30 September 2026 update) informed compact rows and progressive inspection.
GOV.UK check-answers and WCAG 2.2 SC 3.3.4 informed contextual confirmation, not
a claim that this UI is independently certified or a prescribed accounting model.

## Code and tests

26 October inspector follow-up: **84 focused frontend tests** and one isolated
Edge journey passed. The journey closes/reopens at 1800, 1280 and 760px, checks
full-width geometry, preserved search/attention filters and keyboard focus, and
still publishes synthetic data only after explicit review. The component test
first failed on the absent close control. TypeScript and whitespace checks passed.
No backend/data change or restart is needed; the dev frontend hot-reloads. Report
sub-tabs remain a separate proposed change. No full suite or new financial
acceptance is claimed.

- [Read-only API projections](../../apps/reference_api/valuation_presentation.py)
- [Scoped API integration](../../apps/reference_api/valuation_routes.py)
- [Report model](../../apps/ops-console/src/features/valuation/ops-review-model.ts)
- [Result report](../../apps/ops-console/src/features/valuation/result-workspace.tsx)
- [Publication confirmation](../../apps/ops-console/src/features/valuation/publication-action.tsx)
- [Projection tests](../../tests/test_valuation_presentation_api.py)
- [Browser journey](../../apps/ops-console/browser-tests/pnl-ops.spec.ts)
