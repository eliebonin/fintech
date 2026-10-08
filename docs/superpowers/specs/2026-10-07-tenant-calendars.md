# Tenant fund and strategy calendars

## Intent and scope

Extend the existing cal domain, not a disconnected calendar engine. Tenant administrators with MARKET_DATA may publish immutable, attributed calendar versions and assign them to tenant strategies or visible fund reference nodes. Members can inspect and preview. Existing exchange calendars remain platform reference data. No exchange/reference mutation, automatic financial operation, licence grant or valuation/P&L implementation.

## Calendar semantics

Purpose is explicitly VALUATION, DEALING or SETTLEMENT. A tenant schedule is either WEEKDAYS (explicit operating weekdays), ALL_OPEN (all selected reference calendars open), ANY_OPEN (at least one selected reference calendar open), or EXPLICIT (an administrator's dated published schedule). Combinations use dated governed sessions and holidays, not country/domicile guesses; no coverage becomes UNKNOWN, never OPEN. CLOSED defeats ALL_OPEN; OPEN satisfies ANY_OPEN; otherwise unknown propagates. Reference holidays alone prove closure, never coverage of other days. Existing reference sessions and holiday entries must agree, otherwise UNKNOWN. Weekends are not inferred for a reference calendar without coverage.

Tenant coverage is an explicit inclusive interval of at most 1,100 days. Dated OPEN/CLOSED exceptions require reason and source and take precedence within coverage only. Explicit schedules may leave dates UNKNOWN. Every materialized result retains the component/exception reason in immutable definition evidence. Changes publish a new version; removing a holiday means an OPEN exception or removing an exception in a new version, not deleting reference data. Published rows and their sessions are DB-protected against mutation. Calendar local decision time/timezone is independent of exchange close time.

## Assignments and selection

An append-only, idempotent assignment pins one version to exactly one strategy or fund reference node, for its calendar purpose and effective date interval. Reassignment for the same target/purpose/effective interval creates a later recorded decision; overlapping but unequal intervals are rejected to avoid ambiguity. Historical resolution uses only assignments recorded by its information cutoff. Calendar versions cannot be used before they were recorded. Assigned dates beyond coverage are unresolved, never implicitly open.

Only VALUATION assignments affect market-data resolution. A closed strategy calendar yields NOT_EXPECTED / STRATEGY_VALUATION_CLOSED for every requested input, without price selection. A closed fund-subject calendar yields NOT_EXPECTED / FUND_VALUATION_CLOSED only for NAV series, never the listed market price. UNKNOWN yields MISSING / CALENDAR_NOT_ASSESSED. Open decisions attach assignment/version/day evidence to new snapshot items. Old snapshots remain unchanged; existing pricing targets still use their own market calendars. Default policy and explicit rule calendar references must be global references or tenant-owned versions, never another tenant's version. Legacy rules remain supported but assigned calendars apply before price selection.

## UI/API

Market data → Calendars provides reference and tenant version inventory, coverage preview with reasons, editable schedule configuration, dated exceptions (including an explicit dated-schedule paste/import), and assignment form for strategy or fund UUID. Read-only members cannot create or assign. Selected tenant comes from signed server context. Bounded queries, generated contracts and stable idempotency keys. New versions are not silently assigned; existing assignments are visible and pinned.

## Sources and rulings

[BlackRock 2026 schedule](https://www.blackrock.com/uk/literature/shareholder-letters/bfm-schedule-of-non-business-days-2026.pdf), read 2026-10-07: fund-specific exclusions may differ from market holidays and even precede a market closure. It explicitly describes non-dealing days, not a universal NAV calendar. [QuantLib joint-calendar implementation](https://raw.githubusercontent.com/lballabio/QuantLib/master/ql/time/calendars/jointcalendar.hpp), read 2026-10-07: holidays joined by union versus business days joined by union are distinct operations. ALL_OPEN / ANY_OPEN names make this explicit to users.

Design inference: audited tenant-owned versions, coverage and separate purposes suit this platform. Not a regulatory certification. Automated administrator feed ingestion and checker approval are future integrations; alpha uses attributed administrator publication. Source-calendar evidence is frozen during creation so later reference edits cannot rewrite tenant schedules.
