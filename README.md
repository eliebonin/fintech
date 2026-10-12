# fintech

## Local tenant access testing

Open `/select-context` to choose platform administration or a tenant/user.
See [tenant administration, permissions, seed and verification](docs/delivery/tenant-access-administration.md).

## Market data ingestion

Daily ingestion lives in `market_data`, with provider adapters under
`market_data/providers` and operator entry points in `apps/market_data_ingestor`.
The reference API reads stored data; it does not own provider acquisition.

See [module ownership, preserved controls and verification](docs/delivery/market-data-ingestion-boundary.md).
From the repository root, run `python -m apps.market_data_ingestor.yahoo --help`.
The existing `scripts/ingest_yahoo_market_data.py` launcher remains supported.
