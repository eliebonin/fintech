# Tenant Fund Operational Mappings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tenant-scoped, effective-dated mapping profiles and mappings that resolve administrator/custodian fund and share-class IDs reproducibly.

**Architecture:** Add a `cfg` schema for tenant operational configuration. `cfg.external_data_mapping_profile` defines one provider feed and interpretation context; `cfg.external_data_object_mapping` is an approved mapping from that feed's identifier to a canonical fund or share-class object. A small resolver service selects an approved mapping for the report business date and rejects ambiguity.

**Tech Stack:** PostgreSQL, SQLAlchemy Core, Alembic, Python `unittest`/`pytest` compatibility.

**Spec:** `docs/superpowers/specs/2026-09-11-tenant-fund-operational-mappings-design.md`

## Global Constraints

- Use UUIDv7 primary keys and comments on every table and column.
- Preserve raw external IDs; normalisation is controlled per profile.
- Shared identifier mappings remain in `ing.external_object_mapping`; this slice is tenant operational configuration.
- Only approved, effective mappings resolve production input.
- Do not run the entire test suite unless explicitly requested; run focused tests only.
- Do not build the Fund Management Config UI in this slice.

---

### Task 1: Define metadata and migration for tenant operational mapping tables

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260911_41_tenant_fund_operational_mappings.py`
- Modify: `tests/test_schema_metadata.py`

**Interfaces:**
- Produces `cfg.external_data_mapping_profile` and `cfg.external_data_object_mapping` SQLAlchemy tables.
- Consumes `ten.tenant`, `secm.organisation`, `ing.integration_source_system`, `md.dataset`, `ing.source_payload`, `secm.fund`, and `secm.instrument`.

- [x] **Step 1: Write the failing metadata tests**

```python
def test_tenant_operational_mapping_tables_are_available(self) -> None:
    profile = metadata.tables["cfg.external_data_mapping_profile"]
    mapping = metadata.tables["cfg.external_data_object_mapping"]

    self.assertIn("tenant_id", profile.c)
    self.assertIn("integration_source_system_id", profile.c)
    self.assertIn("normalization_mode", profile.c)
    self.assertIn("source_object_scope", mapping.c)
    self.assertIn("external_id_raw", mapping.c)
    self.assertIn("external_id_normalized", mapping.c)
```

- [x] **Step 2: Run the metadata test and verify it fails because the `cfg` tables do not exist**

Run: `python -m unittest tests.test_schema_metadata.SchemaMetadataTests.test_tenant_operational_mapping_tables_are_available -v`

- [x] **Step 3: Add the SQLAlchemy Core tables**

Implement `cfg.external_data_mapping_profile` with tenant, provider organisation,
integration source system, optional dataset, profile code, display name,
operational context, allowed source scope, normalisation mode, parser contract
version, status, business validity and timestamps. Implement
`cfg.external_data_object_mapping` with profile, source scope, polymorphic
canonical target, raw and normalised IDs, role/method/status, approval evidence,
business validity, recorded timestamp, payload evidence and supersession.

Add `CheckConstraint`s for V1 controlled values and lookup indexes:

```python
Index(
    "ix_cfg_external_data_object_mapping_resolve",
    external_data_object_mapping.c.mapping_profile_id,
    external_data_object_mapping.c.source_object_scope,
    external_data_object_mapping.c.external_id_normalized,
    external_data_object_mapping.c.valid_from,
    external_data_object_mapping.c.valid_to,
)
```

- [x] **Step 4: Add the migration**

Create the `cfg` schema if needed. Create the two tables, constraints and
indexes. Add a PostgreSQL exclusion constraint over tenant, profile, source
scope, normalised ID and `daterange(valid_from, coalesce(valid_to, 'infinity'))`
for `APPROVED` records. Add target-validation trigger logic that accepts only
`FUND` target IDs in `secm.fund` and `FUND_SHARE_CLASS` target IDs in
`secm.instrument`.

- [x] **Step 5: Run the metadata test and verify it passes**

Run: `python -m unittest tests.test_schema_metadata.SchemaMetadataTests.test_tenant_operational_mapping_tables_are_available -v`

### Task 2: Implement profile-aware, effective-dated resolution

**Files:**
- Modify: `security_master_schema/tenancy.py`
- Create: `tests/test_tenant_operational_mapping_resolution.py`

**Interfaces:**
- Produces `normalize_external_id(value: str, mode: str) -> str`.
- Produces `select_effective_operational_mapping(records, as_of_date) -> OperationalMappingRecord | None`.
- Raises `AmbiguousMappingError` when more than one approved record applies.

- [x] **Step 1: Write failing resolver tests**

```python
def test_case_insensitive_profile_normalises_only_outer_whitespace() -> None:
    assert normalize_external_id("  nav-i-gbp  ", "TRIM_UPPER") == "NAV-I-GBP"


