# UI Monorepo Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a modular pnpm workspace for Fortem's frontend applications and shared TypeScript packages without changing the existing Python backend.

**Architecture:** Keep one Git repository with independently deployable apps under `apps/` and deliberately shared packages under `packages/`. Start with a metadata-only `apps/ops-console` boundary and avoid adding a second application or framework until its workflow is specified. The Python security-master backend remains a sibling source tree and communicates through versioned API contracts rather than direct imports.

**Tech Stack:** pnpm workspaces, Node.js/TypeScript package metadata, existing Python/SQLAlchemy backend, Markdown specifications. Turborepo is deferred until multiple apps/packages create a measurable orchestration need.

**Spec:** `ui/decisions/0002-server-first-hybrid-rendering.md`, `ui/mvp-scope.md`, and the monorepo decision recorded in `ui/decisions/0003-modular-monorepo.md`.

## Global Constraints

- The browser never connects directly to PostgreSQL or receives tenant database credentials.
- Applications are separate deployables with independent environment variables, permissions, and pipelines.
- Shared packages expose explicit public APIs; applications must not import another application's internals.
- TypeScript API types are generated from versioned API contracts, not imported from SQLAlchemy/Python implementation modules.
- No production data, provider payloads, credentials, or tenant fixtures may be placed in the frontend workspace.
- Do not add Turborepo or Nx until a second application/shared build graph justifies the dependency.

---

### Task 1: Root workspace configuration

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `.npmrc`

**Deliverable:** pnpm recognizes the frontend apps and packages as one workspace with strict local package references.

- [x] **Step 1: Define the root package manifest**

Create a private root package with package-manager pinning and scripts that do not assume an application framework:

```json
{
  "name": "platform-workspace",
  "private": true,
  "packageManager": "pnpm@10.7.1",
  "scripts": {
    "workspace:list": "pnpm -r list --depth -1"
  }
}
```

- [x] **Step 2: Define workspace globs**

Use `apps/*` and `packages/*` only. Do not include the existing Python directories as pnpm packages.

- [x] **Step 3: Set safe workspace defaults**

Set a shared lockfile, strict peer dependency checks, and workspace package preference. Do not add remote caching or registry credentials.

- [x] **Step 4: Verify workspace discovery**

Run `pnpm install --lockfile-only` and `pnpm run workspace:list`. Expect all app/package manifests to be discovered and a root `pnpm-lock.yaml` to be created.

### Task 2: Operations console application boundary

**Files:**
- Create: `apps/ops-console/package.json`
- Create: `apps/ops-console/README.md`

**Deliverable:** A private, independently deployable operations-console package exists without prematurely choosing Next.js or another framework.

- [x] **Step 1: Add package metadata**

Define `ops-console` as a private ESM package. Keep scripts limited to placeholders that fail clearly until the framework is selected; do not add fake build commands.

- [x] **Step 2: Document the application boundary**

State that this app owns operations, security-master, mapping, trade, and Soft-NAV screens; it may consume shared packages but cannot be imported by them or by another app.

- [x] **Step 3: Verify package isolation**

Run `pnpm --filter ops-console list --depth -1`. Expect no runtime dependency on the Python backend or another app.

### Task 3: Minimal shared package boundaries

**Files:**
- Create: `packages/api-contracts/package.json`
- Create: `packages/api-contracts/README.md`
- Create: `packages/ui/package.json`
- Create: `packages/ui/README.md`
- Create: `packages/auth/package.json`
- Create: `packages/auth/README.md`
- Create: `packages/test-fixtures/package.json`
- Create: `packages/test-fixtures/README.md`

**Deliverable:** Shared code has explicit ownership and purpose without creating implementation coupling.

- [x] **Step 1: Define package manifests**

Use private packages named `api-contracts`, `ui`, `auth`, and `test-fixtures`, all version `0.1.0` and ESM-compatible.

- [x] **Step 2: Document allowed contents**

`api-contracts` contains generated/view-oriented API contracts; `ui` contains presentational components; `auth` contains UI-server/session helpers; `test-fixtures` contains synthetic fixtures only. None may contain database credentials or direct database clients.

- [x] **Step 3: Keep packages unreferenced until needed**

Do not add dependencies between these packages or to `ops-console` yet. A package becomes shared only when a second consumer exists or the contract boundary is explicit.

### Task 4: Repository boundary documentation

**Files:**
- Create: `ui/decisions/0003-modular-monorepo.md`
- Modify: `ui/README.md`
- Modify: `ui/data-contracts/README.md`

**Deliverable:** The repository shape, runtime separation, CI expectations, and deferred tooling choices are recorded next to the UI specs.

- [x] **Step 1: Record the monorepo decision**

Document one repository, separate deployables, deliberate sharing, independent secrets, and the rule that code-repository structure does not replace tenant isolation.

- [x] **Step 2: Link the decision from UI documentation**

Update the UI README and contract notes to reference the modular monorepo layout and generated contract boundary.

### Task 5: Verification

**Files:**
- No production code changes beyond the manifests and documentation above.

**Deliverable:** Workspace configuration is syntactically valid and discoverable by pnpm.

- [x] **Step 1: Run package-manager checks**

Run `pnpm install --lockfile-only`, `pnpm run workspace:list`, and `pnpm --filter ops-console list --depth -1`.

- [x] **Step 2: Check repository status**

Confirm only the intended workspace manifests, lockfile, and UI documentation are added. Do not commit generated `node_modules` or secrets.
