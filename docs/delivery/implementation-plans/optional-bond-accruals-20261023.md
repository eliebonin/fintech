# Optional bond accrual coverage

Approved scope: the 23 October conversation explicitly requests supplied interest
to be included, missing interest to be disclosed rather than fabricated as zero,
and complete coverage only when explicitly requested. This is general valuation
behaviour, not accommodation in the one-off external CSV importer.

## Design and alternatives

Use optional-by-default assessed daily accruals and an explicit
`requireCompleteAccruals` request flag (default false). Reject both the previous
universal requirement and silent zero-filling: neither represents the agreed
scope. Supplied invalid evidence, currency/FX failures and unsupported maturity
still block. No coupon/accretion model or financial-history rewriting.

Record missing canonical bond/date coverage in immutable line and batch evidence,
show a prominent results warning, and preserve confirmed-zero inputs separately.
Publication must refuse an omitted input that has since been supplied, just as it
already refuses a revised supplied input. A new calculation is required; existing
published results remain immutable.

## Sequential implementation

- [x] Add failing focused tests for absent, partial, zero, strict and invalid
  coverage, immutable staging and missing-then-supplied publication protection.
- [x] Add request option and coverage evidence in the existing accrual consumer;
  preserve all supplied-input validation and economic calculations.
- [x] Wire the option into the existing form and show missing coverage clearly,
  without client-side financial calculation or weakening display permissions.
- [x] Run focused disposable-database/API and frontend tests, type/contract checks;
  update maintained capability/methodology records and activation evidence.

No migration, trade mutation, invented daily interest or automatic publication.

Verification: [delivery record](../optional-bond-accruals-20261023.md). Native
sequential execution, focused checks only as requested; unrelated dirty changes
preserved. Legacy reassessment without a recorded coverage mode retains its
former strict requirement rather than silently broadening an old calculation.
