# Option expiry notifications and read-only inspection

**Approved direction:** Implement the option notification slice in the existing lifecycle dashboard, following futures. Structured-product observation/autocall notices are a subsequent discussion, not part of this delivery. Sequential/current-checkout execution remains authorised; preserve existing work.

## Design
Independent retained `OPTION_EXPIRY` strategy selection supports manual0/notifications1 under the existing commercial ceiling and explicit LIFECYCLE_READ/CONFIGURE scopes. No positive defaults/grants. Native financial handlers remain unavailable at every purchased tier. Extend the retained event CHECK constraint through additive migration114; existing rows remain unchanged.

Use the general worklist/filter/count/pagination/drawer rather than a separate dashboard or bond/futures visibility inheritance. Share the authorised held-candidate query and deadline-state helper with futures; product-specific term/evidence inspection stays in its own domain module.

Show distinct last-trading cutoff, explicit expiry and final settlement only where sourced. Do not infer cutoff, expiry, settlement lag, AM/PM fixing or broker instruction deadlines from names or generic calendars. Last-trading instants use UTC exactly; date-only milestones have day-level due status. Missing expiry/evidence remains blocked/unknown. No automatic exercise, assignment, lapse, closing trade, cash/delivery, payoff or P&L effect.

Inspect canonical contract, visible underlying, call/put, supported fixed strike/currency, exercise style, cash/physical settlement, signed contract quantity, deliverable units per contract, premium multiplier, approval/source IDs and explicit data gaps. Premium multiplier is not an underlying exposure or an exercise instruction. American-style early exercise/assignment risk is explained; no recurring daily exercise event is invented. OTC options not currently booked by the product remain outside this release; current supported listed booking evidence stays authoritative.

Reconstruct immutable ledger and joint allocations before determining open holdings. Retain shorts and opposing allocations at net0; remove flat/cancelled holdings without declaring settlement complete. Current versus original BOOKED contract conflicts are flagged. Lazy GET inspection rechecks tenant/strategy/selection/reference/source identities, aborts obsolete reads and rejects a changed source fingerprint. Never leak inaccessible underlying names/IDs.

## Research (opened/read 11 November 2026)
- [OCC/OIC exercise guidance](https://www.optionseducation.org/referencelibrary/faq/options-exercise): styles, broker instruction cutoffs and exercise-by-exception are distinct from proof of exercise. No thresholds or broker deadlines are hardcoded.
- [Cboe SPX specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications): last trading can differ by series from expiry. Its dated product snapshot informs terminology, not a current calendar or universal cutoff formula.
- Existing [modal interaction guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) applies through reuse of the native focus-preserving drawer.

Independent notification selection and this read-only rollout are project choices, not claims of regulatory compliance.

## Acceptance
Scoped real approved option bookings and cancellation; long/short/flat/net0 allocations; cash/physical and American/European facts; exact cutoff; missing and revised terms; full-population filters/pagination; tenant/selected-strategy access; notifications0/1 and downgrade/DB constraint; GET-only guarded BFF; mobile/focus/stale-response UI; existing bond/FX/coupon/futures regressions. Use isolated synthetic databases; no operating financial writes. Activation only adds migration114 and restarts the task-owned API.
