# Coupon notifications implementation plan

Sequential execution using superpowers:executing-plans; no subagents.
**Goal:** read-only coupon notices and inspection in the existing Lifecycle page.
**Spec:** [bounded scope](../specs/2026-11-11-coupon-notifications.md).

- [x] Add failing contract/source/inspection tests including scope, schedules, reversals, reference dates, readonly effects and no inferred cash/income.
- [x] Add coupon contract, scoped schedule/position read model and lazy inspection GET; merge before counts/page selection, with bond notification visibility.
- [x] Add filter/status labels and readonly coupon drawer; retain maturity workflows. Update guidance and generated contracts.
- [x] Verify focused isolated domain/API tests, frontend/BFF and synthetic browser read-only journeys; restart only our API as needed.
- [x] Reconcile delivery/capability map/register and record limits: shared visibility, no income/payment matching, no missing-schedule claims or task acknowledgements.
