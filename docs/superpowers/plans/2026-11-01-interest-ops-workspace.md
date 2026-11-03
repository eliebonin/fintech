# Interest maintenance workspace — 1 November 2026

**Completed:** [delivery, checks and limits](../../delivery/interest-ops-workspace-20261101.md).

## Intent and boundaries

Ops maintain three related datasets: daily earned interest, sourced closing-balance
inputs and rebuilt accrued-balance history. Replace the crowded two-tab page with
three task tabs, contextual editors, explicit applied filters and independent
loading/error states. Remove page-specific P&L navigation and the calculation
step banner. Normal workspace navigation remains available.

Financial arithmetic, coupon reset/payment rules, authorization, append-only
revision history, exact decimal values and retained idempotent retries stay in
their existing services. This is not bulk upload or an accounting workflow.

## Delivery steps

1. Add focused tests for exact inputs, correction payload preservation, accessible
   tab/table presentation and unchanged-key retry after uncertain responses.
2. Split data loading, input editing and source tables out of the register.
   Apply strategy/date filters explicitly; isolate history pagination from source
   reads. Keep the per-row full-series chart and its 25/50/100/All table.
3. Add separate add/correct/withdraw editors with clear context, field errors,
   discard protection and retained mutation feedback. Rebuild is a deliberate
   write; refreshing records is read-only. Show current/stale/unassessed honestly.
4. Allow the existing history query to filter by instrument before counting and
   pagination, preserving strategy authorization. No migration is required.
5. Run focused frontend and isolated backend checks, TypeScript and read-only
   browser acceptance. Update the capability, implementation map and page help.

## Research applied

- [Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
  (updated 30 September 2026): table toolbars, contextual row actions and progressive
  evidence disclosure. Use compact tables with separate source and rebuild actions.
- [GOV.UK tabs](https://design-system.service.gov.uk/components/tabs/): related
  datasets shown one at a time for regular users; do not make a mandatory wizard.
- [GOV.UK error summaries](https://design-system.service.gov.uk/components/error-summary/):
  identify actionable field failures and preserve entered data.
- [Visibility of system status](https://www.nngroup.com/articles/visibility-system-status/)
  (3 June 2018): distinguish loading, saved sources, stale derived history and
  uncertain mutation outcomes.
- [Native dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog):
  modal focus/background behavior, Escape and accessible names.

These are UI recommendations, not financial or regulatory rules. The three-tab
split and explicit rebuild action are project-specific applications.
