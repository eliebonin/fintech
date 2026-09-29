# Tenant Workspace and Strategy Alpha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first usable tenant alpha: server-backed tenant selection, module-aware workspace access, and tenant-scoped strategy creation and management.

**Architecture:** Extend the existing `tenant_user_account` membership and `tenant_module_entitlement` records rather than creating parallel identity tables. The Ops Console stores only a selected, validated tenant in a secure server session cookie; every BFF command obtains tenant and actor context on the server and the Reference API verifies membership and authorization again. Strategies use the existing `trd.strategy` record with a controlled `strategy_type` catalogue and tenant-unique codes.

**Tech Stack:** PostgreSQL 18, Alembic, SQLAlchemy Core, FastAPI/Pydantic, pytest, Next.js App Router, React 19, TypeScript, MUI 9, Vitest, pnpm.

**Spec:** `docs/superpowers/specs/2026-09-29-tenant-cash-trading-alpha-design.md`

## Global Constraints

- The browser must never send arbitrary tenant authority to the Reference API; only the BFF adds tenant/actor headers.
- The trusted-header path remains local-alpha plumbing and must stay replaceable by production OIDC/Auth0 claim validation.
- All strategy mutations are tenant-scoped, actor-attributed, and idempotent; strategy history is not destructively overwritten.
- Supported alpha strategy types are `AMC_MANDATE`, `FUND`, `MANAGED_ACCOUNT`, `PROP_SLEEVE`, `MODEL_PORTFOLIO`, and `OTHER`; `OTHER` requires an explanatory label.
- A strategy code is unique within its tenant, not globally; inactive strategies remain readable but cannot receive new trades in the later trading slice.
- Platform administration is distinct from tenant membership, and this plan deliberately does not implement tenant impersonation.
- Hosted Python CI must provision PostgreSQL before it runs integration tests.

## Review Focus

- A user selects a tenant they do not actively belong to: the BFF must refuse to set the cookie and the API must still deny any attempted direct access; test in Task 4.
- A tenant's module entitlement expires after a session starts: navigation must disappear on refresh and the strategy command must return the safe forbidden problem; test in Tasks 3 and 5.
- Identical strategy codes in different tenants must succeed while a duplicate in one tenant must fail deterministically; test in Task 1 and Task 3.
- A stale browser form is submitted after tenant switching: the BFF must bind the command to the active server session, not the form's prior tenant; test in Task 4.
- `OTHER` is selected without a descriptive label: reject it as a field validation error rather than creating an ambiguous operating model; test in Task 3 and Task 5.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `alembic/versions/20260929_48_tenant_workspace_strategy_controls.py` | Tenant-local strategy-code constraint, strategy type/`OTHER` label controls, platform-admin authority table, comments/indexes. |
| `security_master_schema/models.py` | SQLAlchemy declarations for new strategy metadata and platform authority. |
| `security_master_schema/tenant_workspace.py` | Focused membership, entitlement, and role resolution helpers. |
| `apps/reference_api/contracts.py` | Pydantic request/response contracts for session workspace and strategies. |
| `apps/reference_api/repository.py` | Tenant workspace reads and strategy persistence/read operations. |
| `apps/reference_api/main.py` | Membership/workspace and strategy routes with existing safe-problem conventions. |
| `apps/ops-console/src/lib/tenant-session.ts` | Server-only active-tenant cookie parsing, validation, and local actor source. |
| `apps/ops-console/src/lib/tenant-workspace.ts` | Typed BFF client and view models for membership/module workspace data. |
| `apps/ops-console/src/app/api/session/*` | BFF session/current-workspace/select-tenant routes. |
| `apps/ops-console/src/app/workspace/*` | Tenant home page and module-aware shell integration. |
| `apps/ops-console/src/app/strategies/*` | Strategy list, create, and detail pages/forms. |
| `apps/ops-console/src/app/api/strategies/*` | BFF strategy read/write routes. |
| `apps/ops-console/src/components/workspace-shell.tsx` and `src/lib/navigation.ts` | Active tenant chrome and entitlement-filtered navigation. |
| `tests/test_tenant_workspace.py`, `tests/test_strategy_workspace_api.py` | Database/API behavior and tenant isolation. |
| `apps/ops-console/src/lib/tenant-session.test.ts`, `tenant-workspace.test.ts`, and route/page tests | BFF/session/UI behavior. |
| `.github/workflows/quality.yml` | PostgreSQL service and database URL for hosted Python checks. |

### Task 1: Add durable workspace and strategy controls

