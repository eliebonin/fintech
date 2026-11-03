# Non-ETF ETP then spot-crypto P&L implementation plan

> Execute sequentially with the planning, test-first and executing-plans skills. Preserve the existing dirty checkout; no subagents, automatic commits or pushes.

**Goal:** Close the two immediate booking-versus-P&L gaps identified and accepted on 28 October, in order: exchange-traded wrappers, then spot digital assets.

**Architecture:** Share governed cash-product classification below the HTTP adapter, preserve actual wrapper/asset types, and reuse the immutable security price/FX/execution bridge. Freeze original listing factors; do not reapply wrapper underlying exposure or crypto currency-role factors. Existing permissions, rights, calendars, corporate-action safety, staging and publication remain authoritative.

**Tech stack:** Python Decimal, SQLAlchemy/PostgreSQL, FastAPI, existing React/Next inspector.

**Spec:** User direction: implement the recommended next products in order, focused on vital supplied-price P&L. Broader futures, bond and standalone option subtypes remain separate subsequent increments; this run closes the two explicitly recommended immediate gaps.

## Constraints and decisions

- Support ETC, ETN, ETV, ETI, EXCHANGE_TRADED_VEHICLE and EXCHANGE_TRADED_CERTIFICATE, retaining their product identity. Generic ETP resolves its effective concrete kind, rather than becoming an ETF by default.
- Preserve historic booked quantities, factors, prices and definition IDs. New cash snapshots bind product/unit and effective generic ETP terms; old snapshots retain original evidence with explicit unambiguous effective-term classification where needed.
- Use quoted whole-security prices, not underlying spot/index levels or an issuer indicative value silently substituted for an exchange quote. No extra leverage, commodity entitlement or embedded fee multiplication.
- Extend reviewed same-security unit-ratio replay to the wrappers, preserving all review/fraction/order/source guards. Crypto forks, migrations and redenominations are not share splits and remain unsupported transformations requiring Ops handling.
- New wrapper/spot-crypto quantities are UNITS. Older SHARES labels remain unchanged in the ledger; holdings and valuation normalize that label to UNITS with explicit evidence, so new sales offset old purchases. No price/quantity/factor rescaling. The same label correction preserves the existing fund NAV path; equity/ETF labels remain unchanged.
- Spot crypto retains exact listing identity and fractional quantity. No venue netting or substitute exchange prices. Native RAW daily marks use configured governed cuts/calendars; weekend coverage is tested explicitly. No automatic stablecoin USD peg, invented FX, staking/fork income or perpetual/futures support.
- Quoted zero boundary values are valid for these funded/spot assets when supplied, including native RAW under AS_TRADED; negative/missing prices and positive values that underflow to zero are not. Original cash execution validation remains.
- Preserve existing ETP monetary-preview behavior under actual subtype classification; broader crypto monetary measures are outside this P&L slice.
- Use existing economic-flow roles; no generated distributions, cash-countertrades or maturity postings. Conditional notes retain the separate CLEAN/DIRTY framework.

## Review focus

1. Missing/ambiguous generic ETP terms or conflicting frozen classification must fail explicitly, not become ETF.
2. Listed factors apply once. Whole-wrapper price is not underlying exposure; share-ratio review stays mandatory.
3. Token fractions, shorts, new trades, partial/full sales and zero marks reconcile exactly.
4. Kraken/Coinbase listings and stablecoin/fiat quotation currencies remain distinct; missing selected-listing marks/FX fail without substitution.
5. Weekend cuts, availability/information times, tenant/strategy/source rights and publication evidence retain their existing checks.

## Tasks

- [x] 1. RED→GREEN ETP quotation/product/position/unit-ratio tests; implement shared classification, frozen booking evidence and generic-ETP holdings normalization without changing economic values.
- [x] 2. Real ETP bookings, source selections, unit factors, new/short/closed holdings, ratio evidence and stage/amend/publish checks in disposable PostgreSQL.
- [x] 3. RED→GREEN spot crypto fractions, multiple listings, zeros and currency/FX cases; extend native RAW configured-cut selection and preserve historical unit labels.
- [x] 4. Disposable crypto weekday/weekend and missing exchange/FX checks; same review/publication and authorization regressions. No operating financial writes or source grants.
- [x] 5. Readable per-product inspection guidance, focused frontend/browser tests, current capability/methodology/root documentation and local activation where needed. No full Python suite.

## Research and verification ledger

Best-practice sources checked 28 October:
- [SEC ETN bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-50): legal identity, market versus indicative value and embedded leverage differ from ETF/underlying exposure. We reuse arithmetic without relabelling the security.
- [CME/CF crypto benchmark FAQ](https://www.cmegroup.com/articles/faqs/cme-cf-cryptocurrency-benchmarks-faq.html): London/New York/APAC daily rates are distinct observations. The project requires configured cuts and calendar coverage, rather than inferring one universal crypto close or acquiring licensed benchmark data automatically.

Completed 28 October. [Delivery and limits](../../delivery/etp-spot-crypto-pnl-20261028.md).

- Final offline numerical, normalization, architecture and repository-neutrality checks: **117 passed**. OpenAPI export check passed.
- Final native ETP/crypto booking and P&L file, against a new automatically migrated/seeded/dropped database: **31 passed**. Covers historical unit netting, real fund bookings, actual separate crypto exchange listings, reporting FX, source-right revocation and tenant denial, plus staging/publication.
- Earlier adjacent disposable runs: **62 passed** across the initial product cases, price-basis valuation, cash-booking integrity and economic flows; **31 passed** across note P&L, AMC measures, strategy holdings and selected fund/crypto boundary cases. A focused final classification/authorization run passed **10** cases. These runs overlap; counts are not additive.
- Frontend calculation, coverage, strategy workspace and listing-readiness checks: **40 passed**; TypeScript passed. Two isolated Edge browser journeys passed, including readable exact inputs, narrow-screen display, inspector close and console guard. Screenshot inspected.
- Local operating schema read-only verification: **20261028_102**. API **8001** reloaded and `/health` returned OK. No migration, permission/source grant, operating booking or valuation was performed. No full Python suite, commit or push.

Implementation rulings from the regressions:

- Crypto requested-day OPEN coverage is mandatory: a closed Saturday previously reused Friday even with zero freshness. The fixed selector still permits explicitly configured lag/prior-price allowances on a calendar covering the requested day.
- Legacy generic ETP quantity-only views use the original definition's parent when older CASH snapshots omit it. Missing financial proof still cannot become valuation evidence.
- Generic ETP remains the canonical instrument/policy/licensing identity; concrete terms classify its economic adapter without silently granting subtype data rights.
- The local PostgreSQL container was stopped during verification. Restarted it and retried isolated tests with a bounded connection timeout. Fixture errors were corrected without disabling immutable definitions or changing financial guards.
