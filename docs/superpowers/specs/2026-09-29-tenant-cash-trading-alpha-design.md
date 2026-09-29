# Tenant workspace and cash-trading alpha design

**Status:** Proposed for review  
**Date:** 2026-09-29  
**Scope:** Tenant-facing operating journey through strategy setup, instrument use,
tenant classification, and plain-cash trade booking.  
**Out of scope:** Production authentication, support impersonation, OTC trade
booking, valuation, NAV, P&L, confirmations, settlement processing, and accounting.

## 1. Purpose and success criteria

The alpha must let a real user operate inside a tenant without manually supplying
tenant IDs or relying on fixture-only screens. The first complete journey is:

```text
sign in / local alpha identity
  -> choose an active tenant membership
  -> see the tenant's enabled modules
  -> create and manage strategies
  -> find a shared instrument or propose a tenant-owned instrument/listing
  -> apply tenant classifications
  -> book and inspect a plain-cash trade
```

The user wants an operator to be able to represent fund-management, asset-management,
and proprietary-trading organisations in one platform. The alpha must make the
strategy's operating purpose explicit while preserving the canonical shared security
master and its governed approval workflows.

Success means a permitted user can complete the journey above, while a user without
the required tenant membership or module entitlement cannot see or invoke the action.
Every created business record carries its tenant and actor provenance. The UI must
show human-readable codes and names rather than asking an operator to work from UUIDs.

## 2. Authority model

### 2.1 Roles

The alpha separates authority into three layers:

| Role | Scope | Alpha permissions |
| --- | --- | --- |
| Tenant member | One active tenant membership | Can see modules and actions granted by membership role and module entitlement. |
| Tenant administrator | One active tenant membership | Can manage tenant strategies, tenant classifications, and tenant-operational setup when the respective module is enabled. |
| Platform administrator | Platform control plane, not tenant business data | Can manage tenant setup and entitlement grants in a separate platform area. It cannot impersonate a tenant in this alpha. |

Platform administration is a distinct role/authority source, not a special tenant
membership. A platform administrator who also works for a tenant uses an ordinary
tenant membership to enter that tenant's workspace.

### 2.2 Tenant selection

At alpha sign-in, the BFF derives the available active memberships for the current
user and presents a tenant switcher. The selected tenant is stored in the
server-side session and used exclusively by server BFF calls to the Reference API.
The browser never chooses an arbitrary tenant ID for an API request.

The active-tenant chrome displays the tenant name/code, membership role, and enabled
modules. Switching tenant clears tenant-scoped cached data and returns the user to
the tenant home. A tenant that is inactive, not a current membership, or not
permitted for the session cannot be selected.

The existing trusted-header local seam remains valid only for local alpha development.
The API contract must continue to isolate that seam so later Auth0/OIDC claim
validation can replace it without changing business endpoints.

### 2.3 Module visibility and enforcement

The workspace renders a module navigation item only when the active tenant has a
current `GRANTED` entitlement for the module. The BFF and Reference API both enforce
the same entitlement; hiding a link is not authorization.

Initial module/action mapping:

| Module | Alpha actions |
| --- | --- |
| Security Master | Search canonical instruments; submit/inspect tenant instrument or listing proposals; maintain tenant classifications. |
| Trading | Create, inspect, and correct cash trades. |
| Fund Management | Create/manage fund-oriented strategies and use fund/share-class instruments. |
| Valuation | Visibility only where already implemented; no new valuation scope in this alpha. |

## 3. Strategy model and workflow

`trd.strategy` remains the tenant-owned investment mandate/container. Alpha adds a
controlled operating-model classification to make its business role clear without
duplicating legal fund, organisation, or portfolio data.

The first controlled values are:

- `AMC_MANDATE` — an asset-management-company mandate or book;
- `FUND` — a fund or sub-fund strategy;
- `MANAGED_ACCOUNT` — a separately managed client/account mandate;
- `PROP_SLEEVE` — a proprietary trading sleeve;
- `MODEL_PORTFOLIO` — a model portfolio;
- `OTHER` — permitted only with a mandatory explanatory label.

