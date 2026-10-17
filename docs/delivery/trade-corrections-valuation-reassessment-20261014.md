# Trade corrections and valuation reassessment — 14 October 2026

Status: implemented, verified in disposable fixtures and locally activated with approval on 14 October 2026. Migration `20261014_92` is applied to `platform_secm`; the restarted API reports healthy and registers both reassessment routes. This is bounded alpha acceptance, not production or complete NAV sign-off.

[Approved plan](../superpowers/plans/2026-10-14-trade-corrections-valuation-reassessment.md) · [Capability records](../product/features/valuation-and-pnl.md).

## Behaviour

Historical booking cancellations/supersessions effective at the original execution remove the erroneous economic booking from reconstruction without generating a fictitious offsetting execution. The original facts remain in lineage; an earlier information cutoff still reconstructs what was known then. Explicit replacement identifiers and reasons are validated. A later-effective termination inside the calculation period remains unsupported rather than being mistaken for a historical correction.

Migration `20261014_92` adds transactional strategy ledger revisions, immutable change evidence and retained recalculation requests. Database triggers cover new trades, financial updates and lifecycle events. Mutation, source capture and final publication share a strategy row lock. Metadata-only changes do not trigger financial reassessment. Existing batches without valid frozen revision proof show `UNKNOWN_LEGACY`; historical coverage is not fabricated.

Source health is separate from publication state and frozen financial evidence. A later relevant ledger change flags affected staged/published results; it does not rewrite their numbers or automatically unpublish them. Publication of stale or unverified staged candidates is blocked, including governed self-publication. A replacement publication supersedes the previous batch without altering its financial figures.

Ops can find affected results in History, select candidates and provide a reason plus confirmation. Server-side tenant/strategy-scoped pagination covers the worklist. Explicit recalculation preserves strategy, policy, dates and reporting currency, freezes a new information cutoff, and produces a staged successor. One request accepts at most 25 candidates and at most one base revision per strategy/date. Partial failures retain individual logs and successes. Retry keys preserve the cutoff and child attempts. Existing read/run authority and current evidence permissions govern disclosure and execution. No automatic publication or operating permission grants were added.

## Verification

- Pure reconstruction: 24 passed.
- Focused backend correction/valuation/history/publication regression: 56 passed, 11 existing warnings. No full-project suite was run.
- Final focused reassessment API, ledger impacts and bond redemption valuation: 16 passed after final backend changes.
- Final focused frontend: 35 passed; TypeScript `tsc --noEmit` passed after stopping the isolated dev app and removing its generated cache. An earlier check failed only in that disposable generated validator.
- Disposable browser acceptance: published FX maturity P&L 10,000 USD; cancelled/rebooked closure at 1.125; old result remained published at 10,000 with a reassessment warning; explicit recalculation staged 15,000 USD and zero closing exposure. Independent publication superseded the old batch, which retained 10,000 USD. The affected-results worklist then returned zero. No cash entry was created by closure.
- Bond cancel/rebook and restoration are covered by focused database-backed tests, not a new bond browser walkthrough in this slice. Ordinary historical cancellation, earlier knowledge, unsupported correction lineage, late bookings, future-date exclusion, publication serialization and mixed-success recalculation have focused tests. This does not certify every planned permission/race permutation.

Browser comparison evidence: `C:/Users/forte/.codex/visualizations/2026/09/29/01a0ec5f-933a-7cc3-8efa-fd93dd17f4a7/valuation-reassessment-comparison.jpg`.

The isolated API/UI were stopped; their exact disconnected fixture database and generated Next cache were removed. Generated UI configuration was restored. Subsequent approved activation applied migration 92 and restarted only the operating API. Read-only checks confirmed the revision, all three new tables, both capture triggers, health and route registration. Operating trades, permissions and published valuations were not changed; no operating recalculation/publication was performed. Existing batches without frozen ledger proof will require explicit recalculation, not fabricated historical revisions.

## Deliberate limits and remaining work

- Impact assessment is conservative: subsequent strategy dates may be flagged even when a precise lot dependency would prove no financial change. It is not a cumulative-P&L engine or automatic materiality assessment.
- This register tracks trade-ledger changes, not automatic market-data, policy or corporate-action revision fan-out. Existing input checks remain in force.
- New information can also select newer market data. Do not attribute the whole comparison delta to the trade correction without reviewing evidence.
- Ad hoc attribution amendments are not automatically reapplied. Ops must compare, review and re-enter any still-valid amendments before publication.
- Change detail is bounded to 100 displayed entries; this is not a trade selection cap. Recalculation is synchronous, explicit and bounded, without a scheduler or queued large-batch infrastructure.
- The UI refreshes its worklist on request rather than pushing live updates. Outcome rows describe the recalculation-time result; inspect History/detail for later publication state.
- Direct administrative deletion/manual database edits are not a supported correction workflow. No new valuation products, discounted forward MTM, settlement, cash accounting or automatic compensation were introduced.

## Research rationale

[Microsoft event-sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) informs retained events and reproducible projections. [CSSF Circular 24/856](https://www.cssf.lu/wp-content/uploads/CSSF24_856eng.pdf) illustrates historical NAV assessment/correction; its jurisdiction-specific compensation and notification rules are not asserted applicable or implemented here. Source-health terminology and workflow bounds are project engineering choices.
