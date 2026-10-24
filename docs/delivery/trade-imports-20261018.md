# Trade imports — implementation ledger

**Status:** Bounded trade-import alpha implemented; locally activated  
**Content type:** Delivery record  
**Owner:** Engineering  
**Last reviewed:** 2026-10-19

Plan: [tenant import workflows](../superpowers/plans/2026-10-17-tenant-import-workflows.md).

## Scope and rulings

- User approved trade imports first on 18 October: implement shared intake plus
  NEW listed equities/ETFs/funds. Other templates, cash imports and bulk
  corrections remain later slices, not supported by a generic cash fallback.
- Current feature checkout retained by the user's earlier preference; unrelated
  pending documentation changes are preserved. No merge/push is authorised.
- Ruling: first release uses bounded synchronous validation/confirmation with
  durable database jobs/receipts, not a separate asynchronous worker. This avoids
  introducing an operational service before the first slice. A lost HTTP response
  is recovered from retained intent; it never permits blind rebooking. Cost:
  larger volumes may require queued execution later.
- Ruling: a single explicitly confirmed group is at most 500 rows and 512 KiB,
  fitting the unchanged existing API body budget including base64. No silent
  chunking or truncation. Limits are declared resource budgets, not instrument
  or financial restrictions. Cost: large deliveries require explicit batches.
- Ruling: exact financial/identifier input cells use text. Excel numeric/date
  cells are rejected with instructions rather than guessing lost precision or
  ambiguous dates. CSV ISO values remain supported. Cost: users must preserve
  template formatting when pasting.
- Ruling: original artifacts are stored privately as bounded database binary
  evidence for this alpha; no filesystem/object-storage service is needed.
  Retention cleanup is deferred and must not be claimed implemented.
- Ruling: shared format/storage primitives stay in `data_imports`; trade-specific
  orchestration lives in `apps/reference_api/import_service.py` beside the adapter
  and existing booking service. A generic processor framework waits for a second
  delivered workflow. Cost: later workflows require extracting orchestration,
  rather than prematurely treating trade commands as generic ingestion.
- Existing source identities remain bound to their original booked trades even
  after cancellation/correction; a repeat file does not reopen a cancelled trade.
  Altering an already booked source ID requires the normal correction workflow.

## Delivered journey

`/imports` is available through Trade imports in the tenant menu. Select a
permitted strategy, download its scoped workbook and fill the Trades table.
Instructions and cell comments describe machine headers, standard properties and
tenant custom fields. Governed choices, eligible parties/traders, currencies,
side/purpose/activity and a single-tag convenience field have native dropdowns;
multi-tag input accepts explicit IDs. Listing UUIDs avoid ambiguous symbol matching.
Template metadata records tenant, strategy, schema and generation timestamp.

Upload retains the original file only. Validate checks every accepted row and
produces a review hash. One invalid row blocks all booking, while valid rows remain
in the retained report. Corrected files are new uploads. Explicit confirmation
rechecks authority, reference definitions, properties, duplicates and the review
hash, then calls the same cash-booking writer used by the normal UI.

All bookings, source-row identities, audit and the final receipt share the request
transaction. A crash or lost response is recovered by retained intent/job state;
the UI retains the exact payload/key and offers unchanged retry, not fresh booking.
Repeats from differently packaged files resolve existing source IDs. Equivalent
decimal formatting is normalised; genuine differing economics are conflicts.
Original files and error CSV downloads use current tenant/strategy rights and
private response headers. Error CSV cells are protected against spreadsheet injection.

## Known limits and remaining work

- NEW listing-backed EQUITY, ETF, FUND and FUND_SHARE_CLASS only. Bonds,
  derivatives, generic ETP variants and import cancellation/replacement templates
  are not delivered. Their ordinary product-specific booking pages remain intact.
- One strategy/source namespace per file, maximum 500 data rows and 512 KiB;
  explicit text financial/identifier cells and ISO text dates. A form cannot
  bypass current required custom fields or curated reference eligibility.
- Source-trade deduplication covers this import workflow and its scoped source
  identities, not probabilistic matching of historical manually entered trades.
- Synchronous validation/application may take longer for large rich batches.
  Durable jobs/receipts support uncertain outcomes; queued execution, automatic
  expiry/cleanup, email/webhooks, saved mapping profiles and other data families
  remain future work. No external virus-scanning service is configured or implied.
- Bulk job artifacts are retained in the database. Capacity/retention operations
  require a later explicit policy; no automatic deletion is enabled.
- Static/component/browser checks use synthetic data. Browser tests exercise the
  real React UI with synthetic HTTP fixtures; disposable API tests independently
  exercise PostgreSQL and the real booking writer. This is not one full-stack
  operating-data browser booking or independent real-strategy reconciliation.
- Final review was sequential author review, not an independent code audit.

