# API endpoint implementation review

**Reviewed:** 2026-10-06.  
**Status:** Review complete; historical findings retained. Approved alpha remediation and verification are tracked in [API boundary hardening](../api-boundary-hardening.md).  
**Checkout:** `codex/enriched-trade-booking`, HEAD `3856214`, including current uncommitted work.  
**Scope:** Reference API endpoint boundaries, authorization, transactions, validation, retries, errors, contracts and operational limits. The BFF identity/client boundary was sampled. Valuation algorithms and browser sign-off are outside this review.

## Conclusion

The API is a useful local alpha with substantial domain integrity and regression coverage, but it is not ready for production exposure. The most urgent functional issue is success being emitted before the outer database transaction commits. The most urgent policy issue is inconsistent role/module enforcement across older and newer instrument workflows. Fix these shared boundaries before adding more endpoint families. A rewrite, microservices split or generic event platform is not warranted.

This review used the `best-practice` skill to research and read primary guidance, and systematic debugging to distinguish reproducible failures from static risks. It inventoried all **88 OpenAPI operations across 82 paths**, then inspected the shared boundary and representative service paths; this is not an exhaustive penetration test or proof that every service branch is safe. Installed versions were FastAPI 0.141.1, Starlette 1.7.0, Pydantic 2.13.5 and SQLAlchemy 2.1.1.

## What is working well

- Typed booking request models reject unknown fields and constrain annotations; product-specific economics remain in domain services rather than a generic permissive booking endpoint.
- Booking services share current writer authorization, active tenant-scoped strategy locking, tenant/endpoint-scoped idempotency locks and payload fingerprints. A different payload under an existing key conflicts instead of silently creating another trade.
- Corrections retain original evidence and explicit lineage; expected sequences, row locks and savepoints protect competing corrections and late service-level failure. Unsupported lifecycle evidence fails closed.
- Recent cash and FX/bond/ETP approval hardening rechecks governed dependencies under locks. This is meaningful integrity work, although approval-time dependency validation is not a substitute for approval authority.
- SQLAlchemy statement construction and tenant predicates are used in the inspected trade/proposal paths. Search/history pagination has server-side maxima; trade history has a deterministic date/UUID order.
- RFC 9457 problem responses, safe unexpected-error bodies, typed contract export and generated frontend types provide a sound foundation. The defects below are gaps within that foundation, not reasons to discard it.

## Prioritized findings

### 1. P1 — Outer commit happens after a successful response

