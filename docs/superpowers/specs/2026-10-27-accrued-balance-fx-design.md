# Accumulated interest balance and FX P&L

Agreed scope, 27 October 2026: complete the accrued-interest FX component using
daily earned interest, the full contractual bond schedule, and retained daily
accumulated balances. Missing data produce partial results/warnings, not assumed
zeros or a failure of otherwise valid price/FX or daily-interest components.

## Economic rules

At strategy/canonical-bond/currency level, reconstruct a local accrued stock:
opening + daily earned + signed purchased/sold accrued - actual coupon receipts.
Use supplied reconciled balances as anchors; otherwise replay from the first
recorded acquisition in the complete ledger. Preserve exact trade accrual and
direction, effective valuation dates, cancellations and maturity's principal-only
scope. Zero coupon absence is not daily coupon income. Unknown daily history
breaks reconstruction until a supplied anchor restores it.

Scheduled payments identify periods; they never clear a balance. Only actual,
as-of-confirmed payment revisions reduce it. Reversals restore the stock. A
foreign-payment amount without a supported native-currency conversion is
unassessed; no exchange rate is invented. Interest may remain payable/receivable
after the security is sold or redeemed. A new coupon period may accrue while an
old coupon is still unpaid. Do not blindly reset the whole stock on coupon day.

Daily interest uses closing policy FX. Accrued-stock FX uses opening stock times
closing-minus-opening policy FX. Intraday stock movements use the established
closing-FX attribution convention; they are not new income. Do not multiply the
position-level monetary accrued amount by holding quantity again.

## Implementation boundary

Add a pure balance replay module, a scoped/as-of source adapter, immutable typed
per-attempt daily balance records and source-health checks. The records are
dataset 3, not automatically trusted inputs for future runs: replay from original
sources prevents stale derived checkpoints. Existing detailed daily inputs can
provide assessed anchors; no fourth upload workflow is introduced.

Attach balance FX once per canonical bond to a real investment line when one
exists. Outstanding interest after disposal has a separately identified
receivable attribution, with no invented trade, quantity or market price.
Retain local amounts, exact FX, dates, source IDs/revisions and applied rules.
Missing optional inputs must be visible in coverage and partial-total labels.
Invalid supplied evidence and access/infrastructure failures remain errors.

Coupon payment writers serialize with valuation source review. Source revisions
after staging require recalculation; existing published amounts never mutate.
Existing independent review and explicit self-publication authority remain.
The prior user-controlled strict daily-interest request mode is unchanged;
accrued-balance coverage introduces no blocking mode. Default valuation is partial
when optional interest/balance inputs are unavailable.

## Acceptance

Test coupon-day bridge, late/partial receipt, new-period interest surviving a
receipt, purchases/sales/ex-coupon negative accrued, missing history and recovery
at an anchor, zero/same-currency balances, unavailable FX, multiple listings,
closed-position receivables, as-of/correction/reversal and stale publication.
Use lightweight pure checks first, then focused disposable database and UI tests.
Keep import tooling and unrelated dirty checkout work untouched.
