# Dates and schedules

## Key dates

Use a wide, one-to-one `instrument_dates` table for singular, cross-asset dates. This enables consistent cross-asset queries, such as screening any instrument with a maturity date before a threshold.

```text
instrument_dates
  instrument_node_id
  issue_date
  effective_date
  first_trading_date
  last_trading_date
  strike_determination_date
  expiry_date
  maturity_date
  termination_date
  final_valuation_date
  final_settlement_date
  cash_settlement_date
```

Null columns are acceptable in a reference-data table when they provide a meaningful common cross-asset vocabulary.

Use precise names: do not use ambiguous fields such as `trading_date` or `settlement_date` where `first_trading_date`, `last_trading_date`, or `final_settlement_date` is intended.

## Do not mix date categories

* Instrument contractual and lifecycle dates belong in `instrument_dates`.
* Trade execution, booking, and settlement dates belong to trades/trade events.
* Reference-data version validity belongs to `valid_from` and `valid_to` on versioned records.

## Repeating schedules

Coupon payments, swap resets, fixing dates, and autocall observation dates are repeating schedules. They belong in dedicated schedule tables rather than in `instrument_dates`.

The later schedule design should have a common schedule header and dated child events/cashflows, with links to asset-specific owners such as a bond coupon, swap leg, or structured-product observation rule.
