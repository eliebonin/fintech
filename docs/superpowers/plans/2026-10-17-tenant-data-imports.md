# Tenant data imports — proposed phased roadmap

**Status:** Historical scope roadmap; trade-first slice delivered separately  
**Content type:** Scope and delivery roadmap, not an executable implementation plan  
**Owner:** Product and data operations  
**Last reviewed:** 2026-10-17

**Execution update:** On 18–19 October the user prioritised trade uploads first.
See the [bounded trade-import delivery](../../delivery/trade-imports-20261018.md)
and current [F59 capability](../../product/features/tenant-data-imports.md) for
implemented scope and evidence; the cash-first phases below retain original intent.

**Goal:** Enable real-strategy acceptance data to enter governed domain workflows
without developer seed scripts, with reusable intake and delivery adapters.

**Scope and evidence:** [F59 dataset catalogue and controls](../../product/features/tenant-data-imports.md).
Its twelve families are the long-term exploration envelope, not one release.
The user requested documentation/planning, not implementation of this roadmap.

**Refinement:** The [per-workflow implementation plan](2026-10-17-tenant-import-workflows.md)
adds concrete shared tasks, tenant-aware Excel templates, atomic outcomes,
notifications and validation/application rules for every catalogue family.
Where sequencing differs, that refinement moves XLSX into the cash pilot before
trade imports; this file remains the original scope-level roadmap.

## Phase 0 — agree the first real files and contracts

- Obtain representative anonymised files and identify their source and rights.
- Confirm identifiers, tenant/strategy/account scope, dates, decimal/locale
  conventions, expected volumes and whether each file is a snapshot or delta.
- Define source/delivery/row IDs and the exact meanings of new/correct/revise.
- Inventory existing writer APIs and permission checks; specify per-domain
  validation and receipt contracts before selecting schema changes.
- Decide artifact retention, file limits, batch atomicity and recovery behavior.

**Exit:** A documented pilot template and hand-checkable acceptance dataset.
No claim of support for every custodian layout or instrument variant.

## Phase 1 — browser imports for valuation acceptance

Deliver in small vertical slices, not four half-built importers:

1. **U02 cash balances:** prove private intake, mapping, preview, explicit apply,
   retained revisions and safe retries using the existing snapshot writer.
   Prove CSV first, then tenant-aware XLSX templates before trade uploads.
2. **U03 prices/NAVs/FX:** explicit source/dataset and observation semantics,
   rights and correction handling through market-data owners. Do not broaden
   the current provider publisher's numerical/product constraints blindly.
3. **U01 trades:** start with one currently supported booking template, then
   extend product-specific templates as actual acceptance portfolios require.
   Freeze conventions and use normal corrections; no universal equity shortcut.
4. **U04 daily earned interest:** typed date/bond/strategy/amount/currency intake,
   with optional reconciled balance detail kept separate from daily earnings.

**Shared deliverable:** Tenant Imports list/detail with clear job states,
row-level validation and record links. Browser and API retries retain intent;
long-running work is bounded and does not occupy a browser request transaction.

**Exit:** An anonymised portfolio's inputs load through normal authority checks,
replay without duplicates, and reconcile to source totals. Financial acceptance
still compares calculated results to trusted reports; U11 report upload is not
claimed until its own slice is delivered.

## Phase 2 — practical operations and reconciliation

- Extend the pilot's values-only `.xlsx` coverage and add explicitly saved/versioned
  mapping profiles using real files; do not implement arbitrary tenant code or
  spreadsheet formulas.
- Add U09 identifier mapping administration and ambiguity resolution without
  automatically creating missing instruments or entities.
- Add U05 economic flows and U06 supported coupon-payment confirmations as
  distinct templates with explicit recognition/confirmation semantics.
- Add U11 holdings/NAV/P&L comparison files, kept separate from the trading
  ledger and calculated valuation records. Define comparable scopes/tolerances.

**Exit:** Repeat deliveries, conflicts, corrections and reconciliation breaks
are understandable and recoverable by Ops without database edits.

## Phase 3 — reference-data and configuration batches

- U07 typed instrument/listing proposals through existing approval paths.
- U08 entity matching and supported tenant organisation-list/profile operations;
  canonical new-entity onboarding requires a separately agreed authority path.
- U10 one supported reference subtype at a time, with source evidence and its
  proper review/sealing process. Do not promise ratings/fundamentals coverage
  from a generic file parser.
- U12 governed catalogues only on demonstrated demand; preserve meaning,
  retirement, revision and independent list-activation controls.

**Exit:** Batch intake does not bypass proposal decisions, leak private records
or alter historical booked economics. The paused shared/private stewardship
redesign stays paused unless separately resumed by the user.

## Delivery-channel extensions — demand-led, not prerequisites

Use the intake API behind the browser from Phase 1. External automated access
requires appropriate service identity and scoped authorization, not development
impersonation. Add one real SFTP or object-storage feed when a tenant needs it;
both reuse retained artifacts and domain processors. Handle incomplete uploads,
duplicate delivery, source correction, revocation and recovery explicitly.

No plain FTP, mandatory AWS migration, all-provider connector framework,
settlement/accounting engine, permission-import endpoint or automatic reference
promotion is included.

## Verification strategy for later implementation

Focused parser/domain tests first, then disposable-database and isolated browser
journeys: exact decimals and identifiers, cross-tenant/strategy denial, unknown
references, stale preview, repeat/conflicting delivery, crash/retry, explicit
zero versus absent snapshot, dividend/coupon recognition, full-file validation
beyond the preview page and rejection rather than truncation at limits.

This roadmap deliberately does not choose migration numbers, new endpoint
names or exact schemas before Phase 0 and existing-domain integration review.
