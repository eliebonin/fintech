# Major-exchange calendars and valuation unblock

**Status:** Implemented locally with bounded research coverage  
**Content type:** Delivery / Research  
**Owner:** Market data and valuation  
**Last reviewed:** 2026-10-13

## Outcome

Published **21 sealed 2026 schedules**: twenty major-market candidates plus BATS
for an existing listing. This is a practical universe/regional selection, **not
an exact ranking of the twenty largest exchanges**. Sixteen are ACTIVE; five are
REVIEW_REQUIRED and cannot be activated. Seven existing equity venues are connected:
XNYS, XNAS, XPAR, XAMS, XLON, XETR and BATS. No new venues were fabricated.
CME remains unchanged: derivatives schedules require product-specific treatment.

The user's October 7–8 calculation passed with a current information cutoff and
new **FLEXIBLE_EOD v3**, `01a1358a-e094-7031-8fdb-8bebe78afe47`: one position
line; GBP gross/net market P&L `18809.844746795076905898750000000000000000`,
including EUR→GBP conversion. Diagnostic snapshot writes were rolled back:
**no new attempt, staged financial batch, approval or publication** was created.
This is calculation acceptance, not custodian reconciliation or browser acceptance.
Subsequent [storage rounding fix](valuation-storage-rounding-20261013.md) addresses
the staging failure missed by that calculation-only check and records a successful
normal API calculation/staging attempt. No official financial publication occurred.
API restarted; `/health` returned HTTP 200. Frontend remains on port 3000.
The inherited Anaconda runtime lacked `psycopg`; restart now uses the project's
verified `.venv` runtime. Authenticated Paris calendar-days inspection returned
HTTP 200 with OPEN sessions for both October 7 and 8; frontend calendar page
returned HTTP 200. Repeated import returned the same 21 sealed IDs.
Start a new valuation request selecting FLEXIBLE_EOD v3 with a current information
cutoff; retrying the old frozen v2 request does not adopt the new configuration.

## Sources and quality

