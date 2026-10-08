# Reproducible valuation and P&L alpha

Status: implemented bounded market-only alpha, verified and activated locally, 2026-10-07.

## Intent and boundaries

Replace the retired demo with positions valuation and economic trading P&L, not full fund NAV, settlement processing, accounting postings or percentage performance. Use Fortem-core `data/sources/ops/pnl_attributions` as a behavioural reference, not a runtime dependency. Start with plain listed equities/ETFs; unsupported products, missing economic events, unknown calendars or ineligible data must block complete publication. No new market-data permission is inferred from this work.

## Architecture

A dedicated `valuation` Python package separates pure decimal calculation, event replay, frozen-input orchestration and transaction-bound attribution persistence. The reference API is transport only. Reuse `trd.position_snapshot`, `nav` frozen inputs and `md` policy resolution where compatible; do not duplicate ingestion or implement calculations in the browser.

Position replay has an economic cutoff and a recorded-information cutoff. BOOKED economics and ordered events are authoritative; current mutable lifecycle status is not historical evidence. CANCELLED/SUPERSEDED remove the original record in the relevant historical view; CORRECTED identifies replacement lineage. Unknown lifecycle events fail closed. Missing legacy BOOKED evidence is an exception, not an invented snapshot.

Quoted values normalize with frozen unit multiplier / quote factor. Market valuation, notional exposure and contractual PV remain different measures. Baseline equities use shares/units and positive quoted prices with explicit unadjusted/split-adjusted basis. Split/dividend handling cannot be silently inferred from adjusted close.

## Calculation and attribution

For an unchanged signed lot q, normalized prices P0/P1 and reporting-currency FX F0/F1:

- PRICE = q * (P1-P0) * F0
- FX = q * P0 * (F1-F0)
- PRICE_FX_CROSS = q * (P1-P0) * (F1-F0)
- Their sum equals q * (P1*F1-P0*F0).

Opening holdings use opening marks; period executions use execution price and execution FX, not yesterday's mark. Period sales remain attribution subjects even when the closing holding is zero. This gives a trading P&L bridge without pretending to maintain a bank cash ledger. Income and costs are distinct signed components with economic date and source evidence; unsupported income/corporate-action coverage prevents claims of complete total P&L.

Use Decimal throughout monetary calculations and canonical serialization; reject binary floats, nonfinite values, invalid factors and ambiguous units. Methodology version and exact inputs determine identity. Component totals must reconcile exactly before storage rounding; explicit product/currency tolerances govern external comparisons. Capital contributions are not profit. Realised/unrealised tax-lot reporting is deferred.

## Review and publication

Technical calculation runs and business review batches are different objects. Batches belong to one tenant/strategy/value date. Staging does not change published results. Authoritative refresh and incremental supplementation are explicitly different modes. Immutable attribution versions retain inputs, method, components and supersession. Identical inputs are idempotent. Publication is atomic, rejects stale base populations and unresolved blocking validation, and requires reviewer authority. Self-publication is disabled by default; any personal-alpha exception must be explicit and recorded.

Subjects are typed TRADE, POSITION, CASH_BALANCE, STRATEGY, FUND and FUND_SHARE_CLASS; implement only subjects for which authoritative ownership exists. Database FK/scope checks must enforce actual ownership. Do not force strategy expenses into synthetic trades. Manual adjustment requests require reasons and independent approval; corrected inputs instead trigger upstream recalculation. Adjustment/allocation workflows can follow the first read/review/publish release, never an uncontrolled edit of calculated results.

## Operational evidence and validation

Run attempts survive financial rollback. Persist structured stage events, stage timings, counts, safe failure codes and correlation identifiers. Never dump licensed raw data, credentials or trade payloads into general logs. Financial evidence is immutable and access-controlled; operational status is not a financial result. Reviews retain Ops explanations, reviewer decisions and publication history.

Validation covers scope/units/lifecycle, input coverage/rights/freshness/calendars, component arithmetic, opening-to-closing bridge and external comparison when provided. Missing external evidence is NOT_COMPARED, not MATCHED. A failed line must not disappear from a claimed complete total. Calculated and provider P&L comparisons must align scope, currency, dates and income conventions.

## Acceptance

First-release refinements: VALUATION and MARKET_DATA modules are both required; administrator writes and independent publication remain mandatory. Only complete AUTHORITATIVE staging is enabled. INCREMENTAL population/bridge reconciliation, manual adjustments, external comparison imports and broader attribution subjects are explicitly deferred. No rights or reviewer exceptions are granted automatically. Operational event recording uses wall-clock database timestamps across the independently committed attempt and financial transactions; each engine-owned API transaction receives configured statement/lock budgets.

Lightweight pure tests first: exact decimal decomposition, shorts, new buys/sales, zero closing holdings, information-cutoff replay, cancellations and rejection of unsupported events. Then isolated PostgreSQL tests for immutable versions, idempotency, tenant isolation, rollback-surviving failures, stale publication and reviewer controls. Finally API/UI contract tests and full regression suites. No operating trades or market data are rewritten.

## Research and reference basis

Checked 2026-10-07. [OpenGamma calculation flow](https://strata.opengamma.io/calculation_flow/) supports separation of setup, frozen input preparation, calculation and reporting; its Java implementation is not a dependency recommendation. [OpenGamma market data](https://strata.opengamma.io/market_data/) distinguishes observations from portfolio-derived PV. [CME money calculations](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf), updated June 2015, distinguishes futures variation from ordinary asset valuation. [GIPS handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/) informs trade-date/income/capital-flow treatment; requirements apply to GIPS compliance claims, not universally to this alpha. [OWASP logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) supports correlated events, restricted sensitive information and distinct audit/operational purposes.

Local references: [attribution subjects](../../architecture/market-data-and-valuation/pnl-attribution-subjects.md), [fresh-start scope](../../delivery/pnl-demo-retirement-and-fresh-start.md), Fortem-core `attributions.py`, `models.py`, `repository.py`, `KNOWLEDGE.md`. Its staged/official split, idempotency and stale population checks are retained conceptually; float normalization, trade-only ownership and default signed-notional allocation are not copied.
