# Ops interest maintenance workspace

**Date:** 1 November 2026  
**Status:** Implemented and locally verified  
**Scope:** F38/F39 maintenance UX; F38 PARTIAL / F39 ALPHA remain.  
**Plan and research:** [implementation plan](../superpowers/plans/2026-11-01-interest-ops-workspace.md).

## What Ops can do

`/valuation/interest` is a data-maintenance workspace with three task tabs:

| Tab | Dataset and actions | Consequence |
| --- | --- | --- |
| Daily interest | Add a sourced daily earned amount; correct an existing row. | Retains a new validated source revision. Rebuild history to incorporate it. |
| Closing balance inputs | Add/correct an assessed end-of-day accrued stock; separately withdraw with a reason. | Establishes/reconciles a stock. Withdrawal is not a zero replacement and does not delete the old evidence. |
| Accrued balances | Inspect opening/closing stocks and source status; rebuild an explicit date window; open each row's chart. | Rebuilds immutable maintained history from current sources. It does not book cash or calculate/publish P&L. |

The old calculation step banner and page-specific links to P&L valuation are
removed. Normal workspace navigation remains. Page help now explains maintenance
tasks, correction effects and the difference between read-only refresh and rebuild.

## Interaction and reliability

- Apply strategy/date filters explicitly. The applied scope is displayed beside
  the actions and retained in the URL for reload/bookmark use. A bond filter applies
  across the three datasets; new entries preselect that bond and the end date.
- Daily and closing inputs use the complete returned date-window collection before
  filtering and 25/50/100/All pagination. The balance overview requests only the To
  date, with one row per bond/currency. SQL filters that exact date and instrument
  before count/offset; 25/50/100 server paging counts balances, not historical days.
  The snapshot date appears once in the table caption. The per-bond chart initially
  covers From to To, with its separate full-series 25/50/100/All datapoint table.
  No older value is silently substituted for a missing To-date balance.
- Options, daily inputs, closing inputs and history have independent loading,
  failure and retry states. History paging does not reload source datasets. Scoped
  query identity and abort/obsolete guards prevent old strategy data from appearing
  under a newly selected strategy. Errors are not treated as empty collections.
- Add/correct/withdraw use named native modal dialogs. Corrections lock bond,
  currency and value date, show strategy/date/revision context, and retain previous
  records. Withdrawal requires a source and reason without an unrelated replacement
  amount. Unsaved close/Escape has Keep editing/Discard choices; keeping the editor
  retains entered values. The page unload guard also covers dirty drafts.
- Exact decimal strings accept valid thousands separators, preserve up to the
  existing NUMERIC(30,12) capacity, and reject excess precision instead of rounding.
  Errors remain beside the editor, with a focused summary and known field links.
- Corrections preserve optional eligible nominal/convention and existing detailed
  balance-reconciliation context. Detailed inputs expose their retained bridge for
  correction; the backend still validates it and resolves governed FX. The UI does
  not downgrade a detailed input to a daily-only one to bypass validation.
- Existing retained mutation logic keeps the original payload and idempotency key
  after an uncertain transport/server outcome. Incomplete or wrong-context success
  receipts are also uncertain. Controls stay locked and retry is manual and unchanged.
  Definitive validation failures preserve editable input values.
- Success reports the source/value date and prompts a deliberate rebuild. Rebuild
  confirmation states that it covers all strategy bonds, including any hidden by a
  table filter. Refresh only reloads existing records. No background rebuild occurs.
- The overview emphasizes opening/closing balances. The daily/trade/coupon bridge,
  exact technical proofs and full build source catalogue remain inspectable rather
  than being removed. Tables have no nested vertical scroller; wide tables still
  allow horizontal scrolling. Keyboard tabs, named controls and modal focus remain.

## Authority and financial boundaries

MARKET_DATA + VALUATION and applicable strategy VALUATION_READ remain required.
Writes still require applicable VALUATION_RUN or VALUATION_REVIEW. Current server
authority precedes idempotent replay; BFF context, transactional audit and immutable
revisions are unchanged. The optional instrument history filter only narrows rows;
it does not broaden strategy or tenant visibility. The options response adds the
authorized strategy's display name for readable context after reload.

