# API

[Local identity safeguard](../local-identity-safeguard.md): protected calls require
verified opaque sessions and bootstrap requires a private operator capability.
Header-only/demo identity is disabled; production authentication remains deferred
and non-local API startup is blocked.

**Status:** Current alpha reference
**Content type:** Architecture index  
**Owner:** API team  
**Last reviewed:** 2026-10-12

The API/BFF boundary is described by the [Reference Data API](../../../apps/reference_api/README.md), [API contracts](../../../packages/api-contracts/README.md), [tenant routing contract](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md), and [UI data contracts](../../../ui/data-contracts/README.md). Dated API/frontend findings are in [quality reviews](../../delivery/quality-reviews/README.md).

Market-data evidence creation and replay semantics are documented in [Market Data resolution snapshots](market-data-resolution-snapshots.md).

[Service extraction phases 1–3](../../delivery/api-service-extraction-20261029.md)
place policy commands/models in `market_data` and shared exact evidence primitives
in `security_master_schema`. HTTP responses, errors, current access boundary and
atomic request audit remain API-owned. Catalogue/options/preview and broader
reference/booking decomposition are still partial; no endpoint/schema change.

The subsequent [cash-booking extraction](../../delivery/cash-booking-service-extraction-20261029.md)
places the cash command, its models/store and supporting validators in `trading`.
HTTP and file confirmation share it. HTTP response projection remains inside a
savepoint; outer request audit and all-or-nothing import receipts stay with callers.
Other product writers and cancellation orchestration remain API-owned.

Current API covers platform/tenant access, strategies, governed reference proposals, seven booking paths, history/corrections, source/policy/calendar administration and bounded economic P&L/review. See the [feature register](../../product/feature-register.md) for actual scope; OpenAPI/generated contracts, not this index, own exact endpoints and schemas.

The common boundary applies verified local sessions and active tenant/user/module/action checks; production authentication remains separate from local testing. Request context wraps body budgets and authority, retaining safe correlated RFC problem responses. Authorization DB work is offloaded as a complete sync unit with transaction budgets. Shared governance dates are request-pinned UTC, not exchange/economic dates. Writes own transaction/replay protection and atomic request audit; independently committed calculations retain request acceptance with the durable attempt. Uncertain BFF timeouts do not cancel server-side work or authorize a new request key. Monetary previews separate stable financial reads from current-rights release checks. [October 16 fixes and remaining limits](../../delivery/quality-reviews/2026-10-16-backend-remediation.md) supersede the earlier request-reliability findings. Representative scaling, remaining domain decomposition and non-local identity are still open.
