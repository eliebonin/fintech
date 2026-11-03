# Separately priced rate-exchange swaps

**Status:** Bounded alpha implementation; activation evidence recorded below  
**Content type:** Delivery record  
**Owner:** Trading and valuation engineering  
**Last reviewed:** 2026-10-30

## User intent and representation

A bank can describe a four-leg economic arrangement through two separately
priced two-leg swaps: bond income versus floating rate, and that floating rate
versus another currency's floating rate. Each remains its own instrument, trade,
bank time series, RESET attribution and P&L. The application does not create a
consolidated price or replace the two instruments with a package instrument.

The new [`RateSwapTerms`](../../security_master_schema/rate_swap_terms.py) variant
records exactly two opposing floating legs. Each has a governed rate reference,
currency, positive contractual notional, signed decimal spread, day count,
calculation/observation evidence and reset/payment frequencies. Shared effective,
maturity, booking basis, quotation and source facts are explicit. NOMINAL and
UNITS bases remain distinct; partial bookings scale the reference contract.
The original performance-swap model and its frozen JSON representation remain
unchanged. The proposal API schema is intentionally extended, not a change
hidden under the earlier extraction's compatibility baseline.

Existing database structures suffice: immutable versioned economics JSON,
`swap_terms` CROSS_CURRENCY/INTEREST_RATE categories, two numbered FUNDING legs
and ordinary booking conventions. FUNDING represents each floating funding
stream; no fictitious equity-return profile is assigned. No migration is needed.

## Governance and retained identities

[`trading.rate_swaps`](../../trading/rate_swaps.py) owns reference facts and
materialization below the HTTP adapter. Submission/approval retain existing
REFERENCE_PROPOSE/REFERENCE_APPROVE authority and tenant visibility. References,
currencies and day counts are checked again at approval and booking. Currency
roles are locked together in deterministic order before contract rows; booking
reuses that captured population and rejects changed roles before later locks.

Normal creation produces a new instrument. Guarded first-time completion can
also retain an existing private, non-tradable SWAP reference, with its expected
current definition and retained tenant/shared source receipt. Already configured
contracts, foreign references, stale definitions and references with position
executions are refused. Completion supersedes only the allowed current/status
metadata, appends a sourced approved definition and activates the same identity.
Old definition contents, price series, observations, RESET references and BOOKED
evidence remain retained. This is not general swap amendment or contract novation.

OTC booking continues through the shared writer, current strategy authority,
counterparty/annotations, terms fingerprint and idempotency. The complete variant,
materialized legs and quotation are frozen. Cancellation and linked booking-error
replacement remain the existing SWAP workflow; they are not contractual closure.

## Price-based P&L

The existing whole-swap bridge applies signed quantity, supplied component mark,
quote divisor and reporting-currency FX once. It validates the frozen rate legs
against their approved contract rather than treating a rate as a performance
index. It does not multiply by either leg's contractual notional, rate/spread or
gearing again. Leg currencies do not create extra strategy positions or require
separate rate-curve pricing when a compatible whole-contract mark is supplied.
Recorded RESET flows remain separate dated economic inputs.

A focused synthetic example has two separately marked contracts, each booked
at quantity 100 with divisor 1: marks 0.995→0.997 produce +0.20 and marks
1.004→1.003 produce −0.10. The strategy stages two separate attribution items
with combined market P&L +0.10. It does not net away the contracts or combine
their input price series.

## Frontend

`/instruments/swaps/new` offers **Performance swap** and **Rate versus rate**.
The latter collects both legs and presents their reviewed currencies, notionals,
spreads in basis points, frequencies and source evidence before approval.
Existing context transport, expected-tenant protection, retained uncertain retry
keys and navigation protection apply. Booking and instrument/trade details render
the same typed leg summary with names from approved/frozen facts. The page guide
explains the distinction and that principal/payment facts do not generate cash.

## Explicit limits and source completion

- This variant covers two floating legs, not a universal fixed/floating,
  inflation, credit, optional or multi-leg pricing framework.
