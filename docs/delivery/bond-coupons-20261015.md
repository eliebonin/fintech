# Bond coupon schedules and payment evidence

**Date:** 15 October 2026  
**Status:** Implemented alpha; migration 94/API activated with approval; browser acceptance pending.

## Agreed separation

1. Canonical bonds have informative contractual schedules: explicit accrual periods, payment dates, optional record/ex-coupon dates, sourced rates/amounts per 100/formulas, currency and optional convention metadata. Unknown is not zero. These are future DCF inputs, not a DCF pricer or a completeness certificate.
2. Existing assessed **daily earned interest** continues to contribute to daily valuation. Payment confirmations do not alter earnings. Optional accrued stocks and movements remain in the existing reconciled accrual input path.
3. Ops records actual strategy coupon receipts/payments separately. Positive means received, negative paid. A receipt need not represent the full entitlement. No trade, cash balance, accrued reset, journal or additional interest P&L is created.

Example: opening accrued 990 + earned 10 − coupon movement 1,000 = closing accrued zero. Interest P&L is **10**, not 1,000. The schedule and payment evidence do not populate that reconciliation automatically: Ops supplies the assessed balance/movement evidence where needed.

## Implementation and access

- [Contracts](../../lifecycle/coupon_contracts.py), [tables](../../lifecycle/coupon_tables.py), [service](../../lifecycle/coupon_service.py), [migration 94](../../alembic/versions/20261015_94_bond_coupons.py).
- [API](../../apps/reference_api/coupon_routes.py): `/v1/lifecycle/coupons/options`, `/schedule`, `/schedules`, `/payments`, `/payments/correct`, `/payments/reverse`, `/history`.
- [UI](../../apps/ops-console/src/components/bond-coupon-console.tsx): `/trades/lifecycle?product=coupons`, linked from lifecycle navigation. Choose a permitted strategy and canonical bond UUID, inspect retained schedule versions, maintain explicit rows, filter confirmations and correct/reverse with history.
- Schedule maintenance: `REFERENCE_APPROVE`; confirmation: `LIFECYCLE_BOOK`; correction/reversal: `TRADE_CORRECT`; strategy reads: `LIFECYCLE_READ`. Admin alone is insufficient. No operating grants are added.
- Tenant-owned schedules avoid leaking private overrides through unscoped reference schedules. Versions freeze approved bond terms. Payment revisions retain their original period; new schedule versions never rewrite old receipts.
- Exact decimal strings, typed NUMERIC values, immutable rows, actor/real-operator audit, request keys, revision checks and current authority before replay. Reports project latest revisions before date filtering/count/pagination.
- The BFF allowlists paths/queries and derives identity server-side. Uncertain writes retain the unchanged request for explicit retry.

## Limits / trade-offs

- Explicit sourced periods only: no schedule generator, floating fixing engine, automatic entitlement, DCF discounting, receivable accounting or automatic bank/custody reconciliation.
- A receipt is neither proof of full settlement nor new income. Payment currency can differ from contractual currency without invented FX. Future actual-payment dates are rejected.
- Late receipts after disposal are allowed; entitlement is operator-assessed, not inferred from today's holding.
- Bond suggestions include up to 100 visible traded canonical bonds for the selected strategy; direct canonical UUID entry supports late receipts on other visible bonds. Optional convention metadata still uses UUIDs; full catalogue pickers and bulk upload are later UX work. Latest 25 schedule versions are listed; known historical schedule IDs remain readable through the API. Payment reports paginate the full scoped population.
- Zero-coupon bonds have no periodic schedule in this workflow. Principal redemption remains separate.
- Existing daily-interest valuation, frozen published results and publication authority are unchanged.

## Verification and activation

[Domain/non-interference tests](../../tests/test_bond_coupons.py), [API tests](../../tests/test_bond_coupons_api.py), [UI tests](../../apps/ops-console/src/components/bond-coupon-console.test.tsx), [BFF tests](../../apps/ops-console/src/app/api/lifecycle/[...segments]/route.test.ts).

First focused database run after fixing explicit test-only grants: **12 passed** (coupon domain/API, typed daily interest and bond-redemption API). Eight focused frontend/BFF tests and TypeScript passed. Migration 94 upgraded successfully in the owned disposable database. Additional regression assertions are checked in the final pass below. No full suite.

Expanded focused pass: **24 passed**, including existing accrual and economic-flow regressions, stale revision checks and permission revocation before replay. OpenAPI freshness passed. TypeScript regeneration is byte-identical against the working tree. The repository's `generate:check` exits nonzero because it compares all generated changes to committed HEAD (the checkout already contains uncommitted feature contracts); that is not claimed as a passing clean-Git check. Whitespace checks passed with existing CRLF conversion warnings.

Initial database attempts timed out: Docker was available but the project PostgreSQL container was stopped. Starting that existing container restored connectivity. Initial fixture failures correctly denied missing lifecycle grants; application authority was not weakened.

Final coupon-only pass after the scoped bond-suggestion query: **5 passed**. Final frontend/BFF pass: **8 passed**, TypeScript exit 0. These overlap the 24-test pass; they are not 37 distinct tests.

With explicit user approval, applied **20261015_94** to local `platform_secm` (previous revision 93) and started the stopped API. `/health` returned `status: ok`; served OpenAPI contains all seven coupon paths. Read-only verification found **zero schedules, periods and payment rows**. No operating receipts, trades, grants or valuations were created. API parent process 65324 / server 24812; startup logs are in the Windows temporary directory as `platform-coupon-api-20261015.*.log`. Browser acceptance is not claimed.

## Intent and research

Later same-day [connected mock valuation-cycle acceptance](mock-valuation-cycle-20261015.md)
tests coupon daily-interest non-interference through maturity, amendment, independent
publication and correction/recalculation. It also records an intermittent rebooking
rejection; this is not browser acceptance or an unconditional reliability sign-off.

[Design and authoritative references](../superpowers/specs/2026-10-15-bond-coupons-design.md), [plan](../superpowers/plans/2026-10-15-bond-coupons.md). Announcement, entitlement and receipt are distinct; this schema is a project choice, not an accounting certification.
# Current extension

27 October: the coupon-only schedule is extended by the
[full bond cashflow schedule](bond-cashflow-schedule-20261027.md). The dated
verification below describes the original slice; current names/contracts are in
the [maintained reference](../architecture/trading-and-operations/bond-cashflow-schedules.md).
