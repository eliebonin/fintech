# Lifecycle operations worklist — 5 November 2026

**Status:** Implemented bounded alpha; first discovery detector is bond maturity. **Capabilities:** F51/F24.
[Design](../superpowers/specs/2026-11-05-lifecycle-worklist-design.md) · [Execution plan](../superpowers/plans/2026-11-05-lifecycle-worklist.md).

## Portal journey

Open **Lifecycle** from the tenant menu, at `/lifecycle`. It is separate from the existing `/trades/lifecycle` maturity execution/schedule workspace.

Choose all authorised strategies or one strategy, From/To dates, relevance (actionable/information) and status; choose Apply filters. Defaults are 30 days before/after the current UTC date. Include earlier overdue retains open overdue exposure before From; it does not add all historical completed events. Dates filter contractual maturity, while quantities/status describe the currently known ledger, not a historical valuation snapshot.

The server computes scoped counts across the complete selected population, then pages 25/50/100 rows. Draft filters do not relabel a previous result. Rows show readable strategy/instrument identifiers, exact local quantities, separate-entry counts, status and assistance. UUIDs are restricted to context links/technical details. Zero net with opposing nonzero allocations remains visible; missing evidence says Not assessed, never0.

`Review closing entry` now opens the [contextual closing-entry drawer](lifecycle-action-panel-20261110.md) for assisted events; notification-only rows use `Inspect event`. Remaining quantities, maturity, selected tier/ceiling, review reasons and native actions stay in the selected context. Closing restores focus and scroll; the full workspace remains a secondary link. Opening/navigation does **not** prepare or book. Ops explicitly loads authoritative inputs, then prepares, independently approves, confirms or uses the existing one-click action according to current controls. There is no second posting endpoint or alternate pricing/quantity authority.

## What is discovered

Only `BOND_MATURITY` is currently discovered. Existing FX closure and coupon/schedule workspaces remain linked and usable; their notification discovery is not implied. Current positive lifecycle subscription and explicit strategy/event selection1 or higher are needed. Module access alone does not configure a strategy. Selections above a lowered ceiling remain visible as blocked; no runtime clamp or automatic upgrade is added.

Tenant membership and exact strategy-bound LIFECYCLE_READ scope are applied in SQL before candidate reads, counts and pagination. Subscription0 returns an unavailable explanation without an event population. Strategy-choice paging remains a cheap scoped read. No permission or assistance choice is granted by visiting the page. When a selected strategy (or the whole readable scope) has no explicit positive selection, the page explains that notifications are not enabled and links to strategy assistance settings; this is not presented as missing position data.

Candidates come from scoped booked instruments/listings and current canonical maturity dates. Core ledger and annotation reads are batched per strategy and reconstructed through the shared allocation engine. Current quantities retain native recognition, cancellation and immutable booking validation. A flat ordinary position without active native closure history is not an outstanding maturity task. A held inactive/retired reference remains visible as blocked when tenant visibility permits; retiring a reference must not silently erase operational exposure. Private/restricted scope is not widened.

## Status meaning

| Status | Meaning |
| --- | --- |
| Upcoming | A dated future maturity with remaining exposure; information only for now. |
| Due today / Overdue | Remaining exposure at/past sourced maturity; operational attention is required. |
| Prepared | Retained preparation exists; the native source fingerprint is rechecked when current assistance permits it. Independent REVIEW remains independent. |
| Reassessment needed | Preparation sources/revisions changed, or closure history and remaining exposure need reconciliation. |
| Booked · exposure closed | Current flat allocation exposure with retained active native closure evidence; not payment confirmation. Later current-source changes alone do not rewrite that completed evidence. |
| Blocked · review needed | Position cannot be assessed, maturity/terms are missing/conflicting, reference is inactive, the selected tier exceeds the ceiling, or the bounded handler cannot process the contract. Reasons are explicit. |

Actionable describes the event’s operational relevance, not the individual user’s posting authority. Native pricing, trade-field allocations, required fresh values, group permissions and reviewer/operator checks remain authoritative. Discovery performs no cash movement, accounting, coupon receipt, trade or valuation.

## Implementation boundary

