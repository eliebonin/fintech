# Market Data resolution snapshots

`POST /v1/market-data-resolution-snapshots` creates an immutable, replay-safe record of entitled Market Data selection. It accepts one coherent context—one policy, valuation date and cut, UTC information cut, use purpose, and 1–50 distinct subject reference-node IDs.

The request body uses `subjectReferenceNodeIds`, `valuationPolicyId`, `valuationDate`, `valuationCutId`, `marketDataAsOfUtc`, and `usePurpose`. `marketDataAsOfUtc` must be an RFC 3339 UTC timestamp. `Idempotency-Key` is a required header, scoped to tenant and endpoint. Retrying with the same payload returns the original resource; reusing it with a different payload returns `409` and `idempotency.key_reused`.

Successful creation returns `201 Created`, `Location: /v1/market-data-resolution-snapshots/{id}`, and the complete frozen representation. `GET /v1/market-data-resolution-snapshots/{id}` returns only persisted evidence; it never evaluates present-day entitlement or re-resolves data. Snapshot access is tenant-scoped and missing or inaccessible resources do not disclose another tenant’s data.

Each item records one of `SELECTED`, `MISSING`, `STALE`, or `DENIED`, plus the selected observation/series where applicable, policy rule, entitlement decision, exception code, pricing dates, staleness, and frozen vintage, licence, provider-publication, and receipt evidence. Snapshot headers and items are append-only at both application and database layers.

`GET /v1/market-data/valuation-policies?valuationDate=YYYY-MM-DD` exposes only active, effective policies and their valuation-cut display metadata for the trusted tenant. It is a selector catalogue; it is not historic snapshot evidence.

## Demo active-policy catalogue

The local demo tenant currently exposes the following **synthetic** policies. These codes and local-time cuts are seed configuration for development and testing; they are not a production valuation-policy recommendation. The API deliberately exposes the policy and its permitted cut as a pair, so a browser cannot submit an arbitrary combination.

| Policy code | Purpose in the demo | Permitted valuation cut |
| --- | --- | --- |
| `DEMO_EOD` | General end-of-day valuation example. | `LONDON_CLOSE_DEMO` — Europe/London, 16:30. |
| `UK_FUND_CUTOFF_DEMO` | UK fund valuation example using a London FX cut. | `UK_FUND_FX_1600_DEMO` — Europe/London, 16:00. |
| `US_FUND_CUTOFF_DEMO` | US fund valuation example using a New York FX cut. | `US_FUND_FX_1600_DEMO` — America/New_York, 16:00. |

For a valuation date, the selector returns only policies that are active, effective for that tenant and date, and paired with their allowed cut. Snapshot creation validates the same policy/cut/date relationship again on the server; the selector response alone is not authority to bypass that validation.
