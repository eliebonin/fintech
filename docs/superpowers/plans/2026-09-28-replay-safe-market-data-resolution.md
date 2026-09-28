# Replay-Safe Market Data Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an API-first, tenant-safe resource that freezes replayable market-data selection evidence for one to fifty subjects.

**Architecture:** A domain resolver applies the existing valuation-policy precedence and `valuation_resolver` pricing behaviour, but obtains candidates only through historic vintage/correction and entitlement predicates. A Reference API create command writes an append-only snapshot and idempotency record in one transaction; its GET path returns frozen rows only. OpenAPI remains the source for generated TypeScript contracts, and the Ops Console adds only a one-subject BFF-driven create/read journey.

**Tech Stack:** Python 3.12, SQLAlchemy, PostgreSQL/Alembic, FastAPI/OpenAPI 3.1, pytest/HTTPX, TypeScript, pnpm, `openapi-typescript`, `openapi-fetch`, Next.js, Vitest.

**Spec:** [docs/superpowers/specs/2026-09-28-replay-safe-market-data-resolution-design.md](../specs/2026-09-28-replay-safe-market-data-resolution-design.md)

## Global Constraints

- The public resources are `POST /v1/market-data-resolution-snapshots` and `GET /v1/market-data-resolution-snapshots/{snapshotId}`; do not add a verb endpoint.
- A create request has 1–50 unique `subjectReferenceNodeIds` with one shared policy, valuation date/cut, UTC information cut, and use purpose.
- Require `Idempotency-Key`; scope it to tenant and endpoint; the same key plus same canonical payload replays the original snapshot, while a different payload returns `409`.
- Validate policy tenant, active/effective dates, and policy/cut ownership before any snapshot insert.
- Rules select only in this order: exact series, exact canonical node, instrument type, then policy default; the first matching rule never falls through because of unavailable data.
- A vintage is eligible only if receipt and, when present, source publication were known by the requested UTC information cut. A correction supersedes an older observation only when that correction was eligible at that same cut.
- Persist business outcomes (`SELECTED`, `MISSING`, `STALE`, `DENIED`) as items. Structural invalidity is an RFC 9457 error with no snapshot.
- Snapshots are append-only in application and database paths; reads must not re-resolve data or evaluate current entitlement.
- Continue to use existing `valuation_resolver` pricing-date, lag, staleness, and missing-data calculation semantics unchanged.
- Add API shapes through FastAPI contracts, export the checked-in OpenAPI artifact, and regenerate `packages/api-contracts`; do not hand-write duplicate TypeScript API models.
- Keep tenant context in server/BFF code. The initial UI resolves exactly one currently selected subject and contains no tenant credential.
- This slice excludes live ingestion, generic policy DSL, market-data write API, provider calendars, portfolio job orchestration, and Soft NAV/P&L behaviour changes.

## Review Focus

