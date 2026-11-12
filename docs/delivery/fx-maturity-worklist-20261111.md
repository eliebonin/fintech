# FX-forward maturity in Lifecycle — 11 November 2026

## Delivered workflow

Open `/lifecycle`. The event filter defaults to **All events**, with **Bond maturity** and **FX-forward maturity** choices. Strategy, instrument search, dates, relevance and status apply to the full authorised population before totals and 25/50/100 pagination. Dates, event type and search survive deep links and side-panel work.

Forward rows show signed remaining **base-currency amount**, gross allocation exposure when net is zero, maturity, assistance ceiling/selection and native processing mode. Future maturities are information; due/overdue open positions are actionable. Unknown/inconsistent booking or reference evidence stays blocked/not assessed. Missing maturity pricing configuration is explained for assisted strategies; it does not turn positions into zero. Active executions after contractual maturity require reconciliation and are not declared closed by the bounded maturity projection.

**Review closing entry** opens the shared drawer in native FX mode, locking the chosen contract/strategy. Explicit preview selects the existing policy-governed maturity-day spot suggestion or a sourced Ops rate override. Prior-day substitution and arbitrary rates are not added. Preparation, confirmation, independent approval, unchanged-key retries, required fields and allocation inheritance use the existing services. A recorded closure unwinds exposure; it creates no currency delivery, payment or cash-balance snapshot.

Subscriptions, explicit strategy/event selections and user actions remain separate: Tier0 has no discovery; Tier1 notifies; Tier2 permits retained preparation; Tier3 permits operator-triggered direct booking only when the native mode/permissions allow it. Review mode still requires independent selected-user and real-operator approval. No operating selection, subscription, permission or financial record was changed.

## Implementation

- [Scoped candidates/history](../../lifecycle/worklist_repository.py), [mixed count/page boundary and bond assessment](../../lifecycle/worklist.py), [native FX assessment](../../lifecycle/worklist_fx.py), [contracts](../../lifecycle/worklist_contracts.py).
- [Filter state](../../apps/ops-console/src/features/lifecycle-worklist/client.ts), [console](../../apps/ops-console/src/features/lifecycle-worklist/worklist-console.tsx), [drawer](../../apps/ops-console/src/features/lifecycle-worklist/lifecycle-action-panel.tsx), [page guide](../../apps/ops-console/src/lib/page-guides.ts).
- [Plan](../superpowers/plans/2026-11-11-fx-maturity-worklist.md) and [scope](../superpowers/specs/2026-11-11-fx-maturity-worklist.md).

The read model reuses the native forward term/ledger/allocation reader. Ordinary discovery does not fetch closing rates; pending proposals alone require full native source-fingerprint reassessment, preserving their rate override and governed inputs. Combined event types are filtered and paged together. No new API mutation, schema migration, job scheduler or notification acknowledgement store was introduced.

A focused regression also reproduced loss of operator-entered **standard** fields during prepared-entry revalidation: stored custom properties were replayed, but standard inputs such as Comment were omitted. [The shared reconstruction helper](../../lifecycle/allocations.py) now restores both categories for bond/FX confirmation and worklist reassessment. Existing prepared inputs and historical evidence are retained, never rewritten; all normal validation still runs.

## Verification and limits

- [Domain tests](../../tests/test_fx_maturity_worklist.py) cover exact quantities/read-only discovery, mixed filters/counts, tier/tenant boundaries, partial closes, opposing allocations, source changes, cancellation, missing evidence and standard-field retention. Initial contract/filter tests failed before implementation; the standard-field regressions failed for both products before correction.
- [Mounted browser journey](../../apps/ops-console/browser-tests/fx-maturity-worklist.spec.ts) verifies event filtering, native FX routes, no financial command on opening, explicit booking and retained context; existing bond drawer/worklist journeys are retained.
- The [real isolated driver](../../scripts/run_lifecycle_panel_acceptance.py) accepts `LIFECYCLE_E2E_PRODUCT=fx-forward`, explicit test-only `TEST_DATABASE_ADMIN_URL` and optional `PLAYWRIGHT_CHANNEL=msedge`. It creates its own database, non-owner runtime role and verified synthetic sessions, exercises direct and independently approved closures, verifies exact generated trades/approval/cash counts, and tears down its app/database/role. It does not read operating credentials.
- Bounded backend/native/allocation run: **56 passed**. Final targeted checks separately verified the modified API enum, future-event handling, blocked late execution and retained standard fields. The late-execution fixture initially violated the existing recognition-date constraint; its dates were aligned rather than weakening the constraint.
- Focused frontend/BFF/help checks: **37 passed**; **9 mounted browser journeys** passed across focused runs. TypeScript, OpenAPI export and byte-for-byte generated-contract reproduction passed. The synthetic FX browser fixture was corrected to include the already-required MARKET_DATA_READ permission; no product guard was relaxed.
- Final real BFF/API/PostgreSQL acceptance passed with **two** synthetic MATURITY_CLOSE trades, each −1,000,000 base-currency units at 1.12, direct and independently approved processing, retained Ops Comment, no duplicate effect and unchanged cash-snapshot counts. Search, page size, focus/scroll and 390px mobile behavior remain covered. Screenshots were inspected.
- Normal API 8000 was restarted with its existing private settings; frontend 3001 stays running. No migration or operating trade/selection/permission was applied. This is bounded lifecycle acceptance, not a full backend regression or a complete lifecycle/accounting engine.

Coupons, futures/options expiry, NDF lifecycle, physical cash delivery, persistent drafts and notification acknowledgements remain separate work. No existing strategy is automatically upgraded/enabled. Enable FX-forward maturity assistance for a strategy and configure its maturity pricing policy in the full workspace before using assisted closure.
