# Decision 0002: server-first hybrid rendering

## Decision

The Fortem UI will use a server-first hybrid rendering model:

```text
Browser
  -> authenticated UI server / BFF
      -> Fortem APIs
          -> central canonical and market-data services
          -> tenant overlay services
```

Route-level pages and sensitive initial data are rendered on the server.
Interactive controls are browser components layered onto that server-rendered
page. The browser never connects directly to PostgreSQL and never receives
tenant database credentials or provider secrets.

## Server-rendered responsibilities

- Authenticated tenant context and route authorization.
- Instrument/listing detail and effective definition version.
- External-ID mapping results and approval state.
- Trade detail, parties, and lifecycle history.
- Soft-NAV run review, valuation cuts, input snapshots, and exceptions.
- Initial market-data value, source, dataset/licence, and vintage evidence.
- Permission-aware empty, unauthorized, stale, and missing-data states.

## Browser-rendered responsibilities

- Table sorting, filtering, pagination, and column selection.
- Form drafts, field validation, and unsaved-change warnings.
- Tabs, drawers, dialogs, and expandable evidence panels.
- Interactive charts and client-side visual exploration.
- Refresh/polling or streaming for intraday data when that scope is added.

Browser interactions remain server-authoritative. Mutations call an API/BFF
endpoint with an idempotency key; the server validates tenant scope,
entitlement, lifecycle state, and permissions before writing.

## Data and caching rules

- Never statically generate tenant-specific trades, positions, marks, or NAV
  pages.
- Do not publicly cache tenant responses or responses containing confidential
  identifiers/terms.
- Cache only explicitly approved shared canonical or public data, with cache
  keys that include the relevant version and entitlement context.
- Keep market-data `market_date`, valuation cut, information cutoff, provider,
  dataset, and vintage visible in the view model.
- Do not treat client-side cached values as authoritative after a mutation or
  approval; revalidate from the server.

## Why this fits the platform

The model reduces browser exposure for confidential tenant data and keeps
tenant routing, entitlement checks, and source lineage close to the trusted
server boundary. It still supports the highly interactive tables and review
workflows needed by operations and NAV teams without turning the first MVP into
a real-time trading terminal.

## Chosen for the first implementation slice

- Next.js App Router is the server/BFF host.
- React 19 client components are used only for search input, loading/error
  state, and result selection.
- MUI 9 is the initial enterprise component library.
- The first BFF routes are `/api/instruments/search` and `/api/work-queue`.
  They call the Python reference API server-to-server and preserve an explicit
  synthetic fallback only for local development.

## Deferred technology choices

- Production BFF deployment topology and network policy.
- Python API client generation and retry/time-out policy.
- Client cache/query library.
- Shared component package promotion after a second consumer exists.
- Streaming protocol for future intraday data.
- Separate public/client portal, if required later.
