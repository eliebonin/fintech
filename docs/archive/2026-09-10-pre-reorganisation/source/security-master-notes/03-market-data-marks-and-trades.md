# Market data, marks, and trades

## Evidence status

The common series catalogue, immutable observations, explicit valuation cuts,
and separate marks are internal architecture decisions aimed at reproducible
valuation. They are not a claim that every vendor or accounting platform uses
the same tables. Provider correction, finality, and entitlement semantics must
be documented per dataset; see the [external evidence and research register](24-external-evidence-and-research.md).

## One security-price table

Use one `security_price` table. Every price references one `financial_reference_node_id`.

```text
security_price
  security_price_id
  financial_reference_node_id
  as_of_timestamp
  price_type
  price_value
  price_currency
  source_id
  source_timestamp
  quality_status
```

## Price-placement rule

| Observation | Reference node |
|---|---|
| Official venue close, venue last, bid, ask, volume | Listing node |
| OTC evaluated bond price | Economic-instrument node |
| Vendor composite price | Economic-instrument node |
| Internal end-of-day mark | Economic-instrument node |
| FX, curve, rate-index, index-level observation | Its dedicated reference node |

There is no natural single close for a cross-listed equity. An XLON close and XPAR close must remain separate listing-level observations. A selected or calculated instrument-level value must state its price type and lineage.

Suggested controlled price types:

```text
OFFICIAL_VENUE_CLOSE
VENUE_LAST
COMPOSITE_CLOSE
EVALUATED_CLEAN_PRICE
INTERNAL_EOD_MARK
```

## Trades

One `trade` row is one booked economic event / actual execution. It is not an order or a generic multi-leg container. An OTC composed option or structured product is one economic parent instrument and is correctly booked as one row with one price. A listed option strategy may later use a trade package with separately booked rows, but this is deliberately outside the initial trade model.

Use a UUIDv7 `trade_id` as the immutable internal primary key. Preserve upstream trade identifiers in a separate reference table; do not make an external system's mutable or non-global string the primary key.

```text
trade
  trade_id UUIDv7
  trade_subject_reference_node_id      -- the booked instrument, listing, or cash currency
  reference_instrument_node_id nullable -- instrument causing a related cash event

  trade_type                           -- economic event type
  trade_purpose nullable                -- INVESTMENT, HEDGING, REBALANCING, ...
  market_activity nullable              -- PRIMARY, SECONDARY
  strategy_id                           -- primary portfolio / ledger

  execution_price
  price_basis                           -- UNIT_PRICE, PCT_OF_PAR, CLEAN, DIRTY, RATE, ...
  price_currency_id
  quantity
  quantity_unit

  trade_datetime_utc
  instruction_date nullable
  settlement_date nullable

  trader_person_id nullable             -- commercial decision maker; internal or external
  booked_by_user_account_id              -- authenticated internal user/system actor
  execution_channel                     -- FIX, MANUAL_UI, API, FILE_IMPORT, EMAIL, PHONE
  source_system_id nullable
  source_received_at_utc nullable
  execution_venue_id nullable
  dealing_capacity nullable              -- PRINCIPAL, AGENT, DISTRIBUTOR, INTRODUCER

  lifecycle_status                      -- BOOKED, CANCELLED, SUPERSEDED, VOID
  created_at_utc
  created_by_user_account_id
  comment nullable
```

For an ordinary execution, `trade_subject_reference_node_id` is the traded security or listing. For a related cash booking, it is the cash currency and `reference_instrument_node_id` names the originating instrument. The `trade_type` establishes the meaning of that relationship.

| Trade type | Trade subject | Reference instrument |
|---|---|---|
| `DIVIDEND` | Cash currency | Equity or fund paying it |
| `COUPON` | Cash currency | Bond or structured product |
| `RESET` | Cash currency | Swap |
| `CASH_FLOW` | Cash currency | Originating instrument, when relevant |
| `INVESTMENT` / market execution | Traded instrument or listing | Normally null |

Identity examples:

