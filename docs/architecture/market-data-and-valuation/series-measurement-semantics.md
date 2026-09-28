# Series measurement semantics

**Status:** Accepted  
**Content type:** Architecture decision and implementation record  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-09-11

## Decision

An immutable market-data observation stores a number; its economic meaning belongs to the governed series definition. `md.series_measure_definition` is therefore referenced by `md.market_data_series` through the nullable transitional foreign key `measure_definition_id`.

`series_type` continues to identify the observable stream (`OFFICIAL_CLOSE`, `FX_SPOT`, `EVALUATED_PRICE`, `MARK`), while the measure definition explains the number (`PRICE`, `FX_RATE`, `YIELD`, `IMPLIED_VOLATILITY`, and so on). The distinction is essential because the same reference node may have several economically different streams.

## Default movement convention

| Measure | Example | Default movement | Display |
| --- | --- | --- | --- |
| `PRICE` | listed close or evaluated bond price | `(P_t / P_{t-1}) - 1` | percent |
| `FX_RATE` | GBP/USD spot | `(FX_t / FX_{t-1}) - 1` | percent |
| `INDEX_LEVEL` | price/total-return index | relative return | percent |
| `NAV` | fund share-class NAV | relative return | percent |
| `IMPLIED_VOLATILITY` | 1Y ATM FX volatility | `vol_t - vol_{t-1}` | volatility points |
| `YIELD`, `RATE`, `CREDIT_SPREAD` | bond yield, zero rate, OAS | change × 10,000 | basis points |
| `VOLUME`, `OPEN_INTEREST` | exchange activity | absolute difference | units |
| `MONETARY_VALUE` | trade-specific MTM | monetary difference | mark currency |

Percent-stored values follow the existing convention: `19.00` means 19%. Thus, 18.25 to 19.00 is a `+0.75` volatility-point move. It is not inherently a 4.11% performance return.

## Boundaries

- This change does not alter or calculate on `md.market_data_observation`; raw observations remain immutable evidence.
- The catalogue provides a normal analytical convention, not an immutable P&L mandate.
- Valuation/risk/P&L methodology may later select a different permitted transformation and must persist that selection with the calculation run.
- Listing quote factor and unit/contract multiplier remain separate from measurement semantics.

## Migration and compatibility

Revision `20260911_44_market_data_series_measurement_semantics` creates the catalogue, adds the nullable series FK, and deterministically maps existing price, official NAV, FX-spot rate, rate, yield, spread, index-level and volume series. A legacy series with no unambiguous mapping remains null for operational resolution rather than receiving an invented interpretation.

The local MVP database had already invoked `metadata.create_all()` while focused tests exercised the new metadata. That created the catalogue but, correctly, did not alter existing `md.market_data_series`. The local-only reconciliation therefore stamped the verified catalogue state at revision 44 and applied idempotent revision `20260911_45_reconcile_series_measurement_metadata_bootstrap`, which added the FK column, index, foreign key, and backfill. This is a development-bootstrap exception; production environments must be Alembic-owned or receive an explicit reviewed baseline reconciliation.

## Verification

On 2026-09-11, focused tests passed for:

- governed default conventions for price, FX rate, implied volatility, yield and rate;
- live demo links from price, NAV and GBP/USD spot series to their measure definitions;
- schema metadata for the catalogue and series foreign key;
- offline Alembic SQL generation through revision `20260911_45`.

Detailed design: [series measurement semantics design](../../superpowers/specs/2026-09-11-market-data-series-measurement-semantics-design.md).  
Execution record: [implementation plan](../../superpowers/plans/2026-09-11-market-data-series-measurement-semantics.md).
