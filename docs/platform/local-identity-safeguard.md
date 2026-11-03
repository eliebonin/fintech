# Local identity safeguard

**Status:** Local containment; production authentication deferred  
**Owner:** Platform engineering  
**Last reviewed:** 2026-10-30

Protected API requests require an expiring opaque local session. Identity comes
from that stored session; optional actor/tenant headers must agree. Current
operator, membership, module, action and strategy checks still apply. Real
operator and selected user remain separate for audit and independent review.

## Configure locally

From the repository root:

First complete [private database/runtime setup](security-controls.md#database-setup-and-maintenance).
API startup also refuses an owner/administrative database login. Maintenance uses
a separate private connection; the local selector does not bypass that boundary.

```powershell
.\.venv\Scripts\python.exe scripts/configure_local_access.py
pnpm dev:reference-api
pnpm --filter ops-console dev
```

Setup writes matching private `LOCAL_ACCESS_OPERATOR_KEY`, configured
`LOCAL_PLATFORM_OPERATOR_ID` and explicit `APP_ENV=local` to ignored
`.env.local-access` and `apps/ops-console/.env.local`. It preserves other settings,
reuses an existing matching key, refuses conflicting keys/operators and never
prints the key. Existing database/upstream URL settings remain installation
specific. API launchers load `.env.local-access`; direct uvicorn callers must use
`--env-file .env.local-access` or export its values. Restart both services after
configuration changes.

On initial activation, stop the old unguarded API and revoke any still-active
sessions it issued before using the safeguard. Rotating a bootstrap key alone
does not revoke existing opaque sessions. The implementation's local activation
check found zero active pre-existing sessions; no revocation was needed.

API startup refuses omitted, unknown or non-local modes and missing/short keys.
Allowed modes are exactly `local`, `test` and `development`. Protected requests
also check configuration when an ASGI caller skips startup. Schema/import tooling
does not start the server and needs no secret. The BFF refuses local identity
outside those modes. `NODE_ENV=production` is a JavaScript build setting: explicit
`APP_ENV=local` still supports an optimised build for local performance testing.

## Workflow and guarantees

- `/select-context` remains the entry point for platform or tenant/user selection.
  The BFF supplies a server-only operator capability on the guarded session
  bootstrap routes. The configured operator must be an active platform admin.
- A UUID alone cannot create a session. The API checks the selected membership,
  stores a random hashed four-hour token, and retains operator/subject identity.
  The browser receives an opaque HttpOnly same-site cookie, never the operator key.
- Ordinary requests require `X-Local-Access-Token`; the bootstrap key cannot
  substitute for a session. Invalid/revoked/expired/currently invalid sessions and
  mismatching identity headers fail. No demo-user fallback is attempted.
- Bootstrap forwarding is restricted to the configured API origin/session paths
  and refuses redirects. Expired contexts can be reset/replaced; failed switches
  retain the old context. Ending another real operator's session stays forbidden.
- Legacy signed `active_tenant` cookies no longer authenticate. The old tenant-only
  POST returns 410 with `/select-context` guidance. Existing users may need to
  select a context again; old cookies are not silently upgraded to valid sessions.

## Limits and deferred work

This is **local testing, not individual end-user authentication**. Users of the
local selector act through its configured operator. Keep local mode and its
selector away from untrusted users. Production/staging startup is intentionally
blocked until verified provider authentication and account/session mapping exist.
Relabelling a deployment `local` is not a remedy. SSO, MFA, invitations, service
identity and production support-access policy remain deferred. No migration,
permission grant or financial calculation change is included.

Product HTTP test clients explicitly obtain real sessions through guarded
bootstrap. They do not disable verification or replace supplied tokens. Dedicated
identity probes use original clients. Narrow fake-SQL tests mock session results
to isolate transaction/thread behaviour; router-only DTO tests explicitly inject
fixture context and make no authentication claim. These are different scopes.

Reviewed 30 October 2026: [OWASP REST access control](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html#access-control),
[OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
and [Next.js authentication guidance](https://nextjs.org/docs/app/guides/authentication).
The local capability is this project's containment choice, not an OIDC replacement.
See [delivery evidence](../delivery/local-identity-safeguard-20261030.md) and
[plan](../superpowers/plans/2026-10-30-local-identity-safeguard.md).
