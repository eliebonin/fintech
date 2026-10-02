# OTC autocall-reference swap booking alpha

Date: 2026-10-02. Status: delivered and verified in an isolated environment; not activated against operating data.

## Delivered scope

The dedicated Book trade page now offers Swap. It searches eligible existing canonical OTC TOTAL_RETURN swaps, inherits the performance reference and funding terms, and records nominal, signed swap-value quote, strategy, legal counterparty and the existing governed trade annotations. Approved booking conventions can be proposed from instrument detail and approved through the existing Operations workflow.

There is one trade and one immutable BOOKED snapshot. No cash trade, payment, fee or settlement obligation is automatically generated. Swap settlementDate and listed execution are rejected rather than defaulted. The quote is the swap's value per notional, not the underlying's price or an upfront-only payment.

`entry reference value = signed nominal × quote ÷ quoteFactor`

BUY preserves the contractual holder orientation. SELL negates nominal, not the entered quote. Zero and negative quotes are supported. Factor 100 displays percentage points; other factors display their actual divisor. The review and history distinguish entry reference value from a payment or independently verified valuation.

## Eligibility and evidence

The alpha requires exactly one PERFORMANCE and one FUNDING leg, opposing directions, explicit aligned currencies, funding spread, an active rate reference, a supported total-return profile, explicit schedules, effective/maturity dates, and an approved visible structured-product autocall reference. An active/validated parent-targeting autocall redemption action and active/validated condition group are required.

Submit rechecks authoritative terms under transaction locks, including the underlying projection. Snapshot/fingerprint facts include conventions, definitions, legs, dates, payoff graph, schedules and dated events, including component-owned coupon observation overrides and range-accrual observation schedules. A changed funding spread or schedule invalidates the reviewed ticket. Historical views use the saved booking snapshot, not current reference terms.

Decimal arithmetic retains exact supported precision and rejects non-finite values, invalid factors/increments and out-of-range or inexact stored amounts. Existing tenant permissions, visibility, properties and idempotency paths are reused. Concurrent identical replay returns one trade; invalid properties roll back the transaction. Cash-only P&L fails closed when a strategy contains swaps.

## Verification

- Lightweight rules: initial missing-rule/convention failures reproduced, then 36 related pure tests passed.
- Initial backend compatibility: 59 swap/product/bond API tests passed in disposable databases.
- Frontend: 339 tests across 90 files passed with `--maxWorkers=2`; TypeScript, OpenAPI export check and production build passed. Unbounded parallel testing initially timed out two existing tests; bounded concurrency passed without changing their assertions or timeouts.
- Review regressions reproduced before fixing retired actions/groups, coupon override schedule closure and missing underlying projection lock. Final compatibility run: 82 swap/rules/product/bond tests passed (one dependency warning). A subsequent swap-only run passed all 25 tests, including required false/zero properties and an injected post-insert persistence failure that left no trade behind.
- Browser: isolated production UI3002/API8002; tenant choice, menu booking entry, swap search, read-only terms, zero quote, review/back/edit, SELL negative quote, optional custom property and immutable detail verified. BUY1000000 at0 and SELL1000000 at-1.5 produced exactly two swap trades and zero related other-subject cash trades. The latter stored quantity-1000000, unchanged quote-1.5 and entry reference value15000GBP. One BOOKED event each; no fees or settlement date. No operating tenant trades were created.
- Reviewed-code full Python run: 554 passed, 473 dependency/deprecation warnings, 860.48sec, exit0. Two additional test-only cases added after that run's collection are covered by the fresh 25-test swap run above. Existing SQLAlchemy tuples(), Pydantic field-alias and Starlette status-name warnings remain; they are not assertion failures.

## Explicit gaps and boundaries

- No tenant swap creation wizard: this slice books existing approved economic definitions; generic SWAP rows are not automatically eligible.
- No standalone manually booked cash-event ticket. Separate tenant-directed upfront/cost entries remain a follow-on workflow, not automatic behaviour.
- No valuation, MD mapping, funding accrual, resets, dividends, termination or settlement engine. OPEN/CLOSE metadata is not proof of position closure.
- Full funding schedule rows are retained in the snapshot but are not yet expanded as an event table in ticket/detail UI.
- The existing history adapter retains a local amountKind union because the legacy response exposes economics as a generic dictionary. Product context is generated from OpenAPI.
- Migration 20261002_59 extends the booking-convention kind constraint additively, preserving the forward-only migration policy. Isolated databases were migrated; operating-database activation and GitHub push are not part of this delivery.

Design decisions and research: [approved design](../superpowers/specs/2026-10-02-swap-booking-design.md). Execution details: [log](swap-booking-execution-log.md), [plan](../superpowers/plans/2026-10-02-swap-booking.md).
