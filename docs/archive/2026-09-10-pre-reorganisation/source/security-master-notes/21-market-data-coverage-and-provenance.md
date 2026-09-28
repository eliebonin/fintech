# Market-data coverage and provenance contract

## Evidence status

The provenance, vintage, cut, and entitlement fields below are deliberate
reproducibility and licensing controls. They should not be described as a
single universal vendor convention. Provider-specific correction and historic
vintage semantics remain a research gap; see the [external evidence register](24-external-evidence-and-research.md).

## Decision

`md.market_data_series` describes one economically precise observable. It now
also declares its expected operational shape:

* `expected_frequency_code` — `BUSINESS_DAILY`, `CALENDAR_DAILY`, `MONTHLY`,
  `QUARTERLY`, or `EVENT_DRIVEN`;
* `expected_market_calendar_id` — the governed calendar that defines an open
  business day for the series;
* `coverage_start_date` and `coverage_end_date` — the declared availability
  window, not a claim that every expected point has arrived.

This is deliberately a *series contract*, not fields copied on every
observation. Completeness is calculated for a requested date range against the
contract and calendar. It is not stored as a mutable `is_complete` flag.

## Database guardrail

The database trigger `md.enforce_market_data_observation_market_date()` rejects
an observation without `market_date` when its series cadence is date-based
(`BUSINESS_DAILY`, `CALENDAR_DAILY`, `MONTHLY`, `QUARTERLY`). This prevents the
most damaging class of EOD resolver ambiguity. `EVENT_DRIVEN` series and future
tick/bar storage remain eligible for timestamp-led facts.

The implementation does not yet infer a market date from a timestamp inside the
trigger: that requires a governed venue/session mapping and should occur at
ingestion with an explicit timezone and source-date rule.

## Calendar responsibility

Calendars belong in the `cal` schema, never `secm`. A series selects the
calendar used for *coverage expectations*. A valuation cut may select a
different calendar used for the valuation-date roll. A listed equity close
normally uses its venue calendar; an FX spot series can use a 24x5 FX calendar.
The two are related but not interchangeable.

The current synthetic fixture records full closures for a small, shared holiday
set. Production onboarding must load authoritative calendars and version their
sources; it must not treat the fixture as an exchange calendar.

## Observation-level provenance

Each immutable observation retains its actual:

* dataset and acquisition licence;
* provider, through that dataset's provider product;
* `market_data_vintage_id`, a provider delivery/batch with source key,
  publication time and receipt time; and
* source observation key and source publication timestamp.

The catalogue default dataset is only a selection hint. The row-level values
are the evidence used in a valuation snapshot. The API and market-data history
screen expose both: card-level default provenance and row-level actual
provenance/vintage.

## Deferred choices

1. Implement a calendar-session resolver and expected-point completeness API
   (including early closes and half-day publication expectations).
2. Define provider-specific correction policy: whether a later vintage becomes
   preferred and how an historic information cut selects it.
3. Add a formal source-to-internal market-date mapping policy for intraday and
   cross-timezone feeds.
4. Partition high-volume observation/tick tables once real volumes justify it.
