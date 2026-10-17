# Reviewed findings

**Status:** Open scoped findings  
**Content type:** Review  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-16 (frontend and scoped backend remediation)

Analyzed root: `C:/Users/forte/Elie/projects/python/fintech`. The October 15 review
maps backend/API modules and traces high-risk paths, extending earlier structured-
product, access and valuation reviews. It is not an exhaustive repository defect
backlog or line-by-line security certification. See [review scope](KNOWLEDGE.md).
Documentation alone does not resolve findings. Current October 16 resolution
notes below take precedence over preserved original trigger/evidence text. See
[backend delivery and limits](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md).
BACKEND-009 and MEASURES-005 remain partial; BACKEND-001 remains a deployment gate.

October 14 scope additionally traces supported valuation methodology and frozen
explanations; it does not revalidate every older structured-product finding.

October 15 coupon-focused review: sourced schedules and payment confirmations now
have dedicated immutable storage; this does not close broader receivable/accounting
or source-impact gaps. See [delivery and verification limits](docs/delivery/bond-coupons-20261015.md).

## Backend/API audit — 15 October 2026

<a id="backendapi-audit--15-october-2026"></a>

Reviewed the **working checkout**, branch `codex/tenant-access-transparency`, HEAD
`550399f`, with substantial pre-existing changes. This is not a review of an
assumed clean/pushed main branch. [Coverage, verification and primary sources](KNOWLEDGE.md#backendapi-audit--15-october-2026)
define the confidence boundary. No source-code fixes were made by this audit.

### Recommended repair order

This is the original October 15 repair order. The October 16 current-status notes
under each stable ID record implementation; do not treat this historical list as
evidence that repaired defects still reproduce.

1. **Economic intake correctness:** FIX-SP-001/002 still reproduce. Address nested
   fixing provenance and calendar scope (BACKEND-002/003) in the same boundary work.
2. **Object/strategy scope:** close legacy NAV queue metadata exposure (BACKEND-004).
3. **Measured performance:** MEASURES-005; profile query plans and remove repeated
   work, rather than increasing timeouts or dropping permission/evidence checks.
4. **Request reliability:** event-loop blocking, supplemental audit failure and
   consistent governance time (BACKEND-005/006/007). Preserve mutation/retry semantics.
5. **Maintainability and scale:** explicit selector pagination, domain boundaries,
   typed responses and preview snapshot consistency (BACKEND-008/009/010).
6. **Before any non-local deployment:** BACKEND-001 is a release blocker, not a
   request to replace the explicitly accepted personal/local context selector now.

Previously documented source-impact fan-out, independent financial reconciliation,
large-history/matrix scaling and intermittent bond rebooking remain open under
their existing IDs. Missing futures/forward MTM, full accounting, weights and broad
derivative valuation are agreed scope boundaries, not new bugs.

<a id="frontend-audit-2026-10-15"></a>

## Frontend audit — 15 October 2026

Scope: Operations Console, its BFF and handwritten shared contract interfaces in
the same dirty working checkout. [Coverage, sources and verification](KNOWLEDGE.md#frontend-audit-2026-10-15).
This audit did not change implementation or operating data. The following are
additional frontend findings, not evidence that previously documented backend
issues have been fixed.

**Repair order:** stale-context writes → proposal/retry integrity and error identity
→ refresh/loading truthfulness and exact displays → cross-tab navigation/copy →
browser acceptance and incremental decomposition. Reuse FIX-SP-001/002/003 for the
existing structured economic/default/calendar gaps; do not duplicate those IDs.
Backend scoping/performance and non-local authentication gates remain applicable.

## Resolved frontend findings — 16 October 2026

FRONTEND-001–010 are addressed in the scope of their reviewed defects and bounded refactoring recommendations. [Resolution, implementation, verification and remaining boundaries](docs/delivery/quality-reviews/2026-10-16-frontend-remediation.md). The [original findings](docs/delivery/quality-reviews/2026-10-15-frontend-findings.md) preserve triggers and evidence, including the earlier partial strategy-only fix.

### FRONTEND-001 — Resolved: Shared stale-context write boundary

**Resolution evidence — 2026-10-16:** Next Proxy rejects missing/stale document stamps before any BFF write. Actual two-context browser check passed.

### FRONTEND-002 — Resolved: Upstream request identity

**Resolution evidence — 2026-10-16:** BFF JSON and X-Request-Id retain upstream IDs independently of browser correlation.

### FRONTEND-003 — Resolved: Committed access change / failed refresh

**Resolution evidence — 2026-10-16:** Saved-but-stale state locks edits; recovery reloads rather than resubmits. Server snapshots remount user editors.

### FRONTEND-004 — Resolved: Uncertain proposal / cash intent

**Resolution evidence — 2026-10-16:** Exact payload/key retention, explicit unchanged recovery, known-outcome release, malformed-success protection and navigation warnings.

### FRONTEND-005 — Resolved: Exact cash / fee displays

**Resolution evidence — 2026-10-16:** Decimal-string formatting preserves large, tiny and negative values.

### FRONTEND-006 — Resolved: Register loading / empty states

**Resolution evidence — 2026-10-16:** Cash/coupon pending and unavailable reads no longer imply confirmed absence. Dependent writes require loaded configuration.

### FRONTEND-007 — Resolved: Correction navigation / scope copy

**Resolution evidence — 2026-10-16:** Activate Input, open disclosure, focus register and preserve recorded context. Basis-aware Yahoo explanations and separate cash-preview scope.

### FRONTEND-008 — Resolved: Executable browser assurance

**Resolution evidence — 2026-10-16:** Ten isolated browser cases plus CI browser job. Broader manual accessibility/visual acceptance remains part of F49, not certified here.

### FRONTEND-009 — Resolved: Divergent shared frontend protocols

**Resolution evidence — 2026-10-16:** Consolidated transport, error/retry/navigation/display primitives and browser catalogue implementation; no blanket design-system rewrite.

### FRONTEND-010 — Resolved: Avoidable frontend request amplification

**Resolution evidence — 2026-10-16:** No financial re-selection for currency display, coherent shell props and one bounded visible-label request. Backend SQL latency remains separate.

## BACKEND-001 — P1 for deployment — Header identity is not production authentication

**Evidence status:** Confirmed (static); accepted local-development boundary.

- **Source/function:** [context](apps/reference_api/tenant_context.py),
  `get_tenant_context`/`get_actor_context`; [boundary](apps/reference_api/access_boundary.py),
  `authorization_boundary`; [sessions](security_master_schema/access_sessions.py).
- **Trigger:** Expose this API to untrusted clients without a trusted identity
  gateway. Without a local token, ordinary requests accept caller-supplied actor
  and tenant headers. Setting a non-local environment disables local sessions;
  it does not install authentication for ordinary endpoints.
- **Impact/evidence:** An attacker who supplies an active privileged account ID
  can impersonate that account at this boundary. Membership/action checks still
  run, but against an unverified identity. No deployed exploit is claimed.
- **Fix direction:** Verified authentication adapter, trusted-header stripping and
  fail-closed non-local startup/deployment validation. Keep selected-user testing
  explicitly local. A reverse proxy alone is insufficient without enforced trust.
- **Regression:** Spoofed headers fail in non-local mode; verified identity cannot
  select another actor/tenant; local session expiry, revocation and independence
  checks continue to work. No production sign-off until this is tested end to end.

## BACKEND-002 — P2 — Nested initial-fixing evidence is not scoped/reconciled

**Current status — 2026-10-16:** Resolved for reviewed nested dependency checks; observation/source and approval regressions pass. Snapshot permutation coverage remains bounded. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static); no cross-tenant persistence exploit run.

- **Source/function:** [draft contracts](apps/reference_api/structured_product_contracts.py),
  `validate_autocall_draft`; [repository](apps/reference_api/repository.py),
  `_materialize_structured_product` initial-fixing inserts around line 4071;
  [top-level source guard](apps/reference_api/source_evidence.py).
- **Trigger:** Supply an underlying-level source payload/system, observation or
  resolution-snapshot ID belonging to another tenant or unrelated underlying/date.
- **Impact/evidence:** Validation checks that some provenance ID is present for
  MARKET_DATA/PROVIDER, but does not resolve that evidence. Materialization writes
  nested IDs into ACCEPTED fixings. The top-level source guard does not iterate
  underlying evidence. Global foreign keys establish existence, not ownership,
  source pairing, rights, date/currency/basis or fixing-value agreement.
- **Fix direction:** Resolve each nested provenance reference at submission and
  approval; distinguish manual fixing from a verified sourced fixing. Reconcile
  the selected evidence with underlying/date/units and retain explicit derivations.
  Do not treat resolved FIX-SP-004 as proof that nested provenance is safe.
- **Regression:** Foreign/mismatched source, snapshot, observation and fixing value
  rejected atomically; legitimate shared evidence accepted only under explicit
  scope and rights. Revocation/change between submission and approval revalidated.

## BACKEND-003 — P2 — Structured products can bind a foreign private calendar

**Current status — 2026-10-16:** Resolved for new proposals/approvals: visible, eligible sealed calendars and dependency revalidation. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static).

