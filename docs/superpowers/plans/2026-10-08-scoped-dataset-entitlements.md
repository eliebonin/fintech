# Scoped Dataset Entitlements Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. User instructions override additional approval prompts, subagent review and full-suite runs.

**Goal:** Enforce market/package-level access within mixed datasets without duplicating providers.

**Architecture:** Named packages classify dataset/series pairs; scoped tenant grants reference those packages. A shared SQL predicate gates resolution and disclosure. Existing activity rights remain conjunctive and authoritative.

**Tech Stack:** Python, SQLAlchemy Core, PostgreSQL, Alembic, pytest.

**Spec:** ../specs/2026-10-08-scoped-dataset-entitlements.md

## Global constraints

- Preserve unrelated dirty changes in the existing user-approved feature checkout.
- Use additive migration 73; do not grant new operating-data permissions or apply the migration to the operating database without reporting it.
- No quarterly review workflow, priority engine, or upload UI in this slice.
- Tenant-supplied data uses a tenant-owned provider identity; upload does not erase original vendor provenance or rights. Its designated validated series should default to highest preference in the subsequent priority delivery, not every uploaded record automatically.
- Focused tests only, using disposable databases; no full suite.

## Review focus

- Unclassified series must not bypass a scoped grant.
- A grant to another dataset or tenant must not disclose data.
- Catalogue totals and instrument detail must use identical scope filters.
- Frozen financial evidence must recheck current series-specific scope permissions.
- Legacy dataset-wide grants must remain usable without inventing new package grants.

### Task 1: Persistent coverage and SQL eligibility

Files: security_master_schema/models.py; alembic/versions/20261008_73_dataset_coverage.py; market_data/entitlements.py; tests/test_dataset_coverage.py.

Interface: tenant_series_entitlement_clause(dataset_id, series_id, tenant_id, use_purpose, on_date, *, entitlement=None) returns a correlated SQL predicate. Passing an entitlement constrains that exact row; otherwise the predicate finds an eligible current tenant grant.

- [x] Write tests for package-only selection, unknown classifications, current dates, cross-dataset constraints and existing whole-dataset grants.
- [x] Run focused tests and observe missing-feature failures.
- [x] Add coverage packages, explicit dataset/series classifications, scoped tenant package associations, and an explicit DATASET/SCOPED entitlement mode.
- [x] Add an optional owner_tenant_id to provider records; enforce tenant-private source datasets in the predicate.
- [x] Run focused tests to green; verify migration upgrade and guarded downgrade on an isolated database.

### Task 2: Integrate consumers

Files: security_master_schema/market_data_resolver.py; apps/reference_api/repository.py; market_data/display_access.py; apps/reference_api/valuation_policies.py; valuation/evidence_access.py.

- [x] Add regressions for selection, catalogue/detail disclosure and frozen evidence permission changes.
- [x] Run regressions to observe the missing enforcement (catalogue returned both packages under a scoped grant).
- [x] Apply the shared predicate before observation selection, catalogue pagination/counts and display.
- [x] Pass exact dataset/series contexts when inspecting frozen inputs; unknown contexts fail closed for scoped grants.
- [x] Run affected rights, display, resolver and valuation evidence regression tests.

### Task 3: Document and review

Files: docs/delivery/scoped-dataset-entitlements.md; docs/architecture/integrations-and-data-rights/README.md.

- [x] Record schema, configuration procedure, current upload capability, tenant-source priority requirement, deferred UI/priority work and source references.
- [x] Review the task diff independently of implementation flow; verify Python compilation and whitespace.
- [x] Report verified tests and migration activation status; do not claim priority/upload features implemented by this slice.

## Execution record

- Existing user-approved feature checkout preserved; no new worktree, commits or push.
- Docker was initially unavailable; unit SQL tests used in-memory SQLite, then the user started Docker and isolated PostgreSQL tests completed.
- Baseline metadata test proved the missing scope field. It was removed after substantive query/consumer tests covered the persisted behaviour rather than retaining a source-shape assertion.
- Catalogue regression RED: 2 series visible instead of 1; GREEN after shared scope enforcement.
- Final regression run: 79 passed, 16 existing seed deprecation warnings. No full suite.
- Migration 73 round-trip and guard verified in isolation, then additive upgrade applied to the local app DB; no operating grants changed.
- Ruling: a tenant-owned source identity is supported now, but the upload API/UI and validated tenant-first source priority belong to the subsequent delivery; auto-promoting arbitrary uploads would bypass governed selection.
