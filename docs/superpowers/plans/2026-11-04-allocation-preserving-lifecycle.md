# Allocation-preserving lifecycle bookings implementation plan

> For agentic workers: use superpowers:executing-plans sequentially. Do not delegate. Execution complete within the scope below; see the dated delivery evidence.

**Goal:** Bond and deliverable FX-forward maturity bookings close every remaining tenant allocation as well as the economic position, with validated annotations and retained provenance.

**Architecture:** Add a shared allocation policy and allocation-aware projection below HTTP. Product handlers retain their own economics and authority, and persist ordinary governed annotation rows alongside accurate frozen booking evidence. Do not change the default economic position key globally.

**Tech stack:** Python, SQLAlchemy/PostgreSQL, Alembic, existing FastAPI/BFF and Next.js console.

**Spec:** The design decisions below implement the 4 November lifecycle discussion and the allocation example in this chat. Existing capability boundaries: [F20](../../product/features/trade-operations.md#f20-governed-trade-properties), [F24](../../product/features/trade-operations.md#f24-contractual-lifecycle), [F51](../../product/features/trade-operations.md#f51-tenant-lifecycle-handling-modes).

## Design decisions and constraints

- In trade configuration, explicitly designate fields as position allocation dimensions. Do not infer these from labels, or group by every field/comment. A separate inheritance behavior can preserve a non-allocation value only when all contributing sources agree; otherwise collect a fresh applicable booking input.
- Store audited, versioned policy selections referencing immutable tenant definition IDs. A property definition's business meaning is not changed by a lifecycle policy setting. Catalogue identity and catalogue revision/label evidence are distinct; an unchanged entity's display revision must not create a different allocation.
- Group by the joint allocation signature plus the existing economic identity: tenant, strategy, instrument/listing, currency and native conventions. Distinct contracts and listings stay distinct.
- Derive signed balances from the complete eligible ledger before economic netting. Reuse recognition, correction and cancellation semantics; do not use only the aggregate bucket's surviving source-trade list.
- A full maturity event closes every nonzero allocation. Positive and negative allocations must both close even when their economic total is zero. Do not allocate an unclassified historical sale across classified purchases using invented FIFO/proportions.
- Missing optional classifications remain explicitly unclassified. Missing required allocation values require source remediation; a new required non-allocation booking input can be supplied for the closure. Ambiguous histories require Ops review, not a guessed allocation.
- Frozen inherited classifications are not freely editable on the closing entry. Reclassification is an explicit separately audited operation; a general reclassification feature is outside this increment.
- Original trader/execution identifiers and execution-only numbers are not blindly copied into the new booking. Fresh applicable metadata belongs to the lifecycle entry; original context remains linked source evidence. Existing required-field rules are not bypassed: use sourced values or Ops input, with any future applicability changes separately governed.
- Retired catalogue values are never silently remapped. Stop for review until a documented, tested inheritance-only historical-reference rule permits the exact original identity; ordinary new booking rules stay strict.
- No financial/audit history is rewritten. Configuration activation must preview effects on existing trades/closures; do not silently enable a different allocation interpretation across already closed history.
- Exposure closure remains separate from cash, coupons and settlement. No tax, FIFO, cost accounting, dashboard, new subscription products or assistance-mode redesign in this increment.
- Original BOOKED bytes and published valuation amounts remain immutable. Existing cancellation/reassessment controls remain in force.

## Pre-implementation evidence (retained context)

- `positions/contracts.py:PositionKey` contains economic identity/conventions, not tenant property dimensions.
- `positions/reconstruction.py:reconstruct` groups and prunes financial lineage at economic position level; allocation analysis must occur before that pruning.
- `lifecycle/bond_service.py:candidate/post` creates entries per economic bucket and derives a new snapshot from one source. It does not explicitly persist the new entries' custom-field assignments.
- `lifecycle/fx_service.py:candidate/post` currently prepares one aggregate movement and writes one closure, without explicit annotation persistence.
- `trading/annotations.py:validate_trade_annotations` and `trading/booking_store.py:persist_trade_annotations` provide governed validation and persistence to reuse without relaxing their normal booking rules.

## Review focus

1. Net-zero total with opposing nonzero allocations must remain discoverable and close correctly.
2. Missing or changed classification/catalogue evidence must invalidate the proposal rather than choose the first trade's value.
3. Existing unclassified sales must not be retrospectively assigned to a classified position by guesswork.
4. Concurrent booking, policy edits and cancellation must preserve atomic posting, authorization and idempotency.
5. A correct total is insufficient: persisted property rows, grouped reports and frozen proof must agree for each allocation.

## Task 1: Govern allocation and inheritance policy

**Files:** new `trading/allocation_policy.py`; schema table definitions exported through `security_master_schema/models.py`; next additive Alembic revision; existing `apps/reference_api/trade_configuration.py` and trade-configuration DTO/BFF/UI. Reserve the migration identifier against the current head at execution time.

**Interfaces:** `load_allocation_policy(connection, tenant_id)` returns a retained revision with definition IDs and behavior; `save_allocation_policy(...)` requires the existing configuration authority, expected revision, reason and impact acknowledgement.

- [x] Write focused tests for joint dimensions, cross-tenant rejection, revision conflicts, catalogue label changes versus actual identity changes, and policy activation over already closed history.
- [x] Verify the tests fail for absent behavior, then implement policy loading/configuration and its small trade-configuration control.
- [x] Keep existing economic reports unchanged. Preview legacy ambiguities and require remediation before enabling an inconsistent scope; no automatic data reclassification.
- [x] Run focused configuration/schema tests in an owned disposable database and the touched UI tests/type checks.

## Task 2: Project remaining allocations

**Files:** new `positions/allocations.py`, new `trading/annotation_snapshots.py`; reuse `positions/repository.py`, `positions/reconstruction.py`, and existing native FX maturity ledger validation.

**Interfaces:** batch annotation loading returns typed tenant-scoped source annotations and provenance; allocation projection returns economic identity, joint allocation signature, signed quantity, source identities and a deterministic evidence hash. Product-specific ledger adapters must retain existing per-trade economics checks.

- [x] Write pure tests: Protection +1,000,000, Protection -200,000, Income +500,000 produces +800,000 and +500,000. Opposing +1,000,000/-1,000,000 allocations both survive total-zero aggregation.
- [x] Add cancellation/replacement, missing/unclassified sales, joint dimensions, distinct listings/currencies, earlier flat episodes and identical catalogue identity with revised labels.
- [x] Implement partitioning before netting, using the existing ledger rules. Batch annotation reads; no history cap, per-trade query loop, FIFO or implicit proportional allocation.
- [x] Verify pure tests and relevant reconstruction/FX evidence tests; ordinary economic reconstruction remains unchanged.

## Task 3: Preserve allocations in bond redemption

**Files:** `lifecycle/bond_service.py`, `lifecycle/bond_redemption.py`; existing bond contracts/routes; new focused allocation tests and existing `tests/test_bond_redemption_service.py` / `tests/test_bond_redemption_valuation.py`.

**Interfaces:** candidate movements include allocation signature, typed inherited values, unresolved applicable fields, source evidence and allocation-policy revision. Posting consumes only a current validated proposal plus permitted fresh metadata.

- [x] Reproduce the current dropped-annotation behavior with a disposable database test.
- [x] Prepare one closing entry per remaining allocation using contractual redemption terms. Persist validated annotation rows using shared trading helpers and construct accurate new BOOKED evidence instead of inheriting stale execution identity wholesale.
- [x] Include source annotations/configuration/mandatory field inputs in proposal and request fingerprints. Revalidate under existing locks; any changed material source requires preparation again.
- [x] Post all movements, annotations, audit and receipt atomically. Assert zero per allocation and per economic identity before commit. Failure in any movement rolls back the whole maturity posting.
- [x] Verify duplicate requests create no additional entries; cancellation reopens the same allocations; permissions and independent selected-user/real-operator checks remain unchanged.
- [x] Verify final-day P&L totals remain correct, including offsetting allocations that were economically flat before maturity.

## Task 4: Apply the shared foundation to FX-forward maturity

**Files:** `lifecycle/fx_service.py`, existing FX maturity contracts/routes and affected valuation/position consumers; `tests/test_fx_maturity_service.py`, `tests/test_fx_maturity_api.py`, new allocation evidence tests.

- [x] Add failing tests for multi-allocation and zero-total/opposing-allocation forwards, partial closures, mixed agreements, cancellation and retained multi-movement evidence.
- [x] Replace the single aggregate movement assumption with allocation movements while retaining each agreement's quote orientation, rate policy/override provenance and native source validation.
- [x] Update consumers of stored FX maturity movements to inspect every movement, never assume `[0]` contains the full closure. Preserve existing proof decoding or explicitly require reassessment where old evidence cannot prove allocation coverage; do not invent historical annotations.
- [x] Reuse governed annotation persistence, atomic posting, complete after-state checks and unchanged authorization/idempotency.
- [x] Run focused FX service/API, position, lifecycle-evidence and affected P&L regressions.

## Task 5: Ops preview, acceptance and documentation

**Files:** `apps/ops-console/src/components/bond-redemption-console.tsx` and its tests; touched lifecycle API/BFF contracts; F20/F24/F51 capability record, register and implementation map; a dated delivery note.

- [x] Show an allocation breakdown with before quantity, closing quantity, after quantity and inherited fields, plus fresh mandatory inputs. Keep one event and an explicit count of generated entries.
- [x] Mark inherited dimensions read-only; surface missing/ambiguous data as Needs information. Booking is available only when all entries satisfy their requirements; server enforcement remains authoritative.
- [x] Run focused UI/BFF tests and type/contract checks. Exercise synthetic bond and FX journeys in an isolated app/database: configure, preview, supply required metadata, book and inspect native property rows/grouped zeros. Cover independent preparation/approval, retry, cancellation and changed-source rejection with native service/API tests; these are not claimed as browser scenarios.
- [x] Update maintained documentation with actual delivery boundaries, migration/activation state, evidence and unresolved legacy ambiguities. Do not claim support for option/future/note lifecycle handlers not implemented here.

## Execution result

Implemented sequentially. Migration 110 applied and local API restarted. Focused Python,
frontend, contracts and 15 browser regressions passed; native browser bond/FX acceptance
closed four classified allocations. See [delivery and limitations](../../delivery/lifecycle-allocation-preservation-20261104.md)
for actual verification, test-layer distinctions and remaining retired/history boundaries.
No operating trades, historical classifications or published valuations were changed.

## Verification and activation

Start with lightweight pure tests. Broaden only to the touched configuration, lifecycle, reconstruction and valuation paths after implementation; do not run the entire Python suite by default. Use `scripts/run_isolated_python_tests.py tests/<focused-file>.py -q` for DB checks. Do not seed, correct, reclassify, cancel or post operating financial data to demonstrate the feature. Local migration/API activation is a separately reported step after checks; do not claim it from static tests.

## Research rationale

[FINOS CDM event model](https://cdm.finos.org/docs/event-model/) supports traceable lifecycle state transitions and distinguishes workflow from economic state. It does not prescribe our custom-property policy; preserving joint allocation dimensions is the project's application of those principles. [Current property capability](../../product/features/trade-operations.md#f20-governed-trade-properties) remains the authority for governed tenant definitions and historical values.
