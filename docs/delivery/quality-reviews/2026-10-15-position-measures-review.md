# Position monetary measures: implementation and best-practice review

**Status:** Scoped code/documentation review; not production or financial sign-off  
**Content type:** Review  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-15

## Scope and conclusion

Reviewed all currently implemented **referenceNotional, economicExposure and
marketValue** preview branches, not just the new forward helper. Traced the strategy
API and server UI, holdings/reconstruction, frozen product conventions, selection,
reporting FX, accrued-stock lookup and numerical/integration assertions. This is an
author's sequential self-review, not an independent audit of the entire repository,
all provider adapters or every lifecycle/accounting engine.

The bounded calculations keep amounts, exposure and MTM distinct. They are suitable
as an explicitly limited preview; they are **not yet a complete risk/NAV foundation**.

## Current measure matrix

All available amounts retain native and separately governed strategy-currency values.
Missing market inputs/conversions are unavailable/local-only, never synthetic zero.

| Product | Reference notional | Economic exposure | Market value | Main boundary |
| --- | --- | --- | --- | --- |
| Equity / ETF / fund | Current signed value | Same | Same | Agreed project convention, not original purchase cost; native compatible mark/NAV units required |
| Plain bond | Signed face | Signed face | Dirty price, otherwise clean plus assessed accrued stock | Daily earned interest is not the stock; do not duplicate a canonical accrued balance across listings |
| Unit delta-one index swap | Units × frozen notional per unit | Units × current index level × leverage × performance direction | Units × whole-swap quote ÷ quote factor | Whole-swap quote already includes orientation/financing/leverage; only native index, no interim resets |
| Nominal index swap | Signed nominal | Unavailable | Nominal × whole-swap quote ÷ factor | No invented underlying units/reset price |
| Linear cash-settled index future | Contracts × exact-expiry futures price × frozen monetary multiplier ÷ factor | Same current monetary notional | Unavailable | Listing multiplier not applied twice; no fabricated clearing value |
| Deliverable FX forward | Signed base amount | Two contractual currency legs, separately translated | Unavailable | Not discounted FX exposure or model MTM; original K fixes quote obligation |

Options, structured/autocall measures, physical/crypto/inverse/quanto futures and
general derivative pricing remain unsupported. Separate dated cash snapshots are
not generic investment-trade holdings or part of this endpoint's three measures.

## Findings and implementation follow-up

1. **Fixed in this delivery:** the new forward path initially treated numerically
   equal frozen rates with different Decimal scales as different agreements.
   Comparing rates as Decimal now permits normal maturity closure; the real
   closure/cancellation regression verifies both legs disappear and reopen.
2. **Fixed in this delivery:** a base-flat mixed-agreement forward could otherwise
   be filtered out before validation despite residual quote obligations. The route
   now retains an exception row before pagination. Mixed agreements are rejected;
   they are not valued using a sampled or average rate. See resolved MEASURES-004.
3. **Remaining operational weakness:** paginated output still reconstructs complete
   strategy history. Forward proof loading adds per-bucket reads, including flat
   forward checks before pagination; marks/FX are cached per preview but history is
   not checkpointed. No large-population latency benchmark exists. See MEASURES-005.
4. **Deliberate coverage gaps:** true forward MTM, futures clearing/variation-margin
   value, option measures and reset-aware swaps need explicit inputs/methodologies.
   Withholding a value is safer than confusing notional with a NAV asset. No change
   to their support classification was hidden behind these previews.
5. **Before weights/risk:** the reference-notional column intentionally has different
   product meanings; two FX legs are not a scalar. Introduce explicit, reviewed risk
   definitions and frozen consumer inputs rather than adding every exposure column
   into a total. There is no risk-weight or regulatory-compliance claim today.
6. **Acceptance gaps:** independent provider/custodian comparisons, production-scale
   tests, more native currencies/market conventions and a current browser walkthrough
   remain distinct from the synthetic numerical and component tests below.

The earlier split-price/unit and fund NAV identity fixes (MEASURES-001/002) remain
covered by the affected regression selection. The new path does not weaken native
mark proof, same-group strategy authority, source display rights or publication.

## Source-backed review

Primary pages opened/read on 2026-10-15. These support distinctions, not certification
of this project or a requirement to install their libraries:

- [OpenGamma Strata FX-single pricer](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/fx/DiscountingFxSingleProductPricer.html)
  separates forward-rate, present-value and currency-exposure calculations; the
  latter two discount the payments. Our contractual legs intentionally do not claim
  that discounted exposure calculation. **Recommendation:** retain explicit labels
  and add eligible discounting or sourced MTM before claiming true forward MTM.
- [CME equity-index notional explanation](https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/discover-equity-index-notional-value-and-price)
  derives monetary notional from futures price and contract multiplier. Our contract
  count applies the frozen monetary multiplier once; this is not contract MTM.
- [CME money calculations](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf)
  describes settlement variation, contract value factors and product-specific rounding.
  **Recommendation:** future clearing-value work must retain the relevant settlement
  boundary/rounding, rather than assume zero or use full notional as an asset.
- [OpenGamma Strata fixed-coupon bond pricer](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/bond/DiscountingFixedCouponBondProductPricer.html)
  distinguishes clean/dirty price, accrued interest and date-dependent calculations.
  Its decimal quotation differs from our explicit per-100 convention. **Recommendation:**
  keep quote factor, accrued balance and economic date explicit; never add the daily
  earned amount as though it were the whole accrued stock.

Equal equity/ETF/fund measures, signed face exposure, the preview's swap reference
definition, and the chosen staged scope are **project conventions**, not universal
industry or regulatory definitions inferred from those sources. Independent model
validation and legal accounting requirements remain outside this scoped review.

## Verification

Final affected backend run: **79 passed**, one existing Starlette/httpx deprecation
warning, on an owned disposable PostgreSQL database. Command:

```powershell
.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_fx_forward_measures.py tests/test_fx_forward_measure_inputs.py tests/test_position_measures.py tests/test_future_measures.py tests/test_measure_inputs.py tests/test_position_measures_assurance.py tests/test_future_measure_inputs.py tests/test_strategy_holdings_api.py tests/test_fx_forward_valuation.py tests/test_fx_forward_pnl.py -q -p no:cacheprovider
```

Focused UI command passed **16 tests**:

```powershell
pnpm --filter ops-console test src/components/strategy-measures.test.tsx src/components/strategy-workspace.test.tsx src/lib/server/api-read.test.ts
```

`pnpm typecheck:ops-console`, `pnpm contract:check` and scoped whitespace checks
passed. `pnpm contract:generate:check` returned nonzero because it compares against
committed HEAD, while this feature checkout already contains uncommitted generated
API changes. Direct regeneration succeeded; a second generation preserved the file's
SHA-256 exactly against current OpenAPI. This is not reported as a passing standard
Git-based freshness check. No existing feature work was reset or committed.

The new tests were first run against missing behavior, then passed with the
implementation. Later cases cover real bookings and permissions, including a
forward-only display-denial assertion rather than relying on an equity row failing
first. Normal closure also pins equality of numerically equal rates at different
scales. Earlier test-fixture mistakes (hand-entered arithmetic, booking-response
shape, EOD maturity cutoff) were corrected without weakening production checks.

No full suite, operating financial writes, browser walkthrough, scale benchmark or
independent financial sign-off claimed. API activation is recorded in the delivery.
