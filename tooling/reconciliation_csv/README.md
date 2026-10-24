# External CSV reconciliation — optional tooling, not product code

These scripts import one externally prepared research/reconciliation bundle.
Its CSV layout, field mappings, inferred/mockup terms and local activation steps
are **not** an official product interface or supported tenant upload workflow.
They can be removed without affecting application startup or product tests.

## Boundary

- All source-specific parsing, mapping, precision normalization, seeding, booking,
  cash/interest/RESET publication and price/FX/eligibility operators live here.
- Dependencies point from tooling to existing platform services, never back.
  Normal permissions, business validation, immutable source evidence and replay
  checks still apply. No bypass, provider licence or production correctness claim.
- Production `data_imports` retains only supported tenant intake primitives.
  The existing trade-upload API/UI is separate and unchanged.
- The default pytest collection is `tests/`. This directory's synthetic tests
  require an explicit path and retain the operating-database connection guard.
- `tooling/` is excluded from Docker build contexts and Git source archives.
  There is currently no backend application Dockerfile/wheel distribution; these
  exclusions do not claim an unimplemented production packaging system.
- Raw CSVs and generated evidence remain outside version-controlled source.
  Do not commit private files, credentials or report exports into this directory.

## Explicit local use

From the repository root, inspect help before using any write option:

```powershell
.venv/Scripts/python.exe -B -m tooling.reconciliation_csv.seed_reconciliation_bundle --help
.venv/Scripts/python.exe -B -m tooling.reconciliation_csv.prepare_reconciliation_valuation --help
```

Direct script invocation also works from another directory. The seed operator's
no-apply mode prepares evidence; the eligibility operator defaults to a full
transaction rollback. Existing explicit apply/local-database restrictions remain.
No command runs on application startup, CI product seeding or a tenant page.

Run synthetic tooling checks only against the owned disposable database runner:

```powershell
.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tooling/reconciliation_csv/tests -q -p no:cacheprovider
```

Supply `TEST_DATABASE_ADMIN_URL` as documented by the
[disposable test runner](../../../docs/delivery/README.md#safe-postgresql-verification).
Never point these tests at operating data.

Historical source-specific results and assumptions remain in
[the reconciliation delivery](../../../docs/delivery/fcagf-reconciliation-import-20261023.md).
These records are test-exercise evidence, not additions to the feature catalogue.
