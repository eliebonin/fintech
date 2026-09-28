# Automated Equity Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a policy-mediated, auditable workflow that can propose and (when a trusted policy allows) automatically approve a new equity instrument with one or more listings, identifiers, and source mappings.

**Architecture:** Reuse the existing `secm.reference_data_proposal` and `secm.reference_data_approval` workflow. Add a versioned `secm.reference_data_automation_policy` catalogue, record whether a proposal and decision were manual or automated, and materialise the full equity aggregate only after an approval decision. Manual UI submissions and automated source adapters use the same proposal service; callers cannot set canonical status directly.

**Tech Stack:** SQLAlchemy Core metadata, Alembic, FastAPI/Pydantic, Next.js App Router, TypeScript, Vitest, PostgreSQL UUIDv7 defaults.

**Spec:** Approved design in the conversation and the security-master notes on canonical proposals, source payload lineage, instrument/listing separation, and steward approval.

## Global Constraints

- Preserve immutable UUIDv7 identity and effective-dated versions.
- Keep provider/client identifiers as time-bound mappings, never primary identity.
- Store the equity instrument and its listings as one atomic approved aggregate.
- Automation is policy-bound approval, not an approval bypass.
- Reprocessing the same source object is idempotent.
- Do not auto-create from an ambiguous ticker-only match.
- Every new column has a SQLAlchemy and migration comment.

---

### Task 1: Add the automation-policy and proposal/approval metadata schema

**Files:**
- Modify: `security_master_schema/models.py` around `reference_data_proposal` and `reference_data_approval`
- Create: `alembic/versions/20260902_17_automated_reference_data_approval.py`
- Test: `tests/test_reference_data_automation.py`
- Modify: `tests/test_schema_metadata.py`
- Modify: `tests/test_migrations.py`

**Interfaces:**
- Produces `secm.reference_data_automation_policy`.
- Adds `submission_mode`, `source_system_id`, `automation_policy_id`, `idempotency_key`, `match_status`, `confidence_score`, and `payload_schema_version` to proposals.
- Adds `decision_method`, `automation_policy_id`, and `decision_evidence_json` to approvals.

- [x] **Step 1: Write failing metadata tests** asserting the policy table, new columns, foreign keys, checks, and indexes.
- [x] **Step 2: Run `pytest tests/test_reference_data_automation.py -q` and confirm it fails because the table/columns do not exist.**
- [x] **Step 3: Add the SQLAlchemy table and migration.** The policy is effective-dated and versioned; proposal idempotency is unique within source context; automated decisions reference a policy and authenticated account.
- [x] **Step 4: Run the focused metadata and migration tests and confirm they pass.**

### Task 2: Implement the equity proposal contract and approval/materialisation service

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Test: `tests/test_equity_onboarding.py`

**Interfaces:**
- `EquityListingProposal` contains `marketVenueId`, `tradingSymbol`, `tradingCurrencyId`, `quoteFactor`, `unitMultiplier`, `isPrimaryListing`, and `effectiveFrom`.
- `EquityProposalRequest` contains common equity data, optional ISIN/FIGI/SEDOL/CUSIP/CFI, one or more listings, source metadata, submission mode, and idempotency key.
- `submit_equity_proposal(connection, tenant_id, actor_id, request) -> EquityProposalView` creates a pending or auto-approved proposal.
- `decide_reference_data_proposal(connection, tenant_id, actor_id, proposal_id, decision, reason) -> EquityProposalView` records a manual decision and materialises approved equity aggregates.

- [x] **Step 1: Write repository/API tests for manual pending, trusted automated approval, duplicate idempotency, and manual approval materialisation.**
- [x] **Step 2: Run the focused tests while the contract/service was absent and use the failures as the implementation contract.**
- [x] **Step 3: Implement exact-match validation (ISIN, venue+symbol), policy lookup, confidence/required-identifier checks, and atomic creation of `financial_reference_node`, `instrument`, `instrument_definition_version`, `listing`, `listing_definition_version`, and instrument identifiers on approval.**
- [x] **Step 4: Record automated approval evidence and create source external mappings when supplied; use source namespace and valid dates for the mapping.**
- [x] **Step 5: Run focused repository/API tests and confirm all paths pass.**

### Task 3: Expose the API endpoints and policy-safe decision flow

**Files:**
- Modify: `apps/reference_api/main.py`
- Modify: `apps/reference_api/contracts.py`
- Test: `tests/test_equity_onboarding_api.py`

**Interfaces:**
- `POST /v1/equity-proposals` accepts `EquityProposalRequest` and returns `EquityProposalResponse` with proposal status, decision method, and created instrument/listing IDs when approved.
- `POST /v1/reference-data-proposals/{proposal_id}/decision` accepts only `APPROVED` or `REJECTED`; approval writes the canonical aggregate through the repository service.

- [x] **Step 1: Add FastAPI coverage for manual submission, automated submission, duplicate idempotency, and approval in `tests/test_equity_onboarding.py`.**
- [x] **Step 2: Exercise the route contract against the running PostgreSQL demo database.**
- [x] **Step 3: Add routes with tenant membership and actor checks; callers cannot force `APPROVED` and unknown policies are rejected.**
- [x] **Step 4: Run the API tests and the existing reference API suite.**

### Task 4: Add the minimal equity onboarding UI

**Files:**
- Create: `apps/ops-console/src/app/instruments/new/page.tsx`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Modify: `apps/ops-console/src/components/operations-console.tsx`
- Test: `apps/ops-console/src/lib/equity-onboarding.test.ts`

**Interfaces:**
- `submitEquityProposal(context, request)` posts to the BFF/reference API and returns the typed proposal response.
- `/instruments/new` captures common equity fields and one listing, displays `AUTO-APPROVED` versus `PENDING_REVIEW`, and shows created UUIDs/evidence summary.
- The existing Instruments navigation entry links to `/instruments/new` without changing other placeholder navigation items.

- [x] **Step 1: Add the typed request client contract used by the form.**
- [x] **Step 2: Implement the BFF route and form with explicit automated/manual paths.**
- [x] **Step 3: Implement the typed API client and accessible form with an explicit “automated source” toggle.**
- [x] **Step 4: Run frontend typecheck and production build.**

### Task 5: Document operations, automation policy, and deferred breadth

**Files:**
- Create: `security-master-notes/23-automated-reference-data-onboarding.md`
- Modify: `security-master-notes/06-decision-log-and-open-questions.md`
- Modify: `security-master-notes/16-database-implementation-plan.md`
- Modify: `security-master-notes/README.md`

- [x] **Step 1: Document lifecycle states, policy governance, source trust tiers, idempotency, and examples for equity creation.**
- [x] **Step 2: Record deferred decisions for bulk adapters, classification assignment, and complex instrument aggregate materialisation.**
- [x] **Step 3: Review the documentation against the implemented fields and endpoints.**

### Task 6: Run the complete verification suite

**Files:**
- Test: `tests/` and `apps/ops-console/src/**/*.test.ts`

- [ ] **Step 1: Run the complete Python suite in a process with a timeout longer than the local seed-loader duration.**
- [ ] **Step 2: Run frontend tests: `npm test` from `apps/ops-console`.**
- [x] **Step 3: Run `npm run typecheck` and `npm run build` from `apps/ops-console`.**
- [x] **Step 4: Apply the migration to the running PostgreSQL instance and verify `alembic current` reports `20260902_17`.**
- [x] **Step 5: Exercise the manual and automated equity proposal endpoints against the demo tenant and verify proposal/approval/canonical rows are consistent.**
