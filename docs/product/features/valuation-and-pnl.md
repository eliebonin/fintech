# Valuation and P&L — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). Current engine is `economic-position-pnl-v3`; historical trade-owned/market-only methods remain readable, not a second live fallback calculator. The retired homepage P&L demo is not capability evidence.

## F36 Position reconstruction

- **Desired:** Select economically relevant holdings and period executions from immutable trades, not an arbitrary recent-trade cap.
- **Status / backend / frontend:** ALPHA. `positions/` scopes tenant/strategy/economic/information dates, reads 500-trade keyset chunks with **no total 1,000-trade cap**, reconstructs compatible buckets and retains ledger lineage; UI presents position-owned results and underlying trade links.
- **Cuts/trade-offs:** Net only compatible subject/unit/currency/frozen conventions. Flat-before-opening histories produce no financial lines; period round trips retain execution P&L even without boundary marks. Original trades are not rewritten.
- **Weaknesses:** History I/O/materialization grows; unsupported corporate transformations and in-period correction semantics can block. No lot accounting or automatic cross-listing netting.
- **Remaining:** Governed replay and correction semantics, batched large-universe action queries, versioned checkpoints with backdated/information-cut invalidation, asynchronous jobs and representative benchmarks.
- **Evidence:** [Foundation/scaling](../../delivery/position-reconstruction-foundation.md), [repository](../../../positions/repository.py), [reconstruction](../../../positions/reconstruction.py).

## F37 Economic valuation

- **Desired:** Position price/FX/cross P&L using selected T/T−1 marks, dates/evidence and actual execution prices; fund NAV availability and bond quotation semantics explicit.
- **Status / backend / frontend:** PARTIAL. Supported equity/ETF, native fund NAV and clean-bond economics, direct governed FX and explicitly permitted inverse FX; `/valuation` calculation/evidence/results. No derivative or cash-balance stock valuation.
- **Cuts/trade-offs:** FX translates trade-price currency to reporting/strategy currency, with no silent triangulation. Same-day execution price enters the execution bridge; it does not overwrite a whole existing position's opening market mark. Fund NAV for T remains economically T when signed off T+1; availability/explicit lag decide what may be used at calculation time.
- **FX boundary:** Foreign conversion requires RAW FX_RATE semantics, a NAMED_FIXING or EXPLICIT_TIME rule, a sealed governed session calendar and an explicit maximum staleness. A daily FX bar alone is insufficient. A direct pair with an active qualifying FX series is chosen first; an inverse pair is considered only when no such direct pair is found and its selected rule permits inversion. Missing observations on an existing qualifying direct pair block conversion rather than falling back to the inverse.
- **Weaknesses:** No option/future/swap/structured/FX-forward valuation or supported bond maturity/final-mark handler. Fund native unit proof and price-basis/calendar/rights readiness remain mandatory. Financial/user acceptance is separate from tests.
- **Remaining:** Accept realistic multi-currency/fund/bond cases with provider reconciliation; product-specific pricing/final marks, documented FX methodology and reviewed source availability. Never infer DF=1 or transform rate into MTM without contract semantics.
- **Evidence:** [Economic delivery](../../delivery/economic-pnl-implementation-2026-10-09.md), [input capability guards](../../../valuation/product_inputs.py), [position bridge](../../../valuation/position_calculation.py), [FX](../../../valuation/fx.py).

## F38 Accruals and economic flows

- **Desired:** Separate market movement from dividends, resets, coupons, fees and **daily added** bond interest; retain daily earnings and accumulated balance in local/reporting currency.
- **Status / backend / frontend:** PARTIAL. Append-only assessed daily bond inputs plus typed economic-flow trades; input registers/forms and component/evidence displays. Opening balance + earnings + movements reconciles to closing balance; ACCRUAL includes daily earnings only.
- **Cuts/trade-offs:** Position-level canonical daily inputs allocated once, not duplicated per listing/trade. Operators choose INCOME versus PAYMENT_ONLY; coupon payment is not earned interest again. Cash-flow trades are explicit actual economics, not fabricated investment holdings.
- **Weaknesses:** No automated bond accrual generation, full unbooked income coverage, dividend entitlement engine or automatic swap-reset/mark reconciliation. Operators still own classification correctness; arithmetic checks cannot certify economic completeness.
- **Remaining:** Reviewed calculation/import of interest, coupon/dividend/reset linkage and reconciliation, richer input challenge; maturity handling before claiming complete bond P&L.
- **Evidence:** [Agreed foundation](../../delivery/economic-pnl-agreed-foundation-2026-10-09.md), [accrual checks](../../../valuation/accruals.py), [economic-flow ledger](../../../valuation/flows.py), [delivery](../../delivery/economic-pnl-implementation-2026-10-09.md).

## F39 Review and publication

- **Desired:** Calculate/stage, amend with evidence, independently approve and publish versioned official results with operational logs; preserve each financial result's values and evidence.
- **Status / backend / frontend:** ALPHA. Immutable attribution versions and append-only run/review events; attempt and batch status fields transition through the workflow, including a published batch becoming `SUPERSEDED` when a replacement is published. Pending/stale/applied/rejected amendments and reconciled publication; `/valuation` input/review workspaces with readable failures plus JSON and action-aware controls.
- **Cuts/trade-offs:** A later publication supersedes the prior batch by changing its status, not by rewriting its stored values or attribution evidence. Market/FX/accrual corrections require upstream source correction/recalculation; approved component deltas create replacement candidates. Pending requests block publication. Request keys and review lineage retain the real operator, not only selected identity.
- **Weaknesses:** Legacy operator evidence can be incomplete; production supplemental audit transport and asynchronous recovery need hardening. Broader strategy/fund/share-class attribution ownership and independent external comparison remain unimplemented.
- **Remaining:** Financial/browser sign-off, independent comparison, production recovery/audit operations and typed broader ownership. No self-review by selecting another user; incomplete historical operator lineage fails conservatively.
- **Evidence:** [Current review corrections](../../delivery/economic-pnl-implementation-2026-10-09.md#review-authority-corrections--12-october-2026), [operator checks](../../../valuation/review_authority.py), [publication](../../../valuation/storage.py), [ownership direction](../../architecture/market-data-and-valuation/pnl-attribution-subjects.md).

## F40 Full NAV and cash balances

- **Desired:** Eventually value cash stocks at native price one plus FX, and calculate complete fund/strategy NAV including liabilities/fees/income.
- **Status / backend / frontend:** DEFERRED. Cash/NAV snapshot schema and legacy indicative Soft-NAV foundations exist; current economic trading P&L excludes cash stock valuation/full NAV. No accepted full accounting/NAV UI.
- **Cuts/trade-offs:** Booking an economic payment does not establish a complete cash balance. A CASH helper capability alone is not an end-to-end position path: current repository accepts equity/ETF/fund/bond positions only.
- **Weaknesses:** Missing complete balance/obligation/reconciliation, liability/expense allocation and legal vehicle/share-class valuation workflows.
- **Remaining:** Scoped cash-position foundation, official balances, fund accounting/NAV and independent reconciliation after the user resumes that direction. Do not relabel market/gross/net trading P&L as full fund NAV.
- **Evidence:** [Explicit exclusions](../../delivery/economic-pnl-implementation-2026-10-09.md), [position support guard](../../../positions/repository.py), [earlier Soft-NAV model](../../../security-master-notes/17-soft-nav-pricing-date-resolution.md).
