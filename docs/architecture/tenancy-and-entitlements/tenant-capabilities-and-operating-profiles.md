# Tenant capabilities and operating profiles

**Status:** Accepted  
**Content type:** Architecture decision and implementation record  
**Owner:** Platform security and architecture team  
**Last reviewed:** 2026-10-12

## Decision

A tenant may hold several concurrent operating profiles, such as `FUND_MANAGER`, `TRADING_BOOK_MANAGER`, `AMC_MANAGER`, and `STRUCTURED_PRODUCT_DISTRIBUTOR`. Profiles describe the operating model and provide an onboarding recommendation; they are not access grants.

Server-side capability is determined only by an explicit, effective-dated module entitlement. This prevents an apparently harmless profile edit from expanding or removing a tenant's production access. It also avoids a combinatorial catalogue of composite profiles such as `FUND_MANAGER_AND_AMC_MANAGER`.

## Deliberate separation of controls

| Concern | Authoritative control | What it answers |
| --- | --- | --- |
| Tenant data isolation | Tenant routing and isolated tenant overlay database | Which tenant data may be reached? |
| Operating model | `ten.tenant_operating_profile_assignment` | What does the tenant do? |
| Product capability | `ten.tenant_module_entitlement` | Which platform module may server code enable? |
| User authorisation | Tenant membership and application roles | Which individual may act? |
| Data rights | Dataset/licence entitlement | Which provider data may be used or shown? |
| Release rollout | Technical feature-flag service | Is a released capability being progressively enabled? |

