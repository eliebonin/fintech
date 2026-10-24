# Tenant data imports — capability and staged rollout

**Status:** PARTIAL — bounded trade-import alpha; other families proposed  
**Content type:** Capability reference and dataset catalogue  
**Owner:** Product and data operations  
**Last reviewed:** 2026-10-23 (external tooling boundary)

## F59 Governed tenant file imports

Source-specific external CSV import scripts are not F59 product functionality.
They live in [isolated optional tooling](../../../tooling/reconciliation_csv/README.md).
The supported workflow below remains unchanged; that one-off exercise does not
establish support for any additional template or upload family.

- **Desired:** Let tenants submit business data through files, with reusable
  mappings, validation, review, safe application and traceable outcomes. Later
  delivery channels must reuse the same business rules.
- **Origin:** User requested upload-channel research and a documented scope/plan
  on 17 October 2026. The catalogue and rollout below are recommendations for
  discussion, not approval to implement every family.
- **Overall status:** PARTIAL. U01 NEW listed equity/ETF/fund imports are implemented;
  other product templates and dataset families remain proposed. F35 market-data
  uploads remain FOUNDATION, not implicitly delivered by the shared parser.
- **Backend today:** `/v1/trades/imports` retains private original files, validates
  rows, freezes a review hash and atomically books through the existing cash writer.
  Tenant/strategy-scoped source IDs bind replay to original trades. Domain-specific
  orchestration lives in `apps/reference_api/import_service.py`; shared file/schema
  primitives live in `data_imports`. Provider acquisition remains in `market_data`.
- **Frontend today:** `/imports`, available from Trade imports in the menu, offers
  guided Prepare → Upload → Review & book cards, strategy-scoped Excel templates,
  validation, explicit booking, summary counts, paged errors-first row review and
  separate history. Technical evidence remains expandable; error CSV and original
  downloads remain available. Standard optional properties,
  active tenant custom fields and governed dropdowns are included.
- **Cuts/trade-offs:** One strategy, NEW cash bookings, at most 500 trades/512 KiB per
  explicitly confirmed file. Bounded synchronous commands with durable jobs/receipts;
  no background worker, silent partial booking or arbitrary spreadsheet execution.
  Exact values use text cells/ISO text dates; numeric/formula cells are rejected.
  Original artifacts are private bounded database blobs, not a new storage service.
- **Weaknesses/remaining:** Product-specific derivatives/bond templates, bulk
  corrections, other dataset processors, queued large-file execution, saved mapping
  profiles, automatic artifact retention cleanup and email/webhooks remain absent.
  Representative real-file reconciliation is not established by synthetic acceptance.
- **Delivery:** [Trade import scope, activation and verification](../../delivery/trade-imports-20261018.md).
- **Plan:** [Proposed phased rollout](../../superpowers/plans/2026-10-17-tenant-data-imports.md).
  [Per-workflow implementation plan](../../superpowers/plans/2026-10-17-tenant-import-workflows.md)
  defines the long-term workflow slices; delivery rulings above supersede its
  original cash-first sequence and queued-worker assumptions for this alpha.

## Proposed catalogue: 12 dataset families

Families are business categories, not twelve tables or twelve first-release
importers. Several require distinct templates; sharing intake does not mean
sharing one generic financial mutation schema. Phase is proposed priority.

| ID | Family and examples | Safe write meaning | Proposed phase |
| --- | --- | --- | --- |
| U01 | Trades: historical/new executions and supported properties | NEW listed equities/ETFs/funds delivered through the normal cash writer; other products and file correction/cancellation templates remain later work | 1, first delivered slice |
| U02 | EoD cash balances by strategy, company/account and currency | Proposed exact-date file snapshots through the existing balance writer; no implied file importer from the trade slice | 1, after trade pilot |
| U03 | Market observations: prices, NAVs, outright contract rates and FX | Add governed dated observations/corrections with source, currency/orientation, basis and timing; no silent promotion to preferred/official/valuation-eligible data | 1 |
| U04 | Daily bond earned interest and optional accrued stocks | Record the daily amount, date, canonical bond, strategy and currency through existing assessed-input rules; accumulated balances remain distinct | 1 |
| U05 | Economic income/cost events: dividends, resets, fees and adjustments | Explicit economic date, component and recognition role; do not treat every payment or reset amount as newly earned P&L | 2 |
| U06 | Actual payment confirmations, initially supported bond coupons | Retain payment evidence separately from earnings, expected schedules, trades and cash snapshots; no new settlement/accounting engine | 2 |
| U07 | Instrument and listing definitions, including terms/dependencies | Prepare typed proposals through existing creation/approval permissions and supported product paths; importing is not shared publication or booking readiness | 3 |
| U08 | Legal entities and tenant organisation working lists | Match existing canonical identities first; import tenant labels and supported role selections explicitly. New shared identities require an approved onboarding path, not private-label overwrites | 3 |
| U09 | External identifiers and mappings | Versioned source/tenant/profile-scoped aliases, with ambiguity and validity checks; never globally resolve an identifier by text alone | 2 |
| U10 | Market reference facts/events: corporate actions, contractual schedules and calendars | Separate subtype-specific sourced proposals/revisions and review; no direct CSV alteration of sealed calendars or instrument terms | 3 |
| U11 | External reconciliation statements: holdings, NAV and P&L comparisons | Retain external benchmarks for comparison. Holdings do not become artificial trades, and external NAV/P&L does not overwrite calculated/published results | 2 |
| U12 | Tenant-maintained catalogues: traders, governed choices and selected configuration | Explicit additions/retirements/revisions; preserve historical meanings and independently controlled list activation. No blanket import of users, permissions or licences | Later, demand-led |

