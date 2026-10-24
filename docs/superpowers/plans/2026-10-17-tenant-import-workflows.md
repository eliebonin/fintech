# Tenant Import Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Preserve the user's sequential execution preference; no delegation is authorised by this document.

**Goal:** Deliver tenant-scoped file imports with guided Excel templates, authoritative domain validation, explicit application and recoverable outcomes, one dataset workflow at a time.

**Architecture:** A small shared intake package owns artifacts, parsing, jobs and receipts; separate adapters invoke existing access-checked domain operations. Start with a PostgreSQL-backed worker and private local artifact storage, not a new distributed platform. No upload grants authority, changes source rights or publishes a valuation.

**Tech Stack:** Existing Python/FastAPI, SQLAlchemy/PostgreSQL/Alembic, Next.js/TypeScript and existing request-context transport. Select a maintained XLSX library through dependency review; do not implement an OOXML parser from scratch.

**Spec:** [F59 scope and controls](../../product/features/tenant-data-imports.md), including the Excel and outcome contract. This plan refines the [initial phased roadmap](2026-10-17-tenant-data-imports.md).

**Status:** PARTIAL — trade-first slice delivered separately; later workflow tasks proposed  
**Content type:** Plan  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-19

**Execution update, 19 October:** User prioritised U01 trade uploads before cash.
The [delivery ledger](../../delivery/trade-imports-20261018.md) records the bounded
first slice and explicit rulings (synchronous commands, private database artifacts,
500 rows/512 KiB). Later workflow sections remain proposed, not implemented by
the shared parser. Domain trade orchestration lives alongside the API adapters,
not in the transport-neutral `data_imports` primitives.

## Global constraints

- Tenant/actor identity comes from authenticated context, not trusted spreadsheet columns.
- Uploading, applying an import, approving a reference proposal and publishing a valuation are distinct actions.
- Initial financial imports should block a batch with validation errors.
- Pagination applies to preview/errors, not to how much of the accepted file is validated.
- Do not hold a database transaction while waiting for upload, user review or remote network operations.
- Preserve exact decimals and explicit currencies/units/orientation; do not silently round, truncate or infer unknown economics as zero.
- Every read, download, retry and mutation rechecks current tenant, strategy, domain and dataset rights. Imports are not a permission bypass.
- No operating-database writes, source-rights grants, migrations, restarts or financial bookings are authorised by writing this plan.
- Keep F59 NOT IMPLEMENTED until a delivered slice has its own verification evidence; list supported templates individually.

## Delivery sequence and boundaries

1. Tasks 1–3 with U02: shared foundation plus cash balances, first CSV then tenant-aware XLSX. Do not build a generic framework before proving this slice.
2. U03 prices/NAV/FX, then U01 product-specific trades, then U04 daily interest.
3. U09 mapping administration, U05 economic events, U06 payment confirmations, U11 reconciliation.
4. U07 instruments/listings, U08 organisations and U10 reference-data subtypes.
5. U12 catalogues and external transports only on demonstrated demand.

Use one job for one workflow and one authorised strategy where applicable, or one source/dataset for observations. This is a release boundary, not a permanent single-strategy limitation: later multi-scope files require separately acknowledged commit groups and correctly scoped receipts. Never split and commit secretly. Initial partial-application mode is absent, not an undocumented best-effort option.

Later workflows below have explicit entry gates when their domain model does not exist. Do not fabricate a writer or promise all twelve families at once. Each gate becomes a focused follow-on plan before that subtype's implementation.

## Review focus

1. A worker crash after commit must not duplicate a booking or report it as unbooked: Task 2 fault injection and U01 replay tests.
2. A tenant/context switch or revoked group membership must prevent stale confirmation and artifact disclosure: Tasks 2–3 authorization tests.
3. Excel copy/paste, edited lookup sheets, long decimals and date-system differences must not change accepted economics: Task 1 format tests.
4. Multiple rows sharing a snapshot/event/revision identity must not both pass against the same old version: U02/U03/U04 dependency tests.
5. A valid row after the first preview page must still be checked, while inaccessible errors must not leak names or financial values: Tasks 1–3 full-file and denial tests.

## Proposed file and interface map

Paths marked new are planned, not existing capabilities. Do not allocate a migration number until execution against the then-current migration head.

