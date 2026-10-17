# Access, tenancy and strategies — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Platform engineering  
**Last reviewed:** 2026-10-16 (shared write-context remediation; capability limits retained)

[Feature register](../feature-register.md). Baseline: main `76f6292`. ALPHA is bounded local delivery, not production certification.

## F01 Platform tenant administration

- **Desired:** Service-provider administration outside tenants: tenant details and module grants/suspension.
- **Status / backend / frontend:** ALPHA. Platform-only reads, audited optimistic profile updates and suspension/reactivation; `/platform/tenants` editor and confirmations.
- **Cuts/trade-offs:** UUID/code immutable; local seeded operators instead of enterprise provisioning.
- **Weaknesses:** Registry scaling and supplemental audit durability; no full onboarding/offboarding, contracts or billing.
- **Remaining:** Production control-plane identity, provisioning policy, durable audit/monitoring and latest visual acceptance.
- **Evidence:** [Delivery](../../delivery/tenant-access-administration.md), [backend](../../../security_master_schema/access_management.py), [page](../../../apps/ops-console/src/app/platform/tenants/page.tsx).

## F02 Users, groups and delegated actions

October 16 [backend hardening](../../delivery/quality-reviews/2026-10-16-backend-remediation.md)
uses one request-pinned UTC governance date for current membership/module/strategy/
dataset checks, offloaded budgeted authorization and atomic tenant command audit.
This also applies to F04 entitlements. It does not change role/action grants,
introduce production identity or close matrix scaling and independent access-review gaps.

- **Desired:** Tenant admins curate users and Operations/Trader-style groups with actions within enabled modules.
- **Status / backend / frontend:** ALPHA. Scoped memberships/action grants, suspension and last-admin protection; strategy scopes bound to group actions, versioned preview/confirmation, strategy access matrix and current-state explanations.
- **Cuts/trade-offs:** Controlled action catalogue, not arbitrary permission expressions; local accounts rather than identity-provider invitations. Tenant admins receive access management only; operations require group grants for everyone. Existing admins receive one-time explicit compatibility groups.
- **Weaknesses:** Admins can still self-assign operational groups (audited, not independently approved). Matrix/preview are unpaged alpha views; no federated synchronization, seats, enterprise lifecycle, hierarchy or individual exceptions.
- **Remaining:** Production invite/join/deactivate flow, identity linking and periodic access-review reporting. Do not reinstate implicit legacy non-admin privileges.
- **Evidence:** [Administration/UX](../../delivery/tenant-access-administration.md), [group model](../../../security_master_schema/access_tables.py), [API](../../../apps/reference_api/access_routes.py).

F02 authority separation: [behavior, migration and limits](../../delivery/admin-operational-authority-separation.md),
[focused tests](../../../tests/test_admin_authority_separation.py).

F02/F05 strategy scopes: [delivery, migration and limits](../../delivery/strategy-access-scopes.md),
[evaluator](../../../security_master_schema/strategy_access.py),
[HTTP tests](../../../tests/test_strategy_scopes_api.py).

F02/F05 UI refinement: [workflow, research and acceptance](../../delivery/access-management-ux.md).
The group register exposes strategy scope; the editor separates configuration from
review; the matrix filters users and expands source-group evidence. Client filters
do not resolve the unpaged backend-matrix limitation.

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
- **Weaknesses:** Delivery labels are a maintained map, not runtime workflow discovery; no billing/quotas or historical access inspection.
- **Remaining:** Keep effective-access delivery labels aligned with F41–F45; commercial entitlement administration when scoped.
- **Evidence:** [Capabilities model](../../architecture/tenancy-and-entitlements/tenant-capabilities-and-operating-profiles.md), [resolver](../../../security_master_schema/tenant_workspace.py), [navigation](../../../apps/ops-console/src/lib/navigation.ts).

F02/F04 addition: [effective-access delivery and limitations](../../delivery/effective-access-transparency.md),
[service](../../../security_master_schema/access_explanations.py),
[page](../../../apps/ops-console/src/app/tenant-profile/effective-access/page.tsx),
[HTTP isolation tests](../../../tests/test_effective_access_api.py).

## F05 Strategies

2026-10-16 safety follow-up: strategy creation binds the form's server-prepared
tenant and user to its BFF write. Missing or changed context is rejected before
forwarding, and the client retains the draft with reload guidance. The subsequent
shared document-fingerprint transport and Next Proxy extend stale-context protection
across same-origin BFF mutations, retaining endpoint-specific authority. See
[October 16 resolution and browser evidence](../../delivery/quality-reviews/2026-10-16-frontend-remediation.md).

2026-10-15 follow-up: [contract-date and attention indicators](../../delivery/strategy-workspace-20261015.md#contract-dates-and-attention)
show saved maturity/expiry (futures: last trading), evaluated at the selected
as-of date. Missing/conflicting date evidence is explicit; no last-trade date,
automatic closure, cash posting or Ops notification queue is introduced.

- **Desired:** Tenant-owned Fund, AMC, prop sleeve, mandate, managed-account and other classified strategies.
- **Status / backend / frontend:** ALPHA. Scoped create/read/archive, separate creation permission and atomic initial selected-group access. `/strategies` register, `/strategies/new` creation, and strategy detail with dated executed/recognised holdings grouped alphabetically by booked instrument type, compact UUID-free table, full movement drill-down and quantity-history chart, scoped trade-history link and calendar visibility.
- **Cuts/trade-offs:** A classification is not a legal vehicle or complete fund/AMC workflow; archiving differs from deleting history. Holdings are signed units, not tax lots, prices, value or P&L. Exact listings/contracts remain separate; incomplete evidence blocks rather than displays a partial book.
- **Weaknesses:** Vehicle/share-class lifecycle and hierarchy remain incomplete. The strategy register preloads its scoped list; holdings read in keyset batches then aggregate/recompute in memory. Large-book scale and visual browser acceptance remain unproven; base currency does not imply valuation readiness.
- **Remaining:** Separate vehicle/mapping/hierarchy workflows, large-book optimization, optional per-position diagnostics and cross-listing aggregation. Preserve ownership checks and booked history during cleanup.
- **Evidence:** [Strategy workspace and verification](../../delivery/strategy-workspace-20261015.md), [original strategy delivery](../../delivery/tenant-workspace-strategy-alpha.md), [cleanup boundaries](../../delivery/strategy-register-cleanup-20261009.md), [console](../../../apps/ops-console/src/app/strategies/strategy-console.tsx).

## F06 Production identity and isolation

- **Desired:** Production-authenticated tenant isolation, beyond local switching.
- **Status / backend / frontend:** FOUNDATION. Tenant/resource/action checks and routing foundations exist; server BFF propagates validated local context. No complete production identity integration.
- **Cuts/trade-offs:** Implemented alpha uses shared local PostgreSQL with logical scopes; separate tenant databases are design/routing groundwork, not a deployed fleet.
- **Weaknesses:** Local headers/sessions do not prove Auth0/OIDC claims verification, deployed isolation, service-principal governance or secret rotation.
- **Remaining:** Production identity/deployment design, threat-modelled trust boundaries, provisioning and independent security acceptance. Do not expose research impersonation as production login.
- **Evidence:** [API hardening](../../delivery/api-boundary-hardening.md), [routing direction](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md), [auth boundary](../../../packages/auth/README.md), [request checks](../../../apps/reference_api/access_boundary.py).
