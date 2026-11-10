# Tenant reference data and strategy trade profiles implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. Do not delegate. Execution is implemented; use the [delivery record](../../delivery/tenant-reference-data-trade-profiles-20261104.md) for verified behavior, evidence and differences from these original tasks. Do not commit/push or alter operating settings without the task's actual authorization.

**Goal:** Maintain tenant-wide reference data once and enforce a reusable, versioned standard/custom trade profile for each strategy.

**Architecture:** Reuse canonical parties, users, controlled catalogues and immutable annotations. Introduce normalized profile versions, field rules and retained strategy assignments below HTTP; use one scoped resolver across every supported booking/import/lifecycle consumer. Separate UI maintenance from rule configuration and strategy usage.

**Tech stack:** Existing PostgreSQL 18/SQLAlchemy/Alembic, FastAPI adapters, Next.js BFF/React, generated OpenAPI/TypeScript, Vitest/Playwright.

**Spec:** [Reviewed design, schema and sources](../specs/2026-11-04-tenant-reference-data-trade-profiles.md).

## Global constraints

- Implementation was explicitly approved. Keep standard-field meaning, native product requirements, economic formulas, user permissions and tenant/strategy isolation intact.
- One pinned profile version per strategy; default materialised at strategy creation. No profile inheritance, product-type auto-assignment or strategy overrides.
- Current catalogue and trade evidence retain their original IDs, versions and bytes. No duplicate party lists or generic untyped entity-reference table.
- Core cutover must update all supported booking writers, corrections, import/template confirmation and bond/FX lifecycle, not just cash tickets.
- New backdated bookings resolve current configuration at command time. Successful retry semantics and current authority checks remain unchanged.
- Core scope uses all eligible values from each bound source. Profile-specific value subsets are a later extension with typed memberships, not part of completion criteria.
- Preserve optional metadata semantics and native required economics. Do not make a tenant-global required flag a hidden second authority after profile cutover.
- No operating trades, grants, chosen field values or valuation runs are part of acceptance. Use owned disposable databases and synthetic browser workflows.

## Review focus

1. A tenant/strategy UUID exists but belongs elsewhere: deny before reads/writes, counts, assignments or replay.
2. A profile becomes mandatory/hidden while a ticket, import report or lifecycle preparation is open: report a configuration conflict and preserve entered intent; never silently use a different version.
3. Metadata definitions get label revisions: stable field/record families do not produce additional lifecycle allocations; type/source changes require a different meaning or explicit remediation.
4. Retired/currently hidden values occur in source trades: history remains readable; prove permitted source inheritance, and do not invent a new value or silently widen eligibility.
5. A save succeeds but the following read fails, or an old successful request is retried: preserve confirmation/receipt and recover by read; no duplicate trades or misleading rejected-write state.

## Phase 1 — Reference data workspace, existing behavior retained

### Task 1: Shared source boundary and browsable reference data

**Files:** create `tenant_reference/__init__.py`, `tenant_reference/catalogues.py`, `tenant_reference/sources.py`; modify `apps/reference_api/governed_trade_configuration.py`, `apps/reference_api/trade_configuration_routes.py`, `apps/reference_api/main.py` and `apps/reference_api/workload_admission.py`; add a thin `apps/reference_api/tenant_reference_routes.py`. Existing organisation/person/role eligibility remains authoritative.

**Interfaces:** `list_sources(connection,tenant_id,actor_id,query,offset,limit)` returns typed source descriptors and exact scoped pagination; `list_source_options(...,source_key,consumer_context,query,offset,limit,selected_ids)` returns human labels and immutable/stable identities appropriate to the source. Configuration-maintenance reads and booking-scoped reads must be distinct authority paths.

