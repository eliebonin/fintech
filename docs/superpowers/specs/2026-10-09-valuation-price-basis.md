# Economic price requirements for valuation — proposed design

Status: proposed; planning only. Date: 2026-10-09.

## Outcome

Tenants request an as-traded closing price rather than needing to understand each
provider's adjustment labels. The platform may use a split-adjusted input only
when it can reconstruct a compatible as-traded price with frozen evidence.
This is an equity/ETF price-input enhancement, not a new total-return engine.

## Policy and data responsibilities

- Source observations retain their actual basis, original values and lineage.
- A rule has `priceRequirement: AS_TRADED` and `allowSplitConversion: boolean`.
  New valuation templates explicitly enable verified split conversion. Existing
  policies remain native-only or keep their exact legacy source-basis selection;
  they are not silently broadened. Unknown requirements fail closed.
- `valueBasis` remains an advanced exact SOURCE filter for legacy compatibility
  and non-valuation selection. It is not the valuation output basis.
- The normal editor shows "As-traded valuation price" and "Allow verified
  conversion from split-adjusted data". Official closing method, timing,
  freshness, source priority and rights remain separate requirements.
- Dividend-adjusted, total-return and unspecified provider-adjusted inputs are
  not accepted for as-traded valuation in this release.

## Safe conversion

Define the cumulative split price factor F as adjusted_price / as_traded_price.
Then as_traded_price = source_price / F. A later 2-for-1 split gives F=0.5:
adjusted 40 becomes historical as-traded 80. Booked quantities and execution
prices remain unchanged. Do not also restate those quantities to the adjustment
anchor: that would apply the conversion twice.

Evidence must establish the adjustment method, anchor, complete relevant split
coverage, effective dates/ordering, positive ratios and source vintage. Every
input must have been known at the information cutoff. A missing event list,
equality of Close and Adjusted Close, or an empty response does not prove F=1.
Later provider restatements must not alter previously frozen results.

Use exact retained split ratios, Decimal calculations and a declared conversion
version. Derived as-traded prices use the existing 12-decimal price precision,
ROUND_HALF_EVEN; retain unrounded calculation evidence and the rounding rule.
Reject overflow and nonpositive results. Do not manufacture a RAW source series.

## Selection and evidence

Check permissions, scope, convention, adjustment convertibility and bounded
freshness before source arbitration. Preserve current freshness/source-priority
precedence. Within the same provider/date/rank, prefer native RAW over a converted
equivalent, then retain the existing deterministic revision tie-breaks.

Resolver `selectedValue` stays the original source value. Add separate frozen
`valuationValue`, `valuationBasis` and `priceBasisEvidence`. Calculation consumes
only the valuation value after checking the proof. UI evidence shows both values,
source/used dates, factors, anchor, method, provenance and information cutoff.

## Scope boundaries

The existing corporate-action safety guard remains. Splits during a held
position's life still block until position replay is implemented separately.
This release can undo later historical-price restatements without implementing
every corporate-action lifecycle. Dividend income/P&L, GBP FX conversion, source
permissions and governed exchange calendars remain separate work.

The existing `secm.market_data_adjustment_factor` table expresses raw-to-derived
series relationships, but lacks vintage, recorded-time, revision and completeness
evidence. Do not force a synthetic raw-series relationship into it. Add narrowly
scoped immutable observation-linked price-basis evidence for this requirement.

## Yahoo/TTE gate

The ingestor requests `events=div,splits` but presently discards the events and
labels Close SPLIT_ADJUSTED, Adjusted Close VENDOR_ADJUSTED. First establish the
provider's adjustment anchor and relevant coverage. Retain and parse events with
rights checks. Existing history requires a newly evidenced revision; no backdating.
If Yahoo cannot establish the required proof, retain prices for reporting and
leave conversion blocked rather than assert factor 1. TTE's October 6/7 prices
become acceptable only after native equivalence or a valid conversion is proven.

## Research basis

[Alpha Vantage support](https://www.alphavantage.co/support/) explicitly distinguishes
raw inputs from data adjusted for splits and cash dividends. Inspected during the
discussion. Our inference is that economic-unit compatibility belongs to the
engine, while the policy sets admissible requirements.
Yahoo's [adjusted-close help](https://help.yahoo.com/kb/SLN28256.html) was identified,
but a fresh full-page read returned HTTP 429; it is not treated as evidence of
Yahoo's split-only anchor or complete event coverage.