| Planned path | Responsibility |
| --- | --- |
| `data_imports/contracts.py` (new) | Typed job/row/issue, validation report, apply receipt and processor protocol; no domain writes |
| `data_imports/formats.py` (new) | Bounded CSV/XLSX decoding, stable machine headers, cell addresses, exact scalar conversion |
| `data_imports/templates.py` (new) | Workbook generation from already-authorised template descriptors; no authority resolution |
| `data_imports/artifacts.py` (new) | Private immutable artifact storage, hashes, safe streamed downloads and cleanup |
| `data_imports/tables.py`, `repository.py` (new) | Job/revision/row-result/commit-intent persistence and row claims |
| `data_imports/service.py`, `worker.py` (new) | Intake, validation and confirmation orchestration, leases, recovery; injected domain adapters |
| `apps/reference_api/import_routes.py`, `import_contracts.py` (new) | Audited HTTP routes, session and domain authority, response limits |
| `apps/reference_api/import_adapters/<workflow>.py` (new per delivered workflow) | Authorised options, typed payload building and existing domain operation integration |
| `apps/ops-console/src/app/imports/page.tsx`, `[jobId]/page.tsx` (new) | Import list/create and persistent job detail |
| `apps/ops-console/src/features/imports/` (new) | Template download, upload, preview, issues, receipt and recovery components |
| `apps/ops-console/src/app/api/imports/[...path]/route.ts` (new) | Existing BFF context-checked transport, private downloads and bounded upload streaming |

Suggested Python protocol, defined once in `contracts.py`:

```python
class ImportProcessor(Protocol):
    def template(self, c, scope: ImportScope) -> TemplateDescriptor: ...
    def validate(self, c, scope: ImportScope, rows: Sequence[ParsedRow]) -> ValidationReport: ...
    def apply(self, c, scope: ImportScope, batch: ValidatedBatch, command: CommitIntent) -> ApplyReceipt: ...
```

`ImportScope` binds server-resolved tenant, initiating actor/real operator, workflow and strategy or dataset. `ParsedRow` retains sheet, physical row, stable source row ID and typed input values. `ValidationReport` contains per-row issues and proposed effects, schema/profile versions, dependency revisions and a canonical review hash. `ValidatedBatch` is loaded by the service from retained validation, never trusted directly from the browser. `CommitIntent` binds job revision, review hash, idempotency key and confirmations. `ApplyReceipt` contains result kind, domain IDs, per-row outcome, counts and committed timestamp. Decimal fields serialize as strings.

The caller owns the transaction. An adapter must reauthorize and revalidate at apply, including any checks currently owned by its HTTP route rather than its lower-level writer. Extract narrowly shared command logic with parity tests where needed; do not invoke internal HTTP endpoints in a loop or replace the writer with direct table insertion.

## Task 1 — Safe formats and tenant-aware templates

**Files:** New `data_imports/contracts.py`, `formats.py`, `templates.py`, `tests/test_import_formats.py`, `tests/test_import_templates.py`; dependency manifest only after library review.

**Interfaces:** Produces the protocol/types above; `parse_artifact(stream, *, format, schema, limits) -> ParsedFile` and `render_template(descriptor: TemplateDescriptor) -> bytes`.

- [ ] Write failing tests `test_csv_xlsx_same_typed_payload`, `test_excel_lookup_edits_not_authority`, `test_preserves_identifiers_and_decimal_strings`, `test_formula_macro_external_link_rejected`, `test_date_epochs_and_ambiguous_date_rejected`, `test_limits_reject_without_truncation`, `test_last_row_validated`. Assert exact values, original cell addresses and no domain writes.
- [ ] Run `python -B -m pytest tests/test_import_formats.py tests/test_import_templates.py -q -p no:cacheprovider`; confirm failures establish missing behaviour, not environment breakage.
- [ ] Implement allowlisted UTF-8 CSV and XLSX. Reject duplicate/unknown machine headers and nonempty unrecognised input sheets. Empty formatted rows are not records; hidden populated rows remain subject to validation. Reject formulas in input cells, macros and external data/link dependencies; generated named-range validation references are allowed, not evaluated input formulas.
- [ ] Generate Instructions, a named Data table and Reference lists; include schema/template ID, generated time and scope binding. Human labels are guidance; immutable field IDs/code headers are authoritative identifiers. Dropdown values use stable codes, optionally `CODE — Label`; never depend on a mutable label alone or promise hidden ID/display-value behaviour from native validation.
- [ ] Generate authorised strategies/accounts/currencies/catalogue choices and supported tenant fields. Reuse field-definition IDs so renaming a label does not remap a column. An uploaded list never creates a choice. Compatible older templates may pass if current rules still hold; revoked values fail explicitly.
- [ ] Format IDs and precision-sensitive financial columns as text, with examples. Do not round-trip through binary float. Numeric Excel input is accepted only through a tested lexical conversion policy within declared precision; display its normalised value before confirmation. Never claim recovery of digits already lost by Excel. Use unambiguous ISO text dates/timestamps; decode genuine Excel dates with workbook epoch, rejecting ambiguous locale text.
- [ ] Propose initial limits of 10 MiB upload, 50 MiB uncompressed XLSX content, 10,000 populated data rows, 200 input columns and 1,000 ZIP members. Enforce request, parser and worker limits consistently. These are tunable product defaults, not financial eligibility rules. Commit groups remain smaller (Task 2).
- [ ] Run focused tests to PASS; review dependency/security configuration and update contract documentation. Commit only this tested task when implementation is authorised.

