# Structured-Product Condition Groups Implementation Plan

> **Status:** implemented through Alembic revision `20260909_31`. This file is
> retained as the execution record and decision trail; it is no longer a list
> of pending work.

**Goal:** Replace standalone barriers and rule-owned actions with a versioned
structured-product graph consisting of terms, typed components, condition
groups, atomic predicates, ordered actions, and coupon configuration.

**Architecture:** `secm.structured_product_terms` is the contractual version
anchor. Composition rows identify child occurrences and their signed/typed
values. A group owns observation and Boolean semantics; a barrier rule is an
atomic member; a group action executes once and may target an exact component.

**Tech stack:** Python 3, SQLAlchemy Core metadata, Alembic, PostgreSQL, and
focused pytest tests.

## Implemented tasks

### Task 1: Schema metadata contract — complete

Implemented in `security_master_schema/models.py`:

* versioned `structured_product_terms` with `structured_product_terms_id`,
  scope, supersession, and source lineage;
* `structured_product_condition_group` with terms ownership and
  `underlying_scope`;
* atomic `barrier_rule` members with explicit resolved underlyings;
* `condition_group_action` with parent/component targeting and payout fields;
* typed composition values (`composition_value`, `composition_value_kind`,
  `component_sequence`); and
* `structured_product_component_terms`, coupon programme, and coupon period
  metadata.

Named checks, foreign keys, and unique constraints cover enum values,
sequence ordering, schedule consistency, level bounds, target scope, and
payout shapes. Cross-table membership checks remain service validation.

### Task 2: Alembic and demo fixture — complete

Implemented in
`alembic/versions/20260909_31_structured_product_model_hardening.py` and
`security_master_schema/demo_data.py`.

The migration repairs the earlier terms primary key and dependent foreign keys,
adds the new fields/tables, backfills composition sequences and terms links,
and backfills determinable component-action payout metadata. The preceding
terms/coupon migration now has a reversible downgrade. The fixture contains a
worst-of autocall with typed components, coupon programme/period rows,
component payoff terms, and ordered coupon-then-redemption actions. It remains
idempotent with the legacy demo composition row.

### Task 3: Documentation — complete

The authoritative model is documented in:

* `security-master-notes/26-structured-product-condition-groups.md`;
* `security-master-notes/27-structured-product-terms-and-coupon-memory.md`;
* the structured-product section of
  `security-master-notes/04-derivatives-futures-and-swaps.md`; and
* `docs/superpowers/specs/2026-09-08-structured-product-condition-groups-design.md`.

These documents explicitly record parent versus component barriers, resolved
underlyings, typed composition semantics, terms versioning, coupon memory,
and deferred calculation capabilities.

## Verification record

The following focused checks passed after implementation:

* `tests/test_structured_product_condition_groups.py` and
  `tests/test_schema_metadata.py`: 26 passed;
* `tests/test_migrations.py`: 1 passed, including upgrade and downgrade;
* `tests/test_demo_scenarios.py`: 10 passed;
* `tests/test_reference_api_boundary.py`: 2 passed;
* Python `compileall` for models, migrations, demo loader, and API; and
* `alembic heads`: one head, `20260909_31`.

Per project instruction, the complete Python test suite was not rerun.

## Deferred follow-up

The next slice is not another schema rewrite. It should add service-level
validation and read APIs for terms-version/component membership, followed by a
separate outcome/valuation domain for resolved condition results, coupon
ledgers, cashflows, and market-data snapshots. Count thresholds, nested Boolean
groups, generic payoff AST/pricing, and full amendment replay remain explicit
future decisions.
