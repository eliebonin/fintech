# Macro, commodities, cryptoassets, and exchange-traded wrappers

## Macro indicators

Macro indicators are reference-data-backed economic time series, not instruments, listings, curves, surfaces, or ordinary prices.

```text
macro_indicator
  macro_indicator_id, code, name, geography, publisher_entity_id,
  category, measure, unit, frequency, seasonal_adjustment, status

macro_observation
  macro_observation_id, macro_indicator_id,
  reference_period_start, reference_period_end,
  release_timestamp, value, release_status,
  revision_of_observation_id, source_id, received_at
```

Examples are US CPI-U index level, US CPI-U year-on-year change, US non-farm payrolls, and unemployment rate. `US jobs` is not one indicator; it is a family of separately defined releases.

The reference period and release timestamp are both mandatory concepts. A July CPI value may be released in August and revised later. Do not overwrite the first release. This enables two different questions:

* the latest restated history; and
* the value actually known at a historic timestamp.

The underlying CPI index used contractually by inflation swaps and inflation-linked bonds is an `INFLATION_INDEX` / reference-index object with official fixings. A CPI macro series may link to it, but macro releases and contractual fixings must not be assumed to be the same domain.

## Commodities

Create a non-tradeable `COMMODITY` reference node for an economically precise underlying such as Brent crude, WTI at Cushing, gold, EU gas, or UK power.

```text
commodity_reference_terms
  commodity_group              -- ENERGY / METAL / AGRICULTURE / POWER / EMISSIONS
  commodity_name
  grade_or_quality
  location_or_delivery_point
  unit_of_measure              -- BARREL / TONNE / MWH / TROY_OUNCE
  currency / benchmark conventions
```

Commodity products reuse existing architecture:

| Product/data | Representation |
|---|---|
| Prompt or spot benchmark | Scalar market-data series on the commodity reference. |
| Forward term structure | Generic curve, kind `COMMODITY_FORWARD`; points may have delivery periods. |
| Listed future | Future family, individual expiry instrument, and listing. |
| OTC forward, swap, or option | Economic instrument with terms/legs referencing the commodity, future, or commodity index. |
| Implied volatility | Generic surface. |

Commodity-forward curve points must support a delivery month, quarter, season, or date range as well as an optional tenor. Use `delivery_start_date` and `delivery_end_date` rather than assuming every point is `1M` or `5Y`.

Commodity benchmarks are ordinary `INDEX` nodes. Keep `PRICE_RETURN`, `EXCESS_RETURN`, and `TOTAL_RETURN` variants as distinct index nodes linked by `INDEX_VARIANT_OF`. Their rebalanced constituents use dated snapshots, not contractual payoff composition.

## Cryptoassets

A cryptoasset such as BTC or ETH is one canonical reference node with multiple roles. It is both an economic digital asset/instrument and a currency-like settlement/quote asset. Do not duplicate BTC into separate unlinked currency and instrument identities.

```text
financial_reference_node: BTC
  +-- reference_node_role: INSTRUMENT
  +-- reference_node_role: CURRENCY
  +-- reference_node_role: DIGITAL_ASSET

instrument
  instrument_node_id = BTC
  instrument_type = DIGITAL_ASSET

secm.currency
  reference_node_id = BTC
  currency_code = BTC
  minor_unit = 8
```

The implementation separates asset identity from chain deployment. The parent
asset is represented by the ordinary `DIGITAL_ASSET` instrument node and an
effective-dated `secm.crypto_asset_terms` row:

```text
secm.crypto_asset_terms
  instrument_node_id       -- stable BTC / USDC economic identity
  asset_subtype            -- NATIVE / TOKEN / STABLECOIN / WRAPPED / BRIDGED
  native_symbol
  protocol_name
  issuer_organisation_id   -- nullable for genuinely decentralised assets
  effective_from/to, sequence_no, is_current, status
```

Chain-specific facts belong in one or more `secm.crypto_asset_deployment`
rows, not in the parent terms row:

```text
secm.crypto_asset_deployment
  instrument_node_id
  crypto_network_id        -- FK to governed `secm.crypto_network`
  deployment_kind          -- NATIVE / TOKEN_CONTRACT / WRAPPED / BRIDGED
  contract_address         -- null for a native asset
  token_standard           -- ERC20 / SPL / ...
  on_chain_symbol, decimals, is_canonical
  effective_from/to, is_current, status
```

`secm.crypto_network` is a small governed catalogue for networks such as
Bitcoin mainnet, Ethereum mainnet, Solana mainnet, and Base mainnet. Network
identity is deliberately not inferred from a token symbol or from a venue
ticker. The network's `native_currency_code` is descriptive; the authoritative
currency relationship is still the `secm.currency.reference_node_id` row.

This means BTC has one parent node with both `INSTRUMENT`/`DIGITAL_ASSET` and
`CURRENCY` roles, plus a Bitcoin-native deployment. USDC has one stablecoin
parent node with a USD-pegged currency role and separate Ethereum (ERC-20) and
Solana (SPL) deployments. A wrapped or bridged asset with materially different
issuer, redemption, or bridge risk is a separate parent instrument linked by a
typed relationship; it is not another deployment of the original asset.

