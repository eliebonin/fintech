# Cash-booking domain extraction

**Date:** 29 October 2026. **Status:** completed cash slice of API phase 4.
Broader decomposition remains partial (BACKEND-009).

## What changed

| Owner | Responsibility |
| --- | --- |
| `trading.booking_contracts` | Original cash command and nested property/reference/correction/recognition models; minimal frozen `BookingResult(trade_id)`. API response DTOs remain separate. |
| `trading.booking` | Current action/strategy authority before replay, new-execution validation, orchestration and local savepoint. |
| `trading.booking_store` | Original request fingerprints, endpoint lock namespace, annotations, execution and BOOKED event persistence; replay ownership check. |
| `trading.cash_reference` | Original locked visibility, currencies, current/dated approved definitions, product basis, venue and factors. |
| `trading.annotations` | Original typed values, governed choices/parties/traders, required fields, tag/reference validation, source locks and selection helpers. |
| `trading.recognition` | Original UTC/default/override recognition metadata and frozen representation. |
| `trading.corrections` | Original supported-chain checks and append-only linked replacement helpers. Cancellation orchestration remains API-owned. |

The API's `book_listed_cash_trade` is now an adapter: call the shared command,
then project the existing response. The Excel/CSV confirmer calls that same native
command and uses its trade ID directly. Its reviewed payload, source row identity,
revalidation, all-or-nothing transaction and receipt are retained; its existing
equity/ETF/fund template scope is unchanged. Other product writers continue to
use their current API paths and shared helper exports pending later extraction.

Original command/helper imports remain identity re-exports where existing callers
need them. No duplicate validators, alternate financial formulas, framework or
second booking implementation was introduced. New domain consumers import their
actual owner. External CSV reconciliation remains optional tooling; the isolation
guard now includes the new trading package and regulatory reporting.

## Integrity and transaction boundaries

- Current actor/module/action/strategy checks still precede idempotent replay.
  Exact retries may survive retired references/strategies; revoked authority cannot.
- The fingerprint algorithm and `/v1/trades` retained retry namespace stay exact.
  BOOKED source facts, quantities/sign, unit/quote factors, dates, annotations,
  recognition and correction lineage retain their original representations.
- The native command returns only execution identity. Replay also verifies that
  the retained identity belongs to the tenant and requested strategy; it does not
  reapply today's reference eligibility to historical evidence.
- Commands accept a caller-owned Core Connection and own only a local savepoint.
  They construct no engine and never commit/roll back the outer transaction.
  The API wraps response projection in its own savepoint: a failed detail read
  rolls back the already successful inner command. Removing the redundant route
  savepoint keeps **two base savepoints** on the HTTP path; existing external-reference
  savepoints are unchanged. Direct compatibility-wrapper calls gain the enclosing
  projection boundary; native/import calls avoid the API detail read entirely.
- The request transaction still commits effects and mandatory request audit
  atomically. File effects, source identities, job status and receipt stay in the
  caller's batch transaction. Library calls retain BOOKED actor/source evidence;
  they do not fabricate an HTTP request audit when no such context exists.

## Baseline defect corrected

Before extraction, the correction matrix reproduced SWAP HTTP booking failing
with “Instrument currency changed while acquiring booking locks.”
`generic_swap_booking.load_generic_swap_context` assigned the currency lock
helper's `(currency_id, currency_roles)` result to a single variable, then compared
that tuple with the instrument UUID. It now unpacks the result. No currency lock,
ordering, current-definition check or actual currency-change refusal was removed.
Successful unit-swap/correction tests and two genuine discovery-drift cases pass.

## Verification

- Pre-move OpenAPI and all eight fixed command-schema hashes passed. The small
  baseline had **13 passes and one unrelated existing valuation retry-identity
  expectation failure**. The broader pre-move DB baseline had **92 passes / one
  SWAP failure**, described above. Both failures were observed before source edits.
- New boundary RED tests failed for missing `trading`; after extraction, **54
  focused offline checks passed**, covering schema/recognition/boundaries and
  transaction finalisation. The **final 62 offline checks passed**, adding export
  identity, caller-transaction guards, repository neutrality and optional-tooling
  isolation. The complete OpenAPI check also passed unchanged.
- **12 focused disposable DB checks passed**: nine native command/API/import,
  concurrency, recognition and rollback cases; the former SWAP correction failure;
  and two genuine currency-discovery drift cases.
- **145 focused disposable DB regressions passed** across cash integrity/booking,
  file import, governed fields/roles, enrichment, property storage, cancellation
  and linked corrections for cash, FX forward, option, future, bond, structured
  product and swap, plus swap-unit/failure-rollback cases. Fault-injection targets
  moved to the new function owners; original rollback assertions were retained.
- Exact executable AST comparison confirms **28 moved models/helpers**, fingerprint,
  annotation persistence and execution/BOOKED insertion retain their original
  logic, excluding import relocation. Command orchestration deliberately returns
  an identity instead of an API read response, with the documented replay guard.
- **1,486 scoped local Markdown links resolve**. Root guidance/knowledge/findings,
  the implementation register and current diagram ownership are reconciled.
  Embedded and standalone Mermaid match; updated SVG/PNG renders without browser
  errors and was visually inspected. Whitespace checks pass. Saved pre-extraction
  source/database inventory counts remain explicitly historical.

One regression invocation initially used a nonexistent test selector and collected
no tests; it was corrected before the successful 145-case run. No passing result
was inferred from that aborted collection. Existing SQLAlchemy/Starlette and a
Pydantic header-alias warning were emitted; their broader cleanup is outside this
source-boundary change.

The separate pre-existing valuation retry-identity assertion still expects an
older shape than `valuation.storage.request_identity` (missing current
`calculation_contract`, retaining default false `require_complete_accruals`). It
is unchanged and recorded as [TEST-001](../../FIX.md#test-001--p3--valuation-retry-characterization-has-a-stale-expected-identity).
This extraction does not alter valuation identity or claim a clean whole-project
suite. No full Python/browser suite was run; no frontend behaviour changed.

No operating migration, provider request, operating trade/valuation write, service
restart, commit or push. DB checks used owned disposable databases and their
ordinary migrated synthetic fixtures; operating records remain unchanged.

## Remaining work

Extract other product booking workflows, cancellation orchestration and reference/
proposal services incrementally. Template catalogue/read views and file workflow
orchestration still live in the API; the shared effect command is the completed
slice. Central schema/resolver responsibilities and metadata bootstrap remain a
separate foundation task. Compatibility imports can be removed after their
remaining documented consumers migrate; retained financial retry evidence is not
a second active code path.

See [accepted scope and primary guidance](specifications/cash-booking-service-extraction.md),
[implementation plan](../superpowers/plans/2026-10-29-cash-booking-service-extraction.md),
[current architecture](../architecture/atlas/README.md), [root guidance](../../AGENTS.md),
[reviewed knowledge](../../KNOWLEDGE.md) and [remaining findings](../../FIX.md).
