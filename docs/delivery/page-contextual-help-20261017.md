# Page-specific workflow guidance

**Status:** Implemented; bounded frontend and live read-only acceptance  
**Date:** 2026-10-17  
**Owner:** Frontend engineering with the owning domain maintainer  
**Capability:** [F49 frontend usability](../product/features/platform-quality.md#f49-frontend-acceptance)

## User intent and chosen design

Complex screens need help that explains their purpose, how to operate them, what
the important fields/concepts mean and what actions change in the business flow.
Use a consistent **How to use this page** disclosure near the top of supported
pages, with the current topic named next to it. It is collapsed initially and
opens inline, not as a blocking modal, tooltip or automatic onboarding tour.

The shared widget contains Purpose, How to use it, Key terms and Workflow impact.
It can remain open while the user completes a ticket. Required field hints,
warnings, confirmation controls and validation remain where they were; this
optional explanation does not replace them or hide essential instructions.

## Why this pattern

- [GOV.UK Details](https://design-system.service.gov.uk/components/details/)
  recommends a disclosure for supplementary help and warns against hiding
  information most users need. One related help section does not require another
  tab strip or accordion system. Its guidance also notes that some users may not
  open optional help, so essential content remains on the page.
- [GOV.UK text-input guidance](https://design-system.service.gov.uk/components/text-input/)
  supports visible labels and field hints. The page guide supplements existing
  field-level help rather than turning labels into tooltips.
- [WAI disclosure guidance](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
  informs keyboard show/hide behavior. Native `details`/`summary` supplies the
  disclosure behavior without custom state, redundant roles or a focus trap.
- [WAI modal-dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
  and [MUI Dialog](https://mui.com/material-ui/react-dialog/) describe focus,
  dismissal and interruption requirements for dialogs. A modal is possible but
  less useful here because users need to refer to instructions while working.

Sources opened/read 17 October 2026. MUI online guidance was v9.5 while the app
uses v9.4; no new dialog dependency/API was introduced. Choosing inline help and
these exact section names is a project decision, not a universal requirement or
WCAG conformance claim.

## Implementation and coverage

- [Typed content and route selector](../../apps/ops-console/src/lib/page-guides.ts)
  owns curated, static guidance. Exact routes precede anchored dynamic routes;
  unknown creation paths receive no misleading generic fallback. Own-property
  checks prevent inherited object keys from becoming bogus guides.
- [PageHelp](../../apps/ops-console/src/components/page-help.tsx) renders plain
  React text and semantic lists/definitions. No HTML injection, Markdown runtime,
  remote document request, analytics, local storage or financial request.
- [Workspace shell](../../apps/ops-console/src/components/workspace-shell.tsx)
  places help above page content without changing the existing authority branch.
  If its write-page guard denies the form, it also omits the guide. Context and
  platform tenant screens embed the same component outside the tenant shell.
- [Native presentation](../../apps/ops-console/src/app/native-workspace.css)
  uses the shared visual language, visible summary focus and a two-column reading
  layout that becomes one column on narrow screens. No portal or overlay.

Guides cover these complex workflow families:

| Family | Page-specific explanation |
| --- | --- |
| Context / platform tenants | Selected user vs operator, development-only switching, subscriptions and suspension, licensing separate from module access. |
| Tenant users/groups / effective access | Action-bound strategy scope, ALL/SELECTED, administrator vs operational grants, read-only explanations. |
| Organisations / trade fields | Shared identity vs private settings, independent roles, legacy vs curated/empty lists, definitions vs per-trade values. |
| Strategies / strategy detail | Classification, base currency, signed movements, listing separation, monetary measures and calendars; no FIFO/tax/publication implied. |
| Booking / trade history/detail | Quantity bases, clean/dirty pricing, recognition dates, frozen execution, exact uncertain retry, append-only corrections. |
| Lifecycle | Ops-triggered bond/FX maturity closure, preparation vs posting, rate suggestions and exposure closure separate from payment. |
| Valuation / cash balances | Staged vs published, information cutoff, daily income vs coupon payment, source reassessment and dated company/currency cash stocks. |
| Data policies/sources/calendars/explorer/coverage/snapshots | Rule/default matching, freshness, compatible quantities, source rights/priorities, calendar coverage, price/receipt dates and retained evidence. |
| Instrument catalogue / requests / operations / review | Economic instrument vs listing, proposal vs approval, reference support distinct from booking and valuation readiness. |
| Listing creation / booking conventions / schedules | Parent context, factors, frozen conventions and expected schedules distinct from performed payment/settlement. |
| Type-specific creation | Structured products, swaps, futures/families, bonds, FX forwards, options, funds, ETPs, indices/families and digital assets each have tailored terms. |

Simple tenant-profile/market-data overview pages and retired/redirect-only routes
are not given a generic widget merely to claim every entry point is covered.
Query tabs within a workflow share its guide; this is not a per-field encyclopaedia.

## Preservation and maintenance rules

1. Help has no buttons that save, approve, post, publish, switch context or fetch.
   Opening/closing does not own/unmount the page form or alter retained requests.
2. Static explanations do not grant authority, promise unsupported lifecycle or
   valuation coverage, replace source evidence or override validation. Backend
   authorization remains decisive.
3. Keep essential warnings and required explanations inline even if the guide
   repeats their context. Do not move them into this collapsed panel.
4. The domain change owner updates the relevant guide with the owning capability
   record whenever business behavior/labels change. Review especially approval vs
   submission, daily income vs balance/payment, and reference vs valuation support.
5. New routes get a specific mapping and a route-selection regression. No fuzzy
   route guessing, tenant-private data or fabricated features in the content.
6. Keep guides concise. Longer technical methodology belongs in maintained domain
   documentation; a future user documentation site/search is separate scope.

## Verification and limits

- **957 frontend unit tests across 200 files passed.** This includes guide route
  precedence/unsupported paths and unchanged shell denied-write behavior.
- **21 isolated browser journeys passed.** The help case uses the actual policy
  form and widget: Enter/Space toggle, editable draft retention, zero command
  submissions and 390px reflow. Existing booking, context guard, valuation
  publication, organisation retry and policy preview/evidence cases remain green.
- Optimized production build and TypeScript checks passed. The installed Next
  server/client guide was consulted; no new Next boundary API is needed.
- Mobile help screenshot inspected; the real development app’s structured-product
  guide was opened and read without entering a trade or reference proposal.
- Logs: `logs/page-help-unit.log`, `page-help-browser.log`, `page-help-build.log`.
  Regenerable screenshot: `apps/ops-console/test-results/page-help-mobile.png`.

No migration, operating financial write, permission change, dependency install,
commit or push in this task. Existing development frontend/API remain running.
No claim of screen-reader/voice-control certification, every tenant/permission
combination, every glossary term or all live product subtypes being walked through.
No full Python suite: backend behavior is unchanged.

Existing development logs also contain an Organisations Search-button `disabled`
hydration-attribute warning, both before and after help insertion. This task did
not change that form or suppress hydration warnings. Its isolated component tests
do not establish full live hydration acceptance for that separate page.
