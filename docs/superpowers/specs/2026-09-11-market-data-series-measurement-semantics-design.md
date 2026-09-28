# Market-data series measurement semantics design

**Status:** Proposed  
**Owner:** Market-data and valuation architecture  
**Date:** 2026-09-11

## Objective

Give every `md.market_data_series` a governed definition of what an observation measures and how a normal period-on-period movement should be expressed. This makes price returns, volatility-point movements, yield/spread basis-point movements, and quantity changes explicit without changing immutable raw observations.

## Decision

Add the governed catalogue `md.series_measure_definition` and require `md.market_data_series.measure_definition_id` for newly created series after data backfill. Keep `market_data_series.series_type` and `value_type` during the transition: they remain useful source-stream and legacy-shape descriptors, but are not the authoritative analytic semantics.

### Catalogue contract

`md.series_measure_definition` owns:

| Field | Meaning |
| --- | --- |
| `measure_code` | Stable semantic code, e.g. `PRICE`, `FX_RATE`, `IMPLIED_VOLATILITY`, `YIELD`. |
| `display_name` / `description` | Governed human-readable meaning. |
| `unit_type` | The unit category, e.g. `CURRENCY_PRICE`, `PERCENT`, `BASIS_POINTS`, `INDEX_POINTS`, `QUANTITY`. |
| `default_change_method` | Normal analytical movement: `RELATIVE_RETURN`, `ABSOLUTE_CHANGE`, `BASIS_POINT_CHANGE`, or `MONETARY_CHANGE`. |
| `change_display_unit` | Unit presented for that change, e.g. `PERCENT`, `VOLATILITY_POINTS`, `BASIS_POINTS`, `PIPS`, `UNITS`. |
| `display_decimal_places` / `change_decimal_places` | Default presentation precision; never a storage-scale constraint. |
| `status` / `sort_order` | Governed lifecycle and presentation order. |

`market_data_series.measure_definition_id` references this catalogue. The source series continues to determine cut, venue/data source, currency, dimensions, series type, and official status.

## Initial semantics

| `measure_code` | Typical series | Default movement |
| --- | --- | --- |
| `PRICE` | listed close, evaluated bond price | `RELATIVE_RETURN` displayed as percent |
| `FX_RATE` | GBP/USD spot | `RELATIVE_RETURN` displayed as percent |
| `INDEX_LEVEL` | equity index level | `RELATIVE_RETURN` displayed as percent |
| `NAV` | fund share-class NAV | `RELATIVE_RETURN` displayed as percent |
| `IMPLIED_VOLATILITY` | 1Y ATM FX implied volatility | `ABSOLUTE_CHANGE` displayed as volatility points |
| `YIELD` | bond yield | `BASIS_POINT_CHANGE` displayed as basis points |
| `RATE` | zero/coupon rate | `BASIS_POINT_CHANGE` displayed as basis points |
| `CREDIT_SPREAD` | CDS or OAS | `BASIS_POINT_CHANGE` displayed as basis points |
| `VOLUME` / `OPEN_INTEREST` | exchange activity | `ABSOLUTE_CHANGE` displayed as units |
| `MONETARY_VALUE` | monetary MTM | `MONETARY_CHANGE` displayed in currency |

`PIPS` is a presentation choice for an FX-rate movement and is not the default performance calculation. An option's actual monetary MTM is a `MONETARY_VALUE`; it is not a unit price or implied-volatility series.

## Boundaries

- Raw `md.market_data_observation` values remain immutable and receive no calculation columns.
- The catalogue default is a governed analytic convention, not a mandatory P&L formula.
- A valuation, risk, or P&L policy may explicitly override the default. That selected transformation belongs in the persisted calculation methodology/run, not in an observation.
- The definition lives at series level because a reference node can legitimately have price, yield, spread, and volatility series simultaneously.
- Unit scaling remains distinct from listing quote factor and contract multiplier.

## Migration and compatibility

1. Create the catalogue and nullable series foreign key.
2. Seed the initial catalogue.
3. Backfill existing series deterministically from `value_type` and, where necessary, `series_type`:
   - `PRICE` → `PRICE`;
   - `INDEX_LEVEL` → `INDEX_LEVEL`;
   - `RATE` plus `FX_SPOT` → `FX_RATE`;
   - other `RATE` → `RATE`;
   - `YIELD`, `SPREAD`, `VOLUME`, and `QUANTITY` map to their like-named definitions.
4. Keep the new FK nullable in this slice so unknown legacy series are visible and resolvable by operations rather than rejecting historic data.
5. New API creation must require a recognised measure definition in a subsequent API-contract slice; this schema slice does not silently infer client input.

## Tests and evidence

- Metadata test proves the catalogue, FK and resolver index exist.
- Seed test proves core definitions are governed and idempotent.
- Backfill test proves FX rate and ordinary rate resolve differently, and legacy unknowns stay null.
- Demo time-series fixtures explicitly identify their measure definitions.

## Deferred scope

- P&L attribution and valuation-policy override schema.
- A complete volatility cube convention for delta/strike/tenor dimensions.
- API/UI presentation and validation of change methods.
- Organisation-wide numeric formatting/localisation policy.
