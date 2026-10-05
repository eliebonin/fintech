# Booking consolidation

**Status:** Scope approved; written design awaiting user review  
**Content type:** Design specification  
**Owner:** Engineering delivery team  
**Last reviewed:** 2026-10-05

## Intent and success criteria

The user approved incremental consolidation of shared booking safeguards across supported listed cash, deliverable FX forwards, listed options, structured securities, futures, bonds and swaps. Product economics and existing tickets remain distinct. The objective is to reduce cross-product drift without building a universal booking engine.

Success means that every booking writer enforces the same applicable authorization, replay and atomicity guarantees; common browser mechanics have one tested implementation; and product-specific behavior and saved history remain compatible. This is foundation hardening, not a new product or production-readiness sign-off.

Execution remains sequential, without subagents. Start with lightweight characterization/regression tests, then isolated PostgreSQL integration and broader acceptance. Operating data/services and GitHub are outside activation scope.

## Current evidence and chosen approach

Baseline `604e247`, branch `codex/enriched-trade-booking`.

- Cash is written by `repository.book_listed_cash_trade`; the HTTP route supplies its savepoint.
- FX and option writers have their own savepoints, advisory replay locks, fingerprint adapters, strategy checks and persistence orchestration.
- `product_booking.book` serves structured securities, futures, bonds and swaps, preserving separate economics.
- Annotation validation and persistence are already shared. Do not duplicate or replace the governed catalogue system.
- Fingerprint normalization differs by path; `_trade_booking_fingerprint` contains historic compatibility rules. Generic swaps also require exact scientific-notation handling in browser convention values.
- Product BFF writes share a helper; other tickets repeat tenant/key checks and reviewed-submission mechanics.

Chosen approach: small explicit shared primitives with product services retaining orchestration. Alternatives rejected: a universal callback/plugin engine adds indirection and risks flattening economics; isolated patches retain duplicated safety behavior. This is not a general rewrite of `repository.py`.

## Backend boundaries

Introduce a small booking-controls module, independent of product writers, for:

1. **Writer authorization:** active actor, effective tenant membership and existing `TRADE_WRITE` role/module rules. Call it at the service boundary for new bookings and replay, not only at HTTP routes. Routes reuse it where appropriate. This does not implement JWT/login or database routing.
2. **Active strategy acquisition:** tenant-scoped active strategy lookup with the required lock, used only for new writes. Hidden/missing strategies remain not-found responses.
3. **Replay primitives:** deterministic advisory-key calculation, acquisition, tenant/endpoint/key lookup, fingerprint comparison and durable result registration. The endpoint namespace and lock hash inputs remain byte-for-byte unchanged.
4. **Atomic boundary:** each writer runs within a savepoint owned by that writer; the caller still owns the outer transaction. Trade, annotations, initial lifecycle evidence and replay row succeed together. No helper commits independently.

Use explicit arguments and typed results, not an unrestricted configuration dictionary or registry of product callbacks. Keep product payload validation, eligibility loading, economics derivation and snapshot construction in their current product modules.

If common exception definitions must move to avoid circular imports, preserve existing imports through re-exports. Do not make the new shared module depend on the large repository module merely to access an exception. Existing annotation persistence can remain where it is unless dependency direction requires a focused extraction.

Authorization failures are deliberate hardening: bypassing an HTTP route must not bypass writer permissions. Keep existing HTTP status/error contracts for ordinary requests. Do not gratuitously rename product errors, response envelopes or identifiers. Membership checks are not claimed to authenticate trusted headers.

## Replay and historical compatibility

Authorization is checked on each call. A revoked actor must not obtain a successful replay through the write endpoint; authorized trade-history access remains a separate read concern.

For an authorized caller:

- Acquire the existing endpoint-scoped idempotency lock and compare the original fingerprint before reapplying current product/strategy/catalogue eligibility.
- An identical retry returns the original trade after terms, strategy or catalogue eligibility change. Current authorization is required, current booking eligibility is not.
- Changed content under the same key conflicts. The same textual key in another endpoint or tenant remains independently scoped.
- Preserve each product's request normalization and the shared historic rules, including omission of additive null/default fields, property canonicalization and collection ordering.
- Do not migrate old fingerprints, rewrite snapshots or add a new fingerprint algorithm/version in this slice.
- Missing trade evidence behind a replay row is an explicit controlled error, never a successful empty response or an instruction to write another trade.

Characterization fixtures must contain baseline expected hashes and saved payload shapes established before extraction. Preserve distinctions the current contracts make; do not silently broaden equivalence, such as changing cash numeric normalization to match option normalization.

## Locking and reference integrity

Inventory booking lock acquisition together with the management paths that touch the same rows: catalogue/eligibility publication, convention/term updates, proposal approval and shared-reference loading. A booking-only ordering list is insufficient.

Retain the existing legacy/generic swap UUID ordering fix. Define compatible ordering for actual shared lock sets and use explicit ordered acquisition where multiple rows of the same resource class are locked. Product validators still recheck authoritative facts under their locks. Tenant visibility must be enforced for new bookings, not inferred from a UUID or prior browser selection.

