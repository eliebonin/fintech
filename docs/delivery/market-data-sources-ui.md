# Market data providers, scope and source priorities

Delivered 2026-10-08. Local database migration: **20261008_74**.

## Where to find it

Open `/market-data/sources` from **Data sources** in the workspace menu, or from the configuration links on Market data. The running local UI is `http://localhost:3000/market-data/sources`.

**Providers & scope** lists only datasets currently entitled to the selected tenant. Each card separates delivery provider, product and dataset, shared/tenant-owned identity, effective dates, intended purposes, coverage description and non-display activity permission. Expand details to inspect content-owner/market packages, information timing, dataset UUID/code and purpose-specific entitlement coverage. Reporting and valuation coverage are not interchangeable. Missing package definitions are explicitly labelled; a dataset-wide grant does not certify coverage for every instrument. Confidential agreement/evidence references are not returned.

**Source priorities** shows the effective order by instrument type for **VALUATION**, with platform defaults, tenant overrides, configuration version and timestamp. There is a separate editor for entitled valuation sources. Move sources up/down, exclude/add them, save a tenant override, or restore platform inheritance. Platform administrators additionally see the platform-default scope; tenant-private sources cannot be placed in global defaults. All readers can inspect, but tenant writes require TENANT_ADMIN + MARKET_DATA and platform writes require PLATFORM_ADMIN + MARKET_DATA and an active tenant workspace.

## Selection behaviour

Authority clarification (2026-10-12): tenant editing now follows effective `MARKET_DATA_MANAGE` group/admin permissions, not the original administrator-only role wording above. Platform-default editing remains platform authority in an active governed workspace. Source grants and rankings are separate. See [current access](../product/features/access-and-strategies.md) and [source priority](../product/features/market-data.md#f28-provider-catalogue-and-priority).

- Orders rank **datasets**, not provider names. Distinct products/markets can therefore have independent source preferences without inventing separate delivery-provider identities.
- A saved CUSTOM order excludes every omitted dataset. An empty CUSTOM order explicitly excludes all sources for that instrument type; it does not restore legacy selection.
- Tenant-owned sources are suggested first in an unsaved new draft. Suggestions are not activated until saved. Uploading data alone does not create a priority override or grant any rights.
- An INHERIT version resumes platform defaults. Where neither tenant nor platform configuration exists, existing policy arbitration remains in use; the UI explicitly says **Unconfigured**.
- Tenant coverage, activity rights, acceptance, information cutoff and policy pricing semantics remain mandatory. Source rank cannot rescue an incompatible or unavailable mark.
- Existing policy rules still pin an explicit dataset. A pinned dataset excluded by the configured order blocks selection with `SOURCE_PRIORITY_EXCLUDED`; the resolver cannot silently select another source.
- Latest eligible market date is selected according to the pricing rule, then source rank breaks same-date competition before arrival/observation timestamps. This preserves existing freshness/staleness behaviour: a preferred old price does not displace a newer eligible fallback price.
- Both composite and legacy selection use the shared priority boundary. Resolver version is `market-data-resolver-v4`. Legacy selection reduces each market date by source rank before existing date/staleness selection; composite selection applies rank only after convention/calendar/basis eligibility.

## Persistence and API

`md.source_priority_version` and `md.source_priority_entry` retain ordered versions, actor, timestamp, request key and fingerprint. Tenant-null versions are platform defaults. Foreign keys, rank uniqueness and per-scope version/key uniqueness are database enforced. API saves only create versions; database triggers reject updates/deletes. Downgrade refuses to discard retained configuration evidence. There are no priority rows seeded automatically and no grants, prices, trades or results are rewritten by migration 74.

`GET /v1/market-data/sources` returns safe catalogue/configuration metadata. `POST /v1/market-data/source-priorities` requires a stable Idempotency-Key and `expectedVersionId`; advisory locks serialize keys and scope changes. The same payload/key returns the same version, key reuse with different content conflicts, and stale edits return 409 instead of overwriting. INHERIT cannot contain an explicit order; duplicate source IDs and tenant-private platform defaults are rejected.

Versions apply only when known by the request's information cutoff. Frozen pricing evidence contains tenant/platform version IDs, effective scope and dataset order. Retained snapshots and valuation runs are unchanged. Priority configuration is not a licensing or dataset-upload endpoint.

The Next.js BFF derives tenant/actor from the existing signed session. Save retries retain a frozen request and key, disable editor/context controls while unresolved, and allow unchanged retry or configuration reload. Session absence returns non-retryable HTTP 401, not misleading upstream unavailability. Error text and correlation IDs follow the existing safe BFF boundary.

## Verification

- **66 focused isolated PostgreSQL tests passed** across source configuration/ranking, scoped coverage, composite policy resolution/API, legacy resolution, valuation service and evidence permissions. No full suite was run, as requested. Eight existing SQLAlchemy `.tuples()` seed-loader deprecation warnings remain.
- **18 focused frontend tests passed**, including ordering, tenant-owned suggestions, read-only rendering, navigation, existing policy/market-data views, reporting-only permission messaging and missing-session BFF errors.
- Ops-console TypeScript check passed. OpenAPI export check passed. Regenerating TypeScript contracts was byte-identical. The existing `generate:check` command fails its Git cleanliness comparison because the new contracts and prior work are intentionally uncommitted; this is not contract-generation drift.
- Migration 74 applied to the operating local DB; Alembic confirms head74. API/UI started on 8000/3000. Read-only HTTP checks confirm session selection, page rendering and BFF reads return 200, both section labels and the personal Yahoo dataset appear in rendered HTML, and no-session BFF returns 401. No operating priority configuration was saved as a test.
- Browser acceptance remains pending: the supplied browser runtime exited repeatedly during initialisation. HTTP and server-render checks are not claimed as a click-through walkthrough.
- Final review was performed sequentially by the implementer, following the user's no-subagent instruction. It caught purpose-specific scope ambiguity and missing-session error classification, both covered by regression tests.

## Explicit boundaries / next work

Flexible/strict policy defaults were subsequently implemented in [the policy update](flexible-pricing-policies.md), using resolver v5; this source-priority delivery originally used v4. Licensing proof/review workflows, package/grant management screens, generic tenant-series uploads, observation validation and broader purpose-specific rankings are not implemented here. The page reflects current recorded permissions; it does not create or repair missing rights. At the original October 8 activation, Yahoo had **INTERNAL_REPORTING only**. The later [personal valuation permission activation](yahoo-personal-valuation-permissions.md) and [bounded historical EUR/GBP setup](yahoo-eurgbp-valuation-setup-2026-10-09.md) supersede that historical access state for their explicit tenant/dataset/series/date scope. Current eligibility is evaluated from recorded grants on each request; source ranking cannot add missing rights.

Minor follow-up: catalogue/configuration reads currently make per-type/version queries. Batch these if the source/type universe becomes large. A saved preference does not guarantee that the dataset contains compatible prices for every instrument in its type. Independent visual/browser acceptance and broader production load/security review remain necessary before production signoff.

Design: [specification](../superpowers/specs/2026-10-08-market-data-sources-ui.md), [plan](../superpowers/plans/2026-10-08-market-data-sources-ui.md), [execution ledger](market-data-sources-progress.md). Scope foundation: [scoped dataset entitlements](scoped-dataset-entitlements.md).
