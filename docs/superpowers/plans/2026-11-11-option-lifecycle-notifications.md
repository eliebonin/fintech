# Option lifecycle notifications implementation plan

> Execute sequentially with superpowers:executing-plans; no subagents, automatic commits or pushes. Use lightweight failing tests first and bounded regressions after implementation.

**Goal:** Inspect sourced option deadlines and open contract positions in the shared lifecycle dashboard.
**Architecture:** Shared authorised held-candidate query/deadline state, product-specific domain reader, audited GET/BFF and existing native-modal drawer.
**Tech stack:** PostgreSQL/SQLAlchemy, Pydantic/FastAPI, Next/React, pytest/Vitest/Playwright.
**Spec:** [design and research](../specs/2026-11-11-option-lifecycle-notifications.md).

## Global constraints
No financial effects, operating strategy settings, positive grants/defaults or automatic expiry closure. Independent OPTION_EXPIRY supports0/1 only. Preserve immutable original BOOKED evidence and all tenant/private-reference/strategy rules. Missing data is unknown, never zero. Structured observations/autocalls remain next scope.

## Review focus
Exact last trading versus date-only expiry; early assignment versus scheduled expiry; cancellation/flat/net0 allocation states; immutable source conflicts and invisible underlyings; lazy source changes and notification downgrade guards.

## Tasks
- [x] Write/run failing lightweight option event/deadline tests, then shared held-candidate/deadline extraction and independent0/1 schema/assistance migration114.
- [x] Write real isolated option read-model tests; implement product sources, ledger/allocation aggregation, frozen-source checks and typed GET inspection. Verify scope, cancellation, counts/page ordering and cash/physical facts.
- [x] Write guarded BFF and mounted UI tests; generate contracts, add option event filter/setting/labels/read-only drawer and page help. Verify absence of financial controls, mobile/focus and revised-source rejection.
- [x] Run bounded affected regressions and source review; activate additive migration114/API without financial/configuration writes; reconcile delivery/register/map/root docs and record structured schedule findings separately.

## Verification ledger

[Delivery and limits](../../delivery/option-lifecycle-notifications-20261111.md) records actual bounded backend/frontend/browser groups, the retired unsupported-option negative-test correction, exact generated-contract reproduction and migration114/API activation. Valid cash/physical notices were explicitly checked as unblocked. Native bookings underpin the54-notice/27-strategy pagination case. Sequential implementation/self-review only; no subagents, automatic commits or pushes.
