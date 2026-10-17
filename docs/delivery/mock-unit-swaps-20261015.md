# Tenant-one mock unit swaps

Status: implemented and activated locally, 2026-10-15. Booking/data fixture only;
**not swap-valuation sign-off**. See [F18](../product/features/product-booking.md#f18-generic-swaps).

## Requested records

Tenant one, **Strat Testing** (`1df14361-1a24-40f6-aabb-7c0cb86cf5fb`).
Both are tenant-private, OTC, receive gross total return/pay funding, effective
2024-10-15 and maturing 2027-10-15. Both opening trades are BUY at zero whole-swap
MTM, executed at the underlying's inception-day session close. These are simulated
historical bookings recorded today, not claims of actual executions or historical
availability. Existing strategy dates, policies, trades and cash remain unchanged.

| Contract | Booked units | Leverage | Currency | Reference notional/unit | Unleveraged reference notional | EoD marks |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| SPX / SOFR + 15 bp | 100,000 | 1 | USD | 5,800 | 580,000,000 | 501 |
| UKX / SONIA + 10 bp | 25,000 | 1.5 | GBP | 8,250 | 206,250,000 | 506 |

One unit is explicitly **one currency unit per index point**, not one monetary
notional unit. These are therefore large exposures. Funding is on leveraged
reference notional: USD 580m and GBP 309.375m respectively. The fixed reference
notional per unit is an invented inception index level, not an observed fixing.
Full-contract quantity prefills the ticket; partial positive integer-unit trades
are permitted. No aggregate contract-capacity limit or inventory allocation is added.

- SPX instrument: `01a13f2d-cc60-7316-aa77-0aa199354d2e`;
  trade: `40abf903-aad3-43d8-b7d4-44a7bab76edb`;
  series: `01a13f2d-d08c-7b07-92cf-f3577525ea69`.
- UKX instrument: `01a13f2d-d2d1-7414-b277-3c25693caf19`;
  trade: `5172d36a-6905-4230-9d7f-59bdf82c044e`;
  series: `01a13f2d-d1f9-79cf-9b8c-cb070e917efc`.

Public governed SPX and FTSE 100 indices are reused. The existing SONIA reference
is reused; a tenant-private SOFR benchmark reference was added, without pretending
to populate genuine SOFR fixings. Benchmark references:
[New York Fed SOFR](https://www.newyorkfed.org/markets/reference-rates/sofr) and
[Bank of England SONIA](https://www.bankofengland.co.uk/markets/sonia-benchmark).
The spread is stored as decimal rate `0.0015` / `0.0010`.

## Unit-booking extension

[Generic terms](../../apps/reference_api/swap_creation_contracts.py) now support
`quantityUnit=UNITS`, `contractualUnits` and `notionalPerUnit` in addition to
unchanged default NOMINAL semantics. Unit terms must reconcile exactly:

`contractualNotional = contractualUnits × notionalPerUnit` (before leverage).

Approved conventions use `SWAP_VALUE_PER_UNIT`, divisor 1, minimum/increment 1.
The immutable BOOKED snapshot retains `bookedUnits`, derived unleveraged
`bookedNotional`, approved terms and quote conventions. Entry reference value is
signed units × quote ÷ divisor; leverage is **not** multiplied again. Negative
and zero swap marks remain supported. New optional fields are excluded from old
nominal serialization, preserving existing nominal fingerprints and replay.
Existing JSONB storage supports the additive fields; no migration was required.

Creation, ticket prefill/review, terms facts and trade history/detail distinguish
units from monetary notional. The legacy standalone swap-convention editor still
offers its original nominal-only convention; unit swaps are created through the
generic swap creation page/API. It does not infer a unit convention for legacy swaps.

## Synthetic price evidence and limitations

[Generator](../../scripts/mock_unit_swap_data.py) produces deterministic fixtures
and [seed](../../scripts/seed_mock_unit_swaps.py) defaults to read-only preview;
`--apply` is restricted to the named local database and checks reference, strategy
and market-data authority. Proposals, approvals and bookings use normal APIs with
stable idempotency keys. Guarded metadata/price seeding records audit events,
hashes, synthetic source, owned-data licence, tenant rights and immutable evidence.
It does not grant user permissions or alter existing provider priorities/policies.

[Retained artifact](../../data/mock-unit-swaps-20261015.json), SHA256
`b5bb4e72ddf8b6a2deadf47363065a03d76541afd7855f3b00fd92dc7b36612c`,
contains 2024-10-15–2026-10-14 EoD histories. XNYS/XLON sessions come from the
recorded `exchange_calendars` package version, including DST and early closes.
The underlying levels, dividends, funding path and discounts are **all invented**:
they are neither Yahoo nor counterparty marks and are not a calibrated swap pricer.
The model combines index changes, illustrative gross dividend carry, compounded
funding plus spread, and remaining-tenor discount, with leverage applied once.
SOFR uses ACT/360; SONIA ACT/365F. Both legs reset/pay at maturity to avoid inventing
unimplemented periodic reset cash flows. No funding, dividend or cash entries are
posted separately. RAW means these invented marks have no split normalization;
it does not make them actual or official prices.

The provider/dataset is labelled **MOCK ONLY** and owned by tenant one. Received
and publication timestamps are the actual seed time, not historical/backdated.
Calendar provenance is retained in the artifact; these fixtures do not publish
sealed 2024–2026 platform calendars. No false official-price or third-party-rights
claim is made. Histories are visible through the governed market-data series API.

Latest mock per-unit marks (2026-10-14): SPX **-994.38505019 USD**;
UKX **671.65350266 GBP**. Negative MTM is intentional and valid.

**Current valuation rejects generic SWAP economics.** These new open trades will
therefore block Strat Testing valuation rather than be silently ignored. This
delivery adds no swap P&L, funding/reset lifecycle, pricing policy or publication.
A separately designed frozen-input/whole-swap valuation slice remains necessary.

## Verification

- 56 focused Python rules/generator tests passed.
- Wider creation/booking disposable-DB run: 101 passed, one stale legacy role-based
  test failed. Updated that test to remove explicit action memberships (the current
  authority model), not to weaken authorization; rerun of it and unit-booking API
  regression: 2 passed. Full suite not run.
- 97 focused frontend tests passed, including unit creation submission, exact
  preview/prefill and unit-vs-notional history/detail regression. A cold-import
  test timeout was rerun with a 15-second test timeout; no assertions were removed.
- TypeScript and deterministic OpenAPI freshness passed after the final fixes.
- API restarted; approved instruments and trades exist in the operating local DB.
  Seed replay returned identical IDs; independent DB check found 501 + 506 marks.
  Live strategy positions show 100,000 and 25,000 UNITS, one contributing trade each.
  Both market-data history APIs return the new series. No browser/manual visual
  or external financial acceptance is claimed; no valuation or cash posting made.
