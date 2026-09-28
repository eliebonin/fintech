# MVP Market Data and Portfolio Views Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with tests before implementation and verify the integrated Docker workflow.

**Goal:** Populate a deterministic two-year mock investment universe and expose market-data provenance and date-selectable instrument-level portfolio P&L in the MVP UI.

**Architecture:** Extend the existing idempotent SQLAlchemy demo loader rather than adding production-only tables. Add read-only FastAPI repository queries over `md`, `secm`, and `trd`; derive MVP holdings and P&L from booked trades plus selected observations, with a transparent price/FX split and no persisted formal attribution model. Add server-rendered Next.js pages backed by BFF routes.

**Tech Stack:** PostgreSQL 18, SQLAlchemy Core, Alembic, FastAPI/Pydantic, Next.js/React/MUI, Vitest.

**Spec:** Approved chat design on 2026-09-01.

## Global Constraints

- Use fictional/synthetic values and label them as mock data.
- Preserve existing UUIDv7 identities and idempotent loaders.
- Keep provider, dataset, licence, source-vintage, and observation lineage visible.
- Do not introduce formal persisted P&L attribution methodology in this slice.
- Do not add a new market-data table for daily observations.

---

### Task 1: Mock universe and two-year observations

**Files:**
- Modify: `security_master_schema/demo_data.py`
- Modify: `data/mockup/README.md`
- Create: `security_master_schema/mvp_demo_data.py`
- Create: `data/mockup/mvp-market-data-portfolios.json`
- Test: `tests/test_mvp_market_data_fixture.py`

**Interfaces:**
- Produces deterministic identifiers and rows for providers, datasets, licences, US/EU equity listings, bonds, futures/family, FX forwards, two strategies, trades, daily observations, and UK/US FX-cut series.

- [x] Write tests asserting both portfolios, at least two providers, at least one US and one European listing, a future family/expiry, an FX forward, and at least 500 distinct market dates per daily series.
- [x] Run the fixture test red before implementation.
- [x] Add deterministic generation using a fixed seed and business-day range; retain all observation provenance IDs.
- [x] Add idempotent portfolio/trade inserts and series observations without changing existing demo IDs.
- [x] Run fixture tests and reload the demo twice to prove no duplicate rows.

### Task 2: Market-data series API

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Test: `tests/test_mvp_market_data_api.py`

**Interfaces:**
- `GET /v1/market-data/series?fromDate=&toDate=&referenceNodeId=&seriesType=` returns series metadata and observations, including `marketDataSeriesId`, `dataProviderId`, `datasetId`, `acquisitionLicenceId`, dates, values, currency, and cut.

- [x] Write API tests for date filtering and provenance fields.
- [x] Run them red against the current API.
- [x] Add Pydantic response contracts and a repository query joining provider/dataset/licence/vintage metadata.
- [x] Add route-level tenant membership enforcement and bounded result limits.
- [x] Run API tests and existing API tests.

### Task 3: Portfolio P&L API

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Test: `tests/test_portfolio_pnl_api.py`

**Interfaces:**
- `GET /v1/portfolios/{portfolio_code}/pnl?asOfDate=YYYY-MM-DD` returns portfolio currency, selected valuation date/cut, and one line per instrument/listing with quantity, opening/closing prices, opening/closing FX, local price P&L, FX P&L, and total P&L.

- [x] Write tests proving date selection changes the selected observations and that quote factor/unit multiplier are applied.
- [x] Run them red.
- [x] Derive holdings from active booked trades through the requested date and resolve latest eligible observations on or before the selected date.
- [x] Use the portfolio base currency and the existing FX-cut series; return explicit missing-data errors rather than silently guessing.
- [x] Run API and repository tests.

### Task 4: BFF and market-data page

**Files:**
- Create: `apps/ops-console/src/app/market-data/page.tsx`
- Create: `apps/ops-console/src/app/api/market-data/series/route.ts`
- Create/modify: `apps/ops-console/src/lib/market-data-series.ts`
- Test: `apps/ops-console/src/lib/market-data-series.test.ts`

- [x] Add pure mapping/formatting tests first.
- [x] Add server-rendered page with date controls, sparkline/table, and provider/dataset/licence metadata.
- [x] Render explicit error states and synthetic-data labels.
- [x] Run frontend tests, typecheck, and build.

### Task 5: Portfolio P&L pages

**Files:**
- Create: `apps/ops-console/src/app/pnl/[portfolio]/page.tsx`
- Create: `apps/ops-console/src/app/api/portfolios/[portfolio]/pnl/route.ts`
- Create/modify: `apps/ops-console/src/lib/portfolio-pnl.ts`
- Test: `apps/ops-console/src/lib/portfolio-pnl.test.ts`

- [x] Add pure formatting/summary tests first.
- [x] Add reusable server-rendered portfolio page supporting `us` and `uk` route values and `asOfDate` query parameter.
- [x] Show headline total and instrument-level table with local price, FX, and total components; show selected cut and observation provenance IDs.
- [x] Add navigation from the existing console and date-aware rendering.
- [x] Run frontend tests, typecheck, and build.

### Task 6: End-to-end verification

**Files:**
- Modify: `data/mockup/README.md`
- Modify: `ui/screen-specs/README.md`

- [x] Run `alembic upgrade head` as part of the existing loader/test workflow against the Docker database.
- [x] Load the mock dataset repeatedly and check idempotent fixture assertions.
- [x] Exercise both API endpoints for two dates and both portfolios.
- [x] Check the live UI routes return 200 and contain provenance, portfolio, cut, and P&L content.
- [x] Run the complete Python and frontend test suites.