* OTC bond, swap, FX forward, bespoke option, or structured product: the subject is the economic instrument.
* Exchange-traded equity, ETF, future, or listed option: the subject is normally the listing node, which resolves to the economic instrument.

### Trade classification

Keep `trade_type` for what happened: `INVESTMENT`/`MARKET_EXECUTION`, `SUBSCRIPTION`, `REDEMPTION`, `DIVIDEND`, `COUPON`, `RESET`, `CASH_FLOW`, `FEE`, or `TRANSFER`.

Do not overload it:

* Forward hedging is a `trade_purpose` of `HEDGING`, potentially with a hedge scope (fund or share class).
* `PRIMARY` and `SECONDARY` are `market_activity` values.
* A Bed-and-ISA workflow is a `trade_group` linking multiple genuine trades.
* P&L is a valuation/accounting result, never a trade.

### Parties, external references, and specialised details

Use `trade_party_role` instead of overloading direct client, counterparty, and agent fields:

```text
trade_party_role
  trade_party_role_id
  trade_id
  organisation_id or person_id
  role                                  -- CLIENT, COUNTERPARTY, EXECUTING_BROKER,
                                        -- CUSTODIAN, SETTLEMENT_AGENT, DISTRIBUTOR,
                                        -- ADVISER, SUBSCRIBER_REDEEMER, MONITORED_CLIENT
```

`trader_person_id` represents the real human trader, including an external person. `booked_by_user_account_id` represents the Auth0-backed internal account or service that entered the record. These must remain separate.

```text
trade_external_reference
  trade_external_reference_id
  trade_id
  source_system_id nullable
  trade_party_role_id nullable
  reference_type                         -- SOURCE_TRADE_ID,
                                         -- AGENT_SUBRED_REFERENCE, BASKET_REFERENCE
  reference_value
  source_received_at_utc nullable
```

The agent-provided subscription/redemption booking number is an `AGENT_SUBRED_REFERENCE`, associated with the relevant agent/custodian party role.

Keep genuinely specialised execution facts outside the universal row:

```text
trade_fixed_income_execution
  trade_id
  locked_ytm
  dirty_price
  accrued_interest nullable

trade_bucket_assignment
  trade_id
  bucket_id
  bucket_role                            -- TOP_LEVEL, INVESTMENT, WRAPPER

trade_tag_assignment
  trade_id
  tag_id
```

The historic `fund_id` is retired in favour of `strategy_id`. A fund share class is itself an instrument, so a subscription/redemption points to that share-class instrument rather than needing a dedicated `shareclass_id` column.

### Cash balances

Cash balances are economically important strategy positions and drive FX P&L, but they are states rather than executions. Store them in a dedicated, trade-shaped snapshot table, not as `CASH_BALANCE` rows in `trade`:

```text
cash_balance
  cash_balance_id
  strategy_id
  currency_id
  cash_account_id nullable
  balance_as_of_date
  balance_as_of_datetime_utc
  balance_type                           -- SETTLED, AVAILABLE, LEDGER, MARGIN
  amount
  source_system_id
  source_reference
  received_at_utc
  status                                 -- ACTIVE, SUPERSEDED, REJECTED
  created_by_user_account_id
```

Each row is the full balance for `strategy + currency + cash account + balance type + as-of time`; it is not a cash movement and must not be accumulated across dates. The position resolver selects the latest valid snapshot for a requested date. It combines security holdings from active trade events with these cash positions. Daily FX P&L is then calculated from the currency balance and the selected FX mark, while cash movements are explained separately.

### Client execution, distribution, and fees

Client business uses the same trade row. Add the client, broker/custodian, and distribution roles via `trade_party_role`, and capture execution provenance on the main row (`execution_channel`, source system, and venue).

Fees are a child table because one trade can carry several charges or revenues. In the normal distribution case, the issuer pays the distribution fee to the firm's legal entity; the client is not the payer.

