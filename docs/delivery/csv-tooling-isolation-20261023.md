# External CSV tooling isolation — 23 October 2026

**Status:** Implemented; no operating-data change.

Owner clarification: the externally prepared CSV bundle is a convenient
reconciliation exercise, not an official product integration or upload format.

## Changes

- Moved 16 source-specific adapter/operator modules from `data_imports`,
  `market_data` and `scripts` into `tooling/reconciliation_csv/`.
- Moved their 15 synthetic test modules alongside the tooling. Standard pytest
  discovery is now explicitly `tests/`; tooling tests require an explicit path
  and retain the same operating-database prohibition.
- Generic swap/option valuation tests use native synthetic contracts/bookings,
  never CSV loaders or source-specific mockup completion. Financial formulas and
  production validation are unchanged.
- Added a regression boundary: product packages and product tests may not import
  the tools; application schema, supported trade imports and valuation load with
  tooling imports deliberately unavailable. Both relocated CLIs support help
  from an unrelated working directory without connecting to a database.
- Docker contexts and Git source archives exclude `tooling/`. The repository
  currently has only a PostgreSQL Compose service, not an application image or
  wheel pipeline; this does not claim a new deployment architecture.
- Removed exercise counts from product capability evidence and relinked retained
  delivery records. Existing source-specific records are labelled as exercise
  evidence, not delivered product upload processors.

## What stays in the product

Supported tenant trade-file intake (`data_imports/formats.py`, `tables.py` and API
adapters), governed market-data storage/rights, normal booking services and general
AMC/swap/option/accrual valuation capabilities. No compatibility shim or startup
hook keeps the source-specific modules inside those packages.

## Verification

- 8 architecture/runtime/CLI and market-data boundary tests passed.
- 31 focused native swap/option valuation and supported upload tests passed.
- 61 explicitly opted-in tooling tests passed in a separate disposable database.
- 13 final isolation/neutrality/domain checks passed; API contract export check
  and scoped whitespace checks passed. The native original-fingerprint test also
  passed with recording time explicitly preceding approval, without CSV fixtures.
- Effective `export-ignore` attribute confirmed on `tooling`; API health remains
  `ok`. No service restart was needed for this source/test reorganisation.
- The first native run exposed an inconsistent synthetic performance reference.
  Using the existing approved-reference fixture fixed it; no production validator
  was bypassed or changed.
- No full regression suite, production package build or new financial acceptance.

No migration, data reimport, existing audit rewrite, financial record change,
permission grant, service restart, calculation or publication was performed.

[Operator instructions](../../tooling/reconciliation_csv/README.md).
[Implementation checklist](implementation-plans/isolate-csv-reconciliation-20261023.md).
