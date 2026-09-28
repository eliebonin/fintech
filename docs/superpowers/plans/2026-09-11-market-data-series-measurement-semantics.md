# Market-data series measurement semantics implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Govern the meaning and default change convention of each market-data series without changing immutable observations.

**Architecture:** A `md.series_measure_definition` catalogue is referenced by `md.market_data_series`. Seed data supplies standard financial-measure semantics; an additive migration backfills clear legacy mappings while preserving null for unknowns. Valuation/P&L policy remains out of scope.

**Tech Stack:** PostgreSQL, SQLAlchemy Core, Alembic, Python unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-market-data-series-measurement-semantics-design.md`

## Global Constraints

- Preserve the one immutable observation table.
- Use UUIDv7 identity and document every new table and column.
- Do not implement P&L attribution, valuation-policy overrides, API endpoints, or UI in this slice.
- Do not run the full test suite unless explicitly requested.

### Task 1: Governed series measurement metadata

**Files:**
- Modify: `tests/test_schema_metadata.py`
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260911_44_market_data_series_measurement_semantics.py`

- [x] Write a failing metadata test requiring `md.series_measure_definition`, its semantic fields, and `market_data_series.measure_definition_id`.
- [x] Run the test and confirm it fails because the table and FK do not exist.
- [x] Add the SQLAlchemy table, nullable additive FK, comments, lifecycle checks, and lookup index.
- [x] Add Alembic revision `20260911_44` to create the catalogue/FK and backfill deterministic legacy mappings.
- [x] Run the metadata test and confirm it passes.

### Task 2: Seed and fixture semantics

**Files:**
- Modify: `security_master_schema/seed_data.py`
- Modify: `security_master_schema/demo_data.py`
- Modify: `security_master_schema/mvp_demo_data.py`
- Create: `tests/test_market_data_measurement_semantics.py`

- [x] Write failing seed and fixture tests for price, FX rate, yield/rate, and implied-volatility change semantics.
- [x] Run tests and confirm they fail before the catalogue seeds and fixture links exist.
- [x] Seed the core measure definitions and link existing demo series by semantic code.
- [x] Run focused tests and confirm correct governed definitions resolve.

### Task 3: Documentation and focused verification

**Files:**
- Modify: `docs/architecture/market-data-and-valuation/README.md`
- Create: `docs/architecture/market-data-and-valuation/series-measurement-semantics.md`

- [x] Document series semantics, backfill rules, the distinction from raw observations and P&L methodology, and deferred scope.
- [x] Run schema metadata, seed/fixture, offline-Alembic, and focused resolver tests only.
- [x] Record verification results in the architecture document.

## Local Docker bootstrap reconciliation

Revision `20260911_44` is the normal clean-database migration. During the local metadata-bootstrap test path, `metadata.create_all()` had already created and seeded the new catalogue but could not add a new column to pre-existing `md.market_data_series`. The verified local database was stamped at `20260911_44` and upgraded through idempotent revision `20260911_45`, which added the column, FK, index and deterministic series backfill. This is documented in the architecture decision; it is not a production migration shortcut.
