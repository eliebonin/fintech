# Derivatives, futures, and swaps

## Asset-specific terms

Common identity belongs in `instrument`. Contract-specific data belongs in
focused terms tables keyed by the economic instrument node; when contractual
amendments need history, the terms table has multiple effective-dated versions
behind the same instrument UUID.

```text
bond_terms
option_terms
future_terms
fx_forward_terms
swap_terms
structured_product_terms
fund_share_class_terms
```

Use `x_terms` for data defining one exact economic instrument.

Use `x_family` only where one non-tradeable product specification groups multiple separately tradeable instruments.

## Fund and share-class boundary

A fund, umbrella or sub-fund is a non-tradeable reference object in `secm.fund`.
It may carry legal form, domicile, manager and a parent-fund link. A share class
is a separate `FUND_SHARE_CLASS` economic instrument because it has its own
identifier, currency, NAV, dealing, trade and holding characteristics.

`secm.fund_share_class_terms` is effective-dated and versioned. It holds the
fund relationship, income treatment, share currency, dealing and NAV frequency,
and expected official NAV publication lag. Publication lag describes reference
data; it does not hard-code valuation selection. The tenant valuation policy
still decides whether to use a T-1 official NAV or another permitted input.

## Bond terms boundary

`secm.bond_terms` is also effective-dated and versioned. It holds issue
currency, par amount, coupon type/rate/frequency, day-count convention,
redemption amount and quotation basis. Coupon cashflows belong in the dedicated
schedule tables, not as repeated generic term rows.

`quotation_basis` such as `PCT_OF_PAR` is deliberately distinct from a listing
`quote_factor`: a percentage-of-par bond price needs nominal/accrual logic; it
is not a GBX-to-GBP display conversion.

## Future families

A `future_family` is a non-tradeable contract template. It may contain underlying, standard multiplier, expiry cycle, contract currency, settlement convention, and exchange rulebook.

Each expiry is a separate future economic instrument because it has its own maturity, last-trade date, settlement date, price, trade, and position.

```text
future_family
  Example Equity Index Future
    |
    +-- future instrument: March 2027
    |     +-- listing: XEUR
    |
    +-- future instrument: June 2027
          +-- listing: XEUR
```

`future_terms.future_family_id` links the future contract to the family. A continuous future is a derived market-data series with a roll rule, not a tradeable instrument.

## Product taxonomy

ABC, XYZ, and FOO are internal business labels, not peer canonical instrument types. Store them in an internal taxonomy:

```text
product_taxonomy
  product_type_id, taxonomy, code, name

instrument_product_classification
  instrument_node_id, product_type_id, classification_role, valid_from, valid_to
```

An instrument can independently receive canonical, internal, risk, and regulatory classifications.

## Swap model

The canonical swap model is leg-based:

```text
swap_terms
  instrument_node_id              -- the swap contract
  swap_type                       -- TOTAL_RETURN, INTEREST_RATE, etc.

swap_leg
  swap_leg_id
  swap_instrument_node_id
  leg_number
  leg_role                        -- PERFORMANCE, FUNDING, COUPON, PROTECTION
  pay_receive
  reference_node_id
  spread                          -- decimal rate: 0.015 = 1.50% = 150 bps
  currency
  schedule_id                     -- reset, fixing, observation or payment schedule
```

This supports simple two-leg financed swaps and later extension to baskets, multiple funding legs, fees, protection legs, and restructurings.

### Initial governed swap slice

The first operational scope is total-return and funded swaps. A
`PERFORMANCE` leg requires both a `reference_node_id` and a
`return_profile_id`. A `FUNDING` leg requires a reference rate node and a
currency. Every leg is expressed from the holder's perspective using `PAY` or
`RECEIVE`.

`swap_leg.spread` is always stored as a decimal rate: `0.015` means 1.50% or
150 basis points. No separate unit column is needed while this convention is
strictly enforced.

The common `secm.instrument_dates` record is the sole authority for swap
effective and maturity dates. `swap_terms` deliberately contains no duplicate
effective or termination date columns. Use `effective_date`, `maturity_date`,
and settlement dates on the common date record.

The swap trade carries the signed notional in its existing `quantity` field.
For the initial total-return scope, positive quantity means the holder receives
the performance leg; negative quantity means the inverse. Reset, coupon,
termination, and other cash events remain separate `trd.trade` rows that point
back to the originating swap through `reference_instrument_node_id`.

Existing `info_swaps` fields map as follows:

| Existing field | Canonical interpretation |
|---|---|
| `instrument_id` | The swap economic instrument node. |
| `funded_instrument_id` | Performance reference node. |
| `funding_instrument_id` | Funding reference node. |
| `spread` | Funding-leg spread. |

The existing simple shape can be exposed as an `info_swaps` view derived from `swap_leg` rows.

## Listing-specific performance

