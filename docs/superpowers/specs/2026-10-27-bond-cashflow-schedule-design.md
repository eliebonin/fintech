# Full bond cashflow schedule

Approved intent: extend the existing retained coupon schedule to include both
coupons and principal, as agreed on 27 October 2026. Implement sequentially in
the current feature checkout; preserve unrelated changes.

## Scope and choices

Evolve the current versioned header and payment rows, rather than duplicate them
in an unrelated principal table or use the unversioned generic `secm.schedule`.
The latter lacks tenant, revision and sourced bond economics. Rename the
specialised tables to `secm.bond_cashflow_schedule` and `secm.bond_cashflow`,
retaining all existing identities, amounts, hashes, versions and payment links.
Migration 94 must create its original schema independently of current metadata.
Migration 100 then performs the forward-only extension.

Each row has a unique cashflow key, explicit COUPON/PRINCIPAL type and payment
date. Currency is inherited from the schedule's frozen bond issue currency.
Amounts use per 100 original nominal, not strategy holdings or outstanding
nominal. Coupon rows require ordered, non-overlapping accrual periods and a
sourced rate, amount or formula. Principal rows have no coupon-period metadata
and require a positive amount or sourced formula. Final coupon and principal
may share a date. Multiple explicit principal instalments are representable;
this does not extend automated redemption to amortising bonds. Zero-coupon
bonds accept principal-only schedules, not invented periodic coupons.

Do not generate dates, assume par redemption, calculate entitlement, claim
lifetime completeness, price bonds, reconstruct accrued balances, close trades
or recognise payment as income. Those remain separate work. Unknown formula
amounts stay null. Preserve source/reason, optional calendar/day-count metadata,
approved terms snapshot, revision conflicts, actor/operator and idempotency.

## API and interface

Keep the existing lifecycle API group and navigation URL so the change remains
bounded. Schedule commands/read results use `cashflows`, `cashflowKey`,
`cashflowType`, `amountFormula` and persisted snake-case equivalents. Existing
coupon-payment commands retain `periodId`, referring only to a COUPON row;
principal rows must be rejected by both the service and database payment guard.
Existing payment identities/history remain valid. Past request hashes remain
unchanged; a new-format schedule command uses a new request key.

The lifecycle page becomes “Bond schedules & coupons”. Show type, date,
accrual period where relevant, amount/rate/formula and currency/basis. The editor
allows coupon or principal rows with relevant inputs. Payment selectors include
coupons only. Principal-only schedules do not offer coupon confirmation.
Authority remains REFERENCE_APPROVE for schedule versions and strategy-scoped
LIFECYCLE_READ/BOOK/TRADE_CORRECT for existing read/payment workflows.

## Evidence

[Research](../../research/accrued-interest-fx-20261026.md) records the distinction
between expected schedule, daily earnings, accumulated stock and actual payment.
[OpenGamma Strata](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/bond/ResolvedFixedCouponBond.html),
reopened 27 October, represents coupons and nominal payment separately within
one bond. This supports typed cashflows; this project's relational layout is an
engineering choice, not an accounting standard requirement.

Acceptance: exact decimals; final coupon/principal same date; principal-only
zero bonds; invalid/mixed rows; overlap; unknown amount; retained migration
identities and receipt history; database rejection of principal as coupon;
tenant/scope/retry guards; UI editor and payment filtering. Use focused tests and
owned disposable databases, not a full Python suite or operating bookings.
