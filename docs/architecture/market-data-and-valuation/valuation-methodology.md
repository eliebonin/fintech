# Economic valuation methodology and edge-case matrix

Status: maintained alpha reference. Reviewed 14 October 2026 against the supported `economic-position-pnl-v3` path. This is not complete fund NAV, universal derivative pricing or an accounting policy.

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
unavailable without clearing/variation-margin evidence. The unsupported-futures
P&L row below is unchanged; monetary notional is not a NAV asset.

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

## Product and lifecycle matrix

| Product/case | Current calculation | Required inputs and boundaries | Evidence/tests |
| --- | --- | --- | --- |
| Equity/ETF long or short | Quantity × unit multiplier ÷ quote factor × compatible as-traded mark | Nonzero opening/closing holdings require their marks; source basis conversion needs proof | [Numerical matrix](../../../tests/test_valuation_methodology_matrix.py), [price basis](../../../tests/test_valuation_price_basis.py) |
| New/additional/partial/full close or round trip | Prior holding plus actual signed execution bridge | Closed boundary needs no mark; execution-only round trip still contributes P&L | [Matrix](../../../tests/test_valuation_methodology_matrix.py), [position bridge tests](../../../tests/test_position_valuation.py) |
| Reviewed basic share ratio | Adjust derived quantities at event date, then use native units | Reviewed action and fractional-entitlement policy; original quantities remain booked | [Split replay](../../../tests/test_position_split_replay.py), [action safety](../../../valuation/corporate_actions.py) |
| Fund units | Units × canonical share-class NAV | NAV for T signed off T+1 remains economically T. Policy explicitly selects available NAV dates/lag/calendar; publication and receipt must be known by information cutoff. Missing newer NAV is not silently guessed | [Fund integration](../../../tests/test_economic_pnl_acceptance.py), [date resolver](../../../tests/test_valuation_resolver.py) |
| AMC, unit or percentage quote | Signed quantity × frozen multiplier × eligible price ÷ divisor, plus common execution/FX bridge. Unit quote: multiplier 1. Percentage: divisor 100, denomination applied only to certificate-count quantities, never again to nominal | Canonical type stays ACTIVELY_MANAGED_CERTIFICATE. AMC_PRICE_BASIS series dimension must match quotation. All three monetary measures use the funded-security market-value reporting proxy, not look-through or contractual face. No fund NAV/lag assumption, generated fees or redemption | [AMC booking](../../../tests/test_amc.py), [measure/daily numerical tests](../../../tests/test_amc_measures.py), [scope](../../delivery/amc-onboarding-20261023.md) |
| Plain bond | Nominal ÷ 100 × clean price, plus separately assessed daily interest | Dirty execution is normalized once using frozen bought/sold accrual; dirty market marks are blocked without supported per-nominal normalization. Optional detailed daily inputs reconcile balances/movements; earnings-only inputs disclose unassessed stocks | [Bond integration](../../../tests/test_economic_pnl_acceptance.py), [accruals](../../../tests/test_valuation_accruals.py), [typed interest](../../../tests/test_typed_daily_interest.py) |
| Bond principal maturity | Booked sourced redemption closes nominal; proceeds enter T execution bridge | No arbitrary zero price or inferred cash. Final-day earned interest remains required where eligible; principal closure is not coupon accounting | [Maturity valuation](../../../tests/test_bond_redemption_valuation.py) |
| Deliverable FX forward | Signed base amount × outright-rate movement; net value uses rate minus frozen agreed rate | Contract-specific base/quote/maturity rate series, not generic spot or provider monetary MTM. Value explicitly undiscounted, not a model MTM | [Rate bridge](../../../tests/test_fx_forward_pnl.py), [integration](../../../tests/test_fx_forward_valuation.py) |
| FX-forward maturity | Retained booked close rate enters T P&L and flattens exposure | Ops may use retained policy spot suggestion or sourced override; actual delivery remains contractual. Closure writes no cash balance | [FX maturity delivery](../../delivery/fx-forward-maturity-20261014.md), [integration](../../../tests/test_fx_forward_valuation.py) |
| Historical record correction | Cancel/supersede erroneous booking effective at original execution; explicitly linked replacement enters once | Frozen earlier knowledge remains reproducible. Later-effective economic termination is not treated as record cancellation | [Reassessment delivery](../../delivery/trade-corrections-valuation-reassessment-20261014.md), [reconstruction](../../../tests/test_position_reconstruction.py) |
| Generic swaps with supplied whole-contract marks | Signed units/nominal × whole-swap mark ÷ frozen quote factor, with reporting FX and the shared execution bridge | Zero/negative marks allowed; match whole-swap basis/units/divisor. Do not reapply leverage/reference notional. No funding model or automatic reset/maturity processing | [Delivery and limits](../../delivery/swap-supplied-mark-pnl-20261023.md), [tests](../../../tests/test_swap_valuation.py) |
| Listed vanilla options with supplied contract premiums | Signed contracts × frozen premium multiplier ÷ quote factor, with reporting FX and the shared execution bridge | Canonical premium identity and explicit quote dimensions; zero supplied premiums allowed, no negative/missing substitutions. No second deliverable/listing multiplier, model price or exercise/expiry posting | [Delivery and limits](../../delivery/option-premium-pnl-20261023.md), [tests](../../../tests/test_option_valuation.py) |
| Futures/structured notes | Not implemented in the live valuation engine | Booking support does not imply valuation readiness; no generic equity-price shortcut | [Capability guards](../../../valuation/product_inputs.py), [matrix](../../../tests/test_valuation_methodology_matrix.py) |
| EoD cash balances | Separate exact-date translated stock preview | Account/company/currency/date, explicit zero, source and note; no daily unwind. Not cash P&L, authoritative staged NAV or automatic trade-countercash | [Cash register](../../../valuation/cash_snapshots.py), [delivery](../../delivery/valuation-rules-and-cash-snapshots-20261014.md) |

