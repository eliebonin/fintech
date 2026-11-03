# Dataset rights and expensive-work admission implementation plan

> Execute sequentially in the authorised checkout with focused red/green tests.
> The user has authorised implementation without another plan approval. Preserve
> unrelated changes; do not commit/push or use subagents.

**Goal:** Deny missing dataset governance consistently and prevent concurrent
expensive requests from consuming the API's shared capacity.

**Architecture:** Rights remain below HTTP. Explicit SYNTHETIC profiles and
origin evidence cover invented seed/test data; PERSONAL/COMMERCIAL evidence is
unchanged. A nonblocking application admission controller, coordinated across
workers using dedicated PostgreSQL advisory-lock connections, surrounds expensive
HTTP work after verified identity and before domain connection acquisition.

**Scope choices:** Preserve the synchronous API and existing retained run/retry
workflow. Busy means no command was started, HTTP 429 and Retry-After. Do not add
a new queue/worker platform in this local hardening step. Background durable jobs,
process memory/CPU budgets and production capacity certification remain separate
deployment work, explicitly recorded rather than claimed resolved. No financial
population caps, source/provider restrictions or altered formulae.

## Design and alternatives

- Missing profiles must deny, including unknown requested dataset IDs. A blanket
  personal/commercial backfill would invent rights; restricting shared mock data
  to one tenant would cut existing functionality. Instead retain explicit
  synthetic-origin evidence, requiring ordinary activity and tenant-purpose checks.
- A process-only semaphore would fail with multiple API workers. Sharing the
  business pool for long-held control locks could deadlock one-connection preview
  pools. Use a separate small coordination pool plus local nonblocking slots,
  and deterministic global/tenant lock slots. Release or invalidate on all exits.
- Retain synchronous workflows with fail-fast backpressure. A background queue
  would require a separately reviewed durable worker/cancellation/deployment
  lifecycle; it is not necessary to reject excess concurrent work safely.

## Tasks

- [x] Reproduce missing-profile DISPLAY/NON_DISPLAY and purpose bypasses; retain
  expiry, layered requirements, tenant coverage and current release checks.
- [x] Add migration 106 for explicit synthetic scope/origin, provision only the
  five exact seed identities and link normal demo seeding to the same helper.
  Never mutate real source profiles or rewrite frozen evidence.
- [x] Refactor batched rights to start from all datasets, including missing
  profiles; enforce INTERNAL_REPORTING purpose for every display path.
- [x] Verify existing real profiles stay unchanged; explicitly govern new
  synthetic fixtures rather than inserting automatic test authorization bypasses.
- [x] Reproduce workload overload; implement configurable process/global/tenant
  admission, shared advisory locks, safe cleanup and retryable 429 before effects.
- [x] Cover valuation/reassessment, monetary previews, import validation/confirm
  and regulatory preparation/export work; ordinary reads remain available.
- [x] Forward Retry-After through the BFF and show readable safe-retry messaging;
  do not label a rejected request as a running calculation or retry automatically.
- [x] Verify two-worker admission, tenant independence, worker failure cleanup,
  protected one-connection pools, numerical parity and unchanged public contracts
  except documented busy responses. Apply tested migration/profile backfill.
- [x] Update capability/register/map, AGENTS/KNOWLEDGE/FIX and bounded delivery
  evidence. Keep durable queue/OS resource limits distinct from admission.

## Primary guidance reviewed 30 October 2026

- [OWASP deny by default](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html#deny-by-default)
- [OWASP API resource consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/)
- [PostgreSQL advisory-lock semantics](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS)
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
