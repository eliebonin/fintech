# Trade corrections and valuation reassessment implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task, sequentially, following the user's execution preference. Checkboxes track delivery. This document is a proposed plan, not implementation evidence.

**Goal:** Reconstruct corrected trade economics safely and identify/recalculate affected valuations without rewriting published financial history.

## Execution disposition — 14 October

- [x] Task 1 implementation: historical correction reconstruction and explicit replacement lineage; pure and database-backed FX/bond regression evidence.
- [x] Task 2 implementation: additive migration 92, transactional ledger capture, shared serialization and separate source health/publication guards.
- [x] Task 3 implementation: scoped affected-result worklist, explicit bounded recalculation, frozen retries and per-candidate partial failures.
- [x] Task 4 implementation: operational UI/BFF, focused tests, type/contract checks and disposable FX correction/independent-publication browser acceptance.
- [x] Documentation and test-app cleanup; [delivery report](../../delivery/trade-corrections-valuation-reassessment-20261014.md) is the completion evidence and lists remaining limits.
- [x] Apply migration 92 and restart the operating API: approved and completed; revision/tables/triggers/API health and route registration verified. No operating financial mutations.

The detailed checklists below retain the original planned verification scope; not every permutation received a dedicated new test or browser walkthrough. Bond correction acceptance is database-backed; the new browser walkthrough is FX. No blanket production sign-off is implied.

**Architecture:** Reuse the immutable trade lifecycle and existing position/P&L engine. Add strategy-ledger revision evidence and a small valuation-impact layer; keep source health separate from staging/publication state. Recalculation creates ordinary staged replacement candidates and publication retains existing authority checks.

**Tech stack:** Python, SQLAlchemy/PostgreSQL, FastAPI, Next.js/React, existing Decimal economics and owned disposable test runner. No new queue service or event-sourcing framework.

**Spec / agreed design:** User-approved correction/reassessment discussion of 14 October 2026; [demonstrated FX correction blocker](../../delivery/fx-forward-e2e-acceptance-20261014.md) and [current valuation capability](../../product/features/valuation-and-pnl.md). This plan carries the precise semantics below for review; implementation has not started.

## Global constraints

- Original bookings, lifecycle events, financial result lines and input snapshots stay immutable. Status/impact audit may evolve through retained events.
- An erroneous booking cancelled as a record correction is excluded at its original economic/valuation-recognition date when the cancellation is known at the requested information cutoff. Cancellation is not a new economic sale or cash movement.
- A contractual maturity close remains a separate economic entry on maturity day. Cancelling that entry removes its effect; its valid replacement supplies the corrected effect once.
- Recorded time determines what was known. Economic/recognition time determines which position and P&L period it affects. Retain both and never backdate knowledge.
- Corrections do not change policy, market data or information-cutoff choices implicitly. Recalculation records its new information cutoff and reports input differences.
- Explicit replacement links must connect original/superseded/replacement bookings. Never infer replacement from matching quantities, names or timestamps. Invalid/ambiguous chains still block.
- Tenant/strategy/action scope and current market-data evidence rights remain enforced, including publication and idempotent replay. Admin membership never bypasses them.
- Preserve independent real-operator review and the existing separately governed self-publication exception. Automatic republication is disabled.
- Published results remain reproducible historical records. "Reassessment required" means not confirmed against the latest ledger, not automatically proven financially wrong.
- No operating migration, financial mutation or restart as part of testing. No full-suite run by default; use focused tests first and disposable browser fixtures afterward.

## Scope and alternatives

Recommended: automatic impact assessment plus an explicit Ops action to recalculate. Purely manual correction tracking risks silently stale results; automatic republication undermines the accepted review boundary. Neither is selected.

Deliver in the following order. Shared reconstruction applies to currently supported equity/ETF/fund/bond/FX-forward bookings; bond and FX maturity are the first financial acceptance cases. Do not add unsupported product pricing, accounting, payments, compensation rules or scheduled batch infrastructure.

## Review focus

1. A later-recorded cancellation must not change an earlier-information-cut replay.
2. A correction to a trade absent from existing result lines, including a late new booking, must still flag affected results.
3. Price-only corrections can affect historical/cumulative P&L even when current exposure is flat.
4. A trade mutation racing publication must either precede its final check or occur afterward and flag the publication; no lost impact notification.
5. Bulk recalculation must retain partial successes, individual failures and scope checks without changing published results automatically.

