# Strategy workspace implementation plan and execution record

Approved scope: tenant-scoped register and separate creation, strategy overview,
dated executed holdings, position-to-movement drill-down, trade-history links and
calendar visibility. No tax, FIFO, prices, P&L, settlement or operating writes.

Implementation is sequential in the existing feature checkout, as requested.
Preserve unrelated changes. Focused tests only; no full regression, commits,
permission grants or operating-data seed. The approved conversation is the design.

## Tasks

- [x] Quantity-only projection: reuse lifecycle/split reconstruction, preserve
  shorts and nonzero residuals; never depend on valuation pricing support.
  First test +100,+50,-120=30; +100,-150=-50; closed/reopened episodes,
  cancellations, split movements, incompatible units and information cutoffs.
- [x] Read-only scoped strategy holdings and calendars API; paginate after
  aggregation, retain full-history totals; separate STRATEGY_READ, TRADE_READ and
  CALENDAR_READ. Test cross-tenant/selected-strategy rejection and calendar scope.
- [x] Register/create/detail navigation and positions/calendar panels, URL-bound
  date/filter/pagination, lazy movement drill-down and existing trade-history links.
  Test creation gating, nonzero/short display, drill-down and unavailable states.
- [x] Focused regression, TypeScript/contracts, read-only running-app smoke check,
  delivery notes and feature-register/implementation-map reconciliation.

## Decisions and limits

- Executed holdings default; optional valuation-recognised date basis is labelled,
  not a valuation. A date denotes end of UTC day; information cutoff defaults to
  server transaction time. No silently truncated trade scan.
- Positions remain keyed by exact booked subject, currency, units and compatible
  frozen unit conventions. No automatic cross-listing/contract netting.
- Retain full contributing history, not remaining tax lots. Report reconstruction
  failures explicitly rather than asserting zero holdings.
- Calendar assignments are direct; policy/venue references are indirect, labelled
  as such. Show explicit missing assignments and unknown calendar coverage.
- User preference overrides skill defaults requiring a full suite, a new worktree,
  commits or subagents. Author review is not independent review.

## Progress

Existing code and online Carbon/OWASP/IBKR guidance reviewed in the approved
discussion. Backend/console/installed Next guidance read. Work retained on the
existing `codex/tenant-access-transparency` checkout; no commits or subagents.

Quantity checks were added before the implementation (missing module/import),
then passed against the quantity consumer and unchanged default reconstruction.
UI checks failed against the missing workspace and later against unexplained
composite-calendar modes; implementation then passed. Calendar revision regression
failed with two simultaneously active assignments; shared authoritative calendar
decision selection now identifies one current assignment and retained superseded
history. Tests do not assert request-order chronology from database timestamp ties.

Verification: initial combined affected backend run 68 passed (57 existing seed/
framework deprecation warnings); derivative/unit follow-up 39 passed (one framework
warning). UI/access/creation follow-up 13 passed. TypeScript and OpenAPI freshness
passed; generated TypeScript refreshed. Final holdings/calendar regression result
is recorded in the delivery note. Existing strategy HTTP tests were preserved.

Local acceptance: normal temporary local session rendered register, create,
mock holdings and calendars; test session revoked. Read-only API verified mock
bond 100,000 nominal / two trades. No operating data or permission writes, schema
changes or financial calculations. Local API restarted for activation.

Ruling: fail closed for the entire holdings response on invalid unit/action/ledger
evidence rather than partially return holdings; costs availability, avoids a false
complete book. Register filter/paging reuses its full existing scoped list; holding
and movement pagination are server-side after complete aggregation. Scale work
and independent/visual-browser review remain explicitly outside this acceptance.

Author self-review checked scoped IDs, exact quantities, flat/reopened and short
histories, product-unit keys, FX-forward maturity identity, cutoff preservation,
calendar assignment revisions and page error handling. It is not an independent
review or a production/financial sign-off.
