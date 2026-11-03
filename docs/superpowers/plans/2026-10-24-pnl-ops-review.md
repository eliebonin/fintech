# Daily P&L operations review — implementation plan

**Status:** Implemented; bounded verification recorded in delivery
**Content type:** Plan and accepted design
**Owner:** Valuation / operations console
**Last reviewed:** 2026-10-24

## Goal and accepted design

Help Ops review and explicitly publish daily trading P&L. Retain Input form,
Results and History. Use readable business labels by default, a compact position
report, visible review warnings and a contextual publication confirmation.
Keep full IDs and exact frozen evidence accessible. External reconciliation,
charts, tags, weights and full NAV are outside this scope.

Approaches considered: hiding UUID text alone would leave inconsistent and
ambiguous labels; a full workspace rewrite adds unnecessary regression risk.
The user approved incremental labels, summary, report, inspection and confirmation.

## Constraints

- No calculation, persisted financial values, source rights or authority changes.
- Presentation metadata is current and non-authoritative, outside frozen evidence.
- Enrich financial detail only after existing DISPLAY checks; preserve tenant,
  strategy and private-parent visibility. No broad metadata endpoint.
- Missing interest is not zero. Warnings do not become new publication blockers.
- Group stored components on the server; never calculate financial totals in JS.
- Filters/sorts cover the full selected result before position pagination.
- Existing real-operator independence and explicit self-publication remain intact.
- Work sequentially in the current checkout on `codex/pnl-ops-review`.

## Tasks

1. Add tested read-only presentation projections: batch metadata in bounded
   queries, readable historical strategy/policy/currency labels, stored-component
   rollups and known pending-amendment count. Owners:
   `apps/reference_api/valuation_presentation.py` and `valuation_routes.py`.
2. Add shared reference/technical-ID rendering and full-result search/sort helpers.
   Update result types, summary, table, inspector and price/interest evidence.
   Keep IDs available through disclosures/copy controls.
3. Use the shared labels for amendments, report context, history and reassessment.
   Publication confirmation repeats the selected run, total, warnings and review
   mode. No new mutation or authority route.
4. Add focused unit/API regressions and isolated browser journeys; preserve
   numerical regression fixtures. Update capability, register and implementation
   map plus a dated delivery record with actual verification evidence.

Each task starts with a failing focused test; verify green before proceeding.
Run focused Python tests only in runner-owned disposable PostgreSQL; browser
fixtures use isolated servers and synthetic data. Do not publish operating data.

## Review focus

Duplicate names / different listing buckets; labels beyond the first page;
restricted or foreign references; historical missing evidence; missing optional
interest; unknown publication checks; stale candidates; post-submit refresh errors;
large and sub-penny decimal strings; keyboard and narrow-screen operation.

## Research checked 24 October 2026

- [GOV.UK tables](https://design-system.service.gov.uk/components/table/): semantic
  comparison tables and right-aligned numeric values.
- [GOV.UK details](https://design-system.service.gov.uk/components/details/):
  disclose secondary evidence, never hide essential review warnings.
- [Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
  (updated 30 September 2026): compact rows, sorting, paging and progressive detail.
- [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/):
  contextual summary before committing a consequential submission.
- [WCAG 2.2 SC 3.3.4 explanation](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html):
  review/confirmation helps prevent consequential submission errors. This is
  accessibility guidance, not a financial-control certification.

The financial columns, label hierarchy, warning categories and retained workflow
are project choices informed by these sources, not universal industry requirements.

## Execution ledger

- Setup: clean main at `1b9142d`; feature branch created. No operating data changes.
- Ruling: retain current checkout per prior user preference; no new worktree.
- Ruling: use focused verification per user instruction, not the full Python suite.
- Pre-flight: backend presentation names and component rollups feed the table,
  inspector, amendment selector and publication summary; a single typed frontend
  contract will be shared by these consumers.
- Tasks 1–4: implemented. Metadata/projections, shared labels, review report,
  compact frozen-input comparison and contextual publication are wired and tested.
- RED→GREEN: pure grouping, full-result model, frozen-bucket captions, report
  content, compact input comparison and exact batch totals.
- Verification: 51 focused DB regressions; final 15-test DB follow-up (overlap).
  Four synthetic Edge journeys and final 67 focused frontend tests passed;
  type/contract/whitespace checks passed. No full Python suite.
- Final review: author self-review, sequential execution per user preference.
  Checked disclosure placement, tenant/private-parent scope, fixed-precision
  grouping, frozen evidence identity, complete-result filtering and final authority.
- Ruling: table inputs replace stacked evidence cards after visual inspection;
  same frozen fields/proof are retained, improving scan density.
- Activation: local API 8001 restarted after detecting old-API/new-UI mismatch;
  all 27 FCAGF references resolve. No operating financial data changed.
- Follow-up proposal was subsequently approved and delivered as the
  [source coverage widget](../../delivery/pnl-source-coverage-20261024.md).
  Cash snapshots remain separate and cash FX P&L remains excluded. No new cash
  calculation is part of this UI refinement.

## Approved follow-up: P&L sources and coverage

User approved the coverage widget first on 24 October. Cash-balance FX remains a
separate calculation change. Implementation sequence: failing exact-component
projection tests; response-only grouping behind the existing DISPLAY gate;
compact accessible source/amount/status table with full-result inspection;
focused backend, frontend and isolated browser checks; documentation and local
API activation. No migration, financial mutation or calculation change.

Always show price, position FX, interaction, daily interest, accrued-interest FX,
resets, dividends, other income, costs, adjustments and the excluded cash source.
Recorded zero, no recorded entry, missing inputs, historical unassessed and
unimplemented are distinct. Included groups must be disjoint and reconcile to
the frozen net total. Reconciliation is arithmetic, not certification of complete
income coverage or independent provider comparison.
