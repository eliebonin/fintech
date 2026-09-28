# Dynamic Option Strikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Model vanilla options whose strike is contractually determined or reset on scheduled dates without treating each reset as a new option-terms version.

**Architecture:** Keep one stable economic option instrument. Version the static `option_terms` definition when the legal/static contract changes, reuse the existing `secm.schedule` and `secm.schedule_event` tables for reset dates, store reset methodology in `secm.option_strike_reset_rule`, and store market-derived resolved strikes immutably in `secm.option_strike_fixing`. A small pure resolver returns the strike applicable on an as-of date.

**Tech Stack:** PostgreSQL, SQLAlchemy Core metadata, Alembic migrations, Python dataclasses, pytest/unittest-compatible tests, deterministic demo fixtures, Markdown decision notes.

**Spec:** `security-master-notes/04-derivatives-futures-and-swaps.md`, `security-master-notes/06-decision-log-and-open-questions.md`, and `security-master-notes/16-database-implementation-plan.md`.

## Global Constraints

- Use UUIDv7 internal identifiers and immutable lineage; provider identifiers are not primary identity.
- Keep `instrument_dates` as the authority for expiry/maturity; reset dates belong to schedules.
- `is_current` is a convenience pointer for terms versions, not a substitute for effective-date/as-of resolution.
- `event_sequence` and reset ordering are event order, not terms version numbers.
- Raw market observations and resolution snapshots remain immutable; a corrected fixing supersedes rather than overwrites.
- Every new column and table column must have a SQLAlchemy/Alembic comment.
- Do not introduce a generic EAV terms table or a formula engine in this slice.

---

### Task 1: Extend the SQLAlchemy option model and add reset/fixing tables

**Files:**
- Modify: `security_master_schema/models.py` around `option_terms`.
- Test: `tests/test_option_schema_contract.py`.

**Interfaces:**
- Produces metadata tables `secm.option_terms`, `secm.option_strike_reset_rule`, and `secm.option_strike_fixing`.
- Keeps `option_terms.instrument_node_id` as the lookup column while adding a surrogate `option_terms_id` for child-table references.

- [x] **Step 1: Write failing metadata tests** asserting the terms-version columns, `strike_mode`, reset schedule FK, reset-rule columns, fixing lineage columns, and required constraints/indexes.
- [x] **Step 2: Run `pytest tests/test_option_schema_contract.py -q` and confirm the new assertions fail because the metadata is absent.**
- [x] **Step 3: Add the columns and tables with explicit comments, FKs, unique constraints, and checks.**
- [x] **Step 4: Run the schema-contract tests and the existing option validation/schema tests.**

### Task 2: Add the Alembic migration

**Files:**
- Create: `alembic/versions/20260907_24_dynamic_option_strikes.py`.
- Test: `tests/test_migrations.py`.

**Interfaces:**
- Upgrades databases at revision `20260907_24` from `20260906_23`.
- Backfills existing option rows with version `1`, effective date from the linked instrument where available, `FIXED` strike mode, and `is_current=true`.

- [x] **Step 1: Extend the migration test to assert the new tables, version columns, current index, and foreign keys after upgrade.**
- [x] **Step 2: Run the migration test and confirm it fails against the current head.**
- [x] **Step 3: Implement an additive migration that changes the option primary key to `option_terms_id`, preserves existing rows, adds constraints/indexes, and creates the two child tables.**
- [x] **Step 4: Run the migration test, including downgrade to base, and verify both upgrade and downgrade succeed.**

### Task 3: Implement the pure strike resolver with TDD

**Files:**
- Create: `security_master_schema/option_strike_resolver.py`.
- Create: `tests/test_option_strike_resolver.py`.

**Interfaces:**
- `resolve_option_strike(*, as_of_date, strike_mode, initial_strike_value, reset_rules, fixings) -> ResolvedOptionStrike`.
- `StrikeResolutionError` for a missing applicable fixing or invalid dynamic definition.
- Supported MVP modes: `FIXED`, `FORWARD_START`, and `RESET`; `FLOATING` is rejected until a separate formula/rate convention is specified.

- [x] **Step 1: Write tests for fixed strikes, pre-reset initial strikes, fixed scheduled resets, market-derived fixing selection, missing fixing failure, and correction precedence.**
- [x] **Step 2: Run the resolver tests and confirm they fail because the module is absent.**
- [x] **Step 3: Implement the smallest deterministic resolver using event date/order and accepted, non-superseded fixings.**
- [x] **Step 4: Run resolver tests and refactor only while tests remain green.**

### Task 4: Add deterministic fixtures and integration coverage

**Files:**
- Modify: `security_master_schema/demo_data.py`.
- Modify: `tests/test_demo_scenarios.py`.
- Modify: `data/mockup/README.md` if the fixture inventory needs updating.

**Interfaces:**
- Adds one forward-start/reset call option with a strike-reset schedule, two reset rules, and two fixings.
- Existing fixed, index-point, and Bermudan option fixtures continue to load unchanged.

- [x] **Step 1: Add a failing fixture assertion for the reset option and its rules/fixings.**
- [x] **Step 2: Run the focused demo test and confirm the new fixture is absent.**
- [x] **Step 3: Add deterministic UUIDs and idempotent fixture inserts.**
- [x] **Step 4: Run the focused demo test and the full demo fixture suite.**

### Task 5: Document the decision and operational query rules

**Files:**
- Modify: `security-master-notes/04-derivatives-futures-and-swaps.md`.
- Modify: `security-master-notes/06-decision-log-and-open-questions.md`.
- Modify: `security-master-notes/16-database-implementation-plan.md`.
- Create: `security-master-notes/25-option-strike-resets-and-terms-versioning.md`.

**Interfaces:**
- Documents the distinction between terms versions, schedule event order, reset rules, and fixings.
- Documents when a reset remains one instrument and when a composed parent/child model is required.

- [x] **Step 1: Add the reviewed design and resolver semantics to the dedicated note.**
- [x] **Step 2: Record the implemented choice and deferred formula-engine/composed-product decisions in the decision log and implementation plan.**
- [x] **Step 3: Check links, table names, and migration revision references.**

### Task 6: Full verification

**Files:**
- No additional files.

- [x] **Step 1: Run `python -m unittest discover -s tests -p "test_*.py" -v`.**
- [x] **Step 2: Run `pytest -q` if the project environment provides pytest.**
- [x] **Step 3: Run Python compilation for changed modules.**
- [x] **Step 4: Report exact test counts and any environment limitation without claiming completion based on partial output.**
