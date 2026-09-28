# Entities and instrument parties

## Purpose

The entity model distinguishes group-level aggregation from the legally liable organisation. This is necessary for structured-product issuance: issuer, guarantor, calculation agent, and paying agent may be different legal entities within the same group.

```text
Entity: HSBC Group
  |
  +-- Organisation: HSBC Holdings plc
  +-- Organisation: HSBC Bank plc
  +-- Organisation: HSBC Bank USA, N.A.
```

The group provides a useful aggregation ID. The child organisation represents the actual legal entity or branch with its own identifiers and obligations.

## First-release model

```text
entities
  group/root identity

entity_orgs
  legal entity or branch belonging to the group

org_identifiers
  LEI, BIC, registration number, tax ID, and other dated identifiers

instrument_party_role
  the organisation's effective-dated role on a specific instrument
```

Recommended distinction:

```text
organisation_kind
  LEGAL_ENTITY / BRANCH

instrument party role
  ISSUER / GUARANTOR / CALCULATION_AGENT / PAYING_AGENT / ARRANGER
```

An organisation's legal nature is distinct from its role on an instrument. One legal entity may be issuer, guarantor, counterparty, and vendor in different contexts or even on the same overall business relationship.

## Identifiers

LEIs, BICs, tax IDs, and registration numbers attach to `entity_orgs`, not necessarily the top-level group. They should be effective-dated and source-aware.

The top-level `entities` table should hold group-level data such as an internal code, short name, status, and group/legal display name where useful. An organisation row holds legal name, incorporation country/date, and organisation status.

## Instrument parties and credit

Structured products should link parties through a dedicated table:

```text
instrument_party_role
  instrument_node_id
  org_id
  role
  effective_from
  effective_to
```

This supports issuer, guarantor, calculation agent, paying agent, arranger, and hedging entity roles. Credit-rating observations should be separate, normally against the organisation/legal entity, with instrument-level ratings added only when a specific issuance has its own rating.

## Deferred capabilities

The following are useful but not required for the first master release:

* Generic entity ownership/control graphs.
* Multiple tax-residency history.
* Internal desks and business units.
* System-specific operational profiles and aliases.
* Normalised distribution-list recipients.
* Complex beneficial-ownership structures.

The initial entity/group, organisation, identifier, and instrument-party-role model is sufficient for correct issuance and guarantor identification.