- **Source/function:** [repository](apps/reference_api/repository.py),
  `_structured_product_catalogue_reference` (line 3458), submission and materializer;
  contrast [visible calendar](market_data/calendar_store.py), `visible_calendar`.
- **Trigger:** Submit/approve a structured product using another tenant's ACTIVE
  private calendar UUID, or an inappropriate unpublished calendar kind.
- **Impact/evidence:** The catalogue helper checks ID and ACTIVE status only and
  takes no tenant argument. Submission and materialization both call it for
  `market_calendar`. New private calendar modelling has outgrown this older check.
  This establishes a scope/integrity defect, not proof of calendar-day disclosure.
- **Fix direction:** Tenant-visible calendar eligibility plus an explicit policy
  for which calendar kinds/published versions are valid contractual references;
  revalidate and pin dependencies transactionally at approval.
- **Regression:** Tenant A cannot reference tenant B's calendar; approved shared
  references and explicitly allowed own-tenant calendars work. Status/scope changes
  between proposal and approval cannot leave an invalid approved dependency.

## BACKEND-004 — P2 — Legacy NAV work-queue entries ignore strategy scope

**Current status — 2026-10-16:** Resolved: strategy predicates precede legacy NAV queue rows/counts/pagination. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static); limited to metadata/counts in the reviewed path.

