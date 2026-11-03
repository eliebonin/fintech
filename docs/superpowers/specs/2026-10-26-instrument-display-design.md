# Shared instrument display policy

Status: implemented and verified, 26 October 2026. See the
[delivery record](../../delivery/shared-instrument-display-20261026.md).

## Intent and boundaries

Use one readable name-first, identifier-second policy across valuation, holdings,
trades, catalogue and booking selection. Preserve the exact instrument/listing
link, permissions, server-side search/paging and frozen financial evidence.
Existing names/approved identifiers are the inputs; no renaming, migration,
new provider, configurable naming engine or made-up contract codes.

The approved approach is a shared read-only resolver and reusable frontend
component. A universal ISIN-only label loses native contract/listing context;
individual per-page/product patches drift. Product-aware identifier priorities
inside one bounded resolver retain those differences without separate policies.

## Display contract

`InstrumentDisplayView`: `primaryName`, nullable `identifier` containing `scheme`
and `value`, `context` (readable strings), `searchText`, canonical `instrumentId`
for listing-preserving navigation, optional instrument type/label, and
`basis: CURRENT_ACCESSIBLE_METADATA`.

- Primary name is the existing canonical business name. A listing uses its exact
  canonical parent, never an underlying or umbrella fund. Missing names are
  explicit; do not generate legal names or interpret incomplete symbols.
- Equity/ETF/crypto listings and listed futures/options prefer their native
  listing symbol with venue context. Registered identifiers remain accessible.
- Bonds, funds/share classes, AMCs and structured securities prefer ISIN, then
  recognised alternatives (FIGI/CUSIP/SEDOL). Canonical equities without an exact
  listing may also use a registered identifier; never choose an arbitrary listing.
- OTC swaps prefer an existing approved tenant contract identifier; otherwise use
  an assigned standard identifier. Other OTC contracts use assigned identifiers
  when present. No automatic SPX-TRS-001-style references.
- Context identifies listing venue and explicitly labelled quote currency, or
  denomination currency for canonical funded securities. No arbitrary OTC flag
  or currency implication when not evidenced.
- Identifier selection respects assignment validity and venue context; exact-node
  identifiers precede canonical parent fallbacks at the appropriate scheme priority.
- Missing identifiers remain explicit and technical IDs/codes stay in detail
  disclosures, not promoted to a primary identifier. Search can still match them.
- Labels are current navigation metadata, not a substitute for frozen maturity,
  strike, leverage, quote factors or valuation inputs. Keep those in existing
  financial inspection; don't add mutable economics to historical labels.

Use an additive `ApiMeta.instrumentDisplays` sidecar on typed read/search responses.
Booking-context DTOs are also frozen in financial snapshots: do not add display
fields to those models or their fingerprints. Strategy reads can expose the same
map as top-level `instrumentDisplays`; valuation presentation includes the map
alongside existing read-only labels. Resolve in bounded batches after visibility
gates, with no per-row calls, public label oracle or cross-request cache.

## Rollout and verification

Current authorized checkout/branch and sequential implementation are retained;
preserve earlier uncommitted work, no automatic commit/push. Focused offline
tests first, disposable PostgreSQL for scope/identifier contracts, generated
OpenAPI parity, frontend regressions and isolated browser workflows. No operating
trades, market data or valuations may be written for acceptance.

## Sources checked 26 October 2026

- [ANNA identifiers](https://anna-web.org/identifiers/): descriptive aliases and
  unique identifiers have distinct roles; ISIN is not bond-only.
- [ISO 18774:2024 public abstract](https://www.iso.org/standard/84851.html):
  human-readable names across instrument types. This is not a full standard
  conformance review or a proposal to generate registered FISNs.
- [OpenFIGI](https://www.openfigi.com/api/documentation): names, tickers, market,
  share-class and contract qualifiers are distinct. No provider integration added.
- [W3C accessible tables](https://www.w3.org/WAI/tutorials/tables/): preserve
  semantic headers, readable row labels and keyboard-accessible details.

The two-line layout and identifier preference order are project UX choices,
not a claim that an external standard mandates those exact priorities.
