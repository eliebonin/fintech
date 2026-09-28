# Slice 0 Delivery and API Contract Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Make the Reference Data API a versioned, generated TypeScript contract with safe standard errors and a reproducible, least-privilege quality gate.

**Architecture:** FastAPI remains the source of truth. A small API-boundary module owns problem responses, request IDs, response logging, and OpenAPI post-processing; a deterministic export then drives a separate workspace contract package. The existing Ops Console BFF stays responsible for tenant-context propagation, but imports its API types and typed transport from api-contracts instead of duplicating schema models.

**Tech Stack:** Python 3.12, FastAPI/OpenAPI 3.1, HTTPX/pytest, TypeScript, pnpm 10.7.1, openapi-typescript, openapi-fetch, Next.js/Vitest, GitHub Actions, Gitleaks.

**Spec:** [docs/superpowers/specs/2026-09-28-slice-0-delivery-api-contract-hygiene-design.md](../specs/2026-09-28-slice-0-delivery-api-contract-hygiene-design.md)

## Global Constraints

- Export FastAPI's OpenAPI 3.1 schema without starting a server or opening a database connection.
- The versioned artifact is packages/api-contracts/openapi/reference-data-api.v1.json; generation is deterministic and checked in.
- Use RFC 9457 application/problem+json, X-Request-ID, documented type URIs, and safe code, requestId, and optional errors extensions.
- Never return or normally log rejected values, request/response bodies, credentials, database URLs, headers, cookies, raw exception messages, or stack-trace text.
- Preserve the server-side Ops Console BFF tenant-header boundary; browser code gets no tenant credentials.
- Pin CI to Python 3.12 and Node 24; install Python from a hash-verified lock and Node with pnpm install --frozen-lockfile.
- CI has permissions: contents: read, no pull_request_target, no deployment/publishing, and full 40-character immutable action SHAs.
- Leave existing untracked log files in place; ignore rather than delete them.

## Review Focus

- An invalid X-Request-ID is not reflected; a fresh UUID is returned. Task 1 test: test_invalid_request_id_is_replaced.
- A sentinel secret in an exception or rejected input reaches neither an API body nor normal logs. Task 1 tests: test_unhandled_exception_does_not_disclose_message and test_validation_problem_omits_rejected_input.
- New routes cannot omit common errors from OpenAPI. Task 2 test: test_openapi_operations_include_standard_problem_responses.
- FastAPI changes cannot leave stale JSON/TypeScript generation. Tasks 2 and 3 test exporter and generator check modes.
- A BFF Problem Details response preserves status, code, and request ID, but unknown upstream JSON is not exposed. Task 3 test: reference-api-client.test.ts problem case.

---

## File structure

| Path | Responsibility |
| --- | --- |
| apps/reference_api/problem_details.py | RFC 9457 models, safe mapping, request-ID handling, response logging, and OpenAPI common responses. |
| apps/reference_api/main.py | Installs API-boundary configuration and API metadata. |
| docs/delivery/api-problems.md | Problem type, stable code, status, and client-behaviour documentation. |
| tests/test_reference_api_problem_details.py | Error bodies, redaction, request IDs, and response logging. |
| scripts/export_openapi_contract.py | Deterministically exports or checks FastAPI OpenAPI. |
| packages/api-contracts/openapi/reference-data-api.v1.json | Checked-in v1 contract. |
| packages/api-contracts/src/generated.ts | Generated schema types only; never hand edited. |
| packages/api-contracts/src/client.ts | Typed openapi-fetch factory and problem-result helper. |
| packages/api-contracts/src/index.ts | Stable public package exports. |
| apps/ops-console/src/lib/reference-api-client.ts | BFF adapter consuming api-contracts instead of local payload models. |
| requirements.in, requirements-dev.in, requirements.lock | Python inputs, lock compiler, and verified runtime lock. |
| .github/workflows/quality.yml, .gitleaks.toml | Read-only quality gate and secret scan configuration. |
| docs/delivery/quality-reviews/2026-09-28-slice-0-delivery-api-contract-hygiene.md | Final verification evidence. |

