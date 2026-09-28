# Operations Console

This is the first independently deployable UI application boundary. It will
host the internal operations workflows for:

- canonical instrument/listing review;
- external provider, bank, client, and custodian-ID mapping;
- market-data provenance and vintage review;
- trade booking and append-only lifecycle corrections; and
- tenant-scoped Soft-NAV review and approval.

The application may consume packages under `packages/` through their public
interfaces. It must not be imported by another application and must not access
PostgreSQL or tenant credentials directly.

## Current implementation slice

- Next.js App Router with React 19 and MUI 9.
- Server-rendered home and instrument-detail routes, with a small client
  island for search and result selection.
- `/api/instruments/search` and `/api/work-queue` are BFF seams. They call the
  Python reference API server-to-server and return view contracts with source,
  tenant, API-version, and correlation metadata.
- If the Python API is unavailable, local development may show explicit
  `synthetic-fixture-fallback` data. Production fails closed with HTTP 503.
- Local verification uses the PostgreSQL container and the existing Python
  schema/fixture loader, but the Next app does not connect to PostgreSQL.

## Local run

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts/load_demo_scenarios.py
pnpm run dev:reference-api
pnpm run dev:ops-console
```

Open `http://localhost:3000` after both processes are running.
