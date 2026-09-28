# Tenant overlays, client ingestion, and Soft NAV

## Evidence status

The tenant topology, entitlement resolver, ingestion contract, and Soft-NAV
snapshot model are product/control design decisions for this service. They are
not presented as a universal UCITS or fund-accounting mandate. Compliance,
outsourcing, retention, data-residency, and redistribution review remains open;
see the [external evidence and research register](24-external-evidence-and-research.md).

## Purpose

The security master is a shared canonical reference-data service. It must also support the daily operating reality of fund managers: client-specific positions and cash, private OTC instruments, approved valuation assumptions, administrator comparison, and indicative Soft NAV.

The design therefore separates three concerns:

```text
shared canonical identity and source facts
  + tenant-scoped operational data and governed overlays
  + immutable calculation/audit snapshots
```

UUIDv7 is the stable join key across these layers. It is not an entitlement mechanism and must never be treated as proof that a caller may read or amend an object.

## Physical deployment boundary

The logical tenancy model is implemented as one central generic database plus
one tenant-specific overlay database per client. The central database owns
shared `secm` and `md` data. The tenant database owns `ten`, `trd`, `nav`, and
client-specific `ing` records. Tenant databases store central UUID references,
but cannot use PostgreSQL foreign keys across databases; canonical API
validation and local link evidence provide that boundary.

This physical boundary is the primary protection against operational crossover.
RLS remains defence in depth and is still required for support tooling, shared
deployments and accidental-query protection. It does not replace market-data
licence/entitlement resolution.

## Scope and visibility

| Data class | Owner and visibility | Examples |
|---|---|---|
| Shared canonical | Fortem-governed and visible only under policy/rights | public instrument identity, listings, issuer, identifiers, official reference facts |
| Shared licensed | retained once where permitted, visibility determined by entitlement | vendor series and observations, data-source metadata |
| Tenant overlay | one tenant, effective-dated and approved where required | display alias, classification, valuation-source rule, model-price override |
| Tenant private | one tenant, confidential by default | bespoke OTC terms, private asset, client portfolio, positions and cash |
| Calculation evidence | one tenant/run, immutable | NAV input snapshot, output, reconciliation, exceptions |

## Overlays and private instruments

An overlay references a canonical object and changes its use in one tenant context. It must be explicit about the field/policy changed, old and new value where relevant, reason, effective period, approval, actor, and supersession.

```text
tenant_reference_override
  tenant_id
  target_reference_node_id
  override_kind                 -- alias, classification, valuation policy, approved value
  policy_or_field_code
  value payload / typed child value
  valid_from / valid_to
  recorded_at
  approval status, approver, reason
  supersedes_override_id
```

Do not use a generic JSON override row for confidential contractual economics. Typed tenant terms/valuation tables are safer, queryable, and validateable. A private instrument has its own immutable UUID and tenant visibility. Promotion creates a reviewed canonical record and a recorded promotion link; it must not make private payloads or terms visible to another tenant.

## Deterministic value resolution

A resolver takes an explicit valuation context: tenant, entitled datasets, subject, measure, currency/tenor, valuation date/cut, policy version, and historical information cut-off. It returns either a selected value with full lineage or a structured exception.

```text
approved tenant override
  -> tenant-entitled provider data
  -> platform-entitled approved data
  -> approved public data
  -> explicit missing-data exception
```

Source observations remain immutable. A selected value is a resolver result, and a mark or NAV result is a calculation result; neither overwrites the source observation.

## Client ingestion model

Use a small, supported delivery perimeter:

* HTTPS JSON API for system integrations;
* HTTPS multipart upload for controlled files;
* SFTP for scheduled administrator/custodian extracts; and
* authorised provider adapters where rights permit.

Every route converges into the same processing pipeline:

```text
submission
  -> immutable source payload
  -> schema / security checks
  -> mapping version and external-ID / identifier resolution
  -> reconciliation and exceptions
  -> maker-checker approval when material
  -> immutable tenant snapshot, tenant overlay, or canonical proposal
```