### Task 1: Create the safe API error and request-ID boundary

**Files:**
- Create: apps/reference_api/problem_details.py
- Modify: apps/reference_api/main.py and apps/reference_api/tenant_context.py
- Create: tests/test_reference_api_problem_details.py and docs/delivery/api-problems.md
- Modify: tests/test_reference_api_boundary.py

**Interfaces:**
- Consumes: FastAPI, Request, RequestValidationError, Starlette HTTPException, and existing create_app().
- Produces: configure_problem_details(app: FastAPI) -> None, ProblemDetails, ApiProblem, and request_id_from_request(request: Request) -> str.

- [ ] **Step 1: Write failing API-boundary tests**

~~~python
def test_missing_tenant_context_is_a_problem_response_with_request_id():
    response = asyncio.run(_get("/v1/instruments/search"))
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "authentication.required"
    assert UUID(response.headers["x-request-id"])

def test_invalid_request_id_is_replaced():
    response = asyncio.run(_get("/health", headers={"X-Request-ID": "not-a-uuid"}))
    assert response.headers["x-request-id"] != "not-a-uuid"
    assert UUID(response.headers["x-request-id"])
~~~

Add malformed-validation and RuntimeError("sentinel-secret") cases. Assert no rejected value or sentinel appears in a response or captured normal log message.

- [ ] **Step 2: Run tests to verify they fail**

Run: python -m pytest tests/test_reference_api_problem_details.py tests/test_reference_api_boundary.py -v

Expected: FAIL because the current API returns FastAPI's detail envelope and has no X-Request-ID response header.

- [ ] **Step 3: Implement problem_details and install it in create_app**

Define the Pydantic ProblemDetails model with type, title, status, detail, instance, code, requestId, and optional safe errors. Middleware accepts only a canonical UUID in X-Request-ID, generates a UUID otherwise, sets it on every response, and logs only method, route template/path, status, duration, request ID, and exception class.

Map HTTPException and validation errors to status-specific stable type/code/generic safe detail. Map unknown exceptions to a generic 500 while recording safe diagnostic metadata. Remove all raw repository exception text from response paths. Retain X-Correlation-Id only as a temporary input alias if required by current adapters; emit X-Request-ID and use its UUID internally.

- [ ] **Step 4: Document problem types**

Write docs/delivery/api-problems.md with type URI, status, stable code, safe detail text, retry guidance, and requestId handling for 400, 401, 403, 404, 409, 422, and 500. State explicitly that input values and diagnostic exception messages are absent.

- [ ] **Step 5: Run focused tests to verify they pass**

Run: python -m pytest tests/test_reference_api_problem_details.py tests/test_reference_api_boundary.py -v

Expected: PASS, including generic instead of raw-error response bodies.

- [ ] **Step 6: Commit**

~~~text
git add apps/reference_api/problem_details.py apps/reference_api/main.py apps/reference_api/tenant_context.py tests/test_reference_api_problem_details.py tests/test_reference_api_boundary.py docs/delivery/api-problems.md
git commit -m "feat: standardise API problem responses"
~~~

### Task 2: Export a checked-in OpenAPI contract with common error responses

**Files:**
- Create: scripts/export_openapi_contract.py, packages/api-contracts/openapi/reference-data-api.v1.json, tests/test_openapi_contract.py
- Modify: apps/reference_api/problem_details.py and package.json

**Interfaces:**
- Consumes: configure_problem_details from Task 1.
- Produces: export_contract(output: Path, check: bool) -> int, contract:export, contract:check, and the v1 JSON input for Task 3.

- [ ] **Step 1: Write failing contract tests**

~~~python
def test_openapi_operations_include_standard_problem_responses():
    schema = create_app().openapi()
    operation = schema["paths"]["/v1/instruments/search"]["get"]
    assert operation["responses"]["422"]["content"]["application/problem+json"]
    assert schema["components"]["schemas"]["ProblemDetails"]

