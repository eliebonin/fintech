# Integrations and data rights

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Data operations and platform security team  
**Last reviewed:** 2026-10-07

Boundary payloads—FpML, FIX, ISO 20022, provider feeds, custododian messages—are retained with mapping and processing lineage, not copied into the internal schema. Provider/dataset/licence attribution and tenant entitlement govern use and visibility.

The [Yahoo personal-project delivery](../../delivery/yahoo-market-data-alpha.md) adds activity grants, conjunctive layered prerequisites and immutable ingestion evidence. A personal declaration is not commercial or automated-access clearance. Legacy synthetic fixtures retain their prior entitlement model; commercial datasets require separate review.

Shared activity checks now live in `market_data/rights.py`, used by intake and consumers without importing acquisition. The [ingestion boundary](../../delivery/market-data-ingestion-boundary.md) records ownership, preserved controls and adapter contracts.

Tenant-owned administrator, agent and custodian identifiers whose meaning
depends on an accounting or valuation feed use the dedicated
[tenant fund operational mappings](../trading-and-operations/tenant-fund-operational-mappings.md)
configuration rather than shared canonical mappings.

Primary detail: [industry standards](../../../security-master-notes/12-industry-standards-and-integration-boundaries.md) and [research evidence](../../research/evidence-register.md).