```text
trade_fee
  trade_fee_id
  trade_id
  fee_type                              -- DISTRIBUTION, TRAILER, BROKERAGE,
                                        -- EXCHANGE, CUSTODY, TAX, OTHER
  fee_payer_org_id                      -- normally issuer for distribution revenue
  fee_recipient_org_id                  -- normally the firm's legal entity
  fee_amount                            -- persist the monetary amount
  fee_currency_id
  fee_rate nullable
  fee_rate_unit nullable                -- BPS, PCT
  fee_basis                             -- GROSS_CONSIDERATION, NOTIONAL, NAV, FIXED
  accrual_date nullable
  settlement_date nullable
  status                                -- EXPECTED, CONFIRMED, PAID, WAIVED, CANCELLED
  external_reference nullable
```

The instrument's issuer relationship can help propose the fee payer, but `fee_payer_org_id` is stored explicitly because a guarantor, platform, fund manager, or another entity may actually owe the fee. If fee accounting later needs independent cash postings, create them downstream from `trade_fee`; do not create a second investment trade merely to represent fee income.

## Marks

A mark is a valuation result, not raw market data. It should record the valued trade or position, as-of time, valuation method, selected inputs/snapshot, value, currency, status, and input lineage. Marks must not overwrite raw or official observations.

The tenant-scoped `nav.valuation_mark` table is the generic audit record for
this conclusion. It requires exactly one evidence route: an immutable
`md.market_data_resolution_snapshot` selected under the tenant's entitlement
and valuation policy, or an explicitly approved tenant override. It also stores
the valuation date, named cut, UTC information cutoff, method/calculation
version, subject, optional strategy/position/trade scope, value, currency, and
review status. A later correction creates a new mark; it never edits the mark
or its selected observation. An approved administrator mark, model price, or
private-asset valuation therefore fits the same record without being confused
with a raw market-data observation.

The `approved_override_id` is intentionally a typed UUID placeholder in this
slice. A dedicated tenant override/evidence table and its approval workflow are
deferred until override categories and entitlement semantics are finalized.

## Soft NAV: calculation inputs are an immutable audit snapshot

A Soft NAV uses ordinary market-data series and observations as its source, but it must not query the currently latest values again when an old run is reviewed. Persist the resolved inputs in a dedicated tenant-scoped audit model.

```text
nav_calculation_run
  -> nav_input_snapshot
       -> nav_input_snapshot_item
  -> nav_valuation_line
  -> nav_result / nav_reconciliation
```

`nav_input_snapshot_item` records the subject node, selected series and observation where one exists, selected value and currency, source, policy rule, selection reason, and any approved tenant override. For market-data inputs it also freezes the requested pricing date, actual market date used, staleness outcome, and the direct market-data resolution item. It links to a `portfolio_snapshot`, a cash-balance snapshot, a NAV-policy version, a corporate-action state, and a calculation-code version through the run/header. See [Soft-NAV pricing-date resolution](17-soft-nav-pricing-date-resolution.md).

The snapshot is append-only. A later vendor correction, changed policy, or approved model-price override creates a new calculation run and new snapshot; it never edits the historic Soft-NAV evidence. Soft NAV is an indicative operational result with statuses such as `DRAFT`, `REVIEWED`, `APPROVED`, `REJECTED`, and `SUPERSEDED`; it is not automatically the official administrator NAV.

## Querying policy

Price selection must be explicit. For a listed position, use the specified listing price unless a named valuation policy permits a composite or internal instrument-level fallback. For an OTC position, use the instrument-level observation selected by policy.

## Trade drill-down read model

The operations API exposes `GET /v1/trades` as a read-only catalogue of
`BOOKED` executions and `GET /v1/trades/{trade_id}` as the evidence view for a
single execution. The detail response composes the base trade with:

* `trd.trade_party_role` for client, counterparty, custodian, executing broker,
  distributor, and other organisation/person roles;
* the trade's explicit `trader_person_id` and `booked_by_user_account_id`;
* `trd.trade_external_reference` for source or agent references;
* `trd.trade_fee` for payer, recipient, amount, rate, basis, and fee status; and
* `trd.trade_lifecycle_event` for the append-only booking/correction timeline.

This avoids adding a proliferation of nullable party columns to the trade
table. The seeded MVP uses synthetic organisations and people to exercise each
role; missing production evidence must display as missing, never be inferred
from the instrument issuer.