## Task 1 — Corrected-ledger reconstruction

**Files:** modify `positions/reconstruction.py`, `positions/repository.py`, `positions/contracts.py` as needed for explicit replacement lineage; existing `apps/reference_api/trade_corrections.py` or actual correction owner located during execution; `lifecycle/bond_service.py`, `lifecycle/fx_service.py` only if their retained cancellation evidence needs clarification. Tests: `tests/test_position_reconstruction.py`, `tests/test_trade_corrections.py`, `tests/test_fx_forward_valuation.py`, `tests/test_bond_redemption_valuation.py`.

**Interface:** preserve `reconstruct(facts, request, *, splits=()) -> PositionProjection`. The projection retains all eligible original/correction facts in its hash/evidence while producing economic effects only from valid bookings at the frozen information cutoff. Use explicit supersession/replacement identifiers in ledger adapter evidence rather than synthetic negative correction executions.

- [ ] Add failing tests: ordinary original cancellation within the period; maturity cancellation alone restores exposure; cancellation plus replacement leaves zero exposure; before/after correction knowledge produces the respective original/corrected replay; unsupported or inconsistent chains still block.
- [ ] Confirm the current failure with the owned test runner, not by removing the safety guard blindly.
- [ ] Implement record-correction semantics for CANCELLED/SUPERSEDED; inspect CORRECTED handling and permit only established metadata-only semantics or explicitly linked economic replacement. Keep unsupported chains fail-closed.
- [ ] Verify FX fixture: original +1,000,000 at 1.10; prior rate 1.11; closure 1.12 gives 10,000 USD; corrected closure 1.125 gives 15,000 USD and zero closing value. Verify bond replacement uses sourced redemption terms and keeps final-interest inputs separate. Original events and published evidence remain unchanged.
- [ ] Run focused reconstruction, correction, bond and FX tests; document exact supported cases. Deliver this fix independently before impact/UI work.

## Task 2 — Durable impact evidence and publication protection

**Files:** create `valuation/ledger_impacts.py`; modify `valuation/tables.py`, `valuation/storage.py`, `valuation/service.py`, and trade mutation owners identified by scanning booking/correction/flow/maturity writers. Add one additive Alembic revision after the current head, choosing its unused identifier at execution. Tests: new `tests/test_valuation_ledger_impacts.py`.

**Interfaces:** `record_ledger_change(c, tenant_id, strategy_id, *, change_key, economic_from, trade_ids, reason, actor_id) -> int` returns the monotonic strategy revision, idempotently keyed. `batch_source_health(c, tenant_id, batch_id) -> dict` returns `CURRENT`, `REASSESSMENT_REQUIRED` or `UNKNOWN_LEGACY`, associated changes and earliest affected economic date. `assert_batch_ledger_current(c, tenant_id, batch_id) -> None` rejects staged candidates with relevant newer ledger changes or unverified legacy source provenance.

- [ ] Add failing tests covering late new bookings absent from result lineage, cancellation/replacement, date changes using the earliest old/new recognition date, future-dated non-impacting changes, duplicate mutation retries, price-only correction with flat exposure, and independent strategy/tenant isolation.
- [ ] Retain a strategy revision/change register and per-batch captured revision evidence. Record it transactionally for every valuation-relevant trade mutation, including economic-flow writers. Acquire the same strategy serialization lock in mutation, calculation source capture and final publication check; audit all writer paths, not just FX cancellation.
- [ ] Initially flag conservatively: affected strategy results whose closing economic boundary is on/after `economic_from`, unless narrower dependency proof establishes no impact. Include cumulative consumers when they are implemented; do not presume flat current exposure makes old P&L unaffected. Older requests with frozen earlier knowledge stay reproducible, but can require reassessment against the latest ledger.
- [ ] Preserve publication state and financial values; expose source-health separately. Legacy batches without trustworthy revision coverage display UNKNOWN_LEGACY; do not invent past change history or label them current. Newly published replacements resolve covered impact links, not every later result indiscriminately.
- [ ] Block publication of outdated staged candidates under the shared lock. Test both race orderings and amendment-derived candidates inheriting the source revision. Retain existing permission, evidence, amendment, independence and arithmetic checks.
- [ ] Run isolated migration and impact/publication tests; document conservative over-flagging as an intentional alpha trade-off.

