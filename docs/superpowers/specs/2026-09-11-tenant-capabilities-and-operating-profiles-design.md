# Tenant capabilities and operating profiles

**Status:** Approved for implementation  
**Date:** 2026-09-11  
**Owner:** Platform tenancy, product operations, and security architecture

## Decision

Tenant profiles are plural, effective-dated business classifications. A tenant
may simultaneously be a fund manager, AMC manager, trading-book manager, and
structured-product distributor.

Module entitlements, not profiles, enforce access. A tenant receives an
approved, effective-dated grant to each platform module it may use.

## Separation of concerns

| Plane | Purpose | Enforcement |
| --- | --- | --- |
| Tenant isolation | Bound a request to one tenant | Routing and database boundary |
| Operating profiles | Describe business operating model | Onboarding and UI defaults |
| Module entitlements | Enable purchased/approved capabilities | Server capability resolver |
| User authorisation | Control each account's actions | Role/resource checks |
| Data entitlements | Control licensed data use | Dataset/licence resolver |
| Release flags | Control beta release and kill switches | Technical rollout only |

## Schema

All new tables live in `ten`.

`operating_profile` is the governed profile catalogue. Example codes are
`FUND_MANAGER`, `TRADING_BOOK_MANAGER`, `AMC_MANAGER`, and
`STRUCTURED_PRODUCT_DISTRIBUTOR`.

`tenant_operating_profile_assignment` assigns profiles to tenants with an
effective period, lifecycle state, assignment source, approver, and
supersession lineage. Different active profile assignments may overlap.

`platform_module` is the governed capability catalogue. Initial module codes:

- `SECURITY_MASTER`
- `MARKET_DATA`
- `TRADING`
- `VALUATION`
- `FUND_MANAGEMENT`
- `FUND_OPERATIONS`
- `UCITS_CONTROLS`
- `AMC_MANAGEMENT`
- `STRUCTURED_PRODUCTS`
- `STRUCTURED_PRODUCT_DISTRIBUTION`

`operating_profile_module_recommendation` supplies transparent onboarding
templates. It never gives API access by itself.

`tenant_module_entitlement` is the effective-dated, audited module grant or
revocation. It records a `GRANTED`, `SUSPENDED`, or `REVOKED` state and a
source such as `CONTRACT`, `TRIAL`, `MANUAL`, or `MIGRATION`.

## Resolution

The server resolves active capability codes from:

```text
tenant_id + as_of_date -> effective GRANTED module codes
```

The UI uses the capability set to shape navigation. Every API endpoint still
validates tenant membership, tenant isolation, required module, user
permission, and applicable data entitlement in that order.

Removing an operating profile never silently removes a module. Revoking a
module is its own explicit, audited lifecycle operation.

## Non-goals

- No billing engine or feature-flag provider.
- No replacement for user membership roles.
- No general per-module configuration JSON.
- No entitlement-administration UI in this slice.

## Deferred work

1. Billing/subscription integration.
2. Module quotas and sub-capabilities.
3. Technical feature flags for staged rollout.
4. Tenant-admin UI and API middleware capability cache.

## Research evidence

- [AWS tenant isolation](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/tenant-isolation.html)
- [Azure multitenant configuration](https://learn.microsoft.com/th-th/azure/architecture/guide/multitenant/approaches/deployment-configuration)
- [AWS multi-tenant building blocks](https://aws.amazon.com/isv/resources/building-blocks-of-multi-tenant/)
- [OpenFeature evaluation context](https://openfeature.dev/docs/reference/concepts/evaluation-context/)
- [Stripe entitlements](https://docs.stripe.com/billing/entitlements?locale=en-GB)
