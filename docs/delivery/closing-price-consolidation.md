# Closing-price consolidation

Date: 2026-10-08. Scope: price definitions and policy selection, not a wider
valuation implementation or a permission grant.

## Agreed model

One `CLOSE` series type. A series has an independent `closing_method`:
`EXCHANGE_OFFICIAL`, `LAST_TRADE`, `PROVIDER_DEFINED`, or `UNKNOWN`.
Unknown does not mean non-official; it means the designation is not established.
Method describes the series methodology, not the adjustment of individual prices.
Providers whose methodology changes need a reviewed series definition rather
than silent relabelling of historical evidence.
This task consolidates `CLOSE`/`OFFICIAL_CLOSE`; existing Yahoo `ADJUSTED_CLOSE`
series and their separate adjustment basis are retained, not merged or relabelled.

Rules optionally set `requireOfficialClose`. Unchecked means any closing method
may qualify; checked requires `EXCHANGE_OFFICIAL`. Neither choice relaxes
adjustments, completed-session timing, freshness, source priority, calendars,
quality or rights. A distributor can supply an exchange-official close; official
does not mean the distributor must itself be the exchange.

## Compatibility and migration 76

- Existing `OFFICIAL_CLOSE` series become `CLOSE`, retaining their previously
  asserted designation as `EXCHANGE_OFFICIAL`. This is not independent source
  certification. IDs, observations, prices, adjustments and permissions stay
  unchanged. Existing plain `CLOSE` series remain `UNKNOWN`; the generic
  `is_official` flag is not used to infer closing methodology.
- Saved policy rows and frozen result/snapshot JSON are not rewritten. Legacy
  `OFFICIAL_CLOSE` rules are interpreted as `CLOSE` with the official requirement.
- New API requests with the old spelling are normalized to that same model.
  New saved rules use `CLOSE` and the separate requirement. Policy reads expose
  the canonical view, while preserving the underlying historical policy version.
- Existing creation keys/fingerprints remain replayable; removing an official
  requirement under an existing key must still conflict.
- Legacy series-write clients are normalized at the database boundary so they
  cannot recreate a separate family. Legacy catalogue filters also retain their
  official-only meaning.
- Resolver version advances to `market-data-resolver-v6-close-method`. Newly
  frozen resolution evidence records the selected method and policy requirement.
  The generic `is_official` field remains for NAV/FX and other existing consumers.

The policy editor presents one closing-price choice with an official-only checkbox.
Available source profiles and the market-data history page show closing method.
Compatibility checks include this requirement before source ranking.

## TTE/Yahoo implications

Yahoo remains `CLOSE` with unknown closing methodology, not certified official.
The existing EOD Policy's official-only requirement is preserved. To accept Yahoo,
create a revised policy version with the official requirement unchecked.
This change alone does not resolve split-adjusted position treatment, recorded
valuation/automated-use permissions, governed Paris calendars, or GBP FX conversion.

## Rationale and references

An official closing price follows exchange-specific methodology and may differ
from the last trade. Retain that fact as metadata rather than another price family.
Reference: [NYSE Arca official closing price methodology](https://beta.nyse.com/publicdocs/nyse/markets/nyse-arca/NYSE_Arca_Official_Closing_Price_Calculation.pdf).
Closing designation is independent of historical adjustment. Reference:
[Yahoo adjusted-close explanation](https://help.yahoo.com/kb/SLN28256.html).
Both sources were inspected during the preceding design discussion.

## Verification and activation

Migration 76 applied to local `fortem_secm`: 12 previously designated official
series are now `CLOSE / EXCHANGE_OFFICIAL`; all 543 real Yahoo closing series
remain `CLOSE / UNKNOWN`. Before/after observation count and numeric value sum,
saved rule identifiers/types and policy fingerprints were identical.

Verification: 63 focused isolated PostgreSQL tests passed, followed by an
additional alias-collision regression check during final self-review. The final
isolated closing-definition/ingestion run passed 36 tests; the three lightweight
contract/alias-validation checks also passed. New behavior was observed failing
before implementation, including duplicate publication from legacy spellings.
18 focused frontend tests passed; console and API-contract TypeScript checks,
Python compile checks and deterministic OpenAPI export check passed.
Existing unrelated seed deprecation warnings remain; no full-suite run.

API and console started locally (ports 8000/3000). HTTP 200 confirmed for health,
the saved EOD policy, TTE series, source profiles, signed-session BFF definitions
and the policy page. Server-rendered markup contains the separate official-close
checkbox and no `OFFICIAL_CLOSE` family option. No browser click-through signoff.
No Git commit or push. Sequential implementation and final self-review, as requested.
