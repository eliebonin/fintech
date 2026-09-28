# Index Onboarding UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an approval-driven Index onboarding workflow to the operations console, backed by the existing `secm.index_family`, `secm.index_terms`, `secm.index_methodology_version`, `secm.return_profile`, and canonical reference-node model.

**Architecture:** Reuse the existing proposal/approval envelope used by equities and bonds. The browser submits a sparse, manual-first index proposal through a Next.js BFF route; the Python reference API validates catalog references and stores a pending proposal. Approval materializes a non-tradable `INDEX` node, optional index family, index terms, methodology version, tenant scope, and approval evidence atomically.

**Tech Stack:** Next.js 16 App Router, React 19, MUI, TypeScript, FastAPI, Pydantic, SQLAlchemy Core, PostgreSQL, Vitest, pytest.

**Implementation status (2026-09-07):** Implemented through the focused UI/API
slice. The page is server-rendered with a client form, so active currency,
return-profile, organisation, and index-family options are present in the
initial HTML. The DB-backed family catalogue, BFF route, proposal/approval
endpoints, screen specification, and decision-note updates are present.
Verification was limited to `tests/test_index_onboarding.py`, the two Index
frontend test files, TypeScript, the production build, and live endpoint/page
smoke checks; the full unittest suite was intentionally not run.

**Spec:** Existing index architecture in `security-master-notes/09-indices-fx-forwards-and-market-data-architecture.md`, `security-master-notes/16-database-implementation-plan.md`, and UI onboarding decisions in `ui/mvp-scope.md`.

## Global Constraints

- Manual submission is the default; the API creates `PENDING` proposals and never writes an approved index directly from the browser.
- An index is a non-tradable `INDEX` reference node, not a venue listing or ordinary `secm.instrument` row.
- Price, total-return, gross/net-total-return, excess-return, and dividend-points variants are separate index nodes selected through the governed return-profile catalogue.
- Existing schema migrations are unchanged; this slice uses already-created tables and adds no destructive refactor.
- All API catalogue lookups are tenant-authenticated and return active rows only.

---

### Task 1: Define the API contract and failing backend tests

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Create: `tests/test_index_onboarding.py`

**Interfaces:**
- Produce `IndexProposalRequest`, `IndexProposalView`, and `IndexProposalResponse` with camel-case aliases.
- Required request fields: `canonicalName`, `effectiveFrom`, and `indexKind` (`PUBLIC`, `QIS`, `PROPRIETARY`, `CUSTOM_BASKET`).
- Optional request fields: internal code, family name, return profile, base currency, administrator/calculation-agent organisations, base date/level, methodology reference, weighting/rebalance/calculation frequency, dividend treatment, launch date, back-tested-history flag, methodology URI.

- [ ] **Step 1: Write failing API tests**

  Add tests that submit a valid manual index proposal and assert `201`, `PENDING`, `CREATE_INDEX`, and the selected `indexKind`; reject an unknown `indexKind`; approve a complete proposal and assert an `INDEX` node, `index_terms`, `index_methodology_version`, and `reference_node_scope` are materialized.

- [ ] **Step 2: Run the focused tests and verify the expected failure**

  Run: `pytest tests/test_index_onboarding.py -q`

  Expected: collection or HTTP failures because the request model and endpoints do not yet exist.

- [ ] **Step 3: Add the Pydantic request/view/response models**

  Preserve `populate_by_name=True`, use `UUID | None` and `Decimal | None` for catalog references and numeric levels, and expose `proposalId`, `proposalType`, `indexKind`, `indexId`, `status`, `submissionMode`, and `proposedAt`.

---

### Task 2: Add read-only index catalogues

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Create: `apps/ops-console/src/lib/index-catalogues.test.ts`

**Interfaces:**
- `GET /v1/currencies?groups=REGULAR,CRYPTO` returns active currency rows in
  labelled groups. `REGULAR` maps to `FIAT`; `CRYPTO` maps to `CRYPTOASSET`
  and `STABLECOIN`. Omitting `groups` keeps the regular-currency default.
- `GET /v1/return-profiles` returns active `returnProfileId`, `profileCode`, `displayName`, `description`, `baseReturnBasis`, and `incomeTreatment`.
- `GET /v1/organisations` returns active `organisationId`, `displayName`, `legalName`, and `status`; optional `q` filters display/legal name.
- TypeScript client functions: `listCurrenciesFromBff`, `listReturnProfilesFromBff`, and `listOrganisationsFromBff`.

- [ ] **Step 1: Write failing client tests**

  Assert each client function calls the correct BFF/API path and includes tenant/user headers, and that the returned payload is typed.

- [ ] **Step 2: Run the focused client tests and verify failure**

  Run: `pnpm --filter ops-console test -- src/lib/index-catalogues.test.ts`

  Expected: missing-function or incorrect-path failures.

- [ ] **Step 3: Implement catalogue contracts, repository queries, routes, and BFF client functions**

  Query only `ACTIVE` rows, sort currencies by code inside stable labelled
  groups, return profiles by `sort_order` then code, and organisations by
  display name. Reuse the existing tenant context and API metadata conventions.

- [ ] **Step 4: Run focused backend/frontend tests**

  Run: `pytest tests/test_index_onboarding.py -q` and `pnpm --filter ops-console test -- src/lib/index-catalogues.test.ts`.

---

### Task 3: Implement proposal validation and approval materialization

