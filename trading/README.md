# Trading domain

The current slice is **listed-cash booking, typed fund-unit movements and rate-swap reference materialization**. Other product writers and
cancellation orchestration remain in the API pending incremental extraction.

Read `booking_contracts.py` for original validated inputs and the minimal execution
identity result, `booking.py` for the command flow, and `booking_store.py` for
retry fingerprints and persistence. `cash_reference.py`, `annotations.py`,
`recognition.py` and `corrections.py` are its required shared dependency closure.

Use `book_cash_trade(connection, tenant_id, actor_id, request, idempotency_key)`
inside a caller-owned transaction. The command checks current authority before
replay and rolls back its own savepoint on failure. Callers own outer commit,
request/operator audit and batch receipts. Preserve exact retry/event bytes;
do not import HTTP adapters or construct an engine here.

The API supplies existing detail DTOs. File confirmation uses the returned
`trade_id` directly and keeps its existing product scope and atomic batch.
See [delivery and focused verification](../docs/delivery/cash-booking-service-extraction-20261029.md).

`position_movements.book_fund_unit_movement` records approved fund TRANSFER and
REINVESTMENT unit changes with frozen classification/recognition evidence. It
shares authority, reference validation, annotations and persistence without
relaxing ordinary positive-price purchases. No cash or income is generated.
Caller-owned audit/commit and retry rules apply. Existing cancellation supports
validated movements; linked replacement through a purchase ticket does not.
See [financial conventions and limits](../docs/delivery/fund-unit-movements-20261030.md).

`rate_swaps` validates the governed two-floating-leg reference population and
materializes ordinary or guarded first-time sourced-reference completion in the
caller's transaction. The API still owns proposal/approval and shared product
booking orchestration. Keep both leg currencies locked before contract rows;
never replace two separately priced components with one price or instrument.
See [rate-swap delivery and limits](../docs/delivery/rate-exchange-swaps-20261030.md).
