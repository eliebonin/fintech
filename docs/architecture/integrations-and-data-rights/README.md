# Integrations and data rights

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Data operations and platform security team  
**Last reviewed:** 2026-09-10

Boundary payloads—FpML, FIX, ISO 20022, provider feeds, custododian messages—are retained with mapping and processing lineage, not copied into the internal schema. Provider/dataset/licence attribution and tenant entitlement govern use and visibility.

Tenant-owned administrator, agent and custodian identifiers whose meaning
depends on an accounting or valuation feed use the dedicated
[tenant fund operational mappings](../trading-and-operations/tenant-fund-operational-mappings.md)
configuration rather than shared canonical mappings.

Primary detail: [industry standards](../../../security-master-notes/12-industry-standards-and-integration-boundaries.md) and [research evidence](../../research/evidence-register.md).