The mockup fixture seeds BTC and USDC, their currency-role rows, these network
deployments, and synthetic venue listings. Pair-specific market symbols such
as `BTC-USD` on Coinbase, `BTCUSDC` on Binance, and `USDC/USD` on Kraken use
the existing listing model. The listing's `trading_symbol` is the primary
operational symbol; `TICKER`, `VENUE_PRODUCT_ID`, and `FIX_SECURITY_ID` are
listing-level identifier schemes with venue context.

BTC, WBTC, BTCB, and USDC are separate identities. Wrapped assets may be connected through a typed relationship such as `WRAPPED_REPRESENTATION_OF`; a stablecoin can be `PEGGED_TO` USD but is never the same node as USD.

### Venue markets and derivatives

A crypto venue market can use the listing model:

```text
listing
  instrument_node_id           -- base/traded asset, e.g. BTC
  venue_id                     -- Coinbase / Binance / Kraken
  trading_currency_node_id     -- USD / USDT / ETH
  quote_convention             -- USD_PER_BTC / ETH_PER_BTC
  market_symbol                -- BTC-USD / BTCUSDT
```

| Market | Base instrument | Quote currency |
|---|---|---|
| BTC/USD | BTC | USD |
| BTC/USDT | BTC | USDT |
| ETH/BTC | ETH | BTC |
| BTC/ETH | BTC | ETH |

Crypto operates continuously, so named valuation cuts such as London close, New York close, and internal EOD are especially important; there is no universal natural close.

Crypto futures, options, OTC forwards, and swaps reuse the normal derivatives model. A perpetual future/swap is a dedicated derivative subtype with no maturity and with funding-rate market-data series plus funding schedule terms. Blockchain wallets, transfers, custody, and on-chain balances are outside the security master and belong to a later ledger/custody domain.

## AMC and ETI wrappers

In this notebook, AMC means an actively managed certificate and ETI means an exchange-traded instrument. An AMC is a securitised certificate issued by a legal entity and linked to a managed reference portfolio; it is not a fund or ETF share class.

Use concrete ETF, ETC, ETN, ETV, or ETI economic instrument types and the
generic ETP taxonomy rather than treating `ETP` as a deep universal asset class:

```text
instrument
  instrument_type = EXCHANGE_TRADED_CERTIFICATE

instrument_type
  ETF / ETC / ETN / EXCHANGE_TRADED_VEHICLE / EXCHANGE_TRADED_CERTIFICATE

taxonomy
  EXCHANGE_TRADED_PRODUCT_CLASS = ETF / ETC / ETN / ETV / ETI

secm.etp_terms
  instrument_node_id
  etp_kind
  legal_form
  replication_method
  collateralisation_type
  redemption_model
  distribution_policy
  reference_node_id
  effective-dated version fields
```

An AMC's changing strategy is a separate non-tradeable reference portfolio:

```text
managed_reference_portfolio
  portfolio_node_id, manager_org_id, base_currency_id, valuation_calendar_id

reference_portfolio_constituent_snapshot
  portfolio_node_id, as_of_date, constituent_reference_node_id,
  quantity, weight, cash_component, source_id
```

This is the correct use of dated constituents. It is not `instrument_composition`, which remains reserved for contractual payoff decomposition. The same snapshot pattern can support AMC portfolios, ETF PCFs, and custom baskets.

Market-data placement is explicit:

| Data | Reference level |
|---|---|
| AMC/ETI bid, ask, exchange close | Listing. |
| Issuer NAV or indicative value | Certificate instrument. |
| Managed reference-portfolio NAV | Portfolio/reference node. |
| Price of each underlying holding | Its own listing/instrument/curve series. |

AMC/ETI UCITS treatment is an effective-dated regulatory assessment label. A listed AMC/ETI is not automatically a UCITS fund.

The same common terms boundary now covers ETF, ETC, and ETN. ETFs additionally
reuse `secm.fund` and `secm.fund_share_class_terms`; their PCF or holdings use
`secm.reference_constituent_snapshot` with `snapshot_kind = ETF_PCF`. ETC and
ETN products do not become funds merely because they trade on an exchange. See
the [external evidence register](24-external-evidence-and-research.md) for the
FCA, ESMA, SEC, and Euronext sources supporting these distinctions.

### ETP relationship decisions

The current relationship model is intentionally generic and supports links to
indexes, commodities, futures, swaps, baskets, currencies, and other reference
objects. The following rules are recorded explicitly:

1. `instrument_relationship.relationship_type` will eventually be backed by a
   governed relationship-role catalogue rather than remaining free text.
2. `secm.instrument_relationship` is authoritative whenever an ETP has more
   than one reference, an effective-dated reference change, or distinct roles
   such as `REFERENCE_INDEX`, `UNDERLYING`, and `COLLATERAL`.
3. `secm.etp_terms.reference_node_id` is an optional convenience shortcut for
   one primary reference only. It must not be used to represent the complete
   reference set or to override relationship rows.

These are governance refinements, not blockers for the MVP. ETF constituent
holdings remain in dated `ETF_PCF` snapshots and are not replaced by the
primary-reference shortcut.
