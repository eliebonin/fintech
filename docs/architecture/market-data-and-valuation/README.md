# Market data and valuation

31 October: [Incomplete-price review and independently reviewed marks](../../delivery/incomplete-price-review-20261031.md)
retains unknown investment/cash FX contributions, calculated subtotals and a
required-mark publication gate. Optional assessed interest/cash snapshots remain
separate nonblocking omissions; no price/FX substitute is invented.


29 October: [Compact review and dual-currency accrued stocks](../../delivery/valuation-review-signals-20261029.md)
use retained coverage/FX with independent availability. Partial inputs stay
discoverable and nonblocking; publication blockers remain separate.

28 October: [Bond DIRTY-to-CLEAN quotations](../../delivery/bond-dirty-to-clean-20261028.md)
pair per-100 accrued with the exact source observation. Daily P&L consumes
derived CLEAN; strategy earned interest/stock FX and full DIRTY monetary values
remain distinct. No interest generator or public upload workflow is added.

28 October: [Linear crypto futures](../../delivery/linear-futures-extension-20261028.md)
reuse exact-contract daily variation for cash and physical settlement. Actual
delivery and margin accounting stay separate. [3 November monetary previews](../../delivery/expanded-position-measures-20261103.md) separately add current linear crypto notionals/exposure.

28 October: [Quoted wrappers and spot crypto](../../delivery/etp-spot-crypto-pnl-20261028.md)
use native security/token prices with frozen factors and trade-quote FX. Crypto
pricing days require explicit assessed calendar coverage; venue prices and
stablecoin quotation currencies are not silently interchangeable.

28 October: [Supplied whole-note P&L](../../delivery/structured-note-pnl-20261028.md)
extends the common security bridge with explicit note quotation/interest handling.
Payoff pricing and note lifecycle automation remain deferred.

Publication authority follow-up (14 October 2026): [controlled self-publication](../../delivery/valuation-self-publication-20261014.md)
is an explicit default-off tenant/strategy-scoped continuity exception. Independent
review remains the default; real-operator provenance, amendment independence and
financial validation remain enforced. This does not add full NAV capability.

**Status:** Accepted current alpha boundary  
**Content type:** Architecture index  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-10-13

Start with [market-data capabilities](../../product/features/market-data.md) and [valuation/P&L capabilities](../../product/features/valuation-and-pnl.md). These distinguish code delivery from source/financial/visual acceptance. Older single-currency TRADE-alpha checkpoints are history, not current supported scope.

## Implemented data path

Provider adapters and operator entry points acquire retained source payloads outside API request handling. Provider-neutral rights/publication live in `market_data`; the API inspects stored series and evidence. Jobs/attempts retain retries, partial/failure outcomes and recovery evidence. No scalable scheduled worker service is claimed.

Provider, product, dataset and coverage package are distinct. Layered activity rights, tenant/purpose grants and exact series coverage govern use/disclosure. Platform/tenant source priority ranks eligible datasets only. Personal Yahoo declarations/research exceptions do not establish commercial rights. General tenant upload and periodic entitlement recertification are not delivered workflows.

Source series retain price basis. CLOSE is the common closing-price family; exchange-official designation is an optional separate requirement. RAW/as-traded compatibility is an economic requirement, not arbitrary relabelling. Yahoo derived RAW closes append split-only price reconstruction with anchored source/action proof, leaving split-adjusted and vendor-adjusted values intact. This price pipeline does not transform holdings or generate dividend income; reviewed position-ratio replay is a separate `positions` responsibility.

## Policies, calendars and dates

STRICT uses explicit rules. FLEXIBLE uses explicit rules first, configured defaults only when none match. A matched rule with missing/ineligible data fails; priority cannot substitute a different fixing or bypass rights/basis/freshness. Session close follows the relevant exchange schedule; FX cuts and fund NAV calendars are independent. Policy valuation context is not one universal closing hour.

Tenant fund/strategy calendars have separately purposed, published schedules, composite rules and evidenced dated exceptions. Closed, open and UNKNOWN are different. Recorded-time pinned assignments preserve history. Fund NAV economically belonging to T may only be available on T+1; requested/used NAV date, lag and publication/information cutoff remain explicit.

