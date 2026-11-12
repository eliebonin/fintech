# Reviewed findings

## LIFECYCLE-READ-REDUNDANCY-003 — Fixed option worklist overhead remains after batching

**Open · P3 · Confirmed (reproduced) · 11 November 2026.** `list_worklist` and nested strategy predicates resolve the same tenant/user workspace four times(20 queries); `_option_views` separately reloads original BOOKED payloads after the ledger chain read and bulk-loads related current source tables separately. Trace:55 total calls for13 contracts/21 trades, of which only1 fetches dates. This is fixed request overhead rather than the resolved per-trade amplification. Reuse transaction/request-bound authority and validated source evidence; consolidate compatible source queries while preserving same-group scope, current/original ambiguity checks and native financial authority. Verify full event/inspection/evidence equality, revoked/changed authority behavior and constant-growth budgets. [Exact breakdown](docs/delivery/lifecycle-reader-batching-20261111.md#option-follow-up-what-the55-queries-contain). Product changes remain pending.

**Measured impact:** local warm medians are 6.620 ms for one five-read resolution, 26.809 ms for four, and 19.718 ms for the repeated three. This supports lower-priority consolidation, not a demonstrated seconds-long delay; remote/concurrent performance is unmeasured. Source/context consolidation remains unimplemented.

## LIFECYCLE-READ-AMPLIFICATION-002 — Other product readers repeated historical source and exposure reads

**Resolved · P2 · Confirmed (reproduced and regression-tested) · 11 November 2026.** Distinct futures/options and repeated options caused per-trade historical identity SQL; FX discovery repeated ownership/terms/ledger/policy/annotation reads. Lazy historical candidates and scoped FX batches now retain existing validators and full pending-source reassessment. Complete event/inspection evidence comparisons match. FCPGF FX155→49queries;13-contract futures101→53, options135→55. Bonds/coupons were already batched and remain unchanged. [Measurements, tests, exceptional legacy fallback and scaling limits](docs/delivery/lifecycle-reader-batching-20261111.md).

**Latest scoped review:** 11 November 2026, lifecycle documentation-to-code reconciliation and the bounded futures/option/structured notification extensions. Structured notices deliberately do not assess actual outcomes, suppress later schedules after an unrecorded autocall, or generate financial tasks; [scope and verification](docs/delivery/structured-informational-notifications-20261111.md). Futures first-notice/broker deadlines and financial lifecycle commands are explicitly unimplemented scope, not inferred from delivery dates; see [delivery](docs/delivery/future-lifecycle-notifications-20261111.md). Option broker/fixing/outcome evidence is also deferred; see [option scope](docs/delivery/option-lifecycle-notifications-20261111.md). Coupon shared visibility and absent entitlement/cash reconciliation are deliberate delivery limits, recorded in [the capability](docs/product/features/trade-operations.md#f51-tenant-lifecycle-handling-modes) and [coupon delivery](docs/delivery/coupon-notifications-20261111.md), rather than newly confirmed defects. Existing unrelated findings remain unchanged. The earlier documentation-only reconciliation ran no runtime tests; the subsequent futures implementation has separate focused backend, UI and browser evidence in its delivery record.

## LIFECYCLE-READ-TIMEOUT-001 — Structured worklist amplified per-contract source reads

**Resolved · P2 · Confirmed (reproduced and regression-tested) · 11 November 2026.** A portfolio-wide call to the single-instrument reader made4458 queries; an interim scalar cache reduced this only to2258. `TermsScheduleBatch` now prefetches authorised graph/table relationships in500-ID chunks, with one SQL-free renderer and batched status/identifier search. Full FCPGF evidence matches:270 events/87 source projections,89 queries,1.310-second median over three trials; live BFF1.796seconds. Native distinct-contract regression stays102 queries as24 swaps/references are added,104 with search. Private/missing roots, chunk boundaries, wrappers, cycles/depth, source/scope and allocation controls are covered. [Delivery, exact verification and remaining scaling limits](docs/delivery/structured-lifecycle-batch-reads-20261111.md). No financial or permission behavior was relaxed.

## LIFECYCLE-PREPARED-INPUTS-001 — Prepared standard fields were omitted on revalidation

**Resolved · P2 · Confirmed (reproduced and regression-tested) · 11 November 2026.** A bond/FX preparation with an Ops Comment appeared stale and could not confirm because only custom `properties` were reconstructed, omitting `standardInputs`. `lifecycle.allocations.retained_annotation_inputs` now restores both for native confirmation and worklist source assessment. Two failing-before/passing-after cases verify prepared status and the recorded closing-trade comment. Existing authority/source/allocation checks and immutable evidence remain intact. See [delivery](docs/delivery/fx-maturity-worklist-20261111.md).

## LIFECYCLE-CLOCK-001 — Current closure checks could miss database-recorded facts

**Resolved · Confirmed (reproduced and regression-tested) · 11 November 2026.** A live drawer booking safely rolled back when Python lagged PostgreSQL and the zero-exposure check omitted its own closing entry. `lifecycle.recording_clock` now supplies current database knowledge for bond/FX candidates and worklist reads; closure checks refresh that knowledge after posting while retaining the economic cutoff. [Regression](tests/test_lifecycle_recording_clock.py) covers both products with a five-second application-clock lag, zero exposure and same-key replay. Final real isolated browser acceptance completed direct and independently approved bond closures. No historical timestamps, price/authority guards or operating records were weakened or rewritten; [delivery limits](docs/delivery/lifecycle-action-panel-20261110.md) remain explicit.

## LIFECYCLE-TIER-001 — Commercial access and assistance selection were conflated

**Resolved for bounded bond/FX maturity · Confirmed (reproduced and regression-tested) · 5 November 2026.** New subscription/selection services and native consumer guards deny Tier2 no-proposal posting and above-ceiling assisted use. Reviewed tenant transitions never silently change commercial authority, review controls or financial history. [Delivery/evidence](docs/delivery/lifecycle-assistance-entitlements-20261105.md) records schema112, scoped APIs/UI, actual downgrade locking and receipt/correction rules. General notification discovery, billing and other lifecycle handlers remain planned scope, not claims of this fix.

## BROWSER-LEGACY-001 — Retired allocation editor browser cases

**Resolved · Confirmed (reproduced and browser-regression-tested) · 5 November 2026.** The two cases in `apps/ops-console/browser-tests/lifecycle-allocation-layout.spec.ts` originally timed out while looking for the retired global allocation editor and save endpoint. They now use the current versioned profile workflow and its HTTP contract. Coverage preserves long-label/control readability at 1280px and 390px, keyboard focus return, required publication reason, explicit review, correctly versioned lifecycle-rule payload, read-only published rules and an unchanged tenant default. No product code, old editor or global authority was restored. The repaired cases pass individually and run with the current lifecycle/profile/ticket browser journeys; exact final results are retained in the lifecycle delivery ledger.

## PROFILE-001 — Tenant-global metadata rules prevented strategy-specific configuration

**Resolved · Confirmed (reproduced and regression-tested) · 4 November 2026.**
The former shared annotation validator and tenant-wide lifecycle policy could not express differing requirements for funds, AMCs and sleeves. [Profile delivery](docs/delivery/tenant-reference-data-trade-profiles-20261104.md) replaces effective rule authority with explicit strategy pins and updates every supported consumer. Focused tests cover stale imports, correction provenance, atomic batch adoption, source retirement and booking/adoption races; eight browser tests and the full frontend suite pass. Existing source identities, economic evidence and permission grants are retained. Profile-specific value subsets and saved drafts remain deliberate scope limits; this does not resolve unrelated open audit findings below.

## LIFECYCLE-ALLOC-001 — Aggregate maturity entries lose tenant classifications

**Resolved for bond/deliverable FX maturity; locally activated · 4 November 2026.**
Bond/FX maturity previously netted source allocations and omitted new trade annotation
rows. Multi-entry bond events also reused a globally unique source-event identifier.
[The delivery](docs/delivery/lifecycle-allocation-preservation-20261104.md) records the
allocation view, typed field validation, atomic posting and per-movement identity fixes.
Focused DB tests reproduce classification loss, required-field omission, and second-entry
failure; whole-event rollback, opposing allocations and cancellation are now covered.
Historical mismatches and retired-source remediation remain explicit limitations.

## Rate-exchange follow-up scope — 30 October 2026

The [rate-exchange delivery](docs/delivery/rate-exchange-swaps-20261030.md) closes
the four source posting exceptions with native, separately priced contracts.
Its inferred scheduling/principal conventions and the existing bond-income versus
total-return distinction are disclosed limitations, not confirmed legal terms.
Generated flows, rate-risk sensitivities and full-portfolio financial
acceptance remain outside this change; [F18](docs/product/features/product-booking.md#f18-generic-swaps)
tracks that remaining scope. Focused regressions and live posting checks do not
supersede the other open findings below.

## SEC-RIGHTS-001 — Missing market-data profiles retain legacy use checks

**Resolved · Confirmed (reproduced and regression-tested) · 30 October 2026.**
Missing/unknown profiles now deny use; display purpose is consistently explicit
in `market_data/rights.py`, `display_access.py` and catalogue SQL. Migration 106
and the exact-identity seed provisioner govern five invented fixtures with
SYNTHETIC origin evidence. All seven real profiles and 32 original grants were
verified unchanged. Revocation/current-release and layered/scoped checks remain.
No synthetic/personal evidence supplies commercial source rights. [Delivery and
remaining rights-administration work](docs/delivery/dataset-rights-and-workload-20261030.md).

## SEC-WORK-001 — Deployment workload isolation and durable processing

**P2 locally; deployment capacity gate · Confirmed (static) · 30 October 2026.**
**Admission implemented; remaining deployment work open.**
`apps/reference_api/workload_admission.py` now provides nonblocking local/global/
tenant capacity, shared PostgreSQL slots, cancellation/error cleanup and safe
429/503 retries before domain effects. Separate control pools preserve ordinary
and single-connection financial reads; numeric totals and complete populations
are unchanged. [Evidence and defaults](docs/platform/dataset-rights-and-workload.md).
Remaining: representative load/memory profiling, per-job OS CPU/RSS isolation,
operator rate accounting and a durable queue/status/cancellation/recovery design.
Client deadlines do not imply synchronous work stopped. Do not restore arbitrary
trade caps, drop instruments or silently truncate financial results. Production
capacity and untrusted deployment are not certified by local admission tests.

## Resolved local controls — 30 October 2026

Security-review findings 3/4/6/8 now have [implemented safeguards and evidence](docs/delivery/security-controls-20261030.md):
loopback/password/runtime-role separation, real default secret rules, append-only
access audit/safe denial logs and browser CSP/HTTPS cookie controls. Existing
data/volume are retained. Trusted database/host administrators, external audit
retention and production identity remain separate. Finding 5 and the admission
portion of 7 have since been addressed above; deployment workload work remains.

## SEC-DEP-001 — Vulnerable dependencies and recurring checks

**Resolved for the reviewed locks · 30 October 2026.** Security-review point 2:
targeted Next.js/Vitest/transitive and Certifi/pytest upgrades remove the known
advisories. Complete-lock PR/main/manual/weekly checks fail on findings or scanner
errors, with no advisory/development-package exclusions. See the
[delivery evidence and limits](docs/delivery/dependency-security-20261030.md) and
[maintenance reference](docs/platform/dependency-security.md). Remote workflow
execution is not claimed before push. This closes neither other security
findings nor future advisories; existing production/deployment gates remain.

## REG-001 — Complete regulatory mapping and submission lifecycle

**P2 · Policy decision · 29 October 2026.**
[Reporting preparation checks](regulatory_reporting/assessment.py) and
[retained exports](regulatory_reporting/service.py) intentionally implement local
preparation, not all current RTS 22 field applicability or accepted serialization.
Using this CSV directly as a regulator payload would be unsupported. Keep the
PREPARATION_ONLY/UI boundary, confirm the actual receiving channel, then add
versioned product/identity applicability, official schema validation, regulatory
report references, acknowledgements and cancellation/reconciliation. Regression:
accepted/rejected synthetic schema examples and anonymised accepted real outputs,
including all supported product families and correction chains. No current
regulatory acceptance is claimed. See [F53 limits](docs/product/features/regulatory-reporting.md).

## REG-002 — Preparation/export scale assurance

**P2 · Suspected · 29 October 2026.**
[Execution population](regulatory_reporting/source.py) batches supporting queries
but retains the complete selected scope in memory; the service assembles CSV,
manifest and expected revisions synchronously. No arbitrary execution-count cap
was added. Large scopes may exceed memory/request/transaction budgets; current
fixtures establish correctness, not production capacity. Profile realistic
cross-family volumes before choosing background preparation/streaming and retained
server-side preview tokens. Regression: complete counts/membership/Decimal parity,
source-change rejection and rights revocation under a large multi-page scope.

**Status:** Open scoped findings  
**Content type:** Review  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-30 (identity/dependency safeguards; prior scoped findings retained)

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

## Scoped follow-up — 25 October 2026

28 October [DIRTY bond quotation follow-up](docs/delivery/bond-dirty-to-clean-20261028.md)
closes the bounded daily-P&L normalization gap when matching source quoted
accrued per 100 is provided. It does not infer missing quote evidence, generate
daily interest, replace a strategy accrued balance or fix general market-data
source-impact fanout. New normalized staged inputs are reselected before
publication; older published evidence remains frozen. Broader reconciliation,
scale, warning routing and derived-stock presentation findings remain open.

28 October scoped [linear futures extension](docs/delivery/linear-futures-extension-20261028.md):
blanket crypto/physical booking refusals are removed for the supported dated
linear conventions, with actual asset-role validation and the same governed daily
variation. Current-family changes cannot alter frozen booked arithmetic. This
does not resolve FIX-VAL-003 independent portfolio/scale acceptance or delivery,
assignment, margin-accounting and unsupported-contract scope. Verification is
limited to the paths/tests recorded in the delivery, not an exhaustive review.

31 October maintained-stock follow-up: [delivery and limits](docs/delivery/maintained-accrued-balances-20261031.md)
replace implicit bond reconstruction during valuation with explicit source-verified
history maintenance. Independent anchors, coupon receipts, checkpoint invalidation
and a workbench are delivered. Missing history/native conversion remains disclosed;
interest generation, background scheduling, bulk stock uploads and independent
financial acceptance remain open. This does not close broader valuation findings.

27 October accrued-stock follow-up: [delivery and limits](docs/delivery/accrued-balance-fx-20261027.md)
add source-based balance replay, CARRY and scoped unpaid receivables. The earlier
automatic-balance gap is addressed for complete daily history/assessed anchors;
this does not close accrued-interest generation, currency-change assessment,
coupon entitlement or payment reconciliation. Source-state checks conservatively
require reassessment for new historical revisions, even if an anchor would make
the amount unchanged. Optional FX absence classification is local and tested;
it depends on documented resolver diagnostics and deliberately rethrows unknown
structural failures rather than broadly suppressing errors.

27 October schedule follow-up: the former coupon-only slice now supports
[typed coupon and principal rows](docs/architecture/trading-and-operations/bond-cashflow-schedules.md),
including principal-only zero bonds. The later stock-FX increment provides bounded
accrued-stock reconstruction; entitlement, payment reconciliation and DCF-pricing
remain open. Existing
coupon receipts remain evidence, not extra income or proof of full settlement.
Verification scope: [delivery](docs/delivery/bond-cashflow-schedule-20261027.md).

### SCHEMA-DOC-001 — missing Python column comments (minor, open)

`tests/test_schema_metadata.py::SchemaMetadataTests::test_every_schema_column_has_documentation`
fails for **94 existing columns**, reproduced standalone and by evaluating committed
`HEAD:security_master_schema/models.py` with the unchanged domain registrations.
Affected tables: tenant organisation profiles, AMC terms, corporate-action replay
decisions, bond/FX maturity policies/proposals/postings and four cash-balance
columns. New migration-99 attribution/review cash-owner columns have comments.
This is a metadata documentation gap, not missing columns or a financial/runtime
failure. Deferred from the [cash-FX implementation](docs/delivery/cash-fx-pnl-20261025.md)
to a targeted schema documentation cleanup; do not describe the broad test set as
entirely green or suppress the check.

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

## BACKEND-001 — P1 before deployment — Production authentication deferred

**Evidence status:** Local containment verified; production identity remains open.

30 October [safeguard delivery](docs/delivery/local-identity-safeguard-20261030.md)
closes header-only local access: ordinary protected requests require an opaque
verified session, identity headers cannot override it, and bootstrap requires a
private configured operator capability. Legacy demo-user/signed-tenant identity
is removed. API startup and protected requests fail closed outside explicit local
modes or without configuration. The earlier header-impersonation finding describes
the pre-safeguard code; no deployed exploit was claimed.

- **Source/function:** [verifier](apps/reference_api/local_identity.py),
  `verified_session`/`bootstrap_actor`; [settings](apps/reference_api/config.py),
  `validate_local_identity`; [boundary](apps/reference_api/access_boundary.py),
  [verified context](apps/reference_api/tenant_context.py) and
  [session store](security_master_schema/access_sessions.py).
- **Remaining trigger/impact:** Local context selection intentionally delegates
  through a configured testing operator. It does not authenticate individual
  external people. Exposing or relabelling local mode as a production deployment
  would violate this boundary; production/staging startup is blocked.
- **Fix direction:** Later integrate a maintained verified identity provider,
  account mapping, secure sessions and production support-access policy. Preserve
  current membership/module/action/strategy authority and real-operator review.
- **Regression:** [offline configuration/spoofing](tests/test_local_identity_safeguard.py),
  [real-session expiry/revocation/audit](tests/test_local_identity_sessions.py) and
  [independent calculation/publication](tests/test_valuation_acceptance.py).
  [Setup and limits](docs/platform/local-identity-safeguard.md). No production
  authentication certification is claimed.

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

**Current status — 29 October, cash pilot:** Listed-cash command models,
orchestration, persistence and its annotation/reference/recognition/correction
helpers now have HTTP-free `trading` owners. API and file confirmation share that
command, retaining API read DTOs and caller-owned audit/batch transactions. Fixed
schema/hash/AST checks and focused direct/API/import/rollback regressions are in
the [delivery](docs/delivery/cash-booking-service-extraction-20261029.md). The
baseline generic-swap tuple/UUID lock comparison is also corrected without
removing currency-drift checks. Other product writers, cancellation orchestration,
reference/proposal services, catalogue/preview and metadata registration remain
open. BACKEND-009 is still **partial**, with a completed cash slice.

**Current status — 29 October, phases 1–3:** Selected reverse imports are removed:
accrual visibility, amendment/bond-redemption locks and generic evidence helpers
now use lower owners; pricing-policy creation/models and the Yahoo FX operator
share `market_data` services. Preserved contracts, hash vectors, frozen economics,
retry/lock behaviour, visibility and audit rollback are covered by the focused
[delivery checks](docs/delivery/api-service-extraction-20261029.md). Non-HTTP policy
creation now enforces the same explicit strategy-write scope before replay.
No schema/operating-data change. BACKEND-009 remains **partial**: reference/booking
orchestration, catalogue/preview adapters, central schema/resolver responsibilities
and late intake metadata registration are still coupled. Do not read this pilot
as a fully thin API or a repository-wide dependency DAG. New regressions include
fixed command-schema/evidence vectors and shared-command/API/authority tests.

**29 October pre-extraction inventory:** The [atlas baseline](docs/architecture/atlas/README.md)
recorded the above edges before this implementation, API repository 5,211 lines,
contracts 1,476, factory 1,244 and models 3,064. Complete runtime metadata matched
the inspected live table/FK-pair/column-count structure at migration 104.
Those are dated structural observations, not demonstrated financial failures.

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

## TEST-001 — P3 — Valuation retry characterization has a stale expected identity

**Confirmed (reproduced), 29 October 2026, before cash extraction.**
[test_intraday_request_identity_preserves_existing_retry_keys](tests/test_recognition_retry_compatibility.py)
compares a dataclass projection with `valuation.storage.request_identity`, but
expects absent `calculation_contract` and an explicit false `require_complete_accruals`.
The current implementation includes the calculation-contract version and omits
the default optional-accrual flag. The offline baseline reproduces this mismatch;
the neighbouring booking-fingerprint recognition check passes. No runtime defect
is established by this stale assertion. Update the test against the documented
active calculation contract in a valuation-focused change, including nondefault
strict-accrual and contract-version identity cases; do not remove the calculation
version or alter retained fingerprints merely to satisfy this older expectation.
Cash extraction does not modify that implementation or this test.

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

## MEASURES-006 — Resolved — Frozen option type and unit-note denomination recovery

**Evidence:** Confirmed by failing native preview tests, 3 November 2026.

- **Source:** `positions.holdings_repository.holding_conventions`, consumed by
  strategy positions and `valuation.measure_inputs`.
- **Trigger/impact:** An option BOOKED payload without flat product metadata was
  classified as OPTION_BOOKING; a percentage-quoted note booked in units could
  retain multiplier 1 instead of its saved denomination. These blocked accurate
  measure support and could split equivalent holdings into wrong convention keys.
- **Resolution:** Recover canonical OPTION and the saved percentage-note unit
  denomination. Retain explicit frozen factors; native measure validation rejects
  conflicting proof rather than substituting current reference terms. Stored
  trades and published calculations are untouched.
- **Regressions:** [native product measures](tests/test_expanded_measure_inputs.py),
  [quantity conventions](tests/test_strategy_holdings.py) and
  [delivery/remaining risk boundaries](docs/delivery/expanded-position-measures-20261103.md).

## MEASURES-007 — Resolved — Permitted missing marks crashed the measure page

**Evidence:** Confirmed by live HTTP failure and isolated red/green tests, 3 November 2026.

- **Source:** `valuation.measure_inputs.mark`, native `price_inputs.MissingPriceInput`.
- **Trigger/impact:** A WARN/MANUAL_OVERRIDE policy with an absent eligible mark
  raised the P&L population-gap exception outside the preview's ValueError handler,
  producing HTTP 500 instead of an unavailable measure or compatible dirty/clean
  fallback. Known reference amounts and other rows were hidden by the page error.
- **Resolution:** Handle only this known missing-price exception at mark selection.
  Preserve per-measure unavailability, original policy/override selection and
  current DISPLAY denial. Do not invent a price or change P&L publication rules.
- **Regression:** `test_policy_permitted_missing_mark_is_an_unavailable_measure_not_a_page_failure`
  in [expanded product checks](tests/test_expanded_measure_inputs.py); 46 focused
  price/permission checks and successful live report reload recorded in the
  [delivery](docs/delivery/expanded-position-measures-20261103.md).

## MEASURES-008 — Resolved — Forward reference kept the booked currency

**Evidence:** Introduced and caught during priority-6 implementation; live read and existing contractual-leg regression reproduced it, 3 November 2026.

- **Source:** `valuation.measure_inputs.preview_measures`, FX_FORWARD branch.
- **Trigger/impact:** Separating option strike currency added an independent
  reference currency; the forward branch changed its native base currency but
  did not update that reference field. Reference amount display/conversion could
  therefore disagree with the already correct contractual base leg.
- **Resolution:** Bind forward reference currency to the actual contract base.
  Stored trades, frozen results and daily P&L were untouched.
- **Regression:** [existing native forward checks](tests/test_fx_forward_measure_inputs.py)
  now explicitly compare reference/base-leg currency and strategy conversion;
  42 forward/product checks passed and the corrected live EUR/GBP row was inspected.

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

## FIX-VAL-005 — P2 — Partial-result and position Attention signals are incomplete

**Status:** Resolved within the supported retained-coverage scope, 2026-10-29.
[Delivery and verification](docs/delivery/valuation-review-signals-20261029.md):
cash-only gaps mark new results partial; response/UI review covers interest FX,
stock/FX/currency failures and anchor discrepancies. Compact disclosure and
full-result Attention navigation retain missing-date evidence and existing
publication behavior. Historical/disappeared cash scopes are not reintroduced.
Original finding below records the 27 October snapshot; general source fanout
and independent financial acceptance remain open separately.

**Evidence status:** Confirmed (offline probes and static tracing, 2026-10-27).

- **Source/function:** [calculation](valuation/service.py), `calculate_position`
  `pnlCompleteness`; [presentation](apps/reference_api/valuation_presentation.py),
  `component_display`; [fallback/filter](apps/ops-console/src/features/valuation/ops-review-model.ts),
  `positionAttention`/`selectPositionRows`; [summary](apps/ops-console/src/features/valuation/review-summary.tsx).
- **Trigger:** Cash coverage is PARTIAL/MISSING_INPUTS while interest coverage has
  no missing entries; or an otherwise visible position has missing interest FX,
  accrued-stock FX or an assessed-anchor bridge discrepancy only.
- **Impact:** Cash-only omissions do not select the partial headline. Attention
  does not identify the newer interest-FX/stock/reconciliation warnings, so its
  filter can omit positions requiring review. Global coverage/stock notices and
  the detailed inspector still disclose these cases; this finding does not
  demonstrate incorrect financial amounts or absent retained evidence.
- **Evidence:** An isolated evaluation of the actual completeness expression with
  two missing cash inputs returned RECORDED_COMPONENTS. `component_display` with
  MISSING_DAILY_ACCRUAL_FX and missing stock-FX evidence returned `attention=[]`.
  Anchor differences are retained by replay/inspection but not routed to Attention.
- **Fix direction:** One server-projected review-issue model and consistent
  completeness scope for summary, coverage and Attention. Keep an authoritative
  assessed anchor usable with its warning; do not create new publication blockers
  or historic-account cash obligations merely to unify display statuses.
- **Regression:** Cash-only partial coverage; local missing interest FX; missing
  accrued stock/FX; anchor bridge discrepancy; identity/zero opening stock; normal
  complete result. Assert identical issue counts/filter membership across summary,
  table and inspector without altering totals or missing-data policy.

## FIX-VAL-006 — P3 — Derived accrued stocks lack dual-currency stock presentation

**Status:** Resolved as a read projection, 2026-10-29.
[Delivery](docs/delivery/valuation-review-signals-20261029.md) adds exact
opening/closing reporting amounts using frozen boundary FX or an unambiguous
same-day/orientation retained conversion. Zero/identity and each missing boundary
are explicit. Display uses scan formatting with exact proof; original retained
stocks and CARRY are unchanged. No migration/current-FX fetch. Missing frozen
inputs remain unavailable; this does not claim universal source coverage.
Original finding below is retained as dated evidence.

**Evidence status:** Confirmed (static feature gap, 2026-10-27).

- **Source/function:** [schema](valuation/accrued_balance_tables.py), `register`;
  [inspector](apps/ops-console/src/features/valuation/accrued-balance-inspection.tsx);
  contrast [rich assessed input](valuation/accruals.py), `accrual_amounts`.
- **Trigger:** Ops requests opening/closing accrued stock in strategy/reporting
  currency for a source-derived balance, rather than a rich supplied input.
- **Impact/evidence:** Dataset 3 retains native stocks, reporting currency, FX
  and reporting CARRY; the inspector shows those values. Separate reporting stock
  amounts are absent. Older detailed inputs retain balanceBase/openingBalanceBase,
  so both paths do not yet equally meet the requested local/reporting-stock view.
  Reporting CARRY and supplied daily earnings are already supported; this is not
  evidence that those P&L components are missing or wrongly translated.
- **Fix direction:** Expose explicit local/reporting stocks from frozen evidence
  with independent availability. Decide whether a read projection is sufficient
  before adding duplicate columns; never fetch current FX to redraw an old result.
- **Regression:** Foreign/identity FX, missing optional FX, known zero opening,
  late/partial coupon and negative stock; exact reporting amounts and currency
  labels survive amendments/successors without recomputing published evidence.

## FIX-VAL-002 — Scoped source reassessment delivered

**Current status — 3 November 2026:** [Consistency delivery](docs/delivery/instrument-consistency-20261103.md)
adds scoped market observations/vintages/corrections, chosen policy/rules/cuts/
priorities, calendar/assignment/venue and visible quantity-action/review-chain
fingerprints. Detail, history, SQL-filtered worklist and publication use the same
source comparison. Frozen published amounts stay unchanged. Requested price
windows preserve lagged NAV semantics; unrelated dates, unentitled observations
and independent new policy versions do not automatically replace the frozen
choice. Older batches need fresh calculation to acquire this dependency proof.
General reference amendments, distribution entitlement and representative
large-history capacity remain outside this resolution. The original dated
finding below is preserved as the pre-fix evidence, not current behavior.


**Evidence status:** Confirmed (static scope limitation, 2026-10-14).

**Rechecked 2026-10-27:** Ledger, window-bounded cash, daily-interest and actual
coupon revisions now participate in source health/publication checks. Generalized
market-observation, policy, calendar and corporate-action change fan-out remains
outside these predicates. Preserve that distinction when reading the original
finding below; CURRENT is not universal source recertification.

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

The [ETP/spot-crypto extension](docs/delivery/etp-spot-crypto-pnl-20261028.md) adds
synthetic native-booking, price/FX, unit-label, calendar and publication cases.
These close capability/fixture regressions, not the outstanding independent
real-portfolio or concurrent-scale acceptance.

28 October scoped follow-up: [structured-note delivery](docs/delivery/structured-note-pnl-20261028.md)
adds hand-calculated and disposable real-booking cases plus report inspection.
This does not close the independent real-portfolio/scale acceptance finding.
Note lifecycle, detached coupon receivables and cross-quotation normalization
remain explicitly deferred capabilities; missing optional interest is disclosed.

**Evidence status:** Confirmed (verification limitation, 2026-10-14).

**Rechecked 2026-10-27:** A further 73 offline tests passed in the state review.
The latest accrued-stock delivery records 74 focused database/pure checks, 1,055
frontend checks and two isolated browser cases. Earlier user-reported close
agreement with the exported production process is encouraging, but those rounded
comparisons excluded accrual/cash components and are not an independently retained
complete economic-P&L acceptance set. Source replay still reads historical inputs;
daily accrual coverage reconstructs the ledger per day, and report detail loads
full evidence before client pagination. No representative load bound was measured.

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
