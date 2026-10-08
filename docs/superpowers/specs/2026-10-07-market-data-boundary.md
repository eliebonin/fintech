# Market data ingestion boundary

The market-data ingestor is a distinct module within the existing repository. It must run without the reference API and accept normalized provider output without knowing Yahoo payload structure. This refactor preserves existing EoD behaviour, rights gates, stored identities and transaction semantics. Live prices, new feeds, reference-data acquisition and valuation remain outside scope.

## Responsibilities and dependencies

- `market_data/contracts.py` owns immutable listing context, provider configuration and normalized daily observations. It depends only on the standard library.
- `market_data/ingestion.py` coordinates rights, delivery identity, listing validation, an injected parser and atomic publication. It imports no provider adapter, API app or network client.
- `market_data/storage.py` owns SQL operations for retained deliveries, mapping validation, series and append-only observations. Existing SQLAlchemy metadata remains in `security_master_schema/models.py`; no table moves or migrations.
- `market_data/rights.py` is shared by ingestion, API readers and the existing resolver. It must not import provider acquisition or ingestion code.
- `market_data/providers/yahoo/adapter.py` owns Yahoo HTTP requests, identity/price semantics and normalization. `onboarding.py` owns the existing operator-only personal catalogue setup.
- `apps/market_data_ingestor/yahoo.py` composes the adapter and ingestion. Its own settings and SQLAlchemy engine replace imports of reference API settings/database lifecycle.
- `scripts/ingest_yahoo_market_data.py` remains a thin compatibility entry point. The existing command-line flags and safety checks remain unchanged.

The API can depend on shared rights, but must not import ingestion, provider adapters or the ingestor app. Ingestion and storage may depend on canonical metadata. This is pragmatic module isolation, not a full persistence-independent domain rewrite.

## Preserved contracts

Caller-owned transactions, dataset locks, delivery hashes and replay conflicts, exact listing scope and venue validation, retained rejection reports, immutable raw deliveries, source lineage, separate Close/Adjusted Close adjustment bases and append-only corrections remain unchanged. Yahoo date, payload and access limits remain unchanged. No download, operating database write, entitlement activation or licence relaxation is part of this refactor.

The normalized point explicitly identifies its series type as well as its original source field. The publisher uses provider configuration and normalized fields rather than branching on Yahoo constants. It remains limited to the existing daily PRICE-series workflow; do not introduce a plugin registry or arbitrary data-type framework.

## Acceptance

Automated import-boundary checks fail if forbidden dependencies return. Runtime tests import the core and run the CLI help with API/provider modules unavailable. A synthetic non-Yahoo parser publishes into a disposable database to prove provider neutrality. Existing parser, rights, ingestion, onboarding, display and resolver tests use the new paths. Both CLI entry points retain nonlocal-target rejection. Run the full Python suite through the isolated database harness, plus OpenAPI freshness and whitespace checks.

## Research and applicability

Reviewed 7 October 2026:

- [Microsoft common web application architectures](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures), updated 7 March 2023: application/core logic should not depend on UI implementations; composition belongs at the entry point. The dependency principle applies here, not its .NET-specific project layout.
- [Martin Fowler Monolith First](https://martinfowler.com/bliki/MonolithFirst.html), 3 June 2015: discovering stable boundaries within a modular monolith avoids premature distributed-system costs. The author describes experience, not a universal rule; our alpha does not need independent ingestion deployment yet.
- [Import Linter forbidden contracts](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/), undated stable documentation: module dependency restrictions can be enforced, including indirect imports. We implement focused AST and blocked-import runtime tests using existing Python/pytest dependencies, rather than adding an import-linter dependency. The directory names and test implementation are project choices.

