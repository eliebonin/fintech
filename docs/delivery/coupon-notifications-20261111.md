# Coupon notifications and read-only inspection — 11 November 2026

## Where and what

Open `/lifecycle`, choose **Bond coupon** or **All events**, then apply strategy/instrument/date filters. Coupon rows use the explicit sourced scheduled payment date, not bond maturity. Counts and pagination cover the full authorised filtered population. **Inspect coupon** opens a read-only drawer showing the schedule period, record/ex dates, source/version, exact per100 amount or formula, position context and recorded confirmations. Technical identities stay in collapsed evidence. Refresh inspection performs a fresh authorised GET.

**Review due means Ops review, not unpaid or overdue payment.** Confirmation recorded means a retained confirmation exists, not that the full coupon or its cash representation has been reconciled. Latest logical receipt revisions are used; reversals and earlier-schedule confirmations remain distinguishable. Earlier confirmations are never transferred to a revised cashflow automatically.

The coupon drawer contains no prepare/book/approve/payment-confirmation or balance-update controls, including at Tier3. It does not match cash trades to EoD balances, generate a cash flow, recognise coupon income, alter daily accruals, reset balances, or run valuation. Receipt can already be represented outside the confirmation dataset; absence is not evidence of nonpayment. Existing financial and confirmation workflows remain separate.

## Scope and trade-offs

- Visibility uses existing LIFECYCLE_READ strategy scope, a positive lifecycle subscription and the strategy's **Bond maturity** notification selection. The setting's UI explains that it also controls coupon notices. Coupon inspection is read-only at every tier; no operating setting or permission was changed. A separate coupon visibility switch is a future refinement, not a new migration or implicit grant in this increment.
- Only current tenant-owned **explicit COUPON schedule rows** inside the selected date window are discovered. Principal rows are excluded. Missing schedules are not manufactured into events or zero amounts. Earlier-overdue expansion remains for open maturities; historical coupons do not become perpetual missing-payment warnings.
- Position relevance follows the sourced record date, immediately before the sourced ex-date, or scheduled payment date. Future references use current known holdings. The existing trade-ledger recognition/allocation rules are reused. This is **position context, not settled coupon entitlement**; it does not calculate expected strategy income or certify schedule coverage. Unknown source/position evidence remains explicit. A current linked confirmation keeps an event inspectable when its reference-date position is flat.
- Formula/rate-only coupons remain unknown amounts; supplied zero is retained as supplied. Current schedule-term changes require source review. No bank/custodian reconciliation, notification acknowledgement store, independent coupon automation or tax/net-coupon logic is introduced.

## Implementation

[Read model and inspection](../../lifecycle/worklist_coupons.py) select current scoped schedules/receipt revisions and reuse the existing position reader. [Mixed worklist](../../lifecycle/worklist.py), [contracts](../../lifecycle/worklist_contracts.py), [GET adapter](../../apps/reference_api/lifecycle_worklist_routes.py) and [BFF](../../apps/ops-console/src/app/api/lifecycle/%5B...segments%5D/route.ts) retain current authorization and expected-tenant checks. Inspection selects the exact period before pagination and uses normal read-workload admission. No new writer or schema migration.

[Drawer](../../apps/ops-console/src/features/lifecycle-worklist/coupon-inspection.tsx) binds returned strategy/instrument/period/event identities, aborts obsolete reads and rejects changed contexts. The existing guarded bond/FX booking drawer is retained for maturity events.

## Verification

Initial query/state regression failed before implementation. Focused disposable-database checks cover read-only effects, due/recorded/reversed status, revised schedules, explicit date windows, tier/tenant/strategy scope and later-page inspection. Two bounded backend groups passed 37 tests each, retaining existing maturity/FX behavior; final scoped-reader and principal/formula-only edge checks also passed.

**11 mounted-browser journeys passed**, including read-only Tier3 coupon inspection, stale-context rejection and existing bond/FX actions, retries and focus preservation. Desktop/mobile widths and absence of financial controls were checked. The real BFF/API/PostgreSQL coupon acceptance passed: both a notice without a receipt and one with an existing confirmation were inspected with **no lifecycle POSTs**; trade, cash, accrual-input and coupon-source counts remained unchanged. No operating data was used. The maturity-booking test is intentionally skipped in coupon-only acceptance mode.

Repeat the owned [acceptance driver](../../scripts/run_lifecycle_panel_acceptance.py) with `LIFECYCLE_E2E_PRODUCT=bond-coupon`, explicit test-only `TEST_DATABASE_ADMIN_URL` and optional `PLAYWRIGHT_CHANNEL=msedge`. It creates/removes its own database/runtime role and API/UI. Private test logs/screenshots stay under ignored `.superpowers/sdd/2026-11-11-coupon-notifications/`.

No full backend suite, operating financial run or external payment verification is claimed. Final frontend/BFF/help checks: **38 passed**; TypeScript and OpenAPI export checks passed. The local API 8000 was restarted, with frontend 3001 left running. No migration, operating financial run, confirmation or settings change was performed.
