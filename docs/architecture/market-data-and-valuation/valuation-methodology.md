# Economic valuation methodology and edge-case matrix

Status: maintained alpha reference. Structured-note, non-ETF ETP and spot-crypto supplied-mark extensions reviewed 28 October 2026; broader matrix reviewed 27 October 2026 for accrued-stock reconstruction/FX, alongside account-owned cash FX and `economic-position-pnl-v3`. This is not complete fund NAV, universal derivative pricing or an accounting policy. See the [cross-layer state review](../../delivery/quality-reviews/2026-10-27-valuation-state-review.md) for achieved scope and remaining gaps.

## Required marks and partial review

[Missing-mark review](../../delivery/incomplete-price-review-20261031.md) adds
explicit partial staging under WARN/MANUAL_OVERRIDE. Any missing required daily
bridge excludes that whole investment-position or cash-account/currency period
contribution; unknown P&L is not zero. Full projection/snapshots remain retained,
with calculated subtotals and required-mark publication blocking. Reviewed exact
marks require independent approval and a new calculation; ordinary eligible
observations win. Optional interest and missing cash snapshots remain distinct.
No licensing, product, calendar or price-unit guard is waived.

## Common bridge

Separate from the P&L bridge below: [position monetary measures](../../delivery/position-monetary-measures-20261015.md)
provide an on-demand, non-published stock preview. Equity/ETF/fund measures are
equal by project convention; full bond value prefers dirty then clean plus an
assessed accrued stock; bounded native index swaps distinguish reference notional,
underlying exposure and whole-swap MTM. This does not expand derivative P&L support
or make the preview a staged NAV, weight, regulatory-risk result or official value.

The later [futures monetary slice](../../delivery/future-position-measures-20261015.md)
adds current notional/exposure for linear cash-settled index contracts using the
exact dated futures price and frozen monetary multiplier. Contract MTM remains
unavailable without clearing/variation-margin evidence. The subsequent
[daily futures P&L extension](../../delivery/futures-daily-pnl-20261027.md)
adds supplied-price variation without changing that monetary-preview limit;
monetary notional is not a NAV asset.

The [FX-forward monetary slice](../../delivery/fx-forward-position-measures-20261015.md)
adds signed base notional and two undiscounted contractual currency legs, each with
its own strategy-FX conversion. Contract MTM remains unavailable. A base-flat mixed-
agreement exception is retained rather than silently considered closed. The
[three-measure review](../../delivery/quality-reviews/2026-10-15-position-measures-review.md)
records product definitions, primary-source guidance and remaining gaps; none of
this changes the P&L matrix below or introduces risk weights.

Reconstruct original bookings, recognized execution dates, reviewed share ratios and valid historical corrections at a frozen information cutoff. Net only compatible subject, product, units, quote factors and trade-price currency. Never rewrite booked trades to create today's holdings.

For one daily bridge, local opening value is L0, closing value L1, signed period execution value E, and trade-price-currency → strategy/reporting-currency rates are F0/F1:

- Local market P&L = L1 − L0 − E.
- PRICE = local market P&L × F0.
- FX = L0 × (F1 − F0).
- PRICE_FX_CROSS = local market P&L × (F1 − F0).
- Market P&L = PRICE + FX + PRICE_FX_CROSS = L1F1 − L0F0 − EF1.

E is an economic execution bridge, **not** a balance on a cash account. A sale has negative E. Closing exposure at T does not erase the gain/loss earned up to its booked closing price on T. New holdings use their booked execution cost; the opening mark of an existing holding is not replaced by that new trade's price. For zero opening exposure, the engine uses F0 = F1: a new position does not acquire fictitious overnight FX P&L. Foreign multi-day requests sum daily bridges so executions use their own economic day's FX, not one final-date FX for every trade.

The FX source is the **trade-price currency**, which may differ from instrument currency. Quotes must be compatible or have explicit normalization proof. Reporting currency is the selected strategy/reporting currency. Same currency uses 1 without an observation; direct governed FX is preferred. Inverse use needs explicit permission and retained twelve-decimal half-even rounding. No silent triangulation or alternate fixing. Market price and FX dates are resolved independently; using a prior fund NAV does not shift FX to that prior date.

## Fund NAV dates and FX dates