- A correction arriving after the historic cut must not suppress the older observation; Task 2 adds the late-correction resolver test.
- A provider publication later than the cut, even when receipt is earlier or data is otherwise accepted, must be ineligible; Task 2 adds the late-publication test.
- Retrying an otherwise successful POST after a lost response must not create another snapshot; Task 4 adds the identical-key replay test.
- A caller must never infer another tenant's snapshot existence from `GET`; Task 5 adds the cross-tenant not-found/forbidden-safe test.
- A snapshot detail response must remain identical after present-day entitlement or observation changes; Task 5 adds the frozen-read/no-reresolution test.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `security_master_schema/models.py` | Snapshot evidence columns and idempotency table metadata. |
| `alembic/versions/20260928_46_replay_safe_market_data_resolution.py` | Additive schema migration, append-only triggers, indexes, and idempotency uniqueness. |
| `security_master_schema/market_data_vintages.py` | UTC vintage eligibility helper used by the resolver. |
| `security_master_schema/market_data_resolver.py` | Domain candidate eligibility, outcome classification, batch snapshot creation, and frozen persistence. |
| `tests/test_market_data_vintages.py` | Unit coverage for source/receipt cut eligibility. |
| `tests/test_market_data_resolver.py` | Resolver precedence, timing, entitlement, and frozen persistence coverage. |
| `tests/test_market_data_resolution_snapshot_schema.py` | Migration-level append-only and idempotency constraints. |
| `apps/reference_api/contracts.py` | Pydantic create/read/policy-list contract models and OpenAPI examples. |
| `apps/reference_api/repository.py` | Tenant-scoped policy list, create, and frozen snapshot read adapters. |
| `apps/reference_api/main.py` | POST/GET/list routes, idempotency header, problem mapping, and `Location`. |
| `tests/test_reference_api_market_data_resolution.py` | HTTP contract, tenant, idempotency, and frozen-read tests. |
| `packages/api-contracts/openapi/reference-data-api.v1.json` | Generated OpenAPI artifact. |
| `packages/api-contracts/src/generated.ts` | Generated TypeScript API types; never hand edited. |
| `packages/api-contracts/src/client.ts` | Existing generated typed client surface used by BFF routes. |
| `packages/api-contracts/test/market-data-resolution.test.ts` | Type-level representative create/read consumer test. |
| `apps/ops-console/src/lib/market-data-resolution.ts` | UI-only formatting helpers; no API payload duplication. |
| `apps/ops-console/src/app/api/market-data/resolution-snapshots/route.ts` | Server-side BFF create proxy and server-created idempotency key. |
| `apps/ops-console/src/app/api/market-data/resolution-snapshots/[snapshotId]/route.ts` | Server-side tenant-safe frozen-read proxy. |
| `apps/ops-console/src/app/market-data/page.tsx` | One-subject resolve entry point from selected history. |
| `apps/ops-console/src/app/market-data/resolution-snapshots/[snapshotId]/page.tsx` | Frozen snapshot evidence page. |
| `apps/ops-console/src/app/market-data/resolution-snapshots/[snapshotId]/page.test.tsx` | Evidence rendering test. |
| `docs/platform/api/market-data-resolution-snapshots.md` | Stable request/outcome/evidence and retry semantics for operators/integrators. |
| `docs/delivery/quality-reviews/2026-09-28-replay-safe-market-data-resolution.md` | Final command evidence, limitations, and explicit deferrals. |

### Task 1: Add frozen-evidence and idempotency storage with database immutability

**Files:**
- Modify: `security_master_schema/models.py:2109-2140`
- Create: `alembic/versions/20260928_46_replay_safe_market_data_resolution.py`
- Create: `tests/test_market_data_resolution_snapshot_schema.py`

**Interfaces:**
- Consumes: existing `md.market_data_resolution_snapshot`, `md.market_data_resolution_snapshot_item`, tenant/policy/observation/vintage/dataset/licence tables.
- Produces: `m.market_data_resolution_idempotency`, new frozen evidence columns on `m.market_data_resolution_snapshot` and item, and database rejection of snapshot header/item `UPDATE`/`DELETE`.

- [ ] **Step 1: Write failing schema tests**

Create tests that insert one snapshot/item, assert frozen vintage/publication/receipt/licence evidence round-trips, then assert direct `UPDATE` and `DELETE` fail. Add a test that duplicate `(tenant_id, endpoint, idempotency_key)` insertion fails.

- [ ] **Step 2: Run schema tests to verify they fail**

Run: `python -m pytest tests/test_market_data_resolution_snapshot_schema.py -v`

Expected: FAIL because the fields, idempotency table, indexes, and append-only triggers do not exist.

- [ ] **Step 3: Add model metadata and migration**

Add only additive nullable evidence fields needed to reproduce the response: header `use_purpose`; item `market_data_vintage_id`, `source_published_at_utc`, `received_at_utc`, and `acquisition_licence_id`. Define `md.market_data_resolution_idempotency` with `tenant_id`, literal endpoint, idempotency key, SHA-256 request fingerprint, snapshot foreign key, `created_at_utc`, and `expires_at_utc`; enforce a unique tenant/endpoint/key index and a snapshot lookup index.

In migration `20260928_46_replay_safe_market_data_resolution.py`, add equivalent columns/table/foreign keys/indexes and separate `BEFORE UPDATE OR DELETE` triggers for both snapshot tables. The triggers must reject ordinary mutation with a clear database exception. Do not add trigger exceptions for application roles; migration downgrade may drop the triggers and additive objects in reverse order.

- [ ] **Step 4: Run schema tests to verify they pass**

Run: `python -m pytest tests/test_market_data_resolution_snapshot_schema.py -v`

Expected: PASS; direct row mutation is rejected and an identical idempotency scope is unique.

- [ ] **Step 5: Commit the persistence boundary**

```bash
git add security_master_schema/models.py alembic/versions/20260928_46_replay_safe_market_data_resolution.py tests/test_market_data_resolution_snapshot_schema.py
git commit -m "feat: freeze market data resolution evidence"
```

