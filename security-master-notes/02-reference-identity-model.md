# Reference identity model

## The hybrid node model

Use a common `financial_reference_node` identity with semantic subtype tables.

```text
financial_reference_node
  universal ID for a referenceable financial object

instrument
  economic-instrument subtype

listing
  venue-specific subtype, linked to its economic instrument
```

This is preferred to either two separate price tables or one broad, undifferentiated instrument table. It provides one reference target for market data and derivative legs, while retaining clear business meaning.

## Node types

`financial_reference_node` does not carry an unconstrained text type. It holds a foreign key to the small, governed `reference_node_type` catalogue. A node type says what *structural kind of object* the node is, not what product economics it has.

```text
reference_node_type
  reference_node_type_id
  type_code                   -- INSTRUMENT, LISTING, INDEX, CURRENCY, ...
  node_class                  -- ECONOMIC, VENUE_REPRESENTATION, REFERENCE
  default_is_tradable
  status

financial_reference_node
  reference_node_type_id      -- FK to reference_node_type
  is_tradable                 -- actual value on this specific node
```

Seeded types include `INSTRUMENT`, `LISTING`, `INDEX`, `CURRENCY`, `FX_PAIR`, `COMMODITY`, `RATE_INDEX`, `REFERENCE_PORTFOLIO`, and `FUTURE_FAMILY`. `is_tradable` stays on the individual node because the catalogue supplies only a default. GBP is a non-tradeable `CURRENCY` node; a listed security is a tradeable `LISTING`; an actual FX forward is a tradeable `INSTRUMENT`.

The node is a stable technical identity. The subtype table holds the business terms appropriate to that type.

## Economic instrument types

All economic instruments have `node_type = INSTRUMENT`; their product nature is governed separately by `instrument_type`.

```text
instrument_type
  instrument_type_id
  type_code                   -- EQUITY, BOND, SWAP, OPTION, ...
  default_asset_class
  description
  status

instrument
  instrument_node_id
  instrument_type_id          -- FK to instrument_type
```

The initial seeded catalogue includes equity, bond, convertible bond, ETF, fund, fund share class, FX forward, forward, future, option, composed option, swap, swaption, FRA, cap, floor, credit default swap, credit index/tranche products, structured product, actively managed certificate, exchange-traded certificate, warrant, right, repo, securities lending, and digital asset.

## Internal taxonomy

Commercial archetypes and desk classifications are neither node types nor instrument types. Use a separate hierarchical taxonomy catalogue and effective-dated assignments.

```text
taxonomy
  taxonomy_id
  taxonomy_code               -- STRUCTURED_PRODUCT_ARCHETYPE, or a future governed internal taxonomy

taxonomy_value
  taxonomy_value_id
  taxonomy_id
  parent_taxonomy_value_id    -- optional hierarchy
  value_code

instrument_taxonomy_assignment
  instrument_node_id
  taxonomy_value_id
  effective_from / effective_to
```

For example, an Athena has `node_type = INSTRUMENT`, `instrument_type = STRUCTURED_PRODUCT`, and the `STRUCTURED_PRODUCT_ARCHETYPE` taxonomy value `ATHENA`. The actual payoff remains defined by the terms, barriers, schedules, and composition. The same generic mechanism remains available for future governed internal taxonomies, but none are seeded by default for swap labels.

## Instrument versus listing

An economic instrument is a financial security or contract: an ordinary share, bond issue, fund share class, future contract, option, swap, or structured product.

A listing is a venue-specific representation of one instrument. It holds MIC, ticker, local exchange code, trading currency, and trading status.

Example:

```text
Instrument node: INS-000842
Instrument: ExampleCo plc ordinary shares

Listing node: SEC-020101
Listing: XLON / EXC / GBX

Listing node: SEC-020102
Listing: XPAR / EXCP / EUR
```

The two listing nodes point to `INS-000842`. A separate share class or depositary receipt is a separate economic instrument, not another listing.

## Core tables

| Table | Responsibility |
|---|---|
| `financial_reference_node` | Stable ID, node type, lifecycle status, audit metadata. |
| `instrument` | Common economic-instrument attributes. |
| `listing` | Venue-specific attributes and owning instrument node. |
| `security_identifier` | Internal and external identifiers on the correct node. |
| `instrument_relationship` | Economic links between instruments/entities. |
| `instrument_dates` | Shared, one-off key dates for economic instruments. |

## Identifiers

Attach identifiers to the correct node.

* Instrument-level examples: internal master ID, ISIN when it identifies the issued security, CFI, and global/vendor security IDs.
* Listing-level examples: ticker, exchange code, local security code, and venue-level vendor IDs.

Treat ticker as venue-scoped and effective-dated; it is never a global key by itself.

## Integration identifiers and external mappings

Every canonical object has an immutable Fortem UUID. External systems must map their own identifiers to that UUID through a governed integration-identity layer; never make an upstream identifier the internal primary key.

Keep two related concepts separate:

* `financial_reference_identifier` is a formal or broadly reusable identifier assignment on a node: ISIN, FIGI, CUSIP, SEDOL, MIC-scoped ticker, RIC, and similar identifiers.
* `external_object_mapping` is a source-namespace mapping: a bank's security key, a custodian asset code, a client's portfolio/security code, a vendor's opaque instrument ID, or an upstream trade/organisation identifier.

```text
external_id_namespace
  namespace ID, source-system/provider organisation, tenant scope nullable,
  namespace code, source kind, status

external_object_mapping
  mapping ID
  namespace ID
  external object type and external ID value
  target object type and Fortem UUID
  mapping role and optional venue/context
  valid-from / valid-to, recorded-at
  mapping status, confidence/verification, source-payload link
  supersedes mapping ID nullable
```

The unique business key is the external namespace plus external object type, external ID, relevant context, and validity/current status. A client may use `ABC-123` for a private asset while a custodian uses the same string for an unrelated holding; their namespaces make this unambiguous.

Use the mapping service for `REFERENCE_NODE`, `ORGANISATION`, `STRATEGY`, `TRADE`, and other UUID-backed objects that cross an integration boundary. The initial database may use a controlled polymorphic target (`target_object_type`, `target_object_id`) with application validation and a database trigger; add specialised mapping tables only where high-volume joins or strict database foreign keys justify them.

## Relationships

Use controlled relationship types, including:

```text
ISSUED_BY
HAS_UNDERLYING
TRACKS_INDEX
SHARE_CLASS_OF
HAS_COMPONENT
CONTRACT_OF
```

The listing-to-instrument connection is a direct foreign key in `listing`, not a redundant generic relationship.

## Canonical definition versioning

The UUID on an instrument or listing is the stable economic/venue identity; it
is not a mutable snapshot of today's terms. Approved changes are appended to
`secm.instrument_definition_version` and
`secm.listing_definition_version`. Each version carries a sequence number,
effective date interval, approval status, source evidence, and steward approval
metadata. A partial unique index permits at most one current approved version
per identity. Historic reads select the one approved version effective on the
requested business date. Existing `instrument` and `listing` rows remain as
compatibility identity/subtype rows during the first migration; backfill and
dual-read cutover are deferred until reconciliation tests exist.
