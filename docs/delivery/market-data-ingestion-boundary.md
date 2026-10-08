# Market data ingestion boundary

**Status:** Implemented and locally verified  
**Owner:** Market-data engineering  
**Reviewed:** 2026-10-07

Market-data intake is now a distinct `market_data` package and operator app. It no longer imports the reference API's adapter, settings or engine lifecycle. The existing Yahoo daily-equity workflow and database identities are preserved; this refactor does not acquire data or expand source permissions.

## Module ownership

| Module | Responsibility |
| --- | --- |
| `market_data/contracts.py` | Immutable provider specification, listing context and normalized points; standard library only |
| `market_data/ingestion.py` | Rights, idempotency, validation and publication orchestration; no HTTP or provider import |
| `market_data/storage.py` | Listing/mapping checks, raw delivery retention, vintages, series and observation SQL |
| `market_data/rights.py` | Shared acquisition, storage and consumption rights; no provider or ingestion dependency |
| `market_data/providers/yahoo/adapter.py` | Bounded daily-chart HTTP, source identity validation and Yahoo semantics |
| `market_data/providers/yahoo/onboarding.py` | Operator-only personal catalogue, seeded mappings and layered prerequisites |
| `apps/market_data_ingestor/config.py` | `DATABASE_URL` and `APP_ENV`, independent of API settings |
| `apps/market_data_ingestor/yahoo.py` | Composition root choosing the Yahoo adapter and generic publisher |
| `scripts/ingest_yahoo_market_data.py` | Compatibility launcher; existing flags preserved |

Canonical tables/migrations remain in `security_master_schema` and Alembic. API readers and the existing resolver import shared rights, not acquisition code. No queue, scheduler, microservice, plugin registry or runtime dependency is introduced.

## Data flow and preserved behaviour

The operator app checks acquisition/storage rights before fetching. The adapter returns exact bounded source text. Generic ingestion locks the dataset, rechecks rights, handles delivery replay, validates the mapped listing and calls the injected parser with currency, MIC and timezone. Normalized points explicitly carry series type, source field, adjustment basis and timestamp semantics. Storage publishes accepted observations and linked revisions, then records immutable raw text, rights evidence and outcome within the caller-owned transaction.

An undeclared series type is rejected before mapping verification or publication, with retained rejection evidence. Shared contracts have no Yahoo-specific adjustment/timestamp defaults. Yahoo Close/Adjusted Close codes, source keys, vintages, precision, replay conflicts, tenant checks, exact raw text and correction relationships remain unchanged.

This is a boundary for the existing daily PRICE-series flow, not a universal data framework. Another adapter is selected explicitly at a composition root. Market-reference ingestion, authoritative sessions/calendars, historical identifier continuity, live data and valuation/P&L remain separate work.

## Operator compatibility

Both entry points expose the same flags and local-target safety checks:

```powershell
.venv/Scripts/python.exe -m apps.market_data_ingestor.yahoo --help
.venv/Scripts/python.exe scripts/ingest_yahoo_market_data.py --help
```

`DATABASE_URL` and `APP_ENV` retain their meanings. Preview still rolls back and never downloads; initialize-only never downloads. No acquisition command was run during this refactor. `AUTOMATED_SOURCE_ACCESS` remains unresolved and the previously observed Yahoo HTTP 429 remains unchanged. See the [Yahoo delivery report](yahoo-market-data-alpha.md).

Old internal Python import paths have been replaced, not kept as duplicate implementations. Repository consumers/tests use the new paths; the operator script path is preserved. External code importing former internal modules would need to update its imports.

## Best practice evidence and decisions

Sources opened and reviewed on 7 October 2026:

| Primary source | Guidance and application |
| --- | --- |
| [Microsoft common web application architectures](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures), updated 7 March 2023 | Core logic should not depend on UI implementations; composition belongs at the entry point. Applied to Python dependencies, not copied as .NET scaffolding. |
| [Martin Fowler Monolith First](https://martinfowler.com/bliki/MonolithFirst.html), 3 June 2015 | Experience-based case for learning module boundaries before distributing services. Keeping this repository/database is our alpha-specific choice, not a prohibition on future workers. |
| [Import Linter forbidden contracts](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/), undated stable documentation | Dependency restrictions can be enforced. Focused AST rules and blocked-import runtime tests enforce our boundary with existing pytest; import-linter itself was not installed. |

The skill's check influenced dependency direction, explicit adapter contracts and executable architecture checks. This is pragmatic SQLAlchemy-backed isolation, not fully persistence-independent Clean Architecture.

## Verification

Boundary tests import ingestion/rights with API, HTTP and provider modules unavailable. Both CLI entry points show help without the API and reject nonlocal targets before connection/network access. A synthetic second-provider parser publishes its own field, series code, source ID, vintage basis and timestamp semantics into a disposable database. Its undeclared-series variant retains a rejection without verifying mappings or writing observations.

Existing regressions cover source identity/prices, replay, revisions, raw evidence, immutability, tenant privacy, display/non-display rights, API paging and onboarding. Database checks exclusively use UUID-owned disposable databases through `scripts/run_isolated_python_tests.py`, never operating trades, observations, mappings or entitlements.

Initial baseline: 31 pure tests passed. After extraction: 37 pure tests and 65 focused isolated tests passed. After the normalized-series guard and explicit metadata contract, a fresh focused isolated run passed **66 tests in 21.05s**. The full isolated Python suite passed **1,009 tests, 491 warnings, in 759.01s (12m39s)**, exit code zero. SQLAlchemy/Starlette deprecation and Pydantic header/parameter metadata warnings remain; passing is not warning-free.

OpenAPI freshness, compilation of the new packages and whitespace checks passed. The full diagnostic output is retained in `logs/market-data-boundary-full-python.log`. Frontend code and generated API contracts are unchanged by this refactor; no browser acceptance or production build is claimed.

Verification commands:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_market_data_boundaries.py tests/test_market_data_rights.py tests/test_yahoo_market_data.py tests/test_yahoo_market_data_cli.py tests/test_market_data_ingestion.py tests/test_market_data_display_rights.py tests/test_yahoo_market_data_onboarding.py tests/test_mvp_market_data_api.py -q --tb=short
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py -q --tb=short --durations=15
.venv/Scripts/python.exe scripts/export_openapi_contract.py --check
.venv/Scripts/python.exe -m compileall -q apps/market_data_ingestor market_data scripts/ingest_yahoo_market_data.py tests/test_market_data_boundaries.py
git -c core.autocrlf=false diff --check
```

Review is sequential self-review by the author, as requested, not independent reviewer sign-off. No commits, merge or push are part of this delivery.

See the [specification](../superpowers/specs/2026-10-07-market-data-boundary.md) and [execution plan](../superpowers/plans/2026-10-07-market-data-boundary.md).
