# Structured-product termsheet ingestion implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Sequential execution is preserved; do not delegate without new authorization. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Proposed execution plan; design approved, implementation not started  
**Content type:** Plan  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-13

**Goal:** Populate every applicable structured-product creation input from a
termsheet, support user corrections, and submit eligible unattended drafts into
the existing checking workflow.

**Architecture:** A Python builder owns schedule and proposal normalization for
both the manual page and ingestion. A provider-neutral extractor produces a strict
economic/evidence contract; tenant-aware resolution, revision storage and readiness
checks control assisted and unattended submission. Existing approval materializes
the instrument; ingestion never calls approval.

**Tech Stack:** Existing FastAPI/Pydantic, Decimal, SQLAlchemy/PostgreSQL, Alembic,
httpx, Next.js/React/TypeScript, Vitest and pytest. PDF text extraction is behind a
bounded adapter; select and lock its dependency during implementation after
checking compatibility, rather than invoking system PDF tools from API requests.

**Spec:** [Approved design](../specs/2026-10-13-structured-product-termsheet-ingestion.md).

## Global constraints

- Initial templates: AUTOCALL, AUTOCALL_CONSOLATION, PHOENIX, ATHENA; scopes:
  SINGLE, BEST_OF, WORST_OF. Keep other manual templates available.
- Ingest all applicable terms, including parties, underlying identifiers,
  currencies, amounts, dates, fixings, payoff terms and schedules.
- Decimal strings at ingestion/form boundaries; explicit units and validated ISO
  dates. Missing values never become demo defaults or economic zero.
- Preserve source text/page evidence, explicit schedules/exceptions and corrections.
- Readiness: READY, NEEDS_REVIEW, UNSUPPORTED. Pending fixings block this slice's
  submission, because the existing materialization contract requires their levels.
- Mode: ASSISTED or UNATTENDED; both submit PENDING. Approval remains separate.
- REFERENCE_PROPOSE gates mutations/submission; REFERENCE_APPROVE gates decisions.
  Tenant/actor/source ownership are trusted server context, not model authority.
- No operating DB migrations/seeds, live provider calls, service restarts, commits
  or publication during verification. Use owned disposable DB tests.
- Preserve unrelated working changes and immutable archives. Update F54 record,
  register/map and scoped AGENTS/KNOWLEDGE/FIX evidence together on delivery.

## Review focus

1. Coupon annualization, notional versus issue denomination and absent issuer
   identifiers must not be silently converted or guessed (Tasks 1, 3, 5).
2. Irregular and separate coupon/autocall streams must survive form hydration and
   regeneration without losing period-specific economics (Tasks 2, 7).
3. Future/missing fixing levels and holiday coverage gaps must stop unattended
   submission while retaining editable extracted terms (Tasks 2, 5, 6).
4. Valid-looking model output can contain document instructions or false reference
   IDs; privileged context and reference resolution stay server-owned (Tasks 3–6).
5. Duplicate/stale submissions and provider failure must not create multiple
   proposals or leave a draft claiming successful creation (Tasks 4, 6, 8).

## File and interface map

Create `structured_product_ingestion/` with focused `contracts.py`, `builder.py`,
`calendars.py`, `resolution.py`, `documents.py`, `extraction.py`, `storage.py`,
`service.py` and `__init__.py`. Core building/extraction types remain testable
without importing the FastAPI application or opening DB connections.

Create `apps/reference_api/structured_product_ingestion_routes.py` for routes and
`apps/ops-console/src/app/instruments/autocalls/new/ingestion.ts` plus
`termsheet-intake.tsx` for hydration/intake presentation. Extend the existing form
and BFF/client patterns rather than introducing a parallel creation page.

New names below are intended interfaces, not claims they already exist.

