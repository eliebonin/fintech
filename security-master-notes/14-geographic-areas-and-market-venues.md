# Geographic areas and market venues

## Geographic areas

Countries are one type of geographic or jurisdictional area. The model must also represent `WORLD`, continents, subregions, supranational groups, and internal reporting groups.

```text
geographic_area
  geographic_area_id
  area_code
  display_name
  official_name
  area_type                    -- WORLD / CONTINENT / SUBREGION /
                               -- COUNTRY_TERRITORY / SUPRANATIONAL / INTERNAL_REGION
  status
  valid_from
  valid_to
  source_id

country_terms
  geographic_area_id           -- one-to-one; COUNTRY_TERRITORY only
  iso3166_1_a2                 -- CHAR(2), unique
  iso3166_1_a3                 -- CHAR(3), unique
  iso3166_1_numeric            -- CHAR(3), preserves leading zeroes

geographic_area_membership
  child_area_id
  parent_area_id
  relationship_type            -- GEOGRAPHIC_PART_OF / POLITICAL_MEMBER_OF /
                               -- INTERNAL_CLASSIFICATION
  effective_from
  effective_to
```

Example hierarchy and membership:

```text
WORLD -> EUROPE -> WESTERN_EUROPE -> GERMANY
WORLD -> EUROPE -> EASTERN_EUROPE -> HUNGARY
EUROPEAN_UNION -> GERMANY          (POLITICAL_MEMBER_OF)
EUROPEAN_UNION -> HUNGARY          (POLITICAL_MEMBER_OF)
```

This avoids treating the EU, Europe, or World as countries. Country/subregion reporting views can expose a simple `region_global` and `region_subregion` representation where desired.

## Market venues: one model for traditional and crypto markets

The canonical table is `market_venue`, not `exchange`. A market venue can be a traditional exchange, a MIC market segment, an MTF/OTF, a centralised crypto exchange, a decentralised exchange/protocol, or another execution/pricing venue.

```text
market_venue
  market_venue_id              -- UUIDv7
  venue_code                   -- stable internal code, unique
  venue_name
  venue_kind                   -- REGULATED_EXCHANGE / MARKET_SEGMENT / MTF / OTF /
                               -- CEX / DEX / OTC_PLATFORM / APA / OTHER
  venue_asset_scope            -- MULTI_ASSET / EQUITIES / DERIVATIVES / CRYPTO / ...

  operating_market_venue_id    -- self-FK; parent where this is a market segment
  operating_entity_org_id      -- legal operator, nullable for DEX/protocol
  blockchain_network_node_id   -- nullable; relevant for DEX/protocol

  primary_country_area_id      -- nullable; do not invent one for decentralised venues
  city                         -- nullable
  timezone                     -- IANA; nullable only when genuinely not applicable
  market_calendar_id           -- nullable FK to cal.market_calendar; 24x7 crypto venues may use a 24x7 calendar

  status                       -- ACTIVE / INACTIVE / EXPIRED / SUSPENDED
  valid_from
  valid_to
  source_id
  source_comment
```

Use a separate identifier table. An ISO MIC is important but cannot be mandatory because many crypto venues have no MIC.

```text
market_venue_identifier
  market_venue_identifier_id
  market_venue_id
  identifier_scheme            -- ISO_10383_MIC / EXCHANGE_SLUG / VENUE_API_ID /
                               -- INTERNAL / DEX_PROTOCOL_ADDRESS / ...
  identifier_value
  is_primary
  valid_from
  valid_to
  source_id
```

Enforce uniqueness on `(identifier_scheme, identifier_value, valid_to/current status)` rather than on a nullable `mic` column. A view may expose the current ISO MIC for traditional-market integrations.

### Traditional MIC example

```text
market_venue
  venue_code = XLON
  venue_kind = REGULATED_EXCHANGE
  operating_market_venue_id = null
  primary_country_area_id = UNITED_KINGDOM
  timezone = Europe/London

market_venue_identifier
  scheme = ISO_10383_MIC, value = XLON, is_primary = true

market_venue
  venue_code = AIMX
  venue_kind = MARKET_SEGMENT
  operating_market_venue_id = XLON venue ID
  primary_country_area_id = UNITED_KINGDOM

market_venue_identifier
  scheme = ISO_10383_MIC, value = AIMX, is_primary = true
```

Expired segment MICs remain active reference records with `status = EXPIRED`; they are never deleted because historic listings, prices, and trades may use them.

### Crypto examples

```text
Centralised crypto exchange
  venue_code = COINBASE_EXCHANGE
  venue_kind = CEX
  operating_entity_org_id = Coinbase legal operator where known
  primary_country_area_id = applicable operating jurisdiction where known
  timezone = UTC
  market_calendar = CRYPTO_24X7
  identifier: EXCHANGE_SLUG = coinbase

Decentralised protocol
  venue_code = UNISWAP_V3_ETHEREUM
  venue_kind = DEX
  operating_entity_org_id = null
  blockchain_network_node_id = ETHEREUM
  primary_country_area_id = null
  timezone = UTC
  market_calendar = CRYPTO_24X7
  identifier: DEX_PROTOCOL_ADDRESS = authoritative contract/protocol identity
```

For a centralised crypto venue, `BTC/USD on Coinbase` is a listing/venue market:

```text
listing
  instrument_node_id = BTC       -- base/traded asset
  market_venue_id = COINBASE_EXCHANGE
  trading_currency_node_id = USD -- quote asset
  quote_convention = USD_PER_BTC
  market_symbol = BTC-USD
```

For a DEX, the tradable price source is often a liquidity pool rather than a conventional listing. Do not force a pool into `listing` if it lacks a stable listed-security concept. Add `liquidity_pool` only when DEX trading/valuation becomes operational scope; it can link two digital-asset nodes, a DEX venue, protocol/pool address, fee tier, and blockchain network.

## Jurisdictions and regulated status

A venue's country is not always its regulatory jurisdiction. Keep the simple `primary_country_area_id` for V1 and add this relationship when compliance scope requires it:

```text
market_venue_jurisdiction
  market_venue_id
  geographic_area_id
  jurisdiction_role            -- OPERATION / INCORPORATION / REGULATION / LICENSING
  effective_from
  effective_to
```

This avoids falsely assigning a DEX a country and accommodates global crypto venues with multiple licensed entities.

## Calendar domain boundary

Calendars are cross-cutting operational reference data rather than securities. They
therefore live in the dedicated `cal` schema:

```text
cal.market_calendar
cal.market_calendar_session
cal.market_calendar_holiday
```

`md.valuation_cut` remains in the market-data schema because it describes a
valuation convention. It references a calendar in `cal`. Security-master venues,
contractual schedules, and tenant valuation-policy rules may also reference the
same calendar without duplicating holiday or session data.