def test_exporter_check_reports_stale_contract(tmp_path):
    output = tmp_path / "reference-data-api.v1.json"
    assert export_contract(output, check=False) == 0
    output.write_text("{}", encoding="utf-8")
    assert export_contract(output, check=True) == 1
~~~

- [ ] **Step 2: Run tests to verify they fail**

Run: python -m pytest tests/test_openapi_contract.py -v

Expected: FAIL because neither shared Problem Details OpenAPI components nor an exporter exists.

- [ ] **Step 3: Add OpenAPI common components and deterministic export**

Customise app.openapi after FastAPI generation. Add ProblemDetails plus safe validation-errors schema to components.schemas, define application/problem+json for 400/401/403/404/409/422/500, and attach those responses to every operation without replacing success responses. Keep FastAPI's 3.1 output.

Implement exporter JSON with sorted keys, two-space indentation, and one final newline. Check mode compares exact bytes and does not write. Add root scripts contract:export and contract:check.

- [ ] **Step 4: Generate the initial artifact and verify**

Run: python scripts/export_openapi_contract.py
Run: python -m pytest tests/test_openapi_contract.py -v
Run: python scripts/export_openapi_contract.py --check

Expected: JSON exists, tests PASS, and check mode exits 0 without a modification.

- [ ] **Step 5: Commit**

~~~text
git add scripts/export_openapi_contract.py apps/reference_api/problem_details.py packages/api-contracts/openapi/reference-data-api.v1.json tests/test_openapi_contract.py package.json
git commit -m "feat: export versioned OpenAPI contract"
~~~

### Task 3: Generate TypeScript types and move the BFF to the public contract

**Files:**
- Modify: package.json, pnpm-lock.yaml, packages/api-contracts/package.json
- Create: packages/api-contracts/tsconfig.json, packages/api-contracts/src/generated.ts, packages/api-contracts/src/client.ts, packages/api-contracts/src/index.ts, packages/api-contracts/src/client.test.ts
- Modify: apps/ops-console/package.json, apps/ops-console/tsconfig.json, apps/ops-console/src/lib/reference-api-client.ts, apps/ops-console/src/lib/reference-api-client.test.ts, apps/ops-console/src/lib/browser-api-client.ts, apps/ops-console/src/app/api/reference-nodes/search/route.ts
- Delete: apps/ops-console/src/lib/reference-api-types.ts

**Interfaces:**
- Consumes: v1 JSON from Task 2.
- Produces: createReferenceApiClient(options: { baseUrl: string; fetch?: typeof fetch }), generated paths/components types, and a BFF adapter whose return types come from api-contracts.

- [ ] **Step 1: Write failing TypeScript tests**

~~~ts
import { createReferenceApiClient, type paths } from "api-contracts";

it("types a v1 search request and problem response", async () => {
  const client = createReferenceApiClient({ baseUrl: "https://example.test" });
  const result = await client.GET("/v1/instruments/search", {
    params: { query: { q: "HSBC" } },
  });
  expectTypeOf(result).toMatchTypeOf<{ data?: unknown; error?: unknown }>();
});
~~~

Extend reference-api-client.test.ts with an application/problem+json 409 fixture. Assert ReferenceApiError exposes status, stable code, and requestId; an arbitrary upstream body must not become a browser message.

- [ ] **Step 2: Run focused checks to verify failure**

Run: pnpm --filter api-contracts test
Run: pnpm --filter ops-console typecheck

Expected: FAIL because public exports and generated sources do not yet exist.

- [ ] **Step 3: Add reproducible generation and typed transport**

Add exact package dependencies: openapi-fetch at runtime and openapi-typescript, TypeScript, and Vitest for development/test. Add root scripts contract:generate and contract:check that delegate to api-contracts. Generate packages/api-contracts/src/generated.ts only with:

~~~text
openapi-typescript packages/api-contracts/openapi/reference-data-api.v1.json -o packages/api-contracts/src/generated.ts
~~~

Add generate, generate:check, typecheck, and test scripts. generate:check regenerates then fails on a git diff limited to generated output.

Implement a small handwritten createReferenceApiClient wrapper around createClient<paths>(). It offers typed HTTP methods plus a helper to turn generated Problem Details errors into ReferenceApiProblem. It has no endpoint-specific models and does not attach tenant headers. Turn on noUncheckedIndexedAccess for the contract package.

- [ ] **Step 4: Refactor the BFF adapter without changing browser topology**

Replace imports from reference-api-types.ts with public api-contracts types. Keep current named BFF functions as compatibility adapters, but implement their upstream calls through the typed client and convert only ReferenceApiProblem to ReferenceApiError. Preserve BFF-only tenant/user headers and cache: no-store. Remove the duplicate local types file only after all imports resolve through the workspace package.

- [ ] **Step 5: Generate and run focused web verification**

Run: pnpm contract:generate
Run: pnpm --filter api-contracts test
Run: pnpm --filter api-contracts typecheck
Run: pnpm --filter ops-console test -- reference-api-client.test.ts
Run: pnpm --filter ops-console typecheck
Run: pnpm contract:check

Expected: PASS; a manually stale generated file causes the final check to fail.

- [ ] **Step 6: Commit**

~~~text
git add package.json pnpm-lock.yaml packages/api-contracts apps/ops-console/package.json apps/ops-console/tsconfig.json apps/ops-console/src/lib/reference-api-client.ts apps/ops-console/src/lib/reference-api-client.test.ts apps/ops-console/src/lib/browser-api-client.ts apps/ops-console/src/app/api/reference-nodes/search/route.ts
git rm apps/ops-console/src/lib/reference-api-types.ts
git commit -m "feat: generate typed Reference API client"
~~~

### Task 4: Add deterministic dependencies, CI, and repository hygiene

**Files:**
- Create: requirements.in, requirements-dev.in, requirements.lock, .gitleaks.toml, .github/workflows/quality.yml, tests/test_delivery_hygiene.py
- Modify: requirements.txt, .gitignore, .env.example, package.json

**Interfaces:**
- Consumes: contract check/generation scripts and all checks from Tasks 1-3.
- Produces: reproducible local/CI commands and a read-only pull-request quality workflow.

- [ ] **Step 1: Write failing delivery-hygiene tests**

~~~python
def test_gitignore_excludes_logs_and_keeps_env_example_visible():
    lines = Path(".gitignore").read_text().splitlines()
    assert "*.log" in lines
    assert "logs/" in lines
    assert "!.env.example" in lines

def test_example_environment_uses_only_placeholders():
    example = Path(".env.example").read_text()
    assert "fortem_local_only" not in example
    assert "<local-password>" in example
~~~

Add workflow assertions for contents: read, no pull_request_target, four immutable SHA refs, and Python/contract/web/secret jobs.

- [ ] **Step 2: Run tests to verify failure**

Run: python -m pytest tests/test_delivery_hygiene.py -v

Expected: FAIL because logs are not ignored, the example has a reusable password string, and workflow/lock files do not exist.

- [ ] **Step 3: Make Python dependencies reproducible**

Move runtime ranges to requirements.in. Pin pip-tools in requirements-dev.in. On Python 3.12, generate requirements.lock with pip-compile --generate-hashes --resolver=backtracking. Make requirements.txt a compatibility pointer to the lock, not a second dependency source. Document regeneration on Python 3.12. CI installs with python -m pip install --require-hashes -r requirements.lock.

- [ ] **Step 4: Add hygiene and a read-only workflow**

Append *.log and logs/ to .gitignore. Replace the .env.example password with <local-password>, retaining safe local port and demo IDs. Add a minimal .gitleaks.toml with no broad allowlist or ignored source paths.

