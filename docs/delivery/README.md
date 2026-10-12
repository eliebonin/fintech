# Delivery records

**Status:** Maintained evidence index  
**Content type:** Delivery index  
**Owner:** Engineering delivery  
**Last reviewed:** 2026-10-12

For desired-versus-current scope start with the [feature register](../product/feature-register.md), not a chronological plan. Delivery documents record dated implementation, tests and activation; later work may supersede an earlier scope/exclusion without rewriting its evidence.

## Retrieval

- [Complete delivery-record catalogue](catalogue.md): stable links to individual records.
- [Specifications](specifications/README.md): design intent and historical constraints.
- [Implementation plans](implementation-plans/README.md): intended execution, not completion proof.
- [Quality reviews](quality-reviews/README.md): dated findings and verification limits.
- [Documentation review / reconciliation](quality-reviews/2026-10-12-documentation-reconciliation.md).
- [Merge/remediation verification](tenant-access-administration-progress.md#completed-remediation-verification).

## Current capability evidence by domain

| Domain | Current reference | Principal delivery evidence |
| --- | --- | --- |
| Access/strategies | [Capabilities](../product/features/access-and-strategies.md) | [Tenant administration](tenant-access-administration.md), [strategies](tenant-workspace-strategy-alpha.md) |
| Reference/booking | [Instrument management](../product/features/instrument-management.md), [product tickets](../product/features/product-booking.md) | [Capability matrix](booking-capability-matrix.md), [readiness](booking-readiness-alpha.md) |
| Trade operations | [Capabilities](../product/features/trade-operations.md) | [Properties](governed-trade-configuration-alpha.md), [history](trade-history-alpha.md), [corrections](historical-booking-and-record-corrections-alpha.md) |
| Market data | [Capabilities](../product/features/market-data.md) | [Policies](flexible-pricing-policies.md), [rights](scoped-dataset-entitlements.md), [sources](market-data-sources-ui.md), [Yahoo RAW](yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09), [calendars](tenant-fund-and-strategy-calendars-alpha.md) |
| Valuation/P&L | [Capabilities](../product/features/valuation-and-pnl.md) | [Position foundation](position-reconstruction-foundation.md), [economic delivery](economic-pnl-implementation-2026-10-09.md), [execution evidence](economic-pnl-implementation-progress.md) |
| Quality | [Capabilities/gaps](../product/features/platform-quality.md) | [API hardening](api-boundary-hardening.md), [latest merge](tenant-access-administration-progress.md#completed-remediation-verification) |

## Safe PostgreSQL verification

Never run integration tests against the operating `fortem_secm` database. The pytest guard rejects it before connecting. From the repository root, with the local PostgreSQL service running:

```powershell
$env:APP_ENV='test'
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_migrations.py -q
```

The wrapper creates/migrates/seeds an owned disposable database and removes that exact database afterwards. CI uses `fortem_isolated_tests_ci`, migration and seed setup before pytest. Application development may use the operating DB; test execution must not. Run focused affected suites first. A documentation-only review needs link/structure validation, not full application tests.

Dated commands in historical records are context, not current run instructions; consult current safety guidance before executing them.
