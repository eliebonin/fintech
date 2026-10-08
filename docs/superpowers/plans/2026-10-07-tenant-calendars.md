# Tenant Calendars Implementation Plan

> Execute inline using executing-plans/TDD. Standing user overrides: current feature checkout, sequential, no subagents, no additional plan approval or automatic commit/push. This file retains the execution ledger.

**Goal:** Govern fund/strategy holidays independently of exchange price calendars.
**Architecture:** Extend cal.market_calendar with tenant version/configuration fields and materialized sessions; append-only cal.calendar_assignment pins versions. Pure composition feeds publication; calendar decisions feed existing snapshot resolver without touching observations.
**Tech Stack:** PostgreSQL18/SQLAlchemy/Alembic, FastAPI/Pydantic, Next16/React/TypeScript/Vitest.
**Spec:** ../specs/2026-10-07-tenant-calendars.md

## Global constraints

No operating financial writes or reference holiday imports. Database tests run only through scripts/run_isolated_python_tests.py. New metadata columns have descriptions; migrations additive/forward-only. Legacy snapshot fingerprints unchanged. Selected-tenant API authorization on all new routes. Preserve existing dirty checkout.

## Tasks and tests

- [x] 1. Pure composition: market_data/calendar_composition.py; tests/test_calendar_composition.py. compose_day(day, mode, weekdays, components, exception) -> status/reason/evidence. RED→GREEN explicit coverage, Irish/UK/US intersection, union, unknown, weekend reopening and holiday/session conflict. Run pure pytest; expect pass after implementation.
- [x] 2. Schema, publication and assignment API: extend models.py; migration68; calendar_contracts.py/calendar_service.py/calendar_routes.py, wire main.py. publish_calendar(c,tenant,actor,payload,key), assign_calendar(...), calendar_view(...), options(...). Tests/test_tenant_calendars.py real HTTP RED missing endpoints then GREEN: replay/conflict/version, source freeze, immutable sessions, tenant boundaries, read-only/module denial, assignment overlap and purpose distinction. Run isolated runner with tests/test_tenant_calendars.py; expect pass.
- [x] 3. Resolver integration: market_data/calendar_decisions.py; market_data_resolver.py and policy config visibility. decision_for_target(c,tenant,kind,target,purpose,day,asof) -> frozen decision or None. Assigned closure NOT_EXPECTED, unknown MISSING, NAV-only fund calendar, strategy closure not underlying schedule mutation, information-cutoff selection and frozen snapshot replay. Extend tests/test_tenant_calendars.py, composite and rights regressions; expect isolated tests pass.
- [x] 4. Frontend: /market-data/calendars page, calendar-console.tsx, generated API contracts, selected-context BFF routes under /api/market-data/calendars. TDD payload/import parsing and rendered permissions; typecheck and frontend suite. Link market-data page. Calendar status/reason table and explicit version-pinned assignments.
- [x] 5. Review/acceptance: separate author review under user sequential override; fix important issues RED→GREEN. Full isolated Python suite, frontend/typecheck/OpenAPI/whitespace; apply additive local migration and read-only browser acceptance; document exact results and remaining limitations.

## Review focus

Tenant calendars must not leak in existing policy options. Reference holiday/session conflicts cannot silently become open. Missing coverage and future-recorded versions cannot bypass checks. Concurrent idempotency/version/assignment requests serialize deterministically. Historical information cutoff cannot see later assignment decisions. Explicit dated import must not imply that omitted dates are open.

## Ledger

Pre-flight: Task 1 composition consumed by Task 2 publication; Task 2 immutable rows consumed by Task 3 resolution and Task 4 UI. Matching payload names/status semantics above are binding. Task 5 verifies all interfaces together. No independent review or valuation certification claim.

Ruling: reference composition uses governed DB sessions/holidays only, not automatic bank-country packages — a package cannot determine the administrator's actual fund schedule. Cost: administrators must provide covered reference sessions or an explicit schedule before publication can resolve all dates.

Task 1 complete: 6 pure tests RED missing module → GREEN, 0.05s. Task 2 initial complete: 5 real API tests RED 404 → GREEN. Task 3 broader integration: 35 passed; NAV_DATE added after RED rejected convention → GREEN 34 including fund-session lag and legacy/composite regressions. Hardening exposed reference holiday/session conflicts and corrected them; error-code refinement remains under verification. Task 4 initial frontend: 4 tests RED missing modules → GREEN; typecheck passed. New BFF boundary coverage added.

Tasks 1–5 complete. Final focused review run: 73 passed in 20.76s (`logs/tenant-calendar-review-green.log`). Full frontend: 127 files / 600 tests passed, 9.92s (`logs/tenant-calendar-frontend-final.log`); both typechecks, OpenAPI consistency and final Git whitespace check passed. Final author review fixed closed-strategy-before-rule ordering after `test_closed_strategy_does_not_need_a_matching_price_rule` RED→GREEN. Inventory no longer repeats full configurations after its regression RED→GREEN. Full isolated Python suite: 1,118 passed, 490 warnings, 857.85s; exit0 and successful owned test-database cleanup (`logs/tenant-calendar-full-python.log`). Warnings are documented in the delivery report rather than claimed absent.

Local additive migration68 applied: before/after trades9, strategies50, observations1,358,477, calendars4; assignments0. No operating publication or assignment. Browser loaded the tenant calendar editor and read-only reference preview with no client errors. Sparse synthetic reference coverage is shown as UNKNOWN, not invented market days.

Ruling: NAV_DATE pins a published tenant VALUATION calendar in a NAV pricing rule; exchange/fixing rules cannot borrow tenant fund calendars. Assigned closures determine expected NAV/strategy dates; the NAV_DATE rule governs lag, target date and staleness. Cost: existing LEGACY NAV rules do not automatically change weekday arithmetic; tenants must deliberately create a revised policy with NAV_DATE.

Ruling: same-interval assignment revisions choose the latest recorded decision at the information cutoff; overlapping unequal intervals are rejected. Cost: alpha interval changes require adjacent non-overlapping assignments rather than retroactively splitting a recorded interval.