### Task 2: Make domain selection historic, deterministic, and outcome-explicit

**Files:**
- Modify: `security_master_schema/market_data_vintages.py`
- Modify: `security_master_schema/market_data_resolver.py`
- Modify: `tests/test_market_data_vintages.py`
- Modify: `tests/test_market_data_resolver.py`
- Modify: `tests/test_market_data_cutoff_scenarios.py`

**Interfaces:**
- Consumes: `ResolutionRequest`, valuation policies/rules, observations/vintages/entitlements, and `valuation_resolver.resolve_price`.
- Produces: `resolve_market_data(connection, request) -> ResolvedMarketData` with frozen-vintage evidence and distinct `SELECTED`, `MISSING`, `STALE`, and `DENIED` outcomes; `resolve_market_data_batch(connection, request, subjects) -> tuple[ResolvedMarketData, ...]` preserving request order.

- [ ] **Step 1: Write failing timing and outcome tests**

Add tests named `test_late_correction_does_not_supersede_at_earlier_cut`, `test_late_source_publication_is_ineligible`, `test_receipt_and_publication_at_cut_are_eligible`, `test_policy_valuation_cut_must_match_request`, `test_no_less_specific_fallback_after_exact_rule_misses`, and `test_matching_unentitled_data_is_denied_not_missing`. Assert selected observation IDs and exact stable outcome/reason/exception values.

- [ ] **Step 2: Run focused domain tests to verify they fail**

Run: `python -m pytest tests/test_market_data_vintages.py tests/test_market_data_resolver.py tests/test_market_data_cutoff_scenarios.py -v`

Expected: FAIL on historic correction/vintage and outcome classification assertions; current query only filters receipt and suppresses every accepted correction.

- [ ] **Step 3: Tighten request and policy validation**

Require `market_data_as_of_utc` to have zero UTC offset, not merely any timezone. Extend `_assert_policy_scope(connection, request)` to require `valuation_policy.valuation_cut_id == request.valuation_cut_id`. Keep cross-tenant/inactive/effective-date rejection as `ValuationPolicyScopeError` for the API layer to map safely.

- [ ] **Step 4: Replace candidate query eligibility and classification**

Join observation to vintage and use `is_vintage_eligible`-equivalent SQL predicates for both observation/vintage provenance timestamps. Make the superseding-correction `exists` predicate include accepted status and the same historic eligibility predicates. Query candidate availability separately from entitlement so `DENIED` is distinguishable from `MISSING`; do not return unentitled observation identity/value in the result.

Retain existing rule ordering and call into `resolve_price` unchanged. Map its non-selected stale/missing result to the stable item outcome/reason/exception vocabulary. Add batch orchestration that validates unique subjects and calls the single-subject resolver in supplied order without creating persistence side effects.

- [ ] **Step 5: Extend `ResolvedMarketData` and frozen insert mapping**

Add optional fields for vintage ID, source publication timestamp, receipt timestamp, and acquisition licence ID. Update `persist_resolution_snapshot(connection, request, items)` to insert those fields but preserve its existing use by `soft_nav_service`; no Soft NAV calculation behaviour changes in this task.

- [ ] **Step 6: Run focused domain tests to verify they pass**

Run: `python -m pytest tests/test_market_data_vintages.py tests/test_market_data_resolver.py tests/test_market_data_cutoff_scenarios.py -v`

Expected: PASS, including late-correction, late-publication, denial, precedence, and policy-cut cases.

- [ ] **Step 7: Commit the domain behaviour**

```bash
git add security_master_schema/market_data_vintages.py security_master_schema/market_data_resolver.py tests/test_market_data_vintages.py tests/test_market_data_resolver.py tests/test_market_data_cutoff_scenarios.py
git commit -m "feat: resolve market data at historic information cuts"
```

### Task 3: Define the API contracts and frozen repository adapters

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Create: `tests/test_reference_api_market_data_resolution_repository.py`

**Interfaces:**
- Consumes: `ResolutionRequest`, `resolve_market_data_batch`, `persist_resolution_snapshot`, and snapshot/idempotency schema objects.
- Produces: `MarketDataResolutionSnapshotCreate`, `MarketDataResolutionSnapshotView`, `MarketDataResolutionSnapshotItemView`, `list_active_valuation_policies(connection, tenant_id, valuation_date)`, `create_market_data_resolution_snapshot(connection, tenant_id, payload, idempotency_key, request_id)`, and `get_market_data_resolution_snapshot(connection, tenant_id, snapshot_id)`.