## Task 2 — Durable jobs, atomic application and recovery

**Files:** New `data_imports/artifacts.py`, `tables.py`, `repository.py`, `service.py`, `worker.py`, `apps/reference_api/import_routes.py`, `import_contracts.py`, appropriate additive Alembic revision; modify router registration in `apps/reference_api/main.py`. New `tests/test_import_jobs.py`, `test_import_api.py`, `test_import_recovery.py`.

**Interfaces:** `submit_import(c, scope, artifact, request_key) -> JobReceipt`; `validate_import(c, scope, job_id) -> ValidationReport`; `confirm_import(c, scope, job_id, expected_revision, review_hash, key) -> JobReceipt`. Inject the processor registry; only delivered workflows can be selected.

- [ ] Write failing tests for private artifact/read/receipt scope, same-key replay, conflicting-key rejection, full rollback on row failure, concurrent confirmation, permission revocation, stale preview, worker lease takeover and crash before/after domain commit.
- [ ] Run through the owned disposable runner: `./.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_import_jobs.py tests/test_import_api.py tests/test_import_recovery.py -q -p no:cacheprovider`; confirm relevant failures before implementing.
- [ ] Add durable artifact, job, validation revision, per-row result and commit-intent records. Store typed financial facts in domain tables; job data is staging/evidence, not a parallel ledger. Use private server-generated storage keys, a streaming digest and immutable byte binding; reject path manipulation. Clean orphan temporary artifacts after failures without deleting financial receipts.
- [ ] Use states RECEIVED, VALIDATING, NEEDS_CORRECTION, READY, APPLY_QUEUED, APPLYING, APPLIED, APPLY_FAILED, CANCELLED. Distinguish worker lease expiry from a confirmed failed mutation. Retain attempt evidence and original files; corrected files create linked revisions/jobs, never replace booked evidence.
- [ ] Validate every accepted row and intra-file dependencies before READY. Persist a frozen review hash. Any error blocks confirmation; warnings require the template's explicit acknowledgement, never an authority override.
- [ ] Implement tenant-audited routes under proposed `/v1/imports`: templates, upload/create, list/detail, paginated rows/issues, validate, confirm, receipt and authorised artifact/report download. `202` acknowledges queued processing only. Input validation/request authority runs before enqueue; domain state is checked again by the worker.
- [ ] Run one bounded PostgreSQL-claimed worker initially; configurable lease, attempts and backoff. Reconstruct current authority for the initiating actor/operator, never use a service identity to bypass them. Capture acceptance provenance plus transaction-local command audit.
- [ ] Apply at most 500 rows per explicitly confirmed atomic group initially, or a lower existing domain limit. For larger valid files, present groups before confirmation; no hidden chunks or misleading file-wide atomicity. Linked packages cannot cross groups. Hold no transaction during user review; lock/recheck affected revisions in deterministic order at commit.
- [ ] Persist domain effects, row-to-record links, audit and final receipt in the same transaction. If one fails, roll back the entire group. Existing writers must use the supplied connection without independent commit. On uncertain completion reconcile the durable intent/receipt before retry; never infer failure from a lost response.
- [ ] Deduplicate by scoped delivery identity AND source row ID/payload fingerprint, not file hash alone. Identical rows from differently packaged files resolve to an existing receipt; changed payload for a booked source ID requires explicit correction. No heuristic deduplication of two genuinely distinct identical executions.
- [ ] Original artifact retention defaults to 90 days for the local pilot; show expiry and allow configuration before tenant rollout. Preserve financial receipts/source IDs and required domain evidence under domain retention, not the artifact cleanup timer. Receipt and error exports remain access checked.
- [ ] Pass focused fault-injection tests; exercise empty/missing/zero separately; document migrations and worker operations before activation. Commit only tested changes when authorised.