The working fund convention is explicit previous-valuation-session pricing:
valuation T uses closing NAV T−1 and opening NAV T−2, while FX remains T/T−1.
For 20 October 2026 this means 19/16 October NAVs and 20/19 October FX. Use each
fund's governed valuation calendar, including declared closures, rather than
subtracting calendar dates or shifting FX with the NAV. `FIXED_LAG=1` is a policy
choice with separate freshness bounds; it does not silently permit a missing
requested NAV. See the [31 October correction](../../delivery/fund-nav-lag-20261031.md).
Other actual fund conventions remain explicitly configurable; the calculator
must not hard-code this reconciliation setup across all products.

## Product and lifecycle matrix

| Product/case | Current calculation | Required inputs and boundaries | Evidence/tests |
| --- | --- | --- | --- |
| Equity/ETF long or short | Quantity × unit multiplier ÷ quote factor × compatible as-traded mark | Nonzero opening/closing holdings require their marks; source basis conversion needs proof | [Numerical matrix](../../../tests/test_valuation_methodology_matrix.py), [price basis](../../../tests/test_valuation_price_basis.py) |
| New/additional/partial/full close or round trip | Prior holding plus actual signed execution bridge | Closed boundary needs no mark; execution-only round trip still contributes P&L | [Matrix](../../../tests/test_valuation_methodology_matrix.py), [position bridge tests](../../../tests/test_position_valuation.py) |
| Reviewed basic share ratio | Adjust derived quantities at event date, then use native units | Reviewed action and fractional-entitlement policy; original quantities remain booked | [Split replay](../../../tests/test_position_split_replay.py), [action safety](../../../valuation/corporate_actions.py) |
| Non-ETF quoted wrappers (ETC/ETN/ETV/ETI/vehicles/certificates) | Security value / execution / price-FX bridge using frozen listing factors and the whole wrapper quote once | Actual type retained; generic ETP needs effective terms. No underlying/leverage double multiplication. Reviewed unit ratios are supported; income/costs are separate. Historical SHARES labels normalize to UNITS without rewriting trades | [ETP/spot delivery](../../delivery/etp-spot-crypto-pnl-20261028.md), [native tests](../../../tests/test_cash_product_pnl_integration.py) |
| Spot DIGITAL_ASSET | Fractional signed tokens × listing quote × frozen factors, converted from trade quote currency to reporting | Exact listing; native RAW, explicit governed cut and requested-day OPEN calendar coverage. No assumed stablecoin peg, share-split conversion or staking/fork/margin postings. Missing mandatory prices/FX block | [Delivery](../../delivery/etp-spot-crypto-pnl-20261028.md), [cases](../../../tests/test_cash_product_pnl_integration.py) |
| Fund units | Units × canonical share-class NAV | NAV for T signed off T+1 remains economically T. Policy explicitly selects available NAV dates/lag/calendar; publication and receipt must be known by information cutoff. Missing newer NAV is not silently guessed | [Fund integration](../../../tests/test_economic_pnl_acceptance.py), [date resolver](../../../tests/test_valuation_resolver.py) |
| AMC, unit or percentage quote | Signed quantity × frozen multiplier × eligible price ÷ divisor, plus common execution/FX bridge. Unit quote: multiplier 1. Percentage: divisor 100, denomination applied only to certificate-count quantities, never again to nominal | Canonical type stays ACTIVELY_MANAGED_CERTIFICATE. AMC_PRICE_BASIS series dimension must match quotation. All three monetary measures use the funded-security market-value reporting proxy, not look-through or contractual face. No fund NAV/lag assumption, generated fees or redemption | [AMC booking](../../../tests/test_amc.py), [measure/daily numerical tests](../../../tests/test_amc_measures.py), [scope](../../delivery/amc-onboarding-20261023.md) |
| Plain bond | Nominal ÷ 100 × clean price, plus separately assessed daily interest and opening accrued-stock FX where available | Dirty execution uses frozen bought/sold accrual once. DIRTY market quotes subtract exact observation-paired accrued per 100, known by cutoff; missing quote evidence cannot be replaced with strategy interest. Stocks reconstruct independently from complete history or anchors; gaps remain unknown. Full monetary previews retain DIRTY | [Normalization and limits](../../delivery/bond-dirty-to-clean-20261028.md), [native integration](../../../tests/test_bond_dirty_market_integration.py), [stock-FX integration](../../../tests/test_accrued_balance_integration.py) |
| Confirmed zero-coupon bond | Same nominal/clean-price and FX bridge; absent coupon accrual is explicitly not applicable | Every contributing frozen booking must confirm coupon type ZERO. No invented zero interest or separate discount-accretion entry. Supplied valid interest is still included; unknown/mixed terms retain normal coverage checks | [Applicability delivery](../../delivery/zero-coupon-accrual-applicability-20261026.md), [focused cases](../../../tests/test_zero_coupon_accruals.py), [calculation/publication integration](../../../tests/test_economic_pnl_acceptance.py) |
| Bond principal maturity | Booked sourced redemption closes nominal; proceeds enter T execution bridge | No arbitrary zero price or inferred cash. Final-day earned interest remains required where eligible; principal closure is not coupon accounting | [Maturity valuation](../../../tests/test_bond_redemption_valuation.py) |
| Deliverable FX forward | Signed base amount × outright-rate movement; net value uses rate minus frozen agreed rate | Contract-specific base/quote/maturity rate series, not generic spot or provider monetary MTM. Value explicitly undiscounted, not a model MTM | [Rate bridge](../../../tests/test_fx_forward_pnl.py), [integration](../../../tests/test_fx_forward_valuation.py) |
| FX-forward maturity | Retained booked close rate enters T P&L and flattens exposure | Ops may use retained policy spot suggestion or sourced override; actual delivery remains contractual. Closure writes no cash balance | [FX maturity delivery](../../delivery/fx-forward-maturity-20261014.md), [integration](../../../tests/test_fx_forward_valuation.py) |
| Historical record correction | Cancel/supersede erroneous booking effective at original execution; explicitly linked replacement enters once | Frozen earlier knowledge remains reproducible. Later-effective economic termination is not treated as record cancellation | [Reassessment delivery](../../delivery/trade-corrections-valuation-reassessment-20261014.md), [reconstruction](../../../tests/test_position_reconstruction.py) |
| Generic swaps with supplied whole-contract marks | Signed units/nominal × whole-swap mark ÷ frozen quote factor, with reporting FX and the shared execution bridge | Performance and two-floating-leg rate variants retain separate component marks. Zero/negative marks allowed; match whole-swap basis/units/divisor. Do not reapply leverage/reference or leg notionals. No funding model or automatic reset/maturity processing | [Initial delivery](../../delivery/swap-supplied-mark-pnl-20261023.md), [rate-exchange extension](../../delivery/rate-exchange-swaps-20261030.md), [tests](../../../tests/test_rate_swap_booking.py) |
| Listed vanilla options with supplied contract premiums | Signed contracts × frozen premium multiplier ÷ quote factor, with reporting FX and the shared execution bridge | Canonical premium identity and explicit quote dimensions; zero supplied premiums allowed, no negative/missing substitutions. No second deliverable/listing multiplier, model price or exercise/expiry posting | [Delivery and limits](../../delivery/option-premium-pnl-20261023.md), [tests](../../../tests/test_option_valuation.py) |
| Linear dated index/crypto futures | Signed opening/closing price-reference difference less signed executions, multiplied by frozen monetary multiplier/divisor; daily native variation translates at closing FX | Exact expiry listing/dimensions and original INDEX_POINTS or UNDERLYING_UNIT quotation. Cash/physical crypto delivery terms do not change pre-delivery variation. No gross-notional FX, second multiplier, margin cash generation or assumed contract MTM. Zero boundary needs no mark; open exposure after final settlement blocks | [Initial delivery](../../delivery/futures-daily-pnl-20261027.md), [linear extension](../../delivery/linear-futures-extension-20261028.md), [native cases](../../../tests/test_linear_futures_pnl_integration.py) |
| Fully funded structured notes | Whole-note price/FX/security execution bridge with frozen nominal/units and denomination/divisor once | Native RAW whole-note MARK/CLOSE explicitly matching CLEAN/DIRTY/NONE. Only CLEAN adds supplied daily earnings and assessed stock FX. Ordinary closures keep same-day P&L; no payoff model, generated lifecycle or detached note receivables | [Note delivery](../../delivery/structured-note-pnl-20261028.md), [real-booking tests](../../../tests/test_structured_note_pnl_integration.py) |
| Other futures families / inverse, quanto, perpetual or financing-adjusted contracts | No corresponding family/reference or economic adapter in this slice | Cannot be relabelled as an index or linear crypto contract; delivery/accounting and monetary previews remain separate | [Scope and capability](../../delivery/linear-futures-extension-20261028.md), [linear guard](../../../security_master_schema/future_economics.py) |
| EoD cash balances | Separate translated stock preview plus standard daily cash FX: signed opening native balance × (closing FX − opening FX) | Always assessed; no exclusion switch. Exact daily opening/closing snapshots per account/currency. Missing pairs disclosed and non-blocking, never zero/carried. Required foreign FX governed independently. Cash FX contributes gross/net, not investment market P&L; not cash-stock NAV or generated countercash | [Cash FX delivery/convention](../../delivery/cash-fx-pnl-20261025.md), [exact formula](../../../valuation/cash_fx.py), [native integration](../../../tests/test_cash_fx_storage.py) |

