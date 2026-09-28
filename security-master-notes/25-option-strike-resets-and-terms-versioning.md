# Option strike resets and terms versioning

## Decision

A vanilla option with a contractual strike that changes on scheduled dates remains
one economic instrument when it is one legal contract. The static definition and
the scheduled determination process are separate records:

```text
one stable option instrument
  -> versioned static option terms
      -> strike-reset schedule and ordered events
          -> reset rules
              -> immutable strike fixings
```

Every strike reset is therefore **not** a new `option_terms` version. A terms
version is created only when the legal/static contract definition is corrected
or amended.

## Why this matches external standards

FpML models a strike as a price or percentage and separately supports a
`strikeDeterminationDate` for a forward-starting option. That is evidence for
representing a future strike as a determination event rather than mutating a
current strike field. See [FpML EquityStrike](https://www.fpml.org/spec/fpml-5-8-6-tr-1/html/recordkeeping/schemaDocumentation/schemas/fpml-eq-shared-5-8_xsd/complexTypes/EquityStrike.html)
and [FpML strikeDeterminationDate](https://www.fpml.org/spec/fpml-5-10-5-rec-1/html/confirmation/schemaDocumentation/schemas/fpml-eq-shared-5-10_xsd/complexTypes/EquityStrike/strikeDeterminationDate.html).

The [ISDA glossary](https://www.isda.org/?p=6823) describes a cliquet as
consecutive forward-starting options whose strikes are determined from prior
settlement levels. This supports the schedule/rule/fixing split. The internal
model remains normalized rather than reproducing FpML XML.

## Terms versions versus event order

`secm.option_terms` now has a surrogate `option_terms_id`, increasing
`version_no`, effective dates, status, `is_current`, and an optional
`supersedes_option_terms_id`. The stable `instrument_node_id` remains the
economic identity.

`is_current` is an operational convenience pointer. An as-of query must still
select the approved version whose effective period contains the valuation date;
`is_current` alone is not historical version resolution.

The following fields have different meanings and must not be conflated:

| Field/row | Meaning | Versioned? |
|---|---|---:|
| `option_terms.version_no` | Static/legal terms correction or amendment | Yes |
| `schedule_event.event_sequence` | Ordering of contractual dates | No |
| `option_strike_reset_rule` | Method and bounds for one reset event | Belongs to terms version |
| `option_strike_fixing` | Actual strike determined from an event | Immutable fact; corrections supersede |

## Implemented tables

### `secm.option_terms`

Static option economics include option type, exercise style, underlying,
settlement, currencies, and strike basis. The new `strike_mode` values are:

- `FIXED`: `strike_value` is the contractual strike.
- `FORWARD_START`: the first strike is determined at a future scheduled event.
- `RESET`: an initial strike may apply and later scheduled events replace it.

`strike_reset_schedule_id` points to `secm.schedule`. Reset dates are not
duplicated in the terms row.

### `secm.option_strike_reset_rule`

One row describes how one schedule event determines the strike:

- `FIXED`;
- `SPOT_AT_RESET`;
- `FORWARD_AT_RESET`;
- `PREVIOUS_FIXING`;
- `FORMULA` (catalogued but deliberately not evaluated in this slice).

The row can carry a market-data series, reference node, strike basis, fixed
value, floor, and cap. `schedule_event.event_sequence` remains the ordering
authority.

### `secm.option_strike_fixing`

For market-derived methods, the resolved strike is stored with its fixing date,
source observation, market-data resolution snapshot, status, and correction
lineage. A correction creates a new row and marks the prior row superseded;
the original value is never overwritten.

## Resolution rule

For an as-of date:

1. Select the approved `option_terms` version effective on that date.
2. Select reset events whose event date is on or before the as-of date.
3. Order events by event date and `event_sequence`.
4. Use a fixed rule value or exactly one accepted fixing.
5. Apply any floor/cap from the reset rule.
6. Fail closed for a missing or ambiguous market-derived fixing.
7. Persist the market-data resolution snapshot used to produce the fixing.

The pure resolver in `security_master_schema/option_strike_resolver.py` implements
this deterministic selection without fetching data or mutating database rows.

## When this is not one option

If each period is legally a separate option, settles independently, or has an
independent payoff, model a composed parent with separate child instruments or
payoff components. Do not hide separate legal contracts inside reset rules.

## Deferred choices

- Formula reset evaluation requires a governed formula vocabulary and versioned
  calculation implementation; `FORMULA` currently fails closed.
- Cross-table validation that a reset rule's `schedule_event_id` belongs to the
  option's `strike_reset_schedule_id` remains an application/approval check.
- A generic version envelope for futures, swaps, and other one-row terms tables
  is deferred until those products need amendment history; no broad refactor is
  implied by this option slice.
- Terms-version overlap exclusion constraints and database-enforced approval
  transitions remain a later hardening step.
