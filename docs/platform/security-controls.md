# Database, audit and browser safeguards

**Status:** Implemented local controls; production authentication deferred  
**Owner:** Platform engineering  
**Last reviewed:** 2026-10-30

These controls address security-review findings 3, 4, 6 and 8, preserving financial
calculations, strategy permissions, complete trade populations and retained
evidence. See [local identity](local-identity-safeguard.md), [delivery evidence](../delivery/security-controls-20261030.md)
and [open findings](../../FIX.md).

## Database setup and maintenance

[Compose](../../docker-compose.yml) publishes PostgreSQL on **127.0.0.1:54329**.
Its password comes from an ignored secret file, with no fixed fallback. Application
settings require an explicit URL and exclude it from dataclass representations.
Normal API startup checks effective privileges and refuses owners, owner-role
members, schema creators and administrative logins. Explicit injected engines
remain a test factory dependency; no environment/header bypass was introduced.

For a fresh installation, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/configure_local_database.py --prepare
docker compose up -d postgres
.\.venv\Scripts\python.exe scripts/migrate_database.py
.\.venv\Scripts\python.exe scripts/configure_local_database.py --apply
.\.venv\Scripts\python.exe scripts/configure_local_access.py
pnpm dev:reference-api
pnpm --filter ops-console dev
```

Preparation generates random private administrator/runtime passwords and a
maintenance URL. Applying creates/updates `platform_runtime`, grants business DML
and explicitly rotates the owner password. For an existing installation first
preserve its actual database/user/container/Compose-project/volume names in
ignored `.env`; supply its **current** connection as `MIGRATION_DATABASE_URL`
while applying. Never replace its volume merely to match a new default name.
Changing a Docker password environment variable does not rotate an existing role.
Generated URLs use 127.0.0.1 directly to match the IPv4 binding and avoid OS IPv6
retries. No database purge/reseed is part of this workflow.

| Private file | Purpose |
| --- | --- |
| `.env` | Existing installation and Compose project/volume names |
| `.local-secrets/postgres-admin-password` | Docker bootstrap/maintenance secret |
| `.local-secrets/postgres-runtime-password` | Generated application secret |
| `.env.migrations` | Separate `MIGRATION_DATABASE_URL` for schema maintenance |
| `.env.local-access` | API runtime URL and local operator configuration |
| `apps/ops-console/.env.local` | Private frontend upstream/operator settings; no database credential needed |

All are Git-ignored. Protect user-folder/backup ACLs: files use owner-only POSIX
mode and inherit the user's folder ACL on Windows. Never print their contents.

`scripts/migrate_database.py` uses the maintenance URL and refreshes application
grants after upgrades, including new schemas. Read-only revision commands do not
change grants. `TEST_DATABASE_ADMIN_URL` is used only by explicit disposable-test
operators, never as the migration target. Direct Alembic callers must deliberately
supply `DATABASE_URL`. Schema/demo/ingestor operators have no weak credential
fallback; the ingestor still has no API identity dependency.

The runtime has schema USAGE, business SELECT/INSERT/UPDATE/DELETE and sequence
access, but no ownership/permanent-schema CREATE, role administration or table TRUNCATE. Audit is
read/append only; migration metadata is maintenance-only. Database owners/host
administrators remain trusted. Tenant enforcement remains in the application;
this does not claim row-level tenant isolation after a shared connection compromise.

## Secret scanning

[Gitleaks configuration](../../.gitleaks.toml) inherits the maintainer's full
default rules. The pinned CI action uses engine 8.30.1; no global finding
allowlist was added. [Local source scanning](../../scripts/scan_working_tree_secrets.py)
requires a synthetic token sentinel to be detected, then scans tracked and
unignored new files through a temporary snapshot. Ignored private settings,
caches, dependencies and reports are excluded; findings are redacted. This is
separate from CI's Git-history scan, and cannot detect every possible secret.

## Audit and denials

[Migration 105](../../alembic/versions/20261030_105_access_audit_immutability.py)
adds UPDATE/DELETE and TRUNCATE rejection triggers to `ten.access_audit_event`,
preserving existing rows. Runtime privilege denial is a second layer; the app
cannot disable triggers. Successful-command audit stays atomic with its effect.

Every API 401/403 emits a structured WARNING on `apps.reference_api.security`,
outside the financial transaction. It includes request ID, UTC timestamp, method,
route **template**, safe reason code, status and verified real operator/selected
subject/tenant when known. Forged headers cannot establish those identities.
Tokens, cookies, headers, bodies, query strings, concrete private URL parameters
and exception messages are excluded. Anonymous failures do not invent a database
user/audit row. External log collection/retention/alerting remains to be deployed;
a trusted DBA can change local storage. This is not external WORM certification.

## Browser and cookies

[Next Proxy](../../apps/ops-console/src/proxy.ts) forwards a fresh CSP nonce to
Next rendering and returns the matching policy. Scripts require the nonce;
`unsafe-eval` is development-only. Inline styles remain allowed for existing
native charts/layout attributes and MUI; script `unsafe-inline` is not enabled.
Object embedding is disabled, framing/forms/base URLs are constrained, MIME
sniffing is disabled, referrers limited and unused device permissions disabled.
Existing stale-context guards remain active, including rejected responses. The
API also adds nosniff, no-referrer and frame-denial headers.

Session creation **and clearing** use HttpOnly, SameSite=Strict, path `/` and
Secure on HTTPS. HTTPS non-loopback responses add HSTS. Local HTTP and optimised
local builds remain usable. Trusted reverse-proxy/TLS configuration, production
authentication and deployment certification remain future work. Static Next
assets are excluded from nonce middleware; HTML CSP controls script loading.

## Related findings and subsequent follow-up

**5 — Data-use profiles:** Subsequently resolved by [strict governance](dataset-rights-and-workload.md).
All datasets need profiles, activity evidence and explicit display purpose.
Migration 106 and exact synthetic-origin backfill preserve genuine source rights.
Commercial agreements and a complete rights-administration UI remain separate.

**7 — Aggregate workload:** [Shared admission](dataset-rights-and-workload.md)
now bounds concurrent expensive requests across workers and tenants, preserving
ordinary reads and complete financial populations. Body/SQL budgets remain.
Per-job OS memory/CPU isolation, durable queues and capacity acceptance are still
deployment work. Do not restore the old trade-count cap. This
direction follows [OWASP deny-by-default authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html#deny-by-default)
and [API resource-consumption guidance](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/);
the particular profile migration/job design still requires its own implementation.

## Primary guidance reviewed

Reviewed 30 October 2026: [Docker ports](https://docs.docker.com/engine/network/port-publishing/),
[Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
[Postgres image/existing volumes](https://hub.docker.com/_/postgres),
[PostgreSQL 18 privileges](https://www.postgresql.org/docs/18/ddl-priv.html),
[Gitleaks inheritance](https://github.com/gitleaks/gitleaks#configuration),
[OWASP logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
and [Next.js CSP](https://nextjs.org/docs/app/guides/content-security-policy).
The local configuration layout is a project choice applying those recommendations.
