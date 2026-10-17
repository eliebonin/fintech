# Valuation review workspace

**Status:** Implemented; frontend verification below  
**Content type:** Delivery / UI decision  
**Owner:** Operations console and valuation  
**Last reviewed:** 2026-10-13

## Intent and reference

Current navigation follow-up: [14 October Results/History reports](valuation-results-history-report-20261014.md)
supersedes this delivery's automatic latest-attempt loading and unfiltered history
list. Its original verification below remains dated evidence, not the new report
acceptance record.

Replace the vertically stacked diagnostic page with an operational P&L review
workspace, inspired by the user's
`legacy_frontend/apps/portal-web/src/pages/pnl-attributions` page, instrument summary,
trade drill-down, request history and amendment/publication dialogs. Preserve all
audit, licensing, tenant/strategy scope, immutable results and real-operator
independent-review rules. This delivery changes presentation, not backend economics
or authority. The implementation is sequential in the existing checkout.

## What changed

- Calculation form, with strategy, version-labelled policy, reporting
  currency and valuation dates. Information cutoff is an advanced disclosure;
  the same frozen payload/key is retained for unchanged retries.
- Automatically inspect the latest accessible attempt; run selection/history uses
  recorded attempts and timestamps, not a synthetic batch population. History is
  still paginated at 25 attempts and remains tenant-scoped, not a new strategy/date
  search endpoint. Failed runs retain readable failure explanations and raw logs.
- Server-returned market/gross/net totals, human-readable instrument labels and a
  position table. Position pages show 20 rows from the returned immutable batch;
  this is client-side presentation pagination, not a cap on valuation inputs.
- Optional reference names use the existing permission-checked market-data
  reference search, at most 20 visible subjects per page. Names are current catalogue
  labels, not frozen valuation inputs. Unavailable names fall back to identifiers;
  no fixture fallback or new price query is introduced.
- Desktop position table/inspector, stacked on narrow screens; optional amendment
  sidebar with ALL/PENDING/APPLIED/REJECTED/STALE filters and counts. Hiding the
  sidebar keeps it mounted so a frozen amendment ticket is not silently discarded.
- Price/FX dates and provenance, original ledger links, exact amounts/rounding,
  frozen JSON and valuation bridge remain inspectable in disclosures. Financial
  amounts are formatted from decimal strings with display-only half-even rounding
  to two decimals; original exact amounts remain in titles and evidence. Display
  rounding is not a stored amendment or recalculation; displayed components may
  differ by a penny from displayed totals. Exact stored amounts remain authoritative.
- Component requests retain signed delta, reason/source reference and immutable
  attribution ID. No direct PRICE/FX/ACCRUAL edits or invented per-trade allocation.
  Operations explanations, source-corrected recalculation and independent publication
  remain separate actions with the same endpoints and payloads.

## Audit and security boundary

No backend, BFF allowlist, authentication, group grants, entitlement, independent
review, input hash or publication invariant was weakened. Restricted DISPLAY
evidence suppresses totals, position rows, ledger links, reference-label requests,
amendment and publication controls. Calculation and review permissions remain
separate; published results expose no component mutation form. The server, not a
disabled button or user-selected context, remains authoritative for independent
real-operator review and pending amendment/source revision checks.

No live financial result was submitted, amended or published during UI acceptance.
Read-only browser checks used the existing TTE staged result. The expiring local
testing session was restored through the normal context selector as the same
tenant/user, with no grant changes. No migration or API restart was required.

## Source-backed presentation guidance

Sources reviewed October 13, 2026:

- [GOV.UK table guidance](https://design-system.service.gov.uk/components/table/):
  tables support comparing/scanning rows; use captions and semantic headers, not
  tables to arrange page layout. Applied to the position/component tables.
- [W3C dialog guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/):
  a genuine modal needs contained keyboard focus, closing and focus restoration.
  We deliberately use native disclosures and inline forms for this bounded delivery
  rather than introducing custom modal behavior without that accessibility work.
- Installed Next.js 16.3.4 `use-client` guidance: interactive selection/fetching
  stays inside the existing client boundary, with no browser database access.

This borrows the reference's review hierarchy, not its monetary allocations,
placeholder defaults, rounding choices or UI-only review authority checks.

## Verification and limitations

Follow-up: [multi-position trade fixture](valuation-review-trade-seed-20261013.md)
adds 29 active synthetic trades on eight Paris names, while preserving the original
TTE position and previously staged results. A fresh calculation is required to
review the resulting nine-name population; this is not an amendment or publication
of the old single-position batch.

- Test-first new workspace/formatting coverage, plus reference-label amendment
  regression. Restricted evidence, calculation/review separation, published
  read-only behavior, source reference and ledger evidence remain covered.
- **785 tests passed across 170 frontend files** using
  `pnpm --filter ops-console test --maxWorkers=2 --testTimeout=15000`.
- `pnpm typecheck:ops-console` passed. Initial full runs exceeded their default
  five-second timeout on valuation/trade-history imports; targeted rerun passed
  and the full run passed with the stated resource/timeout settings. No assertions
  or product behavior were loosened to obtain that result.
- Desktop live TTE result, price/FX evidence, amendment-panel toggle/form and
  read-only request filters inspected in the browser. Financial approval/publication
  was not exercised against operating data; prior disposable workflow tests remain
  the financial gate, not this visual inspection.
- Responsive checks at 1440px and 390px: desktop table and inspector have matching
  top coordinates and separate columns; narrow layout stacks, with document width
  equal to scroll width (no page-level horizontal overflow). The temporary viewport
  override was reset. Session recovery required the existing expired-session reset
  and context selector, not altered cookies, grants or API validation.
- Final focused run after aligning visual/DOM reading order: **20 tests passed**;
  type checking passed. Keyboard focus follows document order; layout no longer
  reorders run history only through CSS.
- Native disclosures replace the reference's modal forms and draggable panes.
  No AG Grid Enterprise dependency, reference-provider P&L, trade-level allocation,
  new backend batch search or full accessibility certification is claimed.

Implementation: [console](../../apps/ops-console/src/components/valuation-console.tsx),
[results/inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[requests](../../apps/ops-console/src/features/valuation/review-workspace.tsx),
[formatting](../../apps/ops-console/src/features/valuation/presentation.ts),
[styles](../../apps/ops-console/src/app/valuation-workspace.css),
[new focused tests](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx).

## Three-tab follow-up — 13 October 2026

The workspace now displays one section at a time, in this order:

| Tab | Content | Navigation behavior |
| --- | --- | --- |
| Input form | Calculation fields, advanced information cutoff, unchanged retries, corrected-input reason and optional daily input register | Default for users with calculation permission; no primary form hidden behind a disclosure |
| Results | Selected recorded run, strategy/period/policy version/currency, totals, position inspector, amendments, independent publication and expandable audit/log evidence | Default for read-only users; opening a run or receiving a calculation response selects this tab |
| History | Paginated attempts with strategy, valuation period, policy version, start time, status, refresh and Open run | Open run selects Results and restores focus to its tab; no financial totals added to the history list |

Preparing a corrected-input recalculation selects Input form and preserves the
predecessor link. Editing a new draft does not clear or relabel the recorded result.
Policy/strategy/currency labels are resolved through the current accessible options
using the run's recorded identifiers; they are not new immutable label snapshots.
An unavailable label falls back to its identifier. Results never use draft fields
as their financial context.

Panels remain mounted when hidden, preserving native dates, amendment drafts and
the frozen retry key/payload. Opening another recorded run does not reset the input
draft. Only one panel is displayed or exposed for keyboard traversal; hiding is
not an authorization boundary. Error and pending/working messages remain outside
the tabs. Switching tabs does not cancel a request. Tabs support Left/Right with
wrapping and Home/End, roving focus, `aria-selected`, and labelled tab panels.
Tab selection is local UI state, not a new URL route or persisted preference.

### Additional source-backed decisions

Sources checked on 13 October 2026; the content assignment above is our project
decision, informed by these primary references:

- [GOV.UK tabs guidance](https://design-system.service.gov.uk/components/tabs/)
  supports separating related content for frequent operational use, but cautions
  against tabs when information needs simultaneous comparison. Accordingly, Results
  repeats its recorded calculation context; reviewers need not compare it with an
  editable Input form. History navigation is not presented as a mandatory workflow
  step, and errors remain visible regardless of the selected tab.
- [W3C tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) informs roles,
  panel associations and keyboard behavior. Automatic keyboard activation is local
  and immediate; tab selection does not trigger a new calculation or network load.
- [GOV.UK details guidance](https://design-system.service.gov.uk/components/details/)
  informs secondary disclosures for advanced inputs and technical evidence. Required
  calculation fields, result context, failure summaries and status remain visible in
  their respective panels. Scope & audit details selects Results and opens its log.

### Follow-up verification boundary

- Test-first tab regressions exercise actual console handlers with a persistent
  hook-state driver, not a DOM runtime. Cover panel associations/visibility, keyboard
  navigation, history/calculation navigation, draft/result separation, linked
  recalculation and unchanged retry key/payload after a network error. Existing SSR
  tests retain restricted DISPLAY and separate calculation/review assertions.
- **41 focused frontend tests passed across nine files**, using
  `pnpm --filter ops-console test src/components/valuation-tabs.test.tsx src/components/valuation-console.test.tsx src/features/valuation src/components/valuation-price-evidence.test.tsx src/components/valuation-failure-summary.test.tsx src/lib/daily-valuation-request.test.ts src/app/valuation/page.test.tsx --maxWorkers=2 --testTimeout=15000`.
  The first expanded run hit the existing page-import five-second timeout; the
  stated timeout allowed the unchanged assertions to finish. No test assertions
  or authorization checks were removed. `pnpm typecheck:ops-console` and
  `git diff --check` passed. No Python/database suite was run for this UI-only task.
- Live browser checks used the existing nine-position staged Strat Testing run:
  only one panel visible, arrow-key/Home navigation, native date preservation across
  tabs, and History → Results with focus restored. Scope navigation selected Results
  and opened its audit disclosure; at the active 732px viewport document width and
  scroll width were equal. Expired local testing session was
  restored through the existing context selector as the same tenant/user; no grants
  changed. No calculation, amendment or publication was submitted.
- No backend, API contract, permissions, economics, migration or publication guard
  changed. This bounded check is not financial acceptance or full accessibility
  certification. History still pages 25 recorded attempts; filters/new backend search
  and persistent deep-linked tab/run selection are not part of this delivery.

Tab implementation and regression:
[console](../../apps/ops-console/src/components/valuation-console.tsx),
[tab interactions](../../apps/ops-console/src/components/valuation-tabs.test.tsx).
