# Shared entity directory and tenant organisation roles

**Status:** Wider phased design; trading-only slice implemented and locally activated 17 October
**Owner:** Product and engineering  
**Recorded:** 2026-10-16  
**Capability:** [F58](../../product/features/organisation-management.md#f58-shared-directory-and-tenant-organisations)

## 17 October scope decision

The user approved planning and implementation of a lightweight first slice:
tenant organisation settings and counterparty/broker lists only. The
[execution plan](../plans/2026-10-17-tenant-organisations-alpha.md) and
[delivery/evidence](../../delivery/tenant-organisations-20261017.md) take precedence
for that slice. Existing role tables remain authoritative, with only private
profile metadata added; no role backfill or duplicated eligibility storage.
Issuer/custodian controls and GLEIF ingestion remain later phases. Earlier
"not implemented" statements below describe the 16 October baseline, not this
subsequent delivery.

## Intent

Provide a maintained, searchable global LEI directory and let each tenant select
organisations for several operational purposes without duplicating legal entities.
Tenant configuration must remain private. Adding an organisation is not KYC,
credit approval or permission to use it in every workflow.

The user agreed the shared-directory/tenant-selection direction and requested a
concrete, non-invasive, maintainable plan. This records that proposal, not approval
of a completed implementation, operating migration or full-directory download.

## Current foundations inspected

- [Schema](../../../security_master_schema/models.py): `organisation`,
  effective-dated `organisation_identifier`, and `instrument_party_role` already
  represent identity and factual instrument relationships.
- The same schema has `trade_selection_policy`, `trade_selection_member` and
  append-only `trade_configuration_event` for existing curated trade roles.
- [Trade configuration](../../../apps/reference_api/governed_trade_configuration.py):
  `restrict_selection`, `assert_selection`, `selection_view`, `publish_selection`
  and `selection_candidates` own current counterparty/broker/trader selection.
  A missing policy means LEGACY/unrestricted selection, subject to the other
  existing eligibility checks. An existing policy with no members means none
  are eligible. Preserve this distinction during transition.
- [Organisation options](../../../apps/reference_api/repository.py):
  `list_organisations` searches active operational organisations. It is not a
  complete GLEIF directory or the proposed tenant organisation workspace.

This was targeted static inspection, not a complete organisation-consumer audit.
No new workflow, migration, import or acceptance tests exist from this task.

## Recommended model and boundaries

1. **Shared sourced directory:** dedicated GLEIF records, provider release/source
   metadata and import progress. Retain LEI registration status separately from
   legal-entity status; retain provenance and changes. A directory entry does not
   automatically become an operational organisation.
2. **Operational organisation:** reuse the existing stable organisation ID and
   identifiers. Selecting a directory entry links an existing organisation or
   creates one through a controlled command. Match by LEI, not name alone;
   ambiguous existing matches require review. Never infer a corporate parent from
   a similar name or manufacture a parent to satisfy a schema foreign key.
3. **Tenant membership:** tenant + organisation, with private display label,
   internal code, notes, current state and revision/audit evidence.
4. **Tenant role eligibility:** independently enable counterparty, executing
   broker, issuer selection and custodian/account-provider use. One organisation
   can hold multiple roles. Use controlled role codes, not arbitrary permission
   strings. These roles are eligibility data, not user-access permissions.
5. **Factual instrument relationship:** an instrument's issuer remains in
   `instrument_party_role`. A tenant issuer list controls new selection, never
   the instrument's historical issuer or the visibility of existing instruments.

Retain support for existing organisations without an LEI. Do not require an LEI
for every broker, exchange, custodian or tenant-created operational organisation.
Source-owned legal facts are not overwritten by tenant labels or notes.

## Incremental delivery plan

### A. Tenant register and compatibility

- Finish the focused consumer inventory, including issuer creation, booking,
  configuration, cash balances and existing organisation lookup endpoints.
- Add tenant membership/role state and retained changes using additive migrations.
  Define explicit read/manage actions in the existing permission system; grant
  management to intended tenant administrators, without bypassing endpoint checks.
- Reuse existing organisation IDs and seed the new role assignments from current
  curated counterparty/broker selections. Preserve no-policy versus empty-policy
  semantics; activation must not silently broaden or narrow existing eligibility.
- Use one organisation eligibility service and compatibility adapters for existing
  consumers. Move reads/writes together in a verified migration; do not maintain
  two independently editable sources of truth or permanent dual-write syncing.
- Leave TRADER/person eligibility on its existing path. Do not expand the trade
  role table into a generic organisation register simply by adding unrelated roles.
- Existing whole-list update quotas must not become a total directory or tenant
  organisation limit. Prefer paged reads and version-checked incremental commands.

### B. Management UI and consumer integration

Proposed route: `/tenant-profile/organisations` (not yet implemented).

- **My organisations:** paged/searchable table, role and state filters.
- **Add from directory:** server-side legal-name/LEI/jurisdiction search, source
  details, identity inspection and explicit tenant selection.
- **Organisation detail:** private tenant settings, independent role state and
  change history. Reuse the same organisation record across purposes.
- Booking shows eligible counterparties/brokers; instrument creation shows enabled
  issuer selections. Cash balances use the relevant account-provider eligibility.
- Link old trade-configuration organisation management to this workspace rather
  than duplicating editors. Preserve existing API compatibility during transition.
- Deactivation prevents new selection, not historical reads. Revalidate eligibility
  at write time so a stale browser selection cannot bypass a role change. Define
  correction/rebooking behavior explicitly before rollout; never rewrite old trades.
- Preserve shared browser context guards, exact-intent recovery, correlated errors,
  database authority checks and transactional audit.

### C. Full GLEIF population

- Prove the workflow using a small sourced fixture before loading the complete
  directory. This is delivery order, not a reduced final universe.
- Implement a separate reference-data ingestor, not browser automation or coupling
  to the market-price ingestor. Initial Golden Copy import, then incremental updates.
- Validate release/checksum and schema, stage/validate before activation, and retain
  an idempotent run ledger with resumability and clear failures. Changes must not
  become tenant role grants or delete referenced operational organisations.
- Use bounded batches, indexed search and server-side pagination; no dropdown or
  ordinary booking request may load the whole global population.
- Preserve the selected full source release and update watermark. Detect missed
  delta coverage and recover from a suitable full release rather than silently
  accepting a partially updated directory.
- Operating bulk import/migration and activation are separate from isolated tests;
  assess storage/runtime and obtain the required authority before executing them.

## Verification and acceptance

Start with lightweight domain tests, then owned disposable PostgreSQL integration
tests and isolated browser checks. No full repository run is required by this plan.

Acceptance must cover:

- Tenant A's membership, notes, internal codes and role state do not leak to B.
- One organisation can be a counterparty and issuer; disabling one role leaves
  the other intact. Global reference presence grants neither role automatically.
- Repeated selection of the same LEI is idempotent; concurrent selection does not
  create duplicate organisations. Ambiguous matches are visible review failures.
- Existing curated sets, empty sets and legacy modes retain their behavior.
- Deactivated records remain readable on old trades/instruments/cash evidence;
  new writes reject stale or unauthorized selections.
- Optimistic revisions prevent lost edits; mutations and their audit are atomic.
- LEI status changes do not silently become tenant approval decisions. Legal
  entity, LEI registration and tenant role statuses remain distinguishable.
- Interrupted/replayed imports are recoverable; provider corrections retain source
  history and do not rewrite frozen financial evidence.
- Search/count/pagination remain correct beyond one page; query counts do not grow
  per displayed entity and no implicit total-size cap is introduced.

## Trade-offs and exclusions

The directory requires ongoing maintenance, storage and search indexes; it is not
a one-off seed. Compatibility work is necessary because existing role lists have
meaningful legacy semantics. Reuse existing schema and contracts where suitable,
but do not force tenant roles into factual instrument relationships.

No full KYC/AML workflow, sanctions screening, credit limits, settlement/accounting
engine, arbitrary tenant-defined role system or parent-relationship import is in
the first delivery. Directory membership never certifies commercial suitability.
No source or operating data was changed while documenting this proposal.

## Source-backed rationale

Sources opened/read on 2026-10-16 during the preceding best-practice review:

- [EDM Council FIBO](https://edmcouncil.org/frameworks/industry-models/fibo/):
  common party/legal-entity concepts and explicit relationships such as issued-by
  support separating identity from role. We borrow that principle, not its entire
  ontology; it does not prescribe our tenant schema or approval workflow.
- [GLEIF Golden Copy and delta files](https://www.gleif.org/en/lei-data/gleif-golden-copy):
  full and incremental reference-data distribution supports maintained ingestion.
- [GLEIF search guidance](https://www.gleif.org/en/lei-data/lei-search/about-lei-search/how-to-use-lei-search):
  entity status and registration status are separate displayed fields; search and
  history support inspectable identity rather than name-only selection.

The layered schema, UI, role states and delivery sequence are project design
recommendations, not a regulatory requirement or proof of compliance.
