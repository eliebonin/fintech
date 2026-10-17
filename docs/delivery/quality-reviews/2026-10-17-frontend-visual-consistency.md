# Frontend visual consistency and density review

**Status:** Implemented; bounded frontend acceptance  
**Date:** 2026-10-17  
**Capability:** [F49 — frontend acceptance](../../product/features/platform-quality.md#f49-frontend-acceptance)

## Outcome

Retained the existing native/MUI operations-console language rather than changing
frameworks. Shared presentation, clearer task separation and long-form orientation
are implemented. No backend, schema, financial computation, authority predicate,
BFF transport or retained mutation protocol was changed by this UI pass.

[Design](../../superpowers/specs/2026-10-17-frontend-visual-consistency.md) and
[execution plan](../../superpowers/plans/2026-10-17-frontend-visual-consistency.md)
record intent and preservation constraints; this record is delivery evidence.

## Review coverage

Initial source inventory covered 50 `page.tsx` entry points, 146 production JSX
modules and nine CSS files within 509 TS/TSX/CSS files. Route/import/pattern review
was project-wide. Manual tracing concentrated on shared styles, shell/providers
and the following families; this was not a line-by-line re-audit of every helper.

| Page family | Assessment / treatment |
| --- | --- |
| Context, platform tenants, tenant profile/access | Keep existing task separation, permission-aware controls and testing banner. Shared presentation/skip link apply where the workspace shell is used. |
| Organisations and trade configuration | Fix organisation text/action alignment, control/focus consistency and excessive grid stretching. Keep separate counterparty/broker eligibility, retained retry and pagination. Existing configuration task navigation stays. |
| Strategies, holdings and movement drill-down | Preserve grouping, dense position rows, numeric alignment, chart and movement evidence. No global financial-table realignment or new data cap. |
| Instrument catalogue, requests, operations, detail/listing and conventions | Keep separate explore/create/review journeys and contextual listing workflow. Shared native fallback styles apply without replacing existing feature variants. |
| Type-specific reference creation | Existing MUI forms keep their terms and validations. Structured-product creation gets semantic section targets and an outline; no wizard or hidden contractual inputs. |
| Booking, trade history/detail and lifecycle | Preserve established product tickets, warnings, correction/cancellation and unknown-outcome recovery. No booking control or economic rule changed. |
| Market-data explorer, coverage, calendars, sources and policy | Keep data/evidence and source-priority workflows. Split the dense policy console into Configuration, Preview and Reference; correct stretched identity inputs. |
| Valuation, cash balances and legacy entry points | Retain existing Input/Results/History separation, explicit staged/publication states, review controls and exact amounts. No new valuation support inferred from restyling. |

## Implemented changes

- `workspace-presentation.ts` owns core palette/control tokens and server-safe
  CSS variables. Root layout supplies them; `workspace-theme.ts` supplies the
  existing MUI theme with aligned action radius/minimum height and a distinct
  compact-action height. Explicit feature `sx` and style variants still win.
- Native button fallback has zero specificity, excludes MUI controls and preserves
  stronger primary/destructive/compact styles. Existing native typography, inputs,
  cards and responsive foundations are reused rather than duplicated.
- Organisation rows use 10px/12px padding and left-aligned descriptive/action
  columns. The selector outranks generic table alignment independently of chunk
  order; horizontal table overflow stays local. `align-content:start` prevents
  short pages stretching rows/controls to fill viewport height.
- Shared tab/list/panel primitives implement linked ARIA IDs, roving focus and
  arrow/Home/End activation. All policy panels stay mounted; draft values and
  preview evidence survive switches. Saved-version picker and command messages
  stay outside the panels. The existing read-only/write boundary is unchanged.
- Policy identity grid items align at the top: explanatory text no longer
  stretches neighbouring inputs vertically. Rule and identity validation remains.
- Structured-product outline links focus actual headings. The events/submission
  link exists only while that existing section is mounted. Terms, essential
  warnings, schedule generation and steward submission remain unchanged.
- Workspace shell adds a focus-visible skip link and focusable content wrapper,
  without nesting another `main` or altering sidebar/module/action checks.

## Verification

- Full frontend unit run: **932 passed across 199 files**.
- Browser suite: **20 passed**, using installed Chrome, isolated Vite/Next test
  servers and synthetic responses. Includes the actual Next stale-context guard,
  booking/retry/valuation publication journeys, organisation commands, real policy
  forms, saved-version preview evidence and actual structured-product navigation.
- TypeScript and optimized Next.js production build passed.
- Desktop (1280px) and mobile (390px) screenshots inspected for policy configuration,
  native/MUI presentation and structured creation. Policy and native/table samples
  assert document reflow; wide financial tables retain local scrolling.
- New failures were reproduced before fixes for task separation, shell target,
  missing structured outline, organisation control styling/stretching and policy
  input stretching. A static streamed-MUI CSS assertion and an exact implicit-label
  select locator were corrected as test-harness mistakes, not product defects.

Logs: `logs/frontend-style-unit.log`, `frontend-style-browser.log`,
`frontend-style-build.log`; ignored screenshots in
`apps/ops-console/test-results/*-mobile.png` and
`pricing-configuration-desktop.png`. These local artefacts are regenerable, not
permanent acceptance attachments. Browser launcher emits a non-failing
`NO_COLOR`/`FORCE_COLOR` environment warning.

Operating services remained stopped; no operating trades, source rights, user
permissions or financial data were changed. No migration was applied. Prior
organisation migration 95 activation remains a separate task.

Subsequent approved activation on 17 October applied migration 95 and verified
live register loading; see the [activation follow-up](../tenant-organisations-20261017.md#approved-local-activation--17-october-follow-up).
The no-migration statement above describes the UI review itself.

## Deliberate trade-offs and remaining acceptance

- Two render families remain. Centralized primitives improve consistency; this
  is not a claim that every feature-specific CSS value has been tokenized.
- Long contractual editors remain long. Navigation is safer than hiding mandatory
  inputs or changing validation in a cosmetic pass. Source-file decomposition
  and product-specific workflow redesign require separate evidence.
- Test fixtures use the real global cascade/theme but do not simulate every live
  tenant, permission combination, record count or economic instrument subtype.
- No exhaustive screenshots of all 50 entry points, assistive-technology audit,
  full chart-interaction acceptance or WCAG conformance certification. Existing
  F49 live walkthrough and screen-reader gaps remain open.
- No backend/full Python suite: no backend behavior was changed in this task.

## Primary guidance and application

- [W3C consistent identification](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html)
  supports predictable repeated controls; it does not mandate this palette.
- [W3C reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
  informs mobile layout and local handling of two-dimensional tables.
- [ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) guides keyboard,
  selection and panel association. [GOV.UK tabs](https://design-system.service.gov.uk/components/tabs/)
  informed related-task grouping, not a sequential booking wizard.
- [GOV.UK details](https://design-system.service.gov.uk/components/details/)
  informed keeping essential warnings/contractual inputs visible rather than
  hiding them simply to shorten a page.
- [USWDS in-page navigation](https://designsystem.digital.gov/components/in-page-navigation/)
  informed orientation on the long contract form.
- [MUI theme components](https://mui.com/material-ui/customization/theme-components/)
  informed bounded defaults/overrides. Online docs were 9.5; installed 9.4 types
  and successful build govern compatibility. Research checked 17 October 2026.

Exact tab names, token values and the choice of pages to change are project
judgments, not requirements imposed by those sources.
