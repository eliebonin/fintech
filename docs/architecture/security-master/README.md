# Security master

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Security-master operations and architecture team  
**Last reviewed:** 2026-10-12

Canonical instruments model economic contracts; listings model venue-specific tradability. Structural node type, governed instrument type, and optional business taxonomy remain distinct. Legal economics live in focused terms, legs, barrier, schedule, and composition models.

Current implemented scope is in [instrument management](../../product/features/instrument-management.md), [product booking](../../product/features/product-booking.md) and the [capability matrix](../../delivery/booking-capability-matrix.md). Creation, listing, booking and valuation eligibility are separate. Future family → canonical expiry → listing is implemented; physical/crypto terms do not imply physical/crypto booking. General tenant taxonomy administration and universal instrument amendments remain incomplete.

Primary detail: [scope](../../../security-master-notes/01-scope-and-principles.md), [identity](../../../security-master-notes/02-reference-identity-model.md), [derivatives](../../../security-master-notes/04-derivatives-futures-and-swaps.md), [entities](../../../security-master-notes/07-entities-and-instrument-parties.md), [structured-product terms](../../../security-master-notes/08-sp-key-terms-and-product-applicability.md), [macro/commodity/crypto/wrappers](../../../security-master-notes/11-macro-commodities-crypto-and-exchange-traded-wrappers.md), [venues](../../../security-master-notes/14-geographic-areas-and-market-venues.md), [option versioning](../../../security-master-notes/25-option-strike-resets-and-terms-versioning.md), and structured-product documents [26](../../../security-master-notes/26-structured-product-condition-groups.md), [27](../../../security-master-notes/27-structured-product-terms-and-coupon-memory.md), [29](../../../security-master-notes/29-structured-product-correction-pass.md).

Tenant operational IDs from fund administrators, agents and custodians remain
outside the shared canonical hierarchy; see
[tenant fund operational mappings](../trading-and-operations/tenant-fund-operational-mappings.md).
