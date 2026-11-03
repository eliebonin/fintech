# Security controls 3, 4, 6 and 8 implementation plan

> Execute sequentially in the authorised checkout. Preserve unrelated edits. Do not commit/push. Production authentication remains deferred.

**Goal:** Harden database deployment/credentials/runtime privileges, activate real
secret scanning, protect access audit and log denials, and add browser/HTTPS
cookie safeguards. Explain findings 5 and 7 without changing their behaviour.

**Architecture:** Keep existing business services and local identity. Use an
explicit non-owner runtime database login and separate private migration/admin
configuration; preserve the current database volume. Install append-only audit
triggers through migration 105. Denials use a separate safe structured log channel
that survives transaction failure. Next Proxy supplies script nonces and security
headers while retaining context-write guards; HTTPS gets Secure cookies.

**Decisions:** Inline styles remain allowed because native charts and MUI use
them; executable scripts require nonces, with eval limited to development.
Loopback HTTP remains usable for local performance testing. HSTS must not pin
localhost to HTTPS. No provider/type/date restrictions or financial caps are added.
Database owners remain trusted maintenance principals; independent external audit
retention and production authentication are not claimed by these local controls.

## Tasks

- [x] Reproduce scanner/configuration, audit mutation, missing denial logs and browser-header/cookie failures.
- [x] Enable Gitleaks defaults; verify a synthetic sentinel is detected and scan current product files with redacted output.
- [x] Add append-only audit migration and safe correlated 401/403 security logs; verify rollback/secret redaction.
- [x] Add CSP/security headers and HTTPS cookie options; verify real Next pages, styles, navigation, writes and HTTP local mode.
- [x] Separate runtime/admin credentials, remove weak executable defaults, bind PostgreSQL to loopback and preserve volumes.
- [x] Verify runtime business DML and booking while refusing ownership/DDL/audit mutation; activate local configuration/migration safely.
- [x] Run focused regression/types/build/scan checks; reconcile documentation, feature records and known limitations.
- [x] Explain the unprofiled-dataset rights gap (5) and workload/admission-control gap (7) from current code.

## Primary guidance reviewed 30 October 2026

- [Docker published ports](https://docs.docker.com/engine/network/port-publishing/)
- [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- [PostgreSQL 18 privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [Postgres image secrets and existing volumes](https://hub.docker.com/_/postgres)
- [Gitleaks inherited default rules](https://github.com/gitleaks/gitleaks#configuration)
- [OWASP logging, denials and secret exclusions](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [Next.js nonce CSP](https://nextjs.org/docs/app/guides/content-security-policy)
