# FX-forward position measures implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` sequentially, following the user's execution preference. Execution completed 2026-10-15 for the bounded scope; see [delivery](../../delivery/fx-forward-position-measures-20261015.md) and [review/verification](../../delivery/quality-reviews/2026-10-15-position-measures-review.md). Browser and financial sign-off are separate.

**Goal:** Extend the read-only position-measures preview to deliverable FX forwards without confusing contractual currency exposure with discounted contract MTM.

**Architecture:** Reuse frozen booking validation and existing position reconstruction. Add per-measure currency handling and two explicitly labelled contractual currency legs; reuse governed reporting FX for each leg. Keep existing rate-based P&L unchanged and discounted MTM unavailable in this first slice.

**Tech stack:** Python Decimal, SQLAlchemy/PostgreSQL, existing reference API, Next.js/TypeScript.

**Spec:** The agreed monetary-measures intent and boundaries in [existing measures](../../delivery/position-monetary-measures-20261015.md) and [FX-forward rate-based P&L](../../delivery/fx-forward-rate-pnl-20261014.md), extended by the proposed definitions below. No weights, tax, FIFO, accounting or new pricing engine.

## Proposed definitions

For a purchase of EUR 1,000,000 against USD at an agreed 1.10 USD/EUR:

| Measure | Result | Meaning |
| --- | --- | --- |
| Reference notional | +EUR 1,000,000 | Signed base-currency notional outstanding. |
| Contractual currency legs | +EUR 1,000,000; −USD 1,100,000 | Amounts to receive/deliver; not two additional trades or cash balances. |
| Strategy-currency equivalents | Translate each amount separately into GBP | Use the selected policy's eligible as-of FX observations. Do not net these into one exposure number. |
| Market value / MTM | Unavailable, with reason | Existing outright-rate observations alone do not establish discounted MTM. |

The contractual quote obligation uses the **booked agreed rate**, not today's forward rate. A sale reverses both signs. Opposite bookings at different agreed rates must retain their different quote obligations; never derive the aggregate quote leg using one arbitrary trade's rate. Preserve existing position identity, closure matching and residual-obligation safeguards rather than introducing pair-level netting.

These are **undiscounted contractual currency legs**, not discounted currency exposure, delta or another risk sensitivity. This distinction matters before later NAV-based risk ratios.

## Global constraints

- Preserve same-strategy authorization, tenant isolation, source display/use permissions and policy/information cutoffs.
- Exact Decimal calculations and string serialization; missing amounts or reporting FX never become zero.
- Reuse `positions/fx_forward.py` validation, including its bounded legacy rules. Do not add another legacy fallback.
- No changes to bookings, published valuations, maturity closure, cash balances, payment recognition or existing P&L mathematics.
- No spot substitution for an outstanding contract's forward mark; spot reporting conversion is a different operation.
- No operating seeds, migrations, provider calls or restarts for plan verification; isolated databases only for implementation tests.

## Review focus

- Base currency differs from trade/quote currency: retain the right currency for each measure.
- Multiple fills, shorts and partial closes: derive each obligation from compatible frozen economics, not one sampled agreed rate.
- Corrected/cancelled bookings and maturity closures: reuse authoritative reconstruction; do not recreate extinguished exposure.
- Missing conversion or revoked display rights: preserve permitted local amounts only; do not leak protected evidence.
- Existing scalar measures: additive leg support must not alter equity, fund, bond, swap or future results.

## Task 1: Exact contractual-leg calculation

**Files:** Modify `valuation/position_measures.py`; create `tests/test_fx_forward_measures.py`.

**Interface:** Add `fx_forward_legs(base_amount: Decimal, agreed_rate: Decimal) -> dict[str, Decimal]`, returning `baseAmount` and `quoteAmount` with `quoteAmount = -baseAmount * agreed_rate`. Currency identity comes from validated frozen conventions, not this arithmetic helper.

