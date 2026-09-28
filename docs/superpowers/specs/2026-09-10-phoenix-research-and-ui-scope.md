# Phoenix research and UI scope

## Conclusion

Phoenix is a structured-product/autocall convention, not a separate economic
instrument model. The common feature is a conditional coupon that can be paid
while the product continues; the product may also have an autocall trigger and
a maturity protection/capital barrier. A memory coupon is common, but it is an
additional contractual feature and must not be inferred solely from the
`PHOENIX` subtype.

This matters for the onboarding screen: Phoenix should use the existing
terms/composition/condition-group/coupon-programme graph, with a useful memory
default, but the term sheet remains authoritative.

## Evidence reviewed

* [SG Forge Phoenix description](https://www.sgforge.com/product-structured-products-phoenix/)
  separates the autocall barrier, conditional coupon barrier, and maturity
  protection barrier. Its examples pay coupons while the product continues and
  redeem principal plus the current coupon when an autocall occurs.
* [RBC Phoenix AutoCallable pricing supplement filed with the SEC](https://www.sec.gov/Archives/edgar/data/1000275/000095010325003216/dp226084_424b2-jpmeln565.htm)
  explicitly labels a memory feature. An unpaid contingent coupon is paid only
  once, on a later eligible coupon date or at maturity, and an early call pays
  principal, the current coupon, and any previously unpaid coupons. The same
  document distinguishes observation dates, coupon payment dates, call
  settlement dates, and final valuation dates.
* [SSPA Lab autocall definition](https://sspa.ch/en/lab/) describes an
  autocall as an obligation to repay principal plus the applicable coupon when
  all underlyings meet the trigger. This supports modelling worst-of as a
  Boolean condition group rather than copying a parent action once per
  underlying.
* [Rothschild structured-products glossary](https://www.rothschildandco.com/fr-fr/banque-privee/gestion-financiere/produits-structures/glossaire-produits-structures/)
  describes Phoenix as an autocall that can pay coupons during the life of the
  product without redeeming it; it does not make memory a defining property.
* [Marex Phoenix product example](https://certificati.marex.com/products/it0006774506/)
  shows the operational fields commonly published together: multi-underlying
  worst-of references, coupon rate/frequency, coupon barrier, first autocall
  date, European barrier type, capital barrier, initial fixing, and maturity.

The sources also show that issuer terminology is not perfectly uniform. A
Phoenix term sheet, not the marketing label, controls the legal payoff.

## Contractual fields the UI must keep distinct

1. **Coupon eligibility barrier**: determines whether the coupon for that
   period is earned. This can differ from the autocall barrier and the capital
   barrier.
2. **Autocall barrier**: determines early redemption. It may be flat,
   step-down, or otherwise period-specific.
3. **Capital/maturity barrier**: determines whether principal is protected at
   maturity when no early redemption occurred. It is not the coupon barrier.
4. **Coupon memory**: `NONE` or an explicitly selected memory treatment. The
   common catch-up rule is “a missed coupon is paid once on a later eligible
   date”; the legal terms may instead pay arrears only at redemption/maturity.
5. **Scope and observation measure**: single, best-of, worst-of, basket, or
   each-underlying, with the relevant close/fixing/averaging convention.
6. **Non-call period**: the first observation at which autocall is allowed.
   Coupon observations may still occur before that date.
7. **Settlement**: cash versus physical or other maturity settlement, where
   the term sheet permits it.

## Fit with the current model

The existing model is suitable for the core Phoenix graph:

* parent `instrument` + versioned `structured_product_terms`;
* fresh option component instruments and signed `instrument_composition` rows;
* dated `schedule`/`schedule_event` rows;
* separate condition groups and barrier rules for coupon, autocall, and
  capital protection;
* `structured_product_coupon_programme` and
  `structured_product_coupon_period` for memory and period-specific coupons;
* parent actions for component payment and redemption.

The submitted UI value `memoryMode` belongs in the coupon programme. It should
not be copied onto a barrier rule or treated as a product-name label.

## Recommended Phoenix UI slice

### Do now

* Keep `PHOENIX` as a subtype/profile over the shared builder.
* Keep separate coupon, autocall, and capital-barrier inputs.
* Default the memory selector to `NONE`; allow `CONDITIONAL_CATCH_UP` and
  `ACCUMULATE_TO_REDEMPTION` only when the term sheet supports them.
* Show a compact explanatory note: Phoenix means conditional coupons while the
  product remains outstanding; memory is optional.
* Keep worst-of/best-of and listing/economic-reference selection on the same
  canonical reference-node controls.

### Implemented in the current MVP slice

* Add independent coupon and autocall-observation frequencies. The operator
  can state N coupon periods per year and M parent redemption observations per
  year; non-Phoenix products continue to use one shared cadence.
* Default coupon eligibility to the autocall barrier in force at the coupon
  date, while retaining an explicit fixed-barrier override for term sheets
  where the coupon barrier differs.
* Generate a union date view while keeping coupon rows and parent actions on
  their respective cadence. Step-down numbering is based on autocall dates,
  not coupon dates.
* Persist separate coupon and autocall schedules on approval, together with a
  coupon programme and dated coupon periods.
* Accept an explicit first autocall observation/non-call boundary. Coupon
  observations continue before it, while `REDEEM_PARENT` actions are omitted
  until the boundary.
* Expose final-payment treatment for accrued memory (`PAY_SEPARATELY`,
  `INCLUDE_IN_REDEMPTION`, or `FORFEIT`) only when a memory mode is enabled,
  and persist it on the coupon programme. With `NONE`, the API and database
  store `NULL` because the treatment is not applicable.
* Generate an explicit maturity `FINAL_REDEMPTION` action. It maps to
  `TERMINATE_PARENT` with an unconditional/`NONE` condition group; lifecycle
  processing applies it only if no earlier parent redemption and no mutually
  exclusive maturity branch (such as consolation) occurred.
* Carry an editable settlement/payment date on every generated component or
  parent outcome row. Approval persists that override on the coupon period or
  action, while the schedule event remains the default.

### Still deferred

* Add an explicit final valuation/settlement method when a product uses
  averaging, physical delivery, or another maturity convention.

These additions are contractual-data work, not pricing-engine work. A later
valuation service must maintain a coupon arrears ledger so a missed coupon is
never paid twice.

## Current implementation assessment

The current Athena/Phoenix profile change is directionally correct for an MVP:
Athena uses a flat autocall-barrier default, while Phoenix starts with memory
`NONE` and lets the operator opt into a documented catch-up mode. The Phoenix
helper text must continue to say that memory is a choice, not a subtype
invariant. Calendar/session
resolution and lifecycle outcome/arrears processing remain separate future
services; they are not hidden in the creation payload.
