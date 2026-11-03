# Cash booking service extraction

**Accepted:** 29 October 2026. First trading-domain extraction after API phases 1–3.

Create a root `trading/` package. `booking.py` owns cash-booking orchestration,
`booking_contracts.py` the original command validators and a minimal booked-trade
identity result, and `booking_store.py` persistence/fingerprints. Extract only the
required supporting reference, annotation, recognition and linked-correction
functions into cohesive modules. No trading module may import the API or FastAPI.

The API retains response/detail projection, context, errors, custom audited routes
and outer commit/audit. The Excel/CSV confirmer calls the same shared command and
retains its existing all-or-nothing batch transaction, identity and receipt.
Existing template product restrictions are unchanged; no product is added or removed.

Preserve aliases/schema, strict Decimal handling, request fingerprints, endpoint
lock namespaces/order, current tenant/action/strategy checks before replay,
retired-reference replay, dated approved definitions, governed choices/parties,
recognition metadata, immutable BOOKED snapshots and append-only corrections.
Commands use the supplied Core Connection and a savepoint, never commit or open
an engine. A failed command leaves the caller transaction usable. The API's
projection remains within a savepoint so its failure cannot leave booked effects.

Return only the trade identity from the command; existing detail DTOs remain
API-owned. Preserve old public imports through identity re-exports where callers
still use them. Shared correction helpers move, while cancellation HTTP/workflow
and the other product writers remain for later extraction. No schema, UI,
operating-data change, provider call, automatic restart, commit or push.

## Research basis

Opened/read 29 October 2026: [original service-layer guidance](https://www.cosmicpython.com/book/chapter_04_service_layer)
supports sharing orchestration across entry points; no abstract repository/UoW
framework is required here. [SQLAlchemy 2.1 Core savepoints](https://docs.sqlalchemy.org/en/21/core/connections.html#sqlalchemy.engine.Connection.begin_nested)
allow local rollback inside the caller's outer transaction. Keep audit and batch
receipts in that outer effect transaction; a savepoint release is not a commit.
[FastAPI modular application guidance](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
supports HTTP adapters in the existing application. Retain this application's
audited route subclass and function-scoped dependency. These are engineering
recommendations applied to the current Core/FastAPI stack, not regulatory rules.

## Acceptance

Pin pre-move schema hashes and booking fingerprints; unchanged OpenAPI is required.
Test trading imports with HTTP blocked. Use owned disposable databases for native
command/API/import parity, frozen inputs, governance failures, reference/history
boundaries, current rights on replay, concurrent keys, linked replacement, late
failure rollback and audit failure. Focused tests only; no full Python suite.
