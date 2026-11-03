# Valuation report tabs implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. User
> requested implementation without another approval round. Preserve the dirty
> checkout; no automatic commit, push, operating data changes or service restart.

**Goal:** Split the selected report into four task-focused views, retaining audit
and financial controls and the closable inspector.

**Architecture:** A small controlled report-tab/panel component and URL helpers;
existing ResultWorkspace owns financial selection; ValuationConsole supplies the
unchanged review actions and a separate selected-run log component. Keep panels
mounted, use one active report state, and leave outer workspace tabs intact.

**Tech stack:** Next 16.3.4 / React / TypeScript / Vitest / isolated Playwright.

**Spec:** [Approved design](../specs/2026-10-26-valuation-report-tabs-design.md).

## Global constraints

- No financial calculations or authoritative permissions in presentation code.
- No hidden blockers, weakened DISPLAY checks or duplicate publication pathways.
- Preserve pending request identity, review drafts, filters and inspector state.
- Current feature branch/current checkout; sequential author review per user.
- Focused frontend/browser tests, no full Python run for frontend-only work.

## Review focus

1. Failed/no-result and denied-DISPLAY attempts: no invented financial content.
2. Hidden review drafts and uncertain writes survive report-tab navigation.
3. Source links reveal the panel before focus; close/reopen remains full-width.
4. Direct links, Back/Forward and refresh preserve the selected run/report.
5. New results reset to Breakdown, failures to Logs; refresh preserves context.

## Task 1 — controlled navigation and URL boundary

Files: `features/valuation/report-tabs.tsx`, `report-navigation.ts` and tests.
Interfaces: `ReportView = breakdown | positions | review | logs`;
`ReportTabs`, `ReportPanel`, `readReportLocation`, `writeReportLocation`.

- [x] RED: pure URL parse/format and real-render tab/panel contracts.
- [x] GREEN: short controlled components, roving focus and safe hash navigation.
- [x] Verify focused Vitest tests.

## Task 2 — financial report sections

Files: `result-workspace.tsx`, `review-summary.tsx`, their tests and fixtures.
Consumes ReportView and ReportPanel; ResultWorkspace accepts controlled view,
`onNavigate(view)` and review/log content slots; selection remains request-local.

- [x] RED: visible summary/coverage, hidden financial panels, cross-panel source
  navigation, closed inspector retained on returning, denied disclosure.
- [x] GREEN: move source/bridge to Breakdown; positions/cash to their panel;
  expose actual omission counts globally, detailed lists in Positions & cash.
- [x] Verify component suite; no arithmetic or new data selection.

## Task 3 — selected attempt integration and logs

Files: `valuation-console.tsx`, `run-evidence.tsx`, workspace CSS and tests.
Consumes navigation and financial sections. Existing mutation handlers remain;
failed/no-result branches use explanatory panels and their real operational log.

- [x] RED: history opens Logs; new calculation opens Breakdown; failures open
  Logs; retained retry, read-only access and draft input behavior stay pinned.
- [x] GREEN: remove long-page sidebar toggles; Review is a full panel. Keep one
  publication action and explicit confirmation outside report tabs. Wire hash
  restore without repeating the financial calculation.
- [x] Verify focused tests and TypeScript.

## Task 4 — browser assurance and maintained docs

Files: isolated browser journeys, delivery/capability/register/implementation map.

- [x] Test all four views, source links, inspector widths/focus, draft retention,
  hash/Back/Forward/refresh, failed attempts, DISPLAY denial and read-only review.
- [x] Run valuation UI suite, TypeScript and whitespace checks. Inspect synthetic
  screenshots. Restore normal Next generated imports after acceptance servers.
- [x] Update docs with actual evidence and limitations; separate author review.

## Execution ledger

- Pre-flight: report state/URL is shared by console and financial source links;
  navigation owns identities, ResultWorkspace owns position filters/selection.
- Ruling: preserve mounted review/financial panels rather than new endpoints —
  avoids losing drafts or changing authority; does not reduce API payload size.
- Ruling: no agent dispatch, commit or new worktree — existing user preferences
  and unrelated checkout edits take precedence over generic skill defaults.
- Tasks 1–3 RED→GREEN: controlled tab/URL contracts, financial panels and selected
  history/failure transitions verified. The handler-test runtime previously ran
  only its first mount effect; it now runs all mount effects by hook index.
- Browser first pass: five new/read-only/navigation cases passed; five older
  journeys exposed duplicate status-text locators or a corrected-input action
  now correctly hidden in Review. Also found duplicate sibling React keys;
  publication/result keys are now distinct and console errors are asserted.
- Author review: added RED→GREEN cases for malformed deep-link path segments
  and an asynchronous refresh overwriting a newer report-tab choice. A live ref
  retains the current choice; no financial request or authority is changed.
- Final verification: **102 focused tests passed in 19 files; all 1,017 frontend
  tests passed in 210 files; 10 isolated Edge journeys passed**. Full frontend
  run initially exposed one stale primary-UUID assertion; its fixture now follows
  the existing business-label contract while retaining ownership/lineage checks.
- Final TypeScript and `git diff --check` passed. Synthetic mobile screenshot
  inspected; normal Next imports restored with no tsconfig diff. Existing browser
  colour warnings remain; navigation journey asserts no browser console errors.
- Author review (sequential per user preference), not independent sign-off:
  financial/UI ownership remains distinct; denied DISPLAY hides amounts/names/
  review controls; no tab change or URL navigation calculates or publishes.
  Pending review and actual omission notices remain outside hidden report panels.
- Activation: existing UI **3001 /valuation HTTP 200** and API **8001 /health OK**.
  No migration, backend restart, operating financial write/calculation/publication,
  permission change, commit or push. Frontend changes hot-reload.
