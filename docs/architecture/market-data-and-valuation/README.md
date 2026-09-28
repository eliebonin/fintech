# Market data and valuation

**Status:** Accepted  
**Content type:** Architecture index  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-09-10

`market_data_series` identifies one economically precise observable stream; observations are immutable and selected under an explicit valuation context. Local cut-offs, calendars, source vintage, corporate-action basis, and entitlement must be reproducible in a valuation snapshot.

Primary detail: [marks and trades](../../../security-master-notes/03-market-data-marks-and-trades.md), [dates/schedules](../../../security-master-notes/05-dates-and-schedules.md), [indices and FX](../../../security-master-notes/09-indices-fx-forwards-and-market-data-architecture.md), [corporate actions](../../../security-master-notes/10-corporate-actions-and-adjusted-market-data.md), [tenant Soft NAV](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md), [pricing-date resolution](../../../security-master-notes/17-soft-nav-pricing-date-resolution.md), and [coverage/provenance](../../../security-master-notes/21-market-data-coverage-and-provenance.md).

Current decision: [series measurement semantics](series-measurement-semantics.md).

Future attribution direction: [P&L attribution subjects and cost ownership](pnl-attribution-subjects.md).