`contracts.py` also owns `IngestionView` (ID, tenant-authorized display metadata,
mode, processing state, revision, extraction, inputs, issues, readiness and nullable
proposal ID), `DocumentRef` (ID, digest, media type and safe locator), and
`DocumentPage` (1-based page number and plain text). `calendars.py` owns
`CalendarEvidence`. Frontend `ingestion.ts` owns `AutocallFormState`, covering every
existing supported-template form field plus imported schedule/evidence/revision.
Import these types from their owners; do not invent parallel envelopes per task.

### Task 1: Strict economic inputs, extraction evidence and readiness contract

**Files:** Create `structured_product_ingestion/contracts.py`, `__init__.py`;
`tests/test_structured_product_ingestion_contracts.py`;
`tests/fixtures/termsheets/regular_phoenix.txt`, `regular_phoenix.expected.json`.
Modify `apps/reference_api/structured_product_contracts.py` only where needed to
add compatibility-safe strict construction, not blanket changes to legacy defaults.

**Interfaces:** Define `FieldEvidence`, `ExtractedField`, `TermsheetExtraction`,
`StructuredProductFormInputs`, `ScheduleSpecification`, `IngestionIssue`,
`PreviewResult`. `PreviewResult` contains readiness, issues, normalized inputs,
schedule rows and nullable `AutocallDraftRequest` payload. Define
`validate_extraction(data: dict) -> TermsheetExtraction` and
`required_term_issues(inputs: StructuredProductFormInputs) -> list[IngestionIssue]`.
Nested ingestion models forbid extra properties. Preserve schema version
`structured-product-extraction.v1`.

- [ ] Write `test_complete_extraction_covers_all_form_terms`: fixture issuer,
  currency, notional, underlying identifiers/levels, dates and payoff inputs are
  retained, with evidence. Write missing-vs-zero, conflicting alternatives,
  decimal precision, invalid ISO date, unknown nested field and unsupported
  template tests. Distinguish issue amount from denomination; annual coupon lacks
  a period rate until an evidenced conversion is supplied.
- [ ] Run the new focused tests and confirm expected missing-module failure.
- [ ] Implement strict typed contracts with nullable extracted values and explicit
  units/states. Name form aliases consistently with current UI payload fields;
  keep parser identifiers distinct from resolved internal IDs. Retain unsupported
  clauses and pending fixing rules.
- [ ] Run new tests plus existing `tests/test_structured_product_draft.py` and
  inspect the scoped diff; legacy valid requests must retain compatibility.

### Task 2: Common calendar-aware builder and explicit schedules

**Files:** Create `structured_product_ingestion/builder.py`, `calendars.py`;
`tests/test_structured_product_builder.py`;
`tests/fixtures/termsheets/irregular_phoenix.expected.json`,
`holiday_autocall.expected.json`. Read existing frontend `schedule.ts`,
`product-profile.ts`, `draft.ts` and Python graph validation/materialization.

**Interfaces:** `preview_structured_product(inputs: StructuredProductFormInputs,
calendar: CalendarEvidence | None) -> PreviewResult`; `CalendarEvidence` contains
calendar ID/version and dated OPEN/CLOSED/UNKNOWN statuses. Implement
`load_calendar_evidence(connection, tenant_id, calendar_id, start, end) -> CalendarEvidence`
using `market_data.calendar_store` interfaces. `ScheduleSpecification` has separate
coupon/autocall streams, EXPLICIT/RULE_BASED/RULE_WITH_EXCEPTIONS mode, stable period
IDs, rule anchors and evidenced exceptions. Edited rows remain explicit.

- [ ] Write exact expected rows for regular autocall/Phoenix/Athena/consolation,
  independent cadences, step-down barriers and memory/final-payment behavior using
  current fixtures as parity references. Add month-end anchors, short final stub,
  weekday holiday, explicit irregular payment dates, conflicting rule/dates,
  variable period coupons, pending fixings and UNKNOWN calendar coverage tests.
