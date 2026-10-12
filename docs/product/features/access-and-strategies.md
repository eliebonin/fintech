# Access, tenancy and strategies — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Platform engineering  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). Baseline: main `76f6292`. ALPHA is bounded local delivery, not production certification.

## F01 Platform tenant administration

- **Desired:** Service-provider administration outside tenants: tenant details and module grants/suspension.
- **Status / backend / frontend:** ALPHA. Platform-only reads, audited optimistic profile updates and suspension/reactivation; `/platform/tenants` editor and confirmations.
- **Cuts/trade-offs:** UUID/code immutable; local seeded operators instead of enterprise provisioning.
- **Weaknesses:** Registry scaling and supplemental audit durability; no full onboarding/offboarding, contracts or billing.
- **Remaining:** Production control-plane identity, provisioning policy, durable audit/monitoring and latest visual acceptance.
- **Evidence:** [Delivery](../../delivery/tenant-access-administration.md), [backend](../../../security_master_schema/access_management.py), [page](../../../apps/ops-console/src/app/platform/tenants/page.tsx).

## F02 Users, groups and delegated actions

- **Desired:** Tenant admins curate users and Operations/Trader-style groups with actions within enabled modules.
- **Status / backend / frontend:** ALPHA. Scoped memberships/action grants, suspension and last-admin protection; Users/Groups UI with explicit saves and preserved drafts.
- **Cuts/trade-offs:** Controlled action catalogue, not arbitrary permission expressions; local accounts rather than identity-provider invitations.
- **Weaknesses:** No federated group synchronization, seats or enterprise account lifecycle.
- **Remaining:** Production invite/join/deactivate flow, identity linking and periodic access-review reporting. Do not reinstate implicit legacy non-admin privileges.
- **Evidence:** [Administration/UX](../../delivery/tenant-access-administration.md), [group model](../../../security_master_schema/access_tables.py), [API](../../../apps/reference_api/access_routes.py).

## F03 Context switching

- **Desired:** Select platform admin or a tenant/user to test isolation.
- **Status / backend / frontend:** ALPHA. Opaque expiring/revocable local sessions retain real actor and selected subject; `/select-context`, indicators and reset/recovery.
- **Cuts/trade-offs:** Research-only impersonation, not production authentication; failed switches preserve context.
- **Weaknesses:** Legacy operator history can be incomplete; switching identities must never satisfy independent review.
- **Remaining:** Production support-access policy. Keep transactional real-operator checks through amendment ancestry; incomplete legacy impersonated review needs recalculation.
- **Evidence:** [Access delivery](../../delivery/tenant-access-administration.md), [sessions](../../../security_master_schema/access_sessions.py), [review authority](../../../valuation/review_authority.py).

## F04 Module entitlements and profile

- **Desired:** Tenant identity/active modules belong in the profile; platform grants govern availability.
- **Status / backend / frontend:** ALPHA. Effective-dated module grants intersect group actions; profile and permission-aware navigation.
- **Cuts/trade-offs:** Business profiles are recommendations, not grants. Module access, individual actions and dataset licensing are separate.
- **Weaknesses:** Enabled module names include future products and can be mistaken for delivery; no billing/quotas.
- **Remaining:** Availability labels aligned with F41–F45; commercial entitlement administration when scoped.
- **Evidence:** [Capabilities model](../../architecture/tenancy-and-entitlements/tenant-capabilities-and-operating-profiles.md), [resolver](../../../security_master_schema/tenant_workspace.py), [navigation](../../../apps/ops-console/src/lib/navigation.ts).

## F05 Strategies

- **Desired:** Tenant-owned Fund, AMC, prop sleeve, mandate, managed-account and other classified strategies.
- **Status / backend / frontend:** ALPHA. Scoped create/read/archive, base currency, code conflicts and authority; `/strategies` register/form.
- **Cuts/trade-offs:** A classification is not a legal vehicle or complete fund/AMC workflow; archiving differs from deleting history.
- **Weaknesses:** Vehicle/share-class lifecycle and mandate hierarchy are incomplete; base currency does not make every instrument valuation-ready.
- **Remaining:** Separately scoped vehicle/mapping workflows and hierarchy. Preserve ownership checks and booked history during cleanup.
- **Evidence:** [Strategy delivery](../../delivery/tenant-workspace-strategy-alpha.md), [cleanup boundaries](../../delivery/strategy-register-cleanup-20261009.md), [console](../../../apps/ops-console/src/app/strategies/strategy-console.tsx).

## F06 Production identity and isolation

- **Desired:** Production-authenticated tenant isolation, beyond local switching.
- **Status / backend / frontend:** FOUNDATION. Tenant/resource/action checks and routing foundations exist; server BFF propagates validated local context. No complete production identity integration.
- **Cuts/trade-offs:** Implemented alpha uses shared local PostgreSQL with logical scopes; separate tenant databases are design/routing groundwork, not a deployed fleet.
- **Weaknesses:** Local headers/sessions do not prove Auth0/OIDC claims verification, deployed isolation, service-principal governance or secret rotation.
- **Remaining:** Production identity/deployment design, threat-modelled trust boundaries, provisioning and independent security acceptance. Do not expose research impersonation as production login.
- **Evidence:** [API hardening](../../delivery/api-boundary-hardening.md), [routing direction](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md), [auth boundary](../../../packages/auth/README.md), [request checks](../../../apps/reference_api/access_boundary.py).
