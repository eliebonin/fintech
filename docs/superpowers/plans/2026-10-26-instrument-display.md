# Shared instrument display implementation plan

> **For agentic workers:** use superpowers:executing-plans sequentially; the user
> has already approved implementation and asked not to pause for plan approval.

**Goal:** Name-first instrument identity with useful, product-aware identifiers
and listing context across the main read/selection workflows.

**Architecture:** One pure policy below the API; one tenant-visible, batched API
resolver; additive presentation sidecars (never booking snapshots); one reusable
React display component. No data migration or financial change.

**Tech stack:** Python/SQLAlchemy/Pydantic, Next/React/TypeScript, pytest/Vitest/
isolated Playwright; existing tooling and dependencies only.

**Spec:** ../specs/2026-10-26-instrument-display-design.md

## Global constraints

- Work in the current authorized feature checkout; retain unrelated dirty edits.
- No subagents, automatic commit/push, operating data writes or full Python suite.
- New display metadata must not enter frozen booking models or fingerprints.
- Names/identifiers cannot bypass tenant, private-parent, strategy or DISPLAY checks.
- Exact links and distinct contracts/listings remain distinct. No invented codes.

## Review focus

Venue-qualified identifier selection; hidden/private parents; share-class identity;
unavailable metadata without internal-code promotion; unchanged financial snapshots.
Each is exercised below, not inferred from a component snapshot.

### Task 1: Shared policy, visible bulk resolver and presentation contract

Files: `security_master_schema/instrument_display.py`,
`apps/reference_api/instrument_display_contracts.py`,
`apps/reference_api/instrument_display.py`, `apps/reference_api/contracts.py`,
`apps/reference_api/valuation_presentation.py`, focused `tests/test_instrument_display*.py`.

Interfaces: `make_instrument_display(...) -> dict`,
`load_instrument_displays(connection, tenant_id, reference_ids) -> dict[str, InstrumentDisplayView]`,
`decorate_response(connection, tenant_id, response, reference_ids)` attaches only
`meta.instrumentDisplays`. Valuation gets the same map in its presentation.

- [x] Write pure policy cases for all supported product families, meaningful
  business codes, missing identifiers, canonical/listing scope and exact names.
- [x] Run focused pytest; observe missing policy failures, then implement.
- [x] Write disposable tests for valid/expired/future and venue-bound identifiers,
  private parents, >500-ID chunking, no-underlying inheritance and unchanged inputs.
- [x] Observe RED; implement bounded authorized reads; run GREEN and existing
  presentation/history regressions.
- [x] Export/regenerate additive API contract and verify it. Do not commit a dirty
  repository merely to satisfy plan bookkeeping.

### Task 2: Integrate read APIs and the shared display component

Files: catalogue/reference/trade/booking read adapters, `strategy_workspace.py`,
`apps/ops-console/src/components/instrument-label.tsx`, related read adapters,
valuation workspace/model, strategy and measure tables, trade history/detail,
instrument catalogue and booking search results.

Interfaces: `InstrumentLabel({display, fallbackName, href?})` renders a semantic
name and second line; `instrumentDisplayText(display)` supports plain options and
client result filters. Consume sidecars without modifying economic view models.

- [x] Write render/filter cases: name first, recognised ID/context, explicit missing
  ID, no exposed internal-code fallback, usable links, no duplicate ticker/name.
- [x] Observe RED; implement the component and scoped styles.
- [x] Attach sidecars after existing read authorization/population selection;
  retain complete search/paging and exact listing IDs. Strategy search includes
  new business identifiers before pagination.
- [x] Use shared component in the listed surfaces; retain raw IDs and frozen
  financial terms in existing detail/inspection disclosures.
- [x] Verify focused frontend tests, read/API contracts and unchanged booking JSON.

### Task 3: Acceptance, documentation and activation

Files: isolated browser tests and maintained capability/register/implementation
map plus a delivery record and research sources above.

- [x] Run complete frontend unit tests with bounded workers and TypeScript;
  focused disposable backend/API/contract suites only.
- [x] Run isolated browser journeys for identities across product types,
  listing separation, filters/paging, keyboard/mobile and DISPLAY denial.
- [x] Do a separate sequential review against the spec and fix evidenced defects
  with RED/GREEN regressions. Record the self-review limitation; no subagent.
- [x] Update docs and record exact tested scope/remaining boundaries; validate links.
- [x] Restart only the local API if needed and health-check; no migration or
  operating financial calculation/publication. Confirm actual labels read-only.

## Execution ledger

- Planning: scope approved in chat; current `codex/pnl-ops-review` checkout is
  intentionally reused under the earlier explicit user choice. No independent
  whole-branch audit/commit is claimed for the pre-existing dirty work.
- Pre-flight: Task 1 owns the display schema and sidecar; Task 2 consumes those
  exact names. Financial booking DTOs are excluded from mutation deliberately.

- Completed: shared policy/sidecars and listed read/search surfaces; listing anchors;
  45 final focused API checks, 1,050 frontend unit checks, 13 existing report and
  two new identity/centering/mobile browser checks. TypeScript/OpenAPI parity pass.
  Local API/frontend activated and catalogue checked read-only. Separate sequential
  self-review found and corrected listing navigation and missing-map fallbacks;
  this was not an independent security or whole-branch audit. See delivery record.