**Files:**
- Modify: `security_master_schema/models.py:550-560, 888+`
- Create: `alembic/versions/20260929_48_tenant_workspace_strategy_controls.py`
- Create: `tests/test_tenant_workspace.py`
- Modify: `security_master_schema/demo_data.py`

**Interfaces:**
- Produces `m.platform_user_account` with `user_account_id`, `platform_role`, `status`, `valid_from`, and `valid_to`.
- Extends `m.strategy` with `operating_model_label` and audit/effective fields required by the specification.
- Changes strategy identity constraint to `uq_strategy_tenant_code(tenant_id, strategy_code)`.

- [ ] **Step 1: Write failing migration/database tests**

```python
def test_strategy_code_is_unique_within_tenant_but_reusable_by_another_tenant(connection):
    insert_strategy(connection, tenant_a, "CORE", "FUND")
    insert_strategy(connection, tenant_b, "CORE", "FUND")
    with pytest.raises(IntegrityError, match="uq_strategy_tenant_code"):
        insert_strategy(connection, tenant_a, "CORE", "FUND")

def test_platform_authority_is_not_a_tenant_membership(connection):
    insert_platform_admin(connection, account_id)
    assert resolve_platform_role(connection, account_id) == "PLATFORM_ADMIN"
```

- [ ] **Step 2: Run the focused tests to verify failure**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_tenant_workspace.py -v`

Expected: FAIL because the tenant-local constraint and platform authority table do not exist.

- [ ] **Step 3: Implement the migration and model declarations**

Create revision `20260929_48` after revision 47. Drop only the existing global strategy-code unique constraint, add the tenant-local unique constraint/index, and add the comments required by project migration policy. Add a check constraint restricting `strategy_type` to the six alpha values and requiring a nonblank `operating_model_label` only for `OTHER`. Add platform authority as a separate `ten.platform_user_account` table; do not add it to `tenant_user_account`.

- [ ] **Step 4: Extend deterministic demo data**

Seed a second tenant, an active membership for the demo actor in that tenant, a tenant-admin membership for the primary tenant, and one separate platform-admin user. Seed only the module entitlements required for deterministic switcher tests.

- [ ] **Step 5: Run migration and database verification**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_migrations.py tests/test_tenant_workspace.py -v`

Expected: PASS; migration round-trip retains the strategy constraint and removes it safely on downgrade.

- [ ] **Step 6: Commit**

```bash
git add security_master_schema/models.py security_master_schema/demo_data.py alembic/versions/20260929_48_tenant_workspace_strategy_controls.py tests/test_tenant_workspace.py
git commit -m "feat: add tenant workspace strategy controls"
```

### Task 2: Resolve memberships, effective entitlements, and roles in one boundary

**Files:**
- Create: `security_master_schema/tenant_workspace.py`
- Modify: `security_master_schema/tenancy.py`
- Modify: `tests/test_tenant_workspace.py`

**Interfaces:**
- Produces `list_active_tenant_memberships(connection, user_account_id, as_of_date) -> list[TenantMembershipView]`.
- Produces `resolve_tenant_workspace(connection, tenant_id, user_account_id, as_of_date) -> TenantWorkspaceView`.
- Produces `require_tenant_action(workspace, action: Literal["STRATEGY_READ", "STRATEGY_WRITE"]) -> None`.
- Produces `resolve_platform_role(connection, user_account_id, as_of_date) -> str | None`.

- [ ] **Step 1: Write failing resolver tests**

```python
def test_workspace_returns_only_current_memberships_and_granted_modules(connection):
    memberships = list_active_tenant_memberships(connection, actor_id, date(2026, 9, 29))
    assert [(row.tenant_code, row.membership_role) for row in memberships] == [("DEMO", "TENANT_ADMIN"), ("SECOND", "OPERATIONS")]
    assert "TRADING" in resolve_tenant_workspace(connection, tenant_id, actor_id, date.today()).module_codes

def test_strategy_write_requires_tenant_admin_and_trading_or_fund_management(connection):
    workspace = resolve_tenant_workspace(connection, operations_tenant, operations_actor, date.today())
    with pytest.raises(TenantActionForbidden):
        require_tenant_action(workspace, "STRATEGY_WRITE")
```

