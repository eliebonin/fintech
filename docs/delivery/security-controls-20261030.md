# Security controls 3, 4, 6 and 8 — 30 October 2026

**Status:** Implemented; bounded verification below  
**Scope:** Existing local installation and publishable source  
**Plan:** [Sequential implementation](../superpowers/plans/2026-10-30-security-controls.md)

| Finding | Result |
| --- | --- |
| 3 Database | Loopback port, random private credentials, explicit owner-password rotation, non-owner runtime login/startup check; weak executable defaults removed |
| 4 Secrets | Inherited Gitleaks defaults, pinned engine, synthetic detection sentinel and redacted source scan |
| 6 Audit | Migration 105 rejects audit UPDATE/DELETE/TRUNCATE; runtime read/append only; correlated safe 401/403 logs independent of business rollback |
| 8 Browser | Per-response nonce CSP, baseline headers and HTTPS Secure session creation/clearing, preserving local HTTP and context guards |

[Setup and limits](../platform/security-controls.md). Findings 5 and 7 were
reviewed/explained, not changed. Production authentication remains deferred and
non-local API startup blocked.

## Local activation

The installed database had historical names and a different Compose project from
repository defaults. These were preserved in ignored configuration; the exact
existing volume was reused. A preservation guard stopped the first attempt before
mutation; retaining Compose project metadata resolved a container-name conflict.
No database purge/reseed occurred. PostgreSQL is healthy and bound only to
127.0.0.1:54329, revision is `20261030_105`, and operating counts remain **162
trades / 3 tenants**. The app connects as `platform_runtime`. No operating trades,
balances, permissions or valuations were created/changed/published. Generated URLs
use IPv4 directly after detecting Windows retries with localhost resolution.

## Verification

- RED checks reproduced scanner/configuration, denial logging, audit mutation and
  browser-header gaps before the corresponding corrections.
- Initial isolated audit/session/atomic-request checks: 23 passed.
- Restricted-role DML/schema/audit/migration-metadata checks passed on a disposable
  DB. Final combined regressions: **29 passed**, including actual synthetic trade
  booking/readback and retained command audit under the restricted role, immutable
  audit, verified-actor denials, rollback and explicit migration-target separation.
- Full frontend: **1,085 tests / 223 files passed**. Targeted header/cookie/identity
  selection: 12 passed. Types, deterministic OpenAPI and isolated optimized build
  passed; every app route remains dynamically rendered for per-request nonces.
- Real Next/installed Chrome acceptance passed: nonce-bearing rendered scripts,
  hydration and stale-context rejection, with no operating context/data.
- Optimized-build Chrome acceptance also passed: strict production script policy,
  matching SSR nonces, local HTTP, no CSP violations or uncaught page errors. The
  temporary server on port 3120 was stopped afterward.
- Read-only operating API lifespan check passed with the runtime login; protected
  unauthenticated request returned 401 and safe structured evidence. Administrative
  connection startup was rejected as intended.
- Official Gitleaks 8.30.1 binary matched its published SHA256 manifest. Synthetic
  token detection passed, then publishable source (~17 MB, including new files)
  scanned with no findings. Ignored credentials/reports/dependencies were excluded.
  Local Git-history scanning was not completed; existing CI retains history scans
  and runs remotely only after push.
- Final naming, ingestion boundary, private setup and configuration/log checks:
  13 passed. The full Python suite was deliberately not run for this scoped fix.
- Private configuration is ignored/untracked. The actual generated database
  credentials and operator capability were absent from all 84 public optimized
  JavaScript assets. Maintained-document local links and scoped whitespace checks
  passed; temporary Next build type-path changes were removed.

No full Python run, independent penetration test, workload-capacity certification,
production TLS/authentication or external immutable retention is claimed. No
commit/push was requested. [Remaining rights/work issues](../../FIX.md).