### What market reference data means here

U03 contains observed numerical values, including dated FX rates. U10 contains
facts/events/conventions used to interpret instruments and observations: split
ratios and event dates, expected coupon/reset schedules and session calendars.
Ratings, fundamentals, index membership and other reference feeds may later fit
this family, but are not promised until their models, contracts, rights and
consumers are specified. Source-specific data models remain necessary.

### Instrument and entity governance remains unchanged

The [shared/private instrument stewardship idea](instrument-management.md#proposed-direction-shared-and-tenant-private-stewardship)
was subsequently put on hold by the user. This import proposal must not implement
that authority/navigation redesign implicitly. U07/U08 will require their own
confirmed scope and use the then-current approved authority model.

Unknown instruments/entities should produce unresolved rows with links to the
appropriate onboarding path, not automatic confidential-to-shared promotion.
Selecting an organisation or importing a legal name is not KYC/credit approval.

## Shared intake, separate business processors

Delivery channels hand artifacts to a common intake/job layer. Versioned format
adapters produce domain-specific proposed records. Existing domain services
remain authoritative; provider acquisition/normalisation stays in `market_data`.
Do not replace domain APIs with a generic table-write or JSON-to-SQL importer.

Proposed user flow:

1. Select the import type, authorised strategy/dataset/source and template/profile.
2. Upload and safely retain the original file; record server receipt time and hash.
3. Parse, map identifiers and validate every row, not merely the preview page.
4. Show proposed effects, unresolved rows, duplicates, errors and warnings.
5. Explicitly confirm application; revalidate authority and stale dependencies.
6. Inspect a durable receipt linking each applied row to its resulting record.

Uploading, applying an import, approving a reference proposal and publishing a
valuation are distinct actions. No upload should automatically publish valuation.

## Non-negotiable semantics

- **Scope:** Tenant/actor identity comes from authenticated context, not trusted
  spreadsheet columns. Strategy/dataset permissions apply to jobs, files, row
  details, validation, commit, receipts and retries. A transport credential must
  not confer broader business authority.
- **Identity:** Source/delivery IDs and stable external row IDs are required where
  replay is possible. File hashes establish content identity but are not enough
  to deduplicate financial rows across differently packaged files. Conflicting
  reuse of the same key is rejected rather than silently accepted.
- **Dates and numbers:** Exact decimals and explicit currencies/units/orientation;
  declared date, timezone and locale formats. Preserve identifiers as text,
  including leading zeroes. Historical economic dates never backdate server
  receipt/knowledge timestamps.
- **Updates:** Distinguish new booking, record correction, snapshot revision,
  observation correction, mapping revision and reference proposal. Never delete
  all existing strategy data because it is absent from an uploaded file.
- **Failure:** Specify atomicity per bounded commit batch. Initial financial
  imports should block a batch with validation errors. Any later partial mode
  must be explicit, report exact committed rows, and retry without duplication.
  Recheck conflicts at commit; an earlier green preview is not a reservation.
- **Capacity:** Explicit size/row/decompression limits; reject oversized input,
  never silently truncate it. Pagination applies to preview/errors, not to how
  much of the accepted file is validated. Do not hold a database transaction
  while waiting for upload, user review or remote network operations.
- **Market data:** Retain original provider and permitted-use evidence. Possessing
  a file is not proof of ownership/redistribution/valuation rights. FX needs its
  pair orientation and actual fixing semantics. Upload does not change source
  priority, confer official status or bypass quantity-basis proof.
- **Reassessment:** Imported financial changes follow existing impact rules.
  Do not silently reprice published valuations. Non-ledger source-change impact
  handling must be scoped before claiming complete automatic reassessment.

## Formats and delivery channels

- **Delivered for U01:** UTF-8 CSV and tenant-aware values-only `.xlsx` through the
  browser/BFF intake API. Bounded synchronous commands retain durable job/status/
  receipt resources. No worker service, microservice or cloud subscription is required.
- **Excel:** Controlled sheets/headers and tenant-aware dropdowns, with template
  version/generation metadata. Saved mapping profiles follow later.
  Reject formula input cells, macro-enabled files and external dependencies;
  do not evaluate formulas or trust cached results as financial facts.
- **Later:** Machine-to-machine HTTPS access with appropriate identity, scoped
  credentials and idempotency. Local impersonation is not production API auth.
- **On demand:** SFTP for an actual custodian/admin feed; object-storage delivery
  for a concrete cloud deployment. Both invoke the same validation/processors.
  Do not assume one S3 bucket per tenant is mandatory; access isolation must be
  explicitly enforced regardless of bucket/prefix organisation.
- **Exclude:** Plain FTP. FTPS is a separate TLS-protected protocol and would be
  considered only for a real integration requirement.

## Excel templates and user outcomes — delivered trade contract, proposed reuse

Generate an Instructions sheet, a named data table and reference lists from the
current user's authorised tenant/strategy/source context. Include template/schema
version and generation time. Tenant custom columns use immutable definition IDs
and current types; choice columns use stable codes, optionally accompanied by
labels. Labels and hidden/protected sheets are usability aids, not authority.
Prefer explicit instrument identifiers over a dropdown of the entire universe.

Reference lists are snapshots. Revalidate current eligibility on upload and apply;
editing an uploaded lookup sheet never creates an authorised choice. Compatible
older templates need not fail just because their generation date is old. Preserve
IDs and precision-sensitive amounts as text; reject ambiguity or unsupported
precision rather than silently rounding. Native named-range validation references
are allowed, but uploaded formulas in financial input cells are not evaluated.

For the initial bounded commit group, ten trades with one invalid row means
**9 valid, 1 requires correction, 0 booked**. Retain the valid staging rows and
all issues; a corrected file is revalidated before explicit confirmation. A
commit-time conflict rolls back that whole group, including audit/receipt effects.
The system must never silently book nine. An explicit partial mode is deferred;
linked corrections/dependency packages must remain atomic even if added later.
Larger files may have separately displayed/confirmed groups, not hidden commits.

Keep an Imports history and durable job detail with checked/valid/invalid/applied/
replayed counts, row/cell explanations and remedies, safe annotated downloads,
record links and correlation IDs. Differentiate received, validating, ready,
applying and applied/failed. Applying means the domain-specific effect: trades
booked, balances saved, observations stored or proposals submitted, not approval
or valuation publication. A network timeout requires outcome recovery, not blind
resubmission. Retries resolve existing row effects without duplication.

Initial notification delivery is persistent in-app status/history with accessible
completion feedback. Email/webhooks and a general notification platform are not
prerequisites. Job visibility, artifacts, errors and receipts all use current
domain/strategy/dataset rights, including after permission revocation.

These are proposed product decisions; source-backed controls and applicability
are recorded in the [implementation plan research](../../superpowers/plans/2026-10-17-tenant-import-workflows.md#research-and-project-choices).

## Research evidence and applicability

Reviewed 17 October 2026. These primary sources support engineering controls;
they do not mandate our twelve-family catalogue or rollout order.

- [OWASP file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html):
  allowlisted formats, content checks, private storage, authorization, scanning
  and limits including decompressed content. For this project, do not send
  confidential uploaded files to public scanning services without authorization.
- [OWASP spreadsheet injection](https://community.owasp.org/attacks/CSV_Injection):
  protect downloadable receipts/error reports from untrusted formula content.
  Keep safe display/export handling separate from original evidence and exact
  typed financial values; a negative financial number is not inherently invalid.
- [Microsoft asynchronous request-reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply):
  durable accepted-job status and retry/idempotency guidance; not a requirement
  to adopt Azure or a heavyweight queue platform.
- [AWS transfer protocols](https://docs.aws.amazon.com/en_en/transfer/latest/userguide/tf-server-endpoint.html):
  SFTP uses SSH, FTPS uses TLS, plain FTP is unencrypted.
- [AWS presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
  and [notification semantics](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html):
  existing object keys can be overwritten; events can duplicate/reorder. Any
  future adapter needs scoped short-lived upload authority, finalised immutable
  artifact/version binding and idempotent processing, not blind event-to-booking.

## Planning and evidence limits

This is a documentation/source-interface inventory, not an exhaustive code audit
or completed implementation design. Reused entry points include
[market-data ingestion](../../../market_data/ingestion.py),
[cash snapshots](../../../valuation/cash_snapshots.py),
[assessed daily accrual](../../../valuation/accruals.py),
[economic flows](../../../valuation/flows.py),
[coupon service](../../../lifecycle/coupon_service.py),
[trade correction](../../../apps/reference_api/trade_corrections.py) and
[organisation commands](../../../apps/reference_api/tenant_organisations.py).
Existing operational [fund/source mapping profiles](../../architecture/trading-and-operations/tenant-fund-operational-mappings.md)
are a narrower model, not already a universal column-mapping service.

The original 17 October planning task made no runtime changes. The subsequent
trade-import implementation is recorded separately in the delivery link above;
it does not implement the remaining catalogue families or publish valuations.
