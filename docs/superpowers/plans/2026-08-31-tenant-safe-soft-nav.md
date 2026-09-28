# Tenant-Safe Soft-NAV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one tenant-safe, reproducible Soft-NAV workflow built on controlled schema changes, canonical identity mapping, entitled market-data resolution, fund terms, and audited calculation inputs.

**Architecture:** Preserve the canonical `secm` master and immutable market-data observations. Add a versioned deployment boundary, then build a resolver service that selects observations under tenant, entitlement, valuation-policy, and historic-cut context. Soft-NAV runs freeze the selected inputs; they do not mutate observations or produce official administrator NAV.

**Tech Stack:** PostgreSQL 18, SQLAlchemy Core, psycopg 3, pytest, Alembic, Docker Compose.

**Spec:** `security-master-notes/18-critical-review-and-delivery-choices.md`

## Global Constraints

* PostgreSQL version is 18 or later because model defaults use native `uuidv7()`.
* Every new database column has a comment and every deployed schema change is an Alembic revision.
* No real client, counterparty, vendor, or licensed market data is committed to fixtures.
* UUIDs are identifiers only; tenant access is enforced by application context and tested database controls.
* Market-data observations are immutable. Corrections create successor observations and new resolver/NAV snapshots.
* The resolver must exclude observations received after `market_data_as_of_utc`.
* Soft NAV remains indicative and separately status-controlled from administrator NAV.

---

### Task 1: Establish controlled schema deployment

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/20260831_01_baseline_schema.py`
- Create: `tests/test_migrations.py`
- Modify: `requirements.txt`
- Modify: `scripts/create_schema.py`
- Modify: `security-master-notes/16-database-implementation-plan.md`

**Interfaces:**
- Produces `alembic upgrade head` as the only supported deployed-schema creation command.
- Produces `alembic downgrade base` for a disposable database only.
- `scripts/create_schema.py` delegates to the migration command rather than `metadata.create_all`.

- [ ] **Step 1: Write the failing migration round-trip test**

```python
def test_upgrade_head_creates_every_sqlalchemy_table(postgres_database_url):
    run_alembic("upgrade", "head", postgres_database_url)
    assert database_table_names(postgres_database_url) >= set(metadata.tables)

def test_downgrade_base_removes_security_master_schemas(postgres_database_url):
    run_alembic("upgrade", "head", postgres_database_url)
    run_alembic("downgrade", "base", postgres_database_url)
    assert not database_schema_exists(postgres_database_url, "secm")
```

- [ ] **Step 2: Run the migration test and verify failure**

Run: `pytest tests/test_migrations.py -v`

Expected: failure because Alembic configuration and revision chain do not exist.

- [ ] **Step 3: Add Alembic dependency and configuration**

```text
alembic>=1.14,<2.0
```

`alembic/env.py` imports `security_master_schema.models.metadata`, reads `DATABASE_URL`, and sets `target_metadata = metadata`. The baseline revision creates schemas in this order: `secm`, `ten`, `ing`, `md`, `trd`, `nav`; then creates metadata tables and indexes.

- [ ] **Step 4: Make the baseline revision reversible for disposable environments**

```python
def downgrade() -> None:
    for schema in ("nav", "trd", "md", "ing", "ten", "secm"):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
```

- [ ] **Step 5: Update bootstrap documentation and script**

`scripts/create_schema.py` invokes Alembic programmatically with `upgrade head`. `security-master-notes/16-database-implementation-plan.md` states that direct manual `ALTER TABLE` is not a deployment method.

- [ ] **Step 6: Run migration, existing schema, and full test suites**

Run: `pytest tests/test_migrations.py tests/test_schema_metadata.py -v` and `pytest -q`

Expected: all tests pass against a blank temporary PostgreSQL database.

- [ ] **Step 7: Commit**

```bash
git add alembic.ini alembic requirements.txt scripts/create_schema.py tests/test_migrations.py security-master-notes/16-database-implementation-plan.md
git commit -m "feat: add versioned security master schema migrations"
```

### Task 2: Make tenant ownership and mapping validity enforceable

**Files:**
- Create: `security_master_schema/tenancy.py`
- Create: `tests/test_tenancy.py`
- Create: `tests/test_external_mapping_rules.py`
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260831_02_tenant_scope_and_mapping_constraints.py`
- Modify: `security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md`

