# Tenant organisations lightweight implementation plan

**Goal:** One tenant organisation workspace for counterparties and executing brokers,
with private labels/codes/notes and unchanged historical booking references.

**Spec:** [Full direction](../specs/2026-10-16-tenant-organisations-design.md).
This approved implementation slice supersedes its wider first-delivery scope:
issuer/custodian controls, GLEIF ingestion and new permissions are deferred.

**Architecture:** Existing `trade_selection_policy/member` remain the single source
of role eligibility for both old and new APIs and booking. Add only tenant metadata;
the register reads the union of those profiles and existing role memberships.
No role-list backfill, dual-write mirror or new booking eligibility algorithm.
Reuse TRADE_CONFIGURE authority and the existing Trading module requirement.

**Tech stack:** SQLAlchemy/PostgreSQL, FastAPI audited router, Next 16/React,
existing context transport, pytest disposable database runner, Vitest/Playwright.

## Global constraints

- No operating database migration, grant, booking or source import without separate
  activation authority. Preserve 519 pre-existing working changes; no commit/push.
- Work in the current feature checkout, as previously requested, sequentially.
- Preserve LEGACY/no-policy versus CURATED/empty-list semantics.
- Role activation is explicit, acknowledged and audited; editing notes never
  activates or changes an unconfigured list. No new switch to legacy mode.
- All writers share the existing tenant advisory lock; optimistic profile/role
  revisions protect old/new editor concurrency. Exact command replay is retained.
- Historical trades and instrument issuers are never rewritten. Trader lists stay.
- No total organisation cap; bounded server-side search/count/pagination only.

## Review focus

1. Notes and metadata remain tenant-private even for a shared organisation.
2. Old whole-list publication and new incremental changes see the same membership.
3. Unknown save outcome retains exact payload/key; refresh failure is not rejection.
4. Inactive canonical organisations remain inspectable but cannot be newly enabled.
5. An empty curated list denies new selection, while a missing policy stays legacy.

## Task 1: Domain and additive storage — complete

- [x] Write failing `tests/test_tenant_organisations.py`: tenant metadata isolation,
  legacy versus empty, old/new eligibility equivalence, role independence, stale
  revisions, exact replay/conflicting key, inactive organisation and paged search.
- [x] Verify RED with owned disposable PostgreSQL runner.
- [x] Add `tenant_organisation_profile` in `security_master_schema/models.py` and
  migration 95, with no seed/grants and no changes to role tables.
- [x] Add `apps/reference_api/tenant_organisations.py`: `list_organisations`,
  `organisation_detail`, `save_organisation`, `activate_role`; all accept validated
  tenant/actor, enforce TRADE_CONFIGURE and reuse original eligibility tables.
- [x] Verify GREEN plus existing governed trade-configuration tests.

## Task 2: API and BFF — complete

- [x] Add HTTP tests for foreign actor/tenant, unknown organisation, strict schemas,
  validation/conflict responses and rollback after audit failure.
- [x] Add typed contracts/routes under `/v1/trade-configuration/organisations`,
  `organisations/candidates`, `organisations/{id}`, and `organisation-roles/{role}`.
  Reuse audited transaction dependency and safe problem responses.
- [x] Permit only these paths through existing trade-configuration BFF/context guard.
- [x] Run domain/API/booking-annotation affected tests; regenerate/check contracts.

## Task 3: Organisation workspace and navigation — complete

- [x] Write failing UI/model tests, then implement
  `/tenant-profile/organisations` with register, paged local-reference search,
  metadata/role editor, explicit curated activation and retained history.
- [x] Preserve stale-context and uncertain-outcome protocols, use named inputs,
  real loading/error/empty states and controlled focus.
- [x] Link from tenant profile and replace counterparty/broker editors in Trade
  configuration with a link; retain trader editor and historical audit.
- [x] Verify focused Vitest/type checks and isolated browser edit/recovery cases.

## Task 4: Assurance and documentation — complete

- [x] Run broader affected backend tests, frontend suite and production build where
  practical. Do not run the entire Python suite by default.
- [x] Review changes separately for role-policy equivalence, authority, audit,
  concurrency and non-mutating historical reads; fix evidenced regressions.
- [x] Update capability F58, map and delivery record with exact evidence and limits.

## Execution ledger

- Task 1: RED missing service; 26 new/existing domain tests passed after implementation.
  Additive migration 95 verified in disposable databases only.
- Task 2: audited API and BFF paths implemented; full-API request-audit success and
  rollback verified. Final affected backend cohort: 69 passed, 33 existing warnings.
- Task 3: UI initially RED for missing component. Browser fixture required an
  installed Chrome channel and test-only Next Link adapter; no dependency install
  or production link/security changes were used to make the harness work.
- Task 4: author self-review found pagination using draft rather than applied
  filters and incomplete-success acceptance. Both regressions reproduced RED and
  passed after fixes. Final frontend 928 tests, browser 15 tests, TypeScript and
  optimized build passed. No full Python run or independent reviewer used.
- Contract export check passed; generated output hashes matched across generation.
  The repository's generate:check exits nonzero because it compares uncommitted
  generated contracts against HEAD, including pre-existing work; not a clean check.
- Ruling: tenant labels/codes are presentation in this register; existing booking
  labels stay shared. This avoids altering booking contracts in the first slice.
- Operating activation remains separate: no migration/grant/operating financial
  write, app restart, commit or push. No operating app listeners remained at check.

The checkbox steps above/below describe the executed sequence; completion and
verification evidence are this ledger and the linked delivery record.

- Pre-flight: Task 1 produces original-table role state and typed dictionaries;
  Task 2 contracts and Task 3 client must match them. No duplicated role storage.
- Ruling: reuse TRADE_CONFIGURE for this trading-only slice; a broader organisation
  authority can be designed when non-trading consumers are implemented.
- Ruling: retain current checkout and self-review, following user preference for
  sequential work. Existing dirty changes are not part of this delivery.
- Research (17 October): opened OWASP Authorization Cheat Sheet, GOV.UK table
  guidance and PostgreSQL 18 explicit locking. They inform request-level permission
  checks, semantic tables and transaction-scoped concurrency; our exact schema,
  scope and revisions are project choices, not regulatory requirements.

Sources: [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
[GOV.UK](https://design-system.service.gov.uk/components/table/),
[PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html).