- It reuses the current whole-swap quotation convention: quote and contractual
  booking-basis currencies agree; each leg's currency/notional is independent.
- Frequency labels do not establish complete fixing/payment schedules. There is
  no generated interest, cash, principal exchange, FX reset, maturity closure or
  curve-based valuation.
- Rate-exchange position monetary/risk measures are not defined by the index
  performance-swap preview. They remain explicitly unavailable; supplied-mark
  P&L is supported independently.
- The [FCPGF exercise](fcpgf-reconciliation-import-20261030.md) infers USD-leg
  notionals from the separate exported USD companion bookings. Effective dates,
  overnight compounding/day counts and quarterly reset conventions are disclosed
  completion assumptions. Principal exchanges and exact observation calendars
  remain unassessed. Source-specific pairing stays in optional reconciliation
  tooling, outside application packages and product tests.
- The owner clarified that the bond-side reference pays **income**. Earlier
  source completion used a gross-total-return profile; that is not confirmation
  of an income-only contractual payoff. Existing signed quantities, marks and
  BOOKED evidence are preserved. Exact income-only contractual modelling and
  source quote orientation need confirmation before relying on generated
  cashflows or underlying-risk measures. No such generation is implemented here.

## Verification and activation

Focused verification covers strict terms/precision, opposing legs, native
approval and status revalidation, stale/foreign completion refusal, stable
reference/series identity, booking/retry and independent-mark calculation/staging.
Frontend checks cover mode selection, readable leg summaries, exact spreads,
tenant changes, unchanged retries and existing performance-swap behavior.

- The owned-disposable regression run passed **173 Python tests**. The final
  rate-swap file passed **7 integration checks**, including real HTTP proposal/
  approval/booking/cancellation, independently staged marks, correction evidence
  and changed-currency refusal. These checks overlap; they are not 180 unique tests.
- The final focused frontend run passed **90 tests across 10 files**. TypeScript
  checking and OpenAPI export parity passed. No full Python/frontend suite or
  production build was run for this increment.
- The operating import approved/booked all four rate components. Replay reused
  the same identities; frozen proofs validated. All **383 source position rows**
  now map uniquely to native trades, alongside **1,002 RESETs**. There are **1,385
  records**, zero unposted source rows and no partial-import label.
- Fingerprints confirm the four original series and all **88 observations** are
  unchanged, as are every RESET row and the other strategies' **162 trades**.
  Detailed private reports are indexed by the [source delivery](fcpgf-reconciliation-import-20261030.md).
- API 8000 and frontend 3001 were restarted. Browser smoke checks confirmed the
  rate creation mode, loaded currency/day-count catalogues, readable SOFR/SONIA
  terms and zero captured console errors. A stale server-rendered label module
  was cleared by restarting the frontend. No financial actions were submitted
  through the browser; posting used the explicit native operator.

No migration, permission grant, generated payment or operating valuation run/
publication is part of this change. Posting completeness is distinct from full
portfolio pricing-policy/financial acceptance and confirmed contractual terms.

## Primary guidance checked on 30 October 2026

[OpenGamma's swap model](https://strata.opengamma.io/swap/) separates product legs,
pay/receive direction, notional/currency, accrual and payment schedules from the
trade. Its [swap loader](https://strata.opengamma.io/trade_loader_swap/) supports
explicit per-leg terms and cross-currency conventions. These support our typed
leg representation; they do not confirm source-specific contractual assumptions.
Reusing supplied whole marks without introducing a new curve pricer is the
bounded project decision for this increment.

For the UI, [W3C WAI form grouping](https://www.w3.org/WAI/tutorials/forms/grouping/)
supports separate fieldsets/legends for related pay/receive fields, and the
[GOV.UK check-answers pattern](https://design-system.service.gov.uk/patterns/check-answers/)
supports reviewing the entered contract before submission. These guide grouping
and review; backend validation and immutable approval remain authoritative.
