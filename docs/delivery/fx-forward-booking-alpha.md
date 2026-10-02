# Deliverable FX-forward booking alpha

Implemented and engineering-accepted for booking alpha 2026-10-01. Approved [design](../superpowers/specs/2026-10-01-deliverable-fx-forward-booking-design.md) and [plan](../superpowers/plans/2026-10-01-deliverable-fx-forward-booking.md). Full-suite/browser evidence, deployment prerequisites and scope limits are in the [quality review](quality-reviews/2026-10-01-fx-forward-booking-alpha.md). This is not production or valuation sign-off.

Deployment prerequisite: migrate to Alembic head (`20261001_54`) before starting updated code. Sign-off fixes include nullable bond coupon columns and synthetic demo-definition bootstrapping; no live database migration was performed during acceptance.

## Operator workflow

Open **Book trade** from the menu, then choose **Deliverable FX forward** (`/trades/new?product=FX_FORWARD`). Listed cash remains the default and its existing listing context is supported.

Search economic contracts by name or code, then select an eligible contract. Results include explicit ineligibility reasons and Load more for subsequent pages. No artificial listing is created. Select an active tenant strategy, BUY/SELL, positive base-currency amount, offset-aware execution timestamp and governed counterparty. Optional broker, trader, purpose, typed custom properties, governed dropdowns, tags, source references and comment reuse the cash configuration. OTHER purpose requires a comment.

Rate, currency convention and settlement date are read-only facts inherited from the instrument. Review shows the two obligations, then confirm one immutable record of an already-executed trade. This does not send an order. Back to edit preserves annotations; uncertain outcomes can only retry the original frozen payload, idempotency key and tenant. A conflict blocks further submission and requires checking history before reopening/reselecting.

## Economic semantics and supported scope

For EUR/USD, `USD_PER_EUR`, agreed rate 1.10:

| Side | Positive ticket amount | Receive on settlement | Pay on settlement | Stored quantity |
| --- | --- | --- | --- | --- |
| BUY | 1,000,000 EUR | 1,000,000 EUR | 1,100,000 USD | +1,000,000 |
| SELL | 1,000,000 EUR | 1,100,000 USD | 1,000,000 EUR | -1,000,000 |

The single trade has an economic instrument subject, no listing/venue, RATE price basis, CURRENCY_AMOUNT quantity unit, and quote-currency price. Obligations use Decimal arithmetic on the server and BigInt decimal multiplication for the browser preview. Ticket quantity permits up to 18 integer and 12 fractional digits; no floating-point arithmetic is used to store amounts or calculate obligations.

Eligible contracts require an ACTIVE/tradable/current instrument, ACTIVE type/currencies, a current APPROVED/effective definition consistent with the base/type, complete terms, distinct currencies, positive rate and normalized `{QUOTE}_PER_{BASE}` convention. The API locks/revalidates authoritative definitions and terms at submission. Tenant-private scope and TRADE_WRITE remain enforced server-side.

This slice supports DELIVERABLE only. Maturity supplies settlement when explicit settlement, cash-settlement and final-settlement dates are absent or agree with it. Conflicting dates block booking with an actionable error; legacy terms are never rewritten. Execution must be offset-aware, within instrument effective dates and on/before settlement using the UTC execution date. FX never gets the cash ticket's weekday T+2 default.

NDF, CASH-settled forwards, reverse convention, separate currency payment dates, FX swaps, options, early termination/correction and accounting settlement postings remain outside this booking alpha. A catalogue counterparty selection is not credit approval or legal confirmation matching.

## API and replay contract

| Endpoint | Purpose |
| --- | --- |
| GET `/v1/trades/fx-forward-instruments?q=...&limit=25&offset=0` | Tenant-visible contract search, eligibility and pagination metadata |
| GET `/v1/trades/fx-forward-instruments/{instrument_id}` | Authoritative terms, eligibility and terms fingerprint |
| POST `/v1/trades/fx-forwards` | One FX execution, required Idempotency-Key |
| GET `/v1/trades` and `/v1/trades/{trade_id}` | Existing tenant history/detail with optional FX economics snapshot |

The booking payload includes instrumentId, strategyId, side, quantity, tradeDatetime, counterpartyOrganisationId and expectedTermsFingerprint, plus annotations. It forbids listingId, executionPrice, settlementDate and marketActivity overrides. The BFF derives tenant/actor from the server session, requires X-Expected-Tenant-Id and rejects tenant switches before forwarding.

An endpoint/tenant/key advisory lock serializes concurrent retries. A committed same-key/same-normalized-request replay returns the same trade even after references retire. A changed request under the same key returns 409 `idempotency.key_reused`; a stale contract fingerprint returns 409 `fx_forward.terms_changed`. Invalid quantity/terms/dates and governed annotation errors return 422 with field locations; hidden or missing instruments/strategies return 404. Invalid or unauthorized actors receive 403. Persistence is savepoint-atomic, including annotation/reference failures.

The first BOOKED lifecycle event contains schemaVersion=1, kind=FX_FORWARD_BOOKING, base/quote IDs and normalized snapshot economics. History/detail read this snapshot in a batch, not current terms. They show precise rates and base amounts, OTC and receive/pay obligations. Instrument-term changes do not alter historical economics.

## Valuation boundary

Existing display-only cash P&L is not an FX-forward engine. A queried strategy containing booked FX forwards as of the requested date returns 422 `valuation.fx_forward_unsupported` before scalar-rate selection or totals. The frontend labels VALUATION UNSUPPORTED and shows no partial numerical total. Cancelled or future-execution trades follow the existing lifecycle/as-of filtering.

Later work must distinguish provider forward rates, adjusted marks and monetary MTM, retain raw observations, govern discount curves/collateral assumptions, and reconcile with custodian results. Custodian agreement with simple rate differences does not prove embedded discounting. No guessed discount curve or silent DF=1 fallback was added.

## Research traceability

The approved design's [external evidence](../superpowers/specs/2026-10-01-deliverable-fx-forward-booking-design.md#evidence-and-scope-of-conclusions) records OpenGamma FX/payment/PV/discount-factor models, collateral assumptions, historical CME FX MTM methodology and ESMA reporting guidance. Source links and applicability caveats are also summarized in the [evidence register](../research/evidence-register.md). The single-date deliverable restriction is a project alpha choice, not an industry-wide assertion.
