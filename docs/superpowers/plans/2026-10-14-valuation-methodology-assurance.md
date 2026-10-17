# Valuation methodology assurance implementation plan

> Execute sequentially using executing-plans and TDD. The user explicitly requested planning followed by implementation without another approval round. Preserve the current feature checkout, focused-test preference and existing audit/security boundaries.

**Goal:** Make supported product economics and edge cases traceable to numerical tests and frozen, readable applied-rule evidence.

**Design/spec:** This bounded design strengthens existing `economic-position-pnl-v3`; it does not introduce a new pricer or NAV/accounting engine. Document supported equity/ETF, fund NAV, clean bond and deliverable-forward methods. Fix evidence omissions at calculation and stored-line boundaries. Existing UI renders the explanations; no frontend redesign is required. Unsupported products stay blocked.

**Architecture:** Keep numerical selection/calculation unchanged unless a reproduced defect requires a scoped fix. `decisions.py` explains frozen facts only; `service.py` supplies assessed economic input evidence; `position_storage.py` passes existing boundary values into those explanations. Human methodology reference links to tests, not a second runtime dispatch registry.

**Constraints:** No operating financial writes, migrations, grants, publication, dependency installation or unsolicited commits/push. Exact Decimal arithmetic; fund NAV economic date separate from receipt/publication; separate cash-balance preview from P&L. Current checkout is required because its uncommitted foundations are in scope.

## Review focus

Prior fund NAV must not imply prior FX; closing positions retain T P&L without a closing mark; clean and dirty bond execution must not double-count interest; calculation rules must include actual accrual inputs; historical empty evidence must not acquire fabricated explanations.

## Task 1 — Numerical methodology matrix

- [ ] Add `tests/test_valuation_methodology_matrix.py` using real reconstruction, position attribution, accrual attachment and economic-flow classification, with hand-derived literal expectations: long/short, new/additional trade, partial/full close, round trip, foreign holdings/new fund, nominal bond daily interest, forward maturity, missing marks/FX, unsupported capabilities.
- [ ] Run lightweight pure tests; existing behaviour passing is characterization, not a claimed RED/GREEN change.
- [ ] Document exact numerical bridge and map cases to existing resolver, split and maturity integration tests.

## Task 2 — Complete frozen explanations

- [ ] Add failing tests in `test_valuation_decisions.py` for structured requested/actual/availability dates, clean-bond convention and frozen boundary/execution bridge. Absence of complete facts must not invent a rule.
- [ ] Add integration assertions to `test_bond_redemption_valuation.py` requiring calculation-level DAILY_EARNED_ACCRUAL and stored POSITION_VALUE_BRIDGE/CLEAN_BOND_NOMINAL rules.
- [ ] Run tests to reproduce omissions before implementation.
- [ ] Extend `applied_decisions(evidence) -> list[dict]` using existing frozen values only. Pass full existing identity to it from `stage_line`; include every line's economic evidence in calculation rules. Do not mutate old rows or recompute money in explanation code.
- [ ] Run pure tests and owned disposable-DB valuation, accrual, fund-resolution, FX, split and storage suites. Preserve failing input/publication guards.

## Task 3 — Documentation reconciliation

- [ ] Create methodology matrix under `docs/architecture/market-data-and-valuation/` with current methods, source-backed rationale, project choices, limits and linked tests.
- [ ] Write delivery evidence; update F36–F39 references, feature register/map and catalogue.
- [ ] Use md-document on the established repository root: reconcile AGENTS.md, KNOWLEDGE.md and FIX.md with scoped valuation evidence, preserving unrelated stable findings and explicit review limits.
- [ ] Verify links, scoped diff and fresh focused results. Author self-review honors the no-subagent preference; no independent audit claim. Live activation is separate from source/test completion.

## Research applicability

## Completed disposition

- [x] Task 1: 17 numerical matrix cases; affected pure suite 64 passed.
- [x] Task 2: reproduced and fixed evidence omissions; focused disposable-DB suite 63 passed after updating the stale legacy historical fixture without weakening publication safety.
- [x] Task 3: matrix, delivery evidence, capability/register/map and root md-document reconciliation completed. Final verification/activation notes are in the delivery report; no full suite or independent audit claimed.

Detailed steps above retain planned verification intent; this disposition and the delivery report record actual completion.

SEC rule 2a-5 guidance (2021) supports documented/testing methodology and retained valuation evidence for covered US funds, not a compliance assertion for this personal alpha. IFRIC's September 2018 IAS 21 discussion clarifies closing-rate/transaction-date distinctions; the engine's day-end execution FX and PRICE/FX/CROSS decomposition are explicit project conventions, not mandated accounting. FINRA accrued-interest tooling reinforces nominal/day-count sensitivity but is not a methodology specification. FSA's June 2026 notice identifies updated IOSCO valuation recommendations; the linked IOSCO final PDF returned 403, so its detailed provisions are not claimed reviewed.
