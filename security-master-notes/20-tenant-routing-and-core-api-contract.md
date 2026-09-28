# Tenant routing and core API contract

## Purpose

The central database is the trusted control plane for tenant routing. An
authenticated request supplies an authorised tenant context, not a database
name. The service selects the destination from `ten.tenant_database_registry`
and opens a tenant-specific pool using a secret reference held by the control
plane.

```text
Auth0 subject
  -> authenticated tenant membership
  -> registry lookup for exactly one ACTIVE route
  -> tenant database connection
  -> central canonical/market-data API calls as needed
```

## Registry fields and rules

Each registry row identifies the tenant, logical database name, cluster and
environment, deployed schema revision, secret reference, lifecycle status, and
audit timestamps. A tenant must have exactly one active route in the current
environment. Database names and endpoints are never accepted from a client
request, and registry entries are not tenant-editable data.

Routing failures are explicit (`TENANT_NOT_FOUND`, `ROUTE_INACTIVE`,
`ROUTE_AMBIGUOUS`, or `ROUTE_CONFIGURATION_ERROR`) and are auditable. A route
change is a control-plane operation with a migration/health-check prerequisite,
not an implicit fallback to another tenant database.

## Cross-database canonical references

PostgreSQL foreign keys stop at a database boundary. Tenant rows therefore keep
the central UUID plus local `ten.canonical_reference_link` evidence: canonical
object type, approved version/status, validation timestamp, API version, and
validation result. The central API validates the UUID/object type before a
tenant trade, position, override, or NAV input is committed. The local link is
cache/evidence, never a replacement source of truth.

## Operational requirements still deferred

The schema and pure routing contract are implemented, but production operation
still needs:

* per-tenant role/credential provisioning and rotation;
* migration orchestration and health checks recorded against the registry's
  schema revision;
* authenticated PostgreSQL session context and RLS policies as defence in
  depth;
* central API authorization, rate limits, and audit logging; and
* restore/failover tests that prove a route cannot cross tenant boundaries.

These are deliberately control-plane and deployment concerns rather than
additional polymorphic columns in the canonical tables.
