# Integrations and data rights

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Data operations and platform security team  
**Last reviewed:** 2026-10-12

Boundary payloads—FpML, FIX, ISO 20022, provider feeds, custododian messages—are retained with mapping and processing lineage, not copied into the internal schema. Provider/dataset/licence attribution and tenant entitlement govern use and visibility.

The [Yahoo personal-project delivery](../../delivery/yahoo-market-data-alpha.md) adds activity grants, conjunctive layered prerequisites and immutable ingestion evidence. A personal declaration is not commercial or automated-access clearance. Legacy synthetic fixtures retain their prior entitlement model; commercial datasets require separate review.

Shared activity checks now live in `market_data/rights.py`, used by intake and consumers without importing acquisition. The [ingestion boundary](../../delivery/market-data-ingestion-boundary.md) records ownership, preserved controls and adapter contracts.

Historical selection and current access must each cover the exact same series,
dataset, tenant and purpose; separately dated grants may satisfy these checks.
Neither check substitutes for current activity rights. The bounded
[Yahoo EUR/GBP valuation setup](../../delivery/yahoo-eurgbp-valuation-setup-2026-10-09.md)
tests this distinction and current revocation. Its delivery record includes the
subsequent bounded local activation; this is not a universal grant for all stored
Yahoo FX observations or commercial access. See [current licensing/data scope](../../product/features/market-data.md).

Tenant-owned administrator, agent and custodian identifiers whose meaning
depends on an accounting or valuation feed use the dedicated
[tenant fund operational mappings](../trading-and-operations/tenant-fund-operational-mappings.md)
configuration rather than shared canonical mappings.

Primary detail: [industry standards](../../../security-master-notes/12-industry-standards-and-integration-boundaries.md) and [research evidence](../../research/evidence-register.md).

The [scoped dataset entitlement delivery](../../delivery/scoped-dataset-entitlements.md)
adds explicit licensed-market/package coverage within mixed datasets, without
duplicating providers. Selection and disclosure enforce the actual dataset/series
classification. Tenant-owned source identities are private. The
[source catalogue and priority UI](../../delivery/market-data-sources-ui.md)
adds versioned platform defaults and tenant overrides, with as-known selection
evidence and rights-preserving ranking. Generic upload workflows remain separate.
