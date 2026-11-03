# Selected valuation report tabs

**Approved:** user requested implementation of the researched four-tab proposal
on 26 October. Sequential execution in the current checkout; no financial writes.

## Intent and choice

Keep Input form / Results / History. Within one selected result, use **Breakdown**
(default), **Positions & cash**, **Review**, **Logs**. A single scroll page has
become too dense; separate routes would fragment a single review context. Four
related report panels retain context without a third navigation tier.

- Shared context/status, exact headline totals, actual coverage warnings,
  publication blockers and existing publication confirmation remain outside tabs.
- Breakdown: source contributions/coverage and valuation bridge/scope.
- Positions & cash: existing financial tables and their exact-input inspectors.
  Retain close/reopen, filters, pagination and native details across tab changes.
- Review: existing amendment workflow, source reassessment, corrected-input
  recalculation, Ops explanations and retained review decisions.
- Logs: selected attempt events, readable failure, correlation and technical JSON.
  Failed attempts and History's View logs open Logs, not a financial panel.
- Source inspection activates Positions & cash before focusing the destination.
- Preserve report selection in URL fragments; Back/Forward and direct links work.
  Switching tabs reuses loaded data; it does not reprice or cancel pending writes.
- Keyboard arrows/Home/End and labelled panels; horizontally scroll on narrow
  displays. Financial comparisons remain beside their selected position.
- Denied DISPLAY reveals no amounts, input evidence, instrument/cash names or
  review controls. Do not weaken server actions or immutable evidence.

## Non-goals / trade-offs

No API, schema, calculation, financial-history rewrite, permission grant or new
publication semantics. Mounted panels preserve drafts; this is not a claim that
tabs reduce the existing API payload. No repeated warning banner on complete cash.

## Research checked 26 October

- [GOV.UK tabs](https://design-system.service.gov.uk/components/tabs/): task-related
  sections, persistent URL navigation, clear labels; avoid separating comparisons.
- [Carbon tabs](https://carbondesignsystem.com/components/tabs/usage/): related
  contexts, concise labels; tabs are not workflow progress indicators.
- [W3C APG](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/): keyboard/focus and
  tab/panel semantics; automatic activation only for immediately available panels.
- [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/):
  keep primary tasks visible; secondary technical evidence is disclosed on demand.
  Foundational 2006 guidance, not a new financial-reporting standard.
