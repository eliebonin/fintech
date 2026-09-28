# Security Master Schema Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the small set of database and API integrity gaps exposed by the UI MVP without redesigning the security master.

**Architecture:** Keep the existing canonical-node/instrument/listing model, immutable observations, tenant overlays, and append-only workflows. Add narrowly scoped constraints and metadata: tenant membership and mapping ownership, explicit market-data dimensions, observation idempotency, effective-version read support, and audit links for trade/NAV/cash data. Larger field-level override and full tenant-database routing remain deferred.

**Tech Stack:** PostgreSQL 18, SQLAlchemy Core metadata, Alembic, FastAPI, pytest.

**Spec:** `docs/architecture/schema-hardening.md`

## Global Constraints

- Preserve existing UUIDv7 identities and all existing table names.
- Do not rewrite the canonical instrument/listing hierarchy.
- Do not expose raw provider data without an entitlement decision.
- Preserve legacy rows during migration; new constraints must be data-safe and idempotent.
- Every new column and table column must have a database comment.

---

### Task 1: Document the hardening scope and deferred decisions

**Files:**
- Create: `docs/architecture/schema-hardening.md`
- Modify: `security-master-notes/README.md` (if present) with a link to the hardening note.

**Deliverable:** A concise record of observed weaknesses, implemented fixes, and explicit deferred work.

- [x] Completed.

### Task 2: Add model metadata and migration changes

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260901_12_schema_hardening.py`

**Changes:**
- Add tenant membership table and tenant ownership to external mappings.
- Add a small `market_data_series_dimension` table for tenor/strike/delta/quote-side/session dimensions.
- Preserve legacy source-system code compatibility while adding observation idempotency metadata.
- Add `locked_ytm` to trades and an input-item link from NAV valuation lines.
- Add uniqueness/check constraints and indexes without rewriting existing data.
- Add database trigger/check support for one current approved definition and valid effective ranges where safe.

- [x] Completed.

### Task 3: Harden API reads and mapping writes

**Files:**
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/tenant_context.py`
- Modify: `apps/reference_api/contracts.py` only if response metadata needs new fields.

**Changes:**
- Require active tenant membership for API calls.
- Filter identifiers, mappings, and versions by effective date/status.
- Apply dataset entitlements to market-data evidence.
- Keep tenant-owned mappings tenant-visible only.
- Resolve approved current definition versions deterministically.

- [x] Completed.

### Task 4: Add regression tests first and verify

**Files:**
- Create: `tests/test_schema_hardening.py`
- Modify: `tests/test_reference_api_read.py`
- Modify: `tests/test_reference_mapping_workflow.py`
- Modify: `tests/test_migrations.py` only if migration setup needs coverage.

**Verification:** Run focused tests, full Python tests, Alembic upgrade/downgrade, frontend tests/typecheck/build, and live API smoke tests.

- [x] Completed: 67 Python tests, frontend tests/typecheck/build, migration upgrade/downgrade, and live API smoke checks.
