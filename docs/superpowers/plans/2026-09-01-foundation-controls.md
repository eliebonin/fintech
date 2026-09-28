# Security Master Foundation Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement and document the six foundation controls required for a central canonical database plus isolated tenant overlay databases.

**Architecture:** The central core owns canonical reference data and shared licensed market-data facts. Each tenant overlay owns private instruments, mappings, trades, positions, NAV, marks and ingestion evidence; cross-database references use immutable UUIDs validated through a canonical service. All corrections and valuation decisions are append-only and reproducible.

**Tech Stack:** PostgreSQL 18, SQLAlchemy Core, Alembic, Python 3.12, pytest, UUIDv7.

**Spec:** `security-master-notes/19-tenant-database-topology-and-priorities.md` and `security-master-notes/18-critical-review-and-delivery-choices.md`.

**Implementation status:** Tasks 1–6 are implemented additively in the model,
pure validation modules, tests, and Alembic revisions `20260901_06` through
`20260901_11`. Task 7 documentation is updated. Live PostgreSQL migration
verification remains environment-blocked while the local Docker endpoint is
unreachable; RLS, provisioning, backfill, and typed override enforcement remain
explicit follow-on work.

## Global Constraints

- PostgreSQL schema evolution is migration-only; do not use `metadata.create_all` in production/bootstrap paths.
- Fortem-generated UUIDv7 values are immutable identity; provider, client, custodian and bank identifiers are mappings.
- Raw market-data observations, original trades and historical snapshots are never overwritten.
- Tenant overlays never mutate canonical facts and private terms are not promoted without approval.
- Every valuation price and FX input is selected under an explicit policy, entitlement, named cut and information cutoff.

---

### Task 1: Tenant registry and database routing contract

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/tenant_routing.py`
- Create: `tests/test_tenant_routing.py`
- Create: `alembic/versions/20260901_06_tenant_database_registry.py`
- Create: `security-master-notes/20-tenant-routing-and-core-api-contract.md`

**Deliverable:** A central tenant registry and deterministic routing result that never accepts a client-supplied database endpoint.

### Task 2: True canonical instrument/listing version history

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/reference_versioning.py`
- Create: `tests/test_reference_versioning.py`
- Create: `alembic/versions/20260901_07_reference_definition_versions.py`
- Modify: `security-master-notes/02-reference-identity-model.md`

**Deliverable:** Immutable node identity plus effective-dated, sequenced instrument and listing definitions with one current version per object.

### Task 3: Cross-database canonical UUID links

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/canonical_links.py`
- Create: `tests/test_canonical_links.py`
- Create: `alembic/versions/20260901_08_canonical_reference_links.py`
- Modify: `security-master-notes/19-tenant-database-topology-and-priorities.md`

**Deliverable:** Tenant-local link evidence and a validation contract for central UUID/object type/status without pretending a cross-database FK exists.

### Task 4: Append-only trade correction lifecycle

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/trade_lifecycle.py`
- Create: `tests/test_trade_lifecycle.py`
- Create: `alembic/versions/20260901_09_trade_lifecycle_events.py`
- Modify: `security-master-notes/03-market-data-marks-and-trades.md`

**Deliverable:** Booked trade remains immutable; amendments, cancellations, supersessions and source idempotency are recorded as events.

### Task 5: Generic valuation marks

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/valuation_marks.py`
- Create: `tests/test_valuation_marks.py`
- Create: `alembic/versions/20260901_10_valuation_marks.py`
- Modify: `security-master-notes/03-market-data-marks-and-trades.md`

**Deliverable:** A reusable mark record linked to price/FX/accrual input snapshots, policy and calculation versions, distinct from raw observations and NAV output.

### Task 6: Market-data source vintages and publication semantics

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/market_data_vintages.py`
- Create: `tests/test_market_data_vintages.py`
- Create: `alembic/versions/20260901_11_market_data_vintages.py`
- Modify: `security-master-notes/09-indices-fx-forwards-and-market-data-architecture.md`
- Modify: `security-master-notes/10-corporate-actions-and-adjusted-market-data.md`

**Deliverable:** Explicit source-vintage identity and point-in-time eligibility, distinguishing current vendor-restated history from data knowable at a historic cut.

### Task 7: Integrated verification and documentation review

**Files:**
- Modify: `security-master-notes/16-database-implementation-plan.md`
- Modify: `security-master-notes/18-critical-review-and-delivery-choices.md`
- Modify: `security-master-notes/README.md`
- Modify: `data/mockup/README.md`

**Deliverable:** Fresh migration upgrade/downgrade, full tests, fixture compatibility and a final deferred-decision register.
