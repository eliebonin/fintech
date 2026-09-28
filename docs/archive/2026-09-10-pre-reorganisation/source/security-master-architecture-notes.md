# Financial Instrument Security Master

## Purpose and scope

This document records the agreed architectural direction for a PostgreSQL-backed, canonical reference-data master for financial instruments. Its first release is a source of truth for instrument identity, terms, listings, identifiers, relationships, and market-reference metadata. It will later support trades and marked data, but it is not initially a pricing engine, position engine, or valuation engine.

For the current cross-project product context, shared/tenant data boundary,
market-data licensing constraints, and current delivery focus, see
[`docs/architecture/spineoff-context-and-knowledge-transfer-2026-09-09.md`](docs/architecture/spineoff-context-and-knowledge-transfer-2026-09-09.md).

The asset universe includes currencies, indices, equities, bonds, ETFs, AMCs, funds and fund share classes, FX forwards, swaps, vanilla options, structured products, composed options, and futures.

Operations creates a canonical record when required. External vendors and internal systems enrich the record, provide source lineage, and may propose changes. The canonical record remains governed by operations.

## Current implementation checkpoint (2026-09-10)

The current repository implements a broad reference-data and operations
prototype, including PostgreSQL models, migrations, market-data provenance,
tenant metadata, Soft-NAV evidence tables, trade lifecycle records, and a
Next.js operations console. The cross-layer assessment is recorded in
[`docs/architecture/global-db-api-frontend-review-2026-09-10.md`](docs/architecture/global-db-api-frontend-review-2026-09-10.md).

The most important remaining work is enforceable behaviour: authenticated
tenant routing/RLS, calendar-aware point-in-time market-data replay, a safe
current-version promotion path, complete Soft-NAV cross-currency evidence, and
generated API/frontend contracts. These are control work, not a reason to
replace the node/instrument/listing model or add another generic price table.

Earlier sections of this document use the historical name `security_price` for
the common price boundary. The implemented names are
`md.market_data_series` and `md.market_data_observation`; the historical
description should be read with that mapping.

## Core identity model

The model separates three ideas:

1. **Economic instrument** -- the financial contract or security itself.
2. **Listing** -- a venue-specific, tradeable representation of an economic instrument.
3. **Financial reference node** -- a common technical identity that can be referenced by trades, market data, and contract legs.

The preferred implementation is a hybrid node model:

```text
financial_reference_node
  one universal UUID for an economic instrument, listing, rate index, index,
  FX pair, curve, or other market reference

instrument
  one-to-one subtype for an ECONOMIC_INSTRUMENT node

listing
  one-to-one subtype for a LISTING node; points to its instrument node
```

This avoids both extremes: two separate price tables, or a single wide undifferentiated instrument table. Prices and legs use one foreign key to `financial_reference_node`, while `instrument` and `listing` retain clear business semantics.

### Example: cross-listed equity

```text
Instrument node: INS-000842
Instrument: ExampleCo plc ordinary shares

Listing node: SEC-020101
Listing: ExampleCo on XLON, ticker EXC, trading currency GBX

Listing node: SEC-020102
Listing: ExampleCo on XPAR, ticker EXCP, trading currency EUR
```

There is one economic instrument and two listing records. A listing is not itself the canonical security. A separately issued share class, depositary receipt, or other distinct legal/economic security is instead a separate instrument.

### Table responsibilities

| Table | Responsibility |
|---|---|
| `financial_reference_node` | Stable universal identity and node type. |
| `instrument` | Common economic-instrument data: canonical name, instrument type, lifecycle status, issuer, and similar shared attributes. |
| `listing` | Venue-specific data: MIC, ticker, trading currency, trading status, and its owning economic instrument. |
| `security_identifier` | External and internal identifiers attached to the appropriate node. |
| `instrument_relationship` | Explicit links between instruments and entities, such as underlying, issuer, share class, component, or tracked index. |
| `md.market_data_series` / `md.market_data_observation` | Precise market-data series definitions and immutable observations, each pointing to exactly one reference node. |

## Identifiers and relationships

Identifiers attach at the correct level:

* Instrument-level: internal ID, ISIN when it identifies the issued security, CFI, and global/vendor security identifiers.
* Listing-level: venue ticker, local exchange code, venue-level FIGI, and other venue-specific identifiers.

The ticker is not globally unique. Its identity is effectively the combination of venue/MIC, ticker, and validity period.

`instrument_relationship` is for economic links rather than duplicated attributes. Typical relationship types include:

* `ISSUED_BY` -- instrument to legal entity;
* `HAS_UNDERLYING` or `PERFORMANCE_REFERENCE` -- derivative to an instrument or index;
* `TRACKS_INDEX` -- ETF to index;
* `SHARE_CLASS_OF` -- fund share class to fund;
* `HAS_COMPONENT` -- composed option or structured product to component instruments;
* `CONTRACT_OF` -- a future contract to its future family.

