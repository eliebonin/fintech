# Automated reference-data onboarding

## Evidence status

The proposal, matching, approval, and idempotency workflow is our operational
control design. It is informed by observed API/SFTP ingestion practice, but the
confidence thresholds and automated-approval policy are not universal industry
rules. Source-specific evidence and production adapter certification remain
open; see the [external evidence register](24-external-evidence-and-research.md).

## Purpose

Reference-data adapters may propose new canonical records, but an adapter is
never allowed to write an approved instrument directly. The workflow separates
source submission, matching/validation, approval, and materialisation. This
keeps the operations team in control while removing repetitive data entry for
high-confidence source records.

## Workflow

```text
source adapter / operations UI
        |
        v
structured CREATE proposal (source + idempotency + payload version)
        |
        +-- exact/conflicting identity -> durable conflict / manual review
        |
        +-- governed policy + complete facts + threshold -> automated APPROVED
        |
        +-- otherwise -> PENDING operations review
        |
        v
approval evidence (manual or automated)
        |
        v
atomic materialisation of node, instrument, listings, versions, identifiers,
scope and optional provider/custodian mapping
```

## Policy and evidence

`secm.reference_data_automation_policy` is a versioned, source-bound catalogue.
It defines the target object and operation, confidence threshold, required
identifier schemes, source-specific criteria, tenant scope, effective period,
and whether automatic approval is permitted. A policy is itself approved and
is immutable by version.

`secm.reference_data_proposal` records the structured payload, producer mode,
source system, policy version, idempotency key, matching state, confidence, and
payload-contract version. Retries with the same `(source_system_id,
idempotency_key, tenant_id)` return the original proposal rather than creating a
second instrument.

`secm.reference_data_approval` records the decision method (`MANUAL` or
`AUTOMATED`), policy reference, and structured decision evidence. Automated
evidence includes the policy/version, required and missing identifiers,
criteria results, confidence, and source namespace. No caller can set
`status=APPROVED` without producing an approval row through this workflow.

## Equity MVP contract

The first supported adapter contract is an equity aggregate containing a
canonical name, optional internal code and issuer, base currency, effective
date, ISIN/FIGI/SEDOL/CUSIP values, and one or more venue listings. Each listing
contains venue UUID, symbol, trading currency, quote factor, unit multiplier,
primary-listing flag, optional venue-level FIGI, and effective date. CFI is deliberately deferred: it is a
classification code rather than a unique security identifier and needs a
classification-assignment model before it is accepted by this endpoint.

On approval the service creates one private tenant-scoped instrument aggregate,
one listing node per venue, approved definition versions, formal identifiers,
and (when supplied) a verified source mapping to the instrument or primary
listing. The economic identity remains separate from venue representation.

## Matching and correction rules

* ISIN and internal code conflicts are rejected before materialisation; a
  venue/symbol conflict is also rejected.
* `canonical_name` is a human-readable instrument-level label, not an identity
  key. It may be corrected through a new approved definition version and is not
  globally unique. `internal_code` is a platform convenience code and is
  unique within the canonical master; it is not a provider identifier and is
  not reused after retirement. Listing tickers and venue-specific codes remain
  listing-level identifiers.
  The current equity MVP records the initial values and approval evidence;
  historical label/code version materialisation remains part of the future
  AMEND workflow rather than an in-place edit.
* Issuer selection is deliberately flexible. The workflow first searches for a
  matching legal organisation using governed organisation identifiers (LEI when
  available, registration identifiers, and controlled name/jurisdiction
  evidence). If an exact match exists, the instrument links to that
  `organisation_id`. If the issuer is absent or ambiguous, a manual proposal
  may remain unresolved and is routed to operations; automated approval must
  fail the issuer criterion. Operations should resolve or create one governed
  legal-organisation record, rather than creating a new issuer row for every
  instrument. A group-level `entity_id` remains optional context; the issuer
  link is to the legal organisation that issued the security.
* A source mapping requires a configured source system and namespace. Provider,
  bank, custodian, and client codes therefore remain aliases, not identity.
* A correction is a new proposal and, after approval, a new effective-dated
  definition version. Approved rows are not silently overwritten.
* Automated submission is policy-mediated validation, not a trust shortcut.
  Policies can be disabled or superseded without changing prior approvals.
* The current MVP materialises a tenant-private aggregate. Promotion to shared
  canonical identity remains an explicit, separately approved operation.

## API and UI

`POST /v1/equity-proposals` accepts either `MANUAL` or `AUTOMATED` submissions;
instrument creation may contain zero listings. `POST /v1/listing-proposals`
accepts a listing only together with a selected, approved parent equity or
digital-asset instrument; the legacy `/v1/equity-listing-proposals` path
remains an alias. Both proposal types use the existing approval endpoint, and
listing approval validates the parent again before materialising the venue row
and listing-level identifiers. The operations console therefore has separate
“Add an equity” and “Add a venue listing” screens: the latter requires an
instrument search and explicit selection before listing fields unlock.
`GET /v1/market-venues` and `GET /v1/currencies` supply canonical venue and
quote-currency UUIDs; the browser does not maintain its own catalogues.

Cryptoasset parent creation is now a dedicated manual-first workflow:
`POST /v1/crypto-asset-proposals` and its decision endpoint back the
`/instruments/crypto/new` screen. Approval materialises one tenant-private
`DIGITAL_ASSET` economic node, an effective-dated `secm.crypto_asset_terms`
row, and a `secm.currency` row whose `reference_node_id` points to that same
asset. The native symbol is normalised to uppercase and must not collide with
an active currency role; internal codes remain globally unique when supplied.
Chain deployments and venue pair listings are deliberately separate follow-up
workflows, so the parent page does not pretend that one network or venue is
canonical. The existing generic listing workflow can select the approved
digital-asset parent and add BTC/USD, BTC/USDC, or equivalent venue records.

Structured-product underlying selection uses the same canonical search contract
with an explicit `reference_level`: `ANY` (default), `ECONOMIC`, or `LISTING`.
`LISTING` is a server-enforced scope, not a browser-only filter; the API joins
the listing to its parent instrument to apply the requested economic type and
asset-class filters. Listing results include the parent node UUID, venue MIC,
venue name, trading symbol, and trading currency so Operations can see exactly
which venue representation they are selecting. The UI disables the listing
scope for reference categories without a meaningful venue representation, such
as index, commodity, rate-index, currency, and FX-pair references.

## Deferred decisions

The service intentionally does not yet implement bulk file ingestion, source
payload retention for every adapter, fuzzy matching, CFI/regulatory
classification assignments, corporate-action amendments, or automated
promotion of private records to shared canonical records. Those are separate
capabilities because each needs its own controls and evidence model.
