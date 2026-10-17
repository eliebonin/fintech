# Tenant-one app fixture — 15 October 2026

**Status:** User-authorized app-database seed, verified through the live API. Not a valuation sign-off.

The earlier [connected cycle](mock-valuation-cycle-20261015.md) used disposable databases. The user subsequently requested a visible strategy and trades in tenant one and asked to run the app. This is a separate, explicit operating-local fixture creation, not a claim that the deleted test database was retained.

## Created records

| Record | Value |
| --- | --- |
| Tenant | Platform Demo Tenant / `PLATFORM_DEMO_TENANT` / `00000000-0000-7000-8000-000000000011` |
| Strategy | **MOCK — Bond valuation cycle (GBP)** / `MOCK_BOND_CYCLE_20261015` |
| Strategy UUID | `07ac7abf-7477-4756-90bc-ff254130febd` |
| Classification | PROP_SLEEVE, GBP, ACTIVE; synthetic historical start 2026-09-01 |
| Private canonical bond | **MOCK ONLY — GBP 2% bond maturing 2026-10-01** / `01a13eaa-8441-7270-af80-223f57983330` |
| Contract | Fixed 2% decimal rate .02, semiannual, 30E/360, par/redemption quotation 100; no real issuer identity/ISIN invented |
| Fill 1 | `370946d9-82bf-4fc5-8a85-5ab968581d44`: BUY 60,000 nominal at CLEAN 98.50; total bought accrued 750 |
| Fill 2 | `c4f2311f-6c34-4bd5-a64f-d475e6c6dd66`: BUY 40,000 nominal at CLEAN 98.50; total bought accrued 500 |
| Execution / settlement | 2026-09-30 10:01/10:02 UTC; explicitly simulated T+0 settlement on 2026-09-30, before maturity |
| Counterparty | Existing Bank A Demo plc — synthetic fixture, not an actual execution |
| Totals | Two BOOKED investment trades; +100,000 nominal; clean 98,500, bought accrued 1,250, dirty consideration 99,750 |

These are explicit toy booking inputs, not calculated real-world accrued interest or proof of actual payment/entitlement. Every trade comment and external reference identifies the synthetic seed.

## Safety and execution

[Seed script](../../scripts/seed_mock_bond_strategy.py) defaults to a read-only preview; `--apply` targets only the named local `platform_secm` database on port 54329. Strategy creation, reference proposals/approval, booking-convention approval and trade booking use existing APIs. A clearly named tenant-owned INTERNAL/SANDBOX source supplies source-scoped proposal retry identity; it grants no data rights.

Only the newly created empty synthetic strategy's historical effective date was adjusted directly, with explicit strategy-write authority and an audit event. No preexisting strategy, shared instrument or source price was modified. Stable keys protect both trade fills; source-scoped proposal identity protects retries. Initial manual proposal attempts correctly rejected a missing source identity; no bond/trades were created by those rejected requests. The script was corrected to register its own synthetic source instead of misattributing generated terms to a real provider.

Live API reads returned the strategy and both retained trade details, including BOOKED snapshots, quantities, price/accrual bridge, synthetic settlement evidence and references. Database reads confirmed exactly two trades / 100,000 signed nominal and TENANT_PRIVATE bond ownership for tenant one. No permission grants, maturity closures, coupon confirmations, daily-interest entries, cash balances, valuation calculations or publications were created.

## App and next setup

Subsequent user-approved [mock prices, policy and daily interest](mock-bond-valuation-inputs-20261015.md)
now make September 29 → September 30 valuation runnable with the dedicated v2
policy. A real app run completed and staged at market 500 / gross 510 GBP.
The opening-only limitations below describe this earlier seed, not the later preparation.

Frontend started on port 3000; `/select-context` returned HTTP 200. Existing API on port 8000 remained healthy. Frontend process 33480; temporary startup logs `platform-ui-20261015.*.log`.

Select Platform Demo Tenant and an authorized user, then select this strategy. Use an explicit 2026-09-30 history window: the default last-two-weeks window on October 15 excludes these trades.

This is **opening-ledger setup only**, not yet a complete clickable reproduction of the financial test. The new private bond has no seeded price series, pricing-policy rule, daily-interest inputs, coupon schedule/payment confirmations or cash snapshots. Those must be explicitly populated before a successful full valuation cycle is expected. Lifecycle actions still require existing explicit permissions; admin status is not a bypass. The bond is intentionally past maturity so Ops can exercise the closure workflow later; no closure was auto-booked. The intermittent rebooking finding from the isolated exercise remains open.
