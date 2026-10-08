# S&P 500 and CAC 40 reference universe

**Owner:** Engineering delivery team  
**Snapshot date:** 2026-10-06  
**Delivery status:** Applied to local operating database and verified  
**Scope:** Scripted security-master seed; no browser onboarding

The curated seed contains 503 S&P 500 equity securities and 40 CAC 40 equity securities, each with a canonical ISIN identity and one constituent exchange listing. It provides a known public universe before market-data onboarding. It does not create trades, observations, index weights, holdings, valuations, settlement entries or accounting records.

## Source reconciliation

S&P membership is reconstructed from primary public sources, not presented as a licensed official weighted index feed. The October 5 [SPY holdings file](https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx) supplies tickers, CUSIPs and SEDOLs; exact SEDOL matches in the October 5 [SPY5 holdings file](https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spy5-gy.xlsx) supply ISINs and share-class names. Cash and a TPG merger contingent-value right are excluded. The remaining 503 securities agree with the [IVV holdings file](https://www.ishares.com/us/products/239726/ishares-core-s-p-500-etf/latest-holdings.csv) after excluding its Hologic residual and Warner Bros. Discovery departure and reconciling ticker punctuation/renaming.

The [October 1 S&P announcement](https://press.spglobal.com/2026-10-01-Vylor-Added-to-the-S-P-500-Twilio-Set-to-Join-S-P-500-Others-to-Join-S-P-MidCap-400-and-S-P-SmallCap-600) confirms October 6 membership changes: Corteva and Warner Bros. Discovery leave; Twilio joins. Vylor, added following the earlier spin-off, is retained. ETF files can contain residual assets or pending corporate actions; they are not imported indiscriminately.

US constituent symbols and primary venues are checked against the October 6 [Nasdaq listed directory](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt) and [other listed directory](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt), using the [official field definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs). Venue MICs are checked against the [ISO MIC register](https://www.iso20022.org/market-identifier-codes). The resulting US listings are 345 XNYS, 157 XNAS and one BATS (Cboe BZX). Exchange operating MICs XNAS/XNYS follow the existing security-master convention. Alphabet, Fox and News Corp share classes remain distinct instruments; Berkshire and Brown-Forman retain their class-specific tickers.

CAC 40 membership and ISINs come from [Euronext composition dated October 6](https://live.euronext.com/en/popout-page/getIndexComposition/FR0003500008-XPAR). Symbols, currencies and constituent venues are checked against [Euronext equities by index](https://live.euronext.com/en/markets/paris/equities-by-index/cac40). All 40 constituent listings quote in EUR: 39 XPAR and one XAMS (ArcelorMittal). Being a CAC constituent does not mean its constituent listing must be Paris. No US ADR or alternative currency listing is substituted.

The maintained JSON manifest records normalized facts, source URLs, observation dates, reconciliation notes and SHA-256 hashes for downloaded evidence. Raw workbooks/directories remain in the local research directory outside Git. ETF prices, portfolio quantities and weights are intentionally absent. Public availability does not establish permission for commercial redistribution or a continuing market-data feed; licensing and data entitlements remain separate onboarding decisions.

Cboe BZX uses `America/New_York` for session interpretation, following [Cboe's published Eastern trading hours](https://www.cboe.com/about/hours); its ISO venue location remains Chicago. Trading timezone is not inferred from headquarters location.

## Database representation and safeguards

- `secm.financial_reference_node`, `instrument` and `listing` hold canonical securities and venue representations. `reference_node_scope` marks them `SHARED_CANONICAL`, with no tenant owner. Existing tenant-specific records are not promoted or overwritten.
- `financial_reference_identifier` retains ISIN plus sourced CUSIP/SEDOL and venue-contextual tickers. ISIN checksum, complete constituent counts, duplicate identities, currency and verified venue checks run before DB writes. Identity is not inferred from a company name or ticker alone.
- `instrument_definition_version` and `listing_definition_version` receive approved version-one definitions, linked to the retained normalized `ing.source_payload` and recorded active operator. Quote factor and unit multiplier are one for these ordinary equity shares.
- Two non-tradable index reference nodes own `INDEX_MEMBERSHIP` snapshots dated October 6. Snapshot items reference canonical instruments; weights, quantities and cash components remain null. This is membership evidence, not a portfolio or an index-calculation model.
- An advisory transaction lock serializes the bundle. The entire seed commits or rolls back together. Reruns verify existing scopes, identifiers, approved definitions, listing economics and snapshot membership. Conflicts fail closed and require reviewed resolution; the seed never silently repairs user data.

Definition effective dates mean verified availability in this seed, not original issue/listing dates. Historical booking before October 6 requires independently sourced and approved earlier definitions. Unknown issuer entities, par values, historical calendars and other unsupported facts are not fabricated. Equity base currency follows the selected constituent quotation, not the issuer's financial-reporting currency. The manifest has a targeted Git `eol=lf` attribute so platform line-ending conversion cannot change its retained byte checksum.

## Operator workflow

From the repository root:

```powershell
.venv\Scripts\python.exe scripts\seed_index_universe.py
.venv\Scripts\python.exe scripts\seed_index_universe.py --apply
```

The first command previews with transaction rollback. The second commits atomically. Both are restricted to local `fortem_secm` on port 54329; an active recorded actor can be supplied with `--actor UUID`. This privileged offline operator workflow is not exposed as a tenant API or a self-service shared-data permission. Defaults use the existing demo operator for the local alpha.

The dataset is an opt-in maintained seed bundle, not an automatic expansion of every synthetic test/demo fixture. A newly built operating DB must first run the standard migrations/catalogue setup, then this command. Run isolated tests with `scripts/run_isolated_python_tests.py`; do not run DB integration tests against operating data.

## Verification and activation

The dated universe was committed atomically to local operating `fortem_secm` on October 6. Activation created **543 canonical equity instruments and 543 listings**, with 503 S&P 500 securities and 40 CAC 40 securities. All 1,086 instrument/listing scopes are active and shared, with no tenant owner.

Completed verification:

- Lightweight manifest and CLI-target checks: eight passed. Validation checks cover constituent counts, ISIN checksums, duplicate identities, known venues and currencies; the CLI refuses a different DB or non-local application environment before connecting.
- Latest focused isolated PostgreSQL run: **15 passed in 166.00 seconds**. It covers creation of 543 instruments/listings, no-op reuse, shared search visibility in both demo tenants, approval/source provenance, no trade/lifecycle/market-observation/cash-balance writes, multiplier conflicts, retired instrument projections, inactive index owners, future-effective identifiers, tenant-private scope, altered snapshot cash components and changed source-payload hashes. Regression failures were observed before adding the missing lifecycle/date/session-timezone guards.
- Complete Python suite: **949 passed, 492 warnings in 1,832.80 seconds**, exit code zero, using `scripts/run_isolated_python_tests.py -q --durations=10`. Its disposable database was removed automatically after completion. Warnings include SQLAlchemy `Result.tuples()` deprecations, deprecated Starlette 422 naming and Pydantic field-alias warnings; they remain maintenance work, not a warning-free signoff.
- Compilation of the seed module and operator CLI passed. All six retained downloaded source-file hashes matched the manifest. The normalized manifest SHA-256 is `6218b4130240aa494e19db07cfb09a55d6e49ad90fd854faac7f346e450e7e87`.
- Final rollback-only operating preview confirmed that all **543 listings were booking-ready on October 6**, with zero universe equities persisted after rollback.
- Post-commit read-only checks confirmed 543 approved instrument definitions and 543 approved listing definitions, each linked to the retained source payload and active approving operator. Membership snapshots contain exactly 503 and 40 canonical identities, in manifest order, with null weights, quantities and cash components.
- Every persisted listing matched its manifest symbol, currency and venue. Venue counts are **345 XNYS, 157 XNAS, one BATS, 39 XPAR and one XAMS**; quote factors and unit multipliers are all one. All **543 persisted listings passed cash-booking readiness** on October 6.
- Six repository search checks across both demo tenants passed, covering canonical ISIN, listing symbol `BRK.B` and the ArcelorMittal name. These checks use the application's catalogue implementation, not just raw table counts.
- Trades, lifecycle events, market observations and cash balances stayed respectively **9, 9, 12,469 and 0** throughout the preview, activation and final verification.
- The post-activation CLI preview created **zero** instruments/listings, reused **543** of each, and retained the same source-payload and snapshot identities. The rerun rolled back.

Activation provenance:

- Source payload: `01a11297-7238-7c7f-9c13-651daee6a1e8`.
- S&P 500 membership snapshot: `01a11297-b429-7ba6-bc2b-771cd9b5e2aa`.
- CAC 40 membership snapshot: `01a11297-b45e-795b-98a1-8fa9c1738778`.

## Local environment alignment

Docker Desktop and PostgreSQL were stopped at resumption. Only the existing `fortem-security-master-postgres` container was started, reusing `techv2_fortem_security_master_postgres`; no new volume was created and unrelated containers remained stopped.

The first post-activation catalogue search exposed pre-existing schema drift: operating revision `20261002_58` lacked `secm.swap_definition_version`, which the current generic search references. Reviewed, already-tested revisions `20261002_59`, `20261002_60` and `20261005_61` were applied, bringing the operating DB to head. They add the versioned swap table and adjust constraints; they do not backfill legacy swaps or rewrite existing trades/instruments. The same catalogue search checks then passed. No application-code workaround was added.

The previously used UI on port 3007 uses a separate isolated preview DB and was not seeded. This delivery verifies the operating DB and application repository/readiness functions, not a running browser UI. No operating trades were booked, no browser onboarding was performed, and no changes were committed or pushed to GitHub.

Three older inactive disposable-test databases remain untouched because their ownership was not sufficiently established: `fortem_isolated_tests_daf2424fe3fe4c4e90080b795b1f6fb4`, `fortem_isolated_tests_0cda8bfe548847709bf1b7756d6ca8f3`, and `fortem_isolated_tests_e896667a8c3142b4afcf79c7e2ca9c28`. Verify ownership before any later cleanup; never remove test databases by wildcard. The completed full-suite database from this delivery was verified absent.

## Remaining scope

Only one verified constituent listing per share class is included. All global cross-listings, automatic index refresh, corporate-action processing, MD provider mapping and observations remain outside this delivery. The dated bundle must never be relabelled as continuously current without a new source reconciliation.