- [ ] Write `tests/test_tenant_reference_sources.py`: custom catalogues and canonical organisation/trader sources appear without cloned identities; foreign and inactive sources are rejected; read-only consumers cannot maintain data; Used by output is strategy-scoped and its count does not reveal hidden strategies.
- [ ] Reproduce missing API/domain behavior in disposable/offline tests, then extract the necessary shared catalogue dependency closure below HTTP. Do not move unrelated trading/API logic.
- [ ] Add typed paged/search contracts and BFF allowlists; server predicates precede pagination/count. Preserve existing catalogue IDs/URLs and immutable historical records.
- [ ] Verify existing `tests/test_governed_trade_configuration.py`, `tests/test_tenant_organisations.py`, new source tests and affected authority/domain-boundary tests. Regenerate/check OpenAPI/TypeScript only after behavior is verified.

### Task 2: Reference-data UI and removal of duplicated maintenance

**Files:** create `apps/ops-console/src/features/tenant-reference/` components/client/types, routes under `apps/ops-console/src/app/tenant-profile/reference-data/`, scoped styles and BFF `apps/ops-console/src/app/api/tenant-reference/[...path]/route.ts`; modify tenant-profile navigation, current trade-configuration catalogue links and shared page-help registry at its existing owner.

**Interfaces:** the UI uses Task 1 descriptors; it routes canonical organisations to the existing organisation workspace, users to the existing user workspace and custom catalogues to their own detail. A source selection is a reference, never a submitted authoritative label.

- [ ] Add failing focused component/BFF tests plus `apps/ops-console/browser-tests/tenant-reference.spec.ts`: filter beyond page 1, selected off-page values, separate unavailable/empty states, unchanged stable identity on label correction, keyboard navigation and mobile containment.
- [ ] Build a compact searchable reference register with status/source/usage and paged entry detail. Add Entries / Used by / History using existing manual-activation tab behavior. Keep technical IDs collapsed.
- [ ] Provide Add/correct/retire entry with audit reason, impact review and inline/summary errors. Confirmed writes with failed refresh remain confirmed. Preserve drafts when moving to a related source page.
- [ ] Redirect/link old catalogue maintenance to the new canonical page after parity; no two independent catalogue editors. Keep field-library and profile entry points discoverable.
- [ ] Run touched UI/BFF/type checks and isolated browser tests; record screenshots and console/HTML diagnostics. No claim that moving the UI alone delivers strategy profiles.

## Phase 2 — Relational profiles and complete backend enforcement

### Task 3: Profile schema, published versions and strategy assignments

**Files:** create `security_master_schema/trade_profile_tables.py`, `trading/profiles/{__init__,contracts,store,configuration}.py`; register models in `security_master_schema/models.py`; add additive Alembic migration(s) using the then-current head. Extend `trd.trade` with retained new-booking configuration references without altering old evidence. Add API/BFF profile routes as thin adapters.

**Interfaces:** `publish_profile_version(c,tenant,actor,profile_id,expected_version,rules,reason)`, `preview_assignment_change(c,tenant,actor,strategy_ids,version_id)`, `assign_profile(c,tenant,actor,strategy_id,version_id,expected_revision,reason)`; actor and strategy authority come from server context. Changes are caller-transaction/audit owned and idempotent where existing command patterns require it.

- [ ] Add RED cases in `tests/test_trade_profiles_store.py`: immutable versions/assignments, composite-tenant FK failures, duplicate field-family rules, standard/custom exactly-one binding, wrong catalogue/type, concurrent revision conflict and current permission before replay.
- [ ] Implement the five core relations in the spec, real FKs/indexes, content hash and append-only protection. Standard fields use a backend registry; custom rules pin existing tenant/code/version definitions. Do not add JSONB as the sole rule/assignment store.
- [ ] Add `tests/test_trade_profile_cutover.py`: repeated backfill creates one Standard profile per tenant; copies actual mandatory/allocation settings; explicit assignment/default counts match tenants/strategies; BOOKED payloads/property rows unchanged; foreign tenant data never mixed.
- [ ] Implement a repeatable migration/cutover operation under tenant configuration locking; no arbitrary strategy-type guesses or automatic permission grants. Published profile versions stay immutable and separate from application to strategies.
- [ ] Verify disposable migration/store/cutover tests and inspect representative assignment/rule/usage query plans. No history truncation or per-strategy catalogue/permission N+1 reads.

### Task 4: One resolver across all supported write paths

