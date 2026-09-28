# Tenant capabilities and operating profiles implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add composable tenant operating profiles and effective-dated module entitlements as the server-enforced capability source.

**Architecture:** `ten` owns a profile catalogue, tenant profile assignments, module catalogue, profile recommendations, and explicit tenant module entitlements. Profiles help onboarding; only effective granted module entitlements resolve API capability.

**Tech stack:** PostgreSQL, SQLAlchemy Core, Alembic, Python unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-tenant-capabilities-and-operating-profiles-design.md`

## Constraints

- Preserve tenant isolation, user authorisation, data entitlements, and rollout flags as separate concerns.
- Use UUIDv7 identifiers and comments on every table and column.
- Do not build a UI or feature-flag provider in this slice.
- Do not run the full test suite unless explicitly requested.

### Task 1: Add capability and profile metadata

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260911_42_tenant_capabilities_and_operating_profiles.py`
- Modify: `tests/test_schema_metadata.py`

- [x] Write a failing metadata test for `ten.operating_profile`, `ten.tenant_operating_profile_assignment`, `ten.platform_module`, `ten.operating_profile_module_recommendation`, and `ten.tenant_module_entitlement`.
- [x] Run the test and confirm it fails because the tables do not exist.
- [x] Add the five SQLAlchemy tables with foreign keys, effective dates, lifecycle controls, comments, and resolver indexes.
- [x] Add migration revision `20260911_42` with profile-assignment and entitlement exclusion constraints for overlapping active ranges.
- [x] Run the metadata test and confirm it passes.

### Task 2: Add deterministic capability resolution

**Files:**
- Modify: `security_master_schema/tenancy.py`
- Create: `tests/test_tenant_module_entitlements.py`

- [x] Write failing tests for effective grant selection, revoked/suspended exclusion, missing-module exclusion, and ambiguity rejection.
- [x] Run the tests and confirm imports fail before implementation.
- [x] Add immutable entitlement record and pure `resolve_effective_module_codes()` function.
- [x] Run the focused entitlement tests and confirm they pass.

### Task 3: Seed governed catalogues and demo tenant assignments

**Files:**
- Modify: `security_master_schema/seed_data.py`
- Modify: `security_master_schema/demo_data.py`
- Create: `tests/test_tenant_capability_database.py`

- [x] Write failing fixture lookup tests for multiple profiles and explicit modules.
- [x] Run the test and confirm fixture IDs and rows are absent.
- [x] Seed module and profile catalogues; load a demo tenant with `FUND_MANAGER` and `TRADING_BOOK_MANAGER` profiles plus explicit `FUND_MANAGEMENT`, `TRADING`, `VALUATION`, and `SECURITY_MASTER` grants.
- [x] Run the focused database and pure resolver tests.

### Task 4: Document the operating model

**Files:**
- Create: `docs/architecture/tenancy-and-entitlements/tenant-capabilities-and-operating-profiles.md`
- Modify: `docs/architecture/tenancy-and-entitlements/README.md`
- Modify: `docs/architecture/README.md`

- [x] Document the capability-resolution order, module catalogue, profile semantics, separation from user/data/release controls, source evidence, and deferred scope.
- [x] Link the design and plan and include the external research sources.

### Task 5: Focused verification

**Files:**
- No production edits.

- [x] Compile the schema package.
- [x] Run schema, entitlement, capability fixture, and offline-Alembic tests only.
- [x] Generate offline migration SQL and record the verification outcome in the architecture document.

## Local Docker reconciliation record

The local MVP database had been created from SQLAlchemy metadata before the relevant Alembic revisions existed. After inventorying the existing tables, columns, ordinary constraints and indexes, it was stamped at `20260911_42` and upgraded through the idempotent database-control reconciliation revision `20260911_43`. The resulting database is at Alembic head; its effective-date exclusion constraints and operational mapping target-validation trigger were verified by `tests/test_docker_bootstrap_reconciliation.py`.