- [ ] Run tests and confirm builder is missing.
- [ ] Implement deterministic Decimal graph generation and reconcile headline
  coupon-program economics against the declared schedule. Never invent a required
  annual-to-period conversion. Generate stable IDs, preserve explicit periods and
  exceptions, and call `validate_autocall_draft` before returning a READY payload.
  Support NONE, FOLLOWING, MODIFIED_FOLLOWING and PRECEDING date conventions;
  unrepresented conventions become issues. Bound generation and report excessive
  periods/coverage explicitly instead of truncating.
- [ ] Where current persistence uses a flat headline coupon for all program
  periods, update `_materialize_structured_product` to consume the normalized
  period economics consistently; add isolated persistence reconciliation tests
  in Task 6. Do not falsely declare a variable schedule representable otherwise.
- [ ] Run builder/legacy draft tests and inspect exact row economics and dates.

### Task 3: Tenant-visible reference resolution and source provenance checks

**Files:** Create `structured_product_ingestion/resolution.py`;
`tests/test_structured_product_ingestion_resolution.py`. Modify
`apps/reference_api/repository.py` with shared source-ownership validation;
extend `tests/test_proposal_retry_integrity.py` or a new isolated provenance suite.

**Interfaces:** `resolve_form_references(connection, tenant_id, extraction:
TermsheetExtraction, selections: dict | None = None) -> tuple[StructuredProductFormInputs,
list[IngestionIssue]]`; `validate_ingestion_source(connection, tenant_id,
source_system_id, source_payload_id) -> None`. Selections are authorized human
choices, not internal IDs trusted from extraction.

- [ ] Write tests for exact currency/calendar codes and effective external
  underlying identifiers; issuer/party identifiers resolve only to eligible
  records. Missing/multiple matches return candidate issues; label-only matches
  cannot authorize unattended submission. Check issuer, guarantor and counterparty
  separately. Add cross-tenant reference/source payload and wrong-system cases.
- [ ] Run focused tests and confirm missing resolver/ownership checks.
- [ ] Implement resolution against existing canonical/mapping tables with tenant
  visibility, active/effective state and non-disclosing errors. Validate matching
  tenant/source provenance before submission and again at approval when source
  evidence participates. Preserve explicit human resolution in correction records.
- [ ] Run isolated affected reference/proposal tests through
  `scripts/run_isolated_python_tests.py`; do not connect directly to platform_secm.

### Task 4: Bounded document intake, extraction adapter and versioned draft storage

**Files:** Create `structured_product_ingestion/documents.py`, `extraction.py`,
`storage.py`; `tests/test_termsheet_documents.py`,
`test_termsheet_extraction.py`, `test_structured_product_ingestion_storage.py`.
Add migration `alembic/versions/20261013_84_structured_product_ingestion.py`
after verifying the then-current Alembic head; add models in
`security_master_schema/models.py`. Update dependency input/lock files only for
the selected PDF adapter.

**Interfaces:** `DocumentStore.put(tenant_id, document_bytes, media_type) -> DocumentRef`
and tenant-scoped `get`; `extract_document_pages(document_bytes, media_type) -> list[DocumentPage]`;
`TermsheetExtractor.extract(pages: list[DocumentPage]) -> TermsheetExtraction`;
`create_ingestion_record(connection, tenant_id, actor_id, document, mode) -> IngestionView`;
`append_ingestion_revision(connection, tenant_id, ingestion_id, expected_revision,
extraction, inputs, issues, actor_id) -> IngestionView`;
`get_ingestion_record(connection, tenant_id, ingestion_id) -> IngestionView`.

- [ ] Write tests for page-labelled text, bounded valid PDF text, malformed and
  scanned/no-text PDFs, safe storage identity, digest and wrong-tenant reads.
  Use initial limits of 512 KiB document bytes, 100 pages and 200,000 extracted
  characters within existing request budgets; return explicit limit errors.
- [ ] Write adapter tests using fake httpx transport: valid output, refusal,
  incomplete/malformed response, timeout/unavailable configuration and document
  instructions that cannot control tenant, actor or approval. Define a configured
  HTTP extraction-service adapter accepting document pages and the published
  extraction schema; credentials/endpoint configuration are server-only. No tools
  are exposed to the model. Test fixture adapter is explicitly test-only.
