# Trade booking property section refresh — 2026-10-01

## Delivery status and agreed UX reservation

Implemented and technically verified as an alpha. On 2026-10-01 the user agreed
that the single-column layout improves readability but lengthens the ticket.
Its density/readability balance remains subject to a realistic-trade walkthrough;
agreement with that reservation is not final UX acceptance or production sign-off.
No additional layout change is authorised or implemented by this documentation
update.

## Delivered scope

The dedicated `/trades/new` ticket keeps its listing-first workflow. This slice
redesigns only tenant-defined property entry and its governed catalogue selector,
with separate tag selection. It does not change parties, execution, payload
validation, database schema, booking permissions or financial idempotency.

- Required properties appear first, followed by optional properties. All controls
  remain visible; no collapsed group can conceal a validation target. Existing
  configuration order is preserved within each group.
- Fields use a single-column reading order, explicit required/optional labels,
  friendly type names, tenant descriptions and format hints. Yes/no controls
  retain the three states unspecified, true and false. Numbers remain strings
  until the existing payload/validation path processes them; no floating-point
  conversion or rounding has been introduced.
- Tags have a separate, labelled checkbox group. Definitions and list curation
  remain in Trade configuration, not inside a financial ticket.
- Scalar errors and help text have separate IDs and described relationships.
  Governed fields now provide a focusable target matching the ticket error-summary
  link, with associated hint/error text and a labelled search input.
- Catalogue selection is visibly separate from search text. A published record
  version ID remains the submitted value; its selected code/label is displayed.
  Searching never silently selects a value. Clear value resets the selection and
  restores search focus; missing display labels no longer expose opaque UUIDs.
- Enter in catalogue search searches without submitting the surrounding booking
  form. Search stays explicit, including empty-query browse. Loading, failure,
  no-match and result states are distinct. Changing search invalidates stale
  responses without clearing the existing selected value.
- Catalogue result pages fetch 26 rows and display 25, using lookahead rather
  than a full last page to guess whether Next exists. Paging controls appear
  only when a previous or next page exists. Entries are not loaded as an
  unbounded HTML select. Selection returns focus to the search control.
- Legacy embedded choices or references missing their catalogue fail visibly
  and ask the operator to reopen the ticket; no fallback free-text input is added.

Tenant-authored descriptions are displayed unchanged, even if their prose is
outdated relative to a field's current requiredness. Current required/optional
labels and validation remain authoritative; operators can correct descriptions
through an immutable definition replacement in configuration.

## Best-practice evidence

Sources searched and opened on 2026-10-01. These are applicable form-design inputs,
not fintech rules or proof of complete accessibility compliance.

| Source | Guidance applied | Applicability |
| --- | --- | --- |
| [W3C WAI grouping controls](https://www.w3.org/WAI/tutorials/forms/grouping/), updated 2026-03-27 | Related controls need visual and semantic grouping with concise labels/legends. | Required and optional property fieldsets, separate tag fieldset, labelled catalogue group. |
| [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/) | Explain requested information and explicitly identify optional inputs. | Descriptive hints and optional labels; its one-question-per-page starting point is not copied wholesale into this expert booking workflow. |
| [GOV.UK error message](https://design-system.service.gov.uk/components/error-message/) | Associate field errors with controls and retain entered values. | Separate hint/error IDs, described-by relationships and retained selections. Search-service failures remain separate from value-validation errors. |
| [GOV.UK text input](https://design-system.service.gov.uk/components/text-input/) | Input presentation, hints and error associations should match the information requested. | Readable, bounded controls, explicit labels and numeric/date format guidance. |

Required-first order, single-column layout, always-visible optional fields,
explicit catalogue search and 25-row paging are project decisions, not universal
requirements. Existing native inputs and buttons are retained; this does not
introduce a custom ARIA combobox or a new design-system dependency. Exact search
matching and active-record enforcement remain the existing tenant-scoped API's
responsibility. Required catalogue selection is validated by the ticket, not by
requiring text in its search box.

## Verification

- Five lightweight rendered tests were added before implementation: four failed
  on the old UI, then all five passed after the redesign. They cover grouping,
  readable boolean/type labels, hint/error associations, focusable governed-field
  targets, selected-label presentation and empty states.
- Full frontend suite: 220 tests in 61 files passed with `--maxWorkers=1`.
  An initial two-worker run passed 219 and hit the existing 5-second dynamic-import
  timeout in a trade-history rendering test. No assertion or timeout was changed.
- Frontend TypeScript check and production build passed.
- Running-app browser review used an existing demo listing, without confirming
  or booking a trade. It checked Enter-to-search, published catalogue results,
  selection/clearing, no-match results and existing required-field validation.
- Backend contracts are unchanged; Python tests were not rerun for this UI slice.

## Remaining alpha checks

Latest follow-up: [browser fixes and density evidence](quality-reviews/2026-10-01-trade-booking-browser-follow-up.md)
records consistent Yes/No review/detail, edited-field revalidation, fresh 235-test
verification, an isolated UI lifecycle regression and a 29-property walkthrough.
It does not settle operator density preferences or claim CI/accessibility sign-off.

Follow-up manual acceptance: [2026-10-01 browser cycle review](quality-reviews/2026-10-01-browser-trade-configuration-cycle.md)
records isolated synthetic bookings, lifecycle/history preservation and peer-tenant
isolation. It also records presentation findings and checks not performed; the
implementation-time verification above is preserved as a dated baseline.

Formal screen-reader/device testing, large-catalogue multi-page browser tests,
and automated asynchronous selector interaction tests remain follow-up work.
Rendered tests do not simulate interaction, and no new end-to-end financial
booking was performed. The broader acceptance workflow remains in
[the trade configuration UI record](trade-configuration-ui-alpha.md#recommended-acceptance-walkthrough-and-next-checks).

### Realistic-trade walkthrough before settling density

User decision, 2026-10-01: frontend/UX and density refinements are deferred until
later. Keep the current layout. The [follow-up priorities](quality-reviews/2026-10-01-trade-booking-browser-follow-up.md#follow-up-priorities-and-user-decision)
record trade correction/cancellation review, then market-data/policy review and
strategy valuation/P&L as proposed functional discussion topics. The walkthrough
below is retained for when UX work resumes; it is not an immediate work order.

Use an isolated environment for any test booking; a production booking must
remain an operator-controlled financial action. Include a sparse ticket, a
typical tenant ticket and a property-heavy ticket using scalar and catalogue
fields. Check:

- Whether required fields are immediately discoverable and field hints are useful.
- How much scrolling is needed to complete properties, reach review and return
  to correct a field; whether that interrupts the execution context.
- Whether optional fields and tags are easy to scan without feeling mandatory.
- Whether catalogue search, selection and clearing are obvious, including a
  larger catalogue, no-match search and keyboard-only use.
- Whether validation links reach the right field without losing entered values.
- Whether the review preserves the intended values, including zero, No, an
  unspecified optional value and the selected catalogue entry.

Record operator feedback, viewport/device and representative field counts before
deciding whether to retain the current layout or introduce compact grouping.
Collapsing optional controls, changing column count or adding a compact mode are
possible later options, not agreed changes. Any refinement must preserve clear
requiredness, error discoverability, selected values and the governed-data rules.

The documentation-only follow-up did not rerun tests; the verification figures
above belong to the completed implementation checks.

Implementation: `apps/ops-console/src/app/trades/new/property-fields.tsx`,
`governed-selector.tsx`, `property-fields.test.tsx` and scoped rules in
`apps/ops-console/src/app/globals.css`.