- [x] Write failing tests: +1,000,000 at 1.10 gives +1,000,000 / −1,100,000; negative notional reverses signs; fractional amounts remain exact; non-finite quantities/rates and non-positive agreed rates fail.
- [x] Run the new pure tests and confirm the expected failure.
- [x] Implement the helper using existing Decimal precision/error conventions; keep current product helpers unchanged.
- [x] Rerun the pure tests and existing monetary-kernel tests.

## Task 2: Scoped preview adapter and response

**Files:** Modify `valuation/measure_inputs.py`; reuse `positions/fx_forward.py`, `valuation/fx.py` and `apps/reference_api/strategy_workspace.py`; create `tests/test_fx_forward_measure_inputs.py`.

**Response:** Keep existing scalar measure fields unchanged for existing products. FX-forward `referenceNotional` uses base currency. `economicExposure` adds `representation: "CONTRACTUAL_CURRENCY_LEGS"` and `legs`, each with `role` (`BASE`/`QUOTE`), `localAmount`, `currency`, `strategyAmount`, `strategyCurrency` and status. Its scalar amounts remain null and its status is `MULTI_CURRENCY`; never treat that status as a scalar available amount. `marketValue` remains `UNAVAILABLE` with a readable missing-discounted-MTM reason.

- [x] Add failing disposable integration cases for the EUR/USD/GBP example; direct/inverse reporting FX; base or quote equal to strategy currency; missing one conversion; short positions; multiple fills at different rates; partial/full maturity closure; correction/cancellation; protected evidence and cross-strategy access.
- [x] Run the focused file and establish failures before implementation.
- [x] Validate the original booking facts through the existing forward normalizer, using the required authoritative row/event facts. Derive the remaining obligations using reconstructed movements and compatible frozen agreements. Reject unsupported ambiguity per row, without inventing an average contract or hiding residual obligations.
- [x] Resolve reporting FX independently for each native measure currency; retain rate orientation, dates, observation IDs and evidence hashes. A missing conversion produces `LOCAL_ONLY` for that leg, not a zero or guessed cross rate.
- [x] Run the new integration cases plus existing measure-input, FX and forward booking/valuation regressions through the owned disposable runner. Do not expand into the full suite by default.

## Task 3: Readable measures UI and documentation

**Files:** Modify `apps/ops-console/src/components/strategy-measures.tsx` and its test file; update [methodology](../../architecture/market-data-and-valuation/valuation-methodology.md), [F37 capability](../../product/features/valuation-and-pnl.md), [register](../../product/feature-register.md) and [implementation map](../../product/feature-implementation-map.md). Add a delivery record after verification.

- [x] Add failing UI cases for two signed currency legs, per-leg GBP equivalents, a missing conversion and unavailable MTM; retain scalar-product rendering tests.
- [x] Extend the response type and rendering before the existing null-amount shortcut. Label the FX case **Contractual currency legs**, with receive/pay direction and an explicit undiscounted/not-delta explanation. Keep formulas on the server.
- [x] Run focused UI tests, TypeScript and applicable contract checks; review one isolated mock long and short example. Do not book operating trades merely for acceptance.
- [x] Record formulas, evidence, limitations and exact verification performed. Clearly distinguish implementation, activation and browser acceptance. Update the three capability documents together.

## Separate follow-up: true MTM

Do not quietly introduce a curve engine during this slice. Choose a governed sourced monetary MTM, or an explicitly specified discounted methodology with eligible inputs, before enabling market value. An outright-rate method may use `N × (F − K) × DF_quote` only where its rate, maturity, discounting/collateral and valuation conventions are compatible; never assume `DF = 1` and label the result true MTM. Existing undiscounted P&L remains unchanged.

The reference distinction is supported by [OpenGamma Strata's FX-single pricer](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/fx/DiscountingFxSingleProductPricer.html): forward rate, discounted present value and currency exposure are separate operations; its currency exposure discounts the individual payments. Our first-slice contractual legs intentionally do **not** claim to implement that discounted exposure calculation.
