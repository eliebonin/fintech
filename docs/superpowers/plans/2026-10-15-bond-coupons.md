# Bond coupon schedule and payment tracking implementation plan

> Use executing-plans sequentially and focused TDD; user explicitly asked for implementation after the agreed design. No subagents or additional approval loop for the plan.

**Goal:** Deliver informative coupon schedules and sourced strategy payment confirmations without double-counting interest.
**Architecture:** Separate `lifecycle/coupon_*` schema/contracts/service/routes from valuation. Extend existing lifecycle page/BFF only. No calculator or cash writer calls from coupon handlers.
**Spec:** [Agreed design](../specs/2026-10-15-bond-coupons-design.md).
**Tech:** existing SQLAlchemy/PostgreSQL/Alembic, FastAPI/Pydantic, Next/React and installed pytest/Vitest. No new dependencies.

## Global constraints / review focus

Preserve immutable evidence, Decimal precision, source versions, real-operator audit and action-bound strategy scopes. Unknown future amounts are not zero. Historical schedule changes cannot rewrite confirmed payments. No new automatic trade, daily-accrual reset, cash balance or valuation publication. Only disposable DB test writes. Confirm operating migration/restart separately.

## Task 1 — Persist and validate coupon facts

Files: new `lifecycle/coupon_tables.py`, `coupon_contracts.py`, `coupon_service.py`; register in `security_master_schema/models.py`; additive migration 94 after current head 93. Tests `tests/test_bond_coupons.py`.

- [x] RED tests for period order/unknown/zero/formula semantics, exact decimal amounts, owned versioned schedule, stale revision/idempotency and receipts/corrections/reversals.
- [x] Implement typed schedule/period/payment contracts, immutable persistence, source references and scope checks. Current/latest payment is a projection over retained revisions, not mutable historical facts.
- [x] GREEN tests plus existing daily accrual/valuation regressions demonstrating financial non-interference.

## Task 2 — Scoped API and transport

Files: new `apps/reference_api/coupon_routes.py`; register router, add explicit central access mappings. Extend existing lifecycle BFF allowlist. Tests `tests/test_bond_coupons_api.py`, existing BFF tests.

- [x] Transport tests: reference approval vs operational confirmation, read-only/foreign strategy and tenant denial, bounded query reports, retries after authority changes and input validation. Initial missing fixture grants correctly denied requests.
- [x] Expose options, retained schedules, confirmation/correction/reversal/history and full-population date filtering/counts under `/v1/lifecycle/coupons`. Keep financial effects zero by construction.
- [x] Generate OpenAPI/TypeScript and run focused API/BFF checks. Working-tree freshness passes; clean-HEAD generator check is inapplicable to this dirty checkout and its nonzero result is retained in delivery notes.

## Task 3 — Operational UI and documentation

Files: new `apps/ops-console/src/components/bond-coupon-console.tsx` and tests; extend lifecycle page/navigation. Current frontend AGENTS and installed Next guides govern changes.

- [x] Test readable schedule versus confirmed-payment states and initial read-only surface. Build explicit-date schedule editor with required source/confirmation, no date/amount arithmetic in browser. Full interaction/browser walkthrough remains pending.
- [x] Run frontend/type/backend-focused verification: 24 affected backend tests passed; final five coupon checks passed after the last options-query change; eight frontend/BFF tests and TypeScript passed. Approval received to activate migration 94/restart. No full suite.
- [x] Update delivery, F38/capability/register/map, architecture/knowledge and operational entry links; record exact tests, known gaps and activation separately.

Activation execution and browser limitations are recorded in the [delivery record](../../delivery/bond-coupons-20261015.md). API acceptance uses synthetic disposable data; browser acceptance is not claimed.

## Execution ledger

Current codex feature checkout retained per user preference; no commits/pushes or unrelated cleanup. Dedicated tables avoid leaking tenant schedule overrides through unscoped generic schedules. Payment recording uses existing LIFECYCLE_BOOK; corrections use TRADE_CORRECT; no implicit grants. Unknown entitlement and missing full accrued-stock/receivable valuation remain explicit gaps. Author review only, honoring sequential/no-subagent instruction.