The canonical contract is strict. The boundary can be flexible through either a standard template, a maintained adapter, or a priced bespoke mapping. Do not couple internal tables to individual administrator column names.

### External-ID mapping service

Every incoming object must resolve through a namespace-aware mapping service. A Fortem UUID is the internal identifier; an external system's code is a time-bound mapping, not an alternate primary key.

```text
Custodian A / asset code "78462"
  -> namespace = CUSTODIAN_A_PROD, type = REFERENCE_NODE
  -> Fortem instrument/listing UUID

Client B / portfolio code "INCOME-01"
  -> namespace = CLIENT_B_PMS, type = STRATEGY
  -> Fortem strategy UUID
```

The namespace identifies the provider/bank/client/custodian and, where needed, the tenant and environment. A mapping records the external object type/ID, Fortem object type/UUID, mapping role, venue/context, validity, verification/confidence, source payload, and supersession. It returns one match, an explicit ambiguity, or an exception queue item; it must not guess from ticker or name.

Formal identifiers such as ISIN, FIGI, CUSIP and SEDOL remain separate canonical identifier assignments. The mapping service is for vendor opaque IDs, client/custodian codes, source trade IDs, organisation codes, portfolio codes, and other integration-specific aliases.

Suggested V1 APIs are `position-snapshots`, `cash-balance-snapshots`, `administrator-navs`, and `reference-data/proposals`. Submissions return `202 Accepted` with an idempotent, durable ingestion-job URI. Clients query status rather than waiting on a long HTTP request.

