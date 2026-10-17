# Multi-position valuation review fixture

**Follow-up:** [Reviewed share-ratio replay](share-ratio-position-replay-20261013.md) removes the temporary Air Liquide post-split workaround through a new linked mock correction. Its intended October 2024 100-share acquisition now reconstructs as 110; both earlier records remain superseded audit history. The original seed evidence below remains the record of that initial setup.

**Status:** Booked locally; validation below  
**Content type:** Delivery / Test data  
**Owner:** Trading and valuation  
**Last reviewed:** 2026-10-13

User requested 5–10 names in the existing strategy, with multiple executions over
the preceding two years. Added **29 active synthetic executions across eight Paris
names** to Platform Demo Tenant's **Strat Testing**
(`1df14361-1a24-40f6-aabb-7c0cb86cf5fb`). Together with existing TTE this gives
nine position subjects. Existing trades and the existing staged result were not
overwritten. Bookings went through the normal `/v1/trades` API as the existing
authorized actor `00000000-0000-7000-8000-000000000083`.

| Name | Symbol | Active added trades | Signed shares |
| --- | --- | ---: | ---: |
| Airbus | AIR | 5 | 175 |
| BNP Paribas | BNP | 5 | 175 |
| L'Oréal | OR | 5 | 175 |
| LVMH | MC | 4 | 165 |
| Sanofi | SAN | 4 | 165 |
| Schneider Electric | SU | 4 | 165 |
| Air Liquide | AI | 1 | 100 |
| Vinci | DG | 1 | 100 |

Dates: October 15, 2024; April 15 and October 15, 2025; April 15, 2026;
July 15, 2026 (AI); and October 8, 2026 (three additional BUY executions).
Buys are 100 initial / 50 addition / 40 addition shares, with partial sells of 25
shares on six names; three October 8 buys are 10 shares each. No accidental shorts.

## Provenance and controls

All records carry `SYNTHETIC-PNL-REVIEW-20261013-…` external references, deterministic
request keys and an explicit synthetic-only comment. Execution prices simulate a
historical close: retained **Yahoo CLOSE/RAW** values for the exact trade date,
with the source observation UUID recorded in the comment. These are **not actual
executions** or newly downloaded market data. Missing/ambiguous price inputs fail
preflight; no zero prices, adjustment relabelling or inferred holiday fills.

Listing/version eligibility, trade authority/strategy scope, current market-data
read/display rights, required properties and contract shapes are checked before
booking. The normal writer revalidates every mutation, saves frozen BOOKED
conventions/recognition and records lifecycle evidence. Required allocation weight
is `0.125`, explicitly fixture metadata, not the valuation quantity calculation.
The strategy's configuration/effective date is unchanged; the current historical
booking path permits these imported executions on an active authorized strategy.

Synthetic settlement dates use T+2 trading business days from the installed XPAR
calendar library. Missing source prices are not holidays. This is an explicit
fixture convention, **not certified settlement-calendar coverage**. API booking
currently records its normal `MANUAL_UI` execution channel; the API-seed external
reference/comment identifies the actual synthetic provenance rather than changing
the writer/channel contract for this task.

## Corporate-action safety and correction

The first diagnostic correctly blocked the initial AI acquisition dated October
2024 because it crossed Air Liquide's **June 8, 2026 stock split**. The guard was
not disabled and no replay or split-adjustment proof was fabricated.

That one newly seeded record was replaced through the normal linked booking
correction with an acquisition on **July 15, 2026**, after the split. The original
AI trade `4082993c-cad1-43b7-b04e-e5f87b586b6f` remains SUPERSEDED; replacement
`14a03d82-74f2-4011-a1da-585e78481e39` is BOOKED. Both retain lifecycle evidence
and the reason. Hence **30 physical seed records, 29 active**, not a silent delete.
Other names still provide the requested two-year histories. True pre-split
investment holdings remain blocked until proper corporate-action replay exists.

## Reproduction and verification

[Operator script](../../scripts/seed_valuation_review_trades.py) previews by default:

```powershell
./.venv/Scripts/python.exe -B scripts/seed_valuation_review_trades.py
./.venv/Scripts/python.exe -B scripts/seed_valuation_review_trades.py --apply
```

Restricted to the named local personal database/loopback API and fixed test scope.
All payloads preflight before writes; apply uses deterministic API idempotency keys.
Replay detects changed economics/property conventions rather than silently changing
an existing record. Applying the revised plan replayed the other 28 records and
created only the linked AI replacement. Every seeded record has lifecycle evidence.
No roles, module grants, prices, licences, existing user trades or financial
publications were changed.

- **Two focused pure tests passed**, pinning the scenario count/date distribution,
  partial-sell exposure and business-day fixture behavior; no full Python suite.
- Logs: `logs/valuation-review-trade-preview-20261013.json`,
  `logs/valuation-review-trade-booking-final-20261013.jsonl`,
  `logs/valuation-review-trade-verification-20261013.log`.
- Expanded October 7–8 calculation with FLEXIBLE_EOD v3 and a current information
  cutoff **passed**: nine position lines, three period executions, 35 ledger facts
  scanned. Every line passed the explicit storage-rounding boundary. Diagnostic
  snapshot writes were rolled back; no new run, staged batch or publication was
  created. Evidence: `logs/valuation-review-expanded-diagnostic-20261013.log`.
- A new calculation must use a **current information cutoff**, because these are
  newly recorded historical executions. A retained old batch does not absorb new
  bookings. Start a new FLEXIBLE_EOD v3 request to inspect the expanded strategy.

This expands the [review workspace](valuation-review-workspace-20261013.md) test
population. It is not actual trading history, a custodial comparison, accrued
income completeness or financial sign-off.