## Income, accrual stocks and costs

23 October: daily earned interest is optional by default. Include every valid
supplied eligible input; absent bond/date coverage is frozen and prominently
reported as not supplied/not included, not assessed zero. Explicit
`requireCompleteAccruals` enforces full daily coverage. Invalid supplied inputs
and other required inputs still block. Newly supplied missing interest invalidates
staged publication until recalculated; no published result is rewritten.
[Delivery](../../delivery/optional-bond-accruals-20261023.md).

[Typed daily-interest follow-up](../../delivery/typed-daily-interest-20261014.md):
daily earned amount/currency are mandatory table columns. Accumulated balances
and movements are supplementary; when absent the earnings-only calculation does
not claim balance reconciliation or receivable-FX assessment. The detailed bridge
below applies only when those inputs are supplied, not to every minimal record.

Market P&L is distinct from gross/net economic P&L. Gross adds explicitly recorded income; net adds signed costs/adjustments. Dividend and reset flows use their explicit classification. PAYMENT_ONLY contributes no new income. Current bond coupons are PAYMENT_ONLY: interest is recognized through assessed daily earnings. Reset classification does not by itself prove reconciliation with a swap mark; supplied whole-swap marks are supported, while modelling funding/reset cashflows remains outside scope.

Bond input bridge: opening accrued balance + daily earned interest + signed balance movements = closing accrued balance. Store local and reporting balances and daily earnings separately. Add **daily earned** to ACCRUAL, not the full closing accrued stock. FX on the opening accrued receivable is separately retained as CARRY. Allocate assessed canonical-instrument earnings once, not once per listing. Coverage follows eligible daily exposure, including weekends and maturity-day disposal; assessment/day-count/nominal eligibility remain Ops responsibilities, not an automatic coupon engine.

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

October 15: [coupon schedules and payment confirmations](../../delivery/bond-coupons-20261015.md)
are retained informational inputs outside the calculator. Daily earned interest
continues through `nav.daily_accrual_input`; confirmation alone neither adds
income nor clears the accrued stock. Automatic entitlement, receivable and
stock/cash reconciliation remain separate work.

Independent provider/custodian reconciliation, representative scale tests, queued calculations, automatic non-ledger source-impact assessment, full cash P&L/NAV, broader corporate actions, discounted forward MTM and unsupported-product pricing remain separate work. This matrix documents/test-pins the supported engine; it does not eliminate those boundaries.