- [ ] **Step 1: Write failing repository/contract tests**

Assert Pydantic rejects empty, duplicate, and 51-item subject arrays plus non-UTC timestamps. Add repository tests that create a two-subject snapshot, return results in request order, replay the exact fingerprint to the same snapshot, reject a conflicting reuse, and read frozen fields after changing a live entitlement/observation fixture.

- [ ] **Step 2: Run repository tests to verify they fail**

Run: `python -m pytest tests/test_reference_api_market_data_resolution_repository.py -v`

Expected: FAIL because contracts and repository functions do not exist.

- [ ] **Step 3: Add exact Pydantic models and repository operations**

Use camelCase aliases consistent with current API contracts. `MarketDataResolutionSnapshotCreate` owns the validated payload; model the idempotency key as a header, not body field. Response models expose only the frozen, safe evidence defined by the spec and JSON-safe decimal/date/datetime serialization.

In `create_market_data_resolution_snapshot`, calculate a canonical SHA-256 fingerprint from the validated payload, lock/read the tenant-endpoint-key record, replay identical requests, and raise a dedicated conflict for differing fingerprints. Otherwise resolve all items and persist them plus the idempotency record in one transaction. `get_market_data_resolution_snapshot` selects only persisted header/item rows and tenant filters at the query; it must not call the resolver. Return absence through the existing safe not-found convention.

- [ ] **Step 4: Run repository tests to verify they pass**

Run: `python -m pytest tests/test_reference_api_market_data_resolution_repository.py -v`

Expected: PASS; one transaction produces a frozen ordered snapshot and duplicate POST retry semantics are deterministic.

- [ ] **Step 5: Commit contracts and repository adapters**

```bash
git add apps/reference_api/contracts.py apps/reference_api/repository.py tests/test_reference_api_market_data_resolution_repository.py
git commit -m "feat: add market data snapshot repository contract"
```

### Task 4: Expose create/read and active-policy Reference API routes

**Files:**
- Modify: `apps/reference_api/main.py:693-709`
- Modify: `apps/reference_api/contracts.py`
- Create: `tests/test_reference_api_market_data_resolution.py`
- Modify: `docs/platform/api/README.md`
- Create: `docs/platform/api/market-data-resolution-snapshots.md`

**Interfaces:**
- Consumes: Task 3 contract/repository functions, existing `TenantContext`, problem-details mapping, and request-ID middleware.
- Produces: `POST /v1/market-data-resolution-snapshots`, `GET /v1/market-data-resolution-snapshots/{snapshotId}`, and narrow active-policy lookup `GET /v1/market-data/valuation-policies`.

- [ ] **Step 1: Write failing HTTP contract tests**

Test successful POST returns `201`, `Location`, `X-Request-ID`, full snapshot body, and a subsequent GET returns the same frozen body. Test missing idempotency key yields a documented 4xx problem, duplicate retry yields the original snapshot, changed payload/key yields `409 idempotency.key_reused`, invalid policy/cut returns safe validation/domain problem, and cross-tenant GET does not return another tenant's snapshot.

- [ ] **Step 2: Run HTTP tests to verify they fail**

Run: `python -m pytest tests/test_reference_api_market_data_resolution.py -v`

Expected: FAIL because routes and OpenAPI operations do not exist.

- [ ] **Step 3: Implement routes and problem mapping**

Import only contracts/repository functions at the route boundary. Use `Header(..., alias="Idempotency-Key")`, trusted `get_tenant_context`, `_assert_tenant_membership`, and the existing request-ID mechanism. Translate dedicated invalid context/key conflict/domain exceptions into stable existing problem codes; never pass raw `ValueError`/SQL text into responses. Set `Location` to the new resource URI. Add the active-policy lookup limited to active/effective policies for the trusted tenant, returning policy/cut display metadata required by the UI only.

- [ ] **Step 4: Document the public integration contract**

Write the endpoint, header, 1–50 limit, retry/conflict rules, all outcome and exception codes, immutability guarantee, and the explicit distinction between a history catalogue and frozen evidence. Add it to `docs/platform/api/README.md`.

- [ ] **Step 5: Run HTTP tests to verify they pass**

Run: `python -m pytest tests/test_reference_api_market_data_resolution.py -v`

Expected: PASS, including no cross-tenant disclosure and idempotent retry.