## Task 3 — Imports workspace and notifications

**Files:** Planned frontend/BFF files in the map; new `apps/ops-console/src/features/imports/import-status.test.ts`, `import-review.test.tsx`, and isolated browser journey under the existing browser test configuration. Backend tests extend `tests/test_import_api.py`.

**Interfaces:** Uses Task 2 HTTP contract and the existing `browserFetch` write-context transport. No client-generated authoritative tenant/actor fields. List filters/counts/pagination are server-side and scope-filtered.

- [ ] Write failing component/API tests for every state, scoped list counts, row/cell issues, lost mutation response and preserved request/key. Add browser scenarios for tenant switch, keyboard navigation, screen-reader status, upload errors, page refresh and closed-tab recovery.
- [ ] Build Imports navigation with New import, History and job detail. Require workflow and permitted strategy/dataset selection before downloading templates. Provide a concise how-to panel explaining effect, approval and failure semantics.
- [ ] Show `10 checked · 9 valid · 1 error · 0 applied` and an error table with sheet, physical row, field, human explanation and remedy. Retain machine code/correlation ID behind details. Download an annotated XLSX/error CSV with spreadsheet-injection protection; never mutate the original evidence to make it safe for display.
- [ ] READY offers a domain-specific action: Book trades, Save cash balances, Store observations or Submit proposals. Require explicit acknowledgement of revision/correction effects. Proposed instruction lists never imply permission to approve or publish.
- [ ] After commit show durable counts and record links. Distinguish Booked from Already booked (replay), Stored from Valuation eligible, and Submitted from Approved. A response accepted for processing is not success. If outcome is unknown, show recovery/status checking, not a fresh-booking button.
- [ ] Use persistent in-app job history plus a completion indicator to the initiator; refresh state by bounded polling with backoff, pause while hidden. Permission changes govern every refresh/download. Announce meaningful status changes accessibly, not each polling response. Email/webhooks are deferred; do not build a general notification platform for this slice.
- [ ] Run focused UI tests, typecheck/contracts and the isolated browser journey. Do not run operating-data acceptance or the whole backend suite for a UI-only task. Record evidence separately and commit when authorised.

## Per-workflow implementation tasks

For each workflow below: add the named failing tests first, run them to confirm the expected failure, implement the adapter/commands/UI descriptor, rerun to PASS, then commit the tested slice. New `tests/test_import_<name>.py` files use the owned disposable runner; pure template tests run offline. Every adapter adds one isolated browser happy/error/retry journey. Task-specific tests supplement, not replace, Tasks 1–3.

### U02 — Cash balances (pilot)

**Files:** New `apps/reference_api/import_adapters/cash_balances.py`, `tests/test_import_cash_balances.py`; reuse `valuation/cash_snapshots.py`, `apps/reference_api/cash_snapshot_contracts.py` and route-level authority in `cash_snapshot_routes.py`.

**Interface:** Implements `ImportProcessor`; builds existing `CashUpload` and calls `cash_snapshots.upload(c, tenant, actor, payload, key)` inside the commit transaction.

- [ ] Template: source row ID, account code/ID, value date, currency, amount, source reference, optional note; corrections explicitly name expected revision and reason. Strategy is selected in the job. Company is resolved from the selected account, not inferred from a free-text name.
- [ ] Validate account belongs to strategy/company, active currency, exact date, current expected revision, duplicate account/currency/date in file and current writer's historical/future-date rules. Offer Add account separately; no implicit company/account creation while importing balances.
- [ ] Save exact-date snapshots; missing rows do not delete balances, zero is a supplied zero, absent dates do not carry forward. Display append versus revision and current/new amounts before confirmation.
- [ ] Tests: `test_ten_rows_one_error_writes_zero`, `test_zero_absent_and_duplicate_keys`, `test_stale_revision_rolls_back`, `test_same_file_replay_and_changed_file_source_row`, `test_no_trades_cashflows_or_valuation_created`. Verify 9 valid rows remain staged, not booked. Compare all saved decimals to source totals per currency without combining currencies.