- **Source/function:** [repository](apps/reference_api/repository.py), `work_queue`,
  NAV query/count around lines 4361–4389; [route](apps/reference_api/main.py), `queue`.
- **Trigger:** A user can read reference operations and has VALUATION_READ for a
  selected subset of strategies; another strategy has a legacy pending Soft-NAV run.
- **Impact/evidence:** `include_nav` tests the tenant-wide permission-code union;
  NAV queries constrain tenant/status but not the row's strategy. Run UUIDs, dates
  and counts can appear outside the permitted strategy subset. Financial totals
  are not returned here; this is not a demonstrated cross-tenant financial leak.
- **Fix direction:** Apply `request_strategy_predicate(..., 'VALUATION_READ',
  nav_calculation_run.strategy_id)` to both rows and counts, or explicitly retire
  this legacy queue category with compatible historical reads.
- **Regression:** Two strategies, selected/empty/ALL groups, reference-only users,
  mixed queue pagination and counts. Unauthorized NAV IDs must not appear.

## BACKEND-005 — P2 — Authorization blocks the async event loop without DB budgets

**Current status — 2026-10-16:** Resolved for the reproduced blocking/budget path: complete synchronous authorization offload and transaction budgets. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static and offline controlled reproduction).

- **Source/function:** [boundary](apps/reference_api/access_boundary.py),
  `authorization_boundary`, synchronous transactions at lines 105 and 158;
  [request budgets](apps/reference_api/resource_limits.py).
- **Trigger:** Slow authorization queries, pool checkout or post-response audit I/O.
- **Impact/evidence:** Blocking SQLAlchemy calls execute directly inside async
  middleware; FastAPI's threadpool handling of normal `def` routes does not offload
  those calls. Two concurrent requests with injected 150-ms connection waits took
  0.352 seconds, both 403, without any database connection. Middleware connections
  also do not call the transaction-budget setup used by route dependencies.
- **Fix direction:** Offload complete synchronous authorization/audit units or use
  an appropriate async adapter; do not share a connection concurrently. Apply
  bounded pool/lock/statement policy consistently. A statement timeout is not a
  whole-request elapsed-time budget for thousands of individually fast queries.
- **Regression:** Concurrent unrelated request remains responsive during slow auth;
  controlled pool/lock timeout produces a correlated safe error and no connection leak.

## BACKEND-006 — P2 — Supplemental audit failure follows an already committed command

**Current status — 2026-10-16:** Resolved for ordinary command atomicity and retained calculation acceptance: audit fault injection now rolls back the command. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static); fault-injected operating write not attempted.

- **Source/function:** [main](apps/reference_api/main.py), function-scoped transaction
  dependency; [boundary](apps/reference_api/access_boundary.py), response draining
  and separate `TENANT_REQUEST` audit transaction after `call_next`.
- **Trigger:** A successful command commits, then the separate supplemental audit
  transaction fails (database availability/timeout/storage error).
- **Impact/evidence:** The outer middleware can return 500 even though the business
  mutation succeeded. A client may retry with uncertain outcome. This does not mean
  domain booking/lifecycle/run evidence is absent; much of it is correctly atomic.
- **Fix direction:** Retain actor/operator provenance transactionally with command
  results, or a durable outbox for supplemental events; define explicit handling
  of audit-delivery failure and idempotent replay. Do not silently ignore audit failure.
- **Regression:** Fail only the post-command audit; verify exactly one mutation,
  recoverable audit evidence and a truthful response/retry contract.

## BACKEND-007 — P2 — Governance effective dates mix host-local and UTC clocks

**Current status — 2026-10-16:** Resolved: shared request-pinned UTC governance clock; explicit financial and venue dates unchanged. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static); observed expiry-boundary incident not claimed.

- **Source/function:** [UTC helper](apps/reference_api/resource_limits.py),
  `governance_date`; [reference authority](apps/reference_api/reference_authority.py),
  [boundary](apps/reference_api/access_boundary.py), [strategy authority](security_master_schema/strategy_access.py),
  [access administration](security_master_schema/access_management.py),
  [display rights](market_data/display_access.py).
- **Trigger:** Host-local date differs from UTC around midnight; a membership,
  module or data entitlement begins/expires on that boundary.
- **Impact/evidence:** The same request can pass one authority layer and fail
  another using different dates. `date.today()` and explicit UTC helpers coexist.
  The question is governance time, not exchange-session time or trade recognition.
- **Fix direction:** Choose/document the governance-date convention and inject a
  consistent clock across relevant checks. Preserve explicit exchange/fixing zones.
- **Regression:** Effective-date boundaries with a non-UTC host, including DST;
  module, strategy and dataset decisions agree for the same request.

## BACKEND-008 — P2 — Valuation selectors silently truncate at 500

**Current status — 2026-10-16:** Resolved for silent truncation: scoped search/page/count/selected lookup and paged primary UI. Legacy full bootstrap remains a scaling trade-off. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static).

- **Source/function:** [valuation routes](apps/reference_api/valuation_routes.py),
  `options`, lines 64–72.
- **Trigger:** More than 500 readable strategies or active policy versions; growing
  cryptocurrency currency catalogues can reach the same currency-selector cap.
