# Composite pricing policy alpha

## Approved intent

One tenant/strategy policy selects each listing's exchange-session close and a separate FX fixing for valuation date T. A common information cutoff controls eligible receipts/revisions independently of pricing timestamps. Extend the existing resolver and snapshot boundary, not valuation/P&L calculations or ingestion. Implement sequentially in the current feature checkout, without automatic commits/pushes or licence activation.

## Contracts

Existing rules default to LEGACY and retain existing selection behavior. New conventions are SESSION_CLOSE, NAMED_FIXING and EXPLICIT_TIME. Rules add market_venue_id, pricing_cut_id, fixing_code and value_basis. Market venue is derived from the selected listing; never guess a listing from instrument currency/country. Precedence: exact series, exact subject, venue plus type, venue, type, default; sequence resolves ties. Failed specific rules do not fall through to broader rules.

SESSION_CLOSE selects declared closing series by market/session date, not a daily bar's opening timestamp. Calendar evidence derives from dated governed cal sessions where available, otherwise supported versioned exchange schedules, explicitly labelled comparison evidence. Unknown calendar coverage is an exception, not weekday guessing. Closed dates select the preceding completed session; missing data on an open session follows the rule's explicit tolerance/action. Local times use IANA zones, actual early closes and DST. Information before the target cannot select a future closing mark.

NAMED_FIXING requires an exact fixing_code series dimension and matching pricing_cut_id; Yahoo daily FX/equity bars are not certified fixings. EXPLICIT_TIME uses eligible timestamped observations no later than the local target and rejects source-daily-bar timestamps. Source/dataset and value-basis filters are explicit. New-rule lag and staleness use the chosen calendar, not generic weekdays. Preserve source labels and rights enforcement (including NON_DISPLAY).

Snapshot items freeze pricing evidence: rule convention/filters, selected pricing listing/venue, target date/time, calendar/timezone/source/version, information cutoff and exceptions. Old snapshot evidence stays null; do not invent historical evidence. New managed policy versions are immutable and attributed; optional strategy ownership is tenant-validated. Legacy policy payload fingerprints remain unchanged when the new optional strategy context is absent.

## UI/API

Tenant MARKET_DATA members can list/read configuration and run a bounded, read-only preview; tenant MARKET_DATA administrators can create immutable policy versions, with idempotent submissions. Provide options, policy detail, create/version, and preview routes in a focused API module. Existing active-policy and frozen-snapshot routes remain compatible. Configuration/preview page is reachable from Market data. Show rules, versions, exceptions and selected input evidence; no hidden price repair, licence grant, price import, valuation or cash mutation.

## Acceptance

Mixed US/UK/Paris closes and separate London FX fixing under one information cutoff; deterministic overrides; no foreign tenant access; holidays versus missing open sessions; early close/DST; late receipts and revisions; fake fixing/daily-bar rejection; immutable versions and snapshot evidence; legacy replay compatibility; lightweight tests first, isolated DB/API tests, frontend tests/typecheck, full Python suite last. No changes to existing operating observations or trades.

Source context: NYSE auction times https://www.nyse.com/trade/auctions and WMR named London fixing https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks . These identify conventions, not permission to acquire benchmark data. Prior ingestion calendar evidence remains non-authoritative.