The instrument-to-listing link is maintained directly by `listing.instrument_node_id`, not duplicated as a generic relationship.

## Price and market-data rule

Use one `security_price` table. Every row references a single `financial_reference_node_id`.

```text
security_price
  security_price_id
  financial_reference_node_id
  as_of_timestamp
  price_type
  price_value
  price_currency
  source_id
  source_timestamp
  quality_status
```

The rule is:

* An official venue close, last trade, bid, ask, or volume observation is stored against the **listing node**.
* An OTC evaluated price, vendor composite, or internal end-of-day valuation price is stored against the **economic-instrument node**.
* FX pairs, curves, volatility surfaces, rate indices, and index levels use their own reference nodes rather than pretending to be listed securities.

For example, XLON and XPAR closes for the same equity are distinct listing-level observations. An internal GBP mark derived from the XLON close and FX is an instrument-level observation with documented lineage.

Price types must distinguish source and economic meaning, for example:

```text
OFFICIAL_VENUE_CLOSE
VENUE_LAST
COMPOSITE_CLOSE
EVALUATED_CLEAN_PRICE
INTERNAL_EOD_MARK
```

No automatic mixing of venue prices is permitted. Any fallback to a composite or internal instrument-level price must be an explicit valuation policy.

## Trades and marks

A trade always has an economic identity. For listed execution, it also retains the exact listing node.

```text
trade
  economic_instrument_node_id   -- required
  execution_reference_node_id   -- listing node when venue execution matters; null for OTC
```

Examples:

* OTC bond, swap, FX forward, bespoke option, or structured-product trade: economic instrument node only.
* Exchange-traded equity, ETF, future, or listed option: economic instrument node plus listing node.

Market marks are separate from raw observations. A mark records a trade or position value at an as-of time, valuation method, selected inputs/snapshot, currency, status, and reproducible lineage. It must not overwrite raw vendor or official venue prices.

## Asset-specific terms

`instrument` contains only common attributes. Contractual terms live in one-to-one, asset-specific tables keyed by the economic instrument node:

```text
bond_terms
option_terms
future_terms
fx_forward_terms
swap_terms
structured_product_terms
fund_share_class_terms
```

The rule is:

* `x_terms` holds terms that define **one exact economic instrument**.
* `x_family` holds shared specification for **multiple distinct instruments** and is not itself tradeable or priceable.

Examples:

* A bond issue normally needs `bond_terms` only; no bond family is required.
* A fund is a vehicle-level record; each tradeable share class is an economic instrument with `fund_share_class_terms` and a relationship to the fund.
* Structured and composed products use their terms plus explicit component/underlying relationships.

### Structured-product contractual graph

`structured_product_terms` is the versioned parent-contract anchor. Its
`structured_product_terms_id` owns the condition groups, typed composition
occurrences, component payoff terms, and coupon programmes/periods for that
version. `composition_value` is interpreted by its governed
`composition_value_kind` (`SIGNED_MULTIPLIER`, `PERCENT_WEIGHT`, `QUANTITY`, or
`NOTIONAL_AMOUNT`), not by the ambiguous legacy `composition_rate` label.

`structured_product_condition_group` owns observation style, schedule event,
Boolean operator, underlying scope, and group ordering. `barrier_rule` is an
atomic member with an explicit resolved underlying node; `condition_group_action`
executes once and can target the parent or an exact composition occurrence,
including payout metadata. Component barriers derive their contractual
underlying from child terms; parent lifecycle barriers use explicit parent
composition/reference entries. This is documented in the
[structured-product condition-group note](security-master-notes/26-structured-product-condition-groups.md).

The schema stores coupon memory configuration and component payout terms, but
calculated condition outcomes, coupon ledgers, projected cashflows, and exotic
pricing remain separate deferred valuation work.

## Futures

A future family is a non-tradeable contract template, not an instrument and not a listing. It contains common exchange/product rules such as underlying, multiplier, expiry cycle, settlement convention, contract currency, and rulebook.

Each expiry is a separate economic instrument because it has a distinct expiry, last-trade date, settlement date, price, trade, and position.

```text
future_family: Example Equity Index Future
  |
  +-- INS-FUT-MAR-27: March 2027 future contract
  |     +-- SEC-FUT-MAR-27-XEUR: listing on XEUR
  |
  +-- INS-FUT-JUN-27: June 2027 future contract
        +-- SEC-FUT-JUN-27-XEUR: listing on XEUR
```

`future_terms` connects an individual future contract to `future_family`. A continuous future is not an instrument; it is a derived market-data series with a specified roll rule.

## Swaps