Create quality.yml for pull_request and push to main with permissions: contents: read. Use exactly these immutable action pins:

~~~yaml
actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38 # v6
gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e # v3
~~~

Use fetch-depth: 0 for the Gitleaks checkout. Use Python 3.12/pip cache keyed by requirements.lock, Node 24/pnpm cache keyed by pnpm-lock.yaml, corepack enable, and frozen pnpm install. Python runs compilation, contract check, and pytest; web runs generation check, type-check, test, and build. Gitleaks receives only the restricted automatic GITHUB_TOKEN needed by the action, no deployment credential or organisation licence, and scans checked-out history.

- [ ] **Step 5: Run local checks**

Run: python -m pytest tests/test_delivery_hygiene.py -v
Run: python scripts/export_openapi_contract.py --check
Run: pnpm contract:check

Expected: PASS. If GitHub-hosted Gitleaks cannot run locally, record it as CI-only rather than substituting an unpinned scanner.

- [ ] **Step 6: Commit**

~~~text
git add requirements.in requirements-dev.in requirements.lock requirements.txt .gitignore .env.example .gitleaks.toml .github/workflows/quality.yml tests/test_delivery_hygiene.py package.json
git commit -m "ci: add reproducible contract quality gate"
~~~

### Task 5: Execute whole-slice verification and record evidence

**Files:**
- Create: docs/delivery/quality-reviews/2026-09-28-slice-0-delivery-api-contract-hygiene.md
- Modify: docs/delivery/quality-reviews/README.md only if its dated-review index requires an entry

**Interfaces:**
- Consumes: all scripts and tests from Tasks 1-4.
- Produces: factual command results, artifact locations, workflow safeguards, and remaining administrator-only settings.

- [ ] **Step 1: Run full Python and contract verification**

Run: python -m compileall apps packages scripts tests
Run: python -m pytest -v
Run: python scripts/export_openapi_contract.py --check

Expected: all commands exit 0.

- [ ] **Step 2: Run full workspace verification**

Run: pnpm contract:check
Run: pnpm --filter api-contracts typecheck
Run: pnpm --filter ops-console typecheck
Run: pnpm --filter ops-console test
Run: pnpm --filter ops-console build

Expected: all commands exit 0.

- [ ] **Step 3: Inspect scope and workflow protections**

Run: git diff --check
Run: git status --short

Expected: no whitespace errors; changed/staged files are Slice 0 or explicitly pre-existing user files. Verify workflow action refs and permissions against Task 4 without a mutable tag.

- [ ] **Step 4: Write quality evidence**

Record exact command outcomes, Python/Node/pnpm versions, contract and generated-package paths, workflow jobs/permissions/action SHAs, Gitleaks configuration, and that GitHub Secret Scanning/Push Protection are administrator settings outside source control. Do not record credentials, test secrets, or full logs.

- [ ] **Step 5: Commit**

~~~text
git add docs/delivery/quality-reviews/2026-09-28-slice-0-delivery-api-contract-hygiene.md docs/delivery/quality-reviews/README.md
git commit -m "docs: record Slice 0 verification evidence"
~~~

## Plan self-review

**Spec coverage:** Tasks 1-2 implement the OpenAPI, problem, and correlation requirements; Task 3 implements generated consumer types and typed transport; Task 4 implements dependencies, CI, logs, examples, and secret scanning; Task 5 records evidence and the external administrator-only GitHub setting. No requirement is unassigned.

**Step and type consistency:** Task 1 establishes ProblemDetails and ApiProblem; Task 2 exports them; Task 3 consumes generated paths and the typed client without duplicate domain models. Task 4 invokes the script names established in Tasks 2-3.

**Review-focus coverage:** Every listed failure mode is assigned a named test in its owning task. The workflow is additionally pinned by test_delivery_hygiene.py.

**Proportion:** This plan sets interfaces, assertions, and commands rather than implementation bodies. Authentication, tenant routing, and deployment stay explicitly outside Slice 0.