## Income, accrual stocks and costs

27 October futures follow-up: futures PRICE is economic-day local variation ×
closing reporting FX. FX/cross on gross futures notional are not added; margin
cash is assessed separately. Per-position asset/execution values are null.
Batch non-futures value reconciliation adds an explicit `futuresVariationPnl`
term and excludes futures gross notional/unassessed MTM. Foreign multi-day
requests sum daily variations at their own closing FX. See
[futures conventions and evidence](../../delivery/futures-daily-pnl-20261027.md).

23 October: daily earned interest is optional by default. Include every valid
supplied eligible input; absent bond/date coverage is frozen and prominently
reported as not supplied/not included, not assessed zero. Explicit
`requireCompleteAccruals` enforces full daily coverage. Invalid supplied inputs
and other required inputs still block. Newly supplied missing interest invalidates
staged publication until recalculated; no published result is rewritten.
[Delivery](../../delivery/optional-bond-accruals-20261023.md).

26 October: [zero-coupon applicability](../../delivery/zero-coupon-accrual-applicability-20261026.md)
exempts absent coupon inputs only when all contributing original booked terms
confirm ZERO. Coverage retains canonical bond/date `notApplicable` evidence and
line-level `DAILY_ACCRUAL_NOT_APPLICABLE` rules, without a missing-interest warning
or manufactured amount, including strict mode. A zero rate, name, current master
change or unknown/mixed terms is not sufficient. Supplied inputs are still
validated/included; later supplied interest requires recalculation before staged
publication. Maturity checks and frozen historical results are unchanged.

