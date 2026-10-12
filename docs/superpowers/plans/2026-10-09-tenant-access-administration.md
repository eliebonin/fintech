# Tenant access administration implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially, as requested by the user. Do not spawn subagents.

**Goal:** Make three-tenant isolation and user permissions visible, configurable and testable in the local alpha.

**Architecture:** Extend existing tenant/module membership tables with tenant groups and action grants. Centralize active authorization, expose separately protected management routers, and add a development-only actor/subject context session.

**Tech Stack:** SQLAlchemy, PostgreSQL, Alembic, FastAPI, Next.js, React, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-10-09-tenant-access-administration.md`.

## Global constraints

- Current feature checkout; preserve unrelated dirty files; no commit/push unless requested.
- Sequential implementation; focused disposable-database tests first.
- Preserve current operating data and data-provider rights.
- Local switcher disabled in production; API is authoritative.
- Deny unknown permissions, inactive membership/account/group and cross-tenant references.

## Review focus

- Same-day repeated module toggles must not violate effective-date uniqueness or produce ambiguous grants.
- Removing a user's last group must deny access immediately, not retain cached permission.
- A user selected by a platform admin must never inherit platform privileges.
- Switching tabs or submitting an old ticket must not mutate another tenant's records.
- Existing approval rules must not be bypassed by switching the effective user.

### Task 1: Permission foundation and schema

Files: `security_master_schema/access_control.py`, `models.py`, `tenant_workspace.py`, Alembic revision 82, `tests/test_access_control.py`.

Produces `resolve_tenant_workspace(...).permission_codes`, tenant modules and effective user modules; `require_permission(workspace, action)`.

- [x] Write lightweight permission tests for group union, module intersection, unknown actions and admin boundaries; run and observe missing behavior.
- [x] Add scoped groups, memberships and grants with same-tenant constraints, and access audit/session tables.
- [x] Extend workspace authorization, preserve legacy admin behavior only for enabled modules, and run isolated SQL tests.

### Task 2: Management APIs and seed

Files: `apps/reference_api/access_routes.py`, `access_contracts.py`, `security_master_schema/access_management.py`, `access_seed.py`, `tests/test_access_management.py`.

Consumes Task 1 action catalogue. Produces platform tenant/module endpoints, tenant user/group endpoints and seeded IDs.

- [x] Write API tests for role boundaries, same-tenant assignment, repeated toggle and preservation of data; observe failures.
- [x] Implement transactional module changes and user/group lifecycle with audit evidence and active-actor checks.
- [x] Seed three tenants idempotently with four user personas each; do not reseed historical market/trade fixtures.
- [x] Run management and existing workspace/booking authorization regressions.

### Task 3: Central request authorization and testing session

Files: `apps/reference_api/tenant_context.py`, access router, `apps/ops-console/src/lib/tenant-session.ts`, `src/lib/server/access-session.ts`, affected API forwarding, `tests/test_access_session.py`, frontend session tests.

Produces backend-validated short-lived local testing session, real actor/effective subject, and centrally forwarded context.

- [x] Test forged/expired/revoked sessions, ordinary-user platform access, suspended targets and production rejection; observe failures.
- [x] Implement context validation, private header boundary enforcement, and permission resolution for read/write routes.
- [x] Replace fixed-user forwarding and expose server session mutation routes protected by same-origin checks.
- [x] Ensure session changes cause full navigation and compare real/effective actor for independent review checks.

### Task 4: Administration UI

Files: platform tenants page, tenant access page, context selector, workspace shell and permission UI helpers, their focused Vitest tests.

Consumes management API and workspace effective access; produces requested pages and visible testing-as context.

- [x] Write tests for permitted and forbidden controls and error/recovery behavior; observe failures.
- [x] Build tenant/module registry, tenant Users/Groups workspace and context selector.
- [x] Replace admin-only booking affordances with API-derived action permissions, while retaining safe unknown-access defaults.
- [x] Run focused Vitest and TypeScript checks.

### Task 5: Activation, isolation acceptance and delivery record

Files: `docs/delivery/tenant-access-administration.md` and this plan.

- [x] Run disposable-database migration and isolation regressions; inspect authorization coverage and diff.
- [x] Back up affected operating registry; apply additive migration and idempotent access seed.
- [x] Restart local services; verify platform and three tenant/persona contexts through API and browser where available.
- [x] Document exact verification, remaining production limitations and any acceptance blocked by tooling.


## Acceptance caveat

Implementation, additive migration, access-only seed, service restart, HTTP acceptance and documentation are complete. Browser click-through could not start because the provided automation kernel's Windows sandbox helper failed.

- [ ] Manual browser walkthrough of platform module toggles, user/group edits, and switching all three tenant personas. This remains pending; HTTP/SSR evidence does not replace it.
