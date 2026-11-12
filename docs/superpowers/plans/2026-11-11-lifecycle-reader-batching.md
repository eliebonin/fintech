# Lifecycle reader analysis and batch optimisation plan

> Execute sequentially using superpowers:executing-plans. No subagents, automatic commits or pushes. Preserve the current checkout and all earlier authorised work.

**Goal:** Profile every remaining lifecycle reader and eliminate measured repeated reads while retaining complete economic/authority proof.
**Architecture:** Reuse existing validators with bounded, transaction-scoped source batches. No substitute valuation or lifecycle rules. Already-efficient readers receive evidence and regression coverage rather than unnecessary rewrites.
**Spec:** [Scope and invariants](../specs/2026-11-11-lifecycle-reader-batching.md).

- [x] Freeze current readers and profile real enabled portfolios; establish distinct native fixture query budgets for options/futures/FX and identify already-batched paths.
- [x] Batch historical booking-identity source reads below HTTP, preserving unique fingerprint matching and cancelled legacy behavior; verify old/new and current/historical cases.
- [x] Batch FX maturity discovery sources/ledger/annotations where measured, keeping every native evaluator and pending-source revalidation; verify full proof/error parity.
- [x] Run affected bounded regressions, compare timings/counts and complete outputs, document limits/results, restart only the owned API and verify live reads without financial/configuration changes.

Ruling: Continue in the existing branch because the operating app uses this checkout and it contains previous uncommitted deliveries. No approval checkpoint is added to the user's authorised optimisation work.

Outcome: [measured delivery and remaining limits](../../delivery/lifecycle-reader-batching-20261111.md). Final39-test affected run,111-test central run, complete-output comparisons, OpenAPI/diff/link checks and live BFF reads pass. No migration or financial/configuration changes.
