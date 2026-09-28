# Soft-NAV pricing-date resolution

## Decision

Soft NAV selects immutable observations from the normal market-data store. It does not copy T-1, stale, or fund-NAV values into a separate price table.

The NAV valuation date, requested pricing date, used market date, source publication time, receipt time, and valuation information cut answer different questions and must remain separate.

```text
NAV valuation date       -- date for which the portfolio is valued
requested pricing date   -- date derived by policy, for example T-1
used market date         -- date represented by the selected observation
information cut          -- latest receipt timestamp eligible in the historic run
```

## Policy hierarchy

The resolver evaluates a small, deterministic hierarchy:

```text
exact market-data series
  -> exact canonical subject node
     -> instrument type
        -> policy default
```

Rules belong to the tenant-scoped, versioned valuation policy. They are not generic attributes of an instrument. A fund's official NAV publication convention may be described by its series, but a client still chooses whether its Soft NAV policy uses that official T-1 observation, another permitted mark, or an approved override.

## Required rule fields

`ten.valuation_policy_rule` contains the normal source/series selection fields plus:

```text
subject_reference_node_id      -- exact instrument, listing, index, FX pair, or fund
market_data_series_id          -- exact observable stream
pricing_date_rule              -- SAME_DAY, PRIOR_AVAILABLE, FIXED_LAG
lag_business_days              -- non-negative lag for FIXED_LAG
market_calendar_id             -- calendar when one is required
max_staleness_business_days    -- maximum allowed distance from requested date
missing_data_action            -- FAIL, WARN, MANUAL_OVERRIDE
```

For the first release, policy resolution uses this fixed precedence. It is intentionally not a general-purpose expression engine.

## Resolution behaviour

1. Determine the exact policy rule and the requested pricing date.
2. Restrict candidates to observations received on or before `market_data_as_of_utc`.
3. Select an observation on the requested date for `SAME_DAY`; otherwise select the latest observation on or before the requested date.
4. Calculate business-day staleness against the requested date.
5. Enforce the policy's staleness and missing-data action.
6. Freeze both the result and the decision evidence.

The initial resolver contains a weekday implementation for `FIXED_LAG`. A production calendar resolver will read the shared `cal.market_calendar`, `cal.market_calendar_session`, and `cal.market_calendar_holiday` tables; the rule already carries `market_calendar_id` so its result remains attributable.

## Frozen evidence

Every `md.market_data_resolution_snapshot_item` and, where used by Soft NAV, every `nav.nav_input_snapshot_item` retains:

```text
pricing_date_requested
pricing_date_used
staleness_business_days
staleness_status
policy_rule_id
market_data_resolution_snapshot_item_id  -- NAV input's direct resolver lineage
```

`md.market_data_observation.market_date` is the economic business date represented by the value. It is distinct from `observed_at_utc`, `source_timestamp_utc`, and `received_at_utc`. It is nullable only to preserve older inbound records during the draft's no-migration phase; it is required by the onboarding contract for newly introduced EOD, official NAV, and similarly date-based observations.

## Implemented resolver contract (V1)

`security_master_schema.market_data_resolver.resolve_market_data` is the
database selection boundary. Its request always carries tenant, subject,
versioned valuation policy, valuation date, named cut, timezone-aware
information cut, and intended data-use purpose.

It accepts an observation only when all of the following are true:

* its series belongs to the requested canonical subject and matches the selected rule;
* its series and observation are active/accepted, its `market_date` is known, and it has not been replaced by an accepted correction;
* the tenant has an active entitlement to the observation's exact dataset for the requested purpose and valuation date;
* it was received on or before the historic information cut; and
* it passes the rule's pricing-date and staleness test.

Rule precedence is exact series, exact node, instrument type, then default;
`rule_sequence` breaks ties. V1 intentionally does **not** silently fall through
from a more-specific rule with no eligible value to a less-specific one. Its
`missing_data_action` is the recorded policy result. This makes missing data
visible and makes a historic result reproducible.

`persist_resolution_snapshot` inserts a new immutable header plus one immutable
item per resolved subject in the caller's transaction. The item stores the
observation, dataset, policy rule, entitlement outcome, requested/used dates,
staleness and explicit exception code. It is an audit record, not a cache to be
updated in place.

## FX is a separately resolved valuation input

For a non-reporting-currency holding, the local price and the FX conversion are
two independent resolver subjects. They can have different series types,
datasets, market dates, valuation cuts and permitted staleness. A complete Soft
NAV run therefore freezes both resolver items and records the conversion
direction/convention used to turn local value into reporting value.

The required replay questions are: “which local price did we use?”, “which FX
rate did we use?”, “as of which named cut and information cut were each
eligible?”, and “which policy/entitlement authorised each input?” A stored
numeric `fx_rate` alone cannot answer them.

## Examples

| Holding | NAV date | Rule | Requested | Used | Outcome |
|---|---:|---|---:|---:|---|
| XLON equity | 1 Sep | `SAME_DAY` | 1 Sep | 1 Sep | Current official close |
| Fund share class | 1 Sep | `FIXED_LAG`, 1 | 31 Aug | 31 Aug | T-1 official NAV |
| OTC bond | 1 Sep | `PRIOR_AVAILABLE` | 1 Sep | 29 Aug | Accepted only if within staleness limit |
| Missing fund NAV | 1 Sep | `FIXED_LAG`, 1 | 31 Aug | — | Fail, warn, or require manual override under policy |

## Non-goals for this slice

* No duplicate "T-1 prices" table.
* No hard-coded instrument-level lag flag.
* No automatic use of data received after the historic information cut.
* No generic nested rules language or valuation-committee workflow UI.
