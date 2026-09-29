# Replay-safe Market Data resolution verification

**Date:** 2026-09-29  
**Scope:** persisted, tenant-scoped Market Data selection snapshots; generated API contract; minimal Ops Console frozen-evidence journey.

## Verified behaviours

- Historic eligibility requires UTC information cuts, provider publication and platform receipt timing, and correction timing at the same cut.
- Snapshots retain immutable selection outcome, ordering, policy rule, entitlement decision, observation, vintage, dataset, licence, publication and receipt evidence.
- Snapshot POST is tenant-scoped and idempotent; exact retries replay while conflicting key reuse returns `idempotency.key_reused`.
- Snapshot reads use persisted rows only; current entitlement is not re-evaluated.
- The OpenAPI document is exported from FastAPI and TypeScript is generated from it.
- The Ops Console submits a one-subject command only through the server BFF, derives the permitted valuation cut from an active policy retrieved through that BFF, and displays frozen evidence through the read BFF.

## Commands and evidence

| Command | Result |
| --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests/test_market_data_vintages.py tests/test_market_data_resolver.py tests/test_market_data_cutoff_scenarios.py tests/test_market_data_resolution_snapshot_schema.py tests/test_reference_api_market_data_resolution_repository.py tests/test_reference_api_market_data_resolution.py -q` | Completed against local PostgreSQL; terminal relay lost the final pytest summary after the test process exited. Earlier focused groups were green: resolver 11, repository 6, HTTP 4. |
| `.venv\\Scripts\\python.exe scripts\\export_openapi_contract.py --check` | Passed after generated-contract commit. |
| `pnpm --filter api-contracts test` | 3 files / 3 tests passed. |
| `pnpm --filter api-contracts typecheck` | Passed. |
| `pnpm --filter ops-console test` | 36 files / 115 tests passed, including the frozen-evidence request builder, outcome/timestamp presentation, and active-policy-to-cut selection. |
| `pnpm --filter ops-console typecheck` | Passed. |
| `pnpm --filter ops-console build` | Passed; includes the snapshot read/write and active-valuation-policy BFF routes. |

Schema revisions: `20260928_46` freezes evidence/idempotency; `20260929_47` adds immutable item outcome and request order.

## Deliberate exclusions

This slice does not add live vendor ingestion, a market-data write API, generic policy DSL, provider-calendar onboarding, portfolio-scale orchestration, or Soft-NAV/P&L consumption changes.
