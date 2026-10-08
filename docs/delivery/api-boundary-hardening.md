# API boundary hardening

**Status:** Implemented and automated verification complete; browser sign-off remains paused. **Started/completed:** 2026-10-06.

Implements the approved recommendations from [API review](quality-reviews/2026-10-06-api-endpoint-review.md), sequentially in the current feature checkout. Existing changes are preserved; no commits, push, operating-data mutations or restart are included. Browser sign-off stays paused. Real identity integration and production gateway/rate-limiting remain separate deployment work, not silently substituted with demo authentication.

## Approved scope and progress

1. [x] Transaction finalization before HTTP success: all connection dependency consumers use function scope. Two new regressions first failed (false 201 and uncommitted response headers); the boundary/health run then passed 5 tests. Service-validation refusal/rollback was already supported and remains covered. The final full PostgreSQL-backed regression passed.
2. [x] Consistent instrument authority and active-tenant refusal. User approved TENANT_ADMIN + SECURITY_MASTER for instrument proposals/approval; booking/configuration remain TENANT_ADMIN + TRADING. Read authority stays active tenant membership unless a capability already requires more. No new steward role or mandatory maker/checker split is invented. The expanded authority/workspace/swap run passed 82 tests. Instrument-management page guards mirror SECURITY_MASTER; configuration now rejects inactive actors too.
3. [x] Stable error correlation and safe protocol headers; malformed strategy requests become 4xx. One request ID is retained in body/header/logs, including unexpected failures. Allow, WWW-Authenticate and Retry-After are preserved; unrelated diagnostic headers are not. Strategy type/status, unknown fields, nonblank labels and approval reasons are validated. Duplicate tenant strategy codes now return an explicit 409, serialized by code to avoid a check/insert race.
4. [x] Proposal retry comparisons and bounded contracts/resources implemented and regression-tested. No new replay table or migration is needed: typed canonical requests are compared against retained proposal payloads. See operating semantics below.
5. [x] Expanded regression, final sequential author review, generated contract synchronization and delivery report.

The review's high-level sequence is the implementation authority. Changes are bounded repairs to existing flows, not a repository rewrite. Lightweight RED/GREEN tests preceded each behavior change; final verification included the full Python suite and frontend/contract checks. Results, deviations and remaining deployment limitations are recorded here.

## Authority and transaction boundaries

| Capability | Current authority |
| --- | --- |
| Instrument, listing, family, convention and mapping proposals/approval | Active account, active tenant/effective membership, TENANT_ADMIN + SECURITY_MASTER |
| Trade booking and trade-field configuration | Active account, active tenant/effective membership, TENANT_ADMIN + TRADING |
| Strategy management | Existing STRATEGY_WRITE policy, with active account/tenant checks |
| General tenant-scoped reads | Active account and active tenant/effective membership; existing stronger capability-specific rules remain |

Authorization precedes object lookup and replay. Unqualified callers receive 403 even when the supplied proposal UUID is unknown. Qualified callers still receive tenant-scoped 404s for inaccessible records. Every shared yielded connection is function-scoped: the outer transaction must commit before success headers are sent. Nested domain savepoints remain intact. Authorization effective dates use UTC; this is a governance clock, not an exchange-session/calendar redesign.

## Proposal retry semantics

- Existing source-backed equity/listing, bond, FX-forward, ETP, cryptoasset, index/family and structured-product proposals scope keys by tenant + source system. A key requires its source system. ETP creation now also supports replay instead of reaching its unique constraint.
- Manual option, swap, futures contract/family and booking-convention proposals accept an optional `idempotencyKey` in the body (1–255 characters), scoped by tenant across manual proposal types. Source-backed keys retain their existing contract. Reusing a key for a different type or economic request is a 409; identical retries return the original proposal, including its current status.
- Transaction-scoped advisory locks serialize concurrent API retries. Comparisons reconstruct the typed request, ignoring only known server metadata (`proposedByUserAccountId`, `enrichmentStatus`), and compare normalized values; decimal spelling/default differences are not different intent. Approval reconstruction uses the same metadata removal so strict request models do not break existing stored proposals.
- Manual creation forms retain the same key while unchanged intent is retried; edited intent gets a fresh key. There is no automatic write retry. Form refresh/unmount does not persist that key: after an uncertain response plus reload, inspect the queue before submitting a new request. Durable draft recovery remains separate UX work.
- Proposal keys have no new TTL: they live with retained proposal records. Approval remains a guarded transition, not a new repeat-decision replay service. Strategies use tenant/code natural identity; duplicate creation returns 409 rather than pretending to be a second successful creation.
- No migration/backfill is required. Source-key uniqueness remains database-enforced; NULL-source manual keys are serialized by these API writers. Direct database writers must not bypass the same policy.

## Resource and contract policy

