# Economic strategy P&L: agreed foundation

Status: requirements and researched recommendation, not implemented. 2026-10-09.

## Agreed requirements

- Separate market P&L (PRICE, FX, PRICE_FX_CROSS) from economic P&L including
  instrument-linked income, daily accruals, resets, fees and approved adjustments.
- Convert valuation amounts into strategy currency; ordinarily trade-to-strategy
  currency applies when both booked and market values use the trade currency.
- Select price/NAV dates and FX dates independently through pricing policies.
- For the discussed T+1 fund sign-off convention, strategy T uses NAV(T-1),
  and its opening comparison uses NAV(T-2), following the fund valuation calendar.
  This is configured convention, not unrestricted stale-price fallback.
- Preserve execution-price entry basis and explicit daily execution-FX conventions.
- Cash has unit price 1; maturity/termination requires explicit product treatment.
- Ops may book DIVIDEND and RESET cash-flow trades linked to the instrument and
  strategy, with an economic date independent from payment date. No automatic
  settlement or accounting engine is required for this alpha.
- Bond daily records are position-scoped by tenant, strategy, instrument, date
  and accrual type, with trade lineage where calculation terms require it.
- Store both daily earned interest and accumulated interest balance, each in
  instrument and strategy currency, together with FX/source evidence.
- Only daily earned interest is added to daily income P&L. Coupon payments,
  acquisitions/disposals and FX translation mean daily income is not simply
  the difference between accumulated balances. Previously earned interest is
  not recognized a second time when the coupon is paid.
- Staging -> amendment -> publish remains the operational flow.

## Research checked online

[CFA Institute GIPS Standards Handbook for Firms](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/),
November 2020 edition, read online 2026-10-09, provisions 2.A.8, 2.A.10 and 2.B.3:
total return covers capital movement and earned income; interest-bearing
investments use accrual accounting, and accrued income belongs in beginning and
ending portfolio values. Income already included in market prices must not be
counted twice. Dividend recognition on ex-date is recommended over payment-date
recognition. These are requirements/recommendations within GIPS compliance,
not a claim that this personal alpha is GIPS-compliant or a complete accounting system.

Our application: decompose clean market movement and daily earned interest;
retain accumulated balances for valuation/reconciliation, including their FX
translation where applicable. Use dirty quotes only with an explicit decomposition
so separately added daily interest is not duplicated. Ops controls economic dates
for booked flows; payment date does not create a second income component.

## Workflow recommendation

- Stage immutable calculated candidate evidence, without changing published P&L.
- Allow amendments while staged: correct inputs and recalculate, or submit an
  explicit component adjustment with source, reason and actor. Do not silently
  edit calculated totals. Record each new candidate/version and what it supersedes.
- Publish the selected reviewed candidate atomically after reconciliation,
  completeness and stale-input/population checks, using existing independent review.
- Later corrections create replacement candidates; published history is never
  overwritten. Operational failure evidence remains distinct from financial results.

## Implementation readiness and proposed order

Enough domain information exists to write a bounded staged implementation plan.
Use the legacy ValuationInputs/FundPNL intentions and pnl_attributions workflow,
not a literal copy of its dataframe assumptions or trade-owned persistence.
Keep the current position engine and trade/event lineage.

1. Market foundation: compatible price basis, frozen FX and reconciled PRICE/FX/CROSS.
2. Instrument-linked economic flows and daily bond accrual side inputs, including
   explicit missing-input versus confirmed-zero coverage. Initially allow reviewed
   Ops/imported accrual amounts rather than silently build every bond pricer.
3. Fund NAV conventions, cash and product-specific maturity valuation handlers.
4. Staged amendments, reviewed publication and readable financial/input evidence.

Implementation details still need explicit specification: eligible accrual nominal
around settlement/coupon/ex-coupon dates; accrual-source coverage; trade-specific
yield calculations; execution FX convention; and each supported product's maturity
economics. Use per-product supported scope, not guessed generic overrides. Yahoo
normalization, historical FX dataset coverage, FX selection and sealed reference
calendars remain technical prerequisites, not already delivered capabilities.

## Legacy frontend reference inspected

Reviewed the source under `fortem_front/apps/portal-web/src/pages/pnl-attributions`
(not a rendered browser session). The main screen selects fund/date and batch,
shows instrument-level market/gross/net totals and new/existing/maturing/reference
counts, and drills into attribution groups and individual trade components.
Staged results support position/trade additions and net-P&L adjustment requests,
with reason/source and a request-history sidebar. Publication is a separate
confirmation, with the staging actor prevented from publishing in the UI.

Recommended adaptation: strategy/date rather than fund-only selection, a position
summary with trade/event lineage, readable prices/FX/accrual evidence, separate
component additions versus input correction/recalculation, and explicit amendment
request states. Published batches remain read-only; later corrections stage a new
version. Pending/stale request and independent-review enforcement stays server-side.
Do not copy weekend-only date restrictions (use strategy calendars) or the assumption
that every position-level addition must be allocated to individual trades.
The legacy publish button memoizes with an empty dependency list despite using
changing batch/user state; avoid carrying that stale selection risk into the new UI.