- [ ] **Step 2: Run the resolver tests to verify failure**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_tenant_workspace.py -v`

Expected: FAIL because workspace resolver symbols do not exist.

- [ ] **Step 3: Implement focused workspace resolution**

Use effective-date predicates already used by tenant capabilities. Return typed, display-ready tenant code/name, membership role, granted module code/name, and optional platform role. Do not return tenant IDs from a broad unfiltered catalogue. Keep action policy in one function rather than duplicating role checks in route handlers.

- [ ] **Step 4: Add expiry and cross-tenant coverage**

Add tests for inactive memberships, expired module grants, and an actor trying to resolve a tenant outside their memberships.

- [ ] **Step 5: Run focused verification**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_tenant_workspace.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add security_master_schema/tenant_workspace.py security_master_schema/tenancy.py tests/test_tenant_workspace.py
git commit -m "feat: resolve tenant workspace permissions"
```

### Task 3: Expose workspace and strategy API contracts

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Create: `tests/test_strategy_workspace_api.py`
- Modify: `tests/test_schema_hardening.py`

**Interfaces:**
- Produces `GET /v1/session/memberships` using actor context and returning memberships plus optional platform role.
- Produces `GET /v1/tenant-workspace` using selected tenant context and returning `TenantWorkspaceResponse`.
- Produces `GET /v1/strategies`, `POST /v1/strategies`, `GET /v1/strategies/{strategy_id}`, and `POST /v1/strategies/{strategy_id}/status`.
- Produces `create_strategy(connection, tenant_id, actor_id, request: StrategyCreateRequest) -> StrategyView`.

- [ ] **Step 1: Write failing API tests**

```python
def test_memberships_do_not_require_an_already_selected_tenant():
    response = request("/v1/session/memberships", headers={"X-User-Account-Id": DEMO_ACTOR})
    assert response.status_code == 200
    assert [item["tenantCode"] for item in response.json()["data"]] == ["DEMO", "SECOND"]

def test_tenant_admin_can_create_a_fund_strategy():
    response = post("/v1/strategies", {"strategyCode": "ALPHA_FUND", "displayName": "Alpha Fund", "strategyType": "FUND", "baseCurrencyCode": "GBP"})
    assert response.status_code == 201
    assert response.json()["data"]["tenantId"] == DEMO_TENANT

def test_other_strategy_requires_operating_model_label():
    response = post("/v1/strategies", {"strategyCode": "OTHER", "displayName": "Other", "strategyType": "OTHER"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run focused API tests to verify failure**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_strategy_workspace_api.py -v`

Expected: FAIL with missing routes/contracts.

- [ ] **Step 3: Add session actor dependency and contracts**

Add a narrowly scoped actor-only local dependency for `/v1/session/memberships`; do not weaken existing tenant-required dependencies. Define aliased Pydantic contracts for human-readable membership/module/strategy payloads and preserve the standard metadata envelope.

- [ ] **Step 4: Implement repository operations and routes**

Validate membership and `STRATEGY_WRITE` before mutation. Resolve currency by governed currency code. Make create idempotent with an `Idempotency-Key` header scoped by tenant/endpoint/key using the established market-data pattern. Use `409` for same-tenant code conflict and safe authorization problems for unauthorized actions. Status transitions retain actor/time/reason and only allow active-to-archived in this alpha.

- [ ] **Step 5: Add authorization, idempotency, and response-safety tests**

Test an operations member cannot create, an expired entitlement cannot create, a repeated request replays, differing request/key fails, and a nonmember cannot read the created strategy.

- [ ] **Step 6: Export and verify API contract**

Run: `.venv\\Scripts\\python.exe scripts\\export_openapi_contract.py --check; .venv\\Scripts\\python.exe -m pytest tests/test_strategy_workspace_api.py tests/test_schema_hardening.py -v`

Expected: PASS and no generated OpenAPI drift.

- [ ] **Step 7: Commit**

```bash
git add apps/reference_api/contracts.py apps/reference_api/repository.py apps/reference_api/main.py tests/test_strategy_workspace_api.py tests/test_schema_hardening.py packages/api-contracts
git commit -m "feat: add tenant workspace strategy API"
```

### Task 4: Add a validated server-side active-tenant session to the BFF

**Files:**
- Create: `apps/ops-console/src/lib/tenant-session.ts`
- Create: `apps/ops-console/src/lib/tenant-workspace.ts`
- Modify: `apps/ops-console/src/lib/tenant-context.ts`
- Create: `apps/ops-console/src/app/api/session/memberships/route.ts`
- Create: `apps/ops-console/src/app/api/session/active-tenant/route.ts`
- Create: `apps/ops-console/src/app/api/session/active-tenant/route.test.ts`
- Create: `apps/ops-console/src/lib/tenant-session.test.ts`

