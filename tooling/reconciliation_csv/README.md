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
[disposable test runner](../../docs/delivery/README.md#safe-postgresql-verification).
Never point these tests at operating data.

Historical source-specific results and assumptions remain in
[the reconciliation delivery](../../docs/delivery/fcagf-reconciliation-import-20261023.md).
These records are test-exercise evidence, not additions to the feature catalogue.

## FCPGF exercise

[FCPGF import, assumptions and exceptions](../../docs/delivery/fcpgf-reconciliation-import-20261030.md)
records the separate GBP portfolio at 20 October 2026. Its explicit operator is:

```powershell
.venv/Scripts/python.exe -B -m tooling.reconciliation_csv.fcpgf_import --help
```

Without `--apply` it only validates and summarizes the external bundle. Explicit
local operating writes require `APP_ENV=local`, the runtime database URL and the
private installation name in `LOCAL_WORKSPACE_DATABASE`. Source directories and
personal-file operator identity must be supplied explicitly; no credentials or
customer paths are embedded in source. Booking phases can be run separately so
unrelated source exceptions do not discard completed, audited native commands.

`fcpgf_instruments` owns source metadata completion, `fcpgf_bond_completion`
discloses missing historical settlement-accrual estimates, `fcpgf_option` reuses
the reviewed standard contract, and `fcpgf_import` orchestrates the local phases.
They are not general onboarding or tenant upload services. The strategy is
explicitly labelled **PARTIAL IMPORT** while source executions remain unposted.

`fcpgf_unit_movements` is the owner-approved zero-price fund classification
adapter. The explicit `unit-movements` phase calls the native typed movement
command for transfers/reinvestment credits. Recurring-date inference and source
classification are optional tooling only, not general product rules. Source
zero prices are retained and do not become purchases or generated distributions.

`fcpgf_rate_swaps` completes the four separately priced floating/floating source
components via native proposal approval and the shared booking command. The
explicit `rate-bookings` phase preserves existing canonical/series/RESET
identities, derives the USD-leg notional from its separate source companion and
retains every scheduling/principal limitation. This is not package netting or a
supported general CSV rate-swap upload workflow.

For an explicitly enabled fund NAV policy, `reconciliation_eligibility.prepare`
publishes and pins a tenant VALUATION calendar through the existing calendar
service. That calendar represents source-date-only reconciliation buckets, not
actual fund dealing/publication conventions. Reference-time rules remain separate;
missing same-day marks still fail. The [31 October attempt](../../docs/delivery/fcpgf-valuation-attempt-20261031.md)
records activation, focused checks and missing source data without treating file
import completeness as valuation acceptance.

## Fund NAV convention

Fresh personal-file eligibility setup uses an explicit one-valuation-session fund
NAV lag (T−1/T−2 marks) with same-day FX (T/T−1). Its published tenant calendar
is a declared weekday baseline, not an assertion about actual fund holidays.
Supply governed closures when known; missing requested NAVs still fail/flag under
the selected policy action. See [correction and activation](../../docs/delivery/fund-nav-lag-20261031.md).
Replaying an earlier setup instruction returns its original receipt; update live
configuration through a new native policy/calendar version, not receipt mutation.

## Source trade activity

An explicit `active=False` excludes the row from prepared position bookings and
dated RESET flows. Related daily-interest rows remain retained source evidence
but do not contribute to aggregated interest. Raw CSV bytes and parsed source
rows are preserved; `inactiveTradeIds` records the exclusions in new manifests.
No earlier receipt is rewritten. A present activity column must contain an
unambiguous true/false value (case and surrounding whitespace are normalized);
blank or unknown values fail preparation. Older export variants without that
column retain their existing inclusion behavior.

This preparation filter does not cancel previously booked native trades. Use the
normal audited cancellation command for erroneous imported bookings, then create
a fresh valuation candidate. The [31 October cancellation check](../../docs/delivery/inactive-source-trade-cancellation-20261031.md)
records that workflow, retained history and financial verification.
