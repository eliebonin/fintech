# Lightweight instrument catalogue

Delivered locally on 2026-10-08 following the user's explicit request to optimise catalogue reads. Changes remain uncommitted on `codex/enriched-trade-booking`.

## Behaviour and boundary

The instrument table now reads `GET /v1/instruments/catalogue` through its own session-scoped `GET /api/instruments/catalogue` BFF. Its generated response contains only instrument ID, canonical name, type, asset class, status, base currency and listing count. Page rows use current approved/effective instrument definitions; listing counts are fetched in one batch against the bounded page IDs, using current approved/effective listing definitions and tenant-visible listing scopes. Total, filters, paging, stable name/ID ordering and existing search predicates are retained. The asset-class filter uses the approved definition's asset class rather than a mutable instrument projection.

The reader lives in `apps/reference_api/instrument_catalogue.py` and issues three SQL queries for nonempty pages: total, rows and grouped listing counts (two queries for empty pages). It never calls the full instrument hydrator or reads market observations, provider rights or detail terms. Prices and evidence are absent from the compact payload, so dataset-display licensing cannot be bypassed through it. Full detail routes keep their existing licensing checks. The full `/v1/instruments/search` and `/api/instruments/search` contracts remain available for listing/ETP creation selectors and booking consumers.

The table renders `listingCount`; it no longer receives complete listing arrays. Initial SSR and debounced client filtering both use the compact reader. Existing abort/stale-response handling, source labels, recoverable errors, typed tenant context and permission controls remain. Explicit development fixtures are projected into the same compact shape. Full-search and compact loaders share the same fail-closed fixture eligibility rule. No persistent tenant cache or forced detail prefetch was added.

## Measured performance

Same operating tenant, first 25 active rows, read-only transactions; total stayed 802 in both projections:

| Measure | Full search | Compact catalogue |
| --- | --- | --- |
| Repository SQL queries | 502 | 3 |
| Three repository runs | 1,357 / 1,371 / 1,418 ms | 23 / 28 / 18 ms |
| JSON body size, same metadata | 94,253 bytes | 5,138 bytes |

After activation, direct local HTTP API checks took 30–60 ms for 25/100 rows across both tenants. Signed-session BFF checks took 36–110 ms. Full catalogue page responses: first demo-tenant request 695 ms; warm demo request 167 ms; second-tenant requests 188/236 ms. All timings used 127.0.0.1 to avoid conflating the Python HTTP client's localhost address fallback with application work. These are HTTP completion timings, not browser paint metrics. The existing browser tool's Windows initialization remains unavailable, so visual/hydration acceptance and an independent reviewer are not claimed.

## Verification

- New backend regressions were observed failing before implementation; initial requests fell through to the UUID detail route until the new static route was registered ahead of it. New frontend regressions were observed failing against the full-search URL and listing-array rendering.
- **52 focused Python tests passed** via `scripts/run_isolated_python_tests.py`, exclusively using a disposable database: compact shapes/counts, constant query budget as page sizes grow, filters/paging/empty totals, private instrument/listing scopes, inactive membership, existing detail/full-search contracts, display rights, ingestion/correction semantics and prior observation-index round trips.
- **673 frontend tests / 143 files passed**. Console TypeScript and the final production build passed. Contract package: 3 tests and TypeScript passed. OpenAPI export check passed; repeated TypeScript generation produced an identical SHA256. Git whitespace check passed.
- Live checks passed for both tenants: compact API at 25/100 rows, active-session BFF, catalogue page, full detail API/page, legacy full-search BFF, empty page totals and missing-session rejection.

## Local activation and data

API and built console were restarted on 8000/3000. No database migration, fixture load or financial mutation was performed for this optimisation. Read-only verification observed 1,358,477 observations and 10 trades/10 lifecycle events; earlier delivery records had 9 trades/events, so unchanged operating counts across the whole conversation must not be inferred while the user is using the app. All verification requests here were GETs except session selection; the transaction profile explicitly used READ ONLY and rolled back. Original uncommitted `next-env.d.ts` bytes were restored after build regeneration. The process-only console signing key rotated on restart, so a browser may require tenant selection again.

## References

- [Frontend loading and navigation recovery](frontend-loading-recovery-2026-10-08.md)
- [FastAPI response-model validation, filtering and generated schemas](https://fastapi.tiangolo.com/tutorial/response-model/)


## 9 October: external listing search correlation fix

AMZN searches appeared unchanged because the nested listing-to-external-mapping EXISTS included its own financial_reference_node table. A matching listing mapping therefore admitted unrelated instruments. The inner query now explicitly correlates the mapping and outer instrument node. Catalogue and full search reuse the corrected predicate.

A regression first returned 25 unrelated results for one unique listing code; after correction it returns only the mapped instrument on both endpoints. Forty isolated catalogue and reference-authority tests passed. Backend restarted; live AMZN returned exactly Amazon.com Inc. (total 1), and a nonexistent query returned total 0. No operating data was modified. Browser interaction acceptance remains unverified.
