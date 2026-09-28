# Schema hardening checkpoint

This note records the weaknesses found while building the search, instrument-detail, external-mapping review, and work-queue UI. The existing architecture remains the baseline: a canonical financial-reference graph, separate economic instruments and venue listings, immutable market-data observations, tenant overlays, and append-only operational events.

## Findings

### 1. Definition versions were not the read authority

`secm.instrument` and `secm.listing` contain current/effective fields while `instrument_definition_version` and `listing_definition_version` contain a second copy. The first API read path selected the mutable rows, so a historical or effective-date view could disagree with the approved version history.

The hardening change adds database checks for valid periods and backfills the version tables from legacy rows. The API now reads the approved current version deterministically. Existing base columns are retained as a compatibility projection until writers migrate.

### 2. Tenant scope was only object-level

`reference_node_scope` can mark a complete node as shared or private, but it cannot express a tenant-approved override of one canonical field. This is intentionally not solved with an ungoverned JSON blob. A field-level, typed override model is deferred; the current release only makes ownership and membership explicit and prevents accidental cross-tenant mappings.

### 3. Tenant context and routing were not enforceable end to end

The local API accepts trusted headers supplied by the BFF, but there was no tenant/user membership relation. `tenant_database_registry` records routing metadata but does not yet route a request to a different database. The hardening release adds membership data and API checks. Production Auth0 claim validation and actual overlay-database routing remain deployment work.

### 4. External identifier mappings lacked ownership and strong target rules

Mappings are polymorphic by design, but the previous table did not record tenant ownership directly and relied on service validation for target existence. The existing exclusion rule prevents overlapping effective mappings globally; it did not distinguish shared canonical mappings from tenant-local aliases. The hardening release adds nullable tenant scope (null means shared), effective validation, a target-type trigger for new writes, and lookup indexes. The target remains polymorphic because PostgreSQL cannot express one FK to several subtype tables without a larger redesign.

### 5. Market-data provenance existed, but entitlement was not part of the read path

Observations already retain dataset, licence, vintage, cut, receipt, and source fields. The UI repository did not join tenant dataset entitlements, so provenance did not itself prove that a tenant could view the value. The release applies the entitlement predicate to API evidence reads. A dedicated resolver remains the authoritative valuation path; the UI evidence endpoint is not a generic latest-price service.

### 6. Series and observations needed a small identity layer

One observation table is still correct for prices, rates, curves, volatility, macro data, and marks. What was missing was a way to describe dimensions such as tenor, strike, delta, quote side, fixing, or venue session, and an idempotency key for replayed provider files. The release adds a small series-dimension table and source-observation uniqueness metadata rather than creating separate price/curve/volatility tables. The key is unique within a series, dataset, and source vintage (with a legacy null-vintage sentinel), so a corrected provider vintage can append a new observation without mutating the old one.

### 7. Trade, cash, and Soft-NAV audit details were incomplete

The trade model already separates booked events from cash snapshots and lifecycle events. The release restores the retained `locked_ytm` field, adds an idempotent external-reference key, makes cash snapshots uniquely addressable by account/currency/cut/type/as-of, and links valuation lines to the frozen NAV input item that supplied the price or FX rate. `par_value` remains deliberately retired as a legacy field.

### 8. Type, units, and date semantics remain partly service-governed

The node-type and economic-instrument-type catalogues are correct, but cross-table subtype consistency, term-table applicability, percentage scale, and non-overlapping effective dates are not all expressible with simple foreign keys. New constraints cover low-risk cases. A full type-rule registry, field-level override engine, and complete unit vocabulary are deferred to avoid overengineering the foundation.

## Implemented in this pass

- Tenant membership and active-membership API guard.
- Direct tenant scope on external mappings; shared mappings use null scope.
- Effective-date/status filtering for identifiers, mappings, and definition versions.
- Entitlement-aware market-data evidence reads.
- Market-data series dimensions and observation idempotency fields/indexes.
- Trade `locked_ytm`, external-reference uniqueness, cash snapshot uniqueness, and NAV line input linkage.
- PostgreSQL checks/indexes/triggers with comments on every new column.
- Policy-mediated equity onboarding with source-scoped idempotency, automated/manual decision evidence, and atomic tenant-private materialisation.
- Regression tests for cross-tenant visibility, duplicate mappings/observations, entitlement filtering, and audit links.

## Explicitly deferred

1. A typed field-level tenant override table with approval workflow and merge precedence.
2. Runtime tenant-database routing from `tenant_database_registry`, including secret-manager integration and cross-database UUID validation.
3. Row-level security policies; application/BFF authorization is the current boundary while the topology is finalized.
4. A complete market-data surface model (for example full volatility cubes) beyond the series-dimension table.
5. Full subtype coverage and automated “instrument type requires these term tables” validation.
6. Corporate-action entitlement processing and vendor-restated historical-vintage policy beyond the existing immutable adjustment lineage.
7. A migration of all source-system string columns to foreign keys; legacy integrations are retained until their codes are reconciled.
8. Bulk reference-data adapters, fuzzy matching, CFI/regulatory classification assignments, and automatic promotion of tenant-private instruments to shared canonical identity.

## Acceptance rule

The database is considered ready for the next UI slice when a caller cannot read a tenant-private mapping or unentitled market-data observation, duplicate source observations are rejected deterministically, and a Soft-NAV valuation line can identify the exact frozen price/FX input and cut used. The deferred items are not prerequisites for the current MVP, but they must be resolved before multi-tenant production launch.