**Interfaces:**
- Produces `getSessionActor(): Promise<SessionActor>` and `getActiveTenantContext(): Promise<TenantContext>`.
- Produces `selectActiveTenant(tenantId: string): Promise<ActiveTenantWorkspace>`.
- `POST /api/session/active-tenant` accepts `{ tenantId }`, validates it against `/v1/session/memberships`, and sets an HttpOnly, SameSite=Lax cookie.
- `GET /api/session/memberships` and `GET /api/session/active-tenant` return view payloads only.

- [ ] **Step 1: Write failing BFF session tests**

```ts
it("sets the active-tenant cookie only for a membership returned for the session actor", async () => {
  const response = await POST(requestWithJson({ tenantId: permittedTenantId }));
  expect(response.status).toBe(200);
  expect(response.headers.get("set-cookie")).toContain("active_tenant=");
});

it("does not accept a tenant selected by a stale form or nonmember", async () => {
  const response = await POST(requestWithJson({ tenantId: foreignTenantId }));
  expect(response.status).toBe(403);
  expect(response.headers.get("set-cookie")).toBeNull();
});
```

- [ ] **Step 2: Run BFF tests to verify failure**

Run: `pnpm --filter ops-console test -- tenant-session route.test`

Expected: FAIL because session helpers/routes do not exist.

- [ ] **Step 3: Implement server-only session helpers**

Keep the current demo actor environment seam, but replace the static tenant environment lookup with the HttpOnly cookie after membership validation. Use a documented signed cookie secret in server configuration; fail closed when missing outside development. Do not expose the cookie secret or upstream headers to browser components.

- [ ] **Step 4: Implement membership and tenant-selection BFF routes**

Use existing server-side `reference-api-client` patterns. On tenant switch, return the selected workspace payload and emit a response marker so clients clear tenant-scoped query/cache state. A command route must always call `getActiveTenantContext()` at request time.

- [ ] **Step 5: Run session/BFF verification**

Run: `pnpm --filter ops-console test -- tenant-session tenant-workspace route.test`

Expected: PASS, including nonmember refusal and no arbitrary browser header forwarding.

- [ ] **Step 6: Commit**

```bash
git add apps/ops-console/src/lib/tenant-session.ts apps/ops-console/src/lib/tenant-workspace.ts apps/ops-console/src/lib/tenant-context.ts apps/ops-console/src/app/api/session
git commit -m "feat: add validated active tenant session"
```

### Task 5: Deliver module-aware workspace and strategy UI

**Files:**
- Modify: `apps/ops-console/src/components/workspace-shell.tsx`
- Modify: `apps/ops-console/src/lib/navigation.ts`
- Create: `apps/ops-console/src/components/tenant-switcher.tsx`
- Create: `apps/ops-console/src/app/select-tenant/page.tsx`
- Create: `apps/ops-console/src/app/workspace/page.tsx`
- Create: `apps/ops-console/src/app/strategies/page.tsx`
- Create: `apps/ops-console/src/app/strategies/new/page.tsx`
- Create: `apps/ops-console/src/app/strategies/new/form.tsx`
- Create: `apps/ops-console/src/app/strategies/[strategyId]/page.tsx`
- Create: `apps/ops-console/src/app/api/strategies/route.ts`
- Create: `apps/ops-console/src/app/api/strategies/[strategyId]/route.ts`
- Create: `apps/ops-console/src/app/api/strategies/[strategyId]/status/route.ts`
- Create: `apps/ops-console/src/app/strategies/strategies.test.tsx`

**Interfaces:**
- Consumes `ActiveTenantWorkspace` from Task 4 and strategy contracts from Task 3.
- Produces an active-tenant banner containing tenant name/code, membership role, and enabled modules.
- Produces a strategy form whose submitted fields match `StrategyCreateRequest` and never include tenant/actor IDs.

- [ ] **Step 1: Write failing workspace/UI tests**

```tsx
it("shows only modules granted to the active tenant", () => {
  render(<WorkspaceShell workspace={workspaceWithTradingOnly} />);
  expect(screen.getByRole("link", { name: "Trades" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Market data" })).not.toBeInTheDocument();
});

it("submits a fund strategy without exposing tenant IDs", async () => {
  render(<StrategyCreateForm />);
  await user.type(screen.getByLabelText("Strategy code"), "ALPHA_FUND");
  await user.selectOptions(screen.getByLabelText("Operating model"), "FUND");
  await user.click(screen.getByRole("button", { name: "Create strategy" }));
  expect(fetch).toHaveBeenCalledWith("/api/strategies", expect.objectContaining({ method: "POST" }));
});
```

- [ ] **Step 2: Run the UI tests to verify failure**

