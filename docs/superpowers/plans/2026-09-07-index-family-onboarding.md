# Index Family Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate, auditable UI/API workflow for creating and approving conceptual index families, then make approved families selectable when creating concrete index variants.

**Architecture:** Reuse the existing `secm.financial_reference_node`, `secm.index_family`, `secm.reference_data_proposal`, and `secm.reference_data_approval` tables. Add family-specific contracts, repository operations, API/BFF routes, and a server-rendered Operations form. Keep family creation separate from concrete index creation; the index page remains a DB-backed selector.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy Core, PostgreSQL, Next.js App Router, React, MUI, Vitest, pytest.

**Spec:** Approved in-chat design on 2026-09-07: separate `/instruments/index-families/new` manual workflow, proposal/approval audit, optional provider organisation, no schema change, focused tests only.

## Global Constraints

- Manual submission is the default; no automatic approval is introduced.
- Family records are non-tradable conceptual reference nodes.
- The existing index form selects `indexFamilyId`; it must not create families inline.
- Tenant visibility and shared-canonical visibility use the existing `reference_node_scope` rules.
- Do not run the full unittest suite; run focused API/UI tests and typecheck only.

---

### Task 1: Add failing API contracts and repository tests

**Files:**
- Modify: `tests/test_index_onboarding.py`
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`

**Interfaces:**
- `IndexFamilyProposalRequest` accepts `canonicalName`, optional `internalCode`, optional `providerOrganisationId`, and `submissionMode` (`MANUAL` or `AUTOMATED`, default `MANUAL`).
- `IndexFamilyProposalView` returns `proposalId`, `status`, `proposalType`, `submissionMode`, `familyId`, `familyNodeId`, `familyName`, and `proposedAt`.
- `submit_index_family_proposal` records a pending `CREATE_INDEX_FAMILY` proposal.
- `decide_index_family_proposal` approves or rejects it and materializes the node/family on approval.

- [x] **Step 1: Write the failing API tests**

Add tests that submit a family and assert `201`, `PENDING`, `CREATE_INDEX_FAMILY`, and no family id; approve it and assert `APPROVED`, a family id, a non-tradable `INDEX_FAMILY` node, and visibility in `GET /v1/index-families`. Add a validation test for an unknown provider organisation.

- [x] **Step 2: Run the focused API tests to verify they fail**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Expected: FAIL because the family request/route/repository behavior does not yet exist.

- [x] **Step 3: Add the Pydantic contracts and minimal repository functions**

Add the request/view/response models and implement proposal insertion, visibility checks, provider validation, family-node materialization, approval audit insertion, and proposal status update using the existing transaction patterns.

- [x] **Step 4: Run the focused API tests to verify they pass**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Expected: all index onboarding tests pass, including the new family workflow tests.

### Task 2: Expose the family workflow through FastAPI and the Next BFF

**Files:**
- Modify: `apps/reference_api/main.py`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Create: `apps/ops-console/src/app/api/instruments/index-families/route.ts`

**Interfaces:**
- `POST /v1/index-family-proposals` creates a proposal.
- `POST /v1/index-family-proposals/{proposal_id}/decision` records `APPROVED` or `REJECTED`.
- Browser BFF `POST /api/instruments/index-families` forwards the request with trusted tenant/actor headers.

- [x] **Step 1: Add route tests to the focused API test**

Exercise both FastAPI endpoints through the existing `AsyncClient` helper and assert the response envelope and error status for invalid provider ids.

- [x] **Step 2: Run the route tests and verify the missing-route failures**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Expected: the new endpoint calls fail until the FastAPI routes are registered.

- [x] **Step 3: Implement FastAPI routes and typed frontend client functions**

Follow the existing index proposal error handling and response metadata. Add `submitIndexFamilyProposal` and `decideIndexFamilyProposal` client functions and a BFF route that uses `resolveLocalTenantContext()`.

- [x] **Step 4: Run focused API tests and TypeScript typecheck**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Run: `pnpm --filter ops-console typecheck`

Expected: both pass.

### Task 3: Build the server-rendered family creation page

**Files:**
- Create: `apps/ops-console/src/app/instruments/index-families/new/page.tsx`
- Create: `apps/ops-console/src/app/instruments/index-families/new/form.tsx`
- Create: `apps/ops-console/src/app/instruments/index-families/new/validation.ts`
- Create: `apps/ops-console/src/app/instruments/index-families/new/validation.test.ts`
- Modify: `apps/ops-console/src/lib/navigation.ts`

**Interfaces:**
- Page route: `/instruments/index-families/new`.
- Initial organisation options are loaded server-side from the live catalogue and passed to the client form.
- Form submits a manual proposal and displays the proposal id/status returned by the BFF.

- [x] **Step 1: Write validation tests first**

Test that canonical name is required and that a trimmed valid family name with optional internal code is accepted.

- [x] **Step 2: Run the UI validation test to verify it fails**

Run: `pnpm --filter ops-console test -- src/app/instruments/index-families/new/validation.test.ts`

Expected: FAIL because the validation module does not yet exist.

- [x] **Step 3: Implement validation, server page, and form**

Use the index form’s server-first catalogue pattern and explicit floated MUI labels. Include explanatory copy that a family is non-tradable conceptual lineage, provider organisation is optional, and concrete return variants are created separately. Keep submission mode fixed to `MANUAL` for this UI.

- [x] **Step 4: Add navigation and run the focused UI tests**

Add an `Add index family` action under Reference Data and run:

`pnpm --filter ops-console test -- src/app/instruments/index-families/new/validation.test.ts src/lib/index-catalogues.test.ts`

Expected: all focused UI tests pass.

### Task 4: Include index and family proposals in the work queue and document the workflow

**Files:**
- Modify: `apps/reference_api/repository.py`
- Modify: `ui/screen-specs/index-onboarding.md`
- Modify: `security-master-notes/06-decision-log-and-open-questions.md`

**Interfaces:**
- Pending `CREATE_INDEX` items appear as reference-data review items.
- Pending `CREATE_INDEX_FAMILY` items appear with a family-specific title/detail.

- [x] **Step 1: Add a failing work-queue assertion**

Submit one pending family and one pending concrete index, call `GET /v1/work-queue`, and assert both proposal ids are present under `REFERENCE_DATA_REVIEW`.

- [x] **Step 2: Run the focused API test to verify the queue failure**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Expected: the queue assertion fails because `CREATE_INDEX` and `CREATE_INDEX_FAMILY` are not currently classified.

- [x] **Step 3: Implement queue classification and update docs**

Add titles/details that distinguish family creation from concrete index creation without exposing raw payloads. Document the two-step workflow and the approval boundary.

- [x] **Step 4: Run focused verification**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_index_onboarding.py -q`

Run: `pnpm --filter ops-console test -- src/app/instruments/index-families/new/validation.test.ts src/lib/index-catalogues.test.ts`

Run: `pnpm --filter ops-console typecheck`

Expected: all commands pass. Do not run the full unittest suite.
