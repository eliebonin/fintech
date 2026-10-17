# Futures position measures

**Status:** Bounded alpha implemented; API activated, operating futures financial acceptance not claimed  
**Content type:** Delivery reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-15

## Agreed scope

Extend Strategy → Measures to the existing **linear cash-settled index-futures**
booking alpha. This is monetary exposure, not futures P&L, full NAV, risk weights,
margin processing or delivery. Physical/crypto creation-only contracts, inverse,
quanto, commodity and interest-rate-specific quotations remain excluded.

The three common fields keep their distinct meanings:

| Field | Futures calculation |
| --- | --- |
| Reference notional | Current signed contracts × dated futures price × frozen monetary multiplier ÷ quote factor |
| Economic exposure | Same current market notional in this linear index slice |
| Market value / contract MTM | Unavailable: no clearing/variation-margin settlement boundary and outstanding-value evidence |

Reference notional here is **current market notional**, not historical booked
consideration, initial margin or a cost-basis/FIFO calculation. Market notional
must not be included as a NAV asset. Absence of clearing evidence is not proof
that the contract's remaining MTM is zero. No cash booking is generated.

Example: 10 ES contracts at 6,000 points × USD 50/point = USD 3,000,000 current
notional/exposure. At 6,010 it is USD 3,005,000. The USD 5,000 change is distinct
from that full notional; recognizing P&L or settling variation is outside this
implementation. Shorts retain signed amounts. A genuine zero quote is zero
notional, while missing prices remain unavailable. Negative quotes require the
frozen convention's explicit permission.

## Frozen units and contract identity

The retained BOOKED `FutureConvention` supplies currency, CONTRACTS quantity,
INDEX_POINTS price basis, CASH settlement, monetary multiplier, quote divisor,
negative-price permission and dates. Compatible conventions and one dated
instrument/listing identity are required for each position. Factor/currency/unit
mismatches fail closed; underlying-unit and physical contracts are not silently
valued using this formula.

Booked quantity already counts **canonical contracts**. Apply the monetary
multiplier once and do not multiply again by listing metadata or family contract
size. In the quantity-only holdings key, the historical `unitMultiplier` slot for
futures contains the frozen monetary multiplier; the adapter checks it against
the convention. This does not establish a new non-one-to-one listed-unit booking
workflow. Listing conversion, if ever needed, belongs at an explicit unit boundary.

## Governed input selection

Use the price of the **exact dated listed future**, not its family, underlying
cash index, a different expiry or a continuous/rolled series. A series must identify:

- `CONTRACT_INSTRUMENT_ID`: the canonical expiry UUID from BOOKED terms;
- `FUTURE_PRICE_BASIS=INDEX_POINTS`;
- one numeric `QUOTE_FACTOR` equal to the frozen divisor.

The selected policy must explicitly permit native **RAW** `CLOSE` or `SETTLEMENT`
prices, governed PRICE measurement and SESSION_CLOSE or EXPLICIT_TIME semantics.
Settlement price is not relabelled as ordinary close. Equity AS_TRADED/share-split
normalization is not a futures pricing method. Semantic restrictions narrow the
normal resolver; they do not override rules, source priority or licensing.

Existing sealed-calendar, actual price date, timestamp, information-cutoff,
bounded-freshness, valuation-use and current DISPLAY checks remain. Reporting
conversion uses the selected date's governed price-currency → strategy-currency
FX, including explicit inverse permission where applicable. Native amounts remain
visible as LOCAL_ONLY when FX is missing; no currency relabelling or assumed FX.

No operating prices, policy versions, provider rights or synthetic trades are
provisioned by this feature. Existing strategy policies may need explicit futures
rules and suitably described/eligible contract series before a preview succeeds.

## Lifecycle and presentation

An unclosed position after frozen final settlement is unavailable with an Ops
closure explanation, not automatically zeroed. Between last trading and final
settlement, any permitted price must still pass normal selection; the evidence
warns that only an explicit lifecycle booking closes exposure. Contract expiry
does not itself establish delivery, cash settlement or a variation-margin amount.

The existing Measures table displays local and fund-currency amounts. Market value
is explicitly Unavailable, with a clearing/variation-margin explanation in Inputs
and calculation. Evidence includes `FUTURE_CURRENT_NOTIONAL`, the frozen convention,
canonical-contract quantity basis, price selection, FX and evidence hash. The
preview is not persisted, staged or published. Existing P&L product guards remain;
adding futures exposure does not enable futures in the P&L engine.

## Verification and activation

Test-first kernel cases cover multiplier/divisor once, long/short, zero/missing
prices, approved negative quotes, finite factors and integer contracts. Real
isolated approval → booking → governed price → preview cases cover CLOSE and
SETTLEMENT, explicit-time cuts, reporting FX/inversion, multiple buys/sells,
missing FX, wrong contract/price-basis/divisor metadata, incompatible frozen
conventions and expired open positions. No operating trades are used as fixtures.

Verification on 15 October:

- Ten pure kernel cases failed before the kernel existed, then passed. Real
  integration assertions reproduced unsupported FUTURE results before the adapter
  was added; the financial/FX/expiry cases then passed.
- Final affected disposable-DB run: **104 passed**, nine existing framework/
  SQLAlchemy deprecation warnings. It includes the new futures kernel/input tests,
  existing monetary measures, split/fund assurance, strategy authority, valuation
  selection/resolver and product-booking regressions. This is not a full suite.
- Existing Measures/navigation/read-deadline UI checks: **15 passed**. TypeScript
  and API-contract freshness passed. No new response schema or migration.
- Local API restarted to activate the code. No operating financial rows, provider
  grants, policies or cash were modified. The futures financial examples above
  are hand checks and isolated scenarios, not newly booked operating positions.
- Live health returned 200; the existing Strat Testing preview on 2026-10-08
  still returns all three measures available for its 11 equity/swap positions.
  This checks non-regression, not operating futures financial acceptance.

To use the feature, select a strategy containing supported futures in its Measures
tab and an eligible policy with the exact-contract metadata above. Operating
future prices/rules are **not seeded by this implementation**. A missing input
remains unavailable. Live futures browser/financial acceptance with representative
licensed data remains separate from these passing synthetic checks.

## Sources and applicability

Primary sources read on 15 October 2026:

- [CME equity-index notional value](https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/discover-equity-index-notional-value-and-price):
  futures price times the product multiplier gives contract notional; ES uses
  USD 50/point. Extending that to signed position quantity and our quotation
  divisor is the application's dimensional convention.
- [CME money calculations](https://www.cmegroup.com/education/articles-and-reports/money-calculations-for-futures-and-options):
  futures settlement variation is banked daily. Accordingly we do not label full
  notional as a NAV asset or fabricate a residual MTM without settlement evidence.
  This source does not certify our implementation or enable a margin ledger.

## Implementation

- [Kernel](../../valuation/position_measures.py), `linear_future`.
- [Governed adapter](../../valuation/measure_inputs.py), FUTURE branch.
- [Selection guards](../../valuation/service.py), `_selection`.
- [Pure arithmetic tests](../../tests/test_future_measures.py).
- [Real booking/input tests](../../tests/test_future_measure_inputs.py).
- [Existing booking boundaries](futures-creation-and-contract-conventions-alpha.md).
- [Shared Measures workflow](position-monetary-measures-20261015.md).
