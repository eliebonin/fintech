# Valuation and P&L — capability records

3 November F38/F39 follow-up: [trade markers](../../delivery/balance-trade-markers-20261103.md)
explain the balance history with an independent default-on Buy/Sell strip and
exact per-trade details. The marker date follows balance recognition; execution
and settlement dates remain distinct. TRADE_READ is additional to VALUATION_READ,
and failed annotation access does not block balance viewing. No financial changes.

3 November follow-up: [Explore balances](../../delivery/accrued-balance-explorer-20261103.md)
now delivers the deferred exploration below: strategy, instrument and date range,
full-range chart and paginated exact table. This is independent read-only access
to maintained canonical-bond history; no calculation or validation behavior changes.

3 November F38/F39: [two-stage interest review](../../delivery/interest-daily-review-20261103.md)
is the current maintenance UI: daily assessment → gated balance assessment for
one strategy/day. Drafts are separate from native financial inputs; bulk review
includes all rows. Explicit unknown-input acknowledgements yield **Reviewed with
gaps**, not zero. REVIEW authority is independent of RUN. Exploration remains
follow-up work; earlier three-tab descriptions are historical. Statuses remain
F38 PARTIAL/F39 ALPHA.

26 October F39: [shared instrument display](../../delivery/shared-instrument-display-20261026.md)
replaces bond-only ISIN decoration with a product-aware name/identifier/context
sidecar and shared renderer. Searches retain technical aliases, exact listing
links use the canonical listing anchor, and Instrument type is centred. Current
labels remain separate from frozen quantities, prices, FX and financial results.

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-11-01 (scoped balance-history viewer; prior broader review dated 27 October)

[Achieved versus intended review](../../delivery/quality-reviews/2026-10-27-valuation-state-review.md):
current scope, product matrix, database boundaries and prioritized remaining work.
Source-state CURRENT is bounded, and recorded totals do not certify full economic
coverage. The [29 October follow-up](../../delivery/valuation-review-signals-20261029.md)
resolves warning routing and reporting-stock display within retained coverage
and frozen FX availability; see FIX-VAL-005/006 in [reviewed findings](../../../FIX.md).

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

31 October: [Fund NAV correction](../../delivery/fund-nav-lag-20261031.md) pins
FCPGF to prior-valuation-session NAVs (T−1/T−2) and current FX (T/T−1). Existing
policy/calendar capability is reused; other product conventions stay unchanged.
The optional weekday baseline does not certify actual fund holidays or resolve
the separate inactive-import, accrued-stock and missing-observation findings.

31 October: [incomplete-price review](../../delivery/incomplete-price-review-20261031.md)
stages available positions with explicit unknown investment/cash FX contributions
under WARN/MANUAL_OVERRIDE rules. Headline amounts are calculated subtotals;
required marks or independently reviewed exact-input overrides plus a new
calculation are necessary before normal/self publication. Requests/decisions are
immutable and currently entitled, without provider-price fabrication. Optional
interest/cash snapshots remain nonblocking. This supplements F37/F39 without
claiming complete NAV or changing F37 PARTIAL / F39 ALPHA classifications.

30 October [rate-exchange swap P&L](../../delivery/rate-exchange-swaps-20261030.md)
reuses the frozen whole-component mark bridge for two-floating-leg contracts.
Separate instruments/time series produce separate staged attributions. It does
not derive marks from rate references, generate RESETs or enable rate-swap
monetary/risk previews. Existing publication and source-access controls apply.

30 October [fund-unit movements](../../delivery/fund-unit-movements-20261030.md)
use daily policy NAV/FX to exclude transferred/reinvested principal from market
P&L. Frozen movement proof preserves historical holdings and multi-day daily
bridges. Unconfirmed reinvestment income has a nonblocking occurrence-day
Attention/partial-completeness signal; no distribution amount is invented.
Intraday movement recognition and automatic income reconciliation remain absent.

