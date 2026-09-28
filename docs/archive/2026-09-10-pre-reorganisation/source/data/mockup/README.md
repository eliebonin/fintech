# Synthetic mock-up data

This folder contains deliberately synthetic, non-licensed fixtures for local PostgreSQL development, integration tests, API examples, and demos.

The initial HSBC XLON scenario proves that three external identifiers (`ABC`, `FOO`, and `XYZ`) resolve through different namespaces to one Fortem listing UUID, then flow through a licensed dataset, position snapshot, market-data resolution snapshot, and Soft NAV.

The executable loader is `scripts/load_demo_scenarios.py`. It uses fixed UUIDs from `security_master_schema/demo_data.py` and is idempotent. Do not place real client data, vendor data, credentials, or production extracts in this folder.

`multi-asset-instruments.json` documents the additional fixtures loaded by the same script: an OTC bond, a GBP/EUR forward, an expiry-level future and family, and a dated autocall structured product.

`fund-t1-soft-nav.json` documents a fully fictional fund/subscription share-class
scenario. Its official NAV has market date 27 August and is received on 28
August; the versioned tenant policy deliberately selects it with a one-business-
day lag. It proves that a T-1 NAV is selected from the normal immutable market-
data store and frozen in a valuation snapshot, not copied into a separate price
table.

`market-data-cutoff-funds.json` documents the cutoff fixture loaded by the same
script. It adds three-date equity and bond histories, a GBP/USD pair with
separate London and New York cut-specific series, and two tenant fund policies.
The 28 August 2026 examples use 16:00 Europe/London (15:00 UTC) and 16:00
America/New_York (20:00 UTC); observations arriving after the named cut are
present but must not be selected in a historic replay.

`mvp-market-data-portfolios.json` documents the larger console fixture. It
loads US and European equities, bonds, two expiry-level futures, an OTC FX
forward, GBP/USD and EUR/USD cut-specific series, three synthetic providers,
two portfolios, and more than 500 business-day observations per series from
September 2024 through August 2026. The loader generates those observations
deterministically, with explicit dataset and licence provenance, so repeated
runs do not create duplicate rows.

`index-return-profiles.json` documents the synthetic S&P 500 family fixture. It
contains separate price-return and net-total-return index nodes, methodology
rows, generic return-profile references, and corresponding market-data series.

`index-kind-catalogue.json` documents the governed index-kind metadata seeded
in `secm.index_kind_catalogue`. It deliberately separates public
dissemination from methodology ownership, so a public benchmark such as S&P
500 can still be provider-owned.

`crypto-assets.json` documents the synthetic Bitcoin and USD Coin fixtures.
They demonstrate that a cryptoasset can also have a currency role, while
chain-specific deployments remain separate from venue listings. BTC and USDC
also have synthetic Coinbase, Binance, and Kraken listings with venue product
and FIX security identifiers stored at listing level.

The executable fixture also includes a forward-start/reset vanilla call. Its
single versioned `secm.option_terms` row points to a `STRIKE_RESET` schedule;
each scheduled event has a reset rule and an accepted immutable strike fixing.
The fixture demonstrates that a changing strike does not create a new economic
instrument or overwrite the static option terms.

The executable MVP fixture also includes `ETF`, `ETC`, and `ETN` examples. A
single versioned `secm.etp_terms` row captures their common wrapper terms; the
ETF reuses fund/share-class terms and an `ETF_PCF` constituent snapshot, while
the ETC and ETN demonstrate commodity and issuer-reference links. Each has its
own venue listing and synthetic EOD market-data series.
