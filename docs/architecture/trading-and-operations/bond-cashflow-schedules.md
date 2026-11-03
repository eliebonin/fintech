# Bond cashflow schedules

**Status:** Accepted  
**Content type:** Reference  
**Owner:** Trading operations team  
**Last reviewed:** 2026-10-27

The retained bond schedule describes contractual **coupons and principal** in
one version. It is independent of strategy holdings, daily interest, actual
coupon receipts, cash balances and maturity-closing trades.

## Data and units

`secm.bond_cashflow_schedule` retains tenant, canonical bond, approved terms
snapshot, issue currency, optional calendar/day-count/business-day convention,
source, reason, revision/supersession, request hash/key, actor/operator and time.
`secm.bond_cashflow` contains the typed COUPON and PRINCIPAL rows for that version.
Currency comes from the retained schedule; amounts are **per 100 original
nominal**, not strategy entitlement or per remaining nominal.

| Type | Required economics | Period fields |
| --- | --- | --- |
| COUPON | Sourced decimal rate, amount per 100, or payment formula | Accrual start/end; optional record and ex-coupon dates |
| PRINCIPAL | Positive amount per 100, or sourced formula with unknown amount | No coupon rate/accrual/record/ex-coupon fields |

Every row has its own key and explicit payment date. Final coupon and principal
are separate rows even on the same date. Coupon periods cannot overlap; principal
rows can be interleaved. Principal-only schedules are allowed for zero-coupon
bonds. Zero-coupon bonds cannot acquire invented coupons. Multiple sourced
principal instalments can be recorded without enabling amortising-bond automatic
redemption. Formula-only amounts remain null; no fixing is fabricated.

Example, a 5% semiannual bullet bond in USD:

| Date | Type | Amount per 100 original nominal |
| --- | --- | --- |
| 2027-04-15 | COUPON | 2.50 USD |
| 2027-10-15 | COUPON | 2.50 USD |
| 2027-10-15 | PRINCIPAL | 100.00 USD |

Dates and economics are explicit source facts. The system does not infer lifetime
coverage from the number of rows, generate holiday/payment dates, default
redemption to par, calculate entitlement, or evaluate a DCF. Full-lifetime
schedules and complex/indexed economics require source assessment before future
pricing use.

## Workflow and evidence

Use **Trades → Lifecycle → Bond schedules & coupons**, URL
`/trades/lifecycle?product=coupons`. Select a permitted strategy and visible
canonical bond. Schedule maintenance requires REFERENCE_APPROVE; reading requires
strategy-scoped LIFECYCLE_READ. Saving creates an immutable revision with expected
revision conflict checking. Reads order rows by payment date, type and key.

The established `/v1/lifecycle/coupons` API group remains. Schedule commands use
`cashflows` with `cashflowKey`, `cashflowType`, `paymentDate`, optional coupon
fields, `amountPer100` and `amountFormula`. Reads return persisted snake-case row
fields plus `currencyCode`, `amountBasis=PER_100_ORIGINAL_NOMINAL` and
`coverage=EXPLICIT_SOURCED_ROWS_ONLY`. HTTP decimals remain strings.

`trd.bond_coupon_payment` remains separate append-only coupon receipt history.
Its `period_id` / API `periodId` identifies a COUPON cashflow only. Service and
database both reject principal rows as coupon receipts. Existing LIFECYCLE_BOOK
and TRADE_CORRECT scope, duplicate/retry and real-operator guards remain.
Principal payment confirmation is not introduced by this increment.

Neither schedule nor coupon confirmation creates cash, income, accrued-stock
resets, exposure closure or a valuation. Scheduled and actual payment remain
different facts. Existing principal maturity closure retains its separately
sourced contractual redemption workflow.

## Migration and limits

Migration 100 renames previous coupon schedule/period relations and adds type,
preserving all IDs, exact amounts, source/hash/time and payment links. Old rows
become COUPON without an evidence rewrite. Immutable triggers remain; the payment
scope trigger follows renamed relations and checks coupon type. Migration 94 now
declares its original schema explicitly, so fresh installs traverse the original
shape before migration 100.

The schedule JSON changes from `periods` to `cashflows`; callers update together
and use a new key for a new-format command. Historical request hashes are not
recalculated. No principal rows are retrofitted into old versions. Activation
does not seed operating schedules, confirmations or permissions.

The [accrued-stock/FX extension](../market-data-and-valuation/accrued-balance-fx.md)
now reconstructs evidenced balances and retains unpaid receivables after sale.
Automatic daily earnings, entitlement, payment reconciliation and DCF pricing remain separate.
See [research and agreed balance convention](../../research/accrued-interest-fx-20261026.md)
and [implementation/verification](../../delivery/bond-cashflow-schedule-20261027.md).
