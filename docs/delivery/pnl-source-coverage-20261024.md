# P&L sources and coverage

**Status:** Implemented; focused verification recorded below  
**Content type:** Delivery and research record  
**Owner:** Valuation / Operations engineering  
**Last reviewed:** 2026-10-24

Follow-up to the [Ops review workspace](pnl-ops-review-20261024.md).
The user approved source coverage first, with cash FX P&L a separate calculation
change. No new financial calculation, migration or write workflow is introduced.

**25 October scope update:** the [separate cash-FX delivery](cash-fx-pnl-20261025.md)
now implements opt-in daily account-owned cash FX. The exclusion below records
this earlier presentation-only delivery, not the current calculator's entire
scope. Current UI uses included/partial/unassessed/not-requested states; old
financial results are not recalculated or rewritten.

## Operator workflow

Open `/valuation`, Results, choose a strategy and result. Beneath the headline
amounts, **P&L sources & coverage** shows the whole result in reporting currency:

| Source | Stored components | Meaning / boundary |
| --- | --- | --- |
| Price movements | PRICE | Investment price movement |
| Position FX movements | FX | Investment currency translation, not cash balances |
| Price × FX interaction | PRICE_FX_CROSS | Joint movement; do not add it twice |
| Daily interest earned | ACCRUAL | Daily added earnings, not accrued balance |
| Accrued-interest FX | CARRY | Translation from supplied accrued-stock evidence |
| Resets | RESET | Dated income-classified flows, not cumulative positions |
| Dividends | DIVIDEND | Recorded income flows, not an entitlement-completeness check |
| Other recognised income | COUPON, CASHFLOW | Income-classified entries; payment confirmation alone creates no earnings |
| Fees and taxes | Cost components except ADJUSTMENT | Signed costs, reducing the result when negative |
| Controlled adjustments | ADJUSTMENT | Retained adjustments in this result version |
| Cash-balance FX P&L | None | **Not implemented; excluded**, never shown as zero |

Separately stored MODEL_MARK_CHANGE or unknown future component codes are shown
when present, not dropped from the arithmetic. Existing inclusive market/gross/net
totals are not added as extra sources. Every supported code is classified once.

Included component amounts reconcile, using exact server-side Decimal sums, to
the stored net result. The UI formats decimal strings for scanning and retains
exact source amounts in a disclosure. A mismatch says to investigate; a legacy
result with no adequate breakdown or no stored net says **Not assessed**. A
missing historical breakdown is not replaced with a zero source total.

“Inspect positions” clears conflicting search/attention filters, selects all
contributing positions across the full authorized result before pagination, and
moves keyboard focus to Position attribution. Recorded zero components still
contribute. Rows retain their full position P&L, clearly labelled, rather than
pretending the report has recalculated source-only position totals. “Show all
sources” removes that source filter. Headline totals remain whole-result amounts.

## Status semantics and safeguards

- **Included · recorded:** at least one component is stored, including exact zero
  or a zero resulting from positive/negative entries netting out.
- **No recorded entries:** no P&L component entry in the available breakdown;
  never evidence that no dividend, reset or fee was economically due.
- **Partial · missing interest:** supplied interest is included, with missing
  bond/date input count retained. **Missing inputs · Excluded** has no supplied
  interest amount. Missing optional interest is not a confirmed zero.
- **Not assessed:** historical evidence cannot establish the breakdown.
- **Not implemented · Excluded:** cash FX is outside this result. A persistent
  warning and cash-register link remain visible, even without new API metadata.

Arithmetic reconciliation does not certify complete operational coverage,
independent provider comparison, full NAV, settlement or accounting. Cash snapshots
are dated stocks in a separate register. Do not substitute their translated change
for profit: the later cash-FX calculation must explicitly define balance/flow
timing, revisions, account/currency coverage and any overlap with income flows.

The response-only projection runs after existing strategy and DISPLAY gates.
Denied results release neither this table nor cash/source financial metadata.
No additional database reads, evidence rewrites, component changes, source-rights
grants, publication bypass or automatic cash calculation are added. Publication
keeps all existing server-side controls. Stored batch hashes and totals remain
unchanged; older stored results can receive the projection on an authorized read.

## Research and applicability

Official sources opened and reviewed on 24 October 2026:

- [GOV.UK tables](https://design-system.service.gov.uk/components/table/): comparison
  belongs in a captioned table with scoped headers and right-aligned numbers.
  Applied to source, amount, coverage and inspection; not a layout table.
- [WCAG 2.2, Understanding SC 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html):
  status cannot depend on colour alone. Every state has visible text. This is
  application of guidance, not a complete accessibility certification.
- [Tableau: missing values](https://help.tableau.com/current/pro/desktop/en-gb/missing_values.htm):
  distinguishes missing/null data from absent rows. This reinforces our explicit
  missing/recorded-zero distinction; no Tableau dependency or prescribed schema.
- [IFRS 18 overview](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-18-presentation-and-disclosure-in-financial-statements/):
  aggregation/disaggregation and clearer presentation inform the choice of named,
  disjoint groups and reconcilable subtotals **by analogy only**. IFRS 18 is effective
  for annual periods beginning on/after 1 January 2027, with early application
  permitted. This internal Ops trading report is not an IFRS financial statement.

The exact taxonomy and coverage states are project design choices; these sources
do not require our P&L formula, source codes or cash convention. No source resolves
the future cash-FX methodology decision for us.

## Implementation and verification

- [Pure source projection](../../apps/reference_api/valuation_source_coverage.py),
  called by the [authorized presentation adapter](../../apps/reference_api/valuation_presentation.py).
- [Coverage table](../../apps/ops-console/src/features/valuation/source-coverage.tsx),
  [result integration](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
  [full-result filter](../../apps/ops-console/src/features/valuation/ops-review-model.ts).
- Test-first exact/zero/missing/netting/unknown/legacy checks:
  [pure tests](../../tests/test_valuation_presentation.py).
  [Disposable PostgreSQL checks](../../tests/test_valuation_presentation_api.py)
  compare complete staged evidence, amounts and summaries before/after decoration;
  existing history tests retain financial-denial coverage.
- [Component tests](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx)
  verify visible cash exclusion, status distinctions and denied disclosure;
  [browser journey](../../apps/ops-console/browser-tests/pnl-ops.spec.ts) verifies
  inspection focus and unchanged explicit publication.

Execution evidence:

- **21 focused backend tests passed**: 10 pure projection tests plus the
  presentation/history checks against an owned, migrated disposable PostgreSQL
  database. No operating test writes. One existing Starlette/httpx deprecation
  warning remains.
- **70 frontend tests passed across 13 files**; TypeScript and deterministic
  OpenAPI checks passed. Whitespace and delivery/plan local-link checks passed.
- **Four isolated Edge browser journeys passed**: optional and strict accrual
  ticket flows, legacy bounded-label fallback and the Ops coverage/review flow.
  The latter verifies table statuses, contributor inspection/focus, preserved
  explicit publication and a narrow-screen document-overflow check. Its screenshot
  was visually inspected. Browser colour-environment warnings remain.
- Local **API 8001 restarted**, health 200; UI 3001 responds 200. A read-only GET
  of the retained FCAGF result exposes 11 source rows, 27 investment positions,
  partial supplied daily interest and excluded cash FX. Exact stored breakdown:
  price 27338.838516404389; position FX -4970.815561350541; interaction
  -93.800946718036; supplied interest 226.92; **net 22501.142008335812 GBP**.
  The projection reconciles without recalculation or publication. Refresh an
  already-open result to receive the metadata.

No full Python suite, new financial acceptance, operating recalculation or
publication was performed. Review is sequential author self-review, not an
independent audit. Cash FX remains the next separate calculation change.

## 24 October follow-up: precision and historical unknowns

A bounded self-review reproduced two presentation defects, now corrected:

- The shared valuation formatter previously made positive and negative tiny
  nonzero amounts look like `0.00`. After normal two-decimal half-even rounding,
  amounts that would otherwise become zero display as `<0.01` (positive) or
  `−<0.01` (negative). Genuine zero, including a signed zero, stays `0.00`.
  Ordinary half-even results are unchanged: `0.005` uses the nonzero marker;
  `0.005000000001` displays `0.01`. Inspection keeps original exact strings.
  String digits/BigInt avoid binary-float underflow and precision loss. The marker
  threshold refers to this two-decimal display, not every currency's minor unit.
- Historical `NOT_ASSESSED` rows now say **Not assessed** in the inspection column,
  instead of incorrectly asserting **No contributions**. An assessed absent source
  says **No recorded entries / No recorded contributions**. A recorded zero keeps
  its inspection action. Coverage meaning is unchanged; unknown is not absent.

The visible widget legend explains the signed markers. The shared formatter also
applies the correction to existing valuation headline, report, amendment and
publication displays; no component, stored total, evidence, API, database or
publication-control change.

Sources opened on 24 October 2026:

- [ONS rounding guidance](https://service-manual.ons.gov.uk/content/numbers/rounding):
  balance readability with retained precision, including small important values.
- [GOV.UK data style guide](https://www.ethnicity-facts-figures.service.gov.uk/style-guide/data-style-guide/):
  distinguish unavailable, inapplicable and rounded-to-zero data, with explanations.
  Its statistical symbols and one-decimal convention are not copied as financial
  requirements; our signed inequality marker is an explicit product choice.
- [Commons Library rounding guidance](https://commonslibrary.parliament.uk/research-briefings/sn04443/),
  published 17 March 2026: documents round-to-even and rounding limitations. We
  retain the established half-even policy rather than replacing it with an
  unrelated statistical disclosure-rounding rule.

Test-first regressions: [formatter cases](../../apps/ops-console/src/features/valuation/presentation.test.ts)
and [coverage rendering](../../apps/ops-console/src/features/valuation/source-coverage.test.tsx),
covering sub-cent signs, true zero, underflow-sized strings, half-even boundaries,
exact inspection and historical unknown/assessed-absence distinctions.
Follow-up verification: **89 focused frontend tests across 15 files**, TypeScript,
and **four isolated synthetic browser journeys passed**. This includes 19 new
formatter/rendering cases, with both defects observed RED before the fix. Existing
browser colour-environment warnings remain. The local UI on port 3001 returned
HTTP 200; frontend hot reload serves the changes. No full Python suite, database
changes, operating financial writes or backend restart were needed or performed.