- [ ] Write disposable-DB tests for immutable document/extraction revisions,
  correction actor, expected-revision conflicts and tenant isolation. No model
  call is made while holding a DB transaction/row lock.
- [ ] Run tests and confirm missing implementation/migration failures.
- [ ] Implement adapters/storage and migration. Store documents through a bounded
  tenant-owned locator, not proposal JSON; retain source digest/version. Store
  pending/failed extraction state honestly and support retry with the same intake
  ID. Implement tenant-authorized deletion before submission without deleting
  retained evidence linked to checking/approved proposals.
- [ ] Run pure adapter tests and disposable migration/storage tests; inspect
  migration upgrade/downgrade and confirm no operating DB activation.

### Task 5: Preview and ingestion orchestration API

**Files:** Create `structured_product_ingestion/service.py`,
`apps/reference_api/structured_product_ingestion_routes.py`;
`tests/test_structured_product_ingestion_api.py`. Modify
`apps/reference_api/main.py`, `config.py` and `.env.example` with nonsecret
configuration placeholders.

**Interfaces:** `preview_ingestion(connection, tenant_id, extraction, selections=None)
-> PreviewResult`; `ingest_termsheet(connection_factory, tenant_id, actor_id,
document, mode, extractor, store) -> IngestionView`;
`update_ingestion(connection, tenant_id, actor_id, ingestion_id, request) -> IngestionView`.
Mount the preview, intake, GET and PATCH routes from the approved specification.
Use existing tenant context, membership/action and problem-details conventions.

- [ ] Write HTTP tests for full instrument hydration, correct readiness/issue
  field paths, missing amount versus optional amount, issuer ambiguity, unrecognized
  economic clauses, unsupported subtype, pending fixings and provider failures.
  Assert preview creates no source/proposal/instrument rows. Add authority,
  cross-tenant and revision-conflict cases.
- [ ] Run tests and confirm routes/service are absent.
- [ ] Implement ingestion state transitions and resolution/builder composition.
  Persist extraction/corrections separately from proposal payload. Handle provider
  work outside DB transactions; commit intake before extraction, then record result
  using revision checks. Missing provider returns a readable unavailable state.
- [ ] Run fake-adapter HTTP tests and isolated persistence tests. Verify document
  errors and issue rendering expose no source text to unauthorized callers.

### Task 6: Idempotent assisted and unattended submission into checking

**Files:** Modify `structured_product_ingestion/service.py`, `storage.py`,
`apps/reference_api/structured_product_ingestion_routes.py` and
`apps/reference_api/repository.py` for normalized period materialization if needed;
create `tests/test_structured_product_ingestion_submission.py`.

**Interfaces:** `submit_ingestion(connection, tenant_id, actor_id, ingestion_id,
expected_revision) -> IngestionView`. Intake orchestration invokes this same
function automatically for UNATTENDED/READY; ASSISTED waits for submit.
Use existing `submit_structured_product_proposal`, source-scoped idempotency and
approval service, not separate instrument inserts.

- [ ] Write isolated tests asserting ASSISTED remains editable, UNATTENDED/READY
  creates exactly one PENDING proposal, blocked drafts create none, and neither
  path calls approval/materialization. Add concurrent replay, stale revision,
  changed references/calendar evidence, and changed payload with reused key.
- [ ] Write approval tests comparing persisted parent/component/schedule/coupon
  economics with the normalized expected graph, including variable coupons and
  full parties/amount/date terms; test rejection creates no instrument.
- [ ] Run tests and confirm missing submission behavior.
- [ ] Implement revision/row locking, readiness/reference/source revalidation
  within submission and atomic proposal/revision linkage. Service actor needs
  normal tenant proposal authority. After submission preserve that revision;
  edits require a new replacement draft rather than changing PENDING evidence.