## Task 3 — Explicit recalculation workflow and scoped APIs

**Files:** create `valuation/reassessment.py`, `apps/reference_api/valuation_reassessment_routes.py`; modify `apps/reference_api/valuation_routes.py`, `valuation/history.py` and app router registration. Tests: new `tests/test_valuation_reassessment_api.py`.

**Interfaces:** GET `/v1/valuation/reassessments` returns scoped paginated affected batches, reasons and source health; POST `/v1/valuation/reassessments/recalculate` accepts explicit batch IDs (maximum 25), a reason, confirmation and Idempotency-Key. It returns one outcome per selected batch: staged replacement attempt/batch, blocked failure evidence, or existing idempotent attempt. The caller cannot select tenant/actor authority through payload fields.

- [ ] Add failing transport tests for scoped results/counts, read-only users, per-strategy VALUATION_RUN, duplicate requests, unknown/foreign batches, 25-result bound and mixed-success recalculation.
- [ ] Reuse the existing corrected-input recalculation machinery, predecessor references, calculation/staging and run logs. Preserve each original request's strategy, policy, reporting currency and valuation dates; freeze a new information cutoff per request and retain its difference from the original. Never overwrite the old attempt.
- [ ] Return old/new P&L, values, changed ledger evidence and other selected-input changes. If newer market-data knowledge also changes marks, disclose it rather than falsely attributing the entire delta to the trade correction.
- [ ] No automatic publication or background scheduler. Partial failures retain prior publications and precise per-run reasons. Guard repeated selections and stale revision races before each staged result can be published.
- [ ] Verify amended candidates, multiple affected dates and a correction that changes again during recalculation. Update OpenAPI/generated contracts and run focused API/contract checks.

## Task 4 — Clear operational UI and final acceptance

**Files:** modify `apps/ops-console/src/features/valuation/result-workspace.tsx`, `run-report.tsx`, `publication-action.tsx`, `types.ts`; add a focused `reassessment-panel.tsx` and matching scoped BFF route. Component tests: `reassessment-panel.test.tsx`, existing publication/history interaction tests. Read frontend AGENTS and installed framework guidance before edits.

- [ ] Add component tests before implementation: Published · Reassessment required, Staged · Recalculation required, Unknown legacy source status, permission-aware recalculate/publish controls, old/new comparison and partial-failure results.
- [ ] Show a persistent results/history warning explaining changed trade, effective date, recorded date and whether financial impact is confirmed or pending assessment. Keep published numbers visible with the warning; do not silently switch reports to unreviewed staged numbers.
- [ ] Add explicit "Recalculate affected valuations" selection/confirmation with per-date outcomes; reuse existing publication controls and old/new revision navigation. No separate elaborate dashboard in this first slice.
- [ ] Run focused frontend/type/contract tests. Browser acceptance in owned fixtures: FX and bond normal maturity, cancel/rebook, staged-source change, independent publication of replacement and preservation of previous published evidence. Include a non-maturity historical booking correction and late new trade.
- [ ] Update F36/F37/F39 capability records, feature register, implementation map and delivery evidence with tests/browser/activation distinguished. No operating activation without the required migration/restart authorization.

## Completion criteria

The 15,000 USD corrected FX result stages and can be reviewed/published without double closure or cash creation. Old-information-cut replay still reproduces the original result. A relevant later ledger change flags published results and blocks outdated staged publication. Recalculation issues a distinct candidate and failures never erase the previous publication. Both standard and governed self-publication paths perform the same source-freshness checks.

## Research rationale

[Microsoft event-sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) supports retained original events, explicit compensating corrections and reproducible projection, without requiring us to introduce an entirely new framework.
[CSSF Circular 24/856, sections 4.3–4.4](https://www.cssf.lu/wp-content/uploads/CSSF24_856eng.pdf) illustrates assessment/correction of affected historical fund NAVs. Its jurisdiction-specific materiality/notification/compensation requirements are not being implemented or asserted applicable to this economic-P&L alpha. The proposed source-health labels and staged replacement workflow are our engineering design, not prescribed regulatory terminology.
