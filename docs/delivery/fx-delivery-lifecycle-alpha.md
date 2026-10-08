# FX delivery lifecycle alpha

**Date:** 2026-10-06. **Status:** Implemented; isolated browser acceptance is blocked by local browser policy and remains outstanding.

## Decision and boundaries

Implement the first contractual lifecycle slice as explicit delivery evidence for a booked deliverable FX forward. Keep booking corrections separate. Do not build a universal position, cash posting, netting or accounting engine.

Two alternatives were considered: generic “settled” flags on every trade (too ambiguous), and a complete obligation/allocation ledger (premature without holdings and posting ownership). The bounded FX workflow uses the two immutable booked currency obligations. It records partial confirmations, exact retries and explicit reversals. The original execution is unchanged. Both legs must be fulfilled before the operational delivery status is DELIVERED. Maturity alone gives DUE, never DELIVERED. This status is not a valuation result or a cash balance.

The read projection is based on saved BOOKED economics, never current instrument terms. Each confirmation contains a leg (RECEIVE/PAY), positive currency amount, actual effective UTC timestamp and evidence reference. Currency is inherited, not user-entered. Actual delivery cannot precede contractual settlement or be in the future. Failed/missing transfers remain outstanding; this slice does not send instructions or declare a failure from elapsed time.

Use the existing append-only trade event table with versioned `FX_DELIVERY` payloads. Events do not supersede the BOOKED event. A reversal references one unreversed confirmation, retains its evidence, and is recorded at an explicit effective time no earlier than that confirmation. Recompute totals excluding reversed confirmations. No event can overfill a leg; unsupported/malformed chains fail closed. Original trade lifecycleStatus remains BOOKED: booking validity and delivery progress are separate axes. Correction of a record with contractual evidence remains blocked, even after reversal.

Current active TENANT_ADMIN + TRADING is required for writes, including retry; trade ownership is checked through strategy. Lock the trade, require current sequence for new events, hash normalized trade/request/key and save retry evidence atomically. Identical retry precedes stale sequence checks. Reuse the booking BFF tenant/key/body guards and uncertain-result retry pattern. Reads use existing tenant-scoped trade access.

## High-level remaining product sequence

1. FX delivery evidence (this slice).
2. Option expiry, exercise and assignment: require positions/lot allocation and explicit delivery obligations, not automatic expiry or an opposite trade.
3. Bond/note redemption and distributions: operate on eligible holdings, not the quantity of an arbitrary purchase trade; principal and coupon are distinct.
4. Futures expiry/final settlement and swap resets/termination: separate exposure changes, observations, amounts due and actual transfers. Neither reset frequency nor maturity confirms payment.

These later slices are documented follow-up modules, not claimed delivered by the FX workflow. Historical booking and record correction already have their own delivered contract.

## Implementation checklist

- [ ] Pure decimal replay and request validation: partial/two-sided fulfilment, reversals, bad chains, amounts and dates (red then green).
- [ ] Locked tenant-scoped API writes, idempotency, permission revalidation and atomic rollback; HTTP contract/error coverage.
- [ ] Detail UI: independently derived delivery progress, inherited currencies, explicit evidence/time, review/confirm, frozen retry, reversal and audit labels.
- [ ] API contract generation, focused and broad automated checks, isolated browser acceptance and sequential author review.

## Verification checkpoint

- Pure lifecycle replay: 15 passing checks, including partial delivery, two-leg completion, reversal, invalid evidence and high-precision decimal replay.
- Isolated FX delivery plus existing correction suite: completed without failures. The FX API coverage exercises partial delivery, both legs, reversals, immutable original booking status, retry/idempotency, stale sequences, tenant opacity, revoked authority and HTTP contracts.
- Delivery-control component test: 6 passing checks; TypeScript project check and OpenAPI contract drift check pass.
- An isolated API process on port 8007 served the existing synthetic FX booking as `PENDING`, with EUR 1,000,000 and USD 1,100,000 outstanding. The disposable UI on port 3007 compiled and served `/select-tenant` successfully.
- The browser automation then blocked navigation to the disposable preview after a local connection failure. No browser-policy bypass was attempted. Manual browser acceptance is still required for the final UI interaction proof.

## Research read 2026-10-06

- [FINOS CDM event model v7.0.0](https://cdm.finos.org/docs/event-model/): immutable product facts, reconstructible trade state and separate quantity/reset/transfer operations support keeping booked economics and subsequent delivery evidence distinct. CDM supports many-to-many events; the per-forward simplification here is not a universal allocation model or CDM conformance claim.
- [BIS foreign exchange risk guidance](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/rma/20): final receipt matters separately from expected settlement; both currency flows matter. This bank-focused guidance motivates operational accuracy, not a regulatory compliance claim for this alpha.

Storage, authority, timestamp restrictions and delivery sequence above are project design choices inferred from those distinctions and the existing code.
