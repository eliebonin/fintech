# Reference Data API contract delivery

The Reference Data API OpenAPI 3.1 document is the source of truth for the
Ops Console's API-shaped TypeScript types. It is exported to
`packages/api-contracts/openapi/reference-data-api.v1.json` and generated into
`packages/api-contracts/src/generated.ts` with `openapi-typescript`.

The `api-contracts` workspace package also exports small compatibility aliases
derived from generated schemas, plus an `openapi-fetch` client factory. The
Ops Console consumes that package directly; it does not maintain a copied API
payload type module. Display-only models may add UI behaviour, but must retain
the API's nullable and extensible-string fields.

## Regeneration

Use the repository virtual environment and the locked Node workspace:

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi_contract.py
pnpm contract:generate
```

Verify that checked-in artifacts match runtime schema output:

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi_contract.py --check
pnpm contract:generate:check
```

`openapi-typescript` is pinned to `7.10.1`. The root pnpm override pins
`@redocly/openapi-core` to `1.34.19`: `1.34.20` was observed to omit a runtime
module required by its own loader on this workspace. Keep both pins until the
upstream package is verified fixed, then update them together and rerun the
generation checks.

## Dependency and CI policy

Python production dependencies are compiled under Python 3.12 from
`requirements.in` to hashed `requirements.lock`. CI installs only that lock
with `--require-hashes`. To deliberately update it:

```powershell
.\.venv\Scripts\pip-compile.exe --generate-hashes --resolver=backtracking --output-file requirements.lock requirements.in
```

The quality workflow runs contract freshness, Python tests, TypeScript
generation/typechecking/tests, the Ops Console checks, and Gitleaks. GitHub
native secret scanning and push protection must also be enabled in repository
settings; they cannot be enabled by a checked-in workflow.