**Interfaces:**
- Produces `assert_tenant_owns_strategy(connection, tenant_id, strategy_id) -> None`.
- Produces `resolve_external_mapping(connection, namespace_id, object_type, external_id, as_of_date, venue_id=None) -> UUID`.
- Raises `TenantScopeError`, `MappingNotFoundError`, or `AmbiguousMappingError` rather than guessing.

- [ ] **Step 1: Write failing tenancy and mapping tests**

```python
def test_strategy_cannot_be_used_by_another_tenant(connection):
    with pytest.raises(TenantScopeError):
        assert_tenant_owns_strategy(connection, tenant_b_id, tenant_a_strategy_id)

def test_overlapping_verified_external_mappings_are_rejected(connection):
    insert_verified_mapping(connection, valid_from=date(2026, 1, 1))
    with pytest.raises(IntegrityError):
        insert_verified_mapping(connection, valid_from=date(2026, 6, 1))
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_tenancy.py tests/test_external_mapping_rules.py -v`

Expected: failure because strategies are not tenant-owned and mapping periods may overlap.

- [ ] **Step 3: Add tenant ownership and mapping constraints**

Add `tenant_id` to `trd.strategy`, with a foreign key to `ten.tenant`. Add an exclusion constraint over namespace, object type, external ID, venue context, and `daterange(valid_from, coalesce(valid_to, 'infinity'))` for active/verified mappings. Add a PostgreSQL trigger that validates `target_object_type` against the supported target table set.

- [ ] **Step 4: Implement the query-boundary helpers**

```python
class TenantScopeError(PermissionError):
    pass

def assert_tenant_owns_strategy(connection, tenant_id: UUID, strategy_id: UUID) -> None:
    exists = connection.scalar(select(strategy.c.strategy_id).where(
        strategy.c.strategy_id == strategy_id,
        strategy.c.tenant_id == tenant_id,
    ))
    if exists is None:
        raise TenantScopeError("Strategy is outside tenant scope")
```

- [ ] **Step 5: Run focused and full tests**

Run: `pytest tests/test_tenancy.py tests/test_external_mapping_rules.py -v` and `pytest -q`

Expected: all tests pass, including historic effective-date resolution.

- [ ] **Step 6: Commit**

```bash
git add security_master_schema alembic tests security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md
git commit -m "feat: enforce tenant strategy scope and external mapping validity"
```

### Task 3: Build the database-backed entitled resolver

**Files:**
- Create: `security_master_schema/market_data_resolver.py`
- Create: `tests/test_market_data_resolver.py`
- Modify: `security_master_schema/valuation_resolver.py`
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260831_03_market_data_resolution_constraints.py`
- Modify: `security-master-notes/17-soft-nav-pricing-date-resolution.md`

**Interfaces:**
- Produces `resolve_market_data(connection, request: ResolutionRequest) -> ResolvedMarketData`.
- `ResolutionRequest` contains tenant UUID, subject-node UUID, valuation-policy UUID, valuation date, valuation-cut UUID, information-cut timestamp, and use purpose.
- `ResolvedMarketData` contains selected observation UUID or an explicit status, pricing dates, staleness, policy rule UUID, entitlement decision, and selection reason.

- [ ] **Step 1: Write failing precedence and entitlement tests**

```python
def test_exact_series_rule_beats_node_type_rule(connection):
    result = resolve_market_data(connection, request_for_subject)
    assert result.policy_rule_id == exact_series_rule_id

def test_observation_outside_tenant_entitlement_is_not_selected(connection):
    result = resolve_market_data(connection, request_for_subject)
    assert result.status == "MISSING"
    assert result.exception_code == "NO_ENTITLED_OBSERVATION"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_market_data_resolver.py -v`

Expected: failure because no database resolver exists.

- [ ] **Step 3: Implement fixed rule precedence and candidate query**

Candidate eligibility requires matching subject/series semantics, active tenant dataset entitlement for use purpose and as-of date, `received_at_utc <= market_data_as_of_utc`, accepted quality status, and no superseded status. Rules are ordered by exact series, exact node, instrument type, then sequence-number default.

- [ ] **Step 4: Persist resolution evidence atomically**

```python
def persist_resolution_snapshot(connection, header: ResolutionRequest, items: Sequence[ResolvedMarketData]) -> UUID:
    """Insert immutable header and item rows in the caller transaction."""
