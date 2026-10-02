# Trade configuration UI refresh — 2026-10-01

## Delivery status

Implemented and verified as an alpha on 2026-10-01. This is not a production
readiness sign-off. The legacy embedded-choice cleanup was completed before
this UI refresh; its migration and backend evidence remain in the
[governed configuration record](governed-trade-configuration-alpha.md#migration-and-compatibility).

## Delivered experience

Entry point: Tenant profile → Manage trade configuration, at
`/tenant-profile/trade-configuration`. Permissions, database schema, tenant
boundaries and governed publication rules are unchanged. This is a UI refresh
of [the governed configuration domain](governed-trade-configuration-alpha.md),
not a new configurable-data framework.

- Custom fields is the default section. The register shows labels, stable codes,
  friendly value types, optional/required rules, version and lifecycle status.
  Search covers label/code/definition; type and retired-history filters combine.
  Fields are displayed in pages of 25, with exact filtered totals. The alpha API
  still loads the complete bounded field register; this is client-side paging.
- Add field and Edit definition open a focused editor instead of leaving a
  creation form permanently above the register. Replacements retain their code
  and publish a new immutable version. Retirement sits separately in the editor.
- Dropdown fields show Manage values next to their type. This opens the bound
  catalogue directly, including sources outside the first catalogue page.
  Field drafts remain mounted across section changes; choosing Use for a trade
  field returns to the same draft with its existing label/code/definition intact.
  Drafts are browser-session state, not server-saved drafts; a reload/navigation
  away does not guarantee recovery.
- Reference catalogues use a list/detail pattern with contextual creation,
  entry editing and lifecycle actions. Catalogue/entry paging is server-side;
  fetch 26 rows, display 25 and use the extra row to determine whether Next is
  available. Paging uses the last submitted search, not unsubmitted input text.
- Standard fields use named cards for counterparties, executing brokers and
  traders. Shared eligibility and published tenant-curated policies are clearly
  distinguished. Editing uses candidate/draft lists with identity-based counts
  of additions/removals, reasons and acknowledgement. An empty publication is
  explicitly described as disabling that optional selector. Canonical records
  are referenced, not duplicated. A role cannot be switched mid-edit without
  first publishing or discarding its draft.
- Retirement and catalogue publication use in-page impact confirmations, not
  `window.confirm`/`window.prompt`. Existing record/catalogue actions require a
  persisted reason. Field retirement retains the backend's predefined audited
  reason; the UI does not collect a reason it cannot persist. Cancelling restores
  focus to the initiating control after it has been re-enabled.
- Success notices are shown for writes only, never searches or paging. Errors
  focus a visible summary; native form validation enforces required inputs and
  acknowledgements. Hidden panels remain mounted but are removed from interaction.
  Tabs use labelled panels, selected state, one sequential tab stop, arrow/Home/
  End focus navigation and Enter/Space activation. Manual activation avoids
  initiating delayed audit reads merely by arrowing past a tab.
- Draft-catalogue entries say Awaiting catalogue publication; retired-catalogue
  entries remain history-only even if the record version itself was published.
  Audit identifiers are secondary details, not the primary reading surface.

## Online evidence and project decisions

Sources were opened and reviewed on 2026-10-01. These are design recommendations,
not fintech regulation, a legal requirement or a complete accessibility audit.

| Source | Relevant guidance | Application here |
| --- | --- | --- |
| [IBM Carbon data table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines), page updated 2026-09-30 | Group resource search/filter/actions; distinguish row actions; use pagination and secondary detail. | List-first registers with compact columns, contextual actions and paged catalogue browsing. |
| [Nielsen Norman Group: Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/), 2006-12-03 | Defer secondary controls while making access to them obvious. | Creation/replacement forms open on demand; Manage values is explicit; retirement is separated from routine editing. The age of this foundational guidance is disclosed, not presented as a new study. |
| [GOV.UK: Tabs](https://design-system.service.gov.uk/components/tabs/) | Useful for frequent users switching related, clearly separated tasks; unsuitable when information must be read sequentially or compared across tabs. | Retain four task sections, preserve drafts and avoid claiming that tabs are always preferable to separate pages. |
| [W3C WAI-ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) | Label tab/panel relationships and support keyboard navigation; activation strategy depends on content latency. | Manual activation, persistent hidden panels, selected state and arrow/Home/End focus navigation. |
| [GOV.UK: Error summary](https://design-system.service.gov.uk/components/error-summary/), guidance clarified 2025-02 | Make validation errors visible and keyboard-discoverable. | Focus the summary for API errors and retain inputs. Field-specific API error links and a full GOV.UK validation pattern are not claimed: the current API client exposes a general error message. |

Defaulting to Custom fields, using three standard-role cards, displaying 25 rows,
and using inline confirmation panels are project-specific decisions inferred
from the existing workflow. They should be checked with tenant users, not treated
as universal best practices. No Carbon or GOV.UK component library was added;
the existing application styling and React/Next.js stack are retained.

## Verification

Lightweight model tests were written before implementation, then expanded with
rendered-component and browser checks. Coverage includes compound field filters,
history visibility, paging/clamping, identity-based selection differences,
keyboard navigation, record availability wording, semantic table headers,
tab/panel relationships, read-only history and explicit catalogue actions.

Browser review on the running local app checked search plus retired history,
focused field editing, preservation of an unsaved dropdown draft during catalogue
selection, cancellation of field retirement with focus restoration, and manual
keyboard tab activation. No field, catalogue entry, party policy or trade was
published, retired or otherwise modified during browser verification.

- Full frontend suite: 215 tests passed across 60 files.
- Frontend TypeScript check and production Next.js build: passed.
- Running-app browser checks also confirmed the standard-field cards and live
  paged audit history. No configuration writes were made during these checks.
- Git whitespace/error check: passed (existing line-ending warnings only).
- Python tests were not rerun for this UI-only refresh; backend behaviour and
  contracts were unchanged. The earlier legacy-cleanup checks are recorded in
  the governed configuration delivery notes, not counted as fresh UI testing.

## Remaining alpha boundaries

This does not add approvals, catalogue metadata editing, bulk actions, saved
server-side drafts, schema/type changes, new dataset adapters or credit approval.
Field registers still use the existing bounded all-definitions API. Standard
candidate search remains limited to 100 matches and asks users to refine large
result sets. Unsaved changes survive tabs, not full navigation/reload. Formal
screen-reader, mobile-device and user usability testing remain separate work.

## Recommended acceptance walkthrough and next checks

Use a disposable tenant or isolated test environment for write-based acceptance;
do not change live configuration merely to demonstrate the workflow.

1. Open Tenant profile → Manage trade configuration and inspect the four sections.
2. Create an optional scalar custom field with a clear code, label and definition.
3. Create a draft reference catalogue, add its entries, and publish the catalogue.
4. Create a dropdown field bound to that catalogue. Check that Manage values
   returns directly to the correct catalogue and that field drafts survive tab
   changes and catalogue selection.
5. Open Book trade, verify the fields and selectable values, and book a test
   trade in the isolated environment. Confirm the values in history/detail.
6. Correct a catalogue label or publish a replacement definition, then retire a
   test entry/field. Check that future selection changes while booked historical
   values remain intact. Review the corresponding audit events.

Next priorities, not claimed as delivered by this UI slice:

- Automate browser end-to-end coverage of configuration → booking → history,
  publication/retirement, denied permissions and tenant switching/isolation.
- Test small-screen layouts, horizontal table access, keyboard and screen-reader
  behaviour with real devices/assistive technology.
- Improve protection against losing unsaved edits on full navigation/reload;
  distinguish a navigation warning from genuinely durable server-side drafts.
- Obtain tenant-user acceptance of the complete workflow before adding further
  configuration capabilities.

## Implementation map

- `apps/ops-console/src/app/tenant-profile/trade-configuration/trade-configuration-console.tsx`:
  management workflows and request/draft state.
- `configuration-ui.tsx` in the same directory: reusable tabs, panels, registers,
  status labels, paging and editor controls.
- `configuration-model.ts` and `configuration-model.test.ts` in the same
  directory: filtering, paging, selection differences, keyboard destinations
  and lifecycle wording, with lightweight tests.
- `trade-configuration-console.test.tsx` in the same directory: rendered
  structure, discoverability and read-only history checks.
- `apps/ops-console/src/app/globals.css`: scoped configuration styling.

The browser screenshot captured at delivery is a local review artifact, not a
committed dependency: `C:/Users/forte/Documents/ChatGPT/Tech V2/trade-configuration-ui-20261001.jpg`.