A leg on a named listing must reference the listing node, not just the economic instrument. The leg also needs return type, observation rule, calendar, currency/FX rule, and corporate-action treatment.

If the term sheet names only the economic instrument, reference its instrument node and specify a deliberate composite/primary-market valuation policy.

## Structured products

Structured products are parent economic instruments. Their contractual payoff is explained by a composition of actual payoff-option components, condition groups, atomic barrier rules, ordered actions, and schedules. The authoritative barrier model is [structured-product condition groups](26-structured-product-condition-groups.md).

```text
Parent structured product
  |
  +-- composition: actual payoff components
  |     digital coupon options, calls, puts, caps, KIPs, etc.
  |
  +-- parent barriers: lifecycle/product events
        autocall, final redemption, capital-protection conditions
```

`instrument_composition.composition_value` is the numeric value applied to a
component occurrence. Its companion `composition_value_kind` removes the
ambiguity of the old `composition_rate` name:

* `SIGNED_MULTIPLIER`: `+1` long, `-1` short, and a larger magnitude for
  leverage/participation;
* `PERCENT_WEIGHT`: percentage points used for weighted constituents;
* `QUANTITY`: a contractual number of units; and
* `NOTIONAL_AMOUNT`: an amount whose currency/basis is supplied by the
  component terms.

`component_sequence` is unique within a parent terms version. The optional
`structured_product_terms_id` and `source_payload_id` retain the contractual
version and source lineage. Values use `NUMERIC`, never `FLOAT`.

### Barriers and actions

Barrier rules describe atomic conditions; condition groups own observation and
Boolean semantics; group actions describe the consequences.

```text
structured_product_condition_group
  terms version, observation style/event, logical operator, underlying scope,
  evaluation sequence

barrier_rule
  condition group, owner node, resolved underlying node, comparison operator,
  level basis and level, underlying measure, member sequence

condition_group_action
  condition group, action type, target scope/node, optional target composition,
  payout amount/rate/currency, payment timing/schedule, execution sequence
```

Typical actions are `PAY_COMPONENT`, `REDEEM_PARENT`, `TERMINATE_PARENT`, `CANCEL_FUTURE_COMPONENTS`, and `ACTIVATE_CAPITAL_PROTECTION`.

* Coupon barriers attach to coupon option components because they determine
  component payment.
* Autocall barriers attach directly to the parent product because they alter
  the parent lifecycle; the action targets `PARENT` and no dummy autocall
  option is required.
* KIP/downside barriers attach to the relevant downside component, or to the
  parent when the contractual payoff is parent-level.
* The rule stores the resolved underlying node for deterministic historical
  evaluation. Component rules are validated against child option terms;
  parent rules are resolved from explicit parent composition/reference rows.

The detailed ownership, target-composition, and versioning rules are in
[structured-product condition groups](26-structured-product-condition-groups.md).

### Coupons and memory

Coupon memory is product/coupon-program behaviour, not a generic barrier attribute. A coupon programme points to its eligibility barrier or condition group and defines `payment_mode`, `memory_mode`, and final-payment treatment.

```text
payment_mode: PERIODIC / ON_AUTOCALL / ON_MATURITY
memory_mode: NONE / CONDITIONAL_CATCH_UP / ACCUMULATE_TO_REDEMPTION
```

* A Phoenix may pay periodic coupons and optionally catch up unpaid coupons when a later coupon condition succeeds.
* An Athena normally accumulates its premium and pays it on autocall redemption or the applicable maturity scenario; it does not normally pay independent interim coupons.

### Product patterns

| Product | Parent and composition pattern |
|---|---|
| Autocall | Coupon digital-option components plus parent autocall barriers/actions. |
| Phoenix | Coupon components/barriers, optional memory, and separate autocall terms when applicable. |
| Athena | Parent autocall barriers trigger redemption plus accumulated premium; optional KIP/downside component. |
| Supertracker | Principal redemption plus leveraged upside call, optional negative cap call, and negative KIP/downside put. |
| Range accrual | Internal range-accrual coupon component with periods, an explicit observation convention/accrual basis, and one `IN_RANGE` group containing lower and upper conditions. |

Range accrual must not materialise a separate daily digital-option instrument for every observation. Its coupon amount is driven by the proportion of observations satisfying both the lower and upper conditions. The focused `secm.structured_product_range_accrual_terms` row stores the frequency, denominator basis, non-business-day rule, boundaries, and annualised rate; the detailed fixing/outcome ledger is a lifecycle concern.

Supertracker uses `secm.structured_product_supertracker_terms` for the
positive participation multiplier and optional underlying-return cap. The
contractual graph carries the long upside call, optional short cap call, any
separate KIP/downside component, and a parent maturity redemption action.

## Composed options

The composition model is also the canonical representation for OTC call spreads, straddles, butterflies, condors, ratio spreads, and related package options.

