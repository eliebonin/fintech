# Market data and valuation

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-10-09

`market_data_series` identifies one economically precise observable stream; observations are immutable and selected under an explicit valuation context. Local cut-offs, calendars, source vintage, corporate-action basis, and entitlement must be reproducible in a valuation snapshot.

Primary detail: [marks and trades](../../../security-master-notes/03-market-data-marks-and-trades.md), [dates/schedules](../../../security-master-notes/05-dates-and-schedules.md), [indices and FX](../../../security-master-notes/09-indices-fx-forwards-and-market-data-architecture.md), [corporate actions](../../../security-master-notes/10-corporate-actions-and-adjusted-market-data.md), [tenant Soft NAV](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md), [pricing-date resolution](../../../security-master-notes/17-soft-nav-pricing-date-resolution.md), and [coverage/provenance](../../../security-master-notes/21-market-data-coverage-and-provenance.md).

Current decision: [series measurement semantics](series-measurement-semantics.md).

Local activation update (2026-10-09): owner-approved backup, migrations through
81 and API/UI restart completed. Browser and financial acceptance remain separate;
this supersedes pending local activation wording in the implementation checkpoint.

Current code scope: [economic P&L implementation](../../delivery/economic-pnl-implementation-2026-10-09.md) extends the original single-currency alpha below with governed cross-currency attribution, canonical fund NAVs, clean bond marks with assessed daily interest, and explicitly recorded economic flows. Original source prices, booked trades and published financial versions remain immutable. Amendments create reviewed replacement candidates. This is not full NAV or settlement/accounting. Operating activation and browser sign-off remain pending; unsupported product economics fail closed.

[P&L demo retirement](../../delivery/pnl-demo-retirement-and-fresh-start.md) removes the old repository/browser calculator and synthetic portfolio pages; old API calls still return410. The replacement [market-only attribution alpha](../../delivery/valuation-market-pnl-alpha.md) adds a dedicated `valuation` package and `/v1/valuation` endpoints. `/valuation` now provides calculation attempts, frozen input inspection, staging and independent review/publication. It requires both VALUATION and MARKET_DATA modules. The first scope is single-currency listed equities/ETFs; it is not full NAV, total-return P&L, accounting or a substitute for missing market-data rights.

[Tenant fund/strategy calendars](../../delivery/tenant-fund-and-strategy-calendars-alpha.md) reuse the calendar domain with immutable tenant schedules and recorded-time version-pinned assignments. Valuation, dealing and settlement purposes stay separate. NAV_DATE pricing uses explicit fund valuation days; exchange calendars continue to govern underlying market prices. UNKNOWN coverage is not silently treated as an open day.

[Composite pricing policies](../../delivery/composite-pricing-policy-alpha.md) extend input selection with per-listing session closes, separate named fixings and immutable policy versions under one information cutoff. Configuration and preview are implemented; this does not activate data rights or calculate valuation/P&L. Legacy rules/snapshots retain their original semantics.

Daily equity ingestion/inspection is implemented in the [Yahoo personal-project alpha](../../delivery/yahoo-market-data-alpha.md). Close and Adj Close have separate adjustment bases; bars are not official prices or certified session-close timestamps. Valuation/P&L and authoritative completeness calendars remain outside this delivery.

Yahoo source corporate actions were imported on 2026-10-09: 79 split events and
8,073 dividend events, with original-payload provenance and five quarantined source
inconsistencies. They are unreviewed ANNOUNCED reference facts, not cash flows or
automatic position replay. [Import and evidence assessment](../../delivery/yahoo-market-data-alpha.md#corporate-action-import-and-evidence-assessment--2026-10-09)
records why this does not yet establish a complete split-only normalization proof.

The subsequent [derived as-traded RAW close implementation](../../delivery/yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09)
assesses full split-event coverage through each Yahoo snapshot's regular-market
reference date and appends RAW series, retaining source prices and normalization
lineage. Its explicit provider-method assumption replaces the earlier unspecified
certification requirement. Quantity replay, dividend recognition and commercial
source qualification remain separate.

The owner-approved [five-year backfill](../../delivery/yahoo-five-year-backfill.md) uses a separately labelled PERSONAL_RESEARCH_EXCEPTION, never CONTRACT evidence, on the local personal Yahoo dataset. Full-universe coverage and known short/missing histories are recorded with execution results.

The [ingestion module boundary](../../delivery/market-data-ingestion-boundary.md) separates provider adapters, daily publication/storage and shared rights from the reference API. Operator entry points live in `apps/market_data_ingestor`; acquisition is not part of API request handling. The existing repository/database remain shared, with import-boundary regression tests.

Future attribution direction: [P&L attribution subjects and cost ownership](pnl-attribution-subjects.md).

[Ingestion hardening](../../delivery/md-ingestion-hardening.md) adds durable operational evidence, explicit partial outcomes and historical-continuity reviews. Read-only coverage reconciliation uses versioned exchange schedules, without claiming authoritative calendar certification or rewriting prices.