## Verification/progress

- Parser/template tests written before module: initial collection failed because
  the feature package did not exist. First implementation: 9 passed, one test
  expectation corrected to retain the actual worksheet row after a styled blank.
- Expanded failure injection proved that a second-row booking failure rolls back
  earlier trades, source identities and the final receipt. Regressions cover
  unknown listings, exact 30/12 amounts, required governed custom fields,
  retirements/revocation, reference changes and changed source-ID conflicts.
- Latest import-specific disposable run: **22 passed** (11 format/template and
  11 booking/integration tests). Additional selected import/ordinary-booking
  regressions: **36 passed**, eight existing SQLAlchemy deprecation warnings;
  selected API-contract/readiness follow-up: **29 passed**. No full Python suite
  run; focused scope follows the user's agreed verification approach.
- Frontend: **965 tests / 202 files passed** with `--maxWorkers=2`; typecheck
  passed. Initial unbounded run had two unrelated 5-second timeouts in market-data
  overview/payment-date BFF tests; both independently passed, then the complete
  bounded run passed. No product code was changed to suppress those timeouts.
- Browser: **2 passed** — bad-row blocking and exact retry after uncertain booking.
  Focused BFF/state/navigation checks: **16 passed**. OpenAPI export/check and
  TypeScript generation completed; semantic comparison found **zero changes to
  existing paths**, eight added import paths, no removed paths.
- Broader metadata check: **27 passed, 1 failed**. The remaining documentation
  assertion identifies **77 pre-existing uncommented columns** across cash,
  organisation, maturity/redemption and corporate-action tables. Every new import
  column is documented. This existing gap was not hidden or treated as a feature
  regression; no unrelated schema changes were added to the approved migration.
- Repository-neutrality checks: **2 passed** after implementation. Unrelated
  earlier documentation changes remain preserved; no commit/merge/push performed.

## Local activation — 19 October 2026

User explicitly approved migration 96 and API restart. Verified the operating
database was at `20261017_95`, applied only `20261018_96` and restarted the scoped
API process. Docker Desktop and the existing `platform-postgres` container were
started after finding them stopped; the preserved volume/database were not recreated.

Read-only live verification: API health **200**, authorised import options returned
**8 strategies**, tenant-specific Excel download **200 / 14,493 bytes**, import
history **0 records**, frontend `/imports` **200**. The app is running at
`http://localhost:3000`. No operating file was uploaded, no trade booked/cancelled,
no permission granted and no valuation run/published during activation.

## UI refinement — 19 October 2026

The download is named `trade-upload-template.xlsx` rather than `cash-trades.xlsx`.
This is a presentation-only rename: supported products and the retained workbook
schema identifier remain unchanged. Existing templates remain accepted.

User approved a bounded presentation redesign: Prepare → Upload → Review & book,
with Import history separate. No API, schema, permissions, financial calculations,
booking command, idempotency key or transaction semantics changed in this follow-up.

- Responsive setup cards separate strategy/template selection from file/source
  entry. “File source” replaces the technical “Source namespace” label without
  changing the submitted value or its deduplication scope. The how-to sits directly
  below the page heading, above both tabs, and remains collapsed by default, with
  exact-file/date/identifier requirements intact.
- Once an upload is selected, review replaces the setup form. New import is an
  explicit action and stays disabled during processing/uncertain outcomes.
- Summary cards distinguish file rows, valid rows, errors, existing bookings and
  actual newly booked trades. Unvalidated counts display an em dash rather than
  claiming zero file rows. Booking stays gated by the existing `canConfirm` check.
- Review puts errors first within the current server-paged result, clearly not a
  client-side full-history filter. Exact financial strings remain unchanged.
  IDs, submitted custom-field keys and review hashes remain inspectable under
  details rather than dominating the table. Instrument links use already-returned
  evidence IDs; no current market price or economic re-resolution is introduced.
- Human status badges, explicit UTC dates and error guidance improve readability.
  Newly opened/changed review outcomes receive heading focus; paging does not
  repeatedly steal focus. Original/error downloads remain available.
- Read-only users retain history inspection without upload/booking affordances.
  Uncertain writes retain the exact request/key and cannot start a fresh upload.
- UI split into `import-console.tsx`, `import-review.tsx`, `import-history.tsx` and
  scoped `imports.module.css`, leaving the mutation transport in the console.

Verification: 19 focused presentation/BFF/navigation tests, four isolated browser
scenarios, TypeScript checking and two repository-neutrality tests passed. Browser
checks cover invalid-row booking blocks, errors-first display, focus, unchanged
retry intent, narrow-screen overflow and read-only history. Synthetic
desktop/mobile screenshots were visually inspected. No operating trades or other
financial data were changed. This UI follow-up does not resolve the earlier,
unrelated schema-column documentation finding.
