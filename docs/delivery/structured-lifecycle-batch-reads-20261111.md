# Structured lifecycle batch reads — 11 November 2026

**Status:** Implemented and locally activated. This replaces the interim per-contract lookup-cache mitigation; existing instrument, worklist and inspection response contracts are unchanged.

## Problem and change
The portfolio worklist reused a single-instrument detail loader for87 traded roots and65 structured references. The original reader made4458 queries. A first request-local identity/label cache reduced this to2258 and restored availability, but retained per-contract source-table reads. The original pagination tests used many strategies holding one source contract and did not catch breadth across distinct contracts.

[TermsScheduleBatch](../../security_master_schema/instrument_terms_batch.py) now loads the authorised source graph breadth-first, up to the existing depth bound. It reads applicable definitions, dates, swap terms/legs, structured terms, fixings, conditions, actions, coupon data, composition, options, wrapper/preference-share terms and schedules in table-wide ID batches. Parameter chunks contain up to500 IDs; there is no instrument or event population cap. Empty relationships do not issue empty SQL queries. Rows are indexed and merged in primary-key order, preserving exact Decimal/date/UUID values without JSON aggregation or float conversion.

[One projection renderer](../../security_master_schema/instrument_terms_schedule.py) serves both single-instrument Terms & Schedule and bulk reads. Rendering performs no SQL and has no unbatched fallback. The prior scalar-cache class was removed. The [worklist](../../lifecycle/worklist_structured.py) batches schedule states and visible canonical/listing identifiers before per-root/event work. Source lookup count follows relationship tables, graph levels and parameter chunks rather than instruments or observations.

## Preserved controls and behavior
- Tenant/module/strategy read scope and retained assistance selection still precede candidates. ACTIVE reference and existing tenant visibility predicates apply to roots, dependencies, funding references, component/condition targets and schedule owners.
- The source store belongs to one connection, tenant and transaction. It is not process/global state and cannot be reused across these scopes. New requests reread current source data.
- Missing, private, inactive, cyclic or over-depth dependencies make only the affected root unavailable. Hidden IDs/names do not appear in its public projection. Other valid roots remain available. The original per-root visited/depth guard applies even when a dependency was separately prefetched as another root.
- Complete source fields, primary-key/schedule ordering, quote precision, current versus BOOKED-reference comparison, fingerprint contents and lazy-inspection stale-source checks remain. Historical owner schedules still participate in the existing source projection; discovery continues to use only current-linked observation rows.
- Immutable ledger validation, cancellations/corrections, recognition dates, joint allocation preservation at net0, historical event context, information-only states and conditional-payment/outcome boundaries are unchanged.
- Full-population filtering, totals, source/underlying and visible listing-identifier search, sorting and pagination remain. Financial handlers and write/replay/approval controls are untouched.
- The worklist's existing bounded30-second BFF read budget remains; it was not increased again. Ordinary lookup and financial-write budgets retain their separate policies.

## Measured results
Read-only, fixed-cutoff FCPGF comparison using the same requested window2026-10-12–2028-12-11. Three trials per implementation, rotating order; the table reports median local timings, not a production latency guarantee.

| Reader | SQL queries per request | Median seconds |
| --- | ---: | ---: |
| Original per-contract reader | 4458 | 9.632 |
| Interim scalar-cache mitigation | 2258 | 5.063 |
| Batched source graph | **89** | **1.310** |

All270 complete event records (266 upcoming,4 date-passed), all87 full contractual source projections and inspection contexts/proofs for the available coupon/autocall kinds were equal to the frozen pre-change reader. This comparison covers all events, not merely the first25 displayed rows. Current source rendering has no retained legacy implementation in product code; frozen comparison readers and timing reports are ignored task artifacts.

After API restart, the actual frontend BFF→API request returned HTTP200,270 total/25 loaded rows in**1.796seconds**; structured inspection also returned200 with outcome NOT_ASSESSED. Browser/session/API overhead is included in this latter observation. The independent verification context was revoked. These local observations cover this dataset; larger source graphs, parameter chunks and per-strategy ledger reconstruction can still increase cost.

## Regression evidence
[Distinct-contract and graph tests](../../tests/test_structured_batch_reads.py) use native bookings on24 additional distinct swaps, each referencing a distinct structured instrument. At equal dependency depth, both small and expanded populations used102 queries; visible reference search used104. The tests impose an absolute120-query budget and bounded growth, plus correct full counts and later pages. The old implementation failed the breadth regression with833 queries.

Additional tests force one-ID chunks and assert identical complete source/proof output; isolate a private/missing root among valid neighbours; retain four-layer wrapper/preference-share facts and exact redemption thresholds/terminal branches; reject over-depth and cyclic roots despite separately prefetched dependencies. A first adverse fixture attempted to mutate an immutable wrapper and was correctly rejected by the existing trigger. It was replaced with newly created immutable cyclic test contracts; no guard was disabled or changed.

31 distinct affected backend cases passed across bounded runs:30 passed in the combined source/worklist/HTTP group, and the corrected wrapper case plus10 overlapping lightweight cases passed in an isolated11-case rerun. Existing cases retain tenant/selected-read scope, no write inspection route, original reference mismatch, cancellation, unknown evidence, net0 allocations, source changes and whole-history pagination. [Source worklist tests](../../tests/test_structured_notifications.py) also assert SQL-free rendering after prefetch and fresh-request visibility checks. [Scope/rule tests](../../tests/test_structured_notification_rules.py) retain connection/transaction isolation.

OpenAPI contract and whitespace checks passed. No full project Python suite was run; existing dependency deprecation warnings remain outside this change.

## Activation and remaining limits
API8000 was restarted on existing revision115; no migration was applied. Activation retained trade, assistance-selection, subscription and audit counts. The subsequent short-lived HTTP verification created only ordinary context/audit records and ended its own context. No operating financial data, permissions, strategy settings, valuations or Toolhive services were changed. Frontend3001 remains available.

The graph depth/cycle boundary and current-approved-source semantics remain explicit existing product limits. This does not add issuer fixings, outcome assessment, autocall/coupon entitlement, payment reconciliation, financial booking or a retained task queue. Ledger reconstruction remains per strategy; this is a correction of structured-source query amplification, not a claim that every backend query or scaling concern is solved.

[Authorised specification](../superpowers/specs/2026-11-11-structured-batch-reads.md) and [execution plan](../superpowers/plans/2026-11-11-structured-batch-reads.md).
