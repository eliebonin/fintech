# Market-data series MVP

## User goal

Operations can inspect a precise observable stream over a selected date window
without treating a generic "latest price" as a sufficient market-data query.

## Route and context

`/market-data?fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD` is a server-rendered view.
The BFF route `/api/market-data/series` forwards the local/Auth0 tenant and
user-account context to `GET /v1/market-data/series`.

Selecting **Inspect instrument history** adds `referenceNodeId` to the route.
The API then returns every visible series for that canonical node (for example,
both UK and US FX cuts), rather than silently choosing one stream.

## Display contract

Each card displays the reference-node UUID/name, series type/value type,
currency, observation count/latest value, sparkline, named valuation
cut/timezone, and provider, dataset, licence names/codes/UUIDs. Each card has a
drill-down link. The selected-node view renders an enlarged SVG history chart
and a table of the observations actually returned by the API, sorted ascending
by `marketDate`. The table keeps market date, observed timestamp, receipt
timestamp, value, value basis, and quality visible; timestamps are displayed
in UTC and the underlying observation remains immutable.

## States and acceptance

The page has a date-window form, an explicit API-unavailable state, a no-series
state, a back-to-catalogue link, and a `SYNTHETIC MVP` warning. With the
persisted fixture it shows cut-specific GBP/USD and EUR/USD streams, listed
security closes, futures, bonds, and an FX forward mark. The API bounds
catalogue results, filters by canonical reference node, and enforces tenant
membership.