- [ ] **Step 6: Commit Reference API routes**

```bash
git add apps/reference_api/main.py apps/reference_api/contracts.py tests/test_reference_api_market_data_resolution.py docs/platform/api/README.md docs/platform/api/market-data-resolution-snapshots.md
git commit -m "feat: expose replay safe market data snapshots"
```

### Task 5: Regenerate and verify the OpenAPI TypeScript contract

**Files:**
- Modify: `packages/api-contracts/openapi/reference-data-api.v1.json`
- Modify: `packages/api-contracts/src/generated.ts`
- Modify: `packages/api-contracts/test/consumer.test.ts`
- Create: `packages/api-contracts/test/market-data-resolution.test.ts`

**Interfaces:**
- Consumes: FastAPI OpenAPI export and existing `pnpm` contract-generation scripts.
- Produces: generated `paths` entries and typed request/response/header usage for the snapshot and active-policy endpoints.

- [ ] **Step 1: Write failing generated-consumer tests**

Add a type-level test that calls `client.POST("/v1/market-data-resolution-snapshots", ...)` with the required body and `Idempotency-Key`, and `client.GET` for snapshot/policy paths. Assert TypeScript rejects an empty `subjectReferenceNodeIds` only where the generated type supports it, and use runtime schema/OpenAPI assertions to prove `minItems`, `maxItems`, duplicate prohibition, header, `201`, `409`, and common problem responses are documented.

- [ ] **Step 2: Run contract tests to verify they fail**

Run: `pnpm --filter @fintech/api-contracts test`

Expected: FAIL because the checked-in OpenAPI artifact has no snapshot paths.

- [ ] **Step 3: Export and regenerate; do not edit generated output manually**

Run the existing OpenAPI export and TypeScript generation scripts. Update only source annotations/contracts if export is missing required request constraints or response codes, then regenerate. Keep `src/client.ts` route-agnostic.

- [ ] **Step 4: Run drift and consumer verification**

Run: `pnpm run api:contract:check; pnpm --filter @fintech/api-contracts test; pnpm run typecheck`

Expected: PASS with no OpenAPI/generated-file drift and typed POST/GET consumption.

- [ ] **Step 5: Commit generated contract evidence**

```bash
git add packages/api-contracts/openapi/reference-data-api.v1.json packages/api-contracts/src/generated.ts packages/api-contracts/test/consumer.test.ts packages/api-contracts/test/market-data-resolution.test.ts
git commit -m "feat: generate market data snapshot API types"
```

### Task 6: Add the minimal trusted-BFF Ops Console evidence journey

**Files:**
- Create: `apps/ops-console/src/lib/market-data-resolution.ts`
- Create: `apps/ops-console/src/app/api/market-data/resolution-snapshots/route.ts`
- Create: `apps/ops-console/src/app/api/market-data/resolution-snapshots/[snapshotId]/route.ts`
- Modify: `apps/ops-console/src/app/market-data/page.tsx:100-121`
- Create: `apps/ops-console/src/app/market-data/resolution-snapshots/[snapshotId]/page.tsx`
- Create: `apps/ops-console/src/app/market-data/resolution-snapshots/[snapshotId]/page.test.tsx`

**Interfaces:**
- Consumes: Task 5 generated `api-contracts` client/types and existing server-only tenant context.
- Produces: a one-subject create flow from market-data history and a read-only evidence page driven entirely by a frozen snapshot response.

- [ ] **Step 1: Write failing UI/BFF tests**

Test that the POST BFF builds a one-subject API body, forwards no browser tenant header, generates/forwards an idempotency key server-side, and redirects/returns the created snapshot ID. Render the detail page with a frozen `DENIED` item and a `SELECTED` item and assert result, value, policy rule, provider/dataset/licence, vintage publication/receipt versus cut, pricing/staleness, and exception reason are shown without calling a resolver.

- [ ] **Step 2: Run focused frontend tests to verify they fail**

Run: `pnpm --filter @fintech/ops-console test -- market-data-resolution`

Expected: FAIL because the BFF routes, UI helper, and snapshot page do not exist.

- [ ] **Step 3: Implement server-only BFF adapters with generated types**

Use the `api-contracts` typed client in both BFF routes and `resolveLocalTenantContext()` only on the server. Generate a UUID idempotency key in the POST route; never accept tenant ID or idempotency key from browser form fields. Preserve API problem status/code/request ID through the existing safe BFF error handling rather than exposing unknown upstream JSON.