**Files:** create `trading/profiles/resolution.py`; modify `trading/annotations.py`, `trading/booking.py`, `trading/position_movements.py`, `trading/allocation_policy.py`, `lifecycle/allocations.py`, `lifecycle/bond_service.py`, `lifecycle/fx_service.py`; update `apps/reference_api/{product_booking,option_booking,fx_forward_booking,generic_swap_booking,swap_booking}.py` at their actual shared validation seams, trade lookup/context adapters and `apps/reference_api/import_adapters/trades.py`/import service. Inventory the actual call graph before edits so delegated/shared writers are not double-validated.

**Interfaces:** `resolve_trade_configuration(c,tenant,strategy,actor,operation,expected_assignment_revision=None)` returns typed profile context/hash. Annotation validation consumes this context explicitly; it does not infer a default when strategy identity is absent. Read contexts must enforce consumer authority separately from TRADE_CONFIGURE.

- [ ] Add `tests/test_trade_profile_resolution.py` with one field required in strategy A, optional in B and unavailable in C; same tenant/source identity. Test native product minimums cannot be relaxed, cross-tenant profile/source denial and active tenant/role checks.
- [ ] Add `tests/test_trade_profile_consumers.py`: cash, bond, option, future, FX, note and swap paths, fund transfers/reinvestments and linked corrections resolve the same profile policy, retain product economics and persist exact configuration proof. Test current-authority successful retries after profile change create nothing new.
- [ ] Implement contextual annotation/party validation, searchable lookup and frozen new-booking config IDs/hash. Old trades read back their actual evidence without a fabricated profile association. Resolve current rules for a new backdated booking.
- [ ] Add import/template cases to existing `tests/test_import_trades.py` and `tests/test_import_download.py`: strategy-specific headers/dropdowns/requirements, stale template/report, revalidation at confirmation, unchanged all-or-nothing/retry behavior and exact reference identities.
- [ ] Update templates only within existing supported import families; profiles do not enable unsupported product imports.
- [ ] Add lifecycle cases in `tests/test_trade_profile_lifecycle.py` plus existing allocation tests: joint dimensions, opposing economic zero, renamed definition family, hidden inherited values, retired blockers, required fresh values, changed preparation, atomic rollback/cancellation and independent approval.
- [ ] Implement source-preserving lifecycle/correction validation as explicit server-evidenced operations. No arbitrary browser flag bypass. Impact preview blocks unsafe allocation reinterpretation while positions/history/prepared entries exist; no FIFO/automatic reclassification.
- [ ] Run focused affected Python suites through `scripts/run_isolated_python_tests.py`; broaden only for a demonstrated new change/failure. Do not expose selectable profiles until every supported consumer passes.

## Phase 3 — Profiles UI, strategy adoption and cutover acceptance

### Task 5: Profile editor, review/apply and strategy configuration

**Files:** create `apps/ops-console/src/features/trade-profiles/`, routes under `apps/ops-console/src/app/tenant-profile/trade-configuration/profiles/` and matching BFF adapter; modify the existing trade-configuration field-library UI, strategy detail/create UI, product ticket metadata contexts and file-template screens. Reuse common field/property controls and current transport/draft handling; do not consolidate product economics into one oversized component.

**Interfaces:** list/profile-version reads, reviewed version publication, scoped usage and assignment preview/apply use Tasks 3–4. Every ticket displays the exact assigned version and carries the expected assignment/configuration fingerprint as advisory intent; the server remains authoritative.