A strategy has a stable tenant-unique code, display name, operating model, status,
base/reporting currency, optional legal/management organisation reference, optional
parent strategy, and effective dates. It is not itself an instrument and it is not a
substitute for a legal fund entity or fund-share-class master record.

The initial strategy journey is:

1. Tenant administrator opens **Strategies** and selects **Create strategy**.
2. The form explains the operating-model choice in business language.
3. The API validates membership, `TRADING` or `FUND_MANAGEMENT` access as appropriate,
   tenant-unique code, valid dates, and references.
4. The created strategy appears in a tenant-scoped strategy list/detail page.
5. Archived strategies remain readable but cannot receive new trades.

An activity/audit view must show creator, creation time, and subsequent status changes.

## 4. Instruments and tenant classification

### 4.1 Shared master versus tenant-owned records

The canonical security master remains shared and governed. A tenant does not freely
edit canonical economic identity. In a trade flow an operator first searches the
canonical master, including eligible listings, by name/code/identifier.

When the required cash instrument or listing is absent, the operator uses the existing
proposal workflow for the relevant product family. The request is tenant-scoped and
retains source/actor provenance. Approval creates or links the canonical record; it
does not silently create an ungoverned duplicate.

Tenant-specific operational identifiers, mappings, custom display labels, and
classifications are tenant overlays. They may reference a canonical instrument or
listing but cannot alter canonical economics.

### 4.2 Taxonomy

Alpha provides a tenant classification assignment surface, not a new free-form global
taxonomy editor. A tenant administrator can assign a permitted taxonomy node/value to
a canonical instrument/listing in a tenant context, with effective dates and source.
The first supported uses are internal asset buckets, desks, investment universes, and
restricted/approved-list indicators.

The UI distinguishes:

- canonical taxonomy — shared, governed reference classification;
- tenant classification — overlay usable by that tenant only.

Assignments are versioned/effective-dated. Removing or changing a classification
creates a successor record or closes validity; it does not rewrite prior trade context.

## 5. Plain-cash trade booking

### 5.1 Supported products

The alpha supports cash-style trades on approved, tradeable canonical instruments or
listings in these families:

- equities;
- bonds;
- funds and fund share classes;
- exchange-traded products;
- FX spot;
- cryptoassets.

OTC swaps, forwards, options, structured products, and fund OTC/subscription-specific
flows are explicitly deferred. Some required terms for those products belong to the
instrument/contract description; the alpha does not create or duplicate those
contracts at trade-booking time.

### 5.2 Trade boundary

The trade references an existing selected instrument/listing and strategy. It records
execution facts, not a second copy of instrument economics:

- strategy and selected tradable subject;
- buy/sell direction, trade type/purpose, and market activity;
- quantity and unit;
- execution price and price currency;
- trade datetime, instruction date, settlement date;
- trader and booking user;
- execution channel, external/client references, free metadata, and controlled tags;
- counterparties and fees where provided;
- source system and lifecycle provenance.

The UI validates the product-appropriate minimum facts before submission. For example,
the tradeable listing, its trading currency, and appropriate quantity/price basis are
displayed from the selected record instead of being typed as ungoverned free text.

### 5.3 Lifecycle and corrections

Creating a trade produces a `BOOKED` trade and its first append-only lifecycle event.
The trade detail page is immutable in place. A correction creates a later lifecycle
event and, where required by the existing model, a linked correction/replacement
record; it never updates historic booking facts invisibly.

Alpha supports create, list, detail, and a focused correction/cancellation action.
Allocation, confirmation matching, settlement workflow, corporate-action processing,
and accounting postings are later modules.

## 6. User experience and route shape

The existing Ops Console is the alpha client. It remains a BFF-only client: the browser
does not receive PostgreSQL credentials or direct tenant API authority.

Proposed primary routes:

```text
/select-tenant
/workspace                         tenant home and module tiles
/strategies                         tenant strategy list
/strategies/new
/strategies/[strategyId]
/instruments                        canonical search and tenant overlays
/instruments/propose                routes into existing product proposal flows
/instruments/[instrumentId]/classifications
/trades                             tenant cash-trade ledger
/trades/new
/trades/[tradeId]
/platform/tenants                   platform administrator only
```

Every workspace page carries active-tenant chrome. The trade form is a guided flow:

1. Choose strategy.
2. Search/select approved instrument or listing.
3. Enter transaction facts.
4. Add optional counterparties, fees, tags, and references.
5. Review a human-readable booking summary.
6. Submit once with an idempotency key and show the persisted `BOOKED` result.

## 7. API and data-boundary design

The Reference API gains tenant-scoped read/write endpoints for:

- current-session membership/available tenants and effective module entitlements;
- strategy create/list/read/status transition;
- tenant classification assignment/list/effective-dated close;
- cash trade create/list/read/correction/cancellation.

The BFF exposes narrow view/command endpoints and converts API errors to stable UI
problem contracts. It obtains actor and active tenant from the session. It creates and
preserves idempotency keys for mutation retries.

New persistence work must extend existing tenant, strategy, trade, taxonomy, audit,
and proposal patterns. It must not introduce a parallel tenant table, client-owned
tenant headers, arbitrary JSON-only product economics, or destructive updates of
auditable facts.

## 8. Error handling and controls

- Invalid or expired membership: fail closed with the standard safe authorization
  problem response.
- Missing module entitlement: return forbidden; do not disclose other tenant data.
- Strategy not active or outside the tenant: reject booking.
- Non-tradeable / unresolved instrument: reject booking and direct the user to a
  proposal/search resolution path.
- Duplicate submission: replay the original command result where idempotency matches;
  conflicting key reuse fails deterministically.
- Validation errors: field-level, human-readable messages; UUIDs remain diagnostic
  identifiers, not the primary display value.
- Tenant change during an open form: invalidate the form and require the user to
  restart under the newly selected tenant.

All mutations retain actor, tenant, timestamp, correlation/idempotency context, and
an append-only audit/lifecycle trail.

## 9. Verification

Implementation must add tests at each boundary:

- repository tests for tenant isolation, effective dates, uniqueness, lifecycle
  immutability, and idempotent creates;
- API tests for membership, module entitlement, role/action authorization, safe
  problem responses, and cross-tenant access denial;
- BFF tests proving the browser cannot set an arbitrary tenant and preserving retry
  keys on mutation retries;
- Ops Console tests for tenant switcher/module visibility, strategy classification,
  instrument selection/classification, trade-booking validation, and correction flow;
- a deterministic end-to-end alpha scenario that creates a strategy, selects a
  canonical cash instrument, assigns a tenant classification, books a trade, and
  reads it back under the same tenant.

The CI repair is a prerequisite: PostgreSQL must be provisioned in the hosted Python
job so this evidence is reproducible outside the local Docker environment.

## 10. Delivery sequence

The work is deliberately sequenced as vertical slices:

1. **Access foundation:** session-backed tenant selection, membership list, module
   home, platform-admin boundary, and CI PostgreSQL provisioning.
2. **Strategies:** controlled operating models, strategy API/BFF/pages, roles and
   audit trail.
3. **Instrument overlays:** canonical search refinement, tenant classifications, and
   guided links to current proposal flows.
4. **Cash trading:** cash trade command/read model, ledger/detail UI, idempotency,
   append-only correction/cancellation.
5. **Integrated alpha:** end-to-end scenario, usability pass, evidence labels, and
   documentation updates.

Market-data resolution, valuation, Soft NAV, and P&L are intentionally not expanded
until this operating loop is usable. The next programme will connect these booked
positions to governed, persisted market-data resolution snapshots.

## 11. Explicit decisions and later decisions

Decided for this alpha:

- Tenant selection, not support impersonation.
- Distinct platform-admin authority, but no tenant impersonation.
- Fixed strategy operating-model catalogue with `OTHER` explanation.
- Plain cash instruments only.
- Instrument economics belong to the selected instrument/listing; trade records
  execution and lifecycle facts.
- Append-only corrections rather than mutable historical trades.

Deferred decisions:

- Authentication provider and production claims mapping.
- Detailed tenant-admin permission matrix and maker/checker requirements.
- Free-form tenant taxonomy authoring versus governed taxonomy-catalogue extension.
- OTC contract-definition and booking workflows.
- Position generation, market-data selection, valuation, NAV, and P&L rules.
- Platform-admin tenant onboarding and entitlement-grant user interface details.