### U03 — Prices, NAVs and FX observations

**Files:** New `apps/reference_api/import_adapters/observations.py`, `market_data/tenant_observations.py`, `tests/test_import_observations.py`; reuse `market_data/rights.py`, `storage.py`, `contracts.py`, `closing_prices.py` and current source/dataset controls. Inspect existing constraints before extracting any shared publisher.

**Interface:** Processor calls proposed `store_tenant_observations(c, scope, points, receipt_context) -> ObservationReceipt`, owned by `market_data`, not generic intake.

- [ ] Separate template descriptors for instrument prices/NAV and FX. Include row ID, reference ID/mapping namespace, market date, exact value, currency or FX pair orientation, observation field/basis, actual fixing/publication time where required, and source reference. Dataset/source are selected and governed outside the sheet. Do not require users to invent an observation timestamp for date-only EoD data: use an explicit supported date-only convention.
- [ ] Validate source ownership, acquisition/storage and intended-use rights, reference visibility, dimensions, dates, duplicates and conflicting revisions. Missing valuation rights is an actionable eligibility finding; upload cannot grant them. Historical market date never becomes historical receipt time.
- [ ] Do not blindly reuse `ingest_delivery`: it is a provider daily PRICE path with strictly positive values and parser-specific assumptions. Explicitly support authorised negative/zero marks where their instrument/field contract allows; FX stays positive. Reject unsupported dimensions without relabelling them RAW, official or UK fixing.
- [ ] Retain original values and basis/provenance. Apply governed corrections through the observation owner's version model, not destructive upserts. Report Stored and Valuation eligible separately, explaining missing rights/policy/calendar/basis proof; never silently choose source priority or activate a policy.
- [ ] Tests: `test_fx_orientation_and_exact_values`, `test_tenant_source_and_rights_denial`, `test_stale_observation_revision`, `test_negative_contract_mark_not_equity_shortcut`, `test_adjusted_not_relabelled_raw`, `test_historical_date_retains_receipt_time`. Reconcile stored rows to the preview and verify source-change reassessment coverage before claiming it.

### U01 — Trade bookings and explicit corrections

**Files:** New `apps/reference_api/import_adapters/trades.py`, `tests/test_import_trades.py`; integrate existing cash/product booking entry points, `product_booking_routes.py`, `trade_corrections.py`, `trade_properties.py` and shared booking controls. Resolve the current canonical cash-booking service during the slice; preserve route-level historical/readiness checks.

**Interface:** One descriptor per supported product; maps rows to the existing typed booking request and exact service command. No arbitrary instrument-type fallback and no direct trade insert by the importer.

- [ ] Start plain cash equities/ETFs/funds; list this release subset explicitly. Extend bonds, futures, FX forwards, options, swaps and structured products only through their existing product-specific conventions and acceptance fixtures. Shared parsing must not force contract/notional/nominal into share units.
- [ ] Include source trade ID, subject/listing identifier with namespace where needed, execution timestamp/timezone, settlement date, side/quantity/price/currency and supported generic fields including effective valuation date. Expand tenant custom typed/choice fields from current definitions and governed option codes. Do not infer venue from ticker alone.
- [ ] Validate current actor/strategy booking authority, product readiness, historical reference definitions, terms versions, quantity/quote conventions, tenant property eligibility and all intra-file dependencies. Full precision review precedes confirmation; frozen BOOKED evidence must match ordinary UI booking.
- [ ] NEW, CANCEL and REPLACE are separate operations/templates. Corrections name original trade and expected lifecycle sequence with reason; financial changes follow existing ledger reassessment. No spreadsheet overwrite or deletion; no generic partial application of a correction chain.
- [ ] Tests: `test_ten_rows_one_error_books_zero`, `test_ui_and_import_frozen_evidence_parity`, `test_historical_and_custom_choice_validation`, `test_two_distinct_identical_executions_allowed`, `test_repackaged_delivery_not_duplicate`, `test_crash_after_commit_replays_receipt`, `test_correction_chain_atomic_and_reassessment_retained`. Verify actual open positions against hand-calculated signed quantities, not just HTTP success.

### U04 — Daily earned bond interest

**Files:** New `apps/reference_api/import_adapters/daily_interest.py`, `tests/test_import_daily_interest.py`; reuse `valuation/accruals.py`, `apps/reference_api/valuation_input_contracts.py`, `valuation_input_routes.py`.

