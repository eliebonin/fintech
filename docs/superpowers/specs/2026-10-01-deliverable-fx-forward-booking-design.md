# Deliverable FX-forward alpha: design proposal

Date: 2026-10-01
Status: Design approved by the user on 2026-10-01; detailed implementation plan awaits review.
Repository inspected: C:/Users/forte/Elie/projects/python/fintech.
This workspace copy is a review artifact, not yet canonical repository documentation.

## Intent

Extend the dedicated booking page to book one trade against an approved, tenant-visible OTC FX-forward instrument without inventing a listing. Reuse strategies, governed counterparties/traders, tags, properties, review, idempotency and trade history. Book first; introduce independently verified valuation data in a separate delivery slice.

## Existing implementation

- `docs/architecture/fx-forward-onboarding-2026-09-08.md`: one economic instrument, no venue listing; terms contain the pair, quote convention and agreed rate. Existing onboarding accepts DELIVERABLE, NDF and CASH and optional settlement dates that may follow maturity.
- `apps/reference_api/contracts.py::TradeBookingRequest`: presently requires listingId, executionPrice and settlementDate.
- `apps/reference_api/repository.py::book_listed_cash_trade`: presently writes a listing subject, UNIT_PRICE, SHARES and a venue. Shares/rate semantics cannot be reused unchanged.
- `security_master_schema/models.py::trade`: already accepts an instrument subject, RATE price basis, CURRENCY_AMOUNT quantity and nullable venue. New trade-identity tables are not justified.
- `apps/ops-console/src/app/trades/new/`: existing enriched ticket, review and governed property components should remain shared where their semantics match.
- `apps/reference_api/repository.py::portfolio_pnl`: existing display-only price/FX calculation must not implicitly treat newly booked forwards as cash securities.

## Approaches

1. Recommended: instrument-backed FX booking mode beside unchanged listed-cash booking, with shared annotation and submission controls. Explicit product semantics; minimal risk to working cash flows.
2. Universal booking redesign: normalize all products now. Broader contract and regression surface than this alpha needs.
3. Synthetic listings for OTC: reject; falsely introduces venue/quotation identity and contradicts existing instrument architecture.

## Booking design

- Initial scope: DELIVERABLE forwards with one already-agreed, resolved settlement/value date. NDF, CASH, FX swaps and split currency dates remain unbookable through this slice.
- Instrument identifies base currency, quote currency, quote convention, agreed rate and date. Different rates/dates represent different terms, not ticket overrides. Do not automatically merge unrelated bilateral contracts just because their economic terms match.
- For this alpha, booking supports the normalized quote-currency-per-base-currency orientation. Existing arbitrary or reverse quote conventions must be recognized and rejected with an actionable enrichment message until conversion support is explicitly specified; never guessed.
- Quantity is a positive input amount in base currency. BUY receives base/pays quote; SELL pays base/receives quote. Store signed base quantity using existing trade convention.
- Rate and settlement are read-only inherited terms. API resolves them authoritatively; client values, if echoed for stale-context detection, cannot override terms.
- Persist one instrument-backed trade: execution_price = agreed rate; price_basis = RATE; price_currency = quote currency; quantity_unit = CURRENCY_AMOUNT; venue absent. Retain base currency and quote convention in history/detail economics, not as ambiguous labels.
- Require an active governed counterparty for the bilateral forward. Reuse existing optional trader, broker, purpose, tags, custom properties and references. No PRIMARY/SECONDARY requirement for OTC.
- Display derived receive/pay amounts in booking review and detail using decimal arithmetic. They are contractual obligations, not two trade records and not immediate cash bookings.
- Do not debit quantity times rate at execution. No automatic settlement postings, fees, cancellation or early termination are introduced in the booking slice.
- Preserve cash API compatibility. Introduce explicit FX request/dispatch semantics rather than making every required cash field optional. Detailed endpoint and type signatures follow written-design approval.

## Settlement resolution

For the simple deliverable alpha, maturity is defined as the resolved contractual value date, not an unadjusted schedule date. Do not apply the generic T+2 booking default.

- If explicit final/settlement dates exist and all agree with maturity, use that common date.
- If no explicit settlement date exists, use maturity under this explicitly adopted simple-deliverable convention.
- If any supplied settlement/final/cash date conflicts, reject booking with an enrichment exception. Do not alter historical terms or apply a blanket migration.
- Validate that execution is not after settlement. Any business-calendar validation must use configured currency calendars and fail visibly if required calendars are unavailable; never silently approximate currency holidays using weekdays only.
- Business-day adjustment rules, unadjusted maturity inputs, split dates and NDF fixing/payment dates are a later confirmation-enrichment slice.

## Security, lifecycle and operational controls

