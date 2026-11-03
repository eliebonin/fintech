# Dependency security remediation implementation plan

> **For agentic workers:** Execute sequentially using superpowers:executing-plans. Preserve the current checkout and unrelated edits. Do not commit or push without a user request.

**Goal:** Resolve point 2 of the 30 October security review: vulnerable locked JavaScript/Python dependencies and missing recurring dependency checks.

**Architecture:** Keep the existing pnpm workspace and hashed pip-tools lock. Upgrade affected packages within the current framework/tooling families; use native pnpm auditing and the maintained PyPA audit action in a separate read-only CI workflow.

**Tech stack:** Next.js 16, Vitest 4, Python 3.11 locally/3.12 in CI, pytest 9, pnpm 10, pip-tools and GitHub Actions.

**Spec:** The user authorised security-review point 2 only. Acceptance is zero reported vulnerabilities in both complete lockfiles, installable hashed Python requirements, unchanged generated API contracts, compatible focused tests/typechecks/production build, and fail-closed scheduled/PR/manual audits. Other security findings and operating data are outside this change.

## Constraints and review focus

- Preserve the existing application feature set, financial arithmetic, identity/rights controls and retained evidence.
- No ignored advisories, disabled dependency families or development-package exclusions to obtain a clean scan.
- Preserve existing pins where possible; record necessary resolver changes instead of broadly upgrading unrelated dependencies.
- Verify resolved transitive versions, including sharp, source-map-js, js-yaml and both Vitest consumers.
- Pin added GitHub Actions to verified immutable commits; scheduled jobs must fail on advisories or audit-service errors and request read-only repository permission.
- Keep audit tooling separate from the application environment and never scan an operating database.
- Use the existing feature branch in place: the user previously chose this checkout and sequential implementation. No new worktree or subagents.

## Tasks

- [x] Capture the failing lockfile audit baseline and current manifest/lock hashes.
- [x] Verify maintainer patch guidance and available patched package versions.
- [x] Raise affected manifest floors, regenerate the shared pnpm lock and hash-pinned Python lock, then install the resolved versions.
- [x] Re-audit both complete locks and check installed-version parity.
- [x] Add a separate scheduled, PR, push and manually dispatched dependency-audit workflow using pnpm and a pinned PyPA action.
- [x] Run focused Python and frontend compatibility checks, typechecks, contract parity, a production build and bounded browser acceptance where available.
- [x] Record versions, primary sources, verification and limitations in a delivery record; update the platform capability and root knowledge/finding references.
- [x] Review the scoped diff and local links, preserving all unrelated working changes.

## Decisions

- Dependency scans are the initial failing checks for this configuration-only remediation; do not add tests that merely mirror version literals.
- Keep the existing secret-scanner configuration untouched because it is separate security-review point 4.
- Do not restart operating services or migrate/seed the operating database for dependency verification.
