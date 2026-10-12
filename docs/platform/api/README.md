# API

**Status:** Current alpha reference
**Content type:** Architecture index  
**Owner:** API team  
**Last reviewed:** 2026-10-12

The API/BFF boundary is described by the [Reference Data API](../../../apps/reference_api/README.md), [API contracts](../../../packages/api-contracts/README.md), [tenant routing contract](../../../security-master-notes/20-tenant-routing-and-core-api-contract.md), and [UI data contracts](../../../ui/data-contracts/README.md). Dated API/frontend findings are in [quality reviews](../../delivery/quality-reviews/README.md).

Market-data evidence creation and replay semantics are documented in [Market Data resolution snapshots](market-data-resolution-snapshots.md).

Current API covers platform/tenant access, strategies, governed reference proposals, seven booking paths, history/corrections, source/policy/calendar administration and bounded economic P&L/review. See the [feature register](../../product/feature-register.md) for actual scope; OpenAPI/generated contracts, not this index, own exact endpoints and schemas.

The common boundary applies active tenant/user/module/action checks; production authentication remains separate from local header/session testing. Request context wraps body budgets and authority, retaining safe correlated RFC problem responses. Writes own transaction/replay protection; uncertain BFF timeouts do not cancel server-side work or authorize a new request key. Supplemental audit durability, synchronous execution and representative scaling remain production gaps. [Latest verification](../../delivery/tenant-access-administration-progress.md#completed-remediation-verification) records failed broad diagnostics and successful focused fixes accurately.
