# FX-forward booking alpha quality review

Date: 2026-10-01, Europe/London. Status: **engineering acceptance complete for deliverable FX-forward booking alpha**. Not production-release, financial valuation, settlement-accounting or legal confirmation sign-off.

## Final verification

- Full Python suite: **400 passed, zero failures, zero skips**, 467.56 seconds. Disposable PostgreSQL database migrated to head and seeded before collection. Includes migrations, onboarding, canonical reads, mapping, schema hardening, cash/FX trading, governed properties, history, permissions and P&L boundaries.
- Full frontend suite: **261 passed in 70 files**, 12.00 seconds, with `--maxWorkers=2 --testTimeout=15000`.
- TypeScript type checking, OpenAPI export check and fresh production Next build: passed.
- Prior focused trading regression: 108 passed, plus an active tenant VIEWER test returning 403 with no new trade.
- Generated TypeScript contracts were previously regenerated with identical current-working-tree SHA256. The Git-HEAD generation check remains nonzero for intentionally uncommitted changes; no clean Git/CI claim is made.

Final evidence: `.superpowers/sdd/2026-10-01-deliverable-fx-forward-booking/signoff-{full,frontend,typecheck,contract,build}.log`. Python reports 471 warnings, including existing deprecation warnings; they are not test failures. Bounded frontend concurrency does not establish maximum-worker stress acceptance.

## Browser acceptance

The previous browser blocker was resolved by starting a fresh isolated app on ports 3001/8001. Browser controls exercised the real frontend/BFF/API against synthetic database `fortem_fx_signoff_87ef934b18574808a6b655199926c7b4`, not the operator's app/database.

1. Selected the demo tenant and searched an approved EUR/USD economic contract without a listing.
2. BUY 1,000,000 EUR at 1.10: review and saved detail show receipt of 1,000,000 EUR and payment of 1,100,000 USD. Rate and 2026-12-15 settlement are inherited.
3. Governed counterparty HSBC Demo plc, governed property HEDGE, decimal property **0** and FX acceptance tag survive review, Back to edit, second review and saved detail.
4. SELL 250,000.123456 EUR: review and saved detail show receipt of 275,000.1358016 USD and payment of 250,000.123456 EUR. History retains precise rate, positive base amount, side and OTC labels.
5. History shows both records newest first. BUY trade ID: `d3270afe-1b89-445e-af0f-73729f21e1ff`; SELL: `c0e8e067-7249-461d-ab0a-a9405aceae71`.
6. Switched to the second tenant and opened the BUY URL: NOT FOUND, without first-tenant trade details.
7. An approved synthetic NDF search result shows the unsupported-settlement explanation and has no Select contract control.
8. Added synthetic FX to the UK cash portfolio. `/pnl/uk?asOfDate=2026-10-01` displays VALUATION UNSUPPORTED, an FX explanation and no partial P&L total. This is the existing demo/local-mock P&L surface, not acceptance of a tenant-aware valuation module.
9. Cash smoke check: default Book trade, HSBC listing search/selection, locked GBP/XLON context and Thursday-to-Monday T+2 weekday default all work.

Screenshots: `fx-signoff-buy.jpg` and `fx-signoff-valuation.jpg` in the user's Tech V2 workspace. The final inspected browser warning/error log was empty. These checks are not exhaustive accessibility/responsive certification.

`scripts/prepare_fx_signoff_fixture.py` prepares a separate migrated synthetic fixture. The reusable synthetic-only browser helper's execution-field locators now use the accessible roles verified in the walkthrough. Acceptance was driven through browser controls, not claimed as an unattended execution of the helper.

## Defects resolved for sign-off

The preceding whole-suite run had 381 passes and 13 failures. These failures are now resolved:

- The isolated runner lacked initial demo state. Seeding before collection removes actor/tenant/test-order dependence.
- Demo instrument/listing projections lacked approved definition versions required by canonical reads. The loader bootstraps only its explicit synthetic IDs, skips records with any existing version, and uses stable version IDs. Missing legacy fixture dates use the documented synthetic scenario date, 2026-08-28. No arbitrary application record is approved and existing versions are not rewritten.
- Bond model fields `floating_reference_index` and `floating_spread` lacked a migration. Revision **20261001_54**, following 53, adds nullable columns matching model types/comments; downgrade removes them. The full suite exercises migration boundaries.
- One search assertion expected Ethereum; the governed economic demo assets are Bitcoin and USD Coin, while Ethereum is a network/deployment context. The assertion now matches the fixture without altering search behavior.

New tests cover demo-version presence/idempotence and bond schema alignment. Previously failing onboarding, reference, mapping and hardening modules pass in the final suite.

## Review and boundaries

Earlier independent review identified an omitted approved-definition gate. Authoritative submission now checks APPROVED/current/effective/type/base consistency and active/tradable/type/currency status, and locks versions/terms. Approved-plus-current-draft coexistence is tested and returns one approved booking subject. Search paging and exact-decimal SELL display were also corrected.

API/component tests cover simultaneous same-key submission, frozen uncertain retries, changed payload conflicts, stale fingerprints, permission denial, annotation rollback and cancelled/future FX filtering. Unsupported FX blocks cash scalar P&L rather than silently contributing an incorrect total.

Valuation methodology, discount curves, daily MTM ingestion, NDF, swaps/options, corrections/early termination and accounting settlement postings remain outside this booking alpha. UI density refinement remains a later walkthrough topic.

**Deployment requires migration 20261001_54 before starting updated code.** No live migration, production restart, commit, merge or push was performed. Pre-existing dirty changes were preserved. Acceptance concerns this inspected working tree, not a deployed release.
