# Cash booking service extraction implementation plan

**Goal:** give cash booking a reusable trading-domain owner.
**Architecture:** `trading/booking.py`, `booking_contracts.py`, `booking_store.py`
plus required annotations, cash-reference, recognition and correction helpers;
existing SQLAlchemy Core and API transaction/audit adapters retained.
**Spec:** [accepted scope](../../delivery/specifications/cash-booking-service-extraction.md).
**Execution:** sequential in the authorised current checkout; preserve unrelated
dirty work, no subagents/commits/operating-data mutation.

- [x] Capture schema/fingerprint baselines and run focused current cash/import checks.
- [x] Add failing import-boundary/contract tests for the new domain owner.
- [x] Move command models and necessary helpers unchanged; retain API aliases.
- [x] Implement the shared command/store returning only trade identity. Preserve
      savepoint rollback; API detail projection stays in its enclosing savepoint.
- [x] Route the existing API wrapper and file confirmer through that command.
      Keep template scope, source identities and all-or-nothing receipt semantics.
- [x] Verify direct/API/import parity, current rights, concurrent retries, frozen
      reference/recognition/annotation evidence, corrections and audit rollback.
      Retarget fault injection to new owners without weakening its assertions.
- [x] Reconcile AGENTS/KNOWLEDGE/FIX, capability implementation links and diagrams;
      record tests, source guidance, remaining product/cancellation extraction and limits.

Ruling: three facade files alone would still import API-owned validation. The four
small supporting modules are required by the cash dependency closure, not a new
generic trading framework. The existing shared foundations remain reused.

Ruling: the API needs an outer projection savepoint around the command savepoint.
Remove the now-redundant extra route savepoint, retaining the same two base savepoints
for the HTTP path and the existing outer request commit/audit boundary. Direct
compatibility-wrapper calls gain the projection boundary; native commands own only
their effect savepoint. Prove rollback after a successful inner command as well.

Baseline: eight fixed schemas and OpenAPI pass. The larger cash/import/correction
baseline has 92 passes and one pre-existing SWAP failure: the generic loader
compares a currency UUID with the currency lock helper's tuple result. Fix that
unpacking in the caller and retain both the valid-booking and real-currency-drift
regressions. A separate existing valuation retry-identity test also has a stale
expectation for calculation_contract/optional-accrual fields; record it outside
this extraction, without changing the valuation contract or weakening its test.

Completion: 62 final offline checks, unchanged OpenAPI, 12 focused native/swap
database checks and 145 focused regressions pass. See the
[delivery](../../delivery/cash-booking-service-extraction-20261029.md) for scopes,
the unchanged stale valuation assertion and final documentation/render checks.