- **Impact/evidence:** Each collection is independently limited to 500, without
  paging/count/truncation metadata. Valid records disappear from the selector;
  immutable active policy versions accumulate. This is not the removed trade cap.
- **Fix direction:** Searchable, paged selectors; preserve action-scoped filtering
  before paging and fetch the explicitly selected ID even outside the first page.
- **Regression:** 501+ synthetic entries, correct counts/next page and selection of
  the last eligible item; no widening of read-only users' calculation permissions.

## BACKEND-009 — P3 — Domain/transport boundaries and legacy interfaces have drifted

**Current status — 2026-10-16:** Reviewed lower errors/authority/visibility/controls/forward-loader and Future/Swap model extraction completed after explicit approval. All five reviewed service import guards are mandatory; API compatibility imports, complete OpenAPI and representative frozen JSON remain unchanged. Broader decomposition and remaining compatibility imports in `valuation/accruals.py`, `valuation/amendments.py` and `lifecycle/bond_service.py` remain open; BACKEND-009 is not blanket-closed. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static); refactoring need, not itself a security exploit.

- **Source/function:** [repository](apps/reference_api/repository.py), 5,178 physical
  lines; [main](apps/reference_api/main.py), 1,179; [models](security_master_schema/models.py),
  3,005. Domain imports of transport-owned functions occur in
  [forward normalization](positions/fx_forward.py), [measure inputs](valuation/measure_inputs.py),
  [coupon service](lifecycle/coupon_service.py), [flows](valuation/flows.py) and
  [FX lifecycle](lifecycle/fx_service.py). [Legacy NAV](security_master_schema/soft_nav_service.py)
  remains separate from the active position P&L engine and monetary preview.
- **Trigger/impact:** New product/governance rules are added in one path but missed
  in another. Local imports conceal cycles; broad dict responses and ad hoc frozen
  JSON make interface drift harder to catch. Most code volume is not inherently a bug.
- **Fix direction:** Incrementally extract reusable identity/authority, reference
  dependency validation and booking-proof adapters into lower-level services;
  keep API routers thin and typed at stable boundaries. Explicitly catalogue legacy
  readers/helpers and do not delete retained evidence/schema compatibility blindly.
- **Regression:** Architecture import checks plus contract parity for cash, bond,
  future, option, swap and forward bookings; existing hashes/replay identities stay stable.

## BACKEND-010 — P2 — Monetary preview does not use the calculation snapshot boundary

**Current status — 2026-10-16:** Resolved for reviewed preview consistency/revocation/pool paths: repeatable-read inputs plus fresh current-rights release check. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Suspected concurrency risk; no inconsistent financial output reproduced.

- **Source/function:** [request connection](apps/reference_api/main.py),
  [strategy measures](apps/reference_api/strategy_workspace.py), `snapshot`/`measures`;
  contrast [runner](valuation/runner.py), `calculation_transaction` REPEATABLE READ.
- **Trigger:** Concurrent source/governance/ledger changes during a long preview.
- **Impact/evidence:** The preview uses the ordinary default-isolation request
  connection and many sequential reads; a timestamp filter alone does not create
  a PostgreSQL transaction snapshot. Current rights checks are intentionally current,
  so not every intervening governance change is an inconsistency.
- **Fix direction:** Define which preview inputs must share a stable snapshot and
  pin their versions; separately preserve current authorization/display checks.
  Do not simply cache across tenants, actors, information cutoffs or revocations.
- **Regression:** Deterministic two-connection mutation during a preview, checking
  holdings/marks/FX/evidence alignment and current permission revocation.

## MEASURES-004 — Resolved — Base-flat forward could hide incompatible quote obligations

**Evidence status:** Confirmed (static trigger and regression, fixed 2026-10-15).

- **Source/function:** [strategy workspace](apps/reference_api/strategy_workspace.py),
  measures filtering; [forward proof adapter](valuation/forward_measures.py),
  `contractual_legs`.
- **Trigger/impact:** Same canonical forward booked under incompatible frozen agreed
  rates; offsetting base quantities can leave quote obligations. Filtering solely
  on zero base quantity would hide the exception before the new adapter could reject
  it. This is not permission to net different contracts by currency-pair likeness.
- **Resolution:** `measure_position_rows` checks flat forward proof before pagination,
  retaining exceptions. Mixed agreements are unavailable, not averaged. Numeric
  Decimal comparison also avoids rejecting normal closures over rate scale alone.
- **Regression:** [forward inputs](tests/test_fx_forward_measure_inputs.py),
  `test_zero_base_with_mixed_rates_is_not_filtered_out_as_closed` and
  `test_maturity_close_removes_both_legs_and_cancellation_restores_them`.
- **Boundary:** This fixes the Measures preview, not all generic quantity-only
  position consumers. Historical mixed agreements still require explicit remediation.

## MEASURES-005 — P2 — Slow monetary input resolution and full-history scaling risk

