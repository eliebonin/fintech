# Futures lifecycle notifications implementation plan

> Execute sequentially using superpowers:executing-plans. Preserve current uncommitted work; no subagents or automatic commits/pushes.

**Goal:** Inspect sourced futures milestones and open contracts in the shared lifecycle dashboard.
**Architecture:** Independent retained notification selection; bounded domain read model; audited GET adapter/BFF; existing focus-preserving modal with a futures-only inspector.
**Tech stack:** PostgreSQL/SQLAlchemy, Pydantic/FastAPI, Next/React/TypeScript, pytest/Vitest/Playwright.
**Spec:** [scope and research](../specs/2026-11-11-future-lifecycle-notifications.md).

## Global constraints
No financial effects or operating financial/configuration changes. Explicit futures selection defaults0; only0/1 is supported. Preserve tenant/private-reference and strategy scope before source/count/page work. Missing dates/evidence remain unknown. Preserve distinct allocation exposure at aggregate0.

## Review focus
- Exact last-trading instant versus date-only deadlines.
- Flat/cancelled versus opposing allocations at net0.
- Data sourced from a later approved version versus original BOOKED evidence.
- Failed lazy reads and source changes cannot leave stale instrument information visible.
- Commercial downgrade/permission rules cannot imply unsupported preparation.

## Tasks
- [x] Write/run failing lightweight milestone and contract tests; implement `lifecycle/worklist_futures.py` date helpers.
- [x] Extend assistance contracts/service/schema and migration113; test notification-only choice, denied financial operations and downgrade preview.
- [x] Add scoped candidate/source/projection reader, combined filtering/counts and typed GET inspection; verify with real isolated bookings, cancellations, visibility and API tests.
- [x] Generate contracts; implement futures filter/labels, settings and read-only inspector in shared drawer. Test BFF allowlist/context, mobile/focus/stale responses and existing maturity/coupon journeys.
- [x] Review source/diff and bounded regressions; reconcile capability/register/map/root docs and record actual tests, missing first-notice coverage and local activation state.

## Verification ledger

See the [delivery record](../../delivery/future-lifecycle-notifications-20261111.md) for actual bounded test groups, local migration113 activation and remaining limits. Initial contract/milestone/BFF/mounted UI tests failed before implementation and passed afterwards. The pagination fixture initially attempted invalid cross-strategy profile-proof copies; it now books through the native service and passes without changing validators. Sequential implementation and self-review were used; no subagents, automatic commits or pushes.
