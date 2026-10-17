# Tenant organisations: lightweight trading rollout

**Status:** Implemented; focused verification complete, local activation verified
**Date:** 2026-10-17  
**Scope:** Tenant register, counterparties and executing brokers only  
**Capability:** [F58](../product/features/organisation-management.md#f58-shared-directory-and-tenant-organisations)

## What changed

The first two phases are deliberately narrowed to existing trading parties.
Issuer/custodian controls, a global GLEIF import, directory matching, review queues,
scheduling and KYC/credit workflows are not included.

- New page: `/tenant-profile/organisations`, linked from Tenant profile for users
  granted TRADE_CONFIGURE. This reuses the Trading module requirement and existing
  delegated authority; no new grants or administrator bypass were added.
- Search/paged register and Add organisation search of existing platform records,
  by shared name, LEI, tenant label or internal code. Full counts and role filtering
  are server-side; draft searches do not change the applied pagination query.
- Private tenant labels, uppercase internal codes and notes. These display in the
  new register, not a rewrite of shared legal names or existing booking labels.
- Counterparty and executing-broker membership is independently editable.
  Existing lists remain authoritative; there is no mirror, bulk backfill or new
  booking eligibility algorithm. Trader management stays in Trade configuration.
- The old counterparty/broker UI editors are replaced by a link to Organisations.
  Existing whole-list APIs remain compatible and share the same lock, memberships
  and role revision with the new incremental writer.
- Missing policy still means legacy shared eligibility. A curated empty list still
  allows none. Activation is an explicit, reasoned, acknowledged command; it starts
  with a selected organisation or, after a clear warning, an empty list. Adding
  private notes never activates a role. No reset-to-legacy workflow was added.
- Inactive shared records can be inspected and removed from lists, but not newly
  enabled. Historical trade party references are preserved.
- Changes are transactional with retained audit, actor, reason and exact command
  replay. Stale profile or role revisions conflict rather than overwrite edits.
  Unknown outcomes retain the same payload/key; confirmed saves followed by failed
  refresh remain visibly saved and lock edits until state reload succeeds.
  Successful BFF responses explicitly use `Cache-Control: private, no-store`.
- Recent detail history shows the latest 20 profile commands. Full existing audit
  pagination, including old role-list publications, remains in Trade configuration.

## Implementation map

| Boundary | Owner |
| --- | --- |
| Tenant-private metadata only | `trd.tenant_organisation_profile` in [models](../../security_master_schema/models.py) |
| Additive migration, no data backfill or grants | [revision 95](../../alembic/versions/20261017_95_tenant_organisation_profiles.py) |
| Register, details, revision checks, incremental membership and replay | [tenant_organisations.py](../../apps/reference_api/tenant_organisations.py) |
| Typed audited endpoints | [organisation_routes.py](../../apps/reference_api/organisation_routes.py), included in [trade configuration router](../../apps/reference_api/trade_configuration_routes.py) |
| Original booking/legacy list enforcement | [governed_trade_configuration.py](../../apps/reference_api/governed_trade_configuration.py), unchanged |
| Permission-checked page | [organisations/page.tsx](../../apps/ops-console/src/app/tenant-profile/organisations/page.tsx) |
| Browser workspace and typed response checks | [feature folder](../../apps/ops-console/src/features/organisations/) |

Endpoints under `/v1/trade-configuration`:

- `GET /organisations`: tenant register, q/role/limit/offset.
- `GET /organisations/candidates`: existing active platform records, q/limit/offset.
- `GET /organisations/{id}`: shared identity plus this tenant's profile/roles/history.
- `POST /organisations/{id}`: versioned profile and incremental curated-role edits.
- `POST /organisation-roles/{role}`: explicit initial curated-list activation.

The BFF allows only these specific paths and forwards trusted tenant/actor context.
The shared Next write-context guard remains in place. Browser identity fields are
not authoritative and extra request fields are forbidden.

## Research used for implementation

Opened/read on 2026-10-17:

- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  enforce permissions on every request. Applied through existing middleware and
  domain authority checks, including before idempotent replay; no UI-only control.
- [PostgreSQL 18 explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html):
  transaction-scoped locks coordinate concurrent changes. Reused the existing tenant
  catalogue advisory lock so legacy/new list writers and booking annotation checks
  cooperate; profile/role revisions detect edits prepared against older state.
- [GOV.UK table guidance](https://design-system.service.gov.uk/components/table/):
  semantic captions and row/column headings support scanning. Applied to a compact
  paged register with separate identity inspection and editing, not a certification
  of full accessibility or a prescribed financial workflow.
- Installed Next 16.3.4 forms guide: server-side authority/validation and pending
  states. Kept the established BFF transport rather than introducing Server Actions.

The shared-identity/multiple-role rationale and GLEIF sources remain in the
[broader design](../superpowers/specs/2026-10-16-tenant-organisations-design.md#source-backed-rationale).

## Verification record

- Initial backend RED: missing service; first new+existing domain/API cohort:
  **26 passed**. Expanded six-module affected cohort: **65 passed** in 32.00 s,
  including actual booking rejection after counterparty removal and unchanged
  historical party reads, authorized other-tenant isolation and audit-failure rollback.
- First expanded run had two new-test fixture errors: missing historical-detail
  API arguments and an incomplete/incorrect entitlement fixture. Corrected the tests
  to the actual signature/schema; production authority/constraints were not relaxed.
- Initial UI RED: missing component. Focused UI/configuration cohort: **11 passed**.
  Malformed-success validation and pagination issues found in self-review were
  reproduced as failing tests before fixing them.
- Full frontend run before final self-review fixes: **925 tests / 197 files passed**.
  Full browser run at that point: **14 passed**, including actual Next context guard.
  Final reruns: **928 frontend tests / 197 files passed**, **15 browser tests passed**
  (four organisation cases), TypeScript passed, and optimized production build passed.
- Final seven-module backend cohort: **69 passed** in 34.28 s, including the new
  full-application request-audit retention/failure-rollback cases and existing request
  audit atomicity tests. The 33 warnings are existing SQLAlchemy/Starlette deprecations.
- A final **14-test** organisation-only rerun passed after adding explicit HTTP
  foreign-tenant/unknown-ID/pagination/strict-boolean assertions. Counts overlap.
- Chrome was already installed; Playwright's bundled browser was missing. Used
  `PLAYWRIGHT_CHANNEL=chrome`, with no browser/dependency installation. The Vite
  component fixture uses a test-only anchor adapter for `next/link`; it tests forms,
  state/retry and pagination, not real Next navigation. Context guard uses actual Next.
- OpenAPI export check passed. `contract:generate:check` compares against Git HEAD
  and exits nonzero on this intentionally dirty checkout (including older API work).
  This is not evidence of generation drift; repeated-generation hash comparison is
  the working-tree determinism check, and those hashes matched. No generated
  differences were discarded.
- Existing SQLAlchemy Result.tuples deprecation warnings and browser colour-env
  warnings were observed. No full Python repository suite was run.
- Separate author self-review checked original-table role equivalence, authority,
  audit, profile/role revision conflicts and historical read preservation. It found
  the draft-search pagination defect and insufficient malformed-success validation;
  both now have failing-before/passing-after regressions. No independent reviewer
  or live operating navigation acceptance is claimed.

## Rollout and deliberate limits

### Approved local activation — 17 October follow-up

With explicit user approval, applied `20261017_95` to the verified local
`platform_secm` database on port 54329. Alembic current and sole head both resolve
to 95; no other migration is pending. Confirmed `trd.tenant_organisation_profile`
exists. The already-running API uses the new table without restart.

Reloaded the actual Organisations page as the first tenant's existing
administrator: the service error is gone, both legacy eligibility policies load,
and the tenant register shows zero selected organisations. This is an expected
empty register, not a missing global directory. No list was activated, entity
selected, permission changed, financial write made or GLEIF data imported.
Live edit/activation walkthrough remains separate from this read-only smoke check.

The original rollout checklist and isolated-verification boundary below describe
the implementation stage before this approved activation.

1. Apply additive migration 95 to the operating local DB only with activation
   authority. It creates private metadata storage; it does not curate any list,
   change rights, grant permissions, upload entities or touch historical trades.
2. Restart the API and build/start the frontend when requested. The app was explicitly
   stopped before this task; this implementation does not restart operating services.
3. Inspect existing lists on the Organisations page, then edit one synthetic party.
   A missing list remains unrestricted until an operator explicitly activates it.
4. Broader directory ingestion and issuer/custodian consumers remain separate work.

No GLEIF download, operating migration, operating financial write, service activation,
Git commit or push is implied. Verification is isolated synthetic assurance, not
full-directory load capacity, production authentication or financial sign-off.
