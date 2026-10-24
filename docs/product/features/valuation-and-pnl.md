# Valuation and P&L — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-23 (scoped supplied swap-mark and option-premium P&L follow-up)

[Feature register](../feature-register.md). Current engine is `economic-position-pnl-v3`; historical trade-owned/market-only methods remain readable, not a second live fallback calculator. The retired homepage P&L demo is not capability evidence.

October 14 assurance: [methodology/edge-case matrix](../../architecture/market-data-and-valuation/valuation-methodology.md)
links supported economics to hand-calculated regressions and explicitly distinguishes
source availability, price/FX dates, maturity, income, accrued stocks and cash previews.
[Delivery evidence](../../delivery/valuation-methodology-assurance-20261014.md): 64 pure
and 63 focused disposable-DB tests; missing calculation-level accrual rules fixed,
new staged value-bridge/clean-bond explanations added. No broader valuation readiness
or independent financial reconciliation implied.

## F36 Position reconstruction

- **Desired:** Select economically relevant holdings and period executions from immutable trades, not an arbitrary recent-trade cap.
- **Status / backend / frontend:** ALPHA. `positions/` scopes tenant/strategy/economic/information dates, reads 500-trade keyset chunks with **no total 1,000-trade cap**, reconstructs compatible buckets and retains ledger lineage; UI presents position-owned results and underlying trade links.
- **Cuts/trade-offs:** Net only compatible subject/unit/currency/frozen conventions. Flat-before-opening histories produce no financial lines; period round trips retain execution P&L even without boundary marks. Original trades are not rewritten. Reviewed basic equity/ETF share ratios replay into derived holdings with immutable source/approval evidence; unreviewed/complex transformations and unresolved fractions remain blocked.
- **Weaknesses:** History I/O/materialization grows; unsupported corporate transformations and later-effective in-period termination semantics can block. Historical record corrections at original execution are supported with explicit lineage. No lot accounting or automatic cross-listing netting.
- **Remaining:** Broader entitlement/complex-action replay and economic termination semantics, action-review UI, batched large-universe action queries, versioned checkpoints with backdated/information-cut invalidation, asynchronous jobs and representative benchmarks.
- **Evidence:** [Foundation/scaling](../../delivery/position-reconstruction-foundation.md), [reviewed share-ratio delivery and live acceptance](../../delivery/share-ratio-position-replay-20261013.md), [repository](../../../positions/repository.py), [reconstruction](../../../positions/reconstruction.py).

## F37 Economic valuation

External CSV preparation and local source activation are
[optional tooling](../../../tooling/reconciliation_csv/README.md), not part of
this calculation engine or its supported upload contracts. Valuation and its
native regression tests do not depend on that tooling.

October 16 [query-efficiency delivery](../../delivery/quality-reviews/2026-10-16-query-efficiency.md)
batches retained forward proof/holdings reads and history projections, constrains
price candidates to matching series and reuses stable runner inputs. No financial
formula, history cap or authorization shortcut was introduced. Full-history and
concurrent-load scaling remain partial; see the measured boundaries in that report.

October 16 [backend follow-up](../../delivery/quality-reviews/2026-10-16-backend-remediation.md)
adds coherent monetary-preview inputs with fresh current-access release checks,
measured transaction-local resolver reuse, and scoped paged policy/strategy/currency
selectors. Calculation audit records acceptance separately from completion. No
financial formula, published result or operating source rights were changed.
Large-history and representative concurrent latency remain unverified.

October 15 [Position values & exposure UI](../../delivery/position-values-report-ui-20261015.md)
reworks the existing Measures tab into a grouped compact report with local/strategy
display, backend-classified availability and readable selected-input inspection.
Populated-data review adds two-decimal scan formatting with exact values retained,
and a keyboard-operable full-width inspector that does not stretch the table.
No combined NAV total, weights, settlement or additional derivative pricing is
introduced. Verification and activation limits are retained in its delivery record.

October 15 [deliverable-forward monetary preview](../../delivery/fx-forward-position-measures-20261015.md)
adds signed base reference notional and separately translated contractual currency
legs. These are undiscounted obligations, not delta or true MTM; discounted market
value stays unavailable. Mixed agreements are exceptions even when base quantity
nets to zero. [Cross-product review](../../delivery/quality-reviews/2026-10-15-position-measures-review.md)
records definitions, remaining coverage/performance gaps and verification boundaries.

October 15: [separate monetary-measure preview](../../delivery/position-monetary-measures-20261015.md)
adds a strategy Measures tab and scoped calculation endpoint, without weights or
P&L/publication changes. Cash securities use equal three-measure amounts; bonds
prefer eligible dirty price then clean plus assessed balance; native index swaps
separate reference notional, underlying-equivalent exposure and whole-swap MTM.
Missing inputs remain unavailable. This is not stored/published valuation, an
interim reset engine, autocall/option support or full risk readiness.