Authentication is not tenant isolation or application authorisation; this distinction follows [AWS's tenant-isolation guidance](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/tenant-isolation.html). Azure similarly recommends a licence-entitlement process for customer-specific purchased features rather than using release flags as the long-term entitlement mechanism ([Azure multitenant configuration guidance](https://learn.microsoft.com/th-th/azure/architecture/guide/multitenant/approaches/deployment-configuration)).

## Data model

- `ten.operating_profile`: governed, descriptive catalogue of business operating models.
- `ten.tenant_operating_profile_assignment`: effective-dated, approved assignment of any number of profiles to one tenant.
- `ten.platform_module`: governed module catalogue.
- `ten.operating_profile_module_recommendation`: non-authoritative onboarding template connecting a profile to recommended modules.
- `ten.tenant_module_entitlement`: effective-dated grant, suspension, revocation, or expiry for a tenant/module pair; this is the enforcement input.

The migration prevents overlapping active profile ranges for the same tenant/profile and overlapping `GRANTED`/`SUSPENDED` entitlement intervals for the same tenant/module. The resolver still fails closed if inconsistent data somehow produces two effective grants.

## Capability resolution

For a tenant and as-of business date:

1. Load module entitlements effective on that date.
2. Retain only `GRANTED` rows.
3. Reject ambiguous active grants for the same module code.
4. Return the resulting module-code set to the API service.
5. The API authorises the module operation only after its usual tenant routing and user-role checks.

Profiles do not enter steps 1–4. A provisioning flow may use their recommendations to propose entitlements for approval, but that flow must create explicit entitlement records. Removing `FUND_MANAGER`, for example, does not revoke `FUND_MANAGEMENT`.

## Initial catalogues

Operating profiles: `FUND_MANAGER`, `TRADING_BOOK_MANAGER`, `AMC_MANAGER`, `STRUCTURED_PRODUCT_DISTRIBUTOR`.

Modules: `SECURITY_MASTER`, `MARKET_DATA`, `TRADING`, `VALUATION`, `FUND_MANAGEMENT`, `FUND_OPERATIONS`, `UCITS_CONTROLS`, `AMC_MANAGEMENT`, `STRUCTURED_PRODUCTS`, and `STRUCTURED_PRODUCT_DISTRIBUTION`.

The deterministic demo tenant proves composition with both the fund-manager and trading-book-manager profiles. Its independently granted modules are `SECURITY_MASTER`, `TRADING`, `VALUATION`, and `FUND_MANAGEMENT`.

## Why this is the right boundary

[AWS's multi-tenant building blocks](https://aws.amazon.com/isv/resources/building-blocks-of-multi-tenant/) treats tenant identity, isolation, operations and entitlements as independent platform capabilities. [OpenFeature's evaluation context](https://openfeature.dev/docs/reference/concepts/evaluation-context/) is useful for request-time rollout targeting, but it should not become the legal or commercial system of record for access. Commercial entitlement systems also commonly model feature grants separately from product metadata, as illustrated by [Stripe Entitlements](https://docs.stripe.com/billing/entitlements?locale=en-GB).

This division makes it possible to sell or enable UCITS controls for a fund manager without implying that every fund manager has those controls, while allowing one tenant to operate funds, AMCs, and trading books at the same time.

## Deferred scope

This section originally recorded the September foundation. The later [tenant administration delivery](../../delivery/tenant-access-administration.md) implements request-time action/module enforcement, profile visibility, delegated groups, platform module management and local context switching. These are no longer deferred as local-alpha features. Production identity, commercial provisioning/billing, quotas and periodic access reviews remain separate; see [F01–F06](../../product/features/access-and-strategies.md).

- API middleware and permission-aware UI navigation consume the resolver in the current local alpha; production identity and deployment isolation still require a separate implementation.
- Commercial contract, billing, seat limits, quotas and metering are not yet modelled.
- Local user/group action permissions and tenant administration are implemented; federated identity, group synchronization and periodic access review remain outstanding.
- Technical release flags will remain separate from entitlements; no flag provider is introduced here.
- Platform module changes and tenant administration retain audit events. Commercial approval/provisioning, notifications and full audit-reporting workflows remain outstanding.
- Dataset licensing continues to be resolved independently; possessing `MARKET_DATA` does not grant any vendor dataset.

## Implementation and verification

Implemented in SQLAlchemy metadata and Alembic revisions `20260911_42_tenant_capabilities_and_operating_profiles` and `20260911_43_reconcile_metadata_bootstrap_controls`, with seed catalogues, recommendation templates, a pure resolver, and deterministic demo data.

### Local Docker bootstrap reconciliation

The MVP Docker database had been built through `metadata.create_all()` before revisions 41–42 were adopted. An inventory confirmed that the affected `cfg` and `ten` tables, normal foreign keys, checks and indexes already existed, while Alembic was still recorded at `20260910_40`. It would be unsafe to rerun the historical create-table revisions against those objects.

The explicit local-only reconciliation performed on 2026-09-11 was:

1. Verify all tables introduced by revisions 41 and 42 exist and match the SQLAlchemy metadata-owned columns, ordinary constraints and indexes.
2. Stamp the known metadata-bootstrap state at `20260911_42`; this changes only Alembic's version record and does not alter data or tables.
3. Upgrade to `20260911_43`, an idempotent reconciliation revision which installs the migration-only controls absent from `create_all()`:
   - the approved external-operational-ID effective-period exclusion constraint;
   - the fund/share-class target-validation function and trigger;
   - the active tenant-profile and granted/suspended module-entitlement effective-period exclusion constraints.
4. Verify Alembic is at head and verify all three exclusions and the trigger directly in PostgreSQL.

This is a development-bootstrap procedure, not a general production migration pattern. A production database must begin with Alembic ownership, or receive an individually reviewed baseline reconciliation supported by a schema-diff report and backup/change-control process.

Focused verification completed on 2026-09-11:

- `python -m compileall security_master_schema` passed;
- all 24 schema metadata tests passed;
- 11 focused tenant operational-mapping, tenant capability, entitlement-resolver, fixture and offline-Alembic tests passed;
- offline `alembic upgrade head --sql` generation passed through revision `20260911_43`;
- the local Docker PostgreSQL reconciliation test passed, confirming revision `20260911_43`, all three database exclusion constraints, and the mapping target-validation trigger.

Detailed design: [capabilities and profiles design](../../superpowers/specs/2026-09-11-tenant-capabilities-and-operating-profiles-design.md).  
Execution record: [implementation plan](../../superpowers/plans/2026-09-11-tenant-capabilities-and-operating-profiles.md).
