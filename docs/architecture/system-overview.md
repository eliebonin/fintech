# System overview

**Status:** Accepted  
**Content type:** Architecture  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-10-29

For the current visual structure, start with the [architecture atlas](atlas/README.md):
database schemas, code boundaries, data flow, complete dependency inventory and
confirmed coupling hotspots. Its read-only catalogue check at migration 104 found
204 application tables across ten schemas, matching complete runtime metadata at
the inspected table/FK-pair/column-count level.

The current alpha runs a shared PostgreSQL security/reference plane with tenant-scoped private references, strategies, trades, policies and financial evidence. UUIDs are immutable identity; provider identifiers are effective-dated mappings. Tenant database routing/separate-database topology remains a broader design foundation, not a deployed fleet. Platform administration is separate from the selected tenant; active modules, user/group action grants and dataset licensing are independent controls.

Market data is acquired through `market_data` and operator entry points in `apps/market_data_ingestor`, not reference API requests. Immutable source observations, derived-price proof, scoped rights, source priorities, policies, calendars and information cutoffs govern valuation inputs. Trade booking freezes approved economics; append-only corrections retain original executions. `positions` reconstructs compatible positions without a total trade cap. `valuation` calculates bounded economic position P&L and stages/reviews/publishes immutable versions; it is not full NAV, settlement/accounting or universal derivative valuation.

The Python API owns HTTP context and audited transaction wiring; shared domain
services also execute database queries using caller-owned connections. Pricing-
policy commands are now shared by HTTP and operator entry points; exact evidence
primitives live below valuation. Listed-cash commands and required validation now
live in `trading`, shared by the ticket/API and file confirmer. Reference and other
product booking orchestration remain partly API-owned. See
[phases 1–3](../delivery/api-service-extraction-20261029.md) and the
[cash pilot](../delivery/cash-booking-service-extraction-20261029.md).
Next.js BFF/server components propagate validated local context, and client
components manage interaction. The frontend does not calculate authoritative
financial totals. Production authentication/deployment and latest visual/financial
acceptance remain separate work.

Regulatory Reporting is now a separate bounded preparation/review/export module.
It consumes executions and assessed legal-entity/mapping facts directly, not P&L
results. Its local preparation exports are not FCA submissions or acknowledgements.
File intake uses shared parsers/retained artifacts and existing governed booking;
external-dataset reconciliation remains optional tooling outside product runtime.

Start from the [feature register](../product/feature-register.md) for actual supported scope and gaps. [October 12 reconciliation](../delivery/quality-reviews/2026-10-12-documentation-reconciliation.md) records baseline and verification limits.

Sources: [architecture baseline](../../security-master-architecture-notes.md), [Spineoff baseline](spineoff-context-and-knowledge-transfer-2026-09-09.md), and [global review](global-db-api-frontend-review-2026-09-10.md).
