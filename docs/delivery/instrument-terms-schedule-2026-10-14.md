# Read-only instrument Terms & Schedule

Reviewed and delivered locally: 14 October 2026.

## Access and scope

Open Instruments, search an ISIN, open its detail page, then select **Terms & Schedule**.
Route: `/instruments/{instrumentId}/terms-schedule`.
The button is available for structured products and swaps independently of creation/configuration authority.

The authenticated GET `/v1/instruments/{instrument_id}/terms-schedule` reads current approved definitions and current ACTIVE/VALIDATED structured terms. It preserves decimal strings and explicit stored dates, conditions, barrier inclusivity, actions, payout bases, option components, initial fixings and coupon periods. It does not regenerate a schedule or use execution-date booking readiness to decide whether terms can be inspected.

Linked notes display separate note and preference-share layers, including note early-redemption dates, share call periods, final branches and distinct valuation/maturity dates. A swap displays its own approved economics, recorded reset/payment schedules and its performance-reference structured schedule. The swap → linked note → share chain is supported. Every referenced economic node must be visible to the selected tenant; a hidden required dependency fails closed with 404. `REFERENCE_READ` and active membership are required; a membership label alone is not a permission grant.

Generic swaps store frequencies/source descriptions rather than generated reset/payment dates. The page explicitly states when those dates are unrecorded. Index/rate references have no instrument schedule to expand. Unbounded terminal branch endpoints are displayed as unbounded, not missing.

This is current contractual reference inspection, not an as-of trade snapshot, triggered-event assessment, cashflow ledger, lifecycle processing, pricing or regulatory reporting engine. It does not create instruments or trades, approve requests or change contractual data.

## Implementation and verification

- Backend: `apps/reference_api/instrument_terms_schedule.py`, additive route in `main.py`.
- Frontend: `components/instrument-terms-schedule.tsx`, instrument detail button, server page, server API client.
- OpenAPI and generated TypeScript refreshed independently in the isolated and operating checkouts.
- Disposable database verification: 9 tests passed across the new API/read projection, all-wrapper seeds and product readiness. Cases include Phoenix coupon coverage/decimal preservation, hidden share dependency, both direct and linked autocall swap references, existing scheduled swaps, read permission grants and inactive-member denial. One pytest cache-write warning was environmental; no financial test failed.
- Full frontend suite with two workers: 168 files / 776 tests passed before the final label refinement; final refined schedule and existing swap detail tests passed (4 tests), with TypeScript checking passing in both checkouts.
- Initial unlimited-worker suite timed out; the bounded-concurrency rerun passed. `contract:generate:check` uses Git cleanliness and reports existing uncommitted generated-contract differences; runtime OpenAPI export checks pass. No clean Git baseline is claimed.
- Running API readback: all six PDF-derived parent notes returned 200; two Phoenix notes returned 30 events each, and four linked notes returned their distinct share layers with 4/5 call periods.
- Browser: existing Platform Demo read-only user inspected BNP XS3487050836, including the two date layers, underlying fixings, trigger/payment grid and final redemption branches. Local context switching works on the app's `localhost:3000` origin; `127.0.0.1:3000` was rejected by the existing same-origin context guard.
- Scoped additive files were applied to the operating app checkout under file guards/backups; its existing API startup command was refreshed to activate the route. No schema migration or financial DB mutation was needed. No commits or merge performed.

Swap chain behavior was verified on disposable approved instruments; no synthetic swap was added to the operating database for this feature.
