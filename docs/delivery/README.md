# Delivery records

**Status:** Accepted  
**Content type:** Delivery index  
**Owner:** Engineering delivery team  
**Last reviewed:** 2026-10-08

Use [specifications](specifications/README.md) for approved design intent, [implementation plans](implementation-plans/README.md) for execution sequences, and [quality reviews](quality-reviews/README.md) for dated evidence. None is automatically current architecture without a link from a canonical page.
# Delivery documentation

- [Latest available EoD defaults, explicit overrides and policy-context clarification](flexible-pricing-policies.md)

- [EUR/GBP UK FX readiness for October 6–7 — activated with FLEXIBLE_EOD v2](yahoo-eurgbp-valuation-setup-2026-10-09.md)

- [Economic strategy P&L — delivered scope, tests and pending activation](economic-pnl-implementation-2026-10-09.md)

- [Economic strategy P&L implementation plan — market, income/accruals, staged amendments and publication](../superpowers/plans/2026-10-09-economic-strategy-pnl.md)

- [Agreed economic P&L foundation, research and legacy frontend reference](economic-pnl-agreed-foundation-2026-10-09.md)

- [Proposed valuation price-basis plan: economic requirements and evidenced split conversion](../superpowers/plans/2026-10-09-valuation-price-basis.md)

- [One CLOSE price family with closing-method metadata and official-only policies](closing-price-consolidation.md)

- [Market data provider/scope catalogue and operational source priorities](market-data-sources-ui.md)

- [Public-universe historical booking dates and October 7 Yahoo update](index-trading-history-and-yahoo-2026-10-08.md)

- [Legacy booking cancel-only workflow and lifecycle-aware valuation exclusion](legacy-booking-cancellation-2026-10-08.md)

- [Daily valuation dates and built-in trade recognition — implementation, evidence and pending activation](daily-valuation-recognition-progress.md)

- [Lightweight instrument catalogue, batched reads and operating performance](instrument-catalogue-performance-2026-10-08.md)
- [Frontend loading, workspace failures, catalogue provenance and isolated verification](frontend-loading-recovery-2026-10-08.md)

- [Legacy P&L demo retirement and fresh valuation/P&L starting boundary](pnl-demo-retirement-and-fresh-start.md)
- [Yahoo daily equities, layered rights and personal-project activation](yahoo-market-data-alpha.md)
- [Yahoo five-year personal-research backfill, exception evidence and coverage](yahoo-five-year-backfill.md)
- [Ingestion hardening — durable jobs, partial retries, continuity reviews and calendar audit](md-ingestion-hardening.md)
- [Composite pricing policies — mixed session closes, separate fixings, version configuration and input preview](composite-pricing-policy-alpha.md)
- [Tenant fund and strategy calendars — versioned schedules, sourced exceptions and pinned assignments](tenant-fund-and-strategy-calendars-alpha.md)
- [Market data ingestion module boundary and provider contracts](market-data-ingestion-boundary.md)
- [API error responses](api-problems.md)
- [API boundary hardening — authority, transactions, retries, resource budgets and verification](api-boundary-hardening.md)
- [API contract delivery and dependency policy](api-contracts.md)
- [Current instrument creation and booking capability matrix](booking-capability-matrix.md)
- [Trade-side acceptance checklist, researched rationale and dated evidence](trade-side-acceptance-2026-10-06.md)
- [Swap identifier search and permission-aware instrument/booking UI](swap-search-and-permission-ui-2026-10-06.md)
- [S&P 500 and CAC 40 dated security-master seed](index-universe-seed-2026-10-06.md)
- [Booking readiness frontend and read-only cash eligibility](booking-readiness-alpha.md)
- [Historical booking rules, record cancellation/replacement and later lifecycle plan](historical-booking-and-record-corrections-alpha.md)
- [Shared booking controls, replay compatibility and locking](booking-controls.md)
- [Booking consolidation acceptance and self-review](quality-reviews/2026-10-05-booking-consolidation.md)
- [Instrument integrity review and confirmed hardening priorities](quality-reviews/2026-10-05-instrument-integrity.md)
- [FX booking active-scope enforcement and transaction protection](quality-reviews/2026-10-05-fx-scope-hardening.md)
- [Cash booking integrity and FX/bond/ETP approval revalidation](quality-reviews/2026-10-05-cash-and-approval-integrity.md)
- [Tenant workspace and strategy alpha](tenant-workspace-strategy-alpha.md)
- [Enriched trade booking alpha](enriched-trade-booking-alpha.md)
- [Deliverable FX-forward booking alpha](fx-forward-booking-alpha.md)
- [Listed option booking alpha](listed-option-booking-alpha.md)
- [Structured security and futures booking alpha](structured-security-and-futures-booking-alpha.md)
- [Futures creation and contract conventions alpha — delivered scope, local seed, multiplier semantics and remaining gaps](futures-creation-and-contract-conventions-alpha.md)
- [Bond booking alpha](bond-booking-alpha.md)
- [OTC autocall-reference swap booking alpha](swap-booking-alpha.md)
- [Generic swap creation and booking — implemented scope and activation limits](generic-swap-creation-and-booking.md)
- [Generic swap execution evidence and acceptance status](generic-swap-execution-log.md)
- [Swap booking — approved design and research](../superpowers/specs/2026-10-02-swap-booking-design.md)
- [Swap booking implementation plan and execution evidence](../superpowers/plans/2026-10-02-swap-booking.md)
- [Listed option booking quality review](quality-reviews/2026-10-01-option-booking-alpha.md)
- [Agreed booking and lifecycle scope and next option slice](booking-and-lifecycle-scope.md)
- [FX-forward booking quality review and alpha acceptance](quality-reviews/2026-10-01-fx-forward-booking-alpha.md)
- [Trade booking property section refresh](trade-booking-properties-ui-alpha.md)
- [Browser trade-configuration cycle acceptance](quality-reviews/2026-10-01-browser-trade-configuration-cycle.md)
- [Trade booking browser fixes, reusable regression and density findings](quality-reviews/2026-10-01-trade-booking-browser-follow-up.md)
- [Trade history alpha](trade-history-alpha.md)
- [Governed trade configuration and legacy cleanup](governed-trade-configuration-alpha.md)
- [Trade configuration UI refresh and acceptance checklist](trade-configuration-ui-alpha.md)

## PostgreSQL quality-check contract

PostgreSQL-backed migrations and integration tests are mandatory quality checks locally and in GitHub Actions. Both environments use the sole `DATABASE_URL` setting, conventionally `postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm`.

To check the migration boundary against a running local service, run:

```powershell
$env:DATABASE_URL='postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'
.venv\Scripts\python.exe -m pytest tests/test_migrations.py -v
```

- [Frontend presentation review — 8 October 2026](frontend-style-review-2026-10-08.md): native workspace styling, responsive forms and verification limits.
- [Market data workspace — operational overview, compact explorer and explicit coverage checks](market-data-workspace-2026-10-09.md)
