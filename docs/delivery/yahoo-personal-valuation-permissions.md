# Yahoo personal valuation permissions — 2026-10-09

> Historical activation checkpoint. Its single-currency and pending RAW-normalization limitations below were subsequently addressed by [economic P&L v3](economic-pnl-implementation-2026-10-09.md) and [derived Yahoo RAW prices](yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09). [Historical EUR/GBP eligibility](yahoo-eurgbp-valuation-setup-2026-10-09.md) was later extended for an explicit bounded scope. The original authorization, tests and activation dates remain evidence of this step.

## Delivered and activated

The owner explicitly requested use of the existing Yahoo data for valuation in
this local personal research project. Added an operator-only, dry-run-by-default
command, `scripts/enable_yahoo_personal_valuation.py`, and provider-scoped activation
in `market_data/providers/yahoo/valuation_permissions.py`.

Activated both existing datasets for the current personal tenant:

- `YAHOO_PERSONAL_EQUITY_DAILY` (`01a11302-d25d-7093-9827-3893ed3c6d86`).
- `YAHOO_PERSONAL_FX_GBP` (`01a11cdb-8a1b-7dfd-ac86-2e0a4b4c31cd`).

Each now has a tenant VALUATION entitlement and a conjunctive NON_DISPLAY
requirement backed by an attributable PERSONAL_DECLARATION activity grant. The
description records the actor, tenant, real authorization timestamp and owner
request. This is not provider consent, a contract or commercial licensing
clearance. No acquisition permission is replaced, and no client reporting,
redistribution, other-tenant or commercial right is added.

The command requires active MARKET_DATA tenant-admin authority and VALUATION
module access, active personal source rights, and one of the two existing Yahoo
datasets. It locks each dataset, is repeatable, refuses suspended or unresolved
records rather than reactivating them, and commits all requested datasets together.
No source observations, booking records or pricing policies are changed.

## Date semantics and limits

NON_DISPLAY activity rights start today. The declaration explicitly authorizes
current calculations over the dataset's existing business-date scope; it does
not claim that the owner authorized valuation in the past. The tenant coverage
starts at the existing dataset valid-from date because selection checks both the
market date and current access. Existing dataset dates are not broadened:
equities start 2026-10-06; FX starts 2026-10-08. Earlier FX eligibility is therefore
still a separate historical-scope issue. Older recorded failures remain unchanged.

This fixes the reported NO_VALID_ENTITLEMENT barrier, not all valuation readiness.
Split-adjusted prices still require the separately documented evidence-based
normalization work. The engine remains single-currency, so TTE EUR to strategy
GBP conversion is not implemented. Governed sealed-calendar checks also remain.
No Yahoo prices are relabelled RAW or exchange-official to bypass those checks.

## Verification

- New permission tests failed before implementation (missing activation module).
- Isolated focused run: `test_yahoo_valuation_permissions.py`,
  `test_yahoo_market_data_onboarding.py`, `test_yahoo_fx.py`: **16 passed**.
- Python compile check passed. Live dry-run succeeded without committing, then
  explicitly applied the owner-authorized changes using the same arguments.
- Current NON_DISPLAY rights: PERSONAL allowed for both datasets; COMMERCIAL denied.
- Read-only TTE resolution under DEFAULT_EOD v3 with purpose VALUATION:
  2026-10-06 SELECTED `75.720001220703`; 2026-10-07 SELECTED `75.419998168945`.
  These are original split-adjusted source values, not normalized valuation marks.
  No new valuation attempt, financial batch or trade was created for this check.

## Execution ruling

Address the current rights error as a separate activation step. Do not silently
expand this into the proposed price-basis plan, or declare conversion complete.
The price-basis plan remains pending and is the next economic prerequisite.
Sequential execution, existing feature checkout, focused tests only; no commit/push.