```

The item records requested/used dates, staleness, selected observation, dataset, policy rule, entitlement decision, and exception code.

- [ ] **Step 5: Add calendar adapter and data validation**

`BusinessCalendar` exposes `subtract_business_days(date, count)` and `business_day_distance(start, end)`. `WeekdayCalendar` remains test-only/default. Production resolver requires a registered `market_calendar_id`; reject a `FIXED_LAG` rule without a resolved calendar.

- [ ] **Step 6: Run focused and full tests**

Run: `pytest tests/test_valuation_resolver.py tests/test_market_data_resolver.py -v` and `pytest -q`

Expected: all resolver selections, stale results, and information-cut exclusions are deterministic.

- [ ] **Step 7: Commit**

```bash
git add security_master_schema alembic tests security-master-notes/17-soft-nav-pricing-date-resolution.md
git commit -m "feat: resolve entitled market data under frozen valuation policy"
```

### Task 4: Add fund/share-class and bond daily-valuation terms

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `security_master_schema/fund_terms.py`
- Create: `tests/test_fund_terms.py`
- Create: `tests/test_bond_terms.py`
- Create: `alembic/versions/20260831_04_fund_and_bond_terms.py`
- Modify: `security_master_schema/demo_data.py`
- Create: `data/mockup/fund-t1-soft-nav.json`
- Modify: `data/mockup/README.md`
- Modify: `security-master-notes/03-market-data-marks-and-trades.md`

**Interfaces:**
- Produces `secm.fund`, `secm.fund_share_class`, `secm.fund_nav_terms`, and `secm.bond_terms`.
- A fund share class references one fund; NAV publication terms reference the share class.
- Bond terms expose coupon rate, frequency, day-count, redemption value, denomination, and accrual convention.

- [x] **Implemented (2026-09-01):** `secm.fund`, versioned
  `secm.fund_share_class_terms`, and versioned `secm.bond_terms` were added in
  migration `20260901_05`. The synthetic fund-share-class scenario includes an
  entitled T-1 official NAV selected by `FIXED_LAG`.

```python
def test_share_class_has_one_parent_fund_and_nav_publication_terms(connection):
    assert resolve_market_data(connection, t1_fund_request).pricing_date_used == date(2026, 8, 31)

def test_bond_accrual_terms_require_day_count_and_coupon_frequency():
    assert {"day_count_convention", "coupon_frequency", "coupon_rate"} <= set(bond_terms.c)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_fund_terms.py tests/test_bond_terms.py -v`

Expected: failure because specialised fund and bond terms do not exist.

- [ ] **Step 3: Add focused normalised terms tables and constraints**

`fund` holds legal/umbrella management context; `fund_share_class` holds the tradeable economic share class; `fund_nav_terms` holds NAV currency, valuation frequency, dealing frequency, publication lag, and official-NAV series. `bond_terms` references an economic bond instrument and contains the daily-valuation terms above.

- [ ] **Step 4: Add fully fictional fund T-1 fixture**

The fixture includes a fund, share class, T-1 official NAV observation with market date and publication/receipt time, entitled policy rule, position snapshot, resolver snapshot, and expected Soft-NAV line. It uses fictional provider, manager, and issuer names.

- [ ] **Step 5: Run focused and full tests**

Run: `pytest tests/test_fund_terms.py tests/test_bond_terms.py tests/test_market_data_resolver.py -v` and `pytest -q`

Expected: fund share-class T-1 price selection and bond-term validation pass.

- [ ] **Step 6: Commit**

```bash
git add security_master_schema alembic tests data/mockup security-master-notes/03-market-data-marks-and-trades.md
git commit -m "feat: add fund share-class and bond valuation terms"
```

### Task 5: Complete indicative Soft-NAV calculation and reconciliation

**Progress (2026-09-01):** V1 calculation orchestration is implemented for an
already-ingested, single-reporting-currency position snapshot. It freezes
resolver evidence and applies listing quote factor/unit multiplier. Cash, FX,
accruals, administrator reconciliation and authorised override workflow remain
pending; they are deliberately rejected rather than guessed.

**Files:**
- Create: `security_master_schema/soft_nav_service.py`
- Create: `tests/test_soft_nav_service.py`
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260831_05_soft_nav_calculation_controls.py`
- Modify: `security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md`