Evidence: [shared connection dependency](../../../apps/reference_api/main.py#L90) uses `engine.begin()` around `yield`; consumers use `Depends(connection_dependency)` without function scope. The SQLAlchemy context commits when it exits, whereas this FastAPI version defaults yielded dependencies to request scope, exiting after response transmission.

Reproduction: an in-memory fake engine was injected into the **actual application factory**. The strategy service/authority were stubbed to isolate the boundary, and the engine's outer transaction exit raised a synthetic commit failure. `POST /v1/strategies` still returned **201 with success data**. No real database writes occurred in this probe. This establishes the response-order defect, not its production frequency.

Impact: a commit-time failure can leave the browser believing a strategy, trade, approval or correction succeeded when durability was not established. Inner savepoints do not commit the outer transaction. A response can also advertise a resource before it becomes visible to another request.

Recommendation: make transaction finalization happen before sending success. Function-scoped connection dependencies are a small candidate supported by the installed FastAPI; review response serialization and dependency relationships before adopting them across routers. Add HTTP tests for outer commit failure and confirm rollback, no false 2xx, safe error correlation and authorized retry behavior. Do not solve this by scattering commits through repositories. This diagnosis follows [FastAPI yielded-dependency scope](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#early-exit-and-scope) and [SQLAlchemy transaction context semantics](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine.begin).

### 2. P1 — Approval and creation authority is inconsistent

Evidence: older mapping/equity/bond/ETP/FX/index/structured-product routes in [main.py](../../../apps/reference_api/main.py#L272) principally call `_assert_tenant_membership`. Inspected mapping/equity decision services do not then require a specific membership role or module. The generic decision dispatcher delegates that policy to each product. Conversely, [option approval](../../../apps/reference_api/option_onboarding.py#L38) and [new product approval](../../../apps/reference_api/product_booking.py#L239) demand administrator/trading authority.

A fake-database HTTP probe of the mapping decision endpoint returned **200** and reached simulated INSERT/UPDATE operations after active-account/membership queries, with **no role or module query**. This supports the source finding; it was not an attack against operating data. Under the inspected code, an active READ_ONLY membership is not distinguished from an administrator on that path.

Further gap: `_assert_tenant_membership` checks account and membership status/dates, but not the tenant's ACTIVE status. `resolve_tenant_workspace` does check active tenants; many older read/write routes never call it. Consequently tenant retirement is not uniformly enforced. Approval denial also differs by product: some role refusals become workflow conflicts instead of 403.

Recommendation: establish explicit read, propose, approve, configure and book actions, then enforce a consistent authority matrix at the server boundary and service level where services are directly callable. Do not automatically impose TRADING on every reference-data action; decide which modules/roles actually own reference stewardship. Add negative tests for READ_ONLY, non-admin, missing module, inactive account, expired membership, inactive tenant and foreign IDs through both generic and type-specific aliases. This is aligned with [OWASP function-level authorization](https://api-security.owasp.org/editions/2023/en/0xa5-broken-function-level-authorization/); the precise role matrix remains a project decision.

### 3. Production gate — Identity remains a local demo trust model

[tenant_context.py](../../../apps/reference_api/tenant_context.py#L34) accepts actor/tenant UUID headers without authenticating who supplied them. The BFF's [tenant session](../../../apps/ops-console/src/lib/tenant-session.ts#L36) supplies an environment/demo user rather than a per-user authenticated identity. Signing the selected-tenant cookie prevents arbitrary tenant-cookie alteration but does not authenticate a person. A configured production cookie secret does not change that fact.

This is acknowledged in the API README and the provided launch commands bind the API to loopback; it is an intentional alpha limitation, not evidence that the API is currently public. It becomes high risk if exposed to untrusted clients or reachable through an unprotected proxy.

Recommendation before deployment: real user/session authentication, verified issuer/audience/expiry as applicable, server-derived actor context, and an authenticated BFF-to-API boundary that cannot be forged by direct headers. Fail closed on demo identity/default settings outside local mode. Confirm cookie-based write origin/CSRF policy during that integration. [OWASP authentication guidance](https://api-security.owasp.org/editions/2023/en/0xa2-broken-authentication/) supports robust identity verification; it does not require one particular authentication vendor.

### 4. P2 — Error handling has reproduced correlation and protocol gaps

In [problem_details.py](../../../apps/reference_api/problem_details.py#L81), middleware resets the request-ID context before an escaping exception reaches the outer unexpected-error handler. That handler calls a fallback UUID generator for logging and again for the response body.

- A synthetic unexpected 500 lost the supplied `X-Request-ID`: the response header was absent and body/log IDs differed from the supplied ID and from each other.
- POST to a GET-only synthetic route returned 405 without `Allow`; the HTTP exception handler discards exception headers. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.6) requires that header for 405 responses.
- A probe with successful authority stubs submitted `status: INVALID` to the actual strategy-status route and returned **500/internal.error**. [StrategyStatusRequest](../../../apps/reference_api/contracts.py#L67) accepts any string, and `archive_strategy` raises an uncaught ValueError for unsupported values.

Recommendation: use one request-state correlation value in every error/log/header path; retain necessary safe protocol headers; use typed request enums and explicit domain-error mapping so invalid requests become 4xx. Keep raw exception content private. Extend tests to assert all three behaviors, not only that 500 bodies hide messages. [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) supports consistent machine-readable errors; correlation IDs are our own extension convention.

### 5. P2 — Retry protection outside booking is uneven

Booking/cancellation fingerprints are strong. Older equity/listing proposal source keys, however, return an existing proposal without checking whether the submitted payload changed; see [listing submission](../../../apps/reference_api/repository.py#L1925). Manual newer product proposals and strategy creation do not share booking-style idempotency. A repeated approval is normally a 409 rather than a replay of the original outcome.

Recommendation: classify mutation endpoints by safe-repeat, natural identity or explicit idempotency requirements. Prioritize proposal creation and uncertain-response recovery; reject changed payloads under reused keys. Keep current authorization ahead of replay. Document key scope, retained outcome and expiry semantics. Do not require a new idempotency infrastructure for every naturally repeatable status/read operation. This is an engineering recommendation based on observed inconsistency, not a blanket HTTP requirement that all POSTs be idempotent.

### 6. P2 — Resource bounds need completion

The work queue loads every pending proposal and matching NAV review row; property configuration lists all definition versions, and strategy detail currently retrieves the entire tenant strategy list before selecting one. Several query endpoints have sensible page limits, but these paths do not. The inspected API/DB configuration has no explicit body-size, statement-timeout or lock-timeout policy; sampled BFF API clients have no explicit request deadline. External gateway limits were not inspected and are unknown.

Recommendation: paginate unbounded collections, query strategy detail directly, constrain individual annotation values and request bodies, and set coordinated DB/request/lock budgets. Add rate/resource controls at the chosen deployment boundary. Choose cursor pagination only where volume/concurrent inserts justify it; existing bounded offset pagination is adequate for an alpha catalogue. [OWASP resource-consumption guidance](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/) supports limits on payloads, page sizes, execution and request frequency.

### 7. P2/P3 — Contract and implementation drift remain

- `GET /v1/instruments/{instrument_id}` advertises a generic object with `additionalProperties: true`, despite returning a rich instrument envelope. Having typed `InstrumentView` elsewhere does not constrain this endpoint's response contract.
- The OpenAPI document has no security schemes or operation security requirements; UUID header parameters must not be mistaken for an authentication scheme.
- New booking/readiness routers hard-code `apiVersion: v1`, while main routes use Settings' dated API version.
- Older mutation models use Pydantic's default extra-field ignoring, unlike strict newer tickets. Silent typo acceptance is undesirable for controlled writes. [Pydantic's documented configuration](https://pydantic.dev/docs/validation/latest/api/pydantic/config/#pydantic.config.ConfigDict.extra) explains the behavior; forbidding extras is our recommended mutation policy, not a universal rule for every model.
- Authorization uses host-local `date.today()` while economic booking dates use explicit UTC. Define the governance clock rather than assuming every deployment uses the same timezone.
- `main.py` holds 51 decorated operations in 1,065 lines; `repository.py` mixes many domains. There are router-local policy/meta/error patterns and compressed code that make consistency harder to audit.

Recommendation: typed response envelopes, one metadata/error policy and an accurate endpoint/authority inventory first. Document security schemes when the real mechanism exists. Then extract routers/services by capability in small tested steps, preserving product-specific rules. Do not spend the next iteration on a sweeping repository rewrite.

## Verification and limitations

- Fresh boundary/problem/contract run: **9 passed**, 4.30s, exit 0.
- Fresh focused isolated PostgreSQL run: **112 passed**, 67 warnings, 79.21s, exit 0. Covered workspace, reference reads/review/queue, cash booking/history, cash/approval integrity, historical booking, correction and product readiness modules. The runner created, migrated and seeded a disposable database and completed its cleanup.
- OpenAPI export check: exit 0. Generated contract synchronization does not prove every endpoint schema is sufficiently specific.
- Separate in-memory HTTP probes reproduced the commit-order, 500 correlation, 405 header and invalid-status failures, plus the older approval gate behavior. Existing tests passing does not supersede those observations. Probe code was executed in ephemeral processes, not added to the repository.
- No full-suite rerun in this review, independent reviewer, live penetration test, load test, production gateway inspection or browser acceptance. No API code, application settings or operating records were changed; no app restart or GitHub push. The previously documented browser sign-off remains paused.

## Recommended next sequence

1. Correct the shared transaction/response boundary and add outer-commit HTTP regressions.
2. Agree and enforce the endpoint authority matrix, including inactive-tenant refusal and negative approval tests.
3. Fix error correlation, protocol headers and malformed-request 4xx mapping.
4. Standardize proposal retry behavior and complete bounded contracts/resource limits.
5. Finish real identity/deployment hardening before any production exposure; it can proceed earlier if deployment is imminent.

Items 1–4 harden the present alpha. Item 5 is a deployment gate. Contractual lifecycle and valuation/P&L are separate product work and are not prerequisites for correcting these API boundaries.