[Typed daily-interest follow-up](../../delivery/typed-daily-interest-20261014.md):
daily earned amount/currency are mandatory table columns. Supplied reconciled
balances and movements remain optional. The subsequent [stock-FX extension](accrued-balance-fx.md)
can reconstruct accumulated stocks from complete original daily/trade/receipt
history or assessed anchors; an earnings-only row alone does not prove that
history is complete. Unknown history is not a zero stock.

Market P&L is distinct from gross/net economic P&L. Gross adds explicitly recorded income and supplied cash FX; net adds signed costs/adjustments. Cash assessment is standard; missing balances are disclosed without pretending zero or independently blocking publication. Dividend and reset flows use their explicit classification. PAYMENT_ONLY contributes no new income. Current bond coupons are PAYMENT_ONLY: interest is recognized through assessed daily earnings. Reset classification does not by itself prove reconciliation with a swap mark; supplied whole-swap marks are supported, while modelling funding/reset cashflows remains outside scope.

Cash FX uses the user-approved opening-balance/EoD-movement convention: intraday
cash changes are treated at closing FX. No flow amount is recognized as income
from a snapshot change. Cash days keep exact source revisions/rates and typed
account/currency ownership, separately from security buckets. Every calculation
assesses cash without a request switch. Old request keys do not replay obsolete
cashless calculations; no historical financial values are rewritten. Both cash
and ledger source corrections require fresh staging before publication. See
[cash methodology and limits](../../delivery/cash-fx-pnl-20261025.md).
Cash scope/coverage and source-change detection are bounded to the opening and
closing dates inclusive. Neither daily snapshot supplied does not imply an
expected balance from old history; one supplied boundary still exposes its
missing counterpart. No continued zero uploads are required for vanished scopes.