FundApps uses a comparable approach: controlled position ingestion, API/SFTP/UI delivery, identifier-based enrichment and conversion into a product-specific format. [FundApps Data Adapter](https://docs.fundapps.co/data/ada/propertiesDataAdapterPL.html)  OpenGamma demonstrates the useful `202 Accepted`/polling calculation pattern with versioned APIs and permission checks. [OpenGamma API documentation](https://docs.opengamma.com/)

## Soft NAV domain

Soft NAV is tenant-scoped and built above the reference and market-data domains. It is an indicative operational result, not automatically a fund administrator's official NAV.

```text
portfolio and cash snapshots
  + NAV policy and tenant overrides
  + market-data resolution snapshot
  + corporate-action state
  -> nav_calculation_run
  -> NAV valuation lines and result
  -> administrator reconciliation and review
```

The dedicated audit model is append-only:

```text
nav_calculation_run
  nav_calculation_run_id, tenant_id, fund/share-class/strategy, valuation date/cut,
  status, policy version, calculation version

nav_input_snapshot
  nav_input_snapshot_id, run ID, resolved_at, market-data-as-of time,
  resolver version, input hash

nav_input_snapshot_item
  snapshot ID, subject node, selected series/observation where applicable,
  selected value/currency, dataset, acquisition licence where known,
  entitlement/policy decision, source, selection reason, override reference

nav_valuation_line
  run ID, position/cash reference, quantity, local value, FX, accrual,
  base value, exception status

nav_result
  run ID, gross assets, liabilities, NAV, units, NAV per unit, status
```

When a vendor correction, policy amendment, or approved override occurs, create a new run and a new input snapshot. Never edit an old snapshot in place. FundGuard publicly describes a related principle: trusted, attributable investment-accounting data should be consumed through APIs with lineage rather than repeatedly copied into downstream systems. [FundGuard performance measurement](https://www.fundguard.com/powering-performance-measurement)

Price-date selection is part of the frozen policy decision. The NAV date may differ from the requested pricing date and from the actual date of the selected observation, for example where a fund's official NAV is T-1. The detailed rule hierarchy, staleness treatment, and audit fields are defined in [Soft-NAV pricing-date resolution](17-soft-nav-pricing-date-resolution.md).

## Required controls

* Authorise by tenant, user/service identity, role, dataset entitlement, and operation—not UUID knowledge.
* Retain raw payload checksum, storage locator, parser/mapping version, source timestamp, received timestamp, and processing outcome.
* Enforce idempotency for submitted files/messages and preserve correction/supersession lineage.
* Reconcile every intake against prior snapshot, administrator value, and expected flows with tolerances approved in policy.
* Make private data promotion deliberate: validate terms, remove confidential payload dependencies, obtain approval, then create/link the canonical record.

## First implementation slice

Deliver one complete workflow before broader product coverage:

```text
tenant position and cash upload
  -> identifier resolution / exception queue
  -> entitled EOD market-data resolver at a named cut
  -> Soft-NAV input snapshot and calculation run
  -> NAV result and administrator comparison
```

This proves the shared-master and tenant-overlay model with a daily client outcome. It does not require Fortem to claim full fund accounting, official NAV production, or a universal integration platform.

Namespace-aware external-ID mapping is a **foundation of this slice**, not a later ingestion enhancement. It must support at least `REFERENCE_NODE` and `STRATEGY` before any client position/cash upload is accepted. Without it, every client ingestion route would recreate fragile, adapter-specific identifier matching.

## Implemented indicative calculation boundary (V1)

`security_master_schema.soft_nav_service.calculate_soft_nav` now implements the
first narrow, auditable calculation path. It accepts an already-ingested full
position snapshot, confirms the tenant owns both strategy and snapshot, resolves
each subject under the tenant's versioned policy and historic information cut,
then creates a new resolution snapshot, NAV run, frozen NAV inputs, valuation
lines and result in one caller-owned transaction.

For a venue listing, V1 calculates:

```text
local value = quantity × selected quote × unit multiplier ÷ quote factor
```

This makes a 1,000-share GBP listing at a quote of 1,023 GBX worth £10,230;
the quote factor is not ignored or confused with the contract multiplier.

V1 supports only values already in the requested reporting currency. It refuses
missing/stale policy failures and explicitly raises a conversion-required error
when a frozen FX input would be needed. Cash balances, coupon/accrual valuation,
multi-currency FX selection, liabilities, administrator reconciliation and
approved manual overrides are the next service increments. This is intentional:
an indicative NAV must visibly fail a missing supported method rather than
silently blend source prices, latest FX, or unapproved assumptions.

## Deferred Soft-NAV completeness decisions

### Price and FX cut-off evidence

Every valuation line must eventually distinguish **two selected inputs**:

```text
local price input          -- price/NAV/mark for the held subject
FX conversion input        -- rate converting its local currency into reporting currency
```

Both inputs must be frozen in `nav_input_snapshot_item` records and linked to
their own `md.market_data_resolution_snapshot_item`. For each, retain at least:

* named `valuation_cut_id` and the UTC `market_data_as_of_utc` information cut;
* valuation date, requested pricing date, used market date and staleness result;
* selected series, immutable observation, dataset and acquisition licence;
* policy rule, selection reason and tenant entitlement decision; and
* for FX, base currency, quote currency, quote convention, selected rate and
  whether multiplication or division was applied in the reporting conversion.

`nav_valuation_line.fx_rate` is the numeric result used in a calculation, but
it is not sufficient audit evidence by itself. Its supporting FX input must be
traceable through the same resolver snapshot as the local price. No calculation
may obtain a later “latest FX” during reporting or replay.

### Cash, accruals and liabilities

Cash comes from the tenant strategy's dated `trd.cash_balance` snapshot, rather
than from a synthetic trade. Foreign-currency cash uses the same frozen FX-input
discipline as a security valuation. Bond and swap accruals will be calculated
from approved terms and schedules, stored as distinct valuation/input evidence,
and never inferred from a dirty price unless a policy explicitly selects that
price convention. Pending subscriptions, redemptions, fees, financing and other
liabilities must be separate signed lines with their own source and valuation
logic.

### Reconciliation and overrides

An administrator NAV comparison needs the reference value, currency, source
payload, comparison cut, tolerance policy, difference and review state. A
valuation override must be tenant-scoped, attributable to an authorised person
or service account, effective-dated, approved, and linked to its rationale and
source evidence. It creates a new snapshot/run; it never edits a historic
market-data observation or previous Soft-NAV run.
