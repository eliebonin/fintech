# Trading and operations

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Trading operations team  
**Last reviewed:** 2026-10-12

Trades are booked economic events, not orders or a universal multi-leg abstraction. Party roles identify trader, booker, counterparty, client, agent, and reference context. Fees are effective-dated and generic across funds, share classes, AMCs, and other chargeable objects.

Current scope: [product booking](../../product/features/product-booking.md) and [trade operations](../../product/features/trade-operations.md). `/trades/new` is the dedicated ticket; `/trades` is live tenant history. Common nullable fields and governed tenant properties retain immutable definitions/catalogue values; each tenant is currently limited to 1,000 active field definitions and a separate 1,000 active tags. Supported erroneous records can be cancelled/replaced with lineage, not overwritten.

Contractual delivery/exercise/redemption/reset is distinct from record correction. The existing FX-delivery slice is parked and not signed off; settlement/accounting remain explicitly deferred. Daily interest/economic-flow inputs are a bounded P&L capability, not complete cash posting or fund operations. Generic fee/operational mapping schema does not mean those full modules are delivered.

Primary detail: [market-data/trade boundary](../../../security-master-notes/03-market-data-marks-and-trades.md), [entities and parties](../../../security-master-notes/07-entities-and-instrument-parties.md), and [fees and charges](../../../security-master-notes/22-fees-and-charges.md).

Tenant administrator, agent and custodian feed IDs are documented in
[tenant fund operational mappings](tenant-fund-operational-mappings.md).
