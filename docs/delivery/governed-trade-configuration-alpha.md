# Governed trade configuration alpha — 2026-10-01

UI update: [Trade configuration UI refresh](trade-configuration-ui-alpha.md)
documents the list-first management screens, contextual editors and updated
keyboard/error/confirmation behavior. The governance rules below are unchanged.

## Entry point and delivered workflow

Tenant profile → **Manage trade configuration** opens
`/tenant-profile/trade-configuration`. Management requires an active tenant
administrator membership and the TRADING module. The API enforces these rules
independently of navigation. The page separates four areas:

1. Standard fields: tenant-curated counterparty, executing broker and trader
   eligibility. These reference canonical organisation/person identities, never
   custom dropdown labels. Trader eligibility also requires current active
   account and tenant membership; adding a selection does not grant login rights.
2. Custom fields: create typed definitions (TEXT, INTEGER, DECIMAL, DATE, BOOLEAN,
   REFERENCE), retire definitions, or publish immutable replacements. Codes and
   definition IDs are distinct from display labels. Different business meanings
   require a new code; the application cannot infer meaning from free-text labels.
3. Reference catalogues: create a tenant-owned draft catalogue, publish entries,
   publish the catalogue, reuse it across fields, correct entry labels through
   immutable versions, and retire entries/catalogues. A new dropdown can use an
   existing catalogue or a newly created one; creation is available in the same
   management experience, not inside the booking ticket.
4. Audit history: bounded, tenant-scoped publication/correction/retirement events,
   including actor, timestamp, rationale and complete published eligibility IDs.

The dedicated Book trade page searches eligible parties by role and controlled
catalogue entries by code/label. It submits record-version IDs, not labels.
Review shows selected catalogue codes/labels; historical detail shows the booked
label and record version even after corrections or retirement.

## Migration and compatibility

Migrations `20261001_51` and `20261001_52` add tenant catalogues, record versions,
relational reference assignments, eligibility policies/members, append-only
configuration events, immutable history guards and source/ownership checks.
Migration `20261001_53` retires every active embedded CHOICE definition and
publishes its next version as REFERENCE, backed by a dedicated tenant catalogue.
Original option labels, field code, requiredness, description and ordering are
preserved. Catalogue-code collisions never overwrite another list. An append-only
`LEGACY_CHOICES_MIGRATED` event records old/new definition IDs and the exact
option-to-record-version mapping under a suspended, non-authenticating service
identity. No trade values, IDs or durable booking replay fingerprints are rewritten.
Historical CHOICE definitions remain readable and support unchanged idempotent
replay, but cannot be created or used for a new booking. API/provisioning validation
and a PostgreSQL insert guard enforce that boundary.

Custom fields show active definitions by default; enable **Include retired
definitions** to inspect history. Each reference field has a **Manage values**
button, including catalogues outside the first search page. `BOOKING_BUCKET` is
now a governed catalogue with CORE, TACTICAL and HEDGE entries, maintained under
**Reference catalogues**. The example JSON and provisioning script use catalogue
codes and governed lifecycle helpers, and publish the complete config atomically.
Rerunning an unchanged configuration is idempotent; edits to existing meaning
must use the management lifecycle rather than provisioning overwrites.

Migration 53 rejects downgrade after conversion; use archival or a backup restore.
Malformed legacy choice lists fail the entire upgrade instead of losing values.
Deploy migrations with trade-configuration writes paused and a database backup.
The example config is a provisioning template, not a reconciliation/overwrite
command: it deliberately reports a conflict if an administrator has changed an
existing field (including requiredness).

### Cleanup verification and test isolation

