# Strategy register cleanup — 19 October 2026

Owner approved archiving irrelevant/unused strategies rather than deleting them.
Inventory found eight strategies, all in tenant one; no strategy rows existed in
the other tenants. No replacement strategies were created in this cleanup.

## Archived

| Code | Strategy ID | Previous status | New status |
| --- | --- | --- | --- |
| UK_FUND_CUTOFF_DEMO | 00000000-0000-7000-8000-000000000097 | ACTIVE | ARCHIVED |
| US_FUND_CUTOFF_DEMO | 00000000-0000-7000-8000-000000000098 | ACTIVE | ARCHIVED |

Both were unused cutoff demonstrations: zero trades, legacy calculation runs,
modern valuation attempts/review batches, position snapshots, pricing policies,
resolution snapshots, valuation marks, daily accruals, cash accounts/balances,
file-import jobs and bond/FX maturity policies in the inspected categories.
Archival used the existing authorized API status command, not SQL deletion or
a permission bypass. The successful responses and subsequent API read confirmed
both ARCHIVED statuses.

## Retained active

- STRAT-TEST — main mixed-product exploration strategy.
- MOCK_BOND_CYCLE_20261015 — targeted bond valuation example.
- NEW-STRAT — user-created strategy with a booked trade; not assumed disposable.
- DEMO_INCOME — retained legacy valuation/position evidence.
- MVP_UK_PORTFOLIO and MVP_US_PORTFOLIO — portfolios with booked trade history.

Final readback: six ACTIVE and two ARCHIVED strategies; all eight rows remain.
Retained totals remain 46 trades, 28 modern valuation attempts and six review
batches, matching the pre-cleanup per-strategy inventory totals. No financial,
cash, market-data, policy or access records were deleted or rewritten.

Archived strategies remain inspectable historical records, not purged names.
This does not add a restore UI; any later reactivation requires a separately
authorized administrative operation. No application-code change or restart was
needed, and no financial valuation was calculated or published.