```text
OTC composed option parent
  +-- option components and signed composition rates
```

| Strategy | Component rates |
|---|---|
| Long straddle | Call `+1`, put `+1` at the same strike. |
| Call spread | Lower-strike call `+1`, upper-strike call `-1`. |
| Call butterfly | Calls at K1 `+1`, K2 `-2`, K3 `+1`. |
| Ratio spread | Long call `+1`, short calls `-2`. |

An OTC composed option is one legal/economic parent instrument and can receive an issuer quote at the parent node. A listed strategy is different: it is a trade package containing separately booked trade legs, each pointing to its own listed option node and market data.

```text
Listed call spread package
  +-- buy listed call K1
  +-- sell listed call K2
```

ETF PCFs and custom-basket constituents are not contractual payoff composition. They require separate dated constituent-snapshot tables with weights/quantities and `as_of_date`.

## Vanilla options: first canonical slice

The initial option implementation is intentionally limited to ordinary
vanilla CALL and PUT contracts. `secm.option_terms` is versioned static
contract data for the economic option; the stable `instrument_node_id` remains
the economic identity. The common `secm.instrument_dates` row owns effective,
expiry, maturity, and final-settlement dates. A venue representation is still a
separate `secm.listing` row when the option is exchange traded.

```text
option_terms
  underlying_reference_node_id  -- exact listing, instrument, index, future, or FX pair
  option_type                   -- CALL or PUT
  exercise_style                -- EUROPEAN, AMERICAN, BERMUDAN
  strike_mode                   -- FIXED, FORWARD_START, RESET
  strike_value + strike_basis  -- static value or initial/reference value
  strike_reset_schedule_id      -- schedule for future strike determination
  strike_currency_id           -- required for monetary strikes
  premium_currency_id          -- optional quoting/convention currency
  settlement_method             -- CASH, PHYSICAL, ELECTION, CASH_OR_PHYSICAL
  settlement_currency_id       -- required for cash settlement
  exercise_schedule_id          -- required for BERMUDAN
```

The internal `BERMUDAN` code maps to FpML's spelling `Bermuda`. Strike
currency is not inferred from the option's base or trading currency. A cash
settlement currency is explicit. Contract entitlement/multiplier (for example,
100 shares per equity option or USD 50 per index point) belongs in the
effective-dated `secm.instrument_contract_unit_terms` table, not in the
option terms row. Actual premium amount and payment event are trade-level
economics and are deliberately not duplicated in the canonical instrument
row.

The terms table is source/staging tolerant, while canonical activation uses
the option validation contract. The validator rejects non-vanilla values,
missing monetary-strike currencies, missing cash-settlement currencies, and a
Bermudan option without a dated exercise schedule. Forward-start and reset
strikes are represented by `secm.option_strike_reset_rule` rows tied to
`secm.schedule_event` dates, with market-derived results in immutable
`secm.option_strike_fixing` rows. A reset event is not a new terms version.
Digital, barrier, Asian, quanto, and other exotic payoff features remain
separate extensions; they must not be encoded by overloading `option_type`.
The first structured-product composed-option templates now use the dedicated
component/condition extension described in the [structured-product terms
note](27-structured-product-terms-and-coupon-memory.md): digital semantics are
carried by component terms, while a KIP is a separate barrier component.

See the detailed [option strike reset and terms-versioning note](25-option-strike-resets-and-terms-versioning.md).

This shape follows the narrow convention described by the standards rather
than reproducing their XML: FpML describes vanilla put/call options, American,
European and Bermuda exercise, single/basket underlyings, strike currency,
cash/physical delivery, and optional premium components. ISDA definitions use
the same exercise-period concepts. Exchange specifications additionally show
that an option can reference a specific future contract and that multiplier,
expiry, settlement, and exercise style are product-specific.

See [FpML equity-option architecture](https://www.fpml.org/spec/fpml-5-1-6-rec-1/html/reporting/fpml-5-1-intro-8.html),
[FpML exercise and settlement schema](https://www.fpml.org/spec/fpml-5-11-7-rec-1/html/transparency/schemaDocumentation/schemas/fpml-eqd-5-11_xsd/complexTypes/EquityExerciseValuationSettlement.html),
[ISDA 2000 Definitions](https://www.isda.org/book/2000-isda-definitions-pdf),
[CME strike-price convention](https://www.cmegroup.com/education/courses/introduction-to-options/what-is-exercise-price-strike.hideHeader.hideFooter.hideSubnav.hideAddThisExt.educationIframe.html),
and [CME European options on E-mini futures](https://www.cmegroup.com/education/articles-and-reports/e-mini-sp-500-quarterly-pm-options-european-style-faq.html).

The standards are evidence for the controlled concepts, not a mandate to
copy FpML's interchange structure into PostgreSQL. Raw FpML/FIX confirmations
remain boundary payloads mapped into the normalized terms and schedule tables.
