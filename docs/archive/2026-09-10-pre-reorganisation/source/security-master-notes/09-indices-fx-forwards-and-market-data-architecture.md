# Indices, FX forwards, and market-data architecture

## Evidence status

The index-family and return-profile decisions are supported by the S&P and
IOSCO references recorded in the [external evidence and research register](24-external-evidence-and-research.md).
The database shapes, resolver precedence, and deferred calculation scope remain
our implementation choices.

## Maintainable index classification

Index classification reuses the generic governed taxonomy tables rather than
introducing an index-specific classification hierarchy:

```text
secm.taxonomy
secm.taxonomy_value
secm.instrument_taxonomy_assignment
```

The initial canonical domains are `INDEX_ASSET_CLASS`, `INDEX_GEOGRAPHY`,
`INDEX_SCOPE`, `INDEX_SIZE`, `INDEX_STRATEGY`, `INDEX_BENCHMARK_ROLE`, and
`INDEX_SECTOR`. Values are hierarchical where useful, and assignments are
effective-dated on the concrete index variant. Provider-specific categories
may be retained as separate taxonomy domains; they must not overwrite the
canonical classification.

Classification is deliberately separate from economics: return semantics remain
in `secm.return_profile`, family lineage in `secm.index_family`, and weighting,
currency, calculation frequency, rebalancing, and methodology in
`secm.index_terms` / `secm.index_methodology_version`. This is enough for MVP
filtering and governance without copying every provider's catalogue. The
evidence and rationale are recorded in the [external evidence register](24-external-evidence-and-research.md).

## Boundary: instruments versus market-data series

An `instrument` is a contractual or economic thing that may be traded or held. A `market_data_series` is a precisely defined stream of observations used to price, value, or analyse an object. The two must not be conflated.

Examples:

| Item | Correct identity |
|---|---|
| OTC GBP/EUR forward settling on a fixed date at an agreed rate | Economic FX-forward instrument. |
| HSBC ordinary share | Economic instrument, with one or more listings. |
| HSBC on XLON official close | Market-data series for the XLON listing. |
| GBPEUR 1M | Rolling FX-forward-tenor market-data series. |
| FTSE 100 official close | Market-data series for the FTSE 100 index. |

All internal records can use UUIDv7 IDs. The ID type does not determine the business category: `market_data_series_id` is not an `instrument_id`.

## Indices

An index is a reference node of type `INDEX`, normally non-tradeable. It has an `index_terms` record covering at least index kind, currency, provider, calculation agent, base date, base level, methodology reference, and return profile.

For V1, support `PUBLIC`, `QIS`, `PROPRIETARY`, and `CUSTOM_BASKET` index kinds. QIS and proprietary indices need provider and methodology references plus official levels; defer full methodology-versioning, rebalance snapshots, and internal index calculation until required. Custom baskets need dated constituent snapshots rather than contractual payoff composition.

The schema follows the existing future-family/subtype pattern rather than creating a duplicate `secm.index` identity table:

```text
financial_reference_node (node_type = INDEX)
  +-- index_terms
  +-- index_methodology_version

financial_reference_node (node_type = INDEX_FAMILY)
  +-- index_family
```

Each concrete return or currency variant is its own `INDEX` reference node. `index_family` is only a conceptual grouping and is not used directly for pricing or booking. The generic `secm.return_profile` catalogue is reusable by index terms and performance-based swap legs; it stores stable semantic categories, while tax rates, financing references, formulas, rebalance rules, and other provider-specific details remain in methodology or contractual terms.

### Return profiles

Return type is contractual and valuation-critical. Price return, net total return, gross total return, and excess return are separate index variants and should be separate `INDEX` nodes linked by `INDEX_VARIANT_OF`. A product or swap references the exact variant, never merely the colloquial index name.

