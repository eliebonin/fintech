# Termsheet note booking readiness — 14 October 2026

The user reported no matches for XS3487050836 on the listed-cash ticket. Reproduction
against the original app repository confirmed two separate causes:

1. `/trades/new` searches cash listings and excludes STRUCTURED_PRODUCT types.
   The correct page is `/trades/new?product=STRUCTURED_PRODUCT`, execution route OTC.
2. The six seeded parent notes had approved instrument terms but no approved
   booking conventions. Structured search found BNP but returned MISSING_CONFIGURATION.

The operator seed now submits and separately approves conventions for all six
parent notes, under the user's existing instruction to complete the load using
recorded best guesses. No share layers were granted booking conventions.

| Convention | Reviewed setting |
| --- | --- |
| Funding | FULLY_FUNDED |
| Quantity | UNITS, one source GBP/USD 1 denomination per unit |
| Price | PCT_OF_PAR, divisor 100; price 100 equals par |
| Accrual | DIRTY quote, no separately guessed accrued amount |
| Minimum/increment | 1 unit; explicit secondary-unit assumption, not primary-subscription eligibility |
| Route | OTC allowed; actual counterparty and settlement date supplied at booking |
| Validity | Starts at each existing approved instrument effective date |

Original app readback confirms all six notes READY on 14 October 2026. BNP
XS3487050836 is also READY on 5 October 2026, matching the investigated date.
Cash search still correctly returns zero; no listing was invented and no cash
family filter was relaxed. Internal unconfirmed BNP share remains nontradable.
Strategy/actor permissions, counterparty and execution fields are separate checks.
No trade was booked, and no service restart or migration occurred.

- [Explicit policy](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/data/termsheet_booking_policy_2026_10_14.json).
- [Seed helper](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/termsheet_booking_conventions_seed.py).
- [Operator command](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/scripts/seed_termsheet_booking_conventions.py): rollback by default; `--apply` commits.
- [Regression](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/tests/test_termsheet_booking_conventions_seed.py).

15 focused disposable tests passed, including all-six creation/readiness, BNP on
the investigated date, replay and no-trade side effects. Operating preview and apply
created six convention approvals; replay created zero/reused six. Original app
repository readback verified readiness and unchanged cash exclusion. Evidence:
`.implementation/termsheet-booking-*`. Browser acceptance was not exercised.