def test_effective_operational_mapping_requires_approved_status() -> None:
    record = OperationalMappingRecord(
        mapping_id=UUID("00000000-0000-7000-8000-000000000801"),
        valid_from=date(2026, 1, 1), valid_to=None, status="PROPOSED",
    )
    assert select_effective_operational_mapping((record,), date(2026, 6, 1)) is None
```

- [x] **Step 2: Run the focused tests and verify they fail because the functions and record type do not exist**

Run: `pytest tests/test_tenant_operational_mapping_resolution.py -v`

- [x] **Step 3: Implement the minimal pure resolver**

Add immutable `OperationalMappingRecord`, conservative normalisation modes
`EXACT` and `TRIM_UPPER`, and selection that accepts `APPROVED` mappings within
their inclusive business period. Reuse `AmbiguousMappingError` for collisions.

- [x] **Step 4: Run the focused tests and verify they pass**

Run: `pytest tests/test_tenant_operational_mapping_resolution.py -v`

### Task 3: Add deterministic operational fixtures and database lookup coverage

**Files:**
- Modify: `security_master_schema/demo_data.py`
- Create: `tests/test_tenant_operational_mapping_database.py`

**Interfaces:**
- Produces deterministic fixture IDs for an administrator profile and fund/share-class mappings.
- Proves that the database records can be resolved by profile, normalised ID, and report date.

- [x] **Step 1: Write a failing database fixture test**

```python
def test_demo_administrator_profile_resolves_fund_and_share_class_records() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        assert connection.scalar(select(profile.c.profile_code).where(
            profile.c.external_data_mapping_profile_id == DEMO_IDS["abc_daily_valuation_profile"]
        )) == "ABC_DAILY_VALUATION"
```

- [x] **Step 2: Run it and verify it fails because the fixtures do not exist**

Run: `pytest tests/test_tenant_operational_mapping_database.py -v`

- [x] **Step 3: Add minimal fixtures**

Seed one tenant-owned ABC operational source system/profile for daily valuation
and one for daily accounting. Add a fund-level accounting ID and a share-class
valuation ID referencing existing canonical fixture objects. Do not add real
counterparty data or make the records available cross-tenant.

- [x] **Step 4: Run fixture and resolver tests**

Run: `pytest tests/test_tenant_operational_mapping_database.py tests/test_tenant_operational_mapping_resolution.py -v`

### Task 4: Integrate the documentation information architecture

**Files:**
- Create: `docs/architecture/trading-and-operations/tenant-fund-operational-mappings.md`
- Modify: `docs/architecture/trading-and-operations/README.md`
- Modify: `docs/architecture/integrations-and-data-rights/README.md`
- Modify: `docs/architecture/security-master/README.md`

**Interfaces:**
- Produces canonical documentation for data ownership, resolution semantics, controls and deferred work.

- [x] **Step 1: Document the completed implementation**

Record the canonical-vs-tenant boundary, table responsibilities, approved
status and exclusion semantics, raw/normalised identifier policy, resolver
inputs, provenance retention, supported targets, UI direction, and deferred
operating-account scope. Link to the design and implementation plan.

- [x] **Step 2: Verify documentation links and no stale schema claim remains**

Run: `rg -n "external_data_mapping_profile|external_data_object_mapping|OPERATING_ACCOUNT" docs security-master-notes`

### Task 5: Perform focused verification

**Files:**
- No production changes.

- [x] **Step 1: Compile schema modules**

Run: `python -m compileall security_master_schema`

- [x] **Step 2: Run the relevant unit tests only**

Run: `python -m unittest tests.test_schema_metadata -v; pytest tests/test_external_mapping_rules.py tests/test_tenant_operational_mapping_resolution.py tests/test_tenant_operational_mapping_database.py -v`

- [x] **Step 3: Inspect the migration upgrade SQL without applying it**

Run: `alembic upgrade head --sql`

- [x] **Step 4: Record verification results in the architecture document**

Add exact commands and their pass/fail outcome; do not claim database migration
application unless it was actually run against the local Docker database.

## Plan self-review

- Spec coverage: Tasks 1–3 implement the data model, controls, resolver and
  reproducibility. Task 4 records decisions and deferrals. Task 5 provides
  proportionate verification.
- No placeholders: every table, test target, behaviour and command is named.
- Type consistency: `OperationalMappingRecord` and `AmbiguousMappingError` are
  defined before the database fixture task depends on their semantics.
