# Central canonical database and tenant overlay databases

## Adopted topology

Fortem will use one central generic PostgreSQL database for shared canonical
reference data and shared market-data content, plus one tenant-specific logical
database for each client's confidential operating overlay.

```text
central core database
  secm   canonical nodes, instruments, listings, entities, venues, identifiers
  md     providers, datasets, licences, observations, corporate actions

tenant overlay database (one per client)
  ten    client policies, entitlements, overrides, private instruments
  trd    strategies, trades, positions, cash and trade-party data
  nav    Soft-NAV runs, frozen inputs, marks and reconciliations
  ing    client submissions, mappings and processing lineage
```

The tenant database contains the client's delta and operational records. It
does not copy the canonical master or the full market-data store. A tenant
record stores Fortem UUIDs from the core database; UUIDs remain stable even
though the physical databases are separate.

## Cross-database reference rule

PostgreSQL cannot enforce ordinary foreign keys between databases. The tenant
service therefore validates every central UUID through a versioned canonical
API and stores a small local link/cache containing the canonical object type,
version/status and last-validation time. That cache is not a source of truth.

```text
tenant trade / position / override
  -> central reference UUID
  -> canonical API validation
  -> local immutable link evidence
```

Do not use ad-hoc database links or distributed two-phase transactions for
normal booking. If a core lookup and tenant write cannot complete together, the
operation is a durable pending/exception workflow and is reconciled explicitly.

## Overlay and private-record semantics

An approved tenant override references a central node and changes only that
tenant's interpretation or use of it. It does not create a new canonical
instrument ID. A confidential product that is not suitable for the shared
master receives a tenant-local UUID and may reference shared underlyings.

```text
central instrument UUID
  + tenant A approved alias/preferred series/valuation rule
  + tenant B different approved alias/preferred series/valuation rule

tenant A private OTC instrument UUID
  + shared underlying UUIDs where safe
```

Effective reads apply approved tenant data first, then canonical data, then an
explicit missing-data result. Private terms never become visible through a
shared UUID or promotion shortcut; promotion is a reviewed canonical proposal.

## Market-data and Soft-NAV placement

Raw observations remain in the central market-data database because they are
shared licensed facts. The resolver evaluates tenant entitlement, purpose,
policy and information cut. A tenant Soft-NAV run stores its frozen evidence in
the tenant overlay database, retaining the central series/observation/dataset
UUIDs plus the named valuation cut, UTC information cut, requested/used market
dates and FX-input lineage.

The local snapshot is therefore client-specific audit evidence, not a duplicate
price store. Both local price and FX conversion are independently resolved and
frozen.

## Tenant routing and control plane

A central tenant registry maps an authenticated tenant to its approved overlay
database, cluster/environment, schema revision and secret reference. The client
never supplies a database name or endpoint.

```text
Auth0 identity
  -> authorised tenant context
  -> tenant registry lookup
  -> tenant-specific connection pool
  -> core API calls for canonical/market-data access
```

Use distinct database roles and credentials per tenant. A separate database in
one PostgreSQL cluster provides logical isolation; a separate cluster is needed
when infrastructure-level isolation is contractually required.

## RLS position

The tenant database boundary is the primary operational isolation mechanism.
PostgreSQL RLS remains defence in depth for tenant tables, support access and
future shared deployments. The central database uses restricted steward and
platform roles for canonical writes. Licensed market data is not protected by a
naive `tenant_id` column; entitlement-aware resolver access remains mandatory.

## Migration and operations consequences

Migrations are versioned and applied through a control-plane orchestrator to the
core and every tenant database. Each tenant registry row records the deployed
schema revision. Backups, restore tests, credential rotation, monitoring and
retention are performed per overlay database. Cross-tenant analytics belongs in
an explicitly governed warehouse or reporting extract, never in an accidental
cross-database join.

## Revised implementation priorities

### P0 — foundation before first confidential client

1. Tenant registry, database routing, per-tenant credentials and canonical API
   contracts.
2. True versioning and immutable audit history for canonical instrument/listing
   definitions; current `sequence_no` fields must support actual history rather
   than merely describe it.
3. Cross-database UUID validation and local canonical-link evidence.
4. Append-only trade corrections, cancellation/supersession events and source
   idempotency keys.
5. Generic valuation-mark records linked to frozen price/FX resolution inputs.
6. Market-data provenance/vintage semantics sufficient to answer historic
   information-cut questions.

### P1 — required for a useful operating service

1. Entitlement-aware market-data resolver and tenant-local Soft-NAV snapshots.
2. Cash, FX, bond accrual, liability and reconciliation support in Soft NAV.
3. Shape-specific market data for curves, volatility surfaces, ticks and bars.
4. Controlled trade and product vocabularies plus per-type term validation.
5. RLS policies and pooled-connection context tests as defence in depth.
6. Versioned ingestion/API/file contracts and durable exception queues.

### P2 — later operating breadth

1. Persisted adjusted-history materialisation at scale.
2. Custody-grade corporate-action elections, tax, claims and settlement flows.
3. Settlement instructions, fails and post-trade processing.
4. Additional credit, repo, rate-option and exotic-product terms.

This ordering keeps the core identity, isolation, historical correctness and
trade audit foundations ahead of broad product coverage.

## Current implementation checkpoint

The additive SQLAlchemy/Alembic slice now contains the first primitives for all
six P0 controls: `ten.tenant_database_registry` for trusted routing,
effective-dated instrument/listing definition versions, tenant-local canonical
link evidence, append-only trade lifecycle events, generic tenant valuation
marks, and source-vintage/observation publication lineage. Pure validation
tests cover route selection, effective version selection, UUID/type links,
trade state derivation, mark evidence, and historic vintage eligibility.

The UI hardening follow-up adds active tenant membership, direct tenant scope on
external mappings, approved-version API reads, entitlement-aware market-data
evidence, source observation idempotency, series dimensions, and explicit
price/FX links from Soft-NAV valuation lines. See
[`docs/architecture/schema-hardening.md`](../docs/architecture/schema-hardening.md)
for the complete implemented/deferred list.

The version, lifecycle-event, valuation-mark, and source-vintage tables also
have PostgreSQL mutation-blocking triggers in their Alembic revisions. New
events, versions, or marks supersede prior facts; an application update cannot
rewrite the audit trail.

These are foundations, not a claim that production isolation or calculation
orchestration is finished. PostgreSQL RLS, automated per-tenant provisioning,
runtime database routing, typed override approval, and complete market-data
surface modelling remain explicit next steps.
