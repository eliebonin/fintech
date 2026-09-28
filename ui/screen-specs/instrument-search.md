# Screen specification: instrument search and detail

## Purpose

Give operations an auditable way to find the canonical economic instrument,
see its venue listings, reconcile external aliases, and inspect the evidence
behind a market-data value.

## Implemented route surface

| Route | Rendering | Responsibility |
|---|---|---|
| `/` | Server page + client island | Search, result list, selected instrument detail. |
| `/instruments/[instrumentId]` | Server route | Deep-linkable instrument detail; unknown UUID returns 404. |
| `/api/instruments/search?q=` | Server BFF handler | Returns view-oriented search results and source metadata. |

## Search behaviour

- Empty query shows the initial fixture set.
- Query matches canonical name, UUID, instrument type, issuer, formal
  identifiers, external mapping aliases, listing symbol, or venue MIC.
- Result rows show canonical name/type/currency and listing chips. OTC records
  show `OTC / instrument-level` instead of inventing a listing.
- Empty, error, and loading states are explicit.
- Search results are view models, not SQL rows.

## Detail behaviour

The detail panel makes the following visible:

- immutable internal UUID, governed type, status, effective date/version, and
  issuer;
- formal identifiers with their scope (`INSTRUMENT` or `LISTING`);
- external mappings with namespace, status, and mapping role;
- every listing's venue MIC, symbol, currency, quote factor, and unit
  multiplier, plus listing-level venue/product/FIX identifiers when present;
- market-data series, market date, named valuation cut, provider/dataset,
  source vintage, receipt time, and value basis.

The UI deliberately distinguishes an economic instrument from a venue listing
and never labels a raw observation as a valuation mark.

The listing onboarding form uses the same distinction. `tradingSymbol` is the
primary operational venue symbol; optional venue product and FIX security IDs
are stored as listing-level identifiers. Provider, custodian, bank, and client
aliases are not entered into these fields: they are managed through the
external-mapping workflow. Quote currency is loaded from the canonical
currency catalogue, so crypto pairs can use USD, USDC, BTC, or another approved
currency role without a hard-coded browser list.

## Next acceptance slice

Replace the fixture repository behind the BFF with the Python API adapter and
add authorization/tenant-context tests. The React view model should not change
unless the contract version changes.
