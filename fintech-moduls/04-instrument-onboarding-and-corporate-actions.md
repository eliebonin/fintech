# Module 4 — Instrument onboarding, identifiers, and corporate-action control

## Commercial proposition

Offer a managed canonical-security-master workflow for the universe the manager actually uses. The module does not try to replace global data-vendor coverage. It creates an approved, traceable internal truth across listed securities, funds/share classes, derivatives, indices, currencies, private instruments, and bespoke OTC products.

Primary buyers are data operations, fund operations, COO, investment operations, and administrator oversight teams.

## Core workflow

```text
user / trade / portfolio request
  -> candidate search across authorised providers and internal master
  -> source proposal with identifiers and raw lineage
  -> operations enrichment and maker/checker approval
  -> canonical instrument / listing / identifier activation
  -> downstream API publication
  -> periodic data-quality and corporate-action review
```

The workflow must distinguish:

```text
issuer / legal entity
!= economic instrument
!= fund umbrella
!= fund share class
!= venue listing
```

## Core data model

```text
financial_reference_node
  immutable Fortem ID, structural type, status

instrument
  economic contract and governed instrument type

listing
  venue-specific tradable representation, quote factor, unit multiplier

financial_reference_identifier
  node, scheme, value, venue context, validity, source

provider_instrument_mapping
  provider key to canonical node, mapping state/confidence/effective dates

instrument_party_role
  instrument, organisation, role, effective dates
  -- issuer, guarantor, calculation agent, fund manager, sponsor

corporate_action_event
  event type, announced/ex/record/payment/effective dates,
  source/version/status

corporate_action_effect
  event, affected node, effect type, ratio/cash/new instrument,
  entitlement basis and adjustment method
```

Identifiers are mappings, not identities. ISIN will often identify an issued instrument; tickers are normally listing-and-venue scoped; FIGI can require composite or listing context. Any uniqueness constraint must account properly for venue context and effective dates.

## Corporate-action model

Corporate actions are versioned events with one or more effects: split, consolidation, cash dividend, stock dividend, rights issue, merger, spin-off, tender, redemption, or delisting.

Raw market observations remain immutable. A separate adjustment model records the transformation basis, method, version, and source vintage used to derive adjusted history. Never infer whether vendor history is adjusted from the date Fortem received it.

## Private instruments and promotion

Tenant-private instruments live in a tenant namespace with access controls and confidential source terms. Promotion to the shared canonical master requires operations validation, deduplication, licensing/privacy review, and explicit approval. Promotion must create a new shared canonical record or controlled mapping; it must not expose private terms merely by flipping a visibility flag.

## APIs

```text
POST /v1/instrument-requests
GET  /v1/instrument-candidates
POST /v1/instrument-proposals/{id}/approve
GET  /v1/reference-nodes/{id}
POST /v1/corporate-actions
POST /v1/private-instruments/{id}/promotion-requests
```

Every read response identifies canonical status, source lineage, effective date, approval state, and data-rights visibility.

## MVP

Implement listed equity/ETF/fund-share-class onboarding with ISIN/FIGI/ticker mappings, venues, issuer relationship, two authorised providers, and the operational approval queue. Add mandatory cash dividends and stock splits as the first corporate-action events.

Then extend to bond, future, OTC, and private-instrument workflows. Do not begin by loading millions of records or attempting global-vendor parity.

## Commercial model

Sell as a managed operational control service and API. The value is reduced setup/reconciliation failures, faster approved onboarding, and traceable corporate-action/identifier decisions—not raw data resale. Any external data remains subject to the applicable licence and client entitlement.

## Market evidence and positioning

Rimes markets mastered security, pricing, entity, benchmark, and portfolio data from a large partner ecosystem: [Rimes](https://www.rimes.com/). NeoXam similarly positions DataHub as configurable enterprise data management spanning vendors, internal systems, counterparties, corporate actions, and regulatory data: [NeoXam](https://www.neoxam.com/datahub/). The standalone market is therefore competitive. Fortem should sell a curated operational workflow for the liquid-alternatives/OTC universe and bundle it with valuation or lifecycle control, not promise vendor-scale reference-data coverage.

See [market evidence and go-to-market](06-market-evidence-and-go-to-market.md) for pricing confidence and customer-discovery requirements.