28 October [plain-bond DIRTY normalization](../../delivery/bond-dirty-to-clean-20261028.md)
subtracts the matching source quoted accrued per 100 before the CLEAN price/FX
bridge. It preserves source DIRTY, settlement/market dates and cutoff-known proof;
independent daily earnings and accrued-stock FX are not counted twice. Missing
quote components block price determination; optional strategy interest remains
nonblocking. Monetary previews still consume original DIRTY. Staged normalized
inputs are revalidated before publication; broader source fanout is separate.

28 October [linear crypto futures](../../delivery/linear-futures-extension-20261028.md)
extend supplied-contract price variation to approved UNDERLYING_UNIT CASH/PHYSICAL
bookings. Actual contract basis, multiplier/divisor and quote-currency FX are
retained; source/calendar/authority and ordinary review apply. Delivery,
assignment, margin and crypto monetary-measure previews stay separate.

28 October [non-ETF wrappers and spot crypto](../../delivery/etp-spot-crypto-pnl-20261028.md)
extend supplied-price P&L with actual ETC/ETN/ETV/ETI/vehicle/certificate types and
DIGITAL_ASSET. The common value/FX/execution bridge uses frozen listing factors
once. Generic ETP is not an ETF alias. Crypto retains venue-specific subjects,
fractions, actual quote-currency FX and assessed pricing-day coverage, with no
stablecoin peg. Other futures-family models/options/bonds and token lifecycle remain deferred.

28 October [directly held structured notes](../../delivery/structured-note-pnl-20261028.md)
use the common security price/FX/execution bridge with frozen nominal/units,
denomination and quote divisor once. Supplied whole-note RAW marks explicitly
match CLEAN/DIRTY/NONE execution conventions. Zero marks and valid ordinary
closures are supported; underlying leverage is not reapplied. Payoff models,
automatic lifecycle/redemption and note monetary previews remain deferred.

27 October [futures daily P&L](../../delivery/futures-daily-pnl-20261027.md) adds
the existing cash-settled index slice: opening/closing and execution price
variation with the frozen multiplier/divisor once, economic-day closing FX and
ordinary staging/amendment/publication. Per-position asset values stay null;
batch asset reconciliation adds explicit futures variation. Margin cash and
monetary-preview contract MTM remain separate.

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
- **Status / backend / frontend:** PARTIAL. Supported equity/ETF, native fund NAV, AMC unit/percentage quotes, clean-bond, deliverable FX-forward rate-difference, supplied whole-swap marks, listed-option premiums and cash-settled index-futures variation, direct governed FX and explicitly permitted inverse FX; `/valuation` calculation/evidence/results. Other derivatives and cash-balance stock valuation remain excluded. [Swap extension](../../delivery/swap-supplied-mark-pnl-20261023.md) retains signed units/nominal and divisor once. [Option extension](../../delivery/option-premium-pnl-20261023.md) applies frozen premium multiplier once to actual contract counts; no underlying-price substitution, model price, automatic expiry or extra leverage multiplication.
- **Cuts/trade-offs:** FX translates trade-price currency to reporting/strategy currency, with no silent triangulation. Same-day execution price enters the execution bridge; it does not overwrite a whole existing position's opening market mark. Fund NAV for T remains economically T when signed off T+1; availability/explicit lag decide what may be used at calculation time.
- **FX boundary:** Foreign conversion requires RAW FX_RATE semantics, a NAMED_FIXING or EXPLICIT_TIME rule, a sealed governed session calendar and an explicit maximum staleness. A daily FX bar alone is insufficient. A direct pair with an active qualifying FX series is chosen first; an inverse pair is considered only when no such direct pair is found and its selected rule permits inversion. Missing observations on an existing qualifying direct pair block conversion rather than falling back to the inverse.
- **Weaknesses:** No physical/crypto futures valuation, modelled option pricing/Greeks/exercise, modelled swap pricing/funding or discounted FX-forward model MTM. Daily cash-settled index-futures price variation is supported; assessed futures contract MTM and margin accounting remain unavailable. [Rate-based FX-forward P&L](../../delivery/fx-forward-rate-pnl-20261014.md) requires contract-specific outright-rate data, not spot substitutes; net values are explicitly undiscounted rate differences. [Booked plain-bond principal maturity](../../delivery/plain-bond-redemption-20261014.md) closes exposure; unsupported maturity still blocks. Missing final-interest coverage is disclosed by default and blocks only when strict daily-interest coverage is explicitly requested. Financial/user acceptance is separate from tests.
- **Remaining:** Accept realistic multi-currency/fund/bond cases with provider reconciliation; product-specific pricing/final marks, documented FX methodology and reviewed source availability. Never infer DF=1 or transform rate into MTM without contract semantics.
- **Evidence:** [Economic delivery](../../delivery/economic-pnl-implementation-2026-10-09.md), [input capability guards](../../../valuation/product_inputs.py), [position bridge](../../../valuation/position_calculation.py), [FX](../../../valuation/fx.py).

