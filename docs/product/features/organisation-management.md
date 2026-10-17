# Organisation reference and tenant management

**Status:** Maintained capability record  
**Last reviewed:** 2026-10-17

## F58 Shared directory and tenant organisations

- **Desired outcome:** A maintained global LEI directory; tenant-selected working
  organisations with multiple purpose-specific roles, private configuration and
  auditable activation/deactivation.
- **Overall status:** PARTIAL. Trading-only tenant workspace is implemented and
  isolated-tested; migration 95 is locally applied and register loading verified.
  Full directory and
  non-trading consumers remain undelivered.
- **Backend today:** [schema](../../../security_master_schema/models.py),
  [organisation options](../../../apps/reference_api/repository.py) and
  [curated trade-role service](../../../apps/reference_api/governed_trade_configuration.py),
  [tenant register/commands](../../../apps/reference_api/tenant_organisations.py) and
  [typed audited endpoints](../../../apps/reference_api/organisation_routes.py).
  Private profile metadata is additive; role tables/enforcement remain original.
  Missing-policy legacy behavior differs from an explicitly empty curated list.
- **Frontend today:** `/tenant-profile/organisations` provides register/search,
  private settings, independent counterparty/broker membership, explicit activation
  and recent history. Linked from Tenant profile; old party editors link here.
  Trader curation remains in Trade configuration. Add searches existing platform
  organisations, not GLEIF. [Delivery/verification](../../delivery/tenant-organisations-20261017.md).
- **Proposed design and staged delivery:** [16 October design](../../superpowers/specs/2026-10-16-tenant-organisations-design.md).
- **Trade-offs/weaknesses:** Full directory needs maintained imports, search indexes
  and provenance. Identity matching and legacy eligibility transition require care.
  Issuer facts must remain separate from tenant issuer-selection preferences.
- **Remaining work:** Live edit/activation walkthrough beyond the successful
  register-loading smoke check. Issuer/custodian consumers, broader authority, GLEIF identity
  matching/ingestion/recovery and full-directory search capacity remain separate phases.
  Existing booking labels are not changed by tenant register labels.
- **Deliberate exclusions:** Full KYC/AML, screening, credit limits and accounting;
  selecting an organisation does not establish those approvals.
- **Evidence boundary:** Focused disposable backend tests, full frontend unit suite,
  isolated component-browser journeys plus actual Next context guard and production
  build; see delivery for counts/limits. Migration 95 was applied with approval and
  live register loading checked; no operating entity import, role-list activation,
  financial write, commit or push. Link routing uses a component-fixture adapter;
  these browser tests do not establish full live tenant navigation acceptance.
