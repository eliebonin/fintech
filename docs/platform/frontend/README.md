# Frontend

**Status:** Current alpha reference  
**Content type:** Platform index  
**Owner:** Frontend engineering  
**Last reviewed:** 2026-10-17

The runtime is Next.js App Router/React in `apps/ops-console`. Server/BFF code calls the Python API; browsers never access PostgreSQL or authoritative financial calculations. Native workspace CSS and focused client forms coexist with the existing MUI dependency; do not assume the old mock-up layout describes every current page.

## Runtime journeys

[Incomplete-price review](../../delivery/incomplete-price-review-20261031.md)
adds a compact required-input disclosure, unpriced investment/cash rows and the
Review-tab manual-mark workflow. Exact quote requests retain frozen retries;
independent approval never silently recalculates or publishes. Headline amounts
are explicitly subtotals and unknown contributions are unavailable, never zero.


[Shared instrument labels](../../architecture/security-master/instrument-display.md)
use `InstrumentLabel` and the display sidecars on valuation, holdings, measure
rows, trade history/detail headings, catalogue and booking search. Use the shared
listing-anchor helper; do not put current labels inside frozen booking terms.

[Page-specific contextual help](../../delivery/page-contextual-help-20261017.md)
adds a native **How to use this page** disclosure to complex workflows. Curated
`page-guides.ts` content explains purpose, steps, terms and workflow impact;
`PageHelp` is presentation only. Keep required hints/warnings inline and update
the relevant guide with domain behavior changes. No modal, fetch or form submission
is involved in opening help.

[October 17 visual consistency review](../../delivery/quality-reviews/2026-10-17-frontend-visual-consistency.md)
records the project-wide source inventory, shared native/MUI tokens, bounded
control/table fixes, policy task tabs, structured-product section navigation and
shell skip link. Use `workspace-presentation.ts`, `workspace-theme.ts` and
`native-workspace.css` for shared defaults; preserve feature variants. Keep policy
panels mounted and permission/evidence behavior server-owned. This is bounded
visual/browser verification, not universal live-page or assistive sign-off.

[October 16 shared remediation and acceptance](../../delivery/quality-reviews/2026-10-16-frontend-remediation.md)
records the document-bound BFF transport, retained mutation/recovery protocol,
exact formatting, register states, correction navigation and display-only currency
reuse. Browser checks run with `pnpm --filter ops-console test:browser` against
isolated synthetic servers; operating financial data is not used.

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

October 16 adds ten isolated browser cases, including real DOM focus, mobile-sized navigation and the actual valuation staging/publication component. Component/HTTP tests, typechecks and a production build alone are not browser acceptance; the bounded browser suite is not universal visual or screen-reader conformance. See [frontend remaining acceptance](../../product/features/platform-quality.md#f49-frontend-acceptance), [style review](../../delivery/frontend-style-review-2026-10-08.md) and [trade walkthrough evidence](../../delivery/trade-side-acceptance-2026-10-06.md).

[Operations Console run guide](../../../apps/ops-console/README.md) describes runtime entry points. The [ui workstream](../../../ui/README.md), screen specs and decisions are retained design history; use the [feature register](../../product/feature-register.md) for actual implementation status. Any explicit synthetic fallback is local and route-specific, not a universal substitute for authorized live data.
