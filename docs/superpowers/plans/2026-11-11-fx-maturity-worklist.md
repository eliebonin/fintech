# FX maturity worklist implementation plan

Execute sequentially using superpowers:executing-plans; user requested no subagents.

**Goal:** discover and action forwards in the existing mixed Lifecycle dashboard.
**Architecture:** scoped candidate/history queries, separate bond/FX assessment, shared filter/count/page boundary and native FX drawer.
**Spec:** [task scope](../specs/2026-11-11-fx-maturity-worklist.md).

- [x] RED/GREEN query and isolated FX discovery/status/source/tier/scope tests.
- [x] Extend contracts and scoped read model; combine events before totals/pagination.
- [x] All/Bond/FX UI filter, correct drawer mode/deep link; regenerate contracts.
- [x] Focused native/HTTP/frontend/browser checks and synthetic full-stack flow in an owned disposable DB; no operating financial writes.
- [x] Reconcile delivery, feature register/map and boundary guidance; activate only our API/UI.

Review: preserve opposed allocations, explicit missing evidence, cancellation history, current full source fingerprints, tenant visibility and dates. Preserve uncommitted port-recovery edits.