The generic `return_profile` catalogue records only stable semantics such as the base return basis, income treatment, tax treatment, and whether a financing reference is required. It is optional on consumers while an unapproved source definition is incomplete. A swap leg has its own contractual return definition and can point to or override the reference index profile. Methodology-specific tax rates, financing curves, fees, and formulas remain in `index_methodology_version` or the swap contract terms.

### Index MVP sign-off and research controls

This design is approved for the canonical reference-data MVP. Current provider
practice supports separate Price Return, Total Return, and Net Total Return
variants with distinct identifiers and levels. Return treatment is therefore a
property of the concrete index variant, not a mutable display label. See the
[S&P 500 provider page](https://www.spglobal.com/spdji/en/indices/equity/sp-500/)
and [S&P return-type guidance](https://www.spglobal.com/spdji/en/education/article/an-overview-of-return-types-for-insurance-indices/).

The MVP control boundary is:

* `financial_reference_node` owns identity; no duplicate `secm.index` table is
  created.
* `index_family` is grouping and lineage only; it is never a pricing, trade, or
  valuation subject.
* Every concrete index variant has its own UUID, provider mappings and
  `md.market_data_series`.
* `return_profile` holds stable semantics only. Provider-specific tax rates,
  financing references, fees, formulas and rebalance rules belong to the
  effective-dated methodology or contractual terms.
* A methodology version records weighting, calculation/rebalance frequency,
  launch date and whether a history is back-tested. Pre-launch hypothetical
  history must not be presented as live observed history.
* An approved production variant should have a non-null return profile;
  nullable values are permitted only during source enrichment or draft
  onboarding.

This is consistent with the [IOSCO Principles for Financial Benchmarks](https://www.iosco.org/library/pubdocs/pdf/ioscopd409.pdf), which emphasise benchmark governance, quality, methodology and accountability.

Deferred enhancements are deliberately non-blocking: governed index-kind
catalogues, richer administrator/calculation-agent role history, automated
constituent ingestion, full index replication, and an internal index-calculation
engine. Constituent snapshot tables may remain empty until a use case requires
constituent-level analysis.

## Contractual FX forwards

Each actual FX forward is its own economic instrument. `fx_forward_terms` contains the base and quote currencies, an immutable quote convention, agreed forward rate, delivery/NDF settlement type, settlement or fixing currency where relevant, and associated calendars/conventions. `instrument_dates` carries effective date, NDF fixing date, maturity date, and final settlement date.

The implemented manual-first onboarding slice uses these existing tables and
the `CREATE_FX_FORWARD` approval workflow; it does not add a listing or a
generic quantity-currency field. See the [FX-forward onboarding record](../docs/architecture/fx-forward-onboarding-2026-09-08.md)
for API/UI details and deferred confirmation terms.

The contract's agreed rate belongs in the terms and is also captured in the trade-booking record. A corrected contract must be versioned or recreated according to lifecycle policy; it must not silently overwrite the historical agreed terms.

## FX pair and rolling forward tenors

`GBPEUR 1M` means a one-month forward quote on the GBP/EUR pair, not a persistent legal contract. It rolls every market day: the 1M identity stays the same, while its resolved delivery date changes.

The pair must have an explicit orientation. `GBPEUR` alone is insufficient; store for example `base_currency = GBP`, `quote_currency = EUR`, and `quote_convention = EUR_PER_GBP`. Also retain pair spot lag, business-day convention, and relevant currency calendars.

```text
FX_PAIR: GBPEUR
  +-- FX_FORWARD_CURVE: GBPEUR-FWD
        +-- market-data series: GBPEUR spot
        +-- market-data series: GBPEUR 1W
        +-- market-data series: GBPEUR 1M
        +-- market-data series: GBPEUR 2M
        +-- market-data series: GBPEUR 3M
```

The normal value-date rule is `SPOT_DATE_PLUS_TENOR`, subject to pair calendars and business-day adjustment. A tenor quote may be an `OUTRIGHT_FORWARD_RATE` or `FORWARD_POINTS`; raw forward points and any derived outright rate must retain source and derivation lineage.

Suggested reference-data shape:

```text
fx_pair_terms
  fx_pair_node_id, base_currency_id, quote_currency_id, quote_convention,
  spot_lag_business_days, calendar/convention

fx_forward_curve
  fx_forward_curve_id, fx_pair_node_id

market_data_series
  market_data_series_id, subject_type, subject_id, measure,
  tenor_code, quote_kind, source, currency, status
```

For `GBPEUR 1M`, `market_data_observation.resolved_value_date` is required because the date is different on each as-of date.

## One market-data-series catalogue

Use one common `market_data_series` catalogue. One row defines one economically precise observable stream. It is the resolution target for queries and policies.

```text
market_data_series
  market_data_series_id
  subject_type and subject_id       -- listing, instrument, index, FX pair, etc.
  measure                            -- OFFICIAL_CLOSE, BID, ASK, MID, FORWARD_OUTRIGHT, ...
  tenor_code                         -- nullable; e.g. 1M for FX forwards
  quote convention / currency
  provider, venue, contributor
  valuation_cut_id                  -- nullable for raw series
  status and effective dating
```

Series are delivered through a governed content `dataset`, such as a provider's commodity-index EOD universe or US-equities EOD universe. A provider organisation can offer several products; a product can contain several datasets; a dataset can carry effective-dated licences. A series may be associated with a default dataset for catalogue purposes, but `dataset_id` must also be stored on each observation because the source/dataset can change over time.

Examples:

| Series | Subject | Measure | Tenor/cut |
|---|---|---|---|
| `HSBA_XLON_OFFICIAL_CLOSE` | HSBC XLON listing | `OFFICIAL_CLOSE` | XLON session close |
| `HSBA_XLON_BID_VENDOR_A` | HSBC XLON listing | `BID` | raw intraday |
| `GBPEUR_1M_MID_VENDOR_A` | GBPEUR FX pair | `FORWARD_MID` | 1M, raw intraday |
| `FTSE100_OFFICIAL_CLOSE` | FTSE 100 index | `OFFICIAL_CLOSE` | index official close |

The logical generic scalar fact table is:

```text
market_data_observation
  observation_id, market_data_series_id, dataset_id, acquisition_licence_id nullable,
  market_date, observed_at, value, source_published_at, received_at,
  source_id, quality_status
```

The application asks for a valuation context (subject, measure, tenor where applicable, source/selection policy, as-of and cut) and a resolver selects one series. After that, retrieving the latest eligible scalar observation is uniform. No caller should ask simply for "the latest price".

### Source vintages and historic information cuts

`md.market_data_vintage` identifies the provider revision, file, batch, or
extract that delivered one or more observations. It records the dataset and
provider, source publication time, Fortem receipt time, value basis
(`RAW`, `VENDOR_ADJUSTED`, `RESTATED`, etc.), lifecycle status, content hash,
and retained raw payload link. Observations optionally point to that vintage
and also retain the source publication timestamp directly for efficient
point-in-time filtering. This is source lineage, not a replacement for the
observation's economic `market_date` or `observed_at_utc`.

For a historic valuation or Soft-NAV replay, an observation is eligible only if
its source vintage had been received by the requested information cutoff and,
when supplied, the source had published it by that cutoff. A current vendor
screen that restates 2018 prices is therefore not automatically the 2018
information set. Raw observations remain immutable; corrections and restated
history are new vintages/observations with explicit supersession and value
basis. If a source cannot provide a publication timestamp, receipt time is the
conservative knowability bound and the missing publication fact is retained as
data quality metadata.

The resolver must additionally receive the tenant and dataset-use entitlement. Recommended precedence is: approved tenant override; tenant-entitled provider value; platform-entitled approved value; approved public value; explicit missing-data exception. Physical retention of a shared observation never implies that it may be returned to every tenant.

`acquisition_licence_id` on an observation is provenance: it says which Fortem right enabled receipt/retention where known. Tenant access is a separate, effective-dated `tenant + dataset + intended-use` entitlement and is evaluated at read time. Do not store a tenant entitlement ID on each observation, since the same source fact may be usable by multiple tenants under different rights.

## Valuation cuts

One market date may legitimately have different values at London close, New York close, a venue's official close, and internal EOD. These values have distinct meanings, not competing revisions.

```text
valuation_cut
  valuation_cut_id, code, timezone, local_time, calendar_id, selection_rule
```

| Cut | Meaning |
|---|---|
| `LONDON_CLOSE` | Defined London-time valuation point and selection rule. |
| `NEW_YORK_CLOSE` | Defined New York-time valuation point and selection rule. |
| `INTERNAL_EOD` | Internal approved accounting/P&L cut. |
| Venue session close | The authoritative venue close for a listing. |

For raw observations, `observed_at` records when the source reported the event. A valuation cut represents the business moment that a selected value is intended to represent. Derived/approved end-of-day marks must record the cut, selection method (`LAST_BEFORE_CUT`, `MID`, `APPROVED`, etc.), inputs, and status.

## Intraday data

Maintain the common catalogue but use specialised physical storage when actual intraday ingestion begins:

```text
market_data_series
  +-- market_data_observation       -- EOD and low-volume scalar facts
  +-- market_data_quote_tick        -- bid/ask updates
  +-- market_data_trade_tick        -- execution/last-trade events
  +-- market_data_bar               -- 1m, 5m, daily OHLCV aggregates
  +-- valuation_mark                -- selected/approved valuation results
```

`market_data_quote_tick` retains bid and ask together because they arrive as one market event. It needs `market_timestamp`, `received_at`, `source_sequence`, source/venue, bid/ask values and sizes, indicative flags, and correction lineage. `market_data_trade_tick` separately stores execution price, quantity, conditions, and cancellation/correction status.

Use `timestamptz` normalized to UTC. Keep venue calendars/time zones in reference data to derive a correct local session and market date. For a historic cut, select the latest eligible observation at or before the cut; never select the nearest later point.

Tick tables should be time partitioned and indexed for their actual retrieval paths when volume warrants it. They are not needed in the first release if intraday ingestion is not yet in scope.

## Quote factor and contract multiplier

Quotation conversion and contract economics are different concepts:

```text
economic cash value
  = position quantity × quoted price ÷ quote_factor × unit_multiplier
```

| Concept | Meaning | Normal owner |
|---|---|---|
| `quote_factor` | Divisor converting the displayed quote to its economic price unit. | Listing quotation terms or market-data-series quotation convention. |
| `unit_multiplier` | Economic units represented by one traded contract/unit. | Instrument terms, such as `future_terms` or `option_terms`. |

Example: a GBP share quoted at `1,023 GBX` has `quote_factor = 100` and unit multiplier `1`; its economic price is GBP `10.23`. For 100 shares, cash value is GBP `1,023`.

An index future quoted at 5,000 index points with a multiplier of 20 currency units per point has a contract value of 100,000 currency units. A listed option quoted at 4.25 with a 100-share multiplier has a premium cash amount of 425 currency units per contract.

Suggested effective-dated data:

```text
listing_quotation_terms
  listing_id, quote_currency_id, quote_unit_code, quote_factor,
  display_decimals, tick_size, is_current, n_sequence

instrument_contract_terms
  instrument_id, unit_multiplier, unit_of_measure,
  is_current, n_sequence
```

Do not use a generic ambiguous `multiplier` column. A bond price quoted as a percentage of par (`PCT_OF_PAR`) is a separate quotation basis and must use the bond nominal/par calculation; it is not merely a GBX-style quote factor. Adjusted listed options can have changing multipliers after corporate actions, so their multiplier must be effective-dated.