**Current status — 2026-10-16:** Partially addressed: matching-series constraints fix the measured broad observation scan; rights/history/roster reads, catalogue projections, holdings definitions and complete forward proofs are batched. Read-only operating probes measured identical candidate rows (~899 ms → ~6 ms) and an eleven-position scoped monetary read phase of ~0.53 s. Full-history/checkpoint, explorer-history, complete access-matrix and concurrent-load scaling remain open; existing per-user/per-batch authority checks are deliberately retained. See [query-efficiency evidence and limits](docs/delivery/quality-reviews/2026-10-16-query-efficiency.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (local read-only profile and static scaling paths), 2026-10-15.

- **Source/function:** [holdings loader](positions/holdings_repository.py),
  `load_holdings_facts`; [strategy route](apps/reference_api/strategy_workspace.py),
  `snapshot`/`measure_position_rows`; [forward adapter](valuation/forward_measures.py).
- **Trigger:** Even eleven ordinary/mock positions expose slow governed mark
  resolution. Large strategy history, many forward buckets or flat historical
  forward episodes; small UI page size does not bound reconstruction work.
- **Impact/evidence:** Complete history is loaded in 500-row chunks and materialized;
  forward proof uses per-bucket trade/event reads. Flat forward safety checks run
  before pagination to preserve counts/visibility. Price/FX caching avoids some
  repeated selections but is not a history checkpoint or a latency guarantee.
- **Measured evidence:** Earlier in this same review session, one explicitly
  read-only Strat Testing preview took 42.63 seconds: holdings 0.19 seconds,
  monetary inputs 42.24 seconds, 1,796 SQL statements and 38.61 seconds inside SQL
  execution. Fifteen `resolve_market_data` calls consumed 38.95 seconds; entitled
  observation selection dominated. Rights scans ran 58 times with 290 `load_rights`
  calls; 43 current display checks were performed. These timings overlap and must
  not be added together. No query plan establishes a particular missing index;
  catalogue/correction indexes already exist. This is not a concurrency benchmark.
- **Fix direction:** Inspect actual entitled-observation query plans and bounded
  date selection, then batch/cache immutable policy/calendar and request-scoped
  rights decisions with complete scope keys. Reduce repeated display checks while
  preserving current rights. Display-only currency changes should reuse the loaded
  preview rather than request another financial selection. Subsequently batch retained
  forward evidence and add versioned reconstruction checkpoints with proper
  correction/information-cutoff invalidation. Keep both-leg closure checks before
  pagination; do not restore an arbitrary trade cap or skip history.
- **Regression:** Compare large synthetic paged/unpaged results and deterministic
  hashes after backdated corrections; count SQL calls and record latency/memory.
  Large-history, multi-user and cold/warm representative benchmarks remain pending.

## MEASURES-001 — Resolved — Prior RAW mark mixed with post-split quantity

**Evidence status:** Confirmed (reproduced and fixed), 2026-10-15.

- **Resolution:** The preview now applies `assert_native_mark_units` after
  selection, before accepting a price. A stale pre-action mark yields unavailable
  amounts and a row explanation; a compatible post-action mark remains usable.
  Regression proved both outcomes. Final affected run: 111 passed, no xfails.

- **Source:** [measure adapter](valuation/measure_inputs.py), `preview_measures`.
- **Trigger/impact:** Reviewed share-ratio replay changes the holding units, but
  policy freshness permits a pre-action RAW observation. The preview formerly
  multiplied the new quantity by the old-unit price instead of withholding the
  incompatible measure. This can materially misstate all three equity measures.
- **Original cause:** The P&L service calls `assert_native_mark_units` after selection;
  the monetary preview omitted it. Reconstruction safety alone does not check
  the selected price date against replayed units.
- **Fix direction:** Reuse the native-unit guard against the actual selected
  observation date before cash-security multiplication, retaining a row-level
  explanation and unavailable amounts on mismatch. Keep compatible same/post-action
  prices working; do not weaken replay, source rights or freshness policy.
- **Regression:** [Assurance checks](tests/test_position_measures_assurance.py),
  `test_permitted_stale_raw_mark_cannot_price_post_split_quantity`. Strict expected
  failure recorded the original defect; it is now an ordinary passing regression.

## MEASURES-002 — Resolved — Fund share classes not recognized by monetary preview

**Evidence status:** Confirmed (reproduced and fixed), 2026-10-15.

- **Resolution:** Holdings normalizes frozen FUND_SHARE_CLASS to FUND. Preview
  NAV identity comes from the unique frozen BOOKED instrument ID, not a current
  listing or optional trade reference column. Canonical/listed share-class tests
  pass, including a listing without that optional column, prior NAV date and
  exclusion of a later-received revision. Final affected run: 111 passed.

- **Source:** [holdings adapter](positions/holdings_repository.py), booked type
  classification; [measure adapter](valuation/measure_inputs.py), product branch.
- **Trigger/impact:** A cash booking frozen against a `FUND_SHARE_CLASS` definition
  remained that type in holdings. The preview supported `FUND` only and returned
  unsupported-product amounts even with eligible canonical share-class NAV data.
- **Cause/fix direction:** The existing P&L ledger adapter explicitly maps
  `FUND_SHARE_CLASS` to `FUND`; holdings did not. Normalize the actual booked
  product consistently, preserving canonical NAV identity, price/FX dates and
  unavailable-state safeguards. Validate listed and canonical share-class cases.
- **Regression:** [Assurance checks](tests/test_position_measures_assurance.py),
  `test_fund_measures_use_canonical_prior_nav_and_exclude_late_revision`. Strict
  expected failure recorded the recognition gap; all NAV/date assertions now run
  as ordinary passing regressions.

## MEASURES-003 — Resolved for supported dates — Mock swap selection setup

**Evidence status:** Confirmed (live read and remediated), 2026-10-15.

- **Resolution:** [Guarded setup](scripts/prepare_mock_swap_measures.py) adds two
  retained synthetic index histories under existing owned rights and creates
  strategy-scoped `MOCK_STRAT_TEST_MEASURES_20261015` v1. All 11 positions return
  all three native/fund-currency measures on 2026-10-08. Independent formula checks
  pass; rehearsal after apply reuses the same policy/series. No old policy, grant,
  trade, cash or staged/published financial result was changed.
- **Date boundary:** USD/GBP valuation coverage begins 2026-10-08. October 7
  remains outside that coverage; no historical permission was fabricated. New
  policy validity starts October 8 and ends with the selected 2026 calendars.

- **Source:** [mock fixture](data/mock-unit-swaps-20261015.json),
  [original seed](scripts/seed_mock_unit_swaps.py), strategy Measures preview.
- **Original trigger/impact:** Strat Testing / 2026-10-07 / FLEXIBLE_EOD v4 returned mock
  reference notionals but no swap MTM/index exposure, and no SPX USD→GBP value.
- **Evidence:** NO_MATCHING_POLICY_RULE for swap marks/index levels/FX; visible
  public index series has no valuation-use coverage. The retained owned artifact
  already contains matching invented index levels for both swap mark histories.
- **Fix direction:** Add explicitly synthetic index series under existing owned
  mock-data rights; create a separately labelled, strategy-scoped policy using
  exact mock series, sealed calendars and already permitted FX data. Preserve
  original policies, marks and third-party licensing. Fail if any right is missing.
- **Regression:** Retry-safe setup; incompatible source/hash/date fails without
  mutation; SPX/UKX reference/exposure/MTM reconcile in local and fund currency.

## FIX-VAL-004 — P2 — Intermittent maturity rebooking rejection

**Evidence status:** Confirmed (one HTTP reproduction, 2026-10-15); timestamp cause suspected, not proven.

- **Source/function:** [bond service](lifecycle/bond_service.py), `post` final zero-exposure verification; [acceptance](tests/test_mock_bond_valuation_cycle.py).
- **Trigger:** Complete coupon/accrual valuation, independently amend/publish, cancel a maturity closure, then rebook it using a fresh preview and key.
- **Impact/evidence:** One disposable HTTP run returned 409 `Closing entry did not bring exposure to zero`; transaction rollback preserved operating integrity and frozen published evidence. Subsequent connected runs passed. This is a reliability gap, not evidence of incorrect published totals.
- **Investigation:** Final reconstruction reuses the candidate's information cutoff captured before insertion. Excluding newly recorded rows at that frozen cutoff is a suspected cause; host/DB clock alignment was inspected but no failing timestamp trace has yet established it. Bounded real-query diagnostics are retained in the connected test.
- **Fix direction:** Reproduce with row timestamps at the failing boundary, then make post-write verification include its own committed-intent facts using a consistent authoritative timestamp/snapshot. Preserve historical information cutoffs, current authority, atomic rollback and zero-exposure checks. Do not use arbitrary sleeps or remove the invariant.
- **Regression:** Connected cancellation/rebook → reassessment → successor publication, repeated across independent transactions. [Execution report](docs/delivery/mock-valuation-cycle-20261015.md).

## FIX-VAL-001 — Resolved — Calculation-level daily-interest explanation omitted

**Evidence status:** Confirmed (reproduced and fixed, 2026-10-14).

- **Source/function:** [service](valuation/service.py), `calculate_position`; [decisions](valuation/decisions.py), `applied_decisions`.
- **Trigger/impact:** A bond calculation correctly included final daily interest,
  but calculation-level appliedRules received economic flows only, omitting the
  accrual explanation despite retained dailyAccrualInputs. Financial amounts were
  correct; audit explanation was incomplete.
- **Resolution:** Pass every result line's economic evidence into rule derivation.
  Real bond maturity regression failed on the absent DAILY_EARNED_ACCRUAL rule,
  then passed after the fix. Frozen staged figures and current publication checks
  are unchanged. Existing rows are not backfilled.
- **Regression:** [Bond valuation](tests/test_bond_redemption_valuation.py),
  `test_full_valuation_and_staging_keep_final_daily_interest_separate`.

## FIX-VAL-002 — P2 — Non-ledger source impact fan-out remains incomplete

**Evidence status:** Confirmed (static scope limitation, 2026-10-14).

- **Source/function:** [ledger impacts](valuation/ledger_impacts.py), `source_health`;
  [publication](valuation/storage.py), `publish`; [accruals](valuation/accruals.py),
  `assert_current_accrual_versions`.
- **Trigger/impact:** A market-data, policy or corporate-action revision after
  calculation/publication is not itself a trade-ledger change. Published results
  remain reproducible but do not automatically enter the ledger reassessment
  worklist for every such source revision. Do not read CURRENT as universal input
  validity. Accrual revision checks at publication cover assessed inputs separately.
- **Evidence:** Source-health queries strategy_ledger_change; capture triggers
  observe trades/lifecycle events. No generalized source-impact register was added.
- **Fix direction:** Later scoped source-dependency evidence and reassessment
  rules, preserving frozen results, current rights and explicit staged successors.
- **Regression:** Revised mark/action/policy/accrual after publication should
  identify affected economic dates without rewriting prior numbers; unavailable
  sources and current entitlement loss must not leak evidence or auto-publish.

## FIX-VAL-003 — P2 — Independent numerical reconciliation/scale acceptance pending

**Evidence status:** Confirmed (verification limitation, 2026-10-14).

- **Source/function:** [methodology matrix](docs/architecture/market-data-and-valuation/valuation-methodology.md),
  [calculation](valuation/position_calculation.py), `attribute_projection`;
  [daily aggregation](valuation/service.py), `aggregate_daily_periods`.
- **Trigger/impact:** Production-size populations or an external administrator's
  conventions may differ from bounded synthetic fixtures. Passing exact numerical
  tests is not independent custodian reconciliation or a measured scale guarantee.
- **Evidence:** 64 pure and 63 focused disposable-DB tests in this follow-up;
  no full suite, load benchmark or external reconciliation was performed.
- **Fix direction/regression:** Reviewed representative portfolios and reconciled
  external price/FX/accrual inputs; compare daily and multi-day results, holiday
  NAV availability, historical corrections and repeated large-population runs.

## FIX-ACCESS-001 — P2 — Independent approval of self-assigned access is deferred

**Evidence status:** Policy decision (2026-10-13).

- **Source/function:** [access management](security_master_schema/access_management.py),
  `set_user_groups`/`save_group`; [strategy scope delivery](docs/delivery/strategy-access-scopes.md).
- **Trigger/impact:** A tenant admin can assign themselves an operational group
  within subscribed modules. Separating defaults does not prevent self-escalation
  by an authorized access administrator.
- **Evidence:** ACCESS_MANAGE authorizes assignment; audit exists, independent
  approval is not required. This is an explicitly agreed alpha policy, not a bypass.
- **Fix direction:** Later independent approval/access certification when scoped.
- **Regression:** A proposed governed flow must block self-approval while preserving
  legitimate administration, last-admin protection and immutable decision evidence.

## FIX-ACCESS-002 — P2 — Access matrix/preview scale with the tenant population

**Evidence status:** Confirmed (static, not load-tested; 2026-10-13).

- **Source/function:** [strategy administration](security_master_schema/strategy_access_admin.py),
  `access_rows`/`preview`; [access view](security_master_schema/access_management.py),
  `tenant_access_view`.
- **Trigger/impact:** Large user/group/strategy populations expand full matrix and
  impact computation, payload size and per-user authority resolution work.
- **Evidence:** Matrix/preview collect the tenant view and loop users × strategies
  × scoped actions/groups; no paging or measured large-tenant latency guarantee.
- **Fix direction:** Targeted strategy/member queries, paged matrix and incremental
  impact computation while preserving exact action/scope decisions.
- **Regression:** Large synthetic populations; compare paged/filtered results to
  individual decisions, including empty scopes, counts, overlapping grants and revocation.

## FIX-SP-001 — P1 — Silent omission/defaulting at the economic intake boundary

**Current status — 2026-10-16:** Resolved for the reviewed manual draft boundary: strict finite terms, explicit missing values and template-aware UI. General automated termsheet intake is not claimed. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (reproduced).

- **Source/function:** [Python draft models](apps/reference_api/structured_product_contracts.py),
  `AutocallDraftRequest`/`validate_autocall_draft`; related browser
  [payload conversion](apps/ops-console/src/app/instruments/autocalls/new/payload.ts),
  `numberOrZero`.
- **Trigger:** Add an unrecognized contractual field or omit a headline coupon.
- **Impact:** An unsupported economic clause can disappear; a missing economic
  value becomes zero. AI payload acceptance could be mistaken for complete
  contractual representation.
- **Evidence:** Offline 2026-10-13 probe using `_base_payload` from
  `tests/test_structured_product_draft.py` discarded `unmodelledTermsheetClause`
  and normalized omitted couponRate to 0 while the row rate remained 6.5. Browser
  numeric conversion statically maps non-finite values to 0.
  Rechecked with pure fixtures on 2026-10-15: unknown field retained = false;
  missing headline coupon = 0. No browser interaction was repeated by this audit.
- **Fix direction:** Introduce strict ingestion/form models, explicit missing and
  unsupported states and template-specific economic completeness checks. Review
  compatibility before changing legacy v1 defaults globally.
- **Regression:** Unknown nested/top-level fields rejected; absent/invalid
  required economic values block submission; explicit contractual zero accepted
  when permitted; existing manually entered valid requests remain valid.

## FIX-SP-002 — P1 — Headline economics and explicit graph can disagree

**Current status — 2026-10-16:** Resolved for reviewed coupon/barrier summary and period persistence: explicit variable schedules retained, contradictory summaries rejected. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (reproduced).

- **Source/function:** [Validator](apps/reference_api/structured_product_contracts.py),
  `validate_autocall_draft`; [materialization](apps/reference_api/repository.py),
  `_materialize_structured_product`.
- **Trigger:** Send headline couponRate 1.25 with coupon-row rates 6.5.
- **Impact:** Coupon-program headline/default/period records and child payoff-row
  economics can represent inconsistent contractual terms.
- **Evidence:** Offline 2026-10-13 probe accepted this mismatch. Static inspection
  shows materialization uses the headline for coupon program/period values and
  row rates for component economics. No live valuation impact was reproduced.
  Rechecked on 2026-10-15: accepted headline 1.25 and schedule row rates 6.5.
- **Fix direction:** Normalize one declared economic schedule and reconcile
  headline terms against it. Preserve evidenced variable/step-up periods rather
  than requiring every period to equal one flat headline value.
- **Regression:** Contradictory flat coupon blocked; evidenced variable periods
  preserved consistently across persisted program and component graph; duplicate
  barriers/participation representations agree or have explicit derivations.

## FIX-SP-003 — P1 — Generated payment lag ignores selected calendar holidays

**Current status — 2026-10-16:** Resolved for new generated schedules: server-assessed published calendars, holiday counting and unknown-coverage blocking. Explicit sourced dates stay separate. See [remediation evidence](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md). The original finding below describes the pre-fix trigger.

**Evidence status:** Confirmed (static).

- **Source/function:** [Schedule](apps/ops-console/src/app/instruments/autocalls/new/schedule.ts),
  `addBusinessDays`/`generateAutocallSchedule`; shared interface available in
  [calendar store](market_data/calendar_store.py), `calendar_days`.
- **Trigger:** A positive payment lag crosses a weekday holiday in the selected
  contractual calendar.
- **Impact:** Generated payment dates can differ from contractual business-day
  dates. Unattended submission would propagate the error without form review.
- **Evidence:** `addBusinessDays` excludes only Saturday/Sunday and accepts no
  calendar input. Selected calendar is passed separately in the proposal payload.
- **Fix direction:** Server-authoritative generation with governed dated calendar
  evidence, explicit conventions and UNKNOWN-coverage blocking; preserve explicit
  imported dates and evidenced exceptions.
- **Regression:** Weekday holiday, differing calendars, missing coverage,
  month-end/stub and explicit observation/payment-date cases; assisted/unattended
  parity against independently authored expected dates.

## FIX-SP-004 — Resolved for structured-product submission — Source payload ownership

**Evidence status:** Confirmed (static).

- **Source/function:** [Repository](apps/reference_api/repository.py),
  `submit_structured_product_proposal`; [schema](security_master_schema/models.py),
  `source_payload`; compare ownership checking in equity submission.
- **Trigger:** A caller supplies an existing sourcePayloadId belonging to another
  tenant or a different source system.
- **Impact:** A proposal can claim mismatched source provenance. UUID existence
  and a global foreign key do not establish tenant/source-system ownership.
- **Resolution (2026-10-13):** Structured submission now checks active source-system
  tenant/shared scope and matching source-payload tenant/shared scope before insertion
  and replay, with transactional shared row locks. Disposable-DB regressions reproduced
  and fixed foreign/mismatched acceptance; missing evidence fails before insertion.
  See [delivery and limits](docs/delivery/effective-access-transparency.md) and
  [tests](tests/test_source_payload_scope.py). No document-content disclosure is claimed.
- **Fix direction:** Validate source payload tenant and source-system membership
  before proposal insertion and at ingestion retrieval/submission boundaries.
  Define explicit eligibility for shared source evidence; termsheet uploads are
  tenant-owned by default.
- **Regression:** Same-tenant matching source accepted; cross-tenant/wrong-system
  source rejected without revealing source contents; unauthorized document reads
  rejected; permitted shared evidence tested separately. Future upload/document-read
  endpoint checks remain part of F54; those endpoints do not exist yet.

## FIX-SP-005 — P2 — No integrated ingestion or shared authoritative builder

**Evidence status:** Confirmed (static).

- **Source/function:** [Creation form](apps/ops-console/src/app/instruments/autocalls/new/form.tsx),
  template generator selection and `buildAutocallDraftPayload`; existing
  [API boundary tests](tests/test_structured_product_api.py).
- **Trigger:** A tenant wants termsheet-to-editable-inputs or unattended proposal
  submission using the same schedule behavior as manual creation.
- **Impact:** Existing proposal endpoints alone do not provide extraction,
  resolution, evidence review or automatic schedule generation for machines.
- **Evidence:** Inspected path starts from browser form state and submits a
  completed graph. API tests only establish route publication/importability.
- **Fix direction:** Implement the [proposed F54 design](docs/superpowers/specs/2026-10-13-structured-product-termsheet-ingestion.md)
  with provider-neutral extraction, persisted revisions, common server preview,
  assisted hydration and gated unattended submission.
- **Regression:** Synthetic end-to-end expected economics, blocked drafts cause
  no proposal writes, ready unattended revisions create exactly one PENDING
  proposal, approval materializes the same graph as assisted creation. Later real
  termsheet acceptance must be recorded separately.

## Original October 13 verification and unresolved limits

26 focused pure draft/API-boundary tests passed on 2026-10-13. Reproduction used
pure Pydantic validation and synthetic test fixtures only. No operating DB,
provider or browser was accessed. Source ownership and holiday findings need
focused regression coverage during implementation. The additional 2026-10-13
effective-access work resolves FIX-SP-004 at structured-product submission/replay
with real disposable-DB tests; holiday and other economic findings remain open.
