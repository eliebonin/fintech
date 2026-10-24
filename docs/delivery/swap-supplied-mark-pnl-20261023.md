# Supplied whole-swap mark P&L — 23 October 2026

**Status:** Implemented; focused verification recorded below. Not a portfolio sign-off.

## Decision and scope

Daily swap market P&L uses the swap's own supplied whole-contract quotation,
not its performance reference's price or a newly modelled funding leg. For an
unchanged position:

`signed booked quantity / frozen quote factor × (mark T × FX T − mark T−1 × FX T−1)`.

Units and nominal are distinct supported booking bases. The quotation must match
that basis. The unit multiplier is one: contractual reference notional, underlying
price, notional-per-unit and leverage are **not multiplied again**. A provider's
whole-swap mark already embodies its contract economics. Zero and negative swap
entry/market marks are legitimate; equity price safeguards are unchanged.

New executions and partial/full disposals use the existing signed execution
bridge, including economic-day FX. A fully closed boundary needs no invented
closing mark. A new position uses its actual execution price, not an assumed
opening mark for the whole position. Open exposure after contractual maturity
blocks pending an explicit Ops closing booking; no automatic zero or cash posting.

## Frozen evidence and source selection

- [Frozen adapter](../../security_master_schema/swap_valuation.py) validates the
  original approved generic definition, booking convention, quote currency,
  units, divisor and signed execution economics. Future native generic bookings
  also retain compact `valuationConventions`.
- Existing generic bookings can be read from those already-frozen facts without
  editing their BOOKED payloads or consulting today's terms. Incomplete leg-only
  legacy evidence and inconsistent explicit metadata fail closed.
- [Ledger reader](../../positions/repository.py) supplies the same shared
  [position bridge](../../valuation/position_calculation.py) used by supported
  securities. This is not another valuation calculator.
- [Input selection](../../valuation/service.py) accepts native RAW MARK/CLOSE
  prices on the **swap itself**. `SWAP_PRICE_BASIS`, `QUANTITY_UNIT` and
  `QUOTE_FACTOR` must match the frozen booking, with no contradictory dimensions.
  Underlying index levels cannot substitute for swap marks. Ordinary policy,
  provider ranking, licensing, currency, sealed calendar, information cutoff and
  freshness checks remain enforced. OTC instruments use an explicit pricing cut;
  an exchange session is not invented for them.
- New stored explanations include `SWAP_WHOLE_MARK`, alongside selected T/T−1
  price/FX dates and the shared value bridge. Historical results are not backfilled.

## RESET, payments and remaining limits

Dated RESET bookings retain their explicit INCOME/PAYMENT_ONLY classification.
INCOME contributes on its economic date; PAYMENT_ONLY contributes no new income.
A mark falling from 1 to 0 on 100 units and a separately recorded RESET income
of 100 net to zero in the same currency. Neither creates a cash-account balance
or alters the 100-unit position. Ops remains responsible for coherent marks and
flow classification; this change does not infer a reset or calculate funding.

Options, futures and structured-security P&L are not enabled by this extension.
There is no swap pricer, automatic reset/funding reconciliation, maturity engine,
settlement/accounting generation or independent provider reconciliation.

The FCAGF operating strategy includes an option, and imported private datasets
still need legitimate valuation eligibility and matching policy/calendar setup.
Enabling swaps alone does not establish that its complete valuation can succeed.
No operating rights, policy versions, trades or cash balances were changed here.

## Verification

Focused tests cover signed unit/nominal arithmetic, quote divisor once, zero and
negative marks, reporting FX attribution, new entries, partial/full closures,
separate RESET income and unchanged positive-equity guards:
[arithmetic](../../tests/test_swap_valuation.py),
[frozen evidence](../../tests/test_swap_frozen_valuation.py),
[native booking and real resolver](../../tests/test_swap_valuation_integration.py).
The integration checks run only in runner-owned disposable PostgreSQL databases.
The final bounded regression run passed **98 tests**, including native unit and
nominal booking, new/older frozen formats, real governed price selection,
ambiguous-basis rejection and retained staged results (not publication).
Read-only validation of **all 46 existing FCAGF swap bookings** passed without
changing event payloads. **Two** repository neutrality checks separately passed.
No full regression suite, operating financial reconciliation or browser
publication sign-off is claimed. No schema migration is required.

Local activation: this repository's API was restarted on port **8001** and
`/health` returned `status: ok`. The frontend on 3001 and unrelated services on
3000/8000 were not restarted. No operating valuation was calculated or published
as part of this activation.
