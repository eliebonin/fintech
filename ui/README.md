# UI / Frontend Workstream

> **Legacy workstream index.** Start from the maintained [frontend documentation index](../docs/platform/frontend/README.md) and [project documentation home](../docs/README.md). This folder remains the detailed record of UI decisions, screen specifications, contracts, and workflows; the pre-reorganisation snapshot is in the [archive](../docs/archive/2026-09-10-pre-reorganisation/README.md).

This folder is the working specification area for the Fortem MVP user
interface. It is intentionally separate from the PostgreSQL schema and
backend implementation folders.

The UI must present the system as a controlled operating platform, not as an
unrestricted database editor. It should make identity, tenant scope,
entitlements, provenance, approvals, and valuation cutoffs visible wherever
they affect an operational decision.

## MVP principles

- Operations users can search, review, propose, and approve canonical records.
- Tenant users see their own overlay, overrides, private records, trades,
  positions, and Soft-NAV evidence only.
- Every external identifier resolves to a Fortem UUID with a visible mapping
  status and source namespace.
- Market-data results always show series, valuation cut, market date,
  information cutoff, provider/dataset, and source-vintage lineage.
- Trades are booked economic events; corrections appear as lifecycle history.
- Marks and Soft-NAV results are reviewable conclusions, not editable raw
  observations.

## Folder map

| Folder/file | Purpose |
|---|---|
| `mvp-scope.md` | MVP users, outcomes, non-goals, and release boundary. |
| `screen-specs/` | Screen-level requirements and component behaviour. |
| `workflows/` | End-to-end operational journeys and state transitions. |
| `data-contracts/` | UI-facing API/query contracts and display models. |
| `decisions/` | Explicit frontend decisions and deferred choices. |

The repository-level layout is recorded in [Decision 0003: modular monorepo foundation](decisions/0003-modular-monorepo.md).

## Current status

This section retains the original slice description. Use the [current route/scope map](../docs/platform/frontend/README.md) and [feature register](../docs/product/feature-register.md) for newer access, product booking, market-data and economic-P&L paths. Local synthetic fallback is route-specific, not universal live-workspace or financial-result behaviour.

The first implementation slice is live under `apps/ops-console`: Next.js App
Router, React 19, and MUI 9. It implements search-to-detail and work-queue
views through BFF routes backed by the Python reference API. Responses expose
tenant, source, API-version, and correlation metadata.

The browser does not connect to PostgreSQL. Local development can explicitly
fall back to fictional fixtures when the API process is stopped; production
fails closed instead.
