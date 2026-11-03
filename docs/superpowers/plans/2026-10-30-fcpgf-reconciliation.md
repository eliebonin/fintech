# FCPGF reconciliation import plan

**Goal:** Import the owner-supplied GBP strategy at 20 October 2026, without adding a source-specific interface to the product.

**Boundary:** All adapters and synthetic adapter tests stay in `tooling/reconciliation_csv`. Raw files, financial rows and detailed reports stay in ignored private evidence. Existing native authority, approval, booking, market-data rights and valuation controls remain authoritative. No operating valuation will be published by this exercise.

## Delivery steps

- [x] Retain all source files, including the new coupon/principal schedule. Support identifier-based `fx.csv` without changing existing bundle identities. Test byte preservation and unknown currency rejection.
- [x] Create the separate GBP strategy under tenant one. Reuse compatible private references where justified; retain explicit mappings and assumptions. Ignore stale bond term rows for source-classified funds.
- [x] Create supported native funds, bonds, performance swaps, autocall underlyings, forwards and the standard SPX option. EQUITYOTC is a taxonomy on SWAP instruments. Missing autocall details are explicitly synthetic. The subsequent native rate-exchange extension completes the four remaining two-floating-leg components while retaining their original identities and marks.
- [x] Book supported native investments, all date-only RESET income, separated cash accounts and daily interest using existing writers. Preserve every row identity, precision delta and rejected/unmapped row. No cash-account netting, cumulative RESET position or duplicate option multiplier.
- [x] Import all source prices, FX and contractual bond schedules with retained provenance. Report exact posting reconciliation and unsupported structures without weakening validators.
- [x] Resolve the 28 zero-price fund rows through owner-approved 12 TRANSFER/16 REINVESTMENT native movements, without relaxing positive-price purchase validation. All 200 fund entries and ten quantities reconcile; classification and optional-income limitations are retained.
- [x] Complete all source posting: 383 unique position entries and 1,002 RESET records; four rate components booked idempotently and all existing prices/RESETs unchanged. The negative-price fund entry retains its owner-authorised positive-price correction and original evidence.
- [x] Activate an FCAGF-equivalent policy for FCPGF's own datasets, including a published tenant NAV date calendar; preserve all original financial rows. See the [31 October attempt](../../delivery/fcpgf-valuation-attempt-20261031.md).
- [ ] Full-portfolio valuation acceptance: the 31 October run failed on two absent 19 October contract-forward marks; 248/250 required position marks selected. Supply the missing source observations, then run a new attempt and reconcile. No financial batch staged or published.

## Checks and limits

Use synthetic focused adapter tests first, then disposable database integration checks. Verify source counts, signed native quantities, transformations, replay safety and tenant ownership against the operating import report. No full Python regression suite is required for isolated tooling changes. Two-leg asset swaps must not be silently collapsed or reclassified to evade native model restrictions. New source schedules include historical and future payment dates; those are contractual dates, not future observed prices or confirmation of payment.