All examples labelled internally as ABC, XYZ, or FOO remain canonically `SWAP` instruments. The differences in economics are expressed in their legs and references, not by making them unrelated top-level instrument types.

Canonical classification should have at most three levels:

```text
1. Asset class / risk domain
2. Product type: SWAP
3. Economic payoff subtype: e.g. structured return swap, index total-return swap, asset swap
```

ABC, XYZ, and FOO are governed internal product labels, stored in a taxonomy rather than in the canonical instrument type.

```text
product_taxonomy
  product_type_id, taxonomy, code, name

instrument_product_classification
  instrument_node_id, product_type_id, classification_role, valid_from, valid_to
```

An instrument can therefore be classified independently under an internal product taxonomy, canonical product taxonomy, risk taxonomy, and regulatory taxonomy.

### Swap terms and legs

The preferred canonical model is an extensible leg model:

```text
swap_terms
  instrument_node_id              -- the swap contract

swap_leg
  swap_leg_id
  swap_instrument_node_id
  leg_number
  leg_role                        -- PERFORMANCE, FUNDING, COUPON, PROTECTION
  pay_receive
  reference_node_id               -- instrument, listing, rate index, index, FX pair, etc.
  spread
  currency
  calculation and reset conventions
```

This is more extensible than a fixed two-column swap table and supports multiple funding legs, baskets, multiple underlyings, fees, protection legs, and restructuring events.

The existing simple model maps directly to two leg rows:

| Existing field | Canonical interpretation |
|---|---|
| `instrument_id` | Swap contract economic instrument node. |
| `funded_instrument_id` | Performance reference node. |
| `funding_instrument_id` | Funding reference node. |
| `spread` | Funding-leg spread. |

A compatibility view called `info_swaps` may expose the simple two-leg shape for operations, but it should be derived from the canonical leg records.

If a swap is on performance of a specific listing, its performance leg references the listing node. It also records return type, observation rule, calendar, currency/FX conversion rule, and corporate-action adjustment treatment. A performance swap on an economic instrument rather than a named listing uses the instrument node and an explicit composite/primary-market valuation policy.

## Instrument dates and schedules

The agreed approach is a wide, one-to-one `instrument_dates` table for singular, cross-asset key dates. This makes fields such as maturity date easy to query consistently across asset classes.

```text
instrument_dates
  instrument_node_id
  issue_date
  effective_date
  first_trading_date
  last_trading_date
  strike_determination_date
  expiry_date
  maturity_date
  termination_date
  final_valuation_date
  final_settlement_date
  cash_settlement_date
```

Dates that are singular, broadly meaningful, and often queried belong here. Use unambiguous names rather than generic `trading_date` or `settlement_date`.

Do not confuse these economic dates with reference-data version validity. The latter belongs in `valid_from` and `valid_to` fields on versioned reference-data records.

Repeating coupon payments, swap reset dates, fixing dates, and autocall observation schedules belong in dedicated schedule tables. They should not be represented as many nullable date columns or collapsed into the key-dates table.

## Identifier standard

The agreed internal primary-key standard is UUIDv7:

```sql
id uuid PRIMARY KEY DEFAULT uuidv7()
```

This applies to nodes, instruments, listings, terms, legs, identifiers, taxonomy records, trades, and price observations. Retain normal `created_at` and `updated_at` timestamp columns; UUID timestamps are not audit evidence.

UUIDs are identifiers, not authorization secrets. Access must be controlled by authorization and data-entitlement rules, never merely by knowledge of an ID. The timestamp ordering in UUIDv7 can reveal approximate record creation time, so externally exposed APIs may use separate opaque public identifiers if that leakage becomes commercially sensitive.

## Decisions made

* PostgreSQL is the target store.
* First release is a canonical reference-data master.
* Operations creates canonical instruments; vendor and internal sources enrich with lineage.
* Use the hybrid `financial_reference_node` / `instrument` / `listing` model.
* Use one price table keyed by a single reference node.
* Use future families for contract chains; each expiry is a distinct economic instrument.
* Use generic swap legs as canonical data, with a simple compatibility view for common two-leg swaps.
* Store internal labels such as ABC, XYZ, and FOO in a product taxonomy mapping.
* Use UUIDv7 internal IDs.
* Use wide `instrument_dates` columns for shared one-off dates, plus separate schedule tables for recurring events.

## Design work still open

* Exact identifier, source-provenance, and golden-record/versioning model.
* Legal entity, issuer, fund, AMC, currency, index, rate-index, curve, and FX-pair reference models.
* Exact market-data schema, source priority, quality controls, and valuation selection policy.
* Trade lifecycle, book, portfolio, legal-entity, counterparty, and position model.
* Detailed schedule and cashflow model.
* Exact asset-specific term schemas and controlled vocabularies.
* Effective-dating, audit, correction, and approval workflows.