Do not introduce a blanket global or tenant-wide lock to hide concurrency defects. Existing catalogue publication locks remain scoped as designed. Changes to a paired management path are permitted only where needed to make its lock order compatible, with regression coverage. Do not reduce locks or eligibility checks merely to make tests pass.

Record the concrete acquisition order and resource scope in the shared-controls documentation. Acceptance requires scheduled concurrency tests for known overlapping paths, not an assertion that every possible application deadlock is eliminated.

## Frontend boundaries

Consolidate shared mechanics in small modules while retaining the existing cash, FX, option and product components:

- Exact bounded decimal parsing/formatting and arithmetic primitives using BigInt coefficient/scale; handle supported decimal and scientific API representations without monetary Number conversion. Precision limits remain explicit at the consumer boundary. Product formulas and sign/payment interpretations stay product-specific.
- A reviewed-submission state model that retains the frozen JSON payload, idempotency key and tenant identity after an uncertain result. Retry sends that same envelope, not the current mutable draft. Known validation errors can return to edit; conflicts require checking history/reselection as currently appropriate.
- BFF booking-write guards for required key, expected tenant, selected server context and JSON parsing. Do not change proposal semantics accidentally through the product helper, and never accept browser-supplied actor identity.

Do not merge the forms or replace their product-specific review content. Preserve back-to-edit behavior and navigation/discard protection. Tenant switches invalidate a stale page's ability to submit; a new tenant must not inherit the previous tenant's frozen request. Optional decimal fields preserve zero rather than treating it as absent.

No UI redesign, new settlement defaults, automatic cash trades, dynamic form builder or new product selectors are included.

## Product invariants

| Path | Economics that must remain separate |
|---|---|
| Listed cash | Signed shares and unit execution price; cash route excludes products requiring specialist tickets |
| Deliverable FX forward | Base amount, agreed rate, quote currency, term-derived settlement and two obligations in one trade |
| Listed option | Integer contracts, OPEN/CLOSE intent, premium multiplier/divisor, premium settlement and saved option terms |
| Structured security | Listed/OTC route, approved unit/nominal convention and consideration |
| Future | Family/contract/listing identity, tick and monetary multiplier; reference value is not margin or a payment |
| Bond | Nominal, CLEAN/DIRTY, signed recorded accrual and evidence; dirty quotes do not add accrual twice |
| Swap | Contractual versus booked nominal, whole-swap quote/divisor, zero/negative quotes, no second leverage multiplication or automatic payment; preserve legacy snapshots |

Existing product eligibility limits remain. This refactor does not enable physical/crypto future booking, new option styles, NDFs or arbitrary legacy swaps.

## Verification and delivery documentation

Create a cross-product acceptance matrix covering:

- New valid booking and identical replay; changed-content conflict and tenant/endpoint isolation.
- Actor/membership/module refusal at HTTP and direct service boundaries; foreign/inactive strategy refusal for new writes.
- Hidden/ineligible instruments, stale term fingerprints where supported and saved-history stability.
- Invalid annotations and forced late persistence failures leave no partial trade, children, event or replay row, including when a direct caller catches the error and continues its outer transaction.
- Retry after reference/catalogue/strategy retirement remains successful for an authorized actor without changing the saved trade.
- Concurrent identical requests produce one trade; overlapping management/reference updates exercise documented locking behavior.
- Decimal wire representations, boundary precision, zero, negative values where allowed, unchanged product previews and payloads.
- Browser review/edit, frozen uncertain retry, tenant-switch refusal, successful confirmation and history inspection.

Write lightweight tests first and observe failing tests for new hardening guarantees. Characterization tests establish currently correct compatibility behavior before extraction; they need not be falsely described as failing regressions. Use real isolated PostgreSQL for transaction/locking tests. Finish with complete Python/frontend suites, typecheck, build and reproducible generated-contract checks.

No schema migration or public API change is expected. A discovered requirement for either must be presented as a design change before proceeding. Any schema/API drift generated during the refactor is investigated, not accepted by regenerating blindly.

Deliver one shared-controls reference and one current booking capability matrix linked from the delivery index. Distinguish creation support, listing support and booking support; record remaining restrictions. Update touched legacy documentation to point to the current matrix without rewriting historical acceptance evidence. Record exact commands, results, warnings and deferred issues.

Use isolated synthetic environments for browser/transaction acceptance. Existing permission for mock trades does not authorize operating approvals, migrations, trade creation, restarts or deployment. No GitHub push is part of this task.

## Explicit exclusions and review gate

Valuation/P&L, positions/lots, trade corrections, lifecycle processing, coupon/dividend/payment engines, production authentication, physical tenant routing, instrument amendment workflows, reference-data bulk repair and general UX redesign are separate tasks.

This written specification requires user approval before an implementation plan is prepared. The subsequent plan will preserve sequential execution and lightweight-first verification. Implementation has not started.
