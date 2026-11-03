# Shared instrument display — 26 October 2026

**Status:** Implemented, verified and locally active  
**Scope:** Read-only names and identifiers across main Operations Console workflows

The bond-only valuation ISIN patch is replaced by one product-aware display
policy. It prefers business names, useful identifiers and explicit venue/currency
context across valuation, strategy positions/measure rows, catalogue, trade
history/detail headings and cash/product/option/FX-forward booking search.

Examples include a treasury bill with ISIN, an equity with its listing ticker and
venue, a future with its contract symbol and a swap with its approved tenant
reference. A listing uses the canonical parent's name but retains its own ticker,
venue and link anchor. Missing identifiers are stated explicitly. Internal import
codes remain searchable and in existing technical details.

## Implementation and security

[Maintained rules, source rationale and limits](../architecture/security-master/instrument-display.md).
[Design](../superpowers/specs/2026-10-26-instrument-display-design.md) and
[execution plan](../superpowers/plans/2026-10-26-instrument-display.md).

The shared policy is below HTTP, and the resolver reads only currently visible
references, including private-parent checks. Exact IDs key response sidecars;
names are not keys. The existing financial DTOs remain unchanged: presentation
fields are not placed inside frozen booking terms, request payloads or calculation
fingerprints. Current labels cannot replace historical calculation evidence.

The initial navigation review caught canonical-only detail URLs being given
listing IDs. A shared helper now retains listing identity as an anchor on the
canonical page, and listing rows provide those anchors. Existing distinct listings
are not merged. No operating trade, market observation or valuation was changed.

## Verification

- **1,050 frontend unit tests passed in 212 files.** A subsequent targeted trade
  guard regression verifies that an empty resolved map cannot restore a current
  master name; the frozen booking name remains in booking evidence. The final
  focused frontend rerun passed **44 checks in four files**.
- **45 final focused backend/API checks passed**, including resolver rules,
  identifier dates/venue, private parents, >500-ID batching, response-envelope
  parity, unchanged financial JSON, valuation DISPLAY denial, catalogue paging
  and holdings identifier search. The earlier broader scoped run also passed
  150 checks across trade history, cash/product/option/FX-forward booking and retry
  workflows. These sets overlap; no combined unique-test count is claimed.
- The catalogue test compares identical authorised HTTP reads with and without
  the metadata sidecar. It verifies two extra bulk queries, or three when a page
  contains swaps, rather than retaining an obsolete absolute middleware budget.
  Base query cost stays constant across 1/25/100-row pages; rows/counts are equal.
- **13 existing isolated P&L browser journeys passed**, including DISPLAY denial.
  **Two new headless Edge journeys passed** for product-aware labels, distinct
  listing links, alias search, keyboard inspection/focus return and narrow layout.
  The Instrument type heading and cells are explicitly checked as centred. The
  fixture uses the same scoped report wrapper as production. Its initial missing
  wrapper was a test-fixture defect, not a production CSS change.
- TypeScript and exported OpenAPI parity passed. Generated API types were
  regenerated for the additive display contract. No full Python suite was run.
- Screenshot inspected: local ignored artifact
  `apps/ops-console/test-results/shared-instrument-display.png`. Business names,
  identifiers, context and centred type values remain readable; technical import
  aliases are absent from visible row labels.
- API 8001 restarted against the existing Docker-configured operating database;
  frontend 3001 responds. Read-only catalogue verification returned
  **UKTB 0 02/08/27 · ISIN GB00BSGRDR82 · GBP denomination**. No migration or
  financial-data write was needed. The initial launch used an incorrect database
  name and was corrected before this operating-data check.

Local logs: `logs/instrument-display-ui-final.log`,
`logs/instrument-display-final-api.log`,
`logs/instrument-display-browser.log` (13 existing journeys),
`logs/instrument-display-browser-final.log` (two new journeys),
`logs/instrument-display-contract.log` and `logs/instrument-display-types.log`.

## Remaining boundaries

- Reference-data names/IDs are reused, not cleansed or sourced externally.
- No financial revaluation, instrument rename, weights, or data migration.
- No whole-codebase, production-performance or assistive-technology sign-off.
- Work is sequential in the authorised dirty feature checkout; no automatic
  commit, push or independent subagent review is claimed.