No migration is required. Financial arithmetic, missing-versus-zero behavior,
source freshness/publication guards and coupon treatment are unchanged. This work
does not add automatic daily accrual modelling, scheduled-coupon resets, accounting,
bulk upload, bulk correction or independent source certification. A synchronous
maintenance update retains its existing 366-day window. Source input lists still
load that bounded window in one response; very large populations may eventually
need dedicated server-side paging. Detailed reconciliations still require valid
governed pricing context; an obsolete policy may require source remediation rather
than a silent UI fallback.

## Guidance applied

- [Carbon data-table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines),
  updated 30 September 2026: task toolbars, contextual row actions and progressive
  evidence disclosure, applied to compact input/history tables.
- [GOV.UK tabs](https://design-system.service.gov.uk/components/tabs/): separate
  related content for regular users, rather than a forced sequential wizard.
- [GOV.UK error summaries](https://design-system.service.gov.uk/components/error-summary/):
  focus actionable failures and preserve the data entered.
- [NN/g visibility of system status](https://www.nngroup.com/articles/visibility-system-status/),
  3 June 2018: distinguish read loading, confirmed source saves, derived-source
  freshness and unknown write outcomes.
- [MDN native dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog):
  named modals, background isolation and Escape behavior, with explicit draft handling.

The tab names and source/rebuild separation are project-specific design decisions,
not financial standards. They preserve the existing financial service boundaries.

## Verification

Focused frontend checks cover exact inputs, detailed correction preservation,
withdrawal separation, scoped asynchronous responses, unchanged-key uncertainty,
context receipts, accessible rendering, source/table pagination, charts and BFF
query filtering. TypeScript is checked separately. Backend checks use only the
owned disposable-database runner, including the synthetic daily-save → correction
→ closing input → withdrawal → rebuild loop and denied strategy reads.

Read-only browser acceptance uses existing FCPGF data; no operating source was
saved, withdrawn or rebuilt, and no valuation was run or published for this task.

- **56 frontend tests passed** across 11 focused files, including source payloads,
  uncertain/context receipts, loading races, editor/source pagination, the existing
  chart/model/table, BFF filters and page guidance. `tsc --noEmit` passed.
- **25 backend tests passed** in an owned disposable database: history/series API,
  contracts, revisions, freshness, scoped reads and the native synthetic maintenance
  loop. The only warning was the existing FastAPI/Starlette httpx test-client
  deprecation. The full suite was not run for this bounded UI/query change.
- Browser: applied FCPGF 18–20 October window; 22 daily inputs and 22 sourced closing
  inputs; bond-filtered overview narrowed 36 rows to three USD Treasury dates, with
  counts agreeing. Reload retained the strategy/window and its readable name.
- Add dialog preselected the filtered bond. A 13-decimal input was rejected locally
  without creating a request. Unsaved close → Keep editing retained its exact amount;
  the test draft was then discarded. Withdrawal had no replacement-amount field.
- The selected-row chart retained its bond; Escape closed it and returned focus to
  that row's View chart button. The rebuild confirmation named the strategy/window
  and explained the all-bond scope; it was cancelled without submitting.
- At 420px viewport the page/filter form and editor had no horizontal overflow.
  The temporary viewport override was reset. Browser warning/error log was empty.
- Local API restarted after confirming zero RUNNING valuation attempts. Frontend
  dev hot reload serves the new UI on port 3001. No migration or runtime grant change.

## To-date snapshot follow-up

The owner clarified that the main balance overview should show the state on the
selected To date, while the chart provides the dated history. The initial
range-based overview described in the browser evidence above is superseded by
this snapshot behavior. Daily-interest and closing-input registers retain their
range-based maintenance lists; rebuild still uses the requested From/To window.
The existing scoped history endpoint is reused with both date bounds set to To;
there is no client-only filtering of an already paged range, new API, schema change
or change to accrued arithmetic. The full chart keeps its Date column and original
From/To range. Focused regression checks verify these separate date scopes.

Follow-up verification: 40 focused frontend tests across six related files and
TypeScript passed. Read-only browser acceptance showed FCAGF's three bond/currency
balances on 20 October 2026 instead of the former 99 dated rows. The selected
4.375% Gilt chart retained 18 September–20 October and all 33 stored datapoints,
including 10 unassessed dates; its detail table retained the Date column. Browser
warning/error logs were empty. No backend change, migration, source write or
valuation run was needed.