**Interface:** Builds the existing assessed input payload and invokes `record_accrual`; retains all route-owned strategy/valuation/FX authority checks.

- [ ] Required: source row ID, value date, canonical bond, daily earned amount and its currency. Strategy selected on the job. Optional nominal, source/eligibility note and accrued-balance bridge use a separate advanced descriptor; no proportional allocation across trades.
- [ ] Validate uniqueness per supported strategy/bond/date/input type, superseded input ID for corrections and source/currency evidence. Advanced opening + daily + movements = closing bridge must reconcile exactly; preserve current FX evidence requirements. Missing balances are absent, not zero.
- [ ] Save typed daily-interest amount/currency and existing retained revisions. Do not calculate daily earnings as a naive accrued-stock change, generate coupons or write cash snapshots.
- [ ] Tests: `test_daily_amount_currency_and_revision`, `test_duplicate_bond_day_rejected`, `test_coupon_stock_drop_not_negative_earnings`, `test_optional_balance_missing_not_zero`, `test_advanced_fx_bridge_matches_existing_writer`. Verify daily valuation receives the earned flow once; no valuation publication on upload.

### U09 — External identifier mappings

**Files:** New `apps/reference_api/import_adapters/identifier_mappings.py`, `tests/test_import_identifier_mappings.py`; inspect `tests/test_reference_mapping_workflow.py`, `tests/test_external_mapping_rules.py` and existing mapping services before choosing the narrow command owner.

- [ ] Descriptor: source row ID, supported namespace/profile, external identifier, target reference ID, valid-from/to and explicit revision/action. Separate this from arbitrary user-defined column mappings.
- [ ] Match in tenant/source namespace with historical validity and canonical/listing distinction. Block collisions, ambiguous matches, overlaps and private-parent disclosure. No automatic instrument/entity creation; unresolved references link to onboarding.
- [ ] Preview add/revise/retire effects; apply via existing mapping review where required. Already staged imports do not silently acquire newly changed identifier meanings: revalidate their review hash.
- [ ] Tests: `test_same_symbol_different_namespaces`, `test_overlapping_mapping_blocked`, `test_private_target_hidden`, `test_mapping_change_invalidates_preview`, `test_retirement_preserves_history`.

### U05 — Economic income/cost events

**Files:** New `apps/reference_api/import_adapters/economic_flows.py`, `tests/test_import_economic_flows.py`; reuse `valuation/flows.py` and `valuation_input_routes.py`.

- [ ] Descriptor: source event ID, canonical instrument, economic date, signed amount/currency, supported component, recognition role, source reference and optional payment date. Require an explicit meaning for signs, not an automatic BUY/SELL conversion.
- [ ] Apply through `book_flow`, including trading authority and current component restrictions. Coupon receipts remain PAYMENT_ONLY; daily bond earnings use U04. Reset entries retain their classification; this importer must not fabricate mark/reset reconciliation proof or claim a complete reset lifecycle.
- [ ] Corrections use supported cancel/replace operations, with linked source identity and reassessment, not direct event edits. Preview Income versus Payment only prominently.
- [ ] Tests: `test_dividend_income_vs_payment_only`, `test_coupon_income_rejected`, `test_reset_no_automatic_cash_snapshot`, `test_cancel_replace_no_double_recognition`, `test_missing_economic_date_blocks_batch`.

### U06 — Actual coupon-payment confirmations

**Files:** New `apps/reference_api/import_adapters/coupon_payments.py`, `tests/test_import_coupon_payments.py`; reuse `lifecycle/coupon_service.py` and `apps/reference_api/coupon_routes.py`.

- [ ] Descriptor: external payment ID, instrument/schedule period ID, actual payment date, supported received amount/currency, source evidence/reference and notes using current `PaymentCreate` semantics. Distinguish expected coupon date from confirmed payment date.
- [ ] Preserve schedule/strategy eligibility and current partial/overpayment/correction checks; do not infer full settlement from a nonzero receipt. Apply with `record_payment`, and supported correction/reversal commands separately.
- [ ] No trades, cash balances, daily earnings or automatic P&L arise from confirmation. Receipts link to the payment history and label Confirmed, not income booked.
- [ ] Tests: `test_confirmation_is_financially_inert`, `test_wrong_strategy_period_rejected`, `test_partial_confirmation_preserves_remaining`, `test_reversal_retains_history`, `test_repeat_payment_id_not_duplicate`. Reuse existing coupon financial-inertness fixtures.

