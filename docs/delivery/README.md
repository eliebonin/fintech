# Delivery records

23 October: [external CSV tooling isolation](csv-tooling-isolation-20261023.md) —
source-specific scripts/tests are optional tooling, not product packages or
capability delivery. Existing operating data and evidence are unchanged.

23 October: [optional daily bond accruals](optional-bond-accruals-20261023.md) —
disclosed partial coverage by default, explicit strict coverage and publication
protection against newly supplied interest. Supersedes the missing-accrual blocker
in the earlier imported-data preflight below.

23 October: [imported-data personal valuation eligibility](reconciliation-valuation-eligibility-20261023.md),
separate FCAGF source-date policy, scoped rights evidence and retained forward
quotation-label normalization; price/FX checks pass, daily accrual remains a blocker.

23 October: [supplied listed-option premium P&L](option-premium-pnl-20261023.md),
signed contracts and frozen premium multiplier once, canonical premium evidence,
older booking compatibility and retained staging; no model price or expiry booking.

23 October: [supplied whole-swap mark P&L](swap-supplied-mark-pnl-20261023.md),
signed unit/nominal mark-and-FX changes, immutable older-booking compatibility,
explicit quote dimensions and dated RESET treatment; no swap pricer or option P&L.

23 October: [native AMC onboarding](amc-onboarding-20261023.md), certificate
creation/approval, shared funded booking and bounded unit-price daily processing.

**Status:** Maintained evidence index  
**Content type:** Delivery index  
**Owner:** Engineering delivery  
**Last reviewed:** 2026-10-13

For desired-versus-current scope start with the [feature register](../product/feature-register.md), not a chronological plan. Delivery documents record dated implementation, tests and activation; later work may supersede an earlier scope/exclusion without rewriting its evidence.

## Retrieval

