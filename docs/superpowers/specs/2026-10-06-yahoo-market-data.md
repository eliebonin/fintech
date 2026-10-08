# Yahoo market data and layered rights

The local personal project needs real, inspectable daily equity history for the seeded S&P 500 and CAC 40 universe. Reuse the existing provider, dataset, mapping, series, vintage and observation model. Valuation, P&L, accounting, intraday cuts and commercial distribution are outside this delivery.

## Rights and operating scope

Delivery access is not a data-use licence. A dataset access profile records its operating scope, permitted local tenant, legal licensee, activation state and evidence. Each activity has one or more required licence assignments; all must be active, effective, belong to that dataset and licensee, and explicitly grant the activity. Missing requirements or grants deny access. Activities are ACQUIRE, STORE, DISPLAY, NON_DISPLAY, CLIENT_REPORTING, REDISTRIBUTE and DERIVED_DATA. Agreements can cover upstream rights through valid pass-through terms; a separate direct upstream agreement is not universally mandatory.

Personal scope accepts an explicitly labelled PERSONAL_DECLARATION, reflecting the owner's declared purpose rather than a legal determination. Commercial scope requires CONTRACT evidence. No commercial, reporting or redistribution grants are inferred. Yahoo personal activation is operator-only, local-only and restricted to one simulated tenant. No public configuration endpoint or universal tenant grant is added.

Yahoo acquisition has an additional reserved `AUTOMATED_SOURCE_ACCESS` prerequisite. It starts unassigned and denies acquisition until reviewed provider permission is bound to a valid dataset/licensee assignment. An owner purpose declaration cannot satisfy this prerequisite; it requires CONTRACT-basis evidence of the granted access (not necessarily a paid/commercial licence). Re-running onboarding preserves a separately reviewed assignment and never fills the missing permission automatically.

Existing synthetic datasets remain on their existing entitlement model. New onboarded sources require profiles and explicit grants. Legacy production datasets must be reviewed before migration to strict profiles; existing free-text descriptions do not become machine-readable grants automatically. Expired rights block new use without deleting retained evidence.

## Source semantics and acquisition

Use a small HTTP adapter over the public Yahoo chart response, using the existing HTTP client dependency. No cookie/crumb harvesting, browser impersonation, proxy rotation or access-control bypass. Bounded requests, timeout, maximum response size and no background scheduling. The initial no-429-retry policy was superseded on 7 October at the owner's request: three exponential retries (30/60/120 seconds), respecting longer Retry-After values up to 600 seconds, otherwise stopping. HTTP 401/403 still stop immediately; serial ticker requests are spaced five seconds apart. Network acquisition requires the local personal profile, satisfied ACQUIRE/STORE layers including provider permission, and an explicit operator acknowledgement. Acknowledgement alone never grants rights.

Preserve the provider's Close and Adj Close as separate series. Close is labelled SPLIT_ADJUSTED (not a guarantee of historical unadjusted exchange prices); Adj Close is VENDOR_ADJUSTED, reflecting provider adjustments. Neither is designated official. Provider bar timestamps are stored as source/economic bar timestamps, not invented session-close or publication times. Market dates derive from the provider timezone, checked against the mapped venue timezone. Receipt timestamps are real acquisition timestamps; backfills cannot fabricate historic knowledge.

Initial scope is daily equities with USD/EUR prices. No forward filling or fabricated missing sessions. Future authoritative venue calendars will support expected-session completeness; missing weekdays are not automatically called gaps.

## Mapping and publication

Seed proposed Yahoo identifiers against the dated universe using venue-specific suffixes and known class-symbol normalization. Verify each source response against symbol, exchange, currency and timezone before promoting its listing mapping. Ambiguous, missing, mismatched and malformed input is retained with an explicit rejection report, not attached to a guessed instrument. A provider-delivery symbol maps to the exact listing, not an arbitrary canonical instrument or another venue.

Retain the exact inbound JSON text and SHA-256 in a database-backed ingestion record and link existing source_payload, vintage and observations. Publication and idempotency identity commit in one transaction. The caller owns the transaction. Same delivery key plus same content is a no-op; the same key with different content is a conflict. Across new delivery keys, equal existing points are duplicates and changed values append observations linked to their predecessor. Previously accepted observations are never overwritten. Per-dataset transaction locking serializes overlapping imports.

The ingestion record freezes the evaluated rights evidence and accepted, duplicate and rejection counts. Current use rights are reevaluated independently from historical acquisition evidence. Display APIs must filter exact tenant scope and the actual observation dataset, not just the series default source. Current display history shows only latest accepted revisions; retained history remains available for later point-in-time replay.

## Evidence checked on 6 October 2026

- [Yahoo UK-applicable terms](https://legal.yahoo.com/ie/en/yahoo/terms/otos/index.html), last updated 8 July 2026 and read in the browser on 6 October 2026 after the web reader returned 999: section 2(d)(ix) requires express prior permission for automated collection; sections 2(e), 2(h) and 2(i) distinguish commercial restrictions, reuse and software/API use. Personal purpose alone does not establish automated-access permission. Keep the declaration separate and require the access layer before another acquisition attempt.
- [yfinance maintainer guidance](https://github.com/ranaroussi/yfinance): research/personal intended use, no Yahoo endorsement; software licensing is separate from rights to downloaded data.
- [yfinance download documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) and [price parsing implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/utils.py): Close and Adj Close are different source columns; automatic adjustment can substitute adjusted prices. The direct adapter performs no such substitution or repairs.
- [Yahoo adjusted close explanation](https://in.help.yahoo.com/kb/adjusted-close-sln28256.html): dividend and split adjustments. Provider historical history is not automatically an official raw-price tape.
- [Euronext agreement types](https://www.euronext.com/en/data/pricing-specs-agreements/data-agreements-types): redistributor delivery and subscriber/non-display requirements can coexist; requirements depend on activity, delay and contract.
- [AWS idempotent API guidance](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): atomically record request identity and effects; changed content under the same identity is not a successful replay. PostgreSQL implementation is our design choice, not an AWS dependency.

## Acceptance

Lightweight tests cover layered AND semantics, wrong licensee, date boundaries, personal versus commercial evidence, price basis, malformed/null/nonfinite values, exchange/currency/timezone mismatch and rate-limit behavior. Disposable PostgreSQL tests cover schema constraints, idempotent replay, changed-key conflict, append-only corrections, frozen evidence, rollback and API tenant/rights filtering. Operating activation must preserve existing reference identities, trades and synthetic observations; begin with a small real-data smoke test before a wider universe import.
