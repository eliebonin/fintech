# Instrument names and display identifiers

**Status:** Implemented alpha presentation policy  
**Owner:** Security master / Operations Console  
**Reviewed:** 26 October 2026

The main read and selection screens use a shared two-line label: existing business
name first, useful identifier and market/currency context second. Internal import
codes and UUIDs are retained for search, links and technical inspection; they are
not substitutes for a business identifier. This does not rename any record.

## Rules implemented

| Reference | Preferred display identifier | Context |
| --- | --- | --- |
| Equity, ETF/ETP or crypto listing | Exact listing ticker or trading pair | That listing's venue and quote currency |
| Listed future/option | Exact contract symbol | That listing's venue and quote currency; no guessed expiry/year/strike |
| Bond, fund share class, AMC, structured security | ISIN; otherwise FIGI, CUSIP, SEDOL, then RIC | Listing venue/quote currency where applicable; otherwise denomination currency |
| Canonical equity without an exact listing | Assigned standard identifier | No arbitrarily selected listing ticker |
| OTC swap | Existing approved tenant contract identifier; otherwise assigned standard identifier | Denomination currency |
| Other OTC contract | Assigned standard identifier, when present | Recorded currency context only |

The primary name is the canonical instrument name. A listing uses its exact
canonical parent; derivative underlyings and umbrella funds are not name or ISIN
fallbacks. A supplied FISN can fill a missing name. No generated FISN or invented
client contract reference is created. Missing identifiers say **Identifier not
supplied**. Identical native name/symbol text is not repeated.

Identifier assignments must be valid on the current governance date and match the
exact listing venue or have no venue restriction. Within scheme priority, exact
node assignments precede canonical-parent fallbacks. Primary status, most recent
valid-from and identifier text give deterministic selection. Ambiguous current
swap contract identifiers are not guessed. The original alias/internal code and
other valid identifiers remain in `searchText`.

## Boundaries and surfaces

- [Pure policy](../../../security_master_schema/instrument_display.py) contains no
  database access or financial calculation.
- [Bulk resolver](../../../apps/reference_api/instrument_display.py) applies the
  existing tenant/private-parent visibility predicate. Each 500-reference chunk
  performs one reference read and one identifier read; swaps need a bounded
  additional current-definition read. Chunking is not a total population cap.
- Typed read/search envelopes carry `meta.instrumentDisplays`, keyed by exact
  subject ID. Valuation carries the same map under `presentation`; strategy
  positions and measure previews carry it at the top level. These are current
  accessible navigation labels, separate from retained financial evidence.
- [Shared renderer/helper](../../../apps/ops-console/src/components/instrument-label.tsx)
  serves valuation positions/inspection, strategy positions/measure rows, trade
  history/detail headings, the instrument catalogue and the four booking searches.
  Native option controls and specialised instrument-creation forms are not
  comprehensively rewritten by this change.
- Listing links open the canonical instrument at `#listing-<exact listing ID>`.
  Two listings remain distinct even when their primary name is identical. Trade
  rows keep their exact trade-detail links. Existing technical detail stays available.
- Holdings identifier search and ordering are applied to the full authorised
  population before pagination. Valuation filters the full returned report before
  pagination. Existing catalogue/trade/booking SQL searches keep their semantics.
- No new public label endpoint, cross-request cache, authority bypass, financial
  DTO field or migration is introduced. Display-denied valuation evidence does
  not call the name resolver. Booking payloads/fingerprints are unchanged.

## Trade-offs and remaining limits

Existing names can still be poor or duplicated; fix reference data rather than
inventing names from mutable contract economics. Current labels may differ from
the historical name retained at booking. The frozen booking name and financial
terms remain explicitly visible in booking evidence. Names never substitute for
unique IDs in joins, selection or audit.

The resolver adds bounded metadata reads to page APIs. It does not export all
master data to browsers. Holdings already reconstructs the full population and
now resolves its visible metadata before identifier filtering. This is not a new
large-universe performance certification. No external name/identifier feed,
translation system, user-configurable naming engine or formal FISN conformance
implementation is included.

## Evidence and research

[Delivery and verification](../../delivery/shared-instrument-display-20261026.md).
Sources were searched and opened on 26 October 2026:

- [ANNA identifiers](https://anna-web.org/identifiers/): distinguish names and
  identifiers; ISIN applies across instrument families.
- [ISO 18774:2024 public abstract](https://www.iso.org/standard/84851.html): readable
  financial-instrument names. Only the public abstract was reviewed.
- [OpenFIGI documentation](https://www.openfigi.com/api/documentation): instrument
  identity, tickers, exchanges, currency and share-class qualifiers are distinct.
- [W3C table guidance](https://www.w3.org/WAI/tutorials/tables/): meaningful headers
  and usable table relationships. The renderer uses inline spans inside headings
  and cells and keeps native navigation/focus.

The precise two-line layout and identifier priorities are project choices informed
by these sources; they are not external mandatory requirements.