Use `scripts/run_isolated_python_tests.py` for backend regression checks. It
creates a unique disposable local PostgreSQL database, migrates it, redirects
legacy hard-coded app database URLs inside the pytest process only, and removes
the exact test database after disposing connections. This avoids dependence on
an operator's current tenant settings or changes to their live financial data.

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_trade_property_cleanup.py tests/test_trade_properties.py tests/test_trade_booking_enrichment.py tests/test_trade_configuration.py tests/test_governed_trade_configuration.py tests/test_trade_booking_context.py tests/test_trade_history.py tests/test_trade_history_api.py tests/test_openapi_contract.py tests/test_alembic_offline_sql.py tests/test_migrations.py -q
pnpm --filter ops-console exec vitest run --maxWorkers=2
pnpm --filter ops-console typecheck
pnpm --filter ops-console build
```

The populated migration regression verifies unchanged booked values and durable
replay, exact option labels, catalogue/code collisions, atomic rollback for
malformed lists, the new database insert guard and protected downgrade. Governed
provisioning tests cover unchanged replay without duplicates and complete
rollback after invalid configuration. Direct catalogue reads check tenant scope.
Local migration verification compared every existing trade row before/after:
all nine were unchanged; active embedded-choice definitions went from one to zero.

Cleanup verification results: 74 targeted backend checks passed in the isolated
database (including populated migration, empty downgrade and offline SQL), all
200 frontend tests passed, and frontend typechecking/production build passed.
OpenAPI export is current and TypeScript regeneration is deterministic. Signed
local HTTP checks returned 200 for configuration, direct catalogue lookup and
entry browsing. The API was restarted to serve the new route. Existing required
field settings, including Allocation weight, were retained. The complete Python
suite was not rerun for this cleanup; the commands above cover its affected areas.

**Eligibility transition is explicit.** A role without a published policy retains
legacy eligibility (active shared organisations, or eligible tenant members).
The management page labels this as shared eligibility; the underlying policy
state is LEGACY. Publishing its first eligible list
activates CURATED mode. An empty published list permits no selection for that
optional role; it does not delete canonical records. This avoids silently breaking
existing tenant workflows. It is not a credit, sanctions or regulatory approval.

New and existing tenants currently use this same explicit transition. Deployments
requiring curated eligibility from inception should provision policies during
tenant onboarding rather than assume that absence of a policy means denial.

The schema has no fixed Field X slots. The alpha uses a safety quota of 1,000
active definitions/tags and 1,000 records per published standard eligibility list.
These are safety limits to revisit with capacity testing, not preallocated
columns. Catalogues/entries and audit are searched/paged in batches
of 25 (API catalogue/entry reads permit at most 100). Field definitions currently
load together; large-field administration is a subsequent UX improvement.

Migration 51 rejects downgrade of populated governed configuration: dropping
assignments or record versions would destroy historical evidence. Empty test
installations can downgrade normally. Preserve a database backup;
rollback requires an archival migration or backup restore, not routine downgrade.
No existing trade, definition, canonical organisation/person or taxonomy is deleted.

## Integrity and lifecycle

- Scalars and references use separate assignment tables. Reference targets have
  actual foreign keys; there are no arbitrary table names, SQL sources or URLs.
- Tenant-scoped validation checks field binding, catalogue ownership and active
  record status. PostgreSQL guards also reject cross-source reference assignment,
  scalar substitution for reference fields, history mutation and audit rewriting.
- Tenant advisory locks serialize catalogue, field and eligibility publication
  with booking validation. Booking and child writes remain atomic. Current
  eligibility applies at booking time, not a historical trade-date policy.
- Retired record codes cannot be recycled for a new meaning. Label corrections
  retain record identity but create a new version; old trades retain the old one.
- A catalogue with any active field binding cannot retire. Required reference
  fields need at least one active entry; retirement of their last selectable
  entry is blocked until affected required fields are replaced or retired.
- Eligibility edits use optimistic version checks. Duplicate publication with
  the same expected version and content replays; stale different content conflicts.
  Catalogue/entry creation reuses identical existing content; correction retries
  recognise their immediate successor. These are state-based retries, not a
  general durable management-command idempotency ledger.
- Financial trade booking retains its existing durable idempotency mechanism.
  Fingerprints canonicalise reference UUIDs without requiring current eligibility,
  so an exact booking retry still works after retirement. Changed selection with
  the same booking key conflicts.
- The BFF derives tenant/actor from the selected session and requires an expected
  tenant header for configuration reads/writes. A stale page cannot mutate the
  newly selected tenant. API searches are bounded; membership is rechecked.

## Deliberate alpha boundaries

This is not a full MDM system. Additional platform-source adapters (such as a
currency-valued custom annotation), external trader onboarding without accounts,
multi-select, hierarchies, dependent values, field applicability by trade type,
formulas, maker-checker workflows, bulk import and catalogue metadata corrections
are deferred. Shared organisation/person names in existing first-class trade
views still use canonical current names; immutable booked custom-catalogue labels
are separate from that behaviour. No claims of regulatory approval are made.

The earlier proposed currency example is not delivered in this slice. Canonical
platform identities are used for standard parties, while tenant-owned reference
catalogues supply new custom dropdowns. Existing global instrument taxonomies
are not repurposed or exposed as tenant-editable datasets.

## Best-practice evidence and project decisions

Sources opened and reviewed on 2026-10-01; these are design inputs, not standards
mandating this exact fintech implementation:

- [Microsoft Dataverse choices](https://learn.microsoft.com/en-ca/power-apps/maker/data-platform/create-edit-global-option-sets),
  updated 2022-10-10: reusing lists prevents inconsistent duplicates; sharing
  every single-use list creates management overhead. Applied as explicit
  create-or-reuse catalogue selection, not an automatic catalogue for every field.
- [Reltio lookups and canonical values](https://docs.reltio.com/en/applications/rdm/rdm-at-a-glance/rdm-operation/lookups-and-canonical-values),
  updated 2026-09-25: controlled lookup types and canonical values standardise
  dropdown/search/API use. Applied to distinct catalogue, record and consuming
  field identities. Reltio's transcoding/cache semantics are not copied.
- [OWASP multi-tenant security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html),
  current page reviewed 2026-10-01: client tenant identifiers are selectors, not
  authority; enforce membership and resource isolation. Applied to BFF session
  context, API authorisation, tenant-scoped queries and reference validation.

## Original governed-domain verification (before cleanup and UI refresh)

Lightweight integer/reference normalisation tests were written and observed
failing before implementation. Rollback-backed tests then cover record version
history, retirement, exact booking replay, source mismatch, no partial trade,
stale eligibility edits, invalid members, blocked required-field dead ends,
database immutability, paginated search and HTTP configure/publish/read flow.
Frontend checks cover navigation, scalar/reference payload validation, BFF
tenant-switch rejection and trusted-context forwarding. Browser interaction validation is reported
separately and must not be inferred from static rendering tests.

The following results describe the original governed-domain delivery, not the
latest migration head or UI test count. Subsequent cleanup results are above;
the latest frontend evidence is in [the UI refresh record](trade-configuration-ui-alpha.md#verification).

Verification completed for that original delivery:

- Final full Python run: **332 passed**, 430 deprecation warnings, 1,012.37
  seconds. Three additional isolation/lock/revocation tests added after that
  run's collection passed separately within the 16-test focused module below.
  The first full run exposed the empty-installation downgrade guard and a route
  introspection test's assumption about FastAPI router wrappers. The migration
  now protects populated history while permitting empty downgrade; the test
  checks published OpenAPI paths. Both corrections passed the final full run.

- 16 focused governed-configuration tests passed, including real foreign-tenant
  catalogue records, revoked membership and an independent connection checking
  the tenant advisory lock is held.
- Frontend: 199 tests in 59 files passed with `vitest run --maxWorkers=2`.
  An initial unrestricted run timed out in an existing rendering test; the two
  subsequent bounded runs passed without raising its timeout or weakening it.
- Production build and frontend TypeScript checks passed.
- OpenAPI exporter `--check` passed. Generated TypeScript was regenerated and
  its SHA-256 hash was identical before/after a second generation. The existing
  `generate:check` script compares to Git HEAD and therefore reports expected
  uncommitted contract changes; this is not evidence of generation drift.
- Local database migration head is `20261001_52`. Empty-installation upgrade/
  downgrade and the OpenAPI tests passed together (4 tests).
- Live API health and tenant-scoped catalogue read returned HTTP 200. An isolated
  tenant session through the frontend returned HTTP 200 for the configuration
  page with its TENANT GOVERNANCE heading. No real financial trade or persistent
  example catalogue was created for this smoke check; functional booking tests
  used rolled-back database transactions.
