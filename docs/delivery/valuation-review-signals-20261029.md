# Compact valuation review and dual-currency accrued stocks

**Status:** Implemented; focused verification passed  
**Content type:** Delivery and scoped review  
**Owner:** Valuation and operations engineering  
**Last reviewed:** 2026-10-29

## Agreed scope

User approved review-signal fixes and local/reporting accrued-stock display.
Mixed-portfolio financial acceptance remains deferred until they supply data.
No valuation formula, source rights, publication authority or missing-data gate
is relaxed. This addresses FIX-VAL-005/006; it is not a new full-codebase audit.

## Quiet, persistent review signals

The shared result summary contains one **Inputs to review** disclosure, collapsed
for each newly selected batch. It shows partial coverage and affected position/
cash-input counts. Expanding it reveals grouped notes, exact missing dates/scopes
and actions to show affected positions or cash coverage. The disclosure collapses
again after navigation so it does not obscure the selected data.

Per-position notes are deduplicated; a small count opens the existing inspector.
The Attention-only filter covers the entire result before pagination. Missing
daily-interest FX, accrued-stock FX/balances, currency/scope failure and assessed
anchor differences now participate. Currency failures without a balance line
map to frozen canonical booking identities, not current master-data guesses.
The inspector shows relevant notes locally. Exact source/movement proof remains.

Cash-only actual-window gaps now mark the included total **partial**, including
read display of earlier results carrying those gaps. Absent/disappeared historical
account/currency combinations do not create expectations or warnings. Allowed
prior-session inputs remain review notes rather than an automatic partial-P&L
classification. Recorded components do not certify complete economic coverage.

Duplicated stock/interest/cash banners were removed. Cash dates remain available
under a local disclosure; source-table status/counts remain visible. Blocked
source state and pending amendments still have the existing prominent blocker
area. Optional omissions do not create a modal, acknowledgement requirement or
new publication gate. No warning is permanently dismissed from the evidence.

## Accrued stocks in both currencies

[Response projection](../../valuation/accrued_balance_presentation.py) reads
retained local opening/closing stocks and translates each at its frozen boundary
FX with exact Decimal arithmetic. It can reuse an unambiguous already-retained
policy conversion for the exact day and currency orientation when the stock
proof did not need its own rate. It never looks up current FX, silently inverts
rates or chooses among conflicting conversion values.

Equal recorded currencies imply identity; a known zero stock translates to zero
without a rate. Missing stock, target currency or foreign rate leaves only that
boundary unavailable. A missing opening stock does not hide a known closing
stock. Explicit signed/negative amounts retain their sign. The original accrued
stock, daily interest, movements, coupon receipts and CARRY are unchanged.

The inspector shows local/reporting amounts together for opening and closing
stock, with two-decimal scan formatting and exact values in titles/proof. Daily
movements and FX inputs are behind a native disclosure. No duplicate stock
columns, migration, recalculation or financial-evidence backfill is needed.

## Implementation and verification

- [Coverage/Attention classification](../../valuation/review_coverage.py),
  [calculation completeness](../../valuation/service.py),
  [authorized response decoration](../../apps/reference_api/valuation_presentation.py)
  and [source coverage](../../apps/reference_api/valuation_source_coverage.py).
- [Compact disclosure](../../apps/ops-console/src/features/valuation/coverage-review.tsx),
  [report navigation/inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
  [stock display](../../apps/ops-console/src/features/valuation/accrued-balance-inspection.tsx).
- 51 offline coverage, exact-stock, presentation, replay and architecture cases
  passed. [Focused numerical cases](../../tests/test_valuation_review_signals.py)
  include independent boundary availability, exact precision, currency/date/
  orientation constraints, ambiguity and no evidence mutation.
- 39 owned disposable-database cases passed across cash, accrued stocks,
  authorized metadata and DIRTY bond calculation. Two cases were then rerun with
  explicit assertions that optional cash omissions remain publishable and stock
  projections preserve exact retained evidence. No operating financial writes.
- Final response-projection indexing was checked again with 11 disposable cases;
  missing-scope and FX lookups are indexed per response, with no extra SQL reads.
- 47 focused frontend cases passed; TypeScript and OpenAPI parity passed.
  [Two isolated Edge scenarios](../../apps/ops-console/browser-tests/valuation-review-signals.spec.ts)
  passed, covering keyboard disclosure/focus, full-result filtering past row 25,
  inspector closure, mobile width and console diagnostics. A desktop screenshot
  was visually inspected. This is not assistive-technology certification.
- No full Python suite or independent mixed-portfolio financial sign-off.

API 8001 was reloaded and `/health` returned `status: ok`. The frontend was
started on port 3001 for local review. No schema migration or operating financial
write was performed. Source licensing and publication authority were unchanged.

## Research and limits

Checked 28 October: [GOV.UK notification guidance](https://design-system.service.gov.uk/components/notification-banner/)
supports sparse banners and in-context information. [Carbon notifications,
updated August 2026](https://www.carbondesignsystem.com/building-blocks/core/patterns/notifications)
supports concise inline feedback. [W3C WCAG 2.2 status guidance](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
supports status updates without unnecessary focus interruption. This delivery
uses polite status text, native keyboard-operable disclosure, and words/counts
alongside colour. The specific aggregation and navigation are product choices.

Unavailable frozen conversions are disclosed, not fetched retrospectively.
Broader source-impact fanout, full NAV/accounting, instrument pricing models and
independent realistic-portfolio reconciliation remain separate work. See
[FIX.md](../../FIX.md) and the [implementation plan](../superpowers/plans/2026-10-28-valuation-review-signals.md).
