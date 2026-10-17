# Bond coupons: schedule, earned interest and payment confirmation

Agreed design, 15 October 2026. The user approved documenting, planning and implementing the three separated aspects without another plan-approval loop.

## Non-negotiable economics

1. Daily assessed earned interest continues through `nav.daily_accrual_input` into daily P&L. Already-recognised earnings are not earned again on coupon payment.
2. The canonical bond owns contractual coupon periods, dates, currency and sourced amount/rate/formula metadata. This is informative reference data and future DCF input, not strategy income or evidence of payment.
3. A strategy's actual coupon receipt/payment is a separate, sourced Ops confirmation. It has zero additional interest P&L and does not automatically mutate accrual inputs, create a trade or update an EoD cash balance.

Example: previous accrual 990, daily earnings 10, coupon payment 1,000. Interest P&L is 10. The informative schedule and confirmed payment both show 1,000 only where the relevant nominal/source establishes that amount; the schedule's per-100 quotation is not automatically the strategy's entitlement.

## Scope and architecture

Deliver explicit sourced schedules and payment tracking, reusing existing lifecycle UI/authentication. Do not build a receivable engine, accounting journals, automatic coupon-accrual generator, automatic entitlement calculator or discounted-cash-flow pricer. Existing daily-accrual valuation remains numerically unchanged. Future unpaid coupon asset-value/FX treatment remains a separate gap, not silently solved by a payment label.

Generic `secm.schedule`/`schedule_event` lack tenant ownership, versioned source overrides and coupon-period economics. Add three dedicated tables: tenant-owned bond schedule versions, typed coupon periods and append-only strategy payment revisions. They reference canonical bonds and governed currency/calendar/day-count data. They do not mutate shared/global bond terms. Tenant-specific sourced schedules are visible only in that tenant, not generic reference catalogues.

Each schedule version retains approved bond terms identity, currency, optional calendar/day-count/business-day convention, source reference, override/revision reason, actor/real operator, timestamps and hash. Periods retain stable human coupon keys, accrual start/end, explicit payment date, optional record/ex dates, rate, amount per 100 nominal and/or formula. Unknown amounts remain null. No weekday-only date generator or fabricated fixing; explicit dates can include contractual preceding adjustments. Rows are explicit coverage, not a claim that the entire lifetime schedule is complete or pricing-ready.

Schedule maintenance requires REFERENCE_APPROVE: this directly publishes an informative reference schedule, not a proposal bypass granting Ops approval authority. No new grants are seeded. Lifecycle readers inspect schedules in a permitted strategy context and visible instrument scope. Canonical bond terms/currency must be known. Unsupported zero-coupon schedules are rejected rather than inventing payment rows.

Payments require strategy-scoped LIFECYCLE_BOOK and confirmation; reads require LIFECYCLE_READ; corrections/reversals require TRADE_CORRECT, consistent with existing lifecycle correction authority. A payment is informational, not a ledger booking, so no TRADE_WRITE is needed solely for this record. Retain actual payment date, signed nonzero amount, currency, source reference, note, optional owned cash account, selected actor and real operator. Positive means received; negative paid. Payment currency can differ from contractual currency without invented FX. Do not infer full settlement/entitlement from one receipt: partial receipts are separate confirmations.

Correct/reverse by appending a revision linked to the original logical payment; never overwrite history. Changes to contractual schedules retain old versions and payment references. Replaying a key requires unchanged content and current authority. Matching active receipt fingerprints cannot be accidentally recorded twice under different keys. No automatic notification claiming payment merely because its scheduled date passed.

## API/UI

Under `/v1/lifecycle/coupons`: scoped options, schedule read/version history, sourced schedule version publication, date-filtered paginated payment report, confirm/correct/reverse and revision history. Server filters/counts apply to the full owned population before pagination. UI is accessible from lifecycle navigation: strategy/bond selection, contractual schedule, payment report and explicit sourced forms. Restrict BFF paths and forwarded query parameters; context stays server-authenticated.

## Safety and acceptance

Tests pin exact decimal strings, null unknown versus zero, period order/duplicates, source/revision conflicts, immutable DB evidence, tenant/strategy separation, authority after retries, future payment rejection, corrections/reversals and pagination. Demonstrate that confirming a coupon does not alter daily interest, ledger rows, cash balances or valuation figures. Read/write no operating financial records for acceptance; use disposable DBs. Operating migration and API restart require separate activation approval. Preserve current dirty checkout and use sequential implementation/focused tests per user preference.

## Research basis and limits

The preceding best-practice check opened [DTCC distributions overview](https://www.dtcc.com/products-and-services/asset-services/corporate-actions-processing/distributions), [May 6, 2026 service guide](https://www.dtcc.com/-/media/Files/Downloads/legal/service-guides/Service-Guide-Distributions.pdf) and [Euroclear Sweden](https://www.euroclear.com/sweden/en/for-privatpersoner/vanliga-fragor-privatpersoner1.html). They distinguish announcements, entitlement and actual allocation/payment; market-specific record/payment dates must not be universalised. The tables/permissions/UI here are project engineering choices, not a prescribed industry schema or accounting certification.
