# System overview

**Status:** Accepted  
**Content type:** Architecture  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-10-12

The current alpha runs a shared PostgreSQL security/reference plane with tenant-scoped private references, strategies, trades, policies and financial evidence. UUIDs are immutable identity; provider identifiers are effective-dated mappings. Tenant database routing/separate-database topology remains a broader design foundation, not a deployed fleet. Platform administration is separate from the selected tenant; active modules, user/group action grants and dataset licensing are independent controls.

Market data is acquired through `market_data` and operator entry points in `apps/market_data_ingestor`, not reference API requests. Immutable source observations, derived-price proof, scoped rights, source priorities, policies, calendars and information cutoffs govern valuation inputs. Trade booking freezes approved economics; append-only corrections retain original executions. `positions` reconstructs compatible positions without a total trade cap. `valuation` calculates bounded economic position P&L and stages/reviews/publishes immutable versions; it is not full NAV, settlement/accounting or universal derivative valuation.

The Python API owns database access; Next.js BFF/server components propagate validated local context, and client components manage interaction. The frontend does not calculate authoritative financial totals. Production authentication/deployment and latest visual/financial acceptance remain separate work.

Start from the [feature register](../product/feature-register.md) for actual supported scope and gaps. [October 12 reconciliation](../delivery/quality-reviews/2026-10-12-documentation-reconciliation.md) records baseline and verification limits.

Sources: [architecture baseline](../../security-master-architecture-notes.md), [Spineoff baseline](spineoff-context-and-knowledge-transfer-2026-09-09.md), and [global review](global-db-api-frontend-review-2026-09-10.md).
