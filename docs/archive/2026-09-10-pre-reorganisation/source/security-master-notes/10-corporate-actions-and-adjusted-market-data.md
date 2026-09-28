# Corporate actions and adjusted market data

## Evidence status

This note defines an internal, lean canonical model and does not claim that its
event codes or adjustment algorithms are a universal industry standard. The
first research pass identified ISO 20022 securities-event messages as the next
primary source to validate against, but venue/custodian-specific event and
adjustment conventions remain a research gap. See the
[external evidence register](24-external-evidence-and-research.md).

## Scope and first-release boundary

Corporate actions are a first-class reference-data event domain. They must be kept distinct from both raw market data and portfolio/account processing.

The first release stores the canonical event and its economic effects. It does not attempt to become a global-custody processing engine.

Build now:

* cash dividends;
* stock splits and reverse splits;
* bonus issues;
* spin-offs;
* basic mergers and security replacements;
* event-linked identifier/ticker/listing changes;
* raw, split-adjusted, price-return, and explicitly defined total-return market-data series.

Defer until the platform is responsible for custody processing:

* account/portfolio entitlements;
* voluntary elections, tenders, rights subscriptions, and proration;
* tax withholding elections and beneficial-owner processing;
* settlement claims, manufactured dividends, and confirmed cash/security movements;
* full adjusted-option deliverable baskets.

## Lean canonical model

```text
corporate_action
  corporate_action_id
  affected_instrument_node_id
  event_type                    -- controlled code: CASH_DIVIDEND, STOCK_SPLIT, ...
  status                        -- ANNOUNCED / CONFIRMED / CANCELLED / COMPLETED
  source_id
  external_event_reference
  is_current
  n_sequence
  announced_at
  source_published_at
  received_at
  comment

corporate_action_date
  corporate_action_date_id
  corporate_action_id
  date_role                     -- EX / RECORD / PAYABLE / EFFECTIVE / ELECTION_DEADLINE
  date_or_timestamp
  timezone                      -- required when the value is a timestamp

corporate_action_effect
  corporate_action_effect_id
  corporate_action_id
  effect_type                   -- CASH / SECURITY / QUANTITY_CHANGE / REPLACEMENT
  target_reference_node_id      -- nullable for pure cash effect
  ratio
  cash_amount
  currency_id
  rounding_rule

market_data_adjustment_factor
  adjustment_factor_id
  corporate_action_id
  raw_market_data_series_id
  derived_market_data_series_id
  adjustment_basis              -- SPLIT_ADJUSTED / PRICE_RETURN / GROSS_TR / NET_TR
  effective_date
  factor
  calculation_method
```

Use controlled event types aligned with an industry taxonomy such as ISO corporate-action event codes, while keeping the first internal list small. A source update must create a new `n_sequence` rather than overwrite an earlier announcement.

Corporate-action dates are event data, not `instrument_dates`: an instrument has one issue date; it can have many dividends, splits, and elections.

An event can produce multiple effects. A merger may deliver acquirer shares plus cash; a spin-off delivers a new security; a split changes the holder's quantity. This is why effects are rows, not columns on `corporate_action`.

## Raw historical prices versus adjusted history

Raw prices are immutable source facts. Never overwrite an original venue close with a split-adjusted or dividend-adjusted value.

```text
RAW_OFFICIAL_CLOSE             -- source fact as supplied for its market date
SPLIT_ADJUSTED_CLOSE           -- removes split/reverse-split discontinuities
PRICE_RETURN_INDEX             -- price performance; no ordinary-dividend reinvestment
GROSS_TOTAL_RETURN_INDEX       -- distributions reinvested before withholding tax
NET_TOTAL_RETURN_INDEX         -- distributions reinvested after stated tax assumptions
VENDOR_ADJUSTED_CLOSE          -- vendor-defined method; never assumed equivalent to another basis
```

"Adjusted close" is not a sufficient controlled meaning. The derived series must carry its adjustment basis, calculation method/version, and source.

### The AMZN historical-download rule