### U11 — Reconciliation statements

**Files:** Planned `apps/reference_api/import_adapters/reconciliation.py`, `tests/test_import_reconciliation.py`; a separate benchmark storage/compare module and its migration require the entry gate below.

- [ ] Entry gate: define a retained external-statement schema with strategy, provider/account, statement date/cut, currency/unit, snapshot ID and line identity. Define whether the first subtype is holdings (recommended), NAV or P&L; implement holdings first rather than a universal report parser.
- [ ] Descriptor carries statement coverage and position rows. Match canonical/listing identity explicitly; specify aggregate versus account scope. Unknown references remain breaks, not new positions. Absence is zero only for explicitly complete statements within declared coverage.
- [ ] Store benchmarks, then compare to a frozen internal position projection on matching scope/date/units. Expose missing/extra rows and quantity differences. Later NAV/P&L comparisons require explicit measure definitions and per-currency tolerances; no blanket tolerance across different units.
- [ ] Never turn holdings into synthetic trades, change strategy NAV or overwrite a published valuation. Label Statement stored / Comparison completed, not Booked or Published.
- [ ] Tests: `test_partial_statement_absence_not_zero`, `test_listing_account_scope_comparison`, `test_statement_revision_preserved`, `test_reconciliation_writes_no_trades`, `test_nav_pnl_subtype_unavailable_until_defined`.

### U07 — Instrument and listing proposals

**Files:** Planned `apps/reference_api/import_adapters/reference_proposals.py`, `tests/test_import_reference_proposals.py`; reuse existing product onboarding/proposal commands including `product_booking.submit_proposal` where applicable, not one universal instrument serializer.

- [ ] Separate descriptors for canonical type and listings. List required terms/dependencies for each delivered type; issuer/underlying and parent references must resolve before submission. Listings do not become instruments and instrument creation does not imply listing readiness.
- [ ] Bulk application creates proposals only, preserving REFERENCE_PROPOSE and tenant visibility. Existing approval/materialisation retains its own authority and revalidation. Dependency groups must not partly submit when their prerequisite fails; explicit existing-parent reference or reviewed group ordering is required.
- [ ] Label Submitted for review and link every request; pending approvals remain in the existing queue. A duplicate candidate needs an explicit resolution, not automatic identity merge. Keep the shared/private stewardship redesign paused.
- [ ] Tests: `test_listing_parent_dependency`, `test_terms_required_per_type`, `test_submit_not_approve`, `test_tenant_visibility_and_duplicate_identity`, `test_dependency_group_atomic`.

### U08 — Organisations and tenant role lists

**Files:** Planned `apps/reference_api/import_adapters/organisations.py`, `tests/test_import_organisations.py`; reuse `apps/reference_api/tenant_organisations.py` and current organisation routes.

- [ ] First descriptor selects existing canonical organisations by UUID/LEI, supported role (counterparty/issuer etc.), tenant label and allowed metadata. Match exact canonical IDs; names alone only suggest candidates. Multiple plausible matches block application.
- [ ] Apply tenant profile/list changes through `save_organisation` and the established independent role activation path. Validate current role eligibility; selecting an issuer is not credit/KYC approval. Proposed new canonical entities stay unresolved until their distinct onboarding policy is agreed.
- [ ] Template fields must match existing command semantics; do not expose blanket organisation updates or import a tenant's local labels into shared legal identity.
- [ ] Tests: `test_lei_match_not_name_merge`, `test_tenant_label_does_not_edit_shared_identity`, `test_role_selection_not_activation_bypass`, `test_ambiguous_entity_unresolved`, `test_cross_tenant_profile_hidden`.

### U10 — Market reference facts and schedules

**Files:** Planned `apps/reference_api/import_adapters/reference_data.py`, `tests/test_import_reference_data.py`; inspect `market_data/corporate_actions.py`, `calendar_store.py`, `reference_calendar_import.py`, `apps/reference_api/calendar_service.py`, and `lifecycle/coupon_service.py` per selected subtype.

