# Market data and valuation

**Status:** Accepted current alpha boundary  
**Content type:** Architecture index  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-10-12

Start with [market-data capabilities](../../product/features/market-data.md) and [valuation/P&L capabilities](../../product/features/valuation-and-pnl.md). These distinguish code delivery from source/financial/visual acceptance. Older single-currency TRADE-alpha checkpoints are history, not current supported scope.

## Implemented data path

Provider adapters and operator entry points acquire retained source payloads outside API request handling. Provider-neutral rights/publication live in `market_data`; the API inspects stored series and evidence. Jobs/attempts retain retries, partial/failure outcomes and recovery evidence. No scalable scheduled worker service is claimed.

Provider, product, dataset and coverage package are distinct. Layered activity rights, tenant/purpose grants and exact series coverage govern use/disclosure. Platform/tenant source priority ranks eligible datasets only. Personal Yahoo declarations/research exceptions do not establish commercial rights. General tenant upload and periodic entitlement recertification are not delivered workflows.

Source series retain price basis. CLOSE is the common closing-price family; exchange-official designation is an optional separate requirement. RAW/as-traded compatibility is an economic requirement, not arbitrary relabelling. Yahoo derived RAW closes append split-only reconstruction with anchored source/action proof, leaving split-adjusted and vendor-adjusted values intact. This does not replay position quantities or generate dividend income.

## Policies, calendars and dates

STRICT uses explicit rules. FLEXIBLE uses explicit rules first, configured defaults only when none match. A matched rule with missing/ineligible data fails; priority cannot substitute a different fixing or bypass rights/basis/freshness. Session close follows the relevant exchange schedule; FX cuts and fund NAV calendars are independent. Policy valuation context is not one universal closing hour.

Tenant fund/strategy calendars have separately purposed, published schedules, composite rules and evidenced dated exceptions. Closed, open and UNKNOWN are different. Recorded-time pinned assignments preserve history. Fund NAV economically belonging to T may only be available on T+1; requested/used NAV date, lag and publication/information cutoff remain explicit.

The explorer exposes stored data, lineage and coverage. Eligibility diagnostics are not a complete independently reviewed pre-valuation price-validation workflow. Timed Yahoo research samples are not benchmark fixings, and missing historical bars remain missing.

## Current valuation path

`positions` reads tenant/strategy ledger history in keyset chunks without a total 1,000-trade cap, then reconstructs compatible opening/closing positions and period executions. Only nonzero boundaries need marks; execution-only round trips retain P&L. Historical facts and financial ownership lineage remain distinct.

`valuation` uses `economic-position-pnl-v3`: supported equity/ETF, native fund NAV and clean-bond economics; governed direct/explicit inverse FX; assessed daily bond interest and explicitly booked economic flows. Price/FX/cross, daily accrual and signed income/cost components reconcile to market/gross/net totals. Cash stock, derivative/final-maturity valuation, full NAV and automatic corporate-action quantity replay remain excluded. Unsupported transformations fail closed rather than inventing prices or exposure.

Calculation stages immutable candidates. Source corrections require recalculation; controlled component amendments produce replacement candidates. Independent approval/publication checks real operator ancestry, current disclosure rights, selected versions, totals and stale inputs/populations. Financial input and review history are not overwritten. Operational logs survive failed calculation; readable diagnostics and JSON coexist.

## Current evidence and remaining work

- [Economic delivery and latest operator-authority fixes](../../delivery/economic-pnl-implementation-2026-10-09.md).
- [Position foundation and scaling limits](../../delivery/position-reconstruction-foundation.md).
- [Flexible policies](../../delivery/flexible-pricing-policies.md), [tenant calendars](../../delivery/tenant-fund-and-strategy-calendars-alpha.md).
- [Derived RAW Yahoo activation](../../delivery/yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09), [GBP FX coverage/sampling limits](../../delivery/yahoo-gbp-fx-backfill.md).
- [Scoped licences](../../delivery/scoped-dataset-entitlements.md), [source catalogue/ranking](../../delivery/market-data-sources-ui.md).
- [Attribution ownership: current position owner versus broader future subjects](pnl-attribution-subjects.md).
- [Merge verification scope](../../delivery/tenant-access-administration-progress.md#completed-remediation-verification).

Local migrations through 83 and prior app activation are recorded in delivery history; this documentation review did not query current live state, migrate or restart. Latest browser/financial acceptance, complete price validation, production scalability and commercial source qualification remain outstanding.

## Historical foundations

[Series measurement semantics](series-measurement-semantics.md), [market data/trade concepts](../../../security-master-notes/03-market-data-marks-and-trades.md), [corporate-action discussion](../../../security-master-notes/10-corporate-actions-and-adjusted-market-data.md), [indicative Soft-NAV](../../../security-master-notes/17-soft-nav-pricing-date-resolution.md). These explain intent; they do not expand current engine support.
