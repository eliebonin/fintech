# Tenancy and entitlements

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Platform security and architecture team  
**Last reviewed:** 2026-09-10

The canonical database is shared; tenant databases provide isolated client overlays and confidential data. Data entitlement, licensing, approval, tenant routing, and promotion from private reference data to canonical are explicit controls rather than implied by storage location.

Primary detail: [tenant overlays and Soft NAV](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md), [tenant database topology](../../../security-master-notes/19-tenant-database-topology-and-priorities.md), and [tenant routing/API contract](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md).

Current decision: [tenant capabilities and operating profiles](tenant-capabilities-and-operating-profiles.md).
