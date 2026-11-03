# fintech

## Documentation and feature status

Start at the [documentation home](docs/README.md). The maintained
[desired-versus-implemented feature register](docs/product/feature-register.md)
links every feature to its current status, evidence, shortcuts and remaining work.
Historical plans are not current delivery claims.

## Provider-neutral deployment

Source and documentation use neutral platform names. Existing installations
must retain their explicit connection and volume settings; this cleanup does not
rename stored data. See [deployment compatibility and verification](docs/delivery/provider-neutral-repository-20261017.md).

## Local tenant access testing

First complete [private database/runtime setup](docs/platform/security-controls.md#database-setup-and-maintenance).
Then run `.\.venv\Scripts\python.exe scripts/configure_local_access.py` before
the API/frontend launch commands. This writes matching ignored private bootstrap
configuration without printing its key. Headers alone cannot authenticate.
See [local setup and limits](docs/platform/local-identity-safeguard.md).

Open `/select-context` to choose platform administration or a tenant/user.
See [tenant administration, permissions, seed and verification](docs/delivery/tenant-access-administration.md).

## Market data ingestion

Daily ingestion lives in `market_data`, with provider adapters under
`market_data/providers` and operator entry points in `apps/market_data_ingestor`.
The reference API reads stored data; it does not own provider acquisition.

See [module ownership, preserved controls and verification](docs/delivery/market-data-ingestion-boundary.md).
From the repository root, run `python -m apps.market_data_ingestor.yahoo --help`.
The existing `scripts/ingest_yahoo_market_data.py` launcher remains supported.
