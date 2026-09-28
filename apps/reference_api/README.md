# Reference Data API

This service is the server-side boundary for canonical reference-data reads
and controlled reference-data workflow mutations. It owns PostgreSQL access;
the browser and Next.js client components never receive database credentials.

## Local run

1. Start PostgreSQL and load the deterministic schema/fixtures:

   ```powershell
   docker compose up -d
   .\.venv\Scripts\python.exe scripts/load_demo_scenarios.py
   ```

2. Start the API:

   ```powershell
   pnpm run dev:reference-api
   ```

The interactive OpenAPI document is available at `http://127.0.0.1:8000/docs`.
Every non-health request requires `X-Tenant-Id` and an active
`X-User-Account-Id` membership in that tenant. These headers are supplied by
the BFF from the authenticated session, not chosen by a browser query
parameter. Direct header trust is a local boundary; production deployment
must validate Auth0 claims and derive both values server-side.

## Implemented endpoints

- `GET /health`
- `GET /v1/instruments/search?q=&limit=&offset=`
- `GET /v1/instruments/{instrument_id}`
- `GET /v1/reference-nodes/search?q=&node_type=&instrument_type=&asset_class=&reference_level=&limit=&offset=`
- `POST /v1/equity-proposals` (economic instrument creation; listings may be empty)
- `POST /v1/listing-proposals` (listing creation against an approved equity or digital-asset instrument; the legacy `/v1/equity-listing-proposals` alias remains supported)
- `POST /v1/bond-proposals` (sparse fixed/zero/floating bond proposal; provider enrichment may be required before approval)
- `POST /v1/bond-proposals/{proposal_id}/decision` (manual bond approval or rejection)
- `POST /v1/crypto-asset-proposals` (canonical DIGITAL_ASSET economic instrument and currency-role proposal)
- `GET /v1/crypto-asset-proposals/{proposal_id}` (tenant-scoped proposal review payload)
- `POST /v1/crypto-asset-proposals/{proposal_id}/decision` (manual cryptoasset approval or rejection)
- `GET /v1/day-count-conventions` (active governed accrual-convention catalogue for bond and rate-term forms)
- `GET /v1/currencies?groups=REGULAR,CRYPTO` (active currency roles grouped for selectors; omit `groups` for regular currencies, or request `CRYPTO` explicitly)
- `GET /v1/work-queue`
- `POST /v1/reference-mapping-proposals`
- `POST /v1/reference-mapping-proposals/{proposal_id}/decision` 

The structured-product proposal endpoint also accepts the first composed-option
templates: `VANILLA_SPREAD_KIP`, `VANILLA_KIP`, and `DIGITAL_KIP`, plus the
focused `RANGE_ACCRUAL` and `SUPERTRACKER` slices. These use the existing
parent/component graph. Their rows distinguish an unconditional
`OPTION_PAYOFF` component from a `CAPITAL_PROTECTION` KIP barrier; KIP rows may
carry `observationStyle = CONTINUOUS` or `FINAL_ONLY`. Range accrual stores its
observation frequency, accrual denominator, non-business-day rule, bounds, and
annual rate in `secm.structured_product_range_accrual_terms`; supertracker
stores participation/cap terms in `secm.structured_product_supertracker_terms`.

When KIP is enabled, the request must contain exactly one fresh
`CAPITAL_PROTECTION` PUT component for each underlying. Best-/worst-of groups
retain those child rows but persist one parent-level action with
`payout_multiplicity = ONCE_PER_PARENT`; single/explicit component outcomes
use `PER_COMPONENT`, and `PER_UNDERLYING` is reserved for a future governed
`EACH_UNDERLYING` shape. The API derives this value from the group scope and
action rather than accepting a second conflicting UI value.

Mapping proposals and decisions use the existing append-only reference-data
proposal/approval tables. Approval creates a verified external mapping as a
new row and never overwrites a prior mapping version.

The currency catalogue is caller-configurable rather than instrument-type
hard-coded. `REGULAR` contains `FIAT` rows; `CRYPTO` contains `CRYPTOASSET` and
`STABLECOIN` rows. The response `data` is an ordered list of labelled groups,
each with an `items` array. A new approved cryptoasset creates its currency
role in `secm.currency`, so it appears in the next `CRYPTO` request without a
code or seed change. The Next.js BFF forwards the same `groups` query and the
UI toggle only changes that request.

Reference-node searches accept the optional `reference_level` selector:
`ANY` (the default), `ECONOMIC` (exclude venue listings), or `LISTING` (only
venue representations). The filter is enforced in the API, not just in the
browser. When a listing is returned, the view also carries its parent economic
node, venue MIC/name, trading symbol, and trading currency so Operations can
distinguish a listing from the instrument it represents and avoid selecting an
ambiguous venue record. Categories without a meaningful venue-listing concept
remain eligible for `ANY`/`ECONOMIC`; the structured-product UI disables the
listing choice for those categories.
