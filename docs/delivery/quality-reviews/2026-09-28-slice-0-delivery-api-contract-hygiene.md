# Slice 0 delivery/API contract hygiene — verification record

**Recorded:** 2026-09-28  
**Scope:** Reference Data API contract, error boundary, generated TypeScript
consumer package, CI and repository hygiene.

## Delivered artifacts

- OpenAPI input: `packages/api-contracts/openapi/reference-data-api.v1.json`
- Generated TypeScript: `packages/api-contracts/src/generated.ts`
- Public typed client and derived compatibility aliases:
  `packages/api-contracts/src/client.ts` and `src/reference-data.ts`
- RFC 9457 API error boundary: `apps/reference_api/problem_details.py`
- Quality workflow: `.github/workflows/quality.yml`
- Secret-scan configuration: `.gitleaks.toml`

The Ops Console's prior copied `reference-api-types.ts` module was removed.
Its API-shaped payload types now come from `api-contracts`. Browser calls remain
behind the BFF; no tenant headers are exposed to browser code.

## Fresh local evidence

On the repository Python 3.12.14 virtual environment, Node 23.9.0, and pnpm
10.7.1, the following commands exited successfully:

| Command | Result |
| --- | --- |
| `python -m compileall apps packages scripts tests` | Success |
| `python -m pytest tests/test_openapi_contract.py tests/test_reference_api_problem_details.py tests/test_reference_api_boundary.py tests/test_delivery_hygiene.py -v` | 12 passed |
| `python scripts/export_openapi_contract.py --check` | Success |
| `pnpm contract:generate:check` | Success |
| `pnpm --filter api-contracts test` | 2 passed |
| `pnpm --filter api-contracts typecheck` | Success |
| `pnpm --filter ops-console test` | 110 passed across 35 files |
| `pnpm --filter ops-console typecheck` | Success |
| `pnpm --filter ops-console build` | Success |
| `python -m pip install --dry-run --require-hashes -r requirements.lock` | Success; no installation performed |

The full Python suite previously stalled after collecting 224 tests, so this
record does not assert a full-suite pass. The focused tests cover Slice 0's
error, contract export, hygiene, and BFF Problem Details boundary.

## CI safeguards and external controls

The workflow has top-level `contents: read` only, does not use
`pull_request_target`, and pins checkout, Python setup, Node setup, and
Gitleaks to full immutable SHAs. It runs Python 3.12 from the hashed lock,
Node 24 with frozen pnpm installation, contract freshness, tests, build, and
history-aware Gitleaks scanning.

GitHub Secret Scanning and Push Protection are repository administrator
settings, not source-controlled configuration. Enable both after these files
are committed/pushed, then confirm the first `Quality` workflow run succeeds.

## Outstanding follow-ups

The baseline is now committed and pushed as `b38e59d`; the earlier repository
baseline blocker is resolved. The remaining work is deliberately outside the
completed local Slice 0 implementation:

1. **Run and inspect GitHub Quality.** Confirm the first remote `python`,
   `web`, and `secrets` jobs pass on `main`. This validates the pinned-action
   workflow in GitHub's environment, including Gitleaks history scanning.
2. **Enable GitHub Secret Scanning and Push Protection.** A repository
   administrator must enable both controls in GitHub settings. The checked-in
   workflow cannot configure them.
3. **Diagnose the full Python-suite stall.** `pytest -v` previously collected
   224 tests without completing. Identify the blocking test/dependency and
   make the suite reliably finish, or split integration tests into a
   separately provisioned and bounded CI job.
4. **Review the generator exception during dependency maintenance.** Keep
   `openapi-typescript` 7.10.1 and the `@redocly/openapi-core` 1.34.19 override
   until a controlled upgrade regenerates the contract and passes the stated
   checks.

## Toolchain exception

`openapi-typescript` is pinned to 7.10.1 and the pnpm override pins
`@redocly/openapi-core` 1.34.19. The immediately newer 1.34.20 package lacked
a runtime module required by its own loader in a clean local installation;
generation then failed. Update the pair only after regenerating and running
the checks listed above.