- [Complete delivery-record catalogue](catalogue.md): stable links to individual records.
- [Specifications](specifications/README.md): design intent and historical constraints.
- [Implementation plans](implementation-plans/README.md): intended execution, not completion proof.
- [Quality reviews](quality-reviews/README.md): dated findings and verification limits.
- [Documentation review / reconciliation](quality-reviews/2026-10-12-documentation-reconciliation.md).
- [Merge/remediation verification](tenant-access-administration-progress.md#completed-remediation-verification).

## Current capability evidence by domain

October 19: [strategy register cleanup](strategy-register-cleanup-20261019.md),
two unused cutoff demos archived via the existing API; six active strategies and
all historical records retained.

October 19: [Yahoo missing-data refresh](yahoo-refresh-20261019.md), acquisition
and readback evidence for existing equity prices, corporate actions and GBP FX;
source completeness is distinct from RAW normalization and financial sign-off.

October 17: [contextual workflow help](page-contextual-help-20261017.md), consistent
optional guides for complex screens; purpose, steps, terms and workflow impact
without a modal, form reset, authority change or hidden essential warnings.

October 17: [frontend style/density review](quality-reviews/2026-10-17-frontend-visual-consistency.md),
shared native/MUI presentation, policy task tabs, contract-form outline and skip
navigation. Bounded browser/visual verification; F49 remains partial acceptance.

October 15: [position monetary measures](position-monetary-measures-20261015.md), separate strategy preview with exact cash-security/bond/native-index-swap measures and governed evidence. No weights or P&L/publication expansion; remaining live swap policy/FX gaps are explicit.

October 15: [unit-based SPX/UKX mock swaps](mock-unit-swaps-20261015.md), normal approved creation/booking in Strat Testing and 1,007 labelled synthetic EoD marks. Unit and funding-reference nominal are distinct; swap valuation remains unsupported.

October 15: [strategy workspace](strategy-workspace-20261015.md), separate register/creation, dated quantity-only holdings and movement drill-down, direct/indirect calendar visibility. No tax/FIFO, pricing or financial valuation added.

October 15: [mock valuation cycle](mock-valuation-cycle-20261015.md), connected API/database coupon-to-maturity, amendment/publication and correction/successor checks, plus focused FX/cash regressions. One intermittent maturity-rebooking rejection remains recorded; browser/external reconciliation are not claimed.

October 15: [coupon schedules and actual payment evidence](bond-coupons-20261015.md), separate from earned interest and principal redemption; migration 94/API active with approval, browser acceptance pending.

October 14: [controlled self-publication](valuation-self-publication-20261014.md),
migration 87 applied, tenant policy/grants remain default off; final-publication
exception only, not amendment or financial-validation bypass.

October 13 follow-up: [reviewed share-ratio position replay](share-ratio-position-replay-20261013.md), migration 86 and live Air Liquide 100 → 110 staged acceptance; complex entitlements/actions remain excluded.

Valuation UI: [Input form / Results / History tabs](valuation-review-workspace-20261013.md#three-tab-follow-up--13-october-2026), source-backed presentation choices and bounded frontend/browser verification; backend review authority unchanged.

October 14: [strategy/date Results and operational History reports](valuation-results-history-report-20261014.md), server-side filters/counts, read-aware strategies and explicit calculation/publication states; no new valuation economics.

| Domain | Current reference | Principal delivery evidence |
| --- | --- | --- |
| Access/strategies | [Capabilities](../product/features/access-and-strategies.md) | [Tenant administration](tenant-access-administration.md), [strategies](tenant-workspace-strategy-alpha.md) |
| Access transparency | [F02/F04](../product/features/access-and-strategies.md) | [Effective-access explanations and evidence isolation](effective-access-transparency.md) |
| Access authority | [F02](../product/features/access-and-strategies.md#f02-users-groups-and-delegated-actions) | [Admin/operational separation and migration 84](admin-operational-authority-separation.md) |
| Strategy access | [F02/F05](../product/features/access-and-strategies.md) | [Action-bound scopes, preview/matrix and migration 85](strategy-access-scopes.md) |
| Reference/booking | [Instrument management](../product/features/instrument-management.md), [product tickets](../product/features/product-booking.md) | [Capability matrix](booking-capability-matrix.md), [readiness](booking-readiness-alpha.md) |
| Trade operations | [Capabilities](../product/features/trade-operations.md) | [Properties](governed-trade-configuration-alpha.md), [history](trade-history-alpha.md), [corrections](historical-booking-and-record-corrections-alpha.md) |
| Market data | [Capabilities](../product/features/market-data.md) | [Policies](flexible-pricing-policies.md), [rights](scoped-dataset-entitlements.md), [sources](market-data-sources-ui.md), [Yahoo RAW](yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09), [calendars](tenant-fund-and-strategy-calendars-alpha.md) |
| Valuation/P&L | [Capabilities](../product/features/valuation-and-pnl.md) | [Position foundation](position-reconstruction-foundation.md), [economic delivery](economic-pnl-implementation-2026-10-09.md), [execution evidence](economic-pnl-implementation-progress.md) |
| Quality | [Capabilities/gaps](../product/features/platform-quality.md) | [API hardening](api-boundary-hardening.md), [latest merge](tenant-access-administration-progress.md#completed-remediation-verification) |

## Safe PostgreSQL verification

Private operator delivery: [FCAGF reconciliation source foundation and bond
onboarding](fcagf-reconciliation-import-20261023.md), 23 October 2026; partial,
not a completed financial import.

Never run integration tests against an operating application database, regardless
of its name. The pytest guard permits only recognised disposable fixture names
and the administration database needed to create/drop those fixtures. From the
repository root, with the local PostgreSQL service running:

```powershell
$env:APP_ENV='test'
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_migrations.py -q
```

The wrapper creates/migrates/seeds an owned disposable database and removes that exact database afterwards. CI uses `platform_isolated_tests_ci`, migration and seed setup before pytest. Application development may use the operating DB; test execution must not. Run focused affected suites first. A documentation-only review needs link/structure validation, not full application tests.

Dated commands in historical records are context, not current run instructions; consult current safety guidance before executing them.

For existing database credentials, pass `TEST_DATABASE_ADMIN_URL` to the wrapper.
See [provider-neutral defaults and existing-installation compatibility](provider-neutral-repository-20261017.md)
before changing Compose or application connection settings.
