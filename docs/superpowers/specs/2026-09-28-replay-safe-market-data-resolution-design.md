# Replay-Safe Market Data Resolution Design

**Status:** Approved
**Date:** 2026-09-28
**Scope:** Market-data selection, frozen evidence snapshots, Reference API, generated contract, and a minimal Ops Console drill-down.

## Goal

Create a tenant-safe, point-in-time market-data resolution API that selects
market-data observations deterministically and freezes the complete evidence
needed to explain or replay that selection. The API is the primary product of
this slice. The UI is deliberately limited to creating and reading one
instrument's snapshot.

A successful resolution snapshot answers, without consulting today's provider
state or entitlements: which policy and rule applied; which observation and
vintage were eligible at the historical information cut; why it was selected
or rejected; and which input values were frozen.

## Scope

This slice delivers:

1. a `market-data-resolution-snapshots` resource that creates and reads
   immutable, tenant-scoped snapshots;
2. deterministic policy precedence and historically correct vintage and
   correction eligibility;
3. explicit per-subject outcomes and evidence for selected and unselected
   results;
4. an OpenAPI-described, generated TypeScript contract; and
5. a minimal Ops Console flow to create one snapshot and inspect its frozen
   evidence.

It does **not** add live vendor ingestion, quality-workflow changes, pricing
or FX calculation changes, calendar/session modelling, a portfolio batch job,
Soft NAV/P&L consumption, authentication/authorisation redesign, or a generic
rules language.

## Public API

### Resource shape

The API models an immutable resolution snapshot as a resource, rather than an
imperative `resolve` operation:

* `POST /v1/market-data-resolution-snapshots`
* `GET /v1/market-data-resolution-snapshots/{snapshotId}`

Creation returns `201 Created`, a `Location` header, and the fully populated
snapshot. A successful create is synchronous for this bounded slice; it must
finish only after the header, items, frozen evidence, and idempotency result
are committed. A later portfolio-scale implementation may create an
asynchronous job that itself creates the same snapshot resource.

### Create request

The OpenAPI request schema is strict and generated into `api-contracts`:

```json
{
  "subjectReferenceNodeIds": ["uuid"],
  "valuationPolicyId": "uuid",
  "valuationDate": "YYYY-MM-DD",
  "valuationCutId": "uuid",
  "marketDataAsOfUtc": "RFC 3339 UTC timestamp",
  "usePurpose": "VALUATION"
}
```

`subjectReferenceNodeIds` is unique and bounded to 1–50 entries. Every item
shares exactly the same policy, valuation date, valuation cut, information
cut, and use purpose. That represents one coherent set of evidence rather
than an arbitrary HTTP batch. `marketDataAsOfUtc` must be timezone-aware UTC.

`Idempotency-Key` is required on the request. Its durable record is scoped to
the authenticated/trusted tenant and endpoint, and stores a canonical request
fingerprint plus the created snapshot ID. A retry with the same key and the
same request returns the original `201` representation (or a documented
equivalent successful replay); reusing the key with a different fingerprint
returns `409 idempotency.key_reused`. Expired key retention must be explicit
in configuration/documentation; the initial retention period is at least 24
hours.

Structural errors produce existing RFC 9457 problem details and create no
snapshot: invalid UUIDs/timestamps/purpose, duplicate or over-limit subjects,
tenant/policy mismatch, inactive/expired policy, policy/cut mismatch, or a
missing subject reference node. Each response includes `X-Request-ID`.

### Snapshot representation

The created and fetched representation contains a header and one item per
requested subject. Header fields include ID, tenant-visible policy ID,
valuation date/cut, information cut, use purpose, resolver version, status,
created timestamp, and request ID/idempotency replay metadata where safe.

Each item contains:

* subject ID and `SELECTED`, `MISSING`, `STALE`, or `DENIED` outcome;
* selected value/currency, series and observation IDs where selected;
* applied policy-rule ID and immutable rule-identifying fields needed for
  explanation;
* dataset, licence and provider/source identifiers or safe display values;
* selected vintage ID, provider-publication timestamp, and platform-receipt
  timestamp;
* requested and used pricing dates, staleness value/status;
* entitlement decision, selection reason, and stable exception code.

Snapshot status is `COMPLETED` only if every item is selected; otherwise it is
`PARTIAL`. Business outcomes are valid, persisted items, not request failures:
`MISSING` means no eligible data for the selected rule; `STALE` means the
policy's staleness/missing-data action prevents selection; `DENIED` means
candidate data exists but no valid historic entitlement permits its use.

The existing market-data series catalogue remains a history/provenance
browser. It is not changed into a resolver and must not represent current
entitlements as historical snapshot evidence.

## Resolution semantics

### Validation and policy scope

Before candidate selection, the service validates UTC information-cut time and
confirms that the valuation policy belongs to the request tenant, is active,
is effective on the valuation date, and owns the supplied valuation cut. The
resolver then obtains the subject type and, where applicable, instrument type.

Rules are evaluated with a closed precedence order:

1. exact market-data series;
2. exact canonical subject/reference node;
3. instrument type;
4. policy default;
5. `rule_sequence` within the same specificity.

The first matching rule is authoritative. An unavailable exact rule does not
silently fall through to a less-specific rule; its configured missing-data
action decides the result.

### Point-in-time candidates

