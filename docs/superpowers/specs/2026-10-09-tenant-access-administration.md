# Tenant access administration — approved design

Approved in conversation on 9 October 2026. Implement sequentially in the current feature checkout; do not request a second approval for the already approved plan.

## Outcome and boundaries

Local alpha operators can manage tenant module entitlements from a tenant-independent platform workspace, manage users/groups within a tenant, and test the application as a selected tenant member. Preserve operating trades, strategies, market data and existing identities. Reuse the existing two tenants and add a third rather than replacing operating data.

Platform authority is separate from tenant membership. Platform administrators manage the tenant/module registry. Tenant administrators manage only their own users and groups. Group grants combine, but effective access requires active account, active tenant membership, enabled tenant modules and an allowed action. No platform privilege is inherited while acting as a tenant user. Market-data licences and reviewer separation remain independent constraints.

## Permission foundation

Define a fixed action catalogue mapped to existing modules. Tenant groups grant actions, not arbitrary executable policy. Tenant admins hold enabled-module actions and tenant access-management authority; regular members derive actions from active group membership. Group creation and assignment must enforce same-tenant foreign keys. Unknown permissions deny access. Legacy non-admin role labels do not silently grant permissions.

Distinguish tenant subscription modules from the user's effective modules and actions in workspace responses. Module changes and access-management changes produce audit events. Disabling a module takes effect for subsequent requests without removing data or permanently deleting group configuration.

## UI and local session

`/platform/tenants` lists tenants and enables/disables modules. `/tenant-profile/access` provides Users and Groups, including status and effective access. `/select-context` selects platform mode or a tenant plus active user; the tenant shell shows a testing-as banner and return action.

Use a development-only, server-validated local context session, HttpOnly cookies, expiration and same-origin checks for mutations. Record the real platform operator separately from the effective tenant user. Revalidate active authority and membership on every request. Browser-supplied user IDs never directly become authority without backend validation. Production must fail closed for this local switcher. Existing API trusted headers remain a private local boundary, not production authentication.

Switching context performs a full navigation, discarding mounted forms and browser request state. API/BFF identity must be sourced centrally, with no remaining hard-coded identity forwarding on active-session paths. Reviewer restrictions compare the real acting identity as well as effective subject where applicable.

## Seed and acceptance

Three tenants, each with tenant admin, trader, operations and read-only accounts and tenant-local groups. Different module combinations demonstrate restrictions. Canonical reference data is shared deliberately; tenant trades, strategies, custom reference records, access configuration and licensed data are not implicitly shared.

Focused tests cover union/intersection semantics, cross-tenant IDs and assignments, suspension/revocation, module disable/re-enable, direct API denial, expired/tampered contexts, failed switch preserving context, audited actor/subject, and production disabling. Browser acceptance verifies all three tenant workspaces and permission-specific controls. Do not run the full Python suite unless required by a discovered cross-cutting risk; report the verification scope honestly.

## Research

Reviewed 9 October 2026:

- [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): least privilege, deny by default, check every request and test authorization.
- [OWASP Multi Tenant Security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html): verified tenant context, scoped resources, tenant/user-aware cache isolation.
- [Microsoft control planes](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/control-planes): distinguish privileged platform administration from tenant workloads. This alpha uses logical separation in one deployment, not physically isolated services/databases.
- [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693.html): distinguish real actor from effective subject; no full token-exchange service is required for this local alpha.