When a vendor download made today returns older AMZN prices, those prices may already have been restated for historical stock splits, dividends, or another vendor-specific methodology. **Do not decide whether to apply corporate-action factors from our `received_at` timestamp.** It only says when our platform obtained the file; it does not prove what basis the vendor applied.

Store explicit provenance on every observation or ingestion batch:

```text
market_data_observation
  market_date                   -- date the quote represents
  observed_at                   -- venue/vendor observation timestamp where known
  source_published_at           -- source release timestamp where supplied
  received_at                   -- platform ingestion timestamp
  value_basis                   -- RAW / SPLIT_ADJUSTED / VENDOR_ADJUSTED / DERIVED
  adjustment_set_id             -- required when known and adjusted
  source_snapshot_id            -- identifies the vendor extract/vintage
```

The application rule is:

```text
If value_basis is RAW:
  derive an adjusted series using the applicable corporate-action adjustment set.

If value_basis is SPLIT_ADJUSTED, VENDOR_ADJUSTED, or DERIVED:
  do not apply the same corporate-action factor again.
  Preserve the declared adjustment methodology and source snapshot.
```

For example, a downloaded AMZN 2019 close received today may be `SPLIT_ADJUSTED` for a 2022 stock split. It is a valid contemporary vendor history, but it is not necessarily the price that was known in 2019.

## Two valid historical questions

These must be supported separately:

| Question | Required data |
|---|---|
| "Give me today's vendor-restated history." | Latest vendor snapshot, with declared adjusted/raw basis. |
| "What value was known on 31 December 2019?" | Point-in-time source vintage received/published no later than that timestamp. |

The latter requires retaining source snapshots/vintages captured at the time. A vendor's current historical backfill cannot reconstruct the historic information set merely from the observation's market date.

For historical P&L/backtesting, select data by `source_published_at`/vintage as-of time, not by current restated history. For normal performance reporting, use the explicitly selected split-adjusted, price-return, gross-total-return, or net-total-return series.

## Implemented point-in-time derivation boundary (V1)

`security_master_schema.corporate_action_service` now provides read-only
derivation helpers. `derive_adjusted_observation` accepts only an observation
whose `value_basis` is `RAW`; it returns a calculated value and ordered factor
lineage without updating that observation. A factor applies only when its
corporate action is `CONFIRMED` or `COMPLETED`, its action record existed on or
before the requested timezone-aware information cut, and its effective date is
after the raw observation's market date.

`derive_adjusted_position` likewise returns a calculated quantity from the
immutable position snapshot. It considers confirmed quantity-changing effects
whose effective date is no later than the snapshot date and whose event record
was available by the requested information cut. It supports split/bonus-style
ratio effects; custody movements, elections, tax and cash postings remain
separate operating domains.

This is deliberately not a write-back mechanism or a claim that a current
vendor-restated history was available historically. Persisted derived series and
positions, if later required for performance scale, must retain method/version,
factor/event lineage, and their own immutable creation timestamp.

## Position and derivative implications

Original trades remain immutable. A split, dividend, or spin-off later generates a distinct lifecycle/custody posting or position transformation when that domain is built.

Corporate actions can also change listed-derivative terms. Retain a simple V1 link:

```text
derivative_contract_adjustment
  corporate_action_id
  affected_derivative_instrument_id
  effective_date
  resulting_derivative_instrument_id
  source_reference
  note
```

When adjusted derivatives are in operational scope, extend this with strike/premium multipliers and a deliverable-component table for cash, shares, warrants, rights, and cash in lieu. Do not assume that every adjusted listed option remains a contract on exactly 100 ordinary shares.

## Vintage-aware adjustment rule

Vendor-restated prices and corporate-action-adjusted histories must carry their
source vintage and information-cut semantics. A price's `market_date` answers
which economic day it represents; `received_at_utc` and the linked
`market_data_vintage` answer when that fact became available. For replay at a
historic cut, select only observations/vintages knowable by that cut, then
apply the corporate-action event/effect that was itself knowable by the same
cut. Do not treat a vendor's present-day split-adjusted history as evidence of
what was knowable at the original date. Derived series retain the raw-series
ID, corporate-action state, method, and calculation version; raw observations
are never overwritten.
