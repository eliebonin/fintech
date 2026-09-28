# Spineoff context and knowledge transfer

**Recorded:** 9 September 2026<br>
**Status:** Adopted architectural context; no schema or runtime behaviour was
changed by this transfer.

## Purpose

This record consolidates the context transferred from the prior **Spineoff**
discussion and the subsequent review of the complete `tech-v2` Markdown
knowledge base. It is the concise cross-project context for the Security Master
work, not a replacement for the detailed architecture notebook.

## What has been completed

1. The Spineoff discussion was reviewed and distilled into the Security Master
   task context.
2. The complete Markdown knowledge base under the prior `tech-v2` workspace was
   read: the external-platform notes and Security Master notes numbered 1–14.
3. The resulting design constraints were passed to the active Tech V2 Security
   Master work, including requirements for an explicit gap assessment rather
   than silent scope changes.
4. This file and the linked notebook index now make that transfer durable in the
   repository.

## Product and delivery context

Fortem is an institutional liquid-alternatives manager and investment-solutions
firm. Structured products are important, but are one capability within a wider
operating model that includes funds, bespoke mandates, portfolio construction,
risk, valuation, reporting, market data, and OTC operations.

The product strategy is to externalise selected workflows around proven Python
engines. It is not a wholesale rewrite of `fortem_core`. Productisation requires
new boundaries for tenancy, identity, entitlements, configuration, deployment,
audit, external APIs, and reproducible valuation.

The preferred first delivery is a narrow, managed design-partner workflow with
explicit data and market-data rights. It should be built contract-first:

```text
versioned API and engine contracts
  -> fixtures and generated client/mock server
  -> parallel core, data-quality, and front-end delivery
  -> reconciliation against trusted Fortem outputs
  -> controlled feature-flag release
```

## Canonical data boundary

The shared reference-data plane contains canonical instruments, legal entities,
products, fund/share-class and listing relationships, identifiers, provider
mappings, corporate actions, and authorised market-data observations.

Tenant overlays contain confidential operational data: positions, trades,
private instruments, client aliases/classifications, client-specific policy,
overrides, marks, and entitlement evidence. An approved tenant override never
rewrites shared source data. A private instrument is not promoted by copying it
into the global master; promotion is a governed proposal that preserves mapping
and audit history and excludes confidential terms.

Identity follows these rules:

- Fortem-generated immutable UUIDs identify internal records.
- An economic instrument, a venue listing, an issuer, a fund, and a share class
  are distinct concepts.
- Provider, bank, custodian, client, ISIN, FIGI, ticker, and similar values are
  source-aware, effective-dated mappings—not primary identity.
- Structural node type, economic instrument type, and business taxonomy are
  independently governed. Contract economics live in terms, legs, schedules,
  barriers, and component relationships.

## Market-data, valuation, and history rules

Market data is modelled as an economically precise series followed by immutable
observations. A raw observation, a derived value, and a tenant valuation mark
are different records with different purposes.

Resolution must use an explicit tenant, entitlement, purpose, valuation date,
named valuation cut, source/selection policy, and historic information cut. It
must not ask for an unqualified “latest price.” The selected result and all
input lineage are frozen in a calculation or Soft-NAV snapshot.

The following timestamps and dates are intentionally separate:

- `market_date` — business date represented by an observation;
- `observed_at` — when the source observed the value;
- source publication and platform receipt times — what was knowable when; and
- valuation cut — the defined business moment for selection.

Corporate actions are versioned events with dates and one-or-more effects.
They never overwrite raw price history. Derived price-return or total-return
series declare their adjustment basis and method. Vendor-restated history is
not assumed to reconstruct the information available at a past point in time.

## Integration and licensing boundaries

FpML, FIX, ISO 20022, vendor files, and similar messages are integration
formats. Raw messages/payloads and processing lineage should be retained, then
mapped through versioned adapters into the canonical model. Their nested
interchange structures are not the internal database schema.

Market-data, exchange, and vendor content must be used only within the
applicable contractual rights. Physical storage does not grant a tenant a right
to see or use a datum. Automated scraping or systematic manual transcription
is not a production source-of-record approach without permission for the
intended internal or client-facing use.

## Current authoritative detail

The detailed current design and its implementation/deferment status remain in:

- [Security Master notebook](../../security-master-notes/README.md)
- [Critical review and delivery choices](../../security-master-notes/18-critical-review-and-delivery-choices.md)
- [Tenant database topology and priorities](../../security-master-notes/19-tenant-database-topology-and-priorities.md)
- [Tenant routing and core API contract](../../security-master-notes/20-tenant-routing-and-core-api-contract.md)
- [Market-data coverage and provenance](../../security-master-notes/21-market-data-coverage-and-provenance.md)
- [External evidence and research register](../../security-master-notes/24-external-evidence-and-research.md)
- [Project state and quality review](project-state-and-quality-review-2026-09-07.md)

## Next engineering checkpoint

The priority remains one reliable vertical slice, rather than further breadth:

```text
authenticated tenant
  -> registry-routed tenant overlay
  -> canonical/market-data validation and entitlement
  -> frozen positions, cash, price and FX inputs
  -> reproducible Soft NAV
  -> immutable review/approval and correction evidence
```

This is the test of whether the architecture is becoming an operational
financial-data foundation rather than only a broad schema prototype.
