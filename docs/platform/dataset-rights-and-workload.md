# Dataset rights and expensive-work admission

**Status:** Active local enforcement; deployment workload isolation remains partial  
**Owner:** Platform engineering / market-data governance  
**Last reviewed:** 2026-10-30

This follows [security controls 3/4/6/8](security-controls.md). It addresses the
missing-profile gap (5) and implements shared admission for expensive work (7).
[Delivery evidence](../delivery/dataset-rights-and-workload-20261030.md) separates
focused tests, operating activation and remaining deployment work.

## Explicit data-use governance

Every dataset needs an active, technically enabled access profile, matching
activity evidence and the appropriate tenant purpose/series coverage. Missing
profiles and unknown requested dataset IDs deny access. There is no older-data
fallback. Display always requires `INTERNAL_REPORTING`; valuation eligibility
remains separate and requires `VALUATION` plus `NON_DISPLAY` activity evidence.
All required distributor/content-owner layers still have to be satisfied.

| Profile scope | Permitted evidence |
| --- | --- |
| PERSONAL | Existing attributable personal evidence/contracts; existing narrow acquisition exception unchanged |
| COMMERCIAL | Contracts, as before; synthetic/personal evidence never qualifies |
| SYNTHETIC | Explicit invented-data origin, matching synthetic grants and activity requirements; never a real-provider permission |

Synthetic scope is an explicit classification, not an exception for missing
profiles, missing prices or convenient provider names. The seed provisioner
accepts only five exact loader-owned identities and matching source codes.
Existing profiles, grants, requirements and revocations are preserved. Ordinary
tenant/series/package and private-parent restrictions still apply. External
ingestion is not enabled for invented fixtures merely by granting display/use.

The five seeded mock datasets now retain source-origin evidence and explicit
STORE/DISPLAY/NON_DISPLAY requirements/grants. Their existing fixture tenants'
reporting entitlements retain dates, states and scoped package membership. This
preserves their earlier display workflow without treating real vendor contracts
as implied. Yahoo and imported source profiles are untouched.

For the existing local installation:

```powershell
.\.venv\Scripts\python.exe scripts/migrate_database.py
.\.venv\Scripts\python.exe scripts/provision_seed_dataset_profiles.py --apply
```

Migration 106 extends the scope/evidence checks and column documentation. The
separate provisioner requires an explicitly configured local platform operator,
uses private maintenance configuration, serializes its operation and appends an
access-audit event. It neither imports source data nor grants users/groups access.
Fresh demo loading provisions the same explicit seed profiles. It is not part of
API startup, and it never backfills arbitrary real datasets from inferred rights.

Current display authority applies to historical evidence too. Revocation can
leave operational run status available while hiding raw inputs, components and
financial totals. Frozen calculations and published figures are not rewritten.

## Shared expensive-operation admission

The existing synchronous workflows remain. A full lane returns HTTP **429**,
`workload.busy`, `Retry-After` and `notStarted: true`, before routing/dependencies
start the domain operation. If coordination is unavailable, the same safe
rejection uses HTTP 503. No hidden queue or automatic retry is created.

`notStarted` describes **this HTTP submission**. An earlier request using the
same key may already be running or complete. Retain the exact body/key, inspect
history when needed and retry unchanged. Timeouts retain their existing uncertain
outcome semantics. The BFF forwards retry guidance; the valuation UI distinguishes
capacity rejection from an uncertain timeout and does not retry automatically.

Defaults, configurable through the API's environment:

| Setting | Default | Meaning |
| --- | --- | --- |
| `REFERENCE_API_WORKLOAD_GLOBAL_LIMIT` | 2 | Expensive operations across workers connected to the same database |
| `REFERENCE_API_WORKLOAD_PROCESS_LIMIT` | 2 | Nonblocking local admission slots per application/worker |
| `REFERENCE_API_WORKLOAD_TENANT_LIMIT` | 1 | Concurrent expensive operations for one verified tenant |
| `REFERENCE_API_WORKLOAD_RETRY_AFTER` | 5 | Suggested seconds before a manual unchanged retry |

All values must be positive. Configure all workers consistently; drain running
work before changing slot counts. These settings govern concurrency, never how
many instruments, trades, dates, sources or eligible observations a calculation
may process. SQL/body budgets and existing authority checks remain in force.

Covered operation families are defined in
[`workload_kind`](../../apps/reference_api/workload_admission.py): valuation and
reassessment calculation, monetary-measure previews, trade file/template/review/
confirmation work and regulatory preparation/preview/export/download. Route
classification covers compact, URN and braced UUID forms accepted by routing;
the router still owns input validation. Ordinary booking, selectors, lists and
run/log/status reads do not use the expensive lane, and still require permission.

Admission runs after verified identity/current action checks and before domain
connections are acquired. A nonblocking local semaphore avoids worker queuing.
Deterministic PostgreSQL session-advisory slots enforce global/tenant capacity
across independent workers. A separate small coordination pool avoids borrowing
the business pool's only connection; current one-connection preview snapshots
and fresh release checks remain valid. Coordination SQL/connect/pool waits have
short budgets. Rollback does not release session advisory locks: cleanup explicitly
unlocks each owned key or invalidates the session. Worker/session loss releases
locks in PostgreSQL; app shutdown disposes idle coordination connections.

Slots cover the full ASGI response lifetime, including body sends. A tested
synchronous calculation keeps its slot when its client is cancelled; cancellation
is not proof that physical work stopped. Async cancellation/error cleanup is
shielded. Future detached/background work must have its own admission ownership;
returning a response and continuing arbitrary work would violate this contract.

`apps.reference_api.workload` emits safe structured rejection warnings and
admitted/released INFO events, including request/tenant/kind and elapsed time,
without request bodies, tokens or prices. Enable INFO collection to measure
admitted/released traffic. Coordination connections identify themselves as
`platform_workload_admission` in PostgreSQL activity views.

## Remaining deployment work

Admission protects responsiveness under concurrent work; it does not make one
SQL query faster. It does not bound a single job's Python RSS/CPU, implement
per-operator rate accounting, provide fair durable queuing, interrupt synchronous
financial work or provide asynchronous job cancellation. Representative load
profiling, worker/container resource isolation and a separately designed durable
queue/status/recovery lifecycle remain open in SEC-WORK-001. No arbitrary
financial population cap, data truncation or production capacity certification
is substituted for that work. Production authentication remains deferred.

## Guidance reviewed

[OWASP deny by default](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html#deny-by-default),
[OWASP API resource consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/),
[PostgreSQL 18 advisory locks](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS),
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) and
[SQLAlchemy engine disposal](https://docs.sqlalchemy.org/en/21/core/connections.html#engine-disposal)
were reviewed on 30 October 2026. Synthetic scope and local slot defaults are
project choices applying these principles, not universal licensing/capacity rules.
