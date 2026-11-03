# Cash-balance FX P&L Implementation Plan

The opt-in decision in this completed plan is superseded by the user's
[25 October standard-inclusion instruction](2026-10-25-standard-cash-pnl.md).
Keep this execution record as history, not the current option contract.

> **For agentic workers:** Use superpowers:executing-plans, sequentially, honoring the user's no-subagent preference. Keep the execution ledger in this file. No automatic commit/push or new worktree.

**Goal:** Include exact-date account-owned daily cash FX in governed P&L without inventing cash trades.

**Architecture:** A cash-specific loader/calculator produces immutable account/currency lines and coverage. Typed ownership extends the existing review batch; cash FX is separate from the securities market bridge. Presentation uses frozen inputs and current scoped account labels.

**Tech Stack:** Python Decimal/dataclasses, SQLAlchemy/PostgreSQL/Alembic, FastAPI, Next.js/React/TypeScript.

**Spec:** [Approved convention and explicit rulings](../specs/2026-10-24-cash-fx-pnl-design.md).

## Global constraints

Default opt-out preserves historical requests; explicit daily inclusion; no fake
trade or instrument; no automatic cash movement/income; no inferred zero or carry;
current strategy/DISPLAY/real-operator checks; append-only published financials;
focused disposable-DB tests; operating migration 99 requires approval.

## Review focus

1. Borrowed/zero/same-currency cash must not require irrelevant FX or lose signs.
2. Account/currency scopes appearing mid-period must not imply zero opening cash.
3. No-position cash-only results need valid source disclosure without a fake holding.
4. Correcting a snapshot after staging must block both publication and amendment.
5. Old idempotency keys/results and independent/self-publication remain valid.

### Task 1: Exact cash calculation and economics family

Files: new `valuation/cash_fx.py`, `tests/test_cash_fx.py`; update `valuation/economics.py`, `rounding.py`.
Interface: `cash_fx_amount(opening: Decimal, opening_fx: Decimal, closing_fx: Decimal) -> Decimal`;
`CashFxLine(account_id, currency_id, daily evidence)` and `CashFxResult(lines, coverage)`.

- [x] Test-first signed 100000 × (.76 − .75) = 1000; borrowed = -1000;
  explicit zero and same-currency = 0; exact daily sums use each opening balance.
- [x] Add CASH component family and exact rounded gross/net parity without
  changing investment market subtotal; run pure tests.

### Task 2: Source loading, ownership and immutable storage

Files: new `valuation/cash_fx_storage.py`, migration `20261024_99_cash_fx_pnl.py`,
`tests/test_cash_fx_storage.py`; update schema metadata, `service.py`, `storage.py`,
`evidence_access.py`, `cash_snapshots.py`, `amendments.py`.
Interfaces: `load_cash_fx(c, request) -> CashFxResult`; `stage_cash_line(...) -> owner key, attribution id`.

- [x] Add typed cash account/currency owners and uniqueness/scope FKs to
  attribution/review items without backfill. Reject mixed or cross-strategy owners.
- [x] Resolve scoped latest exact-date revisions at information cutoff; retain
  known scopes/missing dates/unassessed accounts. Select policy FX once per
  currency/date; zero/same-currency proof admits no third-party observations.
- [x] Stage cash-owned versions, gross/net and cash total/coverage alongside
  unchanged position bridge. Extend population identity and amendment copying.
- [x] Test cash-only/mixed results, same-company separate accounts, missing/zero,
  cutoffs, immutable evidence, exact/rounded totals and independent publication
  using the owned disposable runner.

### Task 3: Source-change and request/recalculation controls

Files: new `valuation/cash_fx_health.py`, `tests/test_cash_fx_governance.py`;
update `ledger_impacts.py`, `valuation_contracts.py`, `reassessment.py`, request identity.

- [x] Add strict boolean include flag; preserve false/absent legacy retry hashes.
  Require daily boundaries for included EoD snapshots; retain flag on recalculation.
