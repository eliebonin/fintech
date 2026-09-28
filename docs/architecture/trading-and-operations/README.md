# Trading and operations

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Trading operations team  
**Last reviewed:** 2026-09-10

Trades are booked economic events, not orders or a universal multi-leg abstraction. Party roles identify trader, booker, counterparty, client, agent, and reference context. Fees are effective-dated and generic across funds, share classes, AMCs, and other chargeable objects.

Primary detail: [market-data/trade boundary](../../../security-master-notes/03-market-data-marks-and-trades.md), [entities and parties](../../../security-master-notes/07-entities-and-instrument-parties.md), and [fees and charges](../../../security-master-notes/22-fees-and-charges.md).

Tenant administrator, agent and custodian feed IDs are documented in
[tenant fund operational mappings](tenant-fund-operational-mappings.md).