Run: `pnpm --filter ops-console test -- strategies navigation`

Expected: FAIL because workspace/strategy components do not exist.

- [ ] **Step 3: Implement active-tenant chrome and module-filtered navigation**

Make `/select-tenant` the entry when no active tenant is stored. Render the workspace pages from server-fetched workspace data. Do not use fixture fallbacks for authorization/module visibility; show an explicit unavailable state if the API cannot provide the active workspace.

- [ ] **Step 4: Implement strategy list, create, and detail pages**

Use display-ready currency options and operating-model help text. Restrict create/archive actions to workspace `canManageStrategies`; leave detail/read accessible according to the API contract. Preserve form data on ordinary validation failure, but clear it after an active-tenant change.

- [ ] **Step 5: Add BFF route tests and UI edge cases**

Test `OTHER` requires its explanation, disabled modules do not expose create routes, an archive action has an explicit reason, and an active-tenant switch prevents the prior form from submitting under its old tenant.

- [ ] **Step 6: Run web verification**

Run: `pnpm --filter api-contracts generate:check; pnpm --filter api-contracts typecheck; pnpm --filter ops-console typecheck; pnpm --filter ops-console test; pnpm --filter ops-console build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/ops-console/src/components apps/ops-console/src/lib apps/ops-console/src/app/select-tenant apps/ops-console/src/app/workspace apps/ops-console/src/app/strategies apps/ops-console/src/app/api/strategies
git commit -m "feat: add tenant workspace strategy console"
```

### Task 6: Make hosted Python quality reproducible

**Files:**
- Modify: `.github/workflows/quality.yml`
- Modify: `docs/delivery/README.md`
- Modify: `tests/test_migrations.py` only if it needs the CI service database URL explicitly

**Interfaces:**
- The `python` job exposes `DATABASE_URL=postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm` to compile/contract/test steps.
- GitHub Actions provisions PostgreSQL 18 with matching credentials and a readiness health check.

- [ ] **Step 1: Write/adjust an executable CI-environment regression check**

Add a test or documented smoke command that reads only `DATABASE_URL` and confirms the migration test can create its disposable test database; it must not rely on a developer's Docker container name or filesystem.

- [ ] **Step 2: Run it locally with an explicit CI-style database URL**

Run: `$env:DATABASE_URL='postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'; .venv\\Scripts\\python.exe -m pytest tests/test_migrations.py -v`

Expected: PASS.

- [ ] **Step 3: Add the PostgreSQL service to the Python job**

Use the supported GitHub Actions `services` configuration, image `postgres:18`, explicit database/user/password, port `54329:5432`, and `pg_isready` health options. Scope `DATABASE_URL` to the job/steps and leave the web/secrets jobs unchanged.

- [ ] **Step 4: Document the hosted/local parity contract**

State that PostgreSQL-backed tests are mandatory quality checks and list the one environment variable used by both local Docker and CI.

- [ ] **Step 5: Run final first-phase verification**

Run: `.venv\\Scripts\\python.exe -m compileall apps packages scripts tests; .venv\\Scripts\\python.exe scripts\\export_openapi_contract.py --check; .venv\\Scripts\\python.exe -m pytest -q; pnpm --filter api-contracts generate:check; pnpm --filter api-contracts typecheck; pnpm --filter ops-console typecheck; pnpm --filter ops-console test; pnpm --filter ops-console build`

Expected: all commands pass; Python is run against the local PostgreSQL equivalent of the hosted service.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/quality.yml docs/delivery/README.md tests/test_migrations.py
git commit -m "ci: provision postgres for quality checks"
```

## Plan self-review

- **Spec coverage:** access/session and platform authority map to Tasks 1, 2, and 4; module gating maps to Tasks 2, 3, and 5; strategy model and workflow map to Tasks 1, 3, and 5; verification and CI map to Task 6. Instrument taxonomy and cash trading are intentionally separate subsequent plans because they depend on these contracts.
- **Type consistency:** API `TenantWorkspaceView` is resolved in Task 2, exposed in Task 3, consumed by BFF Task 4, and rendered by Task 5. Strategy contracts originate in Task 3 and are used only after their introduction.
- **Review Focus coverage:** nonmember/stale selection is tested in Task 4; entitlement expiry in Tasks 2/3/5; tenant-local strategy code in Task 1; and `OTHER` labeling in Tasks 1/3/5.
- **Scope:** this plan is limited to the shared foundation and strategies. The tenant-instrument/taxonomy and cash-trade vertical slices receive their own plans after this foundation is accepted, preventing unreviewable cross-cutting work.