- [ ] **Step 4: Add one-subject market-data UI and immutable evidence view**

On an already selected `referenceNodeId` history page, show a compact form with active policy, valuation date/cut, UTC information cut, and use-purpose controls. Submit to the BFF and navigate to the returned snapshot page. Keep the list/catalogue view unchanged.

The evidence page fetches only `GET /api/market-data/resolution-snapshots/{snapshotId}` and renders frozen header/item evidence. Use `apps/ops-console/src/lib/market-data-resolution.ts` only for display formatting/status labels; it must import generated API types rather than defining payload shapes.

- [ ] **Step 5: Run frontend tests and build verification**

Run: `pnpm --filter @fintech/ops-console test -- market-data-resolution; pnpm --filter @fintech/ops-console typecheck; pnpm --filter @fintech/ops-console build`

Expected: PASS; the UI proves a one-subject create-to-frozen-evidence journey.

- [ ] **Step 6: Commit the minimal console flow**

```bash
git add apps/ops-console/src/lib/market-data-resolution.ts apps/ops-console/src/app/api/market-data/resolution-snapshots apps/ops-console/src/app/market-data/page.tsx apps/ops-console/src/app/market-data/resolution-snapshots
git commit -m "feat: show frozen market data resolution evidence"
```

### Task 7: Run slice verification and record delivery evidence

**Files:**
- Create: `docs/delivery/quality-reviews/2026-09-28-replay-safe-market-data-resolution.md`
- Modify: `docs/delivery/quality-reviews/README.md`

**Interfaces:**
- Consumes: all completed API/domain/contract/BFF deliverables and the existing quality commands.
- Produces: a dated, reproducible verification record with remaining limitations.

- [ ] **Step 1: Run full focused verification**

Run:

```bash
python -m pytest tests/test_market_data_vintages.py tests/test_market_data_resolver.py tests/test_market_data_cutoff_scenarios.py tests/test_market_data_resolution_snapshot_schema.py tests/test_reference_api_market_data_resolution_repository.py tests/test_reference_api_market_data_resolution.py -v
python scripts/export_openapi_contract.py --check
pnpm run api:contract:check
pnpm --filter @fintech/api-contracts test
pnpm --filter @fintech/ops-console typecheck
pnpm --filter @fintech/ops-console test -- market-data-resolution
pnpm --filter @fintech/ops-console build
gitleaks git --redact --config .gitleaks.toml
```

Expected: all commands pass. If the known unrelated full Python-suite collection/stall recurs, record the exact command and observed boundary rather than calling the slice verified.

- [ ] **Step 2: Write verification evidence**

Document exact command outputs/status, schema migration revision, contract artifact generation, tested replay scenarios, API/UI scope, and excluded live-ingestion/Soft-NAV work. Link this review from the quality-review index.

- [ ] **Step 3: Commit final documentation**

```bash
git add docs/delivery/quality-reviews/2026-09-28-replay-safe-market-data-resolution.md docs/delivery/quality-reviews/README.md
git commit -m "docs: record market data resolution verification"
```

## Plan self-review

**Spec coverage:** Tasks 1–2 cover frozen evidence, append-only storage, historic vintage/correction eligibility, policy-cut validation, precedence, and outcome vocabulary. Tasks 3–4 cover atomic, tenant-safe idempotent resource creation/read plus active policy selection. Task 5 covers generated OpenAPI/TypeScript contract discipline. Task 6 deliberately limits the UI to one subject and frozen evidence. Task 7 records all verification and exclusions.

**Step scan:** Every task starts with a specific failing test, has an expected failure, a named interface/implementation action, a passing verification command, and a scoped commit. No task contains a generic "handle edge cases" instruction.

**Type consistency:** The create contract is `MarketDataResolutionSnapshotCreate`; the domain input remains `ResolutionRequest`; persistence/read output is `MarketDataResolutionSnapshotView`; `resolve_market_data_batch` is internal and `create_market_data_resolution_snapshot` is the repository boundary. BFF/UI consume the generated OpenAPI contract rather than a local duplicate.

**Review focus:** The five highest-risk silent failures—late correction, late publication, idempotent retry, cross-tenant reads, and accidentally live evidence—are assigned directly to Tasks 2, 4, and 5's tests.

**Proportion:** The plan specifies interfaces, exact files, tests, and decision points without prescribing implementation bodies beyond the few predicates/transaction choices that are architectural requirements.
