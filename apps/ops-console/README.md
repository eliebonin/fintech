# Operations Console

This is the Next.js UI/BFF application boundary. It hosts bounded local-alpha
operations workflows for:

- canonical instrument/listing review;
- external provider, bank, client, and custodian-ID mapping;
- market-data provenance and vintage review;
- trade booking and append-only lifecycle corrections; and
- tenant-scoped Soft-NAV review and approval.

The application may consume packages under `packages/` through their public
interfaces. It must not be imported by another application and must not access
PostgreSQL or tenant credentials directly.

## Current implementation slice

Current route/scope map: [frontend reference](../../docs/platform/frontend/README.md)
and [feature register](../../docs/product/feature-register.md). The original slice
description below is not the full current capability list. Tenant context/profile,
Users/Groups, platform tenant editing, strategies, product tickets/history, data
policies/sources/calendars and economic P&L/review have since been added. The
retired home P&L demo is not supported.

- Next.js App Router with React 19 and MUI 9.
- Server-rendered home and instrument-detail routes, with a small client
  island for search and result selection.
- `/api/instruments/search` and `/api/work-queue` are BFF seams. They call the
  Python reference API server-to-server and return view contracts with source,
  tenant, API-version, and correlation metadata.
- Any explicit local synthetic fallback is route-specific, never an authorization,
  booking or financial-result substitute. Live protected workspace failures must
  remain visible; production must not replace them with fictional success.
- Local verification uses the PostgreSQL container and the existing Python
  schema/fixture loader, but the Next app does not connect to PostgreSQL.

## Local run

The seed command below migrates/writes the configured local DB. Run it only for
explicit setup, not on every app restart. This documentation review did not run
it or restart services. Tests use [isolated databases](../../docs/delivery/README.md#safe-postgresql-verification).

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts/load_demo_scenarios.py
pnpm run dev:reference-api
pnpm run dev:ops-console
```

Open `http://localhost:3000` after both processes are running.
