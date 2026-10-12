# P&L demo retirement and fresh start

> Historical retirement checkpoint. The replacement engine was subsequently implemented; see [economic P&L delivery](economic-pnl-implementation-2026-10-09.md) and [current valuation capabilities](../product/features/valuation-and-pnl.md). The exclusions below describe the retirement task's scope.

Date: 2026-10-07. Owner request: discard the old home-page P&L demonstration and start from the current codebase, with meaningful code comments. Status: retirement implemented; replacement calculation engine not implemented.

## Delivered boundary

The home page already redirects to Instruments. The remaining demo entry points have been retired:

- The menu now opens **Valuation & P&L** at `/valuation`, using signed selected-tenant context and an explicit NOT IMPLEMENTED state. MARKET_DATA access is required to see the development landing state; unavailable access is not labelled an outage.
- Old `/pnl/{portfolio}` bookmarks redirect to `/valuation`. No UK/US demo strategy alias, fixed as-of date, local/demo tenant fallback or financial API call remains in those pages.
- `/api/portfolios/{portfolio}/pnl` returns a non-financial 410 tombstone without calling the reference API. It exposes no tenant/resource data and does not require financial authority to explain public endpoint retirement.
- `/v1/portfolios/{portfolio_code}/pnl` retains its tenant-membership gate and returns RFC9457 `410 / valuation.demo_retired`. OpenAPI marks it deprecated and declares only the 410 problem response, not a successful P&L result. Authentication/validation errors remain possible before the tombstone.
- The legacy repository calculator, its latest-observation/weekday helper, response DTOs, client method, formatting helpers, cutoff lab and orphan synthetic cutoff fixture were removed. Product-specific legacy P&L exceptions/guards were removed; booking authority, economics, corrections and lifecycle code remain.

Comments explain why the new landing state must not query prices, manufacture zero/partial totals or revive old aliases, and why the compatibility routes are tombstones rather than another calculator. Comments should document economic assumptions and invariants, not narrate every statement.

No migrations, operating data deletion, seed deletion, price repair, trade mutation, rights grants, commits or pushes were performed. Existing synthetic strategies/trades/observations remain because booking, history, resolver and rights regression fixtures use them. The removed tracked demo code remains recoverable from Git history. Historical delivery reports/specs retain their dated evidence; this report and the architecture index supersede their demo-delivery claims.

## Fresh implementation direction — not a delivery claim

Build a dedicated valuation boundary instead of reinserting calculations into the reference repository or browser:

1. Position reconstruction: replay economic executions and supported recorded corrections/lifecycle events at explicit effective and information cutoffs. Do not derive historical holdings solely from today's mutable trade status. Keep exact quantities and their units; do not aggregate incompatible contracts/listings/currencies.
2. Valuation: consume frozen resolver selections and booking/instrument economic conventions. Distinguish price, rate, notional, accrued interest, exposure and monetary value. Missing prices/FX/calendar coverage or unsupported products must remain explicit exceptions. Persist calculation version, trade/event evidence and input snapshot references.
3. Daily economic P&L: reconcile opening/closing values with intervening trades, fees and recognised income. Define cost-basis/realised-unrealised and FX attribution conventions before presenting them. Settlement and accounting execution stay separate, but economically material income, corporate actions and lifecycle changes cannot disappear from a claimed complete result.

Start with controlled single-currency equity/ETF fixtures, then multi-currency cases, then explicit product adapters. This retirement pass does not create an empty engine package, expose invented valuation endpoints, support additional instruments, certify reference-calendar coverage or activate Yahoo valuation rights.

## Execution and review evidence

Bounded design was reflected in chat; standing owner instructions waive another approval pause and require sequential execution/current checkout. Tests were written before changes. API RED: existing demo results200 / unknown strategy404 instead of410; OpenAPI lacked deprecation. Frontend RED: missing fresh page, legacy BFF calculation attempt and hardcoded portfolio navigation. Additional RED→GREEN coverage fixed the restricted-page header label and explicit410 problem schema.

The obsolete demo-output/product-guard tests were replaced by retirement/no-results coverage; booking assertions and market-data rights/resolver tests remain. API retirement has real HTTP coverage for both demo aliases, an unknown strategy and missing tenant authority. Frontend coverage exercises actual page rendering, selected-tenant redirect, module denial, old bookmark redirect, navigation and the non-forwarding BFF.

Verification:

- Focused isolated backend: 133 passed, 10 warnings, 111.57s (`logs/pnl-retirement-backend-green.log`); runner exit0 and owned database cleanup. Subsequent pure OpenAPI schema check:1 passed,1.76s.
- Final frontend:127 files /601 tests passed,11.71s (`logs/pnl-retirement-frontend-final-3.log`). Ops-console typecheck passed (`logs/pnl-retirement-types-final-3.log`); generated-contract typecheck passed (`logs/pnl-retirement-types-final-2.log`). OpenAPI consistency and Git whitespace checks passed.
- Full isolated Python suite:1,114 passed,482 warnings,853.01s; runner exit0 and successful owned database cleanup (`logs/pnl-retirement-full-python.log`). Warnings include SQLAlchemy deprecations and Pydantic field-metadata warnings; passing is not a claim of warning-free code.
- Read-only browser: old `/pnl/us` redirected to `/valuation` after selecting the existing demo tenant; new menu/status displayed without a total or captured client warnings/errors. No browser financial writes.

Review: separate author self-review, not independent signoff, under the requested no-subagent workflow. Retirement scope and remaining engine work are explicit. No unsupported valuation result is advertised.

Completion: retirement, dependency cleanup, code comments, documentation, generated contracts, frontend and backend verification are complete. Older screen specifications are explicitly marked retired. No replacement position/valuation/P&L implementation is claimed. The lower Python test count reflects removed demo-only expectations and guards plus the new retirement tests, not removal of booking or resolver coverage.

Related deliveries: [Pricing policies](composite-pricing-policy-alpha.md), [tenant calendars](tenant-fund-and-strategy-calendars-alpha.md), [historical booking and corrections](historical-booking-and-record-corrections-alpha.md). Their implemented boundaries remain prerequisites for the fresh engine.
