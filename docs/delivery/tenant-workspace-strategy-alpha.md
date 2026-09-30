# Tenant workspace and strategy alpha

The alpha begins with an authenticated actor's active tenant membership; it is not a support or platform-admin impersonation flow.

- `GET /v1/session/memberships` is available before a tenant is selected.
- `GET /v1/tenant-workspace` resolves the selected tenant's effective membership, enabled module codes, and separately held platform role.
- The console stores the selected tenant in the HttpOnly `active_tenant` cookie. Its value is HMAC-signed with `ACTIVE_TENANT_COOKIE_SECRET`; production must configure that secret. Local development uses a development-only fallback secret.
- `POST /api/session/active-tenant` validates the candidate against upstream memberships before setting the cookie and marks a context change with `X-Tenant-Context-Changed: 1`.
- The `/tenant-profile` screen is the authoritative UI for the active tenant's identity, the user's membership role, and enabled modules. The switcher changes context; it does not manage tenant settings.
- The `/strategies` console uses that server-side tenant context. Strategy creation is shown only to tenant administrators with `TRADING` or `FUND_MANAGEMENT` entitlement.
- The root Instruments page now resolves the active server-side tenant context for both the initial catalogue request and browser search BFF request. It labels the current catalogue as `GLOBAL`; tenant-owned custom instruments are intentionally the next vertical slice and will be visibly separate rather than silently mixed with canonical records.

This remains an alpha boundary: the demo actor environment seam is still used, and existing legacy pages have not yet been migrated from their static demo tenant context. The next hardening pass must add end-to-end identity integration, mutation idempotency, audit events, and broader browser/API tests.
