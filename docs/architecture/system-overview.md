# System overview

**Status:** Accepted  
**Content type:** Architecture  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-09-10

The platform has a shared canonical reference-data plane for instruments, listings, entities, identifiers, market-data provenance, and corporate actions. Tenant-held systems overlay client-specific reference data and retain tenant positions, trades, marks, policies, and confidential economics. UUIDs are immutable internal identity; provider identifiers are effective-dated mappings.

Market data is selected through governed series, entitlement, valuation-cut, vintage, and policy context. Raw observations never become valuation marks by overwrite. Trade storage records economic events, while cash and valuation results are state/snapshot domains. API contracts and a frontend BFF expose the platform incrementally without requiring a core Python rewrite.

Sources: [architecture baseline](../../security-master-architecture-notes.md), [Spineoff baseline](spineoff-context-and-knowledge-transfer-2026-09-09.md), and [global review](global-db-api-frontend-review-2026-09-10.md).