The explorer exposes stored data, lineage and coverage. Eligibility diagnostics are not a complete independently reviewed pre-valuation price-validation workflow. Timed Yahoo research samples are not benchmark fixings, and missing historical bars remain missing.

## Current valuation path

The [maintained methodology matrix](valuation-methodology.md) defines the supported
daily bridge, product/lifecycle cases, source-backed rationale, numerical regressions
and current limits. [October 14 assurance](../../delivery/valuation-methodology-assurance-20261014.md)
completes the calculation/position explanation path without changing financial formulas.

October 14 follow-up: [applied decisions and dated cash snapshots](../../delivery/valuation-rules-and-cash-snapshots-20261014.md)
documents the supported-product methodology matrix. New staged position evidence
retains versioned readable applied rules under its result hash; old results are not
rewritten. The separate cash register translates exact-date uploaded balances at
policy-selected FX. That preview is not investment P&L, persisted staging or full NAV.

`positions` reads tenant/strategy ledger history in keyset chunks without a total 1,000-trade cap, then reconstructs compatible opening/closing positions and period executions. Only nonzero boundaries need marks; execution-only round trips retain P&L. Historical facts and financial ownership lineage remain distinct.

`valuation` uses `economic-position-pnl-v3`: supported equity/ETF, native fund NAV, AMC and clean-bond economics; governed direct/explicit inverse FX; supplied whole-swap marks, listed-option premiums and bounded FX-forward rate differences. [Cash-settled index-futures P&L](../../delivery/futures-daily-pnl-20261027.md) adds price variation with the frozen multiplier once and economic-day closing FX, without treating notional as a NAV asset. Reviewed basic share ratios transform holdings while retaining original trades and immutable source/decision evidence. Price/FX/cross, supplied daily interest, available accrued-stock FX, cash FX and explicit income/costs reconcile to market/gross/net totals. Plain bond and deliverable-forward maturity have recorded closure paths. Unsupported products/actions and missing required marks fail closed; missing optional interest/cash stocks are disclosed without assuming zero. Full fund NAV, universal derivative pricing, broader lifecycle, income entitlement and complex corporate transformations remain separate work. See the [current methodology matrix](valuation-methodology.md).

Calculation stages immutable candidates. Source corrections require recalculation; controlled component amendments produce replacement candidates. Independent approval/publication checks real operator ancestry, current disclosure rights, selected versions, totals and stale inputs/populations. Financial input and review history are not overwritten. Operational logs survive failed calculation; readable diagnostics and JSON coexist.

## Current evidence and remaining work

- [Economic delivery and latest operator-authority fixes](../../delivery/economic-pnl-implementation-2026-10-09.md).
- [Position foundation and scaling limits](../../delivery/position-reconstruction-foundation.md).
- [Reviewed share-ratio replay, migration86 and local Air Liquide acceptance](../../delivery/share-ratio-position-replay-20261013.md).
- [Flexible policies](../../delivery/flexible-pricing-policies.md), [tenant calendars](../../delivery/tenant-fund-and-strategy-calendars-alpha.md).
- [Derived RAW Yahoo activation](../../delivery/yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09), [GBP FX coverage/sampling limits](../../delivery/yahoo-gbp-fx-backfill.md).
- [Scoped licences](../../delivery/scoped-dataset-entitlements.md), [source catalogue/ranking](../../delivery/market-data-sources-ui.md).
- [Attribution ownership: current position owner versus broader future subjects](pnl-attribution-subjects.md).
- [Merge verification scope](../../delivery/tenant-access-administration-progress.md#completed-remediation-verification).

Earlier migration/activation history remains in its dated deliveries. The October13 share-ratio delivery records local migration86, restart and API staging acceptance separately from component/disposable-DB tests. A new browser walkthrough, independent financial reconciliation, complete price validation, production scalability and commercial source qualification remain outstanding.

## Historical foundations

[Series measurement semantics](series-measurement-semantics.md), [market data/trade concepts](../../../security-master-notes/03-market-data-marks-and-trades.md), [corporate-action discussion](../../../security-master-notes/10-corporate-actions-and-adjusted-market-data.md), [indicative Soft-NAV](../../../security-master-notes/17-soft-nav-pricing-date-resolution.md). These explain intent; they do not expand current engine support.
