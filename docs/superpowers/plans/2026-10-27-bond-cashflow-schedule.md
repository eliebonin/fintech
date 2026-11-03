# Bond cashflow schedule implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. User preference overrides subagent execution and repeated approval loops.

**Goal:** One retained bond schedule containing typed coupon and principal rows.

**Architecture:** Extend and rename the existing versioned coupon tables while
retaining payment identities. Keep contractual reference data separate from
payments, earnings, exposure closure and valuation calculation.

**Tech stack:** SQLAlchemy/Alembic, FastAPI/Pydantic, Next.js/React, pytest/Vitest/Playwright.

**Spec:** [Design](../specs/2026-10-27-bond-cashflow-schedule-design.md).

## Constraints and review focus

- Work in the existing dirty feature checkout; do not commit unrelated work.
- No automatic principal price, generated dates or completeness claim.
- Preserve existing payment revisions and all retained evidence.
- Exact Decimal strings and existing tenant/action/strategy checks remain.
- Same-day final coupon/principal must not conflict; payment selector/DB guard
  must never treat a principal row as a coupon.
- Unsorted interleaved rows must still detect overlapping coupon periods.
- Principal-only zero bonds work without fabricated coupon periods.
- A migrated receipt must still be correctable/reversible with unchanged IDs.
- Test migrations from 94 and a fresh head in disposable databases only.

## Tasks

- [x] Contracts/schema: add failing typed schedule tests; introduce strict
  `BondCashflow` and `ScheduleCreate.cashflows`; freeze migration 94 schema;
  add forward migration 100 preserving IDs and guards. Verify offline contracts.
- [x] Service/API: persist/read ordered cashflows with inherited currency/basis;
  reject coupon rows for zero bonds and principal confirmations. Adapt existing
  coupon regressions and add migration, immutable, isolation and inertness checks.
- [x] UI: extract schedule table/editor into a focused component; show cashflow
  type and basis; conditional coupon fields; coupon-only receipts. Add unit and
  isolated browser checks; regenerate and verify OpenAPI/TypeScript.
- [x] Documentation/acceptance: update capability register/map, delivery and root
  guidance/knowledge/limits. Run focused disposable DB, UI and contract checks.
  Activate local migration/API only after checking target/version and the tested
  migration's safety. No operating schedule/payment/trade data is created.

## Execution record

Implementation begins after the user's “Yes, let's do it.” No additional design
approval is needed. Accrued-balance reconstruction remains a separate increment.

Completed sequentially. 19 initial disposable checks and 31 adjacent checks
passed; 1,053 frontend unit tests and 14 browser journeys passed. A later
workspace-CSS/mobile check also passed (2 journeys), then focused UI/type checks
passed after punctuation correction. Final evidence and activation are recorded
in the [delivery](../../delivery/bond-cashflow-schedule-20261027.md).