- [Contracts](../../lifecycle/worklist_contracts.py), [scoped candidate/history reads](../../lifecycle/worklist_repository.py) and [read model](../../lifecycle/worklist.py) live below HTTP.
- [GET adapter](../../apps/reference_api/lifecycle_worklist_routes.py) serves `/v1/lifecycle/worklist` and `/options`; shared accessible instrument labels are added at the adapter boundary. DTOs are exported/generated normally.
- [BFF](../../apps/ops-console/src/app/api/lifecycle/%5B...segments%5D/route.ts) uses exact GET paths, an expected-tenant check and controlled query forwarding. There is no worklist mutation route.
- [Console](../../apps/ops-console/src/features/lifecycle-worklist/worklist-console.tsx), [report/inspection](../../apps/ops-console/src/features/lifecycle-worklist/worklist-report.tsx) and [page](../../apps/ops-console/src/app/lifecycle/page.tsx) use the existing browser transport and native workspace styles.
- A stable event key hashes tenant/strategy/canonical instrument/event type/current maturity. It does not grant authority and is not a retained task or financial identity. Source changes update the current derived event; original native proposals/postings remain retained.
- Full worklist reads use existing nonblocking workload admission; results are not capped or truncated. Pending source reassessment deliberately reuses the complete native fingerprint, with additional per-preparation reads rather than an incomplete duplicate proof.

No migration/new task table, polling worker or startup backfill is required. The local API is restarted on 8000 and the frontend remains on 3001. Activation does not alter subscriptions, assistance selections, permissions or operating financial rows. Pre/post financial/native/grant hashes and local browser evidence are recorded separately in the execution ledger.

## Validation

- Lightweight state tests preceded the read model. Disposable DB checks cover current scope/tier enforcement, notifications-only handling, exact exposure, >25-row full-population paging, opposing allocations at net0, upcoming/overdue inclusion, stale source proofs, retired references, unknown evidence, ordinary closed positions and native preparation/post/cancel histories. Existing redemption, allocation and authority suites are included: **51 passed** in the final affected regression. After the empty-state refinement, **23 worklist/API checks passed**, plus **18 frontend/BFF/navigation checks** and **3 workload-classification checks**. The full Python suite was not run.
- Integrated frontend: **251 files /1,171 tests passed** with 4 workers. An earlier unrestricted run had three 5-second import timeouts under concurrent load; all tests/timeouts were retained in the bounded rerun.
- Mounted browser: **12 passed**, including the two new worklist/filter/inspection and safe handoff journeys plus current lifecycle/profile/ticket regressions. Mobile 390px, keyboard focus return and runtime/HTML/console guards are covered.
- Final TypeScript/OpenAPI reproduction, source checks, local activation and remaining edge-case results are recorded in `.superpowers/sdd/2026-11-05-lifecycle-worklist/`.
- Own in-app browser: normal first-tenant admin session, menu/page, strategy/actionable filters and an empty-result explanation work; warning/error console is empty. The operating scope currently has no explicit assistance selections; the page now identifies that configuration gap. No positive operating selection was created just to populate that walkthrough. Synthetic populated journeys provide the positive event/inspection evidence.

## Trade-offs and remaining work

This is a current derived worklist, not persisted notifications, immutable discovery history, ownership/acknowledgement/snooze, email/SMS or an unattended booking scheduler. Detection runs when requested; a mature bond is never closed merely because its date passed. Discovery for FX forwards and other products comes next. Partial/amortising/indexed/defaulted bond closure remains outside the native principal-only handler.

A malformed bond ledger can make the strategy’s affected candidate population unassessed; it does not manufacture quantities or silently drop a bad trade. The UI explains this. Full-ledger/source checking costs grow with scope/history, and pending preparations need authoritative source reads; representative portfolio profiling remains necessary before adding caching/checkpoints. Client timeout does not assert server cancellation. Source/name changes and the current-date worklist are not historical point-in-time reporting.

## Research applied

Checked 5 November 2026: [W3C WAI tables](https://www.w3.org/WAI/tutorials/tables/) informs semantic captions/headers; [GOV.UK table guidance](https://design-system.service.gov.uk/components/table/) informs scan/comparison rows. [GOV.UK notification guidance](https://design-system.service.gov.uk/components/notification-banner/) supports keeping directly relevant statuses/explanations in page content, with sparing banners. The detector boundaries, tier gating and derived-read design are project choices, not externally mandated financial rules.

### Inspection action visibility

The contextual workflow link is a full-width primary action directly below the event status, before the supporting details. It retains its event-specific label and strategy/instrument destination, with hover and keyboard-focus states. Helper text explains that opening the workspace does not book a trade; all native authority and review controls still apply.

Instrument-name/identifier search and the redesigned native booking workspace are documented in [the UI follow-up](lifecycle-booking-ui-20261105.md). Search filters the scoped server population before counts and pagination.

11 November: the [closing-entry drawer](lifecycle-action-panel-20261110.md) replaces mandatory navigation for routine bond actions. Discovery remains read-only; explicit user actions invoke the existing native commands.