October 15 [futures monetary exposure](../../delivery/future-position-measures-20261015.md)
extends the preview to frozen linear cash-settled index contracts. Reference
notional/exposure use the exact dated futures price and monetary multiplier once,
with local and fund-currency amounts. Contract MTM remains unavailable without
clearing/variation-margin evidence. No futures P&L, margin or delivery is enabled.

The subsequent [readiness check and remediation](../../delivery/position-monetary-measures-20261015.md#remediation-and-local-acceptance)
reproduced and fixed the split-mark safety and fund-share-class recognition gaps.
Canonical/listed funds now use frozen NAV identity; stale pre-action RAW marks
cannot multiply post-action quantities. A separate mock strategy policy and owned
synthetic index histories give all three native/GBP measures for 11 positions on
2026-10-08. Earlier USD/GBP dates are not granted by this setup. Existing P&L and
publication scope is unchanged; this is not derivative P&L or external acceptance.

- **Desired:** Position price/FX/cross P&L using selected T/T−1 marks, dates/evidence and actual execution prices; fund NAV availability and bond quotation semantics explicit.
- **Status / backend / frontend:** PARTIAL. Supported equity/ETF, native fund NAV, clean-bond, deliverable FX-forward rate-difference, supplied whole-swap marks and listed-option premiums, direct governed FX and explicitly permitted inverse FX; `/valuation` calculation/evidence/results. Other derivatives and cash-balance stock valuation remain excluded. [Swap extension](../../delivery/swap-supplied-mark-pnl-20261023.md) retains signed units/nominal and divisor once. [Option extension](../../delivery/option-premium-pnl-20261023.md) applies frozen premium multiplier once to actual contract counts; no underlying-price substitution, model price, automatic expiry or extra leverage multiplication.
- **Cuts/trade-offs:** FX translates trade-price currency to reporting/strategy currency, with no silent triangulation. Same-day execution price enters the execution bridge; it does not overwrite a whole existing position's opening market mark. Fund NAV for T remains economically T when signed off T+1; availability/explicit lag decide what may be used at calculation time.
- **FX boundary:** Foreign conversion requires RAW FX_RATE semantics, a NAMED_FIXING or EXPLICIT_TIME rule, a sealed governed session calendar and an explicit maximum staleness. A daily FX bar alone is insufficient. A direct pair with an active qualifying FX series is chosen first; an inverse pair is considered only when no such direct pair is found and its selected rule permits inversion. Missing observations on an existing qualifying direct pair block conversion rather than falling back to the inverse.
- **Weaknesses:** No future/structured valuation, modelled option pricing/Greeks/exercise, modelled swap pricing/funding or discounted FX-forward model MTM. [Rate-based FX-forward P&L](../../delivery/fx-forward-rate-pnl-20261014.md) requires contract-specific outright-rate data, not spot substitutes; net values are explicitly undiscounted rate differences. [Booked plain-bond principal maturity](../../delivery/plain-bond-redemption-20261014.md) closes exposure; unsupported maturity and missing final-interest coverage still block. Financial/user acceptance is separate from tests.
- **Remaining:** Accept realistic multi-currency/fund/bond cases with provider reconciliation; product-specific pricing/final marks, documented FX methodology and reviewed source availability. Never infer DF=1 or transform rate into MTM without contract semantics.
- **Evidence:** [Economic delivery](../../delivery/economic-pnl-implementation-2026-10-09.md), [input capability guards](../../../valuation/product_inputs.py), [position bridge](../../../valuation/position_calculation.py), [FX](../../../valuation/fx.py).

FX-forward [bounded end-to-end acceptance](../../delivery/fx-forward-e2e-acceptance-20261014.md)
passed normal browser maturity/calculation and independent publication. The later
[correction/reassessment delivery](../../delivery/trade-corrections-valuation-reassessment-20261014.md)
also verifies historical maturity cancellation/rebooking, restored exposure and a
15,000 USD replacement result. Later-effective economic termination still blocks.

## F38 Accruals and economic flows

23 October: [optional daily-accrual coverage](../../delivery/optional-bond-accruals-20261023.md)
includes supplied valid daily interest and discloses missing bond/date inputs,
without assuming zero or blocking price/FX P&L. `requireCompleteAccruals` opts into
complete coverage. Results show an omission warning; staging retains missing dates
and publication refuses inputs supplied since staging. No automatic coupon or
discount-accretion model or retrospective evidence change.

October 14 follow-up: [typed daily-interest columns](../../delivery/typed-daily-interest-20261014.md)
make date/bond/daily earnings/currency explicit under tenant/strategy scope.
Daily-only inputs are accepted; balances/movements remain optional reconciled
evidence. Missing accrued stock/receivable FX is unassessed, not zero. Revision,
precision and current-source publication safeguards remain.

- **Desired:** Separate market movement from dividends, resets, coupons, fees and **daily added** bond interest; retain daily earnings and accumulated balance in local/reporting currency.
  October 15: [coupon schedules and payment evidence](../../delivery/bond-coupons-20261015.md) adds tenant-owned sourced periods and strategy receipt/correction/reversal history. These are not additional earnings; daily-interest valuation is unchanged. Migration 94/API activated with approval; browser acceptance remains pending.
- **Status / backend / frontend:** PARTIAL. Append-only assessed daily bond inputs plus typed economic-flow trades; input registers/forms and component/evidence displays. Opening balance + earnings + movements reconciles to closing balance; ACCRUAL includes daily earnings only.
- **Cuts/trade-offs:** Position-level canonical daily inputs allocated once, not duplicated per listing/trade. Operators choose INCOME versus PAYMENT_ONLY; coupon payment is not earned interest again. Cash-flow trades are explicit actual economics, not fabricated investment holdings.
- **Weaknesses:** No automated bond accrual generation, full unbooked income coverage, dividend entitlement engine or automatic swap-reset/mark reconciliation. Operators still own classification correctness; arithmetic checks cannot certify economic completeness.
- **Remaining:** Reviewed calculation/import of interest, coupon/dividend/reset linkage and reconciliation, richer input challenge; broader maturity economics before claiming complete bond P&L. Plain-bond principal closure does not replace final-day interest inputs.
- **Evidence:** [Agreed foundation](../../delivery/economic-pnl-agreed-foundation-2026-10-09.md), [accrual checks](../../../valuation/accruals.py), [economic-flow ledger](../../../valuation/flows.py), [delivery](../../delivery/economic-pnl-implementation-2026-10-09.md).

## F39 Review and publication

October 14 correction follow-up: [ledger impact and explicit reassessment](../../delivery/trade-corrections-valuation-reassessment-20261014.md)
retains published figures, separates source health from publication state, blocks
stale staged publication and creates explicitly requested staged successors.
Migration 92 is locally applied and the API restarted with approval. Impact selection is conservative;
new-cutoff data and previously applied amendments require renewed review.

October 14 continuity follow-up: [controlled self-publication](../../delivery/valuation-self-publication-20261014.md)
adds default-disabled tenant opt-in, optional tenant-level expiry and explicit
strategy-scoped `VALUATION_SELF_PUBLISH` alongside review permission. Actual and
selected operator authority is checked; reasons and the self-reviewed publication
mode are retained. Only final publication independence can be waived through this
explicit route; amendment independence and financial checks are unchanged.

October 14: [strategy/date-filtered Results and operational History](../../delivery/valuation-results-history-report-20261014.md)
replace implicit latest-result loading with explicit browsing, add server-side
filter/count pagination, read-aware strategy choices and actual calculation plus
publication labels. Headline financial amounts retain current DISPLAY guards.
An obvious Publish valuation action on staged detail opens a required-comment
confirmation; independent-review and server publication checks remain unchanged.

October 13: [explicit storage rounding](../../delivery/valuation-storage-rounding-20261013.md)
rounds calculated components half-even to twelve decimals at staging, derives
reconciled stored totals and retains exact arithmetic plus rounding deltas.
Publication verifies the rounding bridge; manual amendments remain precision-strict.

October 13 UI follow-up: [review workspace](../../delivery/valuation-review-workspace-20261013.md)
adds position-table/inspector presentation, readable totals, optional amendment
sidebar and progressive evidence disclosure. Its three-tab follow-up separates
Input form, Results and History, preserves drafts/retries, and shows recorded run
context beside the results. Existing BFF/backend authority and
publication checks are unchanged; this is not financial sign-off or per-trade allocation.

- **Desired:** Calculate/stage, amend with evidence, independently approve and publish versioned official results with operational logs; preserve each financial result's values and evidence.
- **Status / backend / frontend:** ALPHA. Immutable attribution versions and append-only run/review events; attempt and batch status fields transition through the workflow, including a published batch becoming `SUPERSEDED` when a replacement is published. Pending/stale/applied/rejected amendments and reconciled publication; `/valuation` Input/Results/History with server-filtered reports, readable failures plus JSON, dual calculation/publication states and action-aware controls.
- **Cuts/trade-offs:** A later publication supersedes the prior batch by changing its status, not by rewriting its stored values or attribution evidence. Market/FX/accrual corrections require upstream source correction/recalculation; approved component deltas create replacement candidates. Pending requests block publication. Request keys and review lineage retain the real operator, not only selected identity. Self-publication is default off; optional expiry applies to tenant opt-in, not per-user membership. No implicit admin grants or retrospective independent-attestation workflow.
- **Weaknesses:** Legacy operator evidence can be incomplete; production supplemental audit transport and asynchronous recovery need hardening. Broader strategy/fund/share-class attribution ownership and independent external comparison remain unimplemented.
- **Remaining:** Financial/browser sign-off, independent comparison, production recovery/audit operations and typed broader ownership. No self-review by selecting another user; incomplete historical operator lineage fails conservatively.
- **Evidence:** [Current review corrections](../../delivery/economic-pnl-implementation-2026-10-09.md#review-authority-corrections--12-october-2026), [operator checks](../../../valuation/review_authority.py), [publication](../../../valuation/storage.py), [ownership direction](../../architecture/market-data-and-valuation/pnl-attribution-subjects.md).

## F40 Full NAV and cash balances

October 14 audit follow-up: [applied valuation decisions and methodology matrix](../../delivery/valuation-rules-and-cash-snapshots-20261014.md)
adds stable versioned explanations to new immutable position evidence, including
booked execution cost, independent fund NAV/FX dates, normalized mark values,
same-currency identity, reviewed quantity ratios and income versus payment-only
flows. This supplements F37–F39; old evidence is not reconstructed in the browser.

- **Desired:** Upload strategy/company/account/currency EoD balance snapshots valid only on their value date, translate with governed FX, and eventually calculate complete fund/strategy NAV including liabilities/fees/income.
- **Status / backend / frontend:** PARTIAL. Separate `trd.cash_account` / `cash_balance` register, manual entry/CSV uploads, append-only corrections, optional notes, revision history and policy-backed cash-value preview at `/valuation/cash-balances`. Migration 89 is active and the API restarted; read-only browser navigation/strategy/empty-state acceptance passed. Full NAV remains deferred.
- **Cuts/trade-offs:** No daily unwind, carry-forward or trade-generated cash. A correction requires current revision and a separate reason. Preview values retain selected FX and balance revisions in the response with an input hash; they are not persisted staged/published batches and never added to trading P&L. Exact-date zero is explicit. Coverage is checked against previously uploaded account/currency scopes, not independently verified complete bank/custody inventory.
- **Weaknesses:** No movement-based cash P&L, statement parsing/automatic reconciliation, account closure workflow or complete balance/obligation/liability allocation. Register reads are date-specific but not paginated; uploads are bounded to 500 rows / frontend CSV 1 MB. Companies must already exist in the organisation catalogue. Crypto balances can be recorded but translation still requires supported governed FX evidence; no crypto price or triangulation is invented.
- **Remaining:** Populated-account/upload/correction browser acceptance, independently complete balance coverage, durable cash valuation staging/publication, movement reconciliation and full fund NAV. Do not relabel cash-value changes or market/gross/net trading P&L as complete NAV.
- **Evidence:** [Delivery and methodology matrix](../../delivery/valuation-rules-and-cash-snapshots-20261014.md), [snapshot service](../../../valuation/cash_snapshots.py), [cash API](../../../apps/reference_api/cash_snapshot_routes.py), [focused API checks](../../../tests/test_cash_snapshot_api.py).

## F57 Valuation purpose and descriptive tags

- **Desired:** Distinguish a run's controlled purpose (daily operations, intraday monitoring, reconciliation or what-if), calculation scope and timing from optional tenant-curated descriptive tags such as month-end or investment committee.
- **Origin:** Discussed 14 October 2026; user explicitly parked the idea to prioritize valuation UI readability and navigation. This is a deferred direction, not an approved implementation specification.
- **Status / backend / frontend:** DEFERRED. Existing engine scope and staging/publication statuses are implemented; purpose-specific result lanes and tenant-curated run tags are not.
- **Cuts/trade-offs:** Tags must not confer publication authority, change calculation economics or relabel economic P&L as full NAV. Scope must describe actual calculated coverage. A published internal indicative estimate is not automatically the fund's official dealing NAV. Intraday labels alone do not enable intraday pricing.
- **Weaknesses:** Current candidate replacement and publication supersession are scoped by tenant, strategy and value date, not independent purposes; merely attaching tags would not prevent a what-if or intraday candidate from displacing the daily operational result.
- **Remaining:** When resumed, define the minimal purpose vocabulary, publication/replacement boundaries, retained purpose evidence, allowed descriptive tags and reporting filters. No additional NAV or live-price engine is authorized by this note.
- **Evidence / related capabilities:** [Current stage/publication behavior](../../../valuation/storage.py), [review workflow](#f39-review-and-publication), [full NAV boundary](#f40-full-nav-and-cash-balances). Terminology references checked 14 October 2026: [SEC indicative intraday value versus NAV](https://content.govdelivery.com/accounts/USSEC/bulletins/4de0c2) and [ESMA UCITS Article 85](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/ucits/article-85). These support distinguishing indicative values and governed NAV; the proposed field structure is a project choice, not a prescribed industry schema.
