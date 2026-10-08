# Historical booking and record corrections

Date: 2026-10-05. Scope: booking records, not valuation, positions, settlement or order execution.

## Decision and rationale

Reuse existing product writers, immutable BOOKED snapshots and the append-only `trd.trade_lifecycle_event` table. Deliver historical-date controls and cancellation/linked replacement of erroneous records. Do not introduce a second cash ledger or a general lifecycle engine.

Historical execution time is distinct from recording time. Authorize against today's active tenant/account/membership/module; evaluate supported reference facts against the execution's UTC date. Reject future UTC execution dates for a new recording. Today's date is allowed (this is a date rule, not a clock-skew/execution-time certification). Preserve authorized exact retries before new-write date/reference/strategy checks. Settlement is expected contractual settlement, never confirmation merely because its date passed.

Back-booking is supported only with current active/visible references and current approved definitions that cover execution. Dated booking-convention history already supported by product loaders remains supported. Retired references, superseded instrument definitions, missing/overlapping historic terms and reconstruction of old annotations are not an unrestricted historical-import path. No latest-definition fallback. An expired contract may be recorded for a valid past execution while its governed reference remains active and its dates cover that execution. FX and option reads/writes must use an explicit as-of date rather than today's date for effective terms. Cash/option premium settlement dates compare to UTC execution date consistently.

## Record corrections

Expose two clearly differentiated actions for tenant administrators with current TRADE_WRITE permission:

- Cancel erroneous booking: preserve execution/annotations/BOOKED evidence; append CANCELLED with reason, actor, original economic timestamp and recording timestamp; update only the record-status projection. This voids an erroneous ledger record, NOT an agreed contract or settlement obligation.
- Replace erroneous booking: re-enter a complete reviewed ticket using the existing product path, same tenant/strategy/product category. Validate current authorization and all product/annotation/date controls. In one savepoint create the replacement, append its CORRECTED predecessor link, append the original's SUPERSEDED successor link, update only original status, and register endpoint-scoped replay. Failure leaves the original active and no replacement remnants.

Both use expected lifecycle sequence and mandatory trimmed reason. Lock the original trade to serialize competing changes. Exact retry returns original evidence; changed payload/key is refused. Only known alpha BOOKED chains and replacement-origin CORRECTED links can be changed; unexpected lifecycle events fail closed. Existing legacy trades without BOOKED evidence cannot be silently cancelled/reconstructed. Cross-tenant originals are opaque 404. Repeated/replacement-chain corrections retain every predecessor.

The UI displays original summary and an explicit correction reason before the ticket, with no automatic copying of stale/retired governed values. Re-entering all desired annotations is intentional; omitted optional annotations do not carry forward implicitly. Original/replacement navigation and effective/recorded timestamps are visible in detail. No hidden edit-in-place route.

## Later lifecycle plan

Separate typed workflows for delivery/settlement evidence, expiry/exercise/assignment, bond redemption/coupons, swap termination/reset and dividends. Before implementing those, specify obligations versus confirmed transfers, partial amounts, holding/trade allocations, reversals and a single cash-posting authority. Passing maturity never automatically closes a record. OPEN/CLOSE is still execution intent. This delivery establishes correction lineage, not those economics. Existing cash-only P&L is not upgraded to historical correction replay; document that limitation and fail closed when corrected/cancelled history would otherwise produce misleading historical totals.

## Research read 2026-10-05

- [FINOS CDM 7 event model](https://cdm.finos.org/docs/event-model/): executions, states, transfers and business events are distinct; immutable product facts and lineage allow reconstruction. Used as an architectural reference, not a mandate to adopt CDM or all its workflows.
- [FIX TradeCaptureReportAck](https://fiximate.fixtrading.org/en/FIX.Latest/msg77.html?find=TradeReportID): correction/cancellation references identify prior reports. This informs explicit lineage; platform actions are record corrections, not a claim of exchange/FIX cancellation acceptance.
- [Microsoft event-sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing): immutable/compensating events, sequence/concurrency checks and idempotency support auditability, but wholesale event sourcing adds substantial complexity. Reuse one existing append-only table with transactional projections, not an app-wide rewrite.

Sources establish structural distinctions. UTC-day cutoff, conservative historical eligibility, same-strategy/category replacement and administrator workflow are project decisions, not regulatory requirements. No jurisdiction/compliance certification is implied.

Self-review: requirements covered by two staged plans below; no new tables, dependencies, operating-data mutation or automatic contractual events. User explicitly requested execution without another approval loop; sequential author review is weaker than independent review.