- [x] Batch cash source-health checks across history headers. Reject changed
  inputs before staged publication and approved amendments, preserving published
  figures and existing reviewer independence. Test corrected/new/backdated and
  future-date snapshots; source history must not expose another strategy.

### Task 4: Cash report and source coverage

Files: new `apps/ops-console/src/features/valuation/cash-fx-report.tsx` and tests;
update request form/BFF contract, types, coverage, result/review report and labels.

- [x] Add explicit cash checkbox and retained retry/recalculation behavior.
- [x] Resolve only authorized cash account/company/currency names; display cash
  separately from investment positions, with daily balances/FX/P&L and exact
  source/date/revision evidence. No browser financial calculation.
- [x] Replace unconditional excluded-cash warning with frozen coverage status;
  support source inspection, partial/unknown warnings and denied-data suppression.
- [x] Test UI, type/contracts and isolated browser staging/review. No operating
  mock trades, balance uploads or publications.

### Task 5: Verification, documentation and activation

- [x] Run focused pure/DB suites, valuation frontend tests, type/OpenAPI checks,
  synthetic browser journey and author self-review. No full Python suite.
- [x] Update methodology, F39/F40 capability/register/map and delivery with sources,
  omissions and actual verification. Preserve earlier dated evidence.
- [x] Request permission for migration 99 and scoped API 8001 restart; once approved,
  apply only additive migration and health/read checks. Never run operating P&L.

## Execution ledger

- Setup: current `codex/pnl-ops-review` checkout intentionally contains the prior
  Ops UI/coverage work; preserve it. User confirmed opening-balance convention.
- Ruling: explicit inclusion defaults false, incomplete snapshots are disclosed
  partial coverage, missing required nonzero FX blocks. This avoids changing old
  requests or fabricating cash; Ops must deliberately include cash on a new run.
- Pre-flight: CASH components feed rounded gross/net but not securities market
  bridge; typed owner identity feeds storage, population hashing, amendments and
  presentation. Include flag feeds API/domain/retry/reassessment/UI consistently.
- Final review will be author self-review per user preference, not independent audit.
- Tasks 1–3: complete; exact arithmetic and native staging/governance RED→GREEN.
  Additional failing queue, direct-insert race and inactive-currency tests passed
  after targeted fixes; no financial guard was relaxed.
- Task 4: complete; 96 UI/request checks and five isolated browser journeys pass.
  The cash inspector sits below the compact account table and takes keyboard focus.
- Task 5: focused run 170 passed/one pre-existing schema-comment failure; standalone
  and committed-model comparison reproduce the same 94 undocumented columns.
  New owner columns are documented. Types/OpenAPI/repeated generation verified.
- Ruling: retain the minor pre-existing column-comment finding as SCHEMA-DOC-001,
  rather than silently suppressing it or expanding this financial change into ten
  unrelated schema tables. Cost: the broad metadata test remains red until cleanup.
- Ruling: native inserts use the same strategy NO KEY UPDATE serialization as
  publication, in addition to existing API locks. Cost: writes/review for one
  strategy serialize; no feature/scope restrictions or cash-ledger coupling.
- Ruling: source-impact discovery is conservatively receipt/date based, while
  publication/amendment approval recompute the complete source hash. Cost: some
  historical updates with no eventual financial effect still need review.
- Final review: author self-review per user request; no independent reviewer used.
- Final: minor (deferred): 94 pre-existing Python column-comment gaps, recorded in
  FIX.md; does not change cash financial behaviour or schema availability.
- Activation: user approved migration 99 and API 8001 restart on 25 October;
  read-only preflight verified the configured local app database at migration 98.
- Task 5: complete with the disclosed legacy metadata failure. Migration 99 is
  applied, API 8001 healthy/live cash flag verified, UI 3001 returns 200. Read-only
  retained FCAGF summary comparison is identical; no operating financial writes
  or permission changes. No automatic commit/push.
