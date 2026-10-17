# Frontend visual consistency and density review

**Status:** Implemented; bounded frontend/browser acceptance
**Date:** 2026-10-17  
**Scope:** Operations Console source, shared presentation and page-family inventory

## Intent and preservation constraints

See [delivery and remaining acceptance](../../delivery/quality-reviews/2026-10-17-frontend-visual-consistency.md)
for verified outcomes; this file records the design, not universal UI certification.

The user requests a project-wide style/readability review, a plan for dense pages
and implementation without breaking features. Keep the existing native/MUI visual
language. Do not replace controls, libraries, financial methods, validation, source
evidence, API/BFF transport, permissions, idempotency or operator workflows.
The operating app remains stopped; use isolated browser fixtures for acceptance.

## Reviewed inventory and approach

Initial inventory: 50 page entry points, 146 non-test JSX files and nine CSS files
within 509 TS/TSX/CSS source files. Inventory/structural pattern review covers the
whole application; manual tracing concentrates on shell/provider/styles and page
families, not an exhaustive second line-by-line audit of API/financial helpers.
Native and MUI pages already share an operations-console palette. Consolidate
defaults rather than introduce a third UI kit or sweeping specificity overrides.

### Findings and chosen treatment

1. Colours/typography/control defaults are maintained independently across native
   and MUI. Add a small shared presentation-token owner; use those values in the
   theme/root and native foundations. Leave domain-specific compact tables intact.
2. Native controls outside the currently enumerated panels can remain browser-default.
   Give unstyled native buttons/inputs a zero-specificity fallback that does not
   override existing primary/destructive/compact classes or MUI controls.
3. Shared native table rules right-align many text/status/action cells, overriding
   the new organisation register's lower-specificity styles. Correct that register
   locally, not every numeric table globally. Retain financial column alignment.
4. Pricing policies display version inspection, long editable rules, preview and
   source reference help together. Split into Configuration, Preview and Reference
   tabs, with the saved-version picker and messages always visible. Keep panels
   mounted: switching must not erase draft rules, context, preview or retry identity.
5. Structured-product creation is long because it expresses contractual terms.
   Use in-page navigation and semantic headings for its existing sections. Do not
   collapse required inputs or introduce a step wizard that changes validation.
6. Shared shell has no skip-to-content link. Add one with explicit focus movement;
   retain sidebar ordering, mobile drawer, permission gating and tenant banners.

Existing valuation/report tabs, tenant access, booking property sections and
strategy holdings already separate major tasks; retain their workflows. Further
source-file decomposition is not automatically a UX improvement and is not a
reason to rewrite the large structured-product calculation/editor state here.

## Acceptance

- Native and MUI representative controls share typography/palette/radius without
  overriding product semantics; disabled/focus states remain recognizable.
- At 390px, content/form controls reflow and tables scroll within their container.
- Tabs provide selected state, linked panels and arrow/Home/End navigation; fields
  remain mounted and preview uses only saved versions, as before.
- Outline links move keyboard focus to the corresponding heading. Essential
  alerts, confirmation and financial evidence remain available.
- Existing frontend suite, focused new regressions, real-browser journeys and
  optimized build pass. No operating mutation or restart is needed.
- Record source-family coverage and visual samples separately from full live-page
  acceptance; do not claim WCAG certification or every data-dependent state reviewed.

## Research checked 17 October

Opened [W3C consistent identification](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html),
[reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
[ARIA tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/),
[GOV.UK tabs](https://design-system.service.gov.uk/components/tabs/),
[details](https://design-system.service.gov.uk/components/details/),
[USWDS in-page navigation](https://designsystem.digital.gov/components/in-page-navigation/),
and [MUI theme components](https://mui.com/material-ui/customization/theme-components/).
Apply consistent identification, grouped related tasks, keyboard/focus semantics,
local table scrolling and centralized light theme overrides. These sources do not
mandate our exact palette, tab labels or financial UI. MUI online guidance is v9.5;
the installed v9.4 API/types and existing patterns govern compatibility.
