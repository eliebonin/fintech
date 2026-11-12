# Coupon notifications and inspection

Add Bond coupon to the mixed Lifecycle worklist. Reuse existing tenant/strategy LIFECYCLE_READ, positive subscription and bond-notification selection. No new tier settings or grants; coupon inspection is read-only at every tier. No schema migration.

Use only current tenant-owned sourced COUPON schedule rows inside the explicit date window. Earlier-overdue expansion remains for maturity exposure, not indefinitely unconfirmed historical coupons. Principal and zero-coupon principal rows are not coupon notifications. No schedule completeness or missing-payment claim is inferred.

Position relevance is trade-ledger context at sourced record date, immediately before sourced ex-date, or scheduled payment date; future references use current known holdings. This is a relevance hint, not settled coupon entitlement. Retain exact source amounts per100 and formula/rate; do not invent total coupon income. Explicit existing confirmations keep an event inspectable even if the position is now flat. Unknown position evidence is not zero.

Show Upcoming, Review due, Confirmation recorded and Blocked states. Review due is an Ops review prompt, not a claim payment is overdue. Existing confirmation is not proof of full payment, reconciliation or income. Use latest logical payment revisions; reversed and earlier-schedule evidence stay distinguishable.

A lazily loaded inspection drawer shows dates, schedule/source/version, position reference and recorded confirmations. It has no prepare, book, confirm-payment or balance-update controls. It never infers whether receipt is represented by a dated cash-flow trade or EoD cash balance; those workflows and daily-accrual/P&L treatment remain separate.