- [ ] Add RED UI/BFF cases for standard/custom fields, missing native-required disable reasons, separate unsaved/published/assigned state, version labels, assignment conflicts and unchanged entered values after configuration conflict.
- [ ] Build Profiles / Field library / History landing views. In profile detail keep Fields and Lifecycle rules separate, with clear source links and one row editor instead of an enormous matrix. Provide Create, Clone and Publish new version; clone rules, not catalogue contents.
- [ ] Build review-before-publish/apply showing differences, dependencies and **scoped** affected strategies. Editing a shared profile never silently changes current assignments. Retired dependencies prevent use with a human-readable remedy.
- [ ] Show assigned profile/version on strategy detail and creation; materialise tenant default atomically when creating a strategy. An authorised user can select another published version; readers can inspect effective settings without getting configuration rights.
- [ ] Remove the tenant-wide Required toggle and tenant-global allocation editor as active writers at cutover. Retain historical schema/evidence only, not permanent dual semantics. Link the existing allocation help to the profile's Lifecycle rules section.
- [ ] Add/adjust ticket and import UX for strategy-dependent fields, selected value retention and explicit stale-context recovery. Changing strategy must not carry disallowed values into another profile silently.
- [ ] Run targeted Vitest/BFF/type/contract tests and isolated browser journeys for configuration, strategy selection and representative product tickets. Verify keyboard focus, 390px/desktop layout, errors, counts and console diagnostics with human labels rather than UUIDs.

### Task 6: End-to-end adoption, documentation and local activation evidence

**Files:** add `tests/test_trade_profile_acceptance.py`, `apps/ops-console/browser-tests/trade-profiles.spec.ts`; reconcile F20/F24/F51 capability/register/implementation map, shared source documentation, source-folder knowledge and a dated delivery report.

- [ ] In an owned disposable app/database create a shared catalogue and two profiles; assign two strategies, require a custom field in only one, verify canonical standard sources and prove foreign tenant denial. Book synthetic supported examples without modifying financial validators.
- [ ] Publish a new version without changing existing strategies; show that usage/booking still uses the pinned version. Explicitly adopt it, reject a stale ticket/import report and preserve a successful historical retry receipt.
- [ ] Close a bond/FX maturity with different allocations and confirm per-allocation zeros and persisted mandatory metadata. Attempt unsafe allocation-profile adoption and require explicit remediation; independently verify readback and cancellation.
- [ ] Fault-inject a save/post/audit failure and a successful write followed by failed refresh; demonstrate rollback or confirmed-read-recovery as appropriate, never partial configuration/trade state.
- [ ] Reconcile documentation as **implemented** only with actual code/test/activation evidence. Preserve the distinction between profile metadata support, product booking coverage and not-yet-built lifecycle handlers.
- [ ] Apply local migration/restart only within the authorization of the implementation task and after passing checks. Record head, health, cutover counts and unchanged operating trade hashes. Do not select non-default business rules, change user grants or run operating financial examples as part of activation.

## Later extension, deliberately separate

Add narrower ALL_ELIGIBLE/SELECTED value sets only if requested. Design typed membership tables and stable catalogue identity FKs first; explicit empty means none. Add no rules for arbitrary queries, automatic type/category assignment or commercial eligibility. Current source membership always bounds profile eligibility. See the spec for the normalized extension, not JSON arrays of UUIDs.

## Verification commands (planned, not run for this documentation task)

- Start with new pure resolver/contract tests, then use `.venv/Scripts/python.exe -X utf8 -B scripts/run_isolated_python_tests.py tests/<focused-file>.py -q` for DB/service checks.
- `pnpm --filter ops-console test <touched paths>` and `pnpm --filter ops-console typecheck`.
- `pnpm contract:check` and `pnpm contract:generate:check` after generated contract updates.
- `pnpm --filter ops-console test:browser browser-tests/tenant-reference.spec.ts browser-tests/trade-profiles.spec.ts` plus affected existing configuration/lifecycle browser cases. Use the installed supported browser channel when bundled browser binaries are unavailable.
- Markdown local links, scoped diff/whitespace and repository content rules. Documentation-only planning does not require a full Python regression suite.

## Execution reconciliation — 4 November

All three phases and six task groups have implemented code and focused coverage. Original checklist items above are the original acceptance prompts, not a claim that every suggested file route was used verbatim. The UI retains one trade-configuration landing route with Profiles / Field library / History, rather than creating duplicate profile-only pages. Shared canonical selectors remain typed adapters; no generic entity master was added. Original task evidence, red/green results and owned service logs are retained in the local task ledger. See delivery for the consolidated verification and explicit limits. Local activation is recorded separately there.
