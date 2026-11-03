# Accrued-balance FX — 27 October 2026

Current rules, limits and workflow:
[maintained reference](../architecture/market-data-and-valuation/accrued-balance-fx.md).
Design/plan:
[agreed scope](../superpowers/specs/2026-10-27-accrued-balance-fx-design.md),
[execution plan](../superpowers/plans/2026-10-27-accrued-balance-fx.md).

Implemented pure local-stock replay, as-of original-source loading, policy FX,
typed immutable dataset 3, once-per-canonical CARRY, separately scoped unpaid
receivables after disposal, coverage/inspection, source-health and publication
revalidation. No import-tool dependency, fabricated cash or new income on receipt.

## Approval and implementation choices

Automatic review rejected the first broad integration proposal. The optional
interest FX handling was isolated and tested without changing the shared FX
resolver. Central staging/evidence integration was separately approved by the
user. Existing financial guards were preserved and a bounded receivable branch
was added after a regression reproduced its rejection of the new owner type.

Existing source-version diagnostic precedence was retained. An adjacent test
that deleted all shared price observations failed against retained snapshots;
it now asserts that a flat round trip makes no price-selection call, preserving
the evidence and the original economic test. The historical reference-calculator
test retains the existing legacy storage branch without adding a new runtime
calculation fallback.

## Verification

Pure replay and optional FX RED→GREEN: 9 checks. Initial integration reproduced
missing component/coverage and whole-run optional-FX failure. Subsequent focused
runs exercised actual governed FX (1,260 GBP opening stock × 0.5 USD/GBP change =
630 USD), daily income, coupon receipts, immutable balances and stale publication.
Final scoped backend run: **74 passed**, covering pure replay, optional FX,
database integration, coupon corrections/reversal/as-of, stale publication,
reassessment, existing bond economics, position/cash ownership and presentation.
Tests explicitly rejected foreign-scope and wrong-amount receivables and mutated
balance rows. The full Python suite was not run. A pre-existing Starlette
deprecation warning remains; no warnings were suppressed.

Frontend regression: **1,055 tests passed in 214 files**. Focused read-only
inspection/coverage/model checks passed. Two isolated browser journeys passed,
covering complete versus missing stock, exact local/FX values, mobile overflow
and closing the inspection panel. These use synthetic responses, not operating
financial commands. Screenshots are retained in ignored `test-results/`.

TypeScript and OpenAPI parity passed. Final focused display checks additionally
cover scaled zero stocks and native currency labels when FX is absent.

## Local activation

Verified the app was at migration 100, then applied **101** and restarted API
8001. Existing operating trade, coupon-payment, attribution and review-batch
counts remained unchanged; the new derived-balance table was empty after
activation. Existing cash, position, component and review scope guards remained
present alongside the bounded receivable branch. No grants or operating
financial inputs were created; no operating valuation was run or published.
Frontend remains on port 3001. Existing financial runs are retained; recalculate
to obtain the new component/coverage and derived stock evidence.

## Deliberate limits

No accrual generator, automatic entitlement/coupon posting, receipt-to-bank
reconciliation, intraday FX accounting or complete NAV. Unknown history remains
unknown; assessed anchors are the recovery path. Multi-currency daily-history
changes and unmatched coupon payment currencies are disclosed, not invented.
The prior opt-in strict daily-interest mode is unchanged. Stock FX coverage is
non-blocking; invalid supplied evidence and stale sources remain blocking.