Actual schedule source: **pandas_market_calendars 5.5.0**,
[maintainer documentation](https://pandas-market-calendars.readthedocs.io/en/latest/).
The [registry](../../data/major-exchange-calendars-2026.json) retains review scope,
exchange links and activation decisions. Sources were researched October 13, 2026.
All imports explicitly retain `sourceKind=LIBRARY_SNAPSHOT` and
`exchangeCertified=false`. A verification URL is not proof that all session clocks
were independently verified. Sealing ensures immutability, not certification.

| MIC | Coverage/status | Primary source and review limitation |
| --- | --- | --- |
| XNYS | 2026 ACTIVE, connected | [NYSE](https://www.nyse.com/trade/hours-calendars): ten closures/two 13:00 early closes checked; core cash session only. |
| XNAS | 2026 ACTIVE, connected | [Nasdaq](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule): regular US cash equity session. |
| XPAR | 2026 ACTIVE, connected | [Euronext](https://www.euronext.com/en/trading/trading-hours-holidays): 2026 closure/half-day dates checked. Normal 09:00–17:30 and half-day 14:05 clocks are library conventions; the page's historical 2021 auction paragraph is not 2026 certification. |
| XAMS | 2026 ACTIVE, connected | Same Euronext source; regular equity session, not every auction/product phase. |
| XLON | 2026 ACTIVE, connected | [LSE](https://www.londonstockexchange.com/trade/trading-access/business-days): dynamic page limited retrieval; library close 16:30, not 16:00. |
| XTKS | 2026 ACTIVE | [JPX calendar](https://www.jpx.co.jp/english/corporate/about-jpx/calendar/index.html), [hours](https://www.jpx.co.jp/english/equities/trading/domestic/01.html): current 15:30 close and lunch break retained. |
| XSHG | 2026 ACTIVE | [SSE](https://english.sse.com.cn/start/trading/schedule/): retrieved English holiday page describes 2025; 2026 remains a library research snapshot. |
| XSHE | 2026 REVIEW_REQUIRED | [SZSE](https://investor.szse.cn/English/services/trading/calendar/index.html): retrieval failed; borrowed SSE candidate is not independently verified. |
| XHKG | 2026 REVIEW_REQUIRED | [HKEX](https://www.hkex.com.hk/News/HKEX-Calendar?sc_lang=en): library omits half-days. |
| XNSE | Jan 1–Oct 13 ACTIVE | [NSE](https://www.nseindia.com/resources/exchange-communication-holidays?apiversion=v2): future November 8 Muhurat hours unresolved; future coverage withheld. |
| XBOM | Jan 1–Oct 13 ACTIVE | [BSE](https://www.bseindia.com/): library research snapshot with same future-exception safeguard. |
| XTSE | 2026 ACTIVE | [TSX](https://www.tsx.com/en/trading/calendars-and-trading-hours/calendar): source returned 403; library research schedule. |
| XETR | Jan 1–Oct 13 ACTIVE, connected | [Deutsche Börse](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours): regular session; provisional December 30 hours excluded. |
| XSWX | 2026 ACTIVE | [SIX guide](https://www.six-group.com/dam/download/the-swiss-stock-exchange/trading/trading-provisions/regulation/trading-guides/trading-guide.pdf): equity 17:30; ETF 17:35 requires separate product treatment. |
| XASX | 2026 ACTIVE | [ASX](https://www.asx.com.au/markets/market-resources/trading-hours-calendar/cash-market-trading-hours/trading-calendar): closures and 14:10 half-days checked. |
| XKRX | 2026 REVIEW_REQUIRED | [KRX guide](https://global.krx.co.kr/contents/GLB/01/0109/0109000000/guide_to_trading_in_the_korean_stock_market.pdf): first-session/exam-day clock exceptions unresolved. |
| XTAI | 2026 ACTIVE | [TWSE](https://www.twse.com.tw/holidaySchedule/holidaySchedule?response=html): explicit 2026 schedule reviewed. |
| BVMF | 2026 REVIEW_REQUIRED | [B3](https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm): library clock conflicts with seasonal 2026 hours. |
| XSES | 2026 REVIEW_REQUIRED | [SGX](https://www.sgx.com/securities/trading): half-day eve exceptions unresolved. |
| XJSE | 2026 ACTIVE | [JSE](https://clientportal.jse.co.za/reports/trading-calendars): source identified but retrieval failed; library research schedule. |
| BATS | 2026 ACTIVE, connected | Library alias uses NYSE core rules; no independent Cboe certification. NYSE is the underlying shared-session verification link. |

## Implementation and evidence

[Importer](../../market_data/reference_calendar_import.py) writes explicit
OPEN/CLOSED/HALF_DAY rows, retaining timezone, breaks, package version, original
review manifest, warnings and schedule SHA-256. Shared publication preserves
provenance. Activation requires active platform-admin authority, a matching unique
MIC and an ACTIVE sealed calendar; the audit retains old/new calendar IDs.
Review-required calendars are excluded from valuation selection.

[Operator CLI](../../scripts/import_reference_calendar.py) previews by default.
Use `--registry data/major-exchange-calendars-2026.json --actor <platform-admin>`;
explicit local publication/activation adds `--apply --activate-venue`.
Publication is fingerprint-idempotent. No migration was needed.
Current Paris version: `3626ada4-0d7d-4570-bfc8-f9de144f0180`.
Earlier [Paris version/evidence](paris-reference-calendar-20261013.md) remains intact.
Activation IDs: `logs/major-calendar-activation-20261013.log`.

The separate FX blocker was a two-day research calendar and source coverage.
Yahoo daily/5-minute EURGBP and USDGBP refresh now reaches October 12. Exact
EURGBP London 16:00 completed five-minute samples were reviewed for October 6–12:
**research observations, not an official benchmark fixing**. A new personal
coverage package, licence evidence, sealed research calendar and policy version
were appended. Existing covering dataset grants are reused, not widened or
reactivated; old scoped grants keep package links and suspension still denies use.
Old policy/package evidence remains unchanged. Series classification itself is
a single current mapping, not historical classification versioning. These personal
declarations do not establish commercial Yahoo rights.

Logs: `logs/yahoo-fx-calendar-refresh-20261013.log`,
`logs/fx-valuation-calendar-activation-20261013.log`,
`logs/valuation-calendar-diagnostic-20261013.log`.
**55 focused tests passed** in an owned disposable PostgreSQL database, covering
calendar import/publication, FX configuration, valuation follow-up/storage,
composite resolution and Yahoo FX parsing. No full Python suite was run.

## Remaining limits

- Five quarantined markets need reviewed exceptions; three active schedules stop
  October 13. Not all twenty are certified or connected to existing venues.
- Only 2026 is populated by this delivery; annual/historical schedule maintenance
  needs an operating owner and acceptance process.
- Venue activation changes the current default pointer. Frozen run evidence stays
  immutable, but this pointer has no as-of assignment history: an information
  cutoff before new publication may block rather than reconstruct its old default.
- Equity schedules are not derivatives, bank, settlement or fund calendars.
  Tenant fund schedules stay separately governed; FX research weekends are not
  a licensed settlement-holiday calendar.
- Missing prices still block valuation. Calendars do not fabricate observations,
  relax freshness or bypass rights.
