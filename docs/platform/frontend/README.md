# Frontend

**Status:** Current alpha reference  
**Content type:** Platform index  
**Owner:** Frontend engineering  
**Last reviewed:** 2026-10-12

The runtime is Next.js App Router/React in `apps/ops-console`. Server/BFF code calls the Python API; browsers never access PostgreSQL or authoritative financial calculations. Native workspace CSS and focused client forms coexist with the existing MUI dependency; do not assume the old mock-up layout describes every current page.

## Runtime journeys

| Journey | Routes | Current capability/evidence |
| --- | --- | --- |
| Context and control plane | `/select-context`, `/platform/tenants` | [Access capabilities](../../product/features/access-and-strategies.md) |
| Tenant profile/access | `/tenant-profile` and access management | [Users/groups/module scope](../../delivery/tenant-access-administration.md) |
| Strategies | `/strategies` | [Strategy register](../../delivery/tenant-workspace-strategy-alpha.md) |
| References | `/instruments`, type creation, detail/listing, `/operations` | [Instrument management](../../product/features/instrument-management.md) |
| Booking/history | `/trades/new`, `/trades`, trade detail | [Booking types](../../product/features/product-booking.md), [operations](../../product/features/trade-operations.md) |
| Market data | `/market-data`, `/market-data/explorer`, coverage, sources, policies | [Data capabilities](../../product/features/market-data.md) |
| Valuation/review | `/valuation` | [Economic P&L/review](../../product/features/valuation-and-pnl.md) |

Module/group permissions govern actions; backend authority remains decisive. Frozen submissions and stale-context checks preserve retry safety. Loading/error recovery and server access errors must not masquerade as empty data or approved results. The retired home P&L demo is not a supported calculator.

## Acceptance boundary

Earlier isolated trade-side browser journeys are recorded separately from the latest access/P&L changes. Component/HTTP tests, typechecks and a production build are not visual/keyboard/mobile/screen-reader acceptance. See [frontend remaining acceptance](../../product/features/platform-quality.md#f49-frontend-acceptance), [style review](../../delivery/frontend-style-review-2026-10-08.md) and [trade walkthrough evidence](../../delivery/trade-side-acceptance-2026-10-06.md).

[Operations Console run guide](../../../apps/ops-console/README.md) describes runtime entry points. The [ui workstream](../../../ui/README.md), screen specs and decisions are retained design history; use the [feature register](../../product/feature-register.md) for actual implementation status. Any explicit synthetic fallback is local and route-specific, not a universal substitute for authorized live data.