- [ ] Run isolated proposal/retry/approval suites and inspect retained evidence
  and exactly-once outcomes.

### Task 7: Shared manual preview, termsheet intake and complete editable hydration

**Files:** Modify `apps/ops-console/src/app/instruments/autocalls/new/form.tsx`,
`payload.ts`, `draft.ts`, `page.tsx`, `apps/ops-console/src/lib/reference-api-client.ts`
and BFF client helpers. Create `ingestion.ts`, `termsheet-intake.tsx` and focused
tests in the same form folder. Add BFF routes under
`apps/ops-console/src/app/api/instruments/structured-product-drafts/preview/` and
`structured-product-ingestions/` for collection, ID and submit operations.

**Interfaces:** `hydrateIngestionForm(view: IngestionView) -> AutocallFormState`;
`requestStructuredProductPreview(inputs, context) -> PreviewResult`;
`loadStructuredProductIngestion(id, context) -> IngestionView` and corresponding
intake/update/submit helpers. Obtain types from generated API contracts.

- [ ] Read app AGENTS.md and installed Next.js docs before behavior edits. Write
  hydration/component tests covering every input (parties, underlying selections,
  currency, amount, effective/start/fixing/maturity dates and payoff terms), missing
  values without demo defaults, editable evidence and revision conflicts.
- [ ] Write exact parity tests showing manual and ingested identical inputs use
  the same server preview. Add explicit imported schedule exceptions, preserved
  user edits, regeneration with explicit preserve/replace choice, stale async
  preview responses, unavailable API and mode switching without weakening gates.
- [ ] Run frontend focused tests and confirm absent hydration/preview behavior.
- [ ] Implement complete typed form-state capture/hydration and source evidence
  panel, bounded intake, draft correction/save and submission status/proposal link.
  Replace authoritative generation for supported templates with server preview;
  retain grouping/display helpers and existing manual unsupported-template paths.
  Use server canonical payload for supported-template submission, not
  `numberOrZero` on unknown extraction values. Debounce/cancel stale previews and
  prevent submission when preview revision differs from current edits.
- [ ] Regenerate OpenAPI/client contracts; run focused frontend tests and
  typecheck. Check latest app creation flow against existing manual regression
  tests; preserve other template behavior.

### Task 8: Integrated fixtures, documentation reconciliation and delivery checks

**Files:** Extend `tests/test_structured_product_ingestion_submission.py` and
frontend ingestion tests. Update F54 record/register/map, root KNOWLEDGE/FIX and
app READMEs; create `docs/delivery/structured-product-termsheet-ingestion.md` with
actual verification and activation limits.

**Interfaces:** Consume all previous task interfaces; no new product behavior.

- [ ] Run synthetic termsheet -> fake extractor -> resolver -> shared builder ->
  assisted edit/unattended submission -> PENDING -> approval tests in the disposable
  DB. Expected terms are authored independently, not captured from builder output.
  Cover end-to-end failures and no false successful status after provider timeout.
- [ ] Run focused affected backend suites through the disposable runner, frontend
  tests/typecheck, `pnpm contract:check` and `pnpm contract:generate:check`; broaden
  only for failures/new unresolved risk. Record exact commands/results.
- [ ] Review security/economic boundaries and scoped diff against this plan.
  Mark FIX findings resolved only with regression evidence; update F54 status
  according to actual implemented slice, not provider or real-document assumptions.
- [ ] Check documentation links/anchors/whitespace and preserve prior working
  changes. State live provider activation, actual issuer termsheet accuracy,
  OCR/vision, browser walkthrough and production acceptance as NOT VERIFIED where
  not performed. Deliver source links and remaining activation requirements.

## Execution and review checkpoints

Sequential native execution is preserved. Each task uses failing regression tests,
implementation, focused verification and scoped diff review. No subagents are
authorized by this plan. Stop for new incompatible requirements or a genuine
dependency blocker; otherwise continue through all tasks once the plan is reviewed.
No commits or live activation are implied. Design approval alone is not delivery.
