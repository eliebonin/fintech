# Decision 0003: modular monorepo foundation

## Decision

Keep one Git repository for the platform, with separate deployable
applications under `apps/` and deliberately shared TypeScript packages under
`packages/`. The first application is `apps/ops-console`; additional portals
or steward applications are added only when their workflows, release cadence,
or security boundary genuinely diverge.

The existing Python security-master code remains a first-class sibling of the
frontend workspace. It is not converted into a JavaScript package and is not
imported directly by browser code.

## Boundaries

- Applications expose deployable shells and may consume shared package APIs.
- Applications must not import another application's internals.
- Shared packages are promoted only after a second consumer or an explicit
  contract justifies them.
- API contracts are generated/view-oriented; they do not mirror SQLAlchemy
  tables or expose database topology.
- Runtime tenant isolation, authorization, and entitlement enforcement remain
  API/database responsibilities; repository structure is not a security
  boundary.
- Each deployable receives independent environment variables, Auth0 settings,
  secrets, CI permissions, and release controls.

## Tooling decision

Use pnpm workspaces first. The workspace is intentionally framework-neutral and
does not add Turborepo or Nx yet. Add task orchestration/caching when multiple
apps or shared packages create measurable build/CI duplication; add stronger
module-boundary tooling if code-ownership rules cannot be enforced through
package APIs, lint rules, and review ownership.

## Consequences

Cross-cutting API/schema changes can be reviewed atomically, while each app can
still be built and deployed independently. The root lockfile provides one
dependency view for the TypeScript workspace. Python tests and Alembic
migrations remain separate commands in CI and are not silently coupled to a
frontend package install.