An observation is a candidate only when it is accepted, matches the selected
series type/dataset constraints, has a market date, and is covered by an
active tenant entitlement for the request purpose and valuation date.

The linked vintage must be eligible at `marketDataAsOfUtc`: platform receipt
is at or before the cut and, when available, source publication is also at or
before the cut. Legacy observations with no vintage use their recorded
receipt/publication fields under the identical predicate only when explicitly
allowed by a migration-compatible rule; otherwise they are not eligible.

An accepted correction suppresses the observation it supersedes only if that
correction is itself eligible at the same information cut. A correction
received after the cut cannot rewrite an earlier replay. Provider publication
and receipt timestamps are compared as UTC instants; equality at the cut is
eligible.

The candidate set then flows to the existing `valuation_resolver` for the
rule's pricing-date, lag, staleness, and missing-data semantics. This slice
does not change those calculations.

### Reasons and data minimisation

Selection reasons and exception codes are stable public vocabulary, e.g.
`ENTITLED_PROVIDER`, `NO_MATCHING_POLICY_RULE`, `NO_ELIGIBLE_VINTAGE`,
`NO_ENTITLED_OBSERVATION`, `STALE_MARK`, and `ENTITLEMENT_DENIED`. The API
must distinguish a true absence of eligible data from a prohibited use of
otherwise matching data, without disclosing vendor data or licence details to
an unauthorised tenant.

## Persistence and immutability

`market_data_resolution_snapshot` remains the header and
`market_data_resolution_snapshot_item` remains the item collection. A new
schema migration adds the explicit frozen evidence fields absent today:

* header: `use_purpose`, idempotency key fingerprint/record linkage, and any
  required creation/request correlation metadata;
* item: `market_data_vintage_id`, source publication and receipt timestamps,
  source/provider and licence identifiers (where represented in the schema),
  and immutable rule/evidence fields required by the API response.

The migration adds an idempotency table with tenant, endpoint, key, request
fingerprint, snapshot ID, creation/expiry timestamps, and a uniqueness
constraint on tenant/endpoint/key. It stores a digest, never a request body or
secret header value beyond the idempotency token required for lookup.

Header and item tables become append-only: application code has no update or
delete path, and database triggers reject `UPDATE` and `DELETE` after insert.
Migrations/bootstrap data remain explicitly permitted administrative paths.
The creation transaction inserts the snapshot header, all items, evidence, and
idempotency record atomically. The read path retrieves only persisted fields;
it never re-resolves candidates or re-checks today's entitlement.

## API and frontend integration

FastAPI Pydantic contracts define the create payload, header/item response,
outcome vocabulary, `Idempotency-Key` parameter, and documented standard
problem responses. Exporting the existing OpenAPI artifact and regenerating
`packages/api-contracts` is mandatory in the same change.

Reference API repository functions own snapshot create/read queries. The
route layer enforces trusted tenant context and maps expected domain failures
to existing safe problem details. The resolver remains a domain module and
does not import FastAPI or frontend code.

The Ops Console gets only:

1. an active valuation-policy selector for the trusted tenant;
2. a one-subject form prefilled from the current Market Data selection;
3. a BFF POST route that passes trusted tenant context and creates an
   idempotency key server-side; and
4. a snapshot evidence page/read BFF route using generated contract types.

No browser code receives tenant credentials. No local TypeScript model may
duplicate the new API schema.

## Verification

Tests precede implementation and cover:

* OpenAPI request constraints, generated client compilation, representative
  create/read calls, `201`/`Location`, standard error declarations, and
  request-ID propagation;
* correct selection, exact precedence, no less-specific fallback, and policy
  cut/tenant/effective-date validation;
* late correction, late platform receipt, late provider publication, equality
  at cut, legacy-observation rule, missing data, stale data, and entitlement
  denial;
* atomic rollback, 1–50 batch order/unique-subject semantics, snapshot status,
  tenant-isolated reads, append-only triggers, and evidence readback without
  live resolution;
* first request, identical idempotent retry, and conflicting key reuse; and
* the one-subject Ops Console create-to-evidence journey.

Before declaring the slice complete, run the focused Python/API tests,
OpenAPI export and generated-client drift checks, Ops Console type-check/test/
build, and the existing secret scan. Record exact commands, outcomes, and any
pre-existing full-suite limitation in a dated delivery quality-review note.

## Acceptance criteria

The slice is complete when a tenant can create and later retrieve an immutable
snapshot for 1–50 subjects, each selection is demonstrably limited to data
knowable and entitled at the requested cut, retries cannot duplicate a
snapshot, all result evidence comes from frozen storage, and the new contract
is generated and consumable from the monorepo package. A single-instrument Ops
workflow must display that frozen evidence without recreating the selection.

## Explicit deferrals

No live feeds, vendor onboarding, quality scoring changes, provider calendar
logic, portfolio/job scheduling, Soft NAV/P&L inputs, pricing algorithms,
market-data write API, or generic policy DSL are delivered by this slice.

## References

The API resource and create semantics follow [Google AIP-133](https://google.aip.dev/133)
and [Microsoft's REST API guidance](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design).
The idempotent POST behaviour follows the [IETF Idempotency-Key HTTP header
draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html).
The request-schema constraints and generated contract follow the [OpenAPI 3.1
Specification](https://spec.openapis.org/oas/v3.1.0).
