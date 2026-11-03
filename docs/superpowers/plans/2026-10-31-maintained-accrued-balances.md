# Maintained accrued-interest balances implementation plan

> Execute sequentially in the current authorized checkout using focused test-driven steps. Preserve unrelated working changes and existing operating evidence.

**Goal:** Separate validated daily interest, maintained local accrued balances and valuation FX attribution.

**Architecture:** Keep existing daily-interest and coupon-confirmation source revisions. Add independently revisioned supplied closing balances and immutable history builds. Extract the existing local rollforward for an explicit update command; valuation reads maintained history and freezes the selected balance evidence without reconstructing it implicitly.

**Tech stack:** PostgreSQL/Alembic, SQLAlchemy, FastAPI, Next.js/React and existing tenant-context transport.

**Spec:** [Agreed economics and current evidence](../../architecture/market-data-and-valuation/accrued-balance-fx.md); the approved three-stage flow in this discussion.

## Constraints

- Local monetary balances are scoped by tenant, strategy, canonical bond, currency and date. Supplied balances are inputs; per-valuation snapshots remain outputs.
- Closing = opening + earned + bought accrued − sold accrued − actual coupon receipts. No forced reset of new-period interest, scheduled-date receipt assumption, generated cash or duplicate income.
- Exact decimals, source revisions and information cutoffs remain authoritative. Source changes invalidate derived history; supplied facts and old publications remain retained.
- Missing/stale balances disclose optional component gaps without aborting or independently blocking publication. No trade, provider, instrument or population cap is introduced.
- Preserve note-specific interest behavior, independent review, evidence-display rights and strategy action scope. Keep external CSV reconciliation scripts outside product code.

## Tasks

- [x] Add failing focused contracts/history tests and additive migration 108 for supplied balance revisions and immutable history builds/rows.
- [x] Extract the existing local bond reconstruction; implement scoped supplied inputs, explicit history updates, exact-date reads, idempotency and freshness proofs.
- [x] Consume maintained balances for FX; preserve per-run evidence, optional absence and reassessment/publication checks.
- [x] Expose scoped API/BFF operations and an interest workbench for daily inputs, balance curation and update/history inspection, linked from valuation.
- [x] Verify coupon full/partial/reversed payment, new-period earnings, bought/sold accrual, gaps/anchors, backdated correction, historical cutoffs, retries and cross-tenant/strategy access using focused pure and disposable-database tests.
- [x] Update maintained references, feature records, delivery and research sources; activate the additive schema/API locally and verify the workflow without inventing operating balances or publishing valuations.

Implementation/activation details and remaining limits are in the
[delivery record](../../delivery/maintained-accrued-balances-20261031.md).

## Research

Ruling: a derived history build is selected by its frozen **source information cutoff**, not by when its computation ran. Original supplied facts still obey their recording timestamps. This permits rebuilding a historical calculation today without admitting subsequently supplied anchors or corrections.

Ruling: unchanged updates retain their request identity but reuse the existing history rows. Receipt-only no-op builds do not invalidate staged financial evidence.

- [Microsoft materialized-view pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view), updated September 2026: explicit refresh, immutable/versioned replacement, access parity and stale-source detection. Applied to derived history, not to supplied facts.
- [IMF BPM6 Compilation Guide](https://data.imf.org/-/media/iData/External-Storage/Documents/FB1F86C7158646DDB554D0882F1F2A3B/en/3-BPM6-com-guide.pdf), paragraph 13.65: payment settles previously accrued interest rather than creating the income again. Economic analogy only; no accounting/regulatory certification claim.