**Files:**
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Modify: `tests/test_index_onboarding.py`

**Interfaces:**
- `submit_index_proposal(connection, tenant_id, actor_id, request) -> IndexProposalView`.
- `decide_index_proposal(connection, tenant_id, actor_id, proposal_id, decision, reason) -> IndexProposalView`.
- Routes: `POST /v1/index-proposals` and `POST /v1/index-proposals/{proposal_id}/decision`.

- [ ] **Step 1: Extend the failing tests for validation**

  Cover invalid/missing active return-profile or currency references, duplicate internal code, duplicate pending idempotency key, and the rule that a manual proposal remains pending.

- [ ] **Step 2: Run tests to verify failure**

  Run: `pytest tests/test_index_onboarding.py -q`

  Expected: endpoint not found or missing repository function failures.

- [ ] **Step 3: Implement proposal persistence**

  Store the aliased request payload with `payload_schema_version = 'index.v1'`, `proposal_type = 'CREATE_INDEX'`, source/idempotency metadata, tenant ID, and `PENDING` status. Return an existing proposal for the same tenant/source/idempotency key.

- [ ] **Step 4: Implement approval materialization**

  On approval:

  1. Resolve the active `INDEX` and optional `INDEX_FAMILY` node types.
  2. Resolve and validate active return profile, currency, and organisation references.
  3. Reuse an exact active family by canonical name when supplied; otherwise create a non-tradable `INDEX_FAMILY` node and `index_family` row.
  4. Create a non-tradable `INDEX` node and tenant-private scope.
  5. Insert `index_terms`.
  6. Insert methodology version 1 when methodology fields are supplied, with `APPROVED` status and steward evidence.
  7. Insert `reference_data_approval` and update the proposal status/reference node ID.

  Reject approval if the proposal is not pending or the supplied family would be ambiguous.

- [ ] **Step 5: Run focused tests to verify green**

  Run: `pytest tests/test_index_onboarding.py -q`.

---

### Task 4: Add the Next.js BFF route and index onboarding page

**Files:**
- Create: `apps/ops-console/src/app/api/instruments/indices/route.ts`
- Create: `apps/ops-console/src/app/instruments/indices/new/validation.ts`
- Create: `apps/ops-console/src/app/instruments/indices/new/validation.test.ts`
- Create: `apps/ops-console/src/app/instruments/indices/new/page.tsx`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Modify: `apps/ops-console/src/lib/navigation.ts`

**Interfaces:**
- BFF `POST /api/instruments/indices` forwards the JSON payload with the local tenant context and returns the reference API response/error shape.
- `validateIndexIdentity(canonicalName, indexKind)` returns field-level errors for the required identity fields.

- [ ] **Step 1: Write the failing UI validation tests**

  Assert blank canonical name and blank index kind are rejected, while a valid public index identity passes.

- [ ] **Step 2: Run the validation test and verify failure**

  Run: `pnpm --filter ops-console test -- src/app/instruments/indices/new/validation.test.ts`

  Expected: missing module/function failure.

- [ ] **Step 3: Implement validation and BFF route**

  Keep manual submission as the only visible/default route in this first slice; preserve the existing error translation used by equity and bond BFF routes.

- [ ] **Step 4: Build the page**

  Add clearly labelled sections:

  - Economic identity: canonical name, internal code, effective-from date, index kind, family name.
  - Return semantics: governed return-profile dropdown, with explanatory copy that S&P 500 price return and S&P 500 total return are different index nodes.
  - Administration: base currency, administrator, calculation agent.
  - Methodology: base date/level, weighting, rebalance/calculation frequency, dividend treatment, methodology reference/URI, launch date, back-tested flag.
  - Approval route: manual review explanation and submit action.

  Load catalogues on mount, show explicit loading/error states, allow blank optional catalog references, and display the proposal ID/status after submission.

- [ ] **Step 5: Add the navigation entry**

  Add `Add index` under the existing Reference data section without changing existing route semantics.

- [ ] **Step 6: Run focused frontend tests and typecheck**

  Run only the index validation/catalogue tests and the TypeScript check: `pnpm --filter ops-console test -- src/app/instruments/indices/new/validation.test.ts src/lib/index-catalogues.test.ts` and `pnpm --filter ops-console typecheck`. Do not run the full frontend suite unless explicitly requested.

---

### Task 5: End-to-end verification and documentation

**Files:**
- Modify: `ui/screen-specs/README.md` or create `ui/screen-specs/index-onboarding.md`
- Modify: `security-master-notes/16-database-implementation-plan.md`
- Modify: `security-master-notes/06-decision-log-and-open-questions.md`

- [ ] **Step 1: Document the UI workflow**

  Record that index creation is a proposal-first workflow, family creation is optional, return variants are separate index nodes, and constituents remain optional/deferred.

- [ ] **Step 2: Run the backend test slice**

  Run: `pytest tests/test_index_onboarding.py -q`.

- [ ] **Step 3: Run the focused frontend test/typecheck/build slice**

  Run the focused index tests, `pnpm --filter ops-console typecheck`, and `pnpm --filter ops-console build`. Do not run the full repository test suites unless explicitly requested.

- [ ] **Step 4: Verify the live endpoints**

  With the API and frontend running, verify `/health`, `/v1/currencies`, `/v1/return-profiles`, `/v1/organisations`, and `/instruments/indices/new` return successfully.
