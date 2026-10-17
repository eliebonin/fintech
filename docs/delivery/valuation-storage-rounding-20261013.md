# Explicit valuation storage rounding

**Status:** Implemented; 61 focused tests passed  
**Content type:** Delivery / Decision  
**Owner:** Valuation and P&L  
**Last reviewed:** 2026-10-13

## Cause and decision

Attempt `01a13591-6af6-7622-811f-8e4643f7eee6` used FLEXIBLE_EOD v3 and
calculated October 7–8 successfully. Staging rejected FX-derived amounts beyond
twelve decimal places. The generic error suggested missing inputs; the prior
calculation-only diagnostic missed this storage boundary.

Keep exact Decimal arithmetic/evidence. At initial staging, round each financial
component to **12 decimal places, ROUND_HALF_EVEN**. Derive market/gross/net
totals from the rounded components in their existing classifications. Do not
independently round totals, add a hidden balancing economic component, or round
to currency pennies.

Each immutable attribution stores `storageRounding`: policy version 1, scale/mode,
exact original components/totals and explicit stored-minus-exact adjustments.
Original position values/execution bridge remain exact. Batch totals sum stored
line totals; `marketRoundingAdjustment` reconciles stored market P&L against the
exact closing-minus-opening-minus-execution bridge. Publication checks this
adjustment against immutable attribution evidence. Amendment versions retain
the original rounding evidence/bridge. Operator amendment input remains exactly
representable to twelve decimals: no silent rounding of submitted amounts.

Failed-run example: exact GBP market P&L `18809.84474679507690589875` stores
as `18809.844746795077`; explicit adjustment `0.00000000000009410125`.
Small synthetic amounts test where summed rounded components differ from an
independently rounded exact total.

Nonfinite values, pre/post-rounding overflow and overflowing component-derived
totals still fail. No zero substitution, float conversion, wider database column,
migration or rewriting of published history. Safe `StorageAmountError` messages
reach operational logs; arbitrary exception details stay redacted. Old results
without rounding evidence use zero adjustment for publication compatibility.

## Implementation and verification

- [Rounding](../../valuation/rounding.py), [staging/publication](../../valuation/storage.py),
  [position evidence](../../valuation/position_storage.py), [logging](../../valuation/runner.py).
- [Pure tests](../../tests/test_valuation_rounding.py): original values, positive/
  negative half-even ties, income/cost reconciliation, nonfinite values, overflow
  including after rounding, and maximum representable amounts.
- [Storage regression](../../tests/test_valuation_storage.py): test-first rejection,
  then disposable PostgreSQL staging, exact evidence, tampered bridge refusal,
  amendment and independent publication.
- **61 focused tests passed**: rounding, storage, amendments, valuation API,
  position-attribution storage and valuation follow-up. No full Python suite,
  following the agreed testing approach. Additional prior focused run: 49 passed.

Currency display/accounting rounding remains separate. This fix makes calculations
reproducibly storable; it does not certify economic completeness, independent
price validation or custodian agreement.

## Local activation

API restarted with the verified project runtime; health returned HTTP 200.
A new normal API request, with a new request key/current information cutoff,
used FLEXIBLE_EOD v3 for the user's October 7–8 period. There were no existing
staged candidates for that strategy/date before acceptance.

- Attempt `01a135d1-d88f-79c3-9e04-ed422c4637b5`: **COMPLETED**.
- Batch `01a135d1-f163-7657-8528-954abc3b47d8`: **STAGED**, not published.
- Stored GBP market/gross/net P&L: `18809.844746795077`.
- Market rounding adjustment: `0.00000000000009410125`.
- API response retained in `logs/valuation-rounding-acceptance-20261013.json`.

Original failed attempt remains unchanged. No operating result was amended,
independently approved or published by this verification. Independent review of
the new staged batch remains the normal next step.