- Work queue: default/max 100 records, stable timestamp/UUID ordering, offset 0–10,000. Proposals remain ahead of NAV rows. Counts and `meta.total` describe the full queue; `meta.limit/offset` identify the page. Operations and Instrument Requests have navigation links; the instrument page filters creation entries within each queue page, not the entire queue. Server-side capability filters/cursors beyond the alpha browsing budget remain future work.
- Trade-field definition history: default/max 1,000 records per request, deterministic code/version/UUID ordering, bounded offset, and typed pagination totals. The existing configuration register follows bounded pages up to a 10,000-record display budget; it fails explicitly above that budget rather than silently omitting history. Server-side register filters replace this compatibility aggregation in a later UX iteration.
- Strategy detail uses a direct tenant/UUID query. The strategy register itself is not redesigned in this repair.
- JSON body budget: 1 MiB by default, counted across actual ASGI chunks before parsing/database access; oversized requests receive correlated RFC 9457 413s. Individual booking property text is limited to 2,000 characters before domain validation.
- Each request transaction sets LOCAL statement timeout 30 seconds and lock timeout 10 seconds. Settings/env overrides: `REFERENCE_API_MAX_BODY_BYTES`, `REFERENCE_API_STATEMENT_TIMEOUT_MS`, `REFERENCE_API_LOCK_TIMEOUT_MS`; values must be positive. These are per-statement/lock budgets, not a whole multi-statement transaction deadline.
- Shared reference API transport, queue reads and configuration requests use a 35-second fetch deadline. Caller cancellation is retained. A timed-out write remains uncertain and must use its unchanged retry key; timeout is not evidence of rollback.
- Instrument detail publishes `InstrumentResponse` rather than a generic object. Router/service metadata uses the configured dated API version, not hard-coded `v1`; URL major versioning remains unchanged. Older proposal models reject unknown fields instead of discarding typos.

## Verification ledger and remaining gates

Lightweight tests first reproduced false-success commit behavior, missing authority checks, correlation/header loss, unknown status/type acceptance, changed-payload replay, inactive configuration actors, unbounded reads, unspecified detail schemas, oversized annotation/body acceptance and missing transport/time budgets. Each implementation followed its RED check. Tests also cover cross-product key reuse and concurrent source retries.

The initial complete frontend run had one 5-second cold-import timeout (484 passed, 1 timed out). That test passed alone (18 tests), then the complete suite passed with two workers. After manual form-key wiring and stronger regressions, the final frontend run passed **488 tests across 112 files**, followed by TypeScript (exit 0).

The first full isolated Python run passed **896 tests**, with two failures in fault-injection tests expecting raw exceptions. The hardened HTTP boundary returns safe 500s instead; both tests were updated to check status/code/correlation/no secret leakage while preserving trade-count rollback and replay evidence checks. The focused follow-up passed **88 tests** (89.12 seconds, exit 0). Final review also closed empty source-key acceptance and nested-listing multiplier typos; their lightweight RED/GREEN tests passed. The final full isolated Python run passed **902 tests, zero failures** (639.25 seconds, exit 0). It reported 491 warnings, including SQLAlchemy/Starlette deprecations and Pydantic field-attribute warnings; this is not a warning-free delivery. The disposable database was used rather than operating data. Evidence: `logs/api-hardening-python-final.log` and `logs/api-hardening-python-final.xml`; frontend evidence: `logs/api-hardening-frontend-verified.log`.

OpenAPI export/check and generation completed. `contract:generate:check` compares output to committed Git content, so it reports expected dirty-tree changes in this uncommitted delivery; separate regeneration was byte-identical. No commit is created to manufacture a green Git-based check.

## Sequential author review

Reviewed shared dependency consumers, authority-before-lookup/replay paths, generic approval dispatch, safe error/header handling, strict stored-payload reconstruction, source/manual key locking, typed metadata, queue/history pagination and frontend uncertain-response keys. No independent reviewer or subagent was used, per the user's sequential-work instruction. Small compatibility adapters preserve the existing register UI; this is not a new UI redesign.

Behaviors considered and deliberately set aside: real authentication/gateway controls (separate production gate); whole-request/upload deadlines and load testing (deployment work, per-statement limits are explicit); durable draft keys across reload (documented queue-inspection recovery); server-side register/queue filtering and cursor browsing beyond alpha limits (later UX); repository decomposition (avoid a sweeping rewrite); decision replay and contractual/valuation lifecycle (separate workflows). No postponed item is represented as production-ready.

Production identity, trusted-header enforcement at a private gateway, rate limiting, upload/whole-request deadlines, connection-pool/load testing and deployment controls remain mandatory before external exposure. No OAuth/security scheme is invented for demo UUID headers. Repository/router decomposition, durable draft retry recovery, large-register UI filtering, contractual lifecycle and valuation/P&L are outside this bounded repair. Browser sign-off remains paused.
