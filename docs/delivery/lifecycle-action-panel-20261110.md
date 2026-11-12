# Lifecycle closing-entry side panel

Implemented 10–11 November 2026; verified 11 November. F24/F51 follow-up to the [worklist](lifecycle-worklist-20261105.md) and [booking UI](lifecycle-booking-ui-20261105.md).

## Delivered behavior

`Review closing entry` opens a wide right-hand drawer on `/lifecycle`, with the chosen strategy and instrument locked. It reuses `BondRedemptionConsole` in embedded mode. Source preview remains an explicit read-only action; opening the drawer does not prepare, approve, book or cancel anything. Notification-only events retain information/manual handling. `Open full workspace` remains available for configuration and complex work.

The drawer has native dialog focus containment, Escape/close handling, a separate scrolling body and a full-width mobile layout. Filters and worklist pagination stay mounted. Confirmed preparation/booking/correction refreshes the scoped worklist without unmounting the active workflow. Closing restores focus to the originating row, or the report heading if that row has left the filtered set, and restores page/scroll-container position (clamped to the new maximum when refreshed content becomes shorter).

Unsaved changes require explicit discard before closing or leaving for the full workspace. Busy requests cannot be dismissed. Uncertain financial outcomes retain the same request key and payload for retry; a subsequently denied retry does not prove the original outcome or release that guard. Confirmed writes remain confirmed if a follow-up history read fails. Browser reload/navigation still has the browser's standard unsaved-work confirmation; no persistent cross-session draft store is introduced.

Shared-console history pagination no longer resets the closing candidate or entered allocation values. Older history responses cannot overwrite a later refresh; abandoned same-turn React effects do not start transport requests. Embedded proposal/posting reads include `instrumentId`; SQL filters before counts and pagination. Cancellation receipts follow their original posting within the same tenant/strategy, since the retained cancellation payload need not duplicate instrumentId. The HTTP adapter still checks strategy authority first. The native writer, commercial tier gate, source fingerprint, allocation rules, real-operator independent approval and idempotency guards remain authoritative.

## Implementation and research

- [Drawer](../../apps/ops-console/src/features/lifecycle-worklist/lifecycle-action-panel.tsx), [worklist integration](../../apps/ops-console/src/features/lifecycle-worklist/worklist-console.tsx), [shared console](../../apps/ops-console/src/components/bond-redemption-console.tsx).
- [History predicate](../../lifecycle/history.py), [native HTTP adapter](../../apps/reference_api/bond_redemption_routes.py), [SQL regression](../../tests/test_lifecycle_history.py), [browser regression](../../apps/ops-console/browser-tests/lifecycle-panel.spec.ts).
- [Implementation plan](../superpowers/plans/2026-11-10-lifecycle-action-panel.md).

The approved layout follows [PatternFly drawer guidance](https://www.patternfly.org/components/drawer/design-guidelines/) for contextual detail and [Carbon dialog guidance](https://www.carbondesignsystem.com/building-blocks/core/patterns/dialogs) on avoiding a complex full-page workflow in a small modal. These were read during the preceding design discussion. A wide drawer with native modal keyboard semantics is the project accessibility choice; the page/context remains intact behind it. No new UI library, migration or financial writer.

## Recording-time correction found during acceptance

A real end-to-end run reproduced a safe rollback: the zero-exposure check could miss the closing entry it had just written when the application clock was behind PostgreSQL. Current bond/FX candidate reads and worklist evaluation now use the [database recording clock](../../lifecycle/recording_clock.py). The post-write closure check takes fresh database knowledge while preserving its economic cutoff. Historical projections, frozen source facts, maturity/price rules, independent approval and the requirement to close every allocation remain unchanged. No timestamp tolerance or evidence retiming is introduced.

[Clock regressions](../../tests/test_lifecycle_recording_clock.py) reproduce an application clock five seconds behind PostgreSQL for both products, then verify one closing entry, same-key replay without duplication, no remaining exposure and the bond worklist's booked status. Synthetic source fixtures now have explicit historical recording timestamps; an old API assertion was corrected to expect the existing Tier0 denial before maturity validation.

## Verification — 11 November 2026

- Full frontend unit/component/BFF suite: **1,174 tests in 252 files passed**. TypeScript, OpenAPI export and generated-contract reproduction checks also passed.
- Focused mounted-browser regression: **13 passed**, covering drawer preparation, preserved filters, dirty-close protection, uncertain same-key retries (including a later 403), retained cancellation reason, out-of-order history, abandoned StrictMode reads, full-workspace handoff and existing assistance/allocation presentation. Responsive screenshots were inspected at desktop and 390px.
- Final disposable PostgreSQL lifecycle/API/service regression: **41 passed**, including bond/FX recording-time, scoped history/cancellation, worklist, native commands and authority checks. An earlier 42-test bounded run also covered the changed economic P&L acceptance fixtures; this was not a full backend-suite rerun.
- **Real full-stack browser acceptance passed** through normal Next BFF, FastAPI and an owned disposable PostgreSQL database using a non-owner runtime login and verified opaque sessions. It completed direct booking and prepare/independent-approval booking in the drawer. The selected user and real operator both differed at approval; self-approval stayed disabled. Applied instrument search, 50-row page size, URL, focus and valid scroll position were retained. Mobile had no horizontal page overflow.
- Post-browser SQL checks confirmed exactly **two** synthetic maturity-redemption trades, each −100,000 nominal at the sourced 100-per-100 redemption price, an independent approval receipt, and unchanged cash-snapshot counts. No operating financial commands or grants were performed.

## Repeatable isolated acceptance and limits

Run [the owned acceptance driver](../../scripts/run_lifecycle_panel_acceptance.py) with an explicit `TEST_DATABASE_ADMIN_URL` pointing to a local disposable-test PostgreSQL server, and `PLAYWRIGHT_CHANNEL=msedge` when using installed Edge:

```text
.venv/Scripts/python.exe -X utf8 -B scripts/run_lifecycle_panel_acceptance.py
```

The driver creates a uniquely named database and non-owner runtime role, starts its own loopback API/UI (defaults 8011/3011), runs [the live browser journey](../../apps/ops-console/browser-tests/lifecycle-panel.live.ts) and checks database effects, then tears those resources down. It never reads operating credentials. Private test-session state, logs and screenshots stay in ignored `.superpowers/sdd/2026-11-11-lifecycle-panel/`; do not commit them. The separate [Playwright config](../../apps/ops-console/playwright.lifecycle-e2e.config.ts) avoids mock/live artifact collisions.

The original operating startup could not bind Windows host port54329. The app was subsequently [recovered on port15432](local-postgres-port-recovery-20261111.md), retaining its original data volume and credentials. Acceptance used an owned PostgreSQL 18 container on loopback 61329; operating port mappings, credentials, subscriptions, permissions and financial rows were not changed. Financial acceptance against operating FCPGF remains unperformed for this increment. No migration is required. Discovery remains limited to bond maturity; existing FX execution shares the console/history/clock safeguards but no FX worklist detector was added. Persistent drafts and cross-session recovery remain outside this delivery.

11 November follow-up: [FX maturity worklist](fx-maturity-worklist-20261111.md) adds deliverable-forward discovery and FX-mode drawer use; it supersedes the bond-only detector boundary above without changing payment separation.