- [ ] Entry gate: select ONE subtype with a supported model/writer. Recommended first coupon schedules; corporate actions and exchange/fund calendar dates follow as distinct descriptors, each with separate permission/review contracts. No catch-all JSON fact uploader.
- [ ] Schedule descriptor includes stable period identity, dates, contractual terms and evidence; an expected amount is not an earned or paid amount. Calendar descriptor identifies calendar/version/session/closure/override meaning and source. Corporate-action descriptor identifies event/source/revision, effective date and exact ratio/terms.
- [ ] Retain proposed revisions and sources, then use existing schedule approval/calendar sealing/action review semantics. Never edit a sealed version, infer fund holidays from one exchange, or automatically declare stock-split history complete.
- [ ] Tests: `test_schedule_import_not_payment`, `test_sealed_calendar_unchanged`, `test_action_ratio_and_revision_evidence`, `test_duplicate_event_not_double_replay`, `test_reference_revision_preserves_old_valuation_evidence`. Model any unsupported subtype before registering it.

### U12 — Governed tenant catalogues

**Files:** Planned `apps/reference_api/import_adapters/catalogues.py`, `tests/test_import_catalogues.py`; reuse `apps/reference_api/governed_trade_configuration.py` and existing configuration routes.

- [ ] Deliver only after demonstrated need. Descriptor: catalogue and stable entry code/ID, label, supported typed metadata, explicit ADD/REVISE/RETIRE and expected revision. Field-definition creation is a separate contract, not inferred from arbitrary spreadsheet columns.
- [ ] Use existing list approval/activation where applicable. Preserve historical definition/choice IDs and meaning; retirement prevents new selection but does not rewrite historical booked values. Reject code reassignment to a different concept.
- [ ] No users, memberships, permissions, modules, strategy grants, source licences or pricing-policy activation through this template.
- [ ] Tests: `test_retired_choice_preserves_history`, `test_code_repurpose_rejected`, `test_revision_conflict`, `test_activation_not_bypassed`, `test_authority_columns_rejected`.

## Release evidence and operational handoff

- [ ] Complete offline parser/template tests first; then adapter parity tests against existing writers in owned disposable databases. Full suites are reserved for a cross-cutting release boundary, not rerun for every descriptor edit.
- [ ] Record the 10-row/one-error scenario, corrected retry, same-source repackaged retry, stale preview, revocation and fault recovery in the isolated browser app. Validate count/amount/quantity totals and resulting domain evidence, not just HTTP success.
- [ ] Before operating activation, get approval for the specific migration/restart and separately for any mock financial bookings. Test fixtures never grant real provider rights.
- [ ] Update F59, F35 where relevant, implementation map and a delivery record with supported formats/workflows/products, deliberate limits, focused test results, local activation and financial acceptance separately. Keep unshipped workflows NOT IMPLEMENTED.
- [ ] Document worker start/stop, lease recovery, retention cleanup, safe revalidation, atomic group boundaries and support lookup by job/correlation ID. Imports do not replace domain operational dashboards.

## Research and project choices

Checked 17 October 2026. These sources support controls, not our rollout order, numerical limits or all-or-nothing product default.

- [Microsoft Excel validation](https://support.microsoft.com/en-gb/excel/more-on-data-validation?nochrome=true): copied/filled cells can bypass validation messages. Tenant lists help entry; server membership and authority checks remain mandatory.
- [Microsoft numeric text guidance](https://support.microsoft.com/en-us/excel/format-numbers-as-text): Excel numeric cells have a 15-digit precision limit. Text-formatted identifiers and exact-value input columns avoid claiming preservation of digits Excel has already discarded.
- [OWASP input validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html): validate syntax and business meaning, including dropdown membership; authorization is separate from identifier validity.
- [OWASP upload security](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html): allowlist formats, distrust declared MIME, bound content and decompression, use private storage and authorised retrieval. Scanning availability is recorded explicitly; no confidential files sent to public scanners.
- [Microsoft asynchronous processing](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply): distinguish acceptance from completion, provide durable status and idempotent retry. PostgreSQL jobs are our lightweight choice, not an Azure dependency.
- [W3C feedback guidance](https://www.w3.org/WAI/tutorials/forms/notifications/): concise overall feedback and errors linked to their affected fields with correction instructions. Apply to row/cell errors and accessible job-state changes.

**Deferred choices:** explicit partial application, general column-mapping UI, email/webhooks, multi-strategy packages, SFTP/S3 feeds and externally authenticated API clients. Add when actual workflows require them; no need to build these before the cash pilot. Existing source-specific permission and observation semantics remain in force.
