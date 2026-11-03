# Local identity safeguard implementation plan

> Execute sequentially in the authorised existing checkout. Preserve unrelated work; no commit/push or production identity provider is authorised by this task.

**Goal:** Contain security-review point 1 while retaining the local tenant/user testing workflow.

**Architecture:** Ordinary protected API requests require the existing expiring,
revocable opaque session. Identity comes from the verified session; optional
identity headers must agree with it. Session bootstrap uses a random server-only
local operator key and the configured operator account. Local/test/development
must be explicit; other environments cannot start the API. Production identity
and external access remain unsupported. Reuse existing authority and audit rules.

**Stack:** FastAPI/Starlette, SQLAlchemy, Next.js 16, existing local session store.

## Scope and decisions

- This implements the safeguard approved in the conversation, not production authentication.
- Protect bootstrap as well as ordinary requests: an admin UUID must never be sufficient to mint a session.
- Verify session subject, tenant, expiry, revocation and current membership; retain real-operator attribution and independent-review checks.
- Remove legacy signed-tenant/demo-user authentication. Keep the context selector, platform mode and tenant/user selection.
- Distinguish `APP_ENV` from Next's build mode: an optimised local build may use explicit `APP_ENV=local`.
- Build/schema tooling may import the app without secrets; server startup and protected requests fail closed when configuration is missing or non-local.
- Generate a private local bootstrap key without printing it; never place it in browser props, responses, public environment variables or foreign-origin requests.
- No database migration, permission grant, financial calculation change or operating booking/publication.

## Tasks

- [x] Add failing request/configuration regressions for forged headers, missing/invalid sessions, bootstrap protection and non-local startup.
- [x] Add local settings/identity helper, verified request context and guarded bootstrap; preserve transaction/thread/audit boundaries.
- [x] Add a safe local setup operator and update launcher/example configuration.
- [x] Add failing frontend regressions; remove demo fallbacks and guard server bootstrap/session access.
- [x] Verify expired/revoked sessions, context mismatch, platform isolation and real-operator attribution against an owned disposable database.
- [x] Update affected test authentication fixtures explicitly; keep security probes on real unmodified authentication.
- [x] Verify types/contracts, relevant frontend/backend tests and isolated browser selection. Run a bounded production build if needed.
- [x] Reconcile BACKEND-001 and capability/knowledge/delivery documentation, distinguishing containment from production authentication.
- [x] Review scoped changes, secrets/neutrality/links and temporary build edits.

## Research basis

Reviewed 30 October 2026:
[OWASP REST access control](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html#access-control),
[OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
and [Next.js authentication guidance](https://nextjs.org/docs/app/guides/authentication).
The server-only bootstrap capability is a local containment decision, not an OIDC
replacement. Existing local-session authority remains intentionally restricted
to local testing.
