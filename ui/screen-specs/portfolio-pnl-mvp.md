# Portfolio P&L MVP

> Retired on 2026-10-07. This is a historical demo specification, not current behaviour or the replacement engine design. See [P&L demo retirement and fresh start](../../docs/delivery/pnl-demo-retirement-and-fresh-start.md). Old page bookmarks redirect to `/valuation`; the old calculation API returns410.

## User goal

Operations can compare a US-base and GBP-base portfolio on a selected date and
see instrument-level price and FX components.

## Route and context

`/pnl/us` resolves `MVP_US_PORTFOLIO`; `/pnl/uk` resolves
`MVP_UK_PORTFOLIO`. Both accept `?asOfDate=YYYY-MM-DD`. The BFF route forwards
the tenant context to `GET /v1/portfolios/{portfolio_code}/pnl`.

## Display contract

The response includes base currency, selected named valuation cut and local
timezone, as-of date, headline total, and one line per booked instrument/listing
with quantity, opening/closing observation values, opening/closing FX, local
price P&L, FX P&L, total P&L, series UUID, and closing observation UUID.

## Deliberate MVP boundary

This is a transparent display decomposition, not persisted official P&L
attribution. It resolves the latest accepted observation on or before the date,
uses the portfolio-specific London/New York FX cut, applies listing quote factor
and unit multiplier, and marks missing history by omitting the line. Formal
valuation runs, approved policy snapshots, and attribution methodology remain
the next domain slice.