**Interfaces:**
- Produces `calculate_soft_nav(connection, request: SoftNavRequest) -> UUID`.
- `SoftNavRequest` contains tenant, strategy, valuation policy, valuation date/cut, information cut, reporting currency, and calculation version.
- Produces immutable NAV run, resolver snapshot, frozen inputs, valuation lines, result, and reconciliation rows.

- [ ] **Step 1: Write failing end-to-end calculation test**

```python
def test_soft_nav_freezes_t1_fund_bond_cash_and_fx_inputs(connection):
    run_id = calculate_soft_nav(connection, fictional_fund_request)
    assert nav_result_value(connection, run_id) == Decimal("1012345.67")
    assert frozen_input_count(connection, run_id) == 4
    assert no_input_received_after_cut(connection, run_id)
```

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/test_soft_nav_service.py::test_soft_nav_freezes_t1_fund_bond_cash_and_fx_inputs -v`

Expected: failure because the calculation service does not exist.

- [ ] **Step 3: Implement calculation orchestration**

The service validates tenant strategy ownership, loads a full position/cash snapshot, calls the resolver per priced subject, calculates local and reporting values, writes one frozen input per selected value, and writes explicit exception lines for stale/missing inputs. It refuses `FAIL` outcomes and leaves an approved override decision to a separately authorised caller.

- [ ] **Step 4: Add controls and reconciliation**

Add non-null source/reference fields required for approved overrides; record administrator NAV source, tolerance, break amount, and review status. Add calculation checks for duplicate valuation-line subjects and missing reporting-currency FX inputs.

- [ ] **Step 5: Run full calculation and regression tests**

Run: `pytest tests/test_soft_nav_service.py -v` and `pytest -q`

Expected: deterministic output, frozen lineage, stale/missing rejection, and administrator break behaviour pass.

- [ ] **Step 6: Commit**

```bash
git add security_master_schema alembic tests security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md
git commit -m "feat: calculate tenant-scoped indicative soft nav"
```

### Task 6: Apply corporate actions with historic information control

**Files:**
- Create: `security_master_schema/corporate_action_service.py`
- Create: `tests/test_corporate_action_service.py`
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260831_06_corporate_action_application.py`
- Modify: `security-master-notes/10-corporate-actions-and-adjusted-market-data.md`
- Modify: `security-master-notes/16-database-implementation-plan.md`

**Interfaces:**
- Produces `derive_adjusted_position(connection, position_line_id, information_cutoff_utc) -> DerivedPosition`.
- Produces `derive_adjusted_observation(connection, observation_id, adjustment_basis, information_cutoff_utc) -> DerivedObservation`.
- Both return explicit corporate-action event/factor lineage.

- [ ] **Step 1: Write failing split and dividend information-cut tests**

```python
def test_split_announced_after_historic_cut_does_not_adjust_historic_position(connection):
    result = derive_adjusted_position(connection, line_id, historic_cut)
    assert result.quantity == Decimal("100")

def test_known_split_adjusts_derived_history_without_mutating_raw_observation(connection):
    result = derive_adjusted_observation(connection, raw_observation_id, "SPLIT_ADJUSTED", later_cut)
    assert result.value == Decimal("50")
    assert raw_observation_value(connection, raw_observation_id) == Decimal("100")
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_corporate_action_service.py -v`

Expected: failure because corporate-action application service does not exist.

- [ ] **Step 3: Add event availability and derived-result lineage**

Add an event-recorded timestamp and source-payload relationship where absent. The service selects only events recorded on or before the historic information cut, applies factors in deterministic effective-date order, and persists a new derived result with method/version/event lineage. It never updates raw price or position snapshots.

- [ ] **Step 4: Run focused and full tests**

Run: `pytest tests/test_corporate_action_service.py -v` and `pytest -q`

Expected: raw immutability and historic-information behaviour pass.

- [ ] **Step 5: Commit**

```bash
git add security_master_schema alembic tests security-master-notes/10-corporate-actions-and-adjusted-market-data.md security-master-notes/16-database-implementation-plan.md
git commit -m "feat: derive corporate action adjusted results"
```

## Plan self-review

* Schema deployment, tenancy, mapping validity, entitled resolver, fund/share-class and bond terms, Soft-NAV calculation, and corporate-action application each have an independently testable task.
* Product breadth beyond the defined fund/bond daily valuation slice is intentionally absent.
* Interfaces in later tasks are defined by earlier tasks or stated explicitly in the task that introduces them.
* The plan keeps raw observations immutable and requires migration-based schema evolution.
