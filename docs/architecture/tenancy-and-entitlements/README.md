# Tenancy and entitlements

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Platform security and architecture team  
**Last reviewed:** 2026-10-12

The implemented local alpha uses a shared database with explicit tenant ownership/scope, not one deployed database per tenant. Separate tenant-database routing/topology is a retained design direction. Platform operators manage tenants/modules outside tenant context; tenant admins manage users/groups. Effective actions intersect enabled modules and membership/group grants. Source licensing is an additional independent gate.

`/select-context` issues validated local sessions with real actor and selected subject; `/tenant-profile` owns module visibility and tenant access management. Production Auth0/OIDC and infrastructure isolation are not certified by local switching. See [access capability records](../../product/features/access-and-strategies.md), [administration delivery](../../delivery/tenant-access-administration.md) and [production gaps](../../product/features/access-and-strategies.md#f06-production-identity-and-isolation).

Primary detail: [tenant overlays and Soft NAV](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md), [tenant database topology](../../../security-master-notes/19-tenant-database-topology-and-priorities.md), and [tenant routing/API contract](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md).

Current decision: [tenant capabilities and operating profiles](tenant-capabilities-and-operating-profiles.md).