Bond input bridge: opening accrued balance + daily earned interest + signed balance movements = closing accrued balance. Derived replay separates purchased/sold accrued and confirmed coupon receipts within those non-income movements. Add **daily earned** to ACCRUAL, not the full closing accrued stock. FX on the opening accrued receivable is separately retained as CARRY. Allocate assessed canonical-instrument earnings once, not once per listing. Coverage follows eligible daily exposure, including weekends and maturity-day disposal; assessment/day-count/nominal eligibility remain Ops responsibilities, not an automatic coupon engine. Rich assessed inputs retain local/reporting amounts; the new derived dataset retains native stocks, reporting currency, FX and reporting CARRY, but does not yet expose separate reporting-currency opening/closing stock amounts. See FIX-VAL-006 in [reviewed findings](../../../FIX.md).

Hand checks pinned by the tests: 10 units at 100→110 with FX .80→.85 gives PRICE 80, FX 50, cross 5, total 135. A new 10-unit fund purchase at 98 with available NAV 100 and current FX .86 gives 17.20, no overnight FX. Nominal 100,000 at clean 99→100 earns market 1,000; daily interest 10 gives gross 1,010, not 2,000. A 1,000,000 forward opened at 1.10, prior rate 1.11 and maturity close 1.125 gives 15,000 quote-currency T P&L and zero closing value.

## Selection, failure and publication

Economic date, price date requested, actual observation date, source publication time, received time and information cutoff are distinct. Source rights, semantic compatibility, sealed calendar coverage, matched policy rules and explicit freshness are checked before calculation. FLEXIBLE supplies defaults only when no rule matches; it does not bypass an unavailable explicit fixing or permit arbitrary prior-day data. Missing nonzero marks/FX, unsupported actions or incomplete evidence block rather than become zero.

Frozen applied rules explain selection dates/availability, normalization, execution price, clean-bond units, value bridge, ratio events, maturity and assessed income. Explanations use already-frozen values; they cannot select prices or reprice. Existing historical results are not backfilled. New staged lines include POSITION_VALUE_BRIDGE/CLEAN_BOND_NOMINAL where evidenced, and calculation rules include daily accrual evidence as well as flows.

Calculate → stage → governed amendments → reviewed publish remains unchanged. Ledger corrections flag existing results without changing financial values and block stale staged publication. New recalculation creates a successor; it may select newer data and does not automatically reapply manual amendments. Default independent review and explicitly governed self-publication remain enforced.

## Research and applicability

Checked 14 October 2026. These sources inform design; they do not certify the alpha:

- [SEC rule 2a-5 guide, 26 February 2021](https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/good-faith-determinations-fair-value-small-entity-compliance-guide): methodology selection/testing, pricing-service oversight and retained evidence for covered US funds. Our matrix and exact regressions apply that engineering discipline; they are not a fair-value governance/compliance programme.
- [IFRIC September 2018, IAS 21](https://www.ifrs.org/news-and-events/updates/ifric/2018/ifric-update-september-2018/): closing-rate and transaction-date distinctions in its specific foreign-operation context. Our day-end execution FX and PRICE/FX/CROSS allocation are documented project conventions, not a claim of prescribed IFRS attribution or transaction-time accounting.
- [FINRA accrued-interest calculator](https://accruedinterest.nga.finra.org/calculator/): bond type and nominal matter to accrual inputs. Its accessible page is limited; no day-count algorithm was imported from it.
- [Japan FSA notice, 8 June 2026](https://www.fsa.go.jp/inter/ios/20260608/20260608.html): confirms the updated IOSCO Recommendations on Valuing CIS supersede/consolidate older principles. The linked final IOSCO PDF returned 403, and its API mirror was inaccessible. Detailed 2026 provisions were not reviewed or represented as implemented; this limitation is retained rather than presenting the 2013 report as the latest guidance.

## Remaining assurance work

27 October: the [full bond schedule](../trading-and-operations/bond-cashflow-schedules.md)
retains coupon and principal events; actual payment revisions remain separate.
Confirmed coupon receipts now reduce subsequent reconstructed accrued stock by
the confirmed amount, without adding income again. A scheduled date alone does
not prove payment or clear a balance. Outstanding accrued receivables can survive
a full security disposal. Automatic entitlement, interest generation, payment-to-bank
and stock/cash reconciliation remain separate work.

Independent provider/custodian reconciliation, representative scale tests, queued calculations, broader non-ledger source-impact assessment, intraday movement-based cash P&L/full NAV, broader corporate actions, discounted forward MTM and unsupported-product pricing remain separate work. Bounded cash-snapshot source-change detection is implemented; it is not a universal source-impact engine. This matrix documents/test-pins the supported engine; it does not eliminate those boundaries.