FX-forward [bounded end-to-end acceptance](../../delivery/fx-forward-e2e-acceptance-20261014.md)
passed normal browser maturity/calculation and independent publication. The later
[correction/reassessment delivery](../../delivery/trade-corrections-valuation-reassessment-20261014.md)
also verifies historical maturity cancellation/rebooking, restored exposure and a
15,000 USD replacement result. Later-effective economic termination still blocks.

## F38 Accruals and economic flows

**Open investigation, not implemented:** fund share-class distribution/yield
accruals. [3 November source review](../../delivery/daily-accrual-csv-refresh-20261103.md#deferred-fund-distribution--yield-accruals)
retains three classes' CSV amounts without posting. Establish NAV inclusion,
recognition/currency and negative/reset/distribution semantics before choosing a
representation. Current daily-interest input eligibility remains bonds/notes.

1 November [Ops maintenance redesign](../../delivery/interest-ops-workspace-20261101.md)
gives daily interest, closing-balance inputs and accrued history distinct task tabs.
Applied filters, per-row corrections/withdrawals, independent loading and deliberate
rebuild replace the mixed maintenance/calculation display. Exact sources, detailed
reconciliation metadata, retained retries and strategy authority remain. The
per-row chart stays available; page-specific P&L navigation is removed. No financial
formula, coupon/accounting behavior or capability classification changes.
The balance overview is a To-date snapshot, one row per bond/currency; only its
chart shows the From-to-To history. Missing To-date stocks are not carried forward.

1 November [balance evolution viewer](../../delivery/accrued-balance-chart-20261101.md)
adds a read-only bond/date chart and exact table with 25/50/100/All pagination at
`/valuation/interest`. It reads the full selected series, displays missing/stale
amounts explicitly and remains available to scoped readers without run authority.
It does not implement the separately discussed schedule-driven coupon reset or
payment/accounting behavior. Existing PARTIAL/ALPHA scope remains.

31 October [maintained accrued balances](../../delivery/maintained-accrued-balances-20261031.md)
separate validated daily interest, immutable local history and valuation FX reads.
`/valuation/interest` provides source correction, assessed stock revisions, explicit
updates and paginated history. Receipts clear only paid stock; optional gaps stay
disclosed/nonblocking. Changed sources invalidate checkpoints and stale staged
publication. Automatic accrual generation, scheduling, cross-currency trade-accrual
conversion and bulk upload remain outside this delivery. F38 PARTIAL/F39 ALPHA remain.

29 October [stock presentation](../../delivery/valuation-review-signals-20261029.md)
shows local/reporting opening and closing accrued stocks from retained conversions.
Each missing stock/rate remains independently unavailable. No new interest,
CARRY, source lookup or persisted financial value is generated by this display.

28 October wrapper distributions use the existing typed economic-flow API with
explicit COUPON income versus PAYMENT_ONLY recognition and frozen type evidence.
No wrapper daily-interest, distribution or token-reward generation is inferred.
The bond coupon payment-only safeguard is preserved.

28 October [note interest extension](../../delivery/structured-note-pnl-20261028.md):
CLEAN notes may add supplied daily interest and assessed stock FX, with partial
nonblocking absence. DIRTY/NONE marks do not add the same accrued again. Typed
note COUPON income is distinct from later PAYMENT_ONLY confirmation; existing
bond payment-only behavior remains. Same-date supplied CLEAN interest/coupon
income overlap is rejected. Note stock anchors are assessed; detached note
receivables and conditional/memory-coupon generation remain deferred.

27 October: [accrued-stock FX](../../architecture/market-data-and-valuation/accrued-balance-fx.md)
adds source-based local stock reconstruction, dataset 3, canonical CARRY and
separately owned unpaid receivables after sale. Daily interest and actual coupon
receipts remain distinct. Missing optional balances/FX leave partial results;
source changes require reassessment rather than rewriting publication. No
automatic earned-interest calculation, entitlement or complete fund accounting.

27 October: [full bond cashflow schedules](../../architecture/trading-and-operations/bond-cashflow-schedules.md)
extend coupon reference data with principal repayments, retaining IDs/revisions
and coupon receipts. Lifecycle UI supports both types and principal-only zero
bonds. No automatic interest, accrued-stock rollforward, entitlement or DCF is
introduced by that schedule increment alone. Actual receipts now enter the
subsequent accrued-stock reconstruction without being recognised as income. See
[delivery evidence](../../delivery/bond-cashflow-schedule-20261027.md).

26 October: [confirmed zero-coupon applicability](../../delivery/zero-coupon-accrual-applicability-20261026.md)
uses original frozen booking terms, not current master data. Absent coupon inputs
are not applicable rather than missing, including strict coverage. Supplied valid
inputs are still included; unknown/mixed coupon terms retain coverage checks.
The retained applicability rule creates no interest amount or accretion model;
later supplied interest blocks stale staged publication. Existing runs are unchanged.

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
- **Status / backend / frontend:** PARTIAL. Append-only assessed daily bond inputs plus typed economic-flow trades; input registers/forms and component/evidence displays. Source-based accrued-stock replay retains immutable per-attempt balances, adds CARRY once and can retain unpaid receivables after disposal. Opening balance + earnings + movements reconciles to closing balance; ACCRUAL includes daily earnings only. Missing stock history remains unknown; rich assessed anchors can restore it.
- **Cuts/trade-offs:** Position-level canonical daily inputs allocated once, not duplicated per listing/trade. Operators choose INCOME versus PAYMENT_ONLY; coupon payment is not earned interest again. Cash-flow trades are explicit actual economics, not fabricated investment holdings.
- **Weaknesses:** No automated bond accrual generation, full unbooked income coverage, dividend entitlement engine or automatic swap-reset/mark reconciliation. Operators still own classification correctness; arithmetic checks cannot certify economic completeness. Derived stocks currently display native balances with reporting FX/CARRY, rather than separate reporting-currency stock amounts. Partial/warning signals are not yet fully unified across cash and interest.
- **Remaining:** Reviewed calculation/import of interest, coupon/dividend/reset linkage and reconciliation, richer input challenge; broader maturity economics before claiming complete bond P&L. Plain-bond principal closure does not replace final-day interest inputs where coupon accrual applies; confirmed zero-coupon terms follow the applicability exception above.
- **Evidence:** [Agreed foundation](../../delivery/economic-pnl-agreed-foundation-2026-10-09.md), [accrual checks](../../../valuation/accruals.py), [economic-flow ledger](../../../valuation/flows.py), [delivery](../../delivery/economic-pnl-implementation-2026-10-09.md).

## F39 Review and publication

31 October: [incomplete-price review](../../delivery/incomplete-price-review-20261031.md)
stages available positions with explicit unknown investment/cash FX contributions
under WARN/MANUAL_OVERRIDE rules. Headline amounts are calculated subtotals;
required marks or independently reviewed exact-input overrides plus a new
calculation are necessary before normal/self publication. Requests/decisions are
immutable and currently entitled, without provider-price fabrication. Optional
interest/cash snapshots remain nonblocking. This supplements F37/F39 without
claiming complete NAV or changing F37 PARTIAL / F39 ALPHA classifications.

26 October [report-tab delivery](../../delivery/valuation-report-tabs-20261026.md)
separates each selected result into Breakdown, Positions & cash, Review and Logs.
Shared context/totals, actual input gaps, blockers and publication stay outside
tabs. Failed/History attempts open Logs; URL navigation and mounted financial/
review panels preserve selection and drafts without repricing or weaker access.
Position attribution offers 25 (default), 50, 100 or All matching rows, with
range/page controls; filters and ordering precede pagination across the full
authorized result. Page size persists across report tabs; totals stay whole-result.
Page-size and Previous/Next controls sit below the table. The position inspector
is closed by default, opening from a row's Inspect position action.
Instrument type is a separate column and full-result filter, combined with search,
attention and source before paging. Listing types resolve from their canonical
parent through current accessible metadata; unavailable types are explicit, not
guessed. This is display classification only, not frozen valuation methodology.
The [position-inspection worksheet](../../delivery/position-inspection-manual-check-20261026.md)
leads with exact frozen opening/closing quantities, valuation prices, actual dates,
FX direction/rates, contract factors, dated executions and the retained value
bridge. Technical IDs/source/rule/JSON proof remains expandable below; no browser
repricing, missing-value substitution or change to publication authority.
Bond business labels prefer current governed ISINs (including a canonical parent's
ISIN for listings), rather than internal import codes. Dates/primary preference
and visibility apply to this current naming metadata, not frozen valuation facts;
equity tickers and the no-ISIN fallback are unchanged.

24 October [source coverage follow-up](../../delivery/pnl-source-coverage-20261024.md):
Results shows disjoint exact component groups in reporting currency, coverage
statuses and full-result contributing-position inspection. Included groups reconcile
to stored net; recorded zero is distinct from missing/not recorded/unassessed.
That delivery initially excluded cash FX. The subsequent [cash-FX extension](../../delivery/cash-fx-pnl-20261025.md)
adds standard daily cash assessment and separate account-owned results, without
an exclusion switch. Missing cash entries are visible/non-blocking; obsolete
results without source proof require recalculation. Coverage is not completeness certification; existing
DISPLAY, review and publication controls remain enforced.

Its [presentation corrections](../../delivery/pnl-source-coverage-20261024.md#24-october-follow-up-precision-and-historical-unknowns)
retain signed `<0.01` / `−<0.01` markers when two-decimal formatting would erase a
nonzero amount, and keep historical **Not assessed** distinct from recorded absence.
True zero and stored financial evidence remain unchanged.

24 October [Ops review refinement](../../delivery/pnl-ops-review-20261024.md):
full-result, permission-scoped business labels replace primary UUID text; exact
stored-component rollups, search/attention filtering and signed-decimal sorting
support daily review. Frozen quantities and a compact price/FX/date/source table
explain selected positions. The position inspector can close for a full-width
table and reopen from a row, preserving filters/paging and returning keyboard
focus on close. Publication confirmation repeats the selected run,
amount and warnings. UUIDs/JSON remain accessible; current labels are response-only
metadata, never rewritten historical evidence. Pending/source metadata is a read
snapshot; the server still rechecks all publication controls. No new calculator,
financial coverage, permission, database migration or full-NAV sign-off.

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

25 October: [cash FX P&L](../../delivery/cash-fx-pnl-20261025.md) adds explicit
daily opening-balance attribution, typed cash-account/currency result ownership,
frozen snapshot/FX evidence and staged/amended/published cash lines. Missing
exact-date pairs remain disclosed omissions when one boundary is supplied;
neither boundary supplied does not create missing-input warnings from history.
Only snapshots within the opening/closing window establish cash scopes or trigger
cash source reassessment. Nonzero required FX still blocks.
Cash changes enter the reassessment queue and block stale publication. Local
migration 99 activation and exact verification are recorded in that delivery.

October 14 audit follow-up: [applied valuation decisions and methodology matrix](../../delivery/valuation-rules-and-cash-snapshots-20261014.md)
adds stable versioned explanations to new immutable position evidence, including
booked execution cost, independent fund NAV/FX dates, normalized mark values,
same-currency identity, reviewed quantity ratios and income versus payment-only
flows. This supplements F37–F39; old evidence is not reconstructed in the browser.

- **Desired:** Upload strategy/company/account/currency EoD balance snapshots valid only on their value date, translate with governed FX, and eventually calculate complete fund/strategy NAV including liabilities/fees/income.
- **Status / backend / frontend:** PARTIAL. Separate `trd.cash_account` / `cash_balance` register, manual entry/CSV uploads, append-only corrections, notes/history and policy-backed cash-value preview at `/valuation/cash-balances`. `/valuation` always assesses cash FX, with no UI/API opt-out; staged/published account reports retain coverage/source controls. Missing cash entries are disclosed but do not themselves block publication. Migrations 89 and 99 are locally active. Synthetic cash P&L acceptance passed; independent financial acceptance/full NAV remain deferred.
- **Cuts/trade-offs:** No daily unwind, carry-forward or trade-generated cash. A correction requires current revision and a separate reason. The translated stock preview is not a staged NAV. Standard cash FX uses signed opening native cash × daily reporting FX change, sums daily over longer periods, and enters gross/net once without altering investment market P&L. Exact-date zero is explicit; absent snapshots are not zero. Supplied foreign balances require valid FX. Obsolete source-proof-less runs require fresh calculation; no opt-out compatibility adapter. Coverage is limited to uploaded account/currency scopes, not independently verified complete bank/custody inventory.
- **Weaknesses:** No movement-based cash P&L, statement parsing/automatic reconciliation, account closure workflow or complete balance/obligation/liability allocation. Register reads are date-specific but not paginated; uploads are bounded to 500 rows / frontend CSV 1 MB. Companies must already exist in the organisation catalogue. Crypto balances can be recorded but translation still requires supported governed FX evidence; no crypto price or triangulation is invented.
- **Remaining:** Populated-account/upload/correction browser acceptance, independent inventory/financial acceptance, durable cash-stock/NAV publication, intraday movement attribution/reconciliation and full fund NAV. Cash FX staging/publication is distinct from cash-stock valuation. Do not relabel translated balance changes or economic P&L as complete NAV.
- **Evidence:** [Delivery and methodology matrix](../../delivery/valuation-rules-and-cash-snapshots-20261014.md), [snapshot service](../../../valuation/cash_snapshots.py), [cash API](../../../apps/reference_api/cash_snapshot_routes.py), [focused API checks](../../../tests/test_cash_snapshot_api.py).

## F57 Valuation purpose and descriptive tags

- **Desired:** Distinguish a run's controlled purpose (daily operations, intraday monitoring, reconciliation or what-if), calculation scope and timing from optional tenant-curated descriptive tags such as month-end or investment committee.
- **Origin:** Discussed 14 October 2026; user explicitly parked the idea to prioritize valuation UI readability and navigation. This is a deferred direction, not an approved implementation specification.
- **Status / backend / frontend:** DEFERRED. Existing engine scope and staging/publication statuses are implemented; purpose-specific result lanes and tenant-curated run tags are not.
- **Cuts/trade-offs:** Tags must not confer publication authority, change calculation economics or relabel economic P&L as full NAV. Scope must describe actual calculated coverage. A published internal indicative estimate is not automatically the fund's official dealing NAV. Intraday labels alone do not enable intraday pricing.
- **Weaknesses:** Current candidate replacement and publication supersession are scoped by tenant, strategy and value date, not independent purposes; merely attaching tags would not prevent a what-if or intraday candidate from displacing the daily operational result.
- **Remaining:** When resumed, define the minimal purpose vocabulary, publication/replacement boundaries, retained purpose evidence, allowed descriptive tags and reporting filters. No additional NAV or live-price engine is authorized by this note.
- **Evidence / related capabilities:** [Current stage/publication behavior](../../../valuation/storage.py), [review workflow](#f39-review-and-publication), [full NAV boundary](#f40-full-nav-and-cash-balances). Terminology references checked 14 October 2026: [SEC indicative intraday value versus NAV](https://content.govdelivery.com/accounts/USSEC/bulletins/4de0c2) and [ESMA UCITS Article 85](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/ucits/article-85). These support distinguishing indicative values and governed NAV; the proposed field structure is a project choice, not a prescribed industry schema.