Enforce tenant instrument visibility, booking permission, active strategy, eligible instrument status, complete approved terms and governed counterparty/properties at submission, not just search. Revalidate stale ticket terms before committing. Preserve existing annotation history and idempotent replay; a retry cannot create a duplicate. A changed request with the same key must conflict. No access to another tenant's instrument or catalogue is permitted through forged IDs.

## Market-data and valuation boundary

Booking does not imply supported valuation. Existing P&L must expose an explicit unsupported-FX exception rather than compute quantity times exchange rate as derivative value or quietly omit the position from an apparently complete total.

Separate follow-on design:

- Preserve raw provider rates/MTMs, units, source, timestamps, cutoff, reference notional, perspective and resolved value date. Unverified provider semantics remain ineligible for authoritative valuation.
- Distinguish outright forward rates, discount-adjusted contract valuation rates, normalized MTMs and monetary MTMs.
- Import documented discount-curve snapshots initially rather than build calibration infrastructure. Curves are selected by collateral/valuation policy, not currency alone.
- Use consistent exact-maturity forward and discount inputs. For an unchanged simple long-base position, quote-currency MTM is signed base notional times the applicable quote discount factor times (forward minus agreed rate). This is a clean valuation formula under consistent curve/collateral assumptions, not universal XVA treatment.
- Daily P&L requires successive monetary valuations, cash-flow handling and strategy-currency conversion; no blind discounting of already adjusted provider values, no silent discount factor of one.
- Settlement cash postings and lifecycle processing require their own tested accounting design.

## Delivery sequence proposed for review

1. Harden booking eligibility and authoritative FX economics/date resolution; test pure rules first.
2. Add instrument-backed booking API/storage with shared governed annotations and idempotency; regenerate API contracts.
3. Add OTC forward search and product-specific ticket/review within the existing menu booking page.
4. Render OTC economics in history/detail and prevent misleading existing P&L treatment.
5. Run stronger PostgreSQL/API/security tests, listed-cash regressions and isolated browser acceptance; document supported and deferred behavior.
6. Separately design provider semantics, curve ingestion and verified valuation/P&L after booking acceptance.

## Acceptance

Lightweight tests first: EUR/USD BUY and SELL, precise derived USD amount, inherited rate/date, conflicting dates, unsupported settlement/quote types, execution after maturity and absent terms.

Then robust tests: generic and tenant-specific forwards; cross-tenant instrument/strategy/counterparty rejection; retired governed values; failed transaction rollback; changed-context rejection; duplicate submission/replay; unchanged cash booking; history after reference retirement; FX valuation exception; browser book/review/retry/history for both directions with custom fields.

Reference example: BUY EUR 1,000,000 at 1.10 USD/EUR yields one booked trade and preview obligations of receive EUR 1,000,000/pay USD 1,100,000 on the inherited contractual date. SELL reverses those obligations. Neither creates an upfront USD 1,100,000 payment or claims a derivative MTM of that amount.

## Evidence and scope of conclusions

- [OpenGamma FX single model](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/fx/FxSingle.html): supports rate/amount/value-date representation, product date adjustments and potentially separate currency payment dates. Single-date restriction is our alpha choice, not a universal FX rule.
- [OpenGamma NDF model](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/fx/FxNdf.html): separate fixing-observation and payment economics; deferred here.
- [OpenGamma FX risk measures](https://strata.opengamma.io/fx_single/): forward FX rate and present value are distinct measures.
- [OpenGamma discount factors](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/DiscountFactors.html): factors obtained from currency/date-specific curves with zero-rate or discount-factor nodes and explicit day count.
- [OpenGamma collateral framework](https://quant.opengamma.io/Multi-Curve-Framework-with-Collateral-OpenGamma.pdf): collateral assumptions affect curve/valuation selection; OIS is not an unconditional universal rule.
- [CME published FX MTM method, 2012, pp. 3–4](https://www.cmegroup.com/rulebook/files/s_6105_otc_fx_pai_cash_mk_to_mkt_ser_020112_revised.pdf): rate difference, signed quantity and discount factor; daily variation differences MTMs. Historical methodology evidence, not a claim about all current clearing arrangements.
- [ESMA EMIR REFIT guidance, 2023, section 3.18](https://www.esma.europa.eu/sites/default/files/2023-10/ESMA74-362-2281_Guidelines_EMIR_REFIT.pdf): signed monetary contract valuations for applicable reporting. Does not prescribe internal database structure or universally apply to every tenant/jurisdiction.

## Review gate

The user approved the written proposal with "Good. Go through them". The next artifact is the detailed implementation plan. Implementation starts after its review; this design does not claim application changes, database migrations, app restarts or implementation commits have occurred.
