# MVP UI scope

## Product objective

Give a fund-manager operations team one reliable workspace to identify
financial objects, resolve provider/custodian identifiers, review market-data
evidence, book and correct trades, and produce a reviewable Soft-NAV run.

## Primary users

| User | Main need |
|---|---|
| Operations analyst | Create and maintain canonical records, resolve exceptions, book trades. |
| Portfolio manager | Inspect instruments, listings, prices, positions, and valuation evidence. |
| NAV reviewer | Review Soft-NAV inputs, stale/missing data, FX choices, and approve/reject a run. |
| Security-master steward | Approve canonical definitions, identifiers, mappings, and effective dates. |
| Tenant administrator | Manage tenant users, entitlements, and approved local overrides. |

## MVP screens

1. **Home / work queue** — unresolved mappings, stale prices, pending approvals,
   failed imports, and NAV runs awaiting review.
2. **Global search** — search by Fortem UUID, ISIN, FIGI, ticker/listing,
   bank/custodian/client code, or name; show whether the match is canonical,
   tenant-local, or an external mapping.
3. **Instrument detail** — economic instrument, listings, identifiers,
   issuer/parties, effective definition versions, terms, taxonomy, and related
   products.
4. **Listing and market-data view** — venue-specific series, valuation cuts,
   dates, quote factor/unit multiplier, provider/dataset/licence, and vintage
   lineage.
5. **Trade booking and detail** — one booked economic event, subject/reference
   instrument, parties, execution channel, price basis, strategy, and lifecycle
   corrections.
6. **Soft-NAV run review** — position/cash snapshot, independent price and FX
   selections, T-1 date rules, stale/missing exceptions, mark evidence, and
   approval outcome.
7. **Administration** — users, tenant context, entitlements, source mappings,
   and steward approval queues.

## Explicit non-goals for MVP

- Full order-management or execution management.
- Portfolio construction or rebalancing.
- Real-time trading blotter or tick-charting.
- Editing raw market data, trades, source payloads, or historical snapshots.
- Replacing official administrator NAV or custody/accounting platforms.
- A generic rules-builder exposed to end users.

## Cross-cutting requirements

- Pages use server-first rendering; browser components are limited to
  interaction-heavy behaviour and never connect directly to databases.
- Tenant context is selected from authenticated identity and cannot be chosen
  by a request field.
- Destructive actions are replaced with propose/approve, supersede, cancel, or
  correction flows.
- Detail pages show `created_at`, effective dates, status, source, and UUID.
- Empty, stale, ambiguous, unauthorized, and pending states are first-class
  UI states with actionable explanations.
- Every approval and correction displays the actor, timestamp, reason, and
  prior version/event it supersedes.
