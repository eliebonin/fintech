# Autocall Persistence Bridge Implementation Plan

> **For agentic workers:** This plan is executed inline in the current task. It deliberately covers one persistence slice, not a pricing engine.

**Goal:** Turn the structured-product/autocall UI draft into a validated, versioned reference-data proposal that can be materialised into the canonical PostgreSQL graph.

**Architecture:** The browser sends a versioned `AutocallDraftRequest` containing parent identity, resolved underlyings, schedule intent, component rows, and parent actions. The API validates cardinality, dates, ranges, and catalogues before storing the append-only proposal. Approval materialises a parent instrument, fresh child component nodes, dated schedules/events, structured-product terms, compositions, condition groups/rules/actions, and initial-fixing provenance in one transaction.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, SQLAlchemy Core, PostgreSQL/Alembic, Next.js/React/MUI, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-08-structured-product-condition-groups-design.md` and `ui/screen-specs/structured-product-autocall-builder.md`.

## Global Constraints

- The security master remains canonical reference/contract data, not a pricing engine.
- UUIDv7 remains the database identity; UI row IDs are draft keys only.
- Approved records are versioned/append-only; edits create a new proposal/version.
- Parent actions are not duplicated per underlying.
- Calendar/session resolution belongs to the `cal` schema; the API must not treat weekend-only preview dates as authoritative.
- Do not run the full test suite unless explicitly requested; use focused Python and frontend tests.

---

### Task 1: Add failing contract and schema tests

**Files:**
- Create: `tests/test_structured_product_draft.py`
- Modify: `tests/test_structured_product_condition_groups.py`

**Interfaces:**
- Tests define the expected `AutocallDraftRequest`, validation errors, governed consolation action/basis values, and initial-fixing table metadata.

- [x] **Step 1: Write failing tests** for a valid discrete two-underlying draft, invalid range, invalid consolation payout basis, missing fixing provenance, and schema enum/table requirements.
- [x] **Step 2: Run the focused tests** and confirm they fail because the draft contract/schema additions do not exist.

### Task 2: Implement the draft contract and validator

**Files:**
- Create: `apps/reference_api/structured_product_contracts.py`
- Modify: `apps/reference_api/contracts.py`
- Test: `tests/test_structured_product_draft.py`

**Interfaces:**
- `AutocallDraftRequest` exposes camel-case API fields for parent identity, underlyings, schedule, components, actions, `observationStyle`, `memoryMode`, `calendarId`, `initialFixing`, and `sourceSystemId`.
- `validate_autocall_draft(request)` returns a normalized request or raises `StructuredProductDraftError` with stable messages.

- [x] **Step 1:** Add Pydantic models with explicit `Decimal`, UUID, date, enum, and range constraints.
- [x] **Step 2:** Validate unique underlying IDs, positive fixings, date ordering, `WORST_OF`/`BEST_OF` cardinality, `BETWEEN` bounds, parent-action targets, and the consolation lower-bound dependency (KIP barrier when present, explicit `consolationLowerBarrier` otherwise).
- [x] **Step 3:** Validate calendar ID and source/provenance fields are present for persisted initial fixings.
- [x] **Step 4:** Run the focused tests and keep them green.

### Task 3: Extend the canonical schema for consolation and fixing provenance

**Files:**
- Modify: `security_master_schema/models.py`
- Create: `alembic/versions/20260909_32_structured_product_persistence_bridge.py`
- Modify: `tests/test_structured_product_condition_groups.py`

**Interfaces:**
- `condition_group_action.action_type` accepts `PAY_CONSOLATION`.
- `condition_group_action.payment_basis` accepts `PCT_OF_MAX_PAYOFF`.
- `secm.structured_product_initial_fixing` stores product/underlying fixing value, date, source observation, resolution snapshot, and status.
- `secm.barrier_rule` stores explicit lower/upper bound inclusivity; the
  consolation draft requires an explicit final payoff barrier and uses an
  inclusive lower / exclusive upper range.

- [x] **Step 1:** Add metadata columns/table with comments, keys, checks, and indexes.
- [x] **Step 2:** Add a forward migration with reversible constraint/table operations.
- [x] **Step 3:** Add schema contract assertions and run them.
- [x] **Step 4:** Add and verify the follow-up bound-semantics migration
  (`20260909_33_barrier_bound_semantics.py`).

### Task 4: Add proposal submission and approval materialisation

**Files:**
- Modify: `apps/reference_api/main.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/structured_product_contracts.py`
- Create: `tests/test_structured_product_api.py`

**Interfaces:**
- `POST /v1/structured-product-proposals` stores a `CREATE_STRUCTURED_PRODUCT` proposal with `structured-product.v1` payload.
- `POST /v1/structured-product-proposals/{proposal_id}/decision` validates and materialises approved proposals.
- `submit_structured_product_proposal(...)` and `decide_structured_product_proposal(...)` are tenant-scoped and idempotent.

- [x] **Step 1:** Add API boundary tests; full integration approval/idempotency coverage remains a follow-up.
- [x] **Step 2:** Implement proposal envelope and tenant/catalogue checks.
- [x] **Step 3:** Implement one-transaction materialisation with fresh UUIDv7 parent/child nodes, terms version, dates, schedules/events, compositions, groups/rules/actions, and initial fixings.
- [x] **Step 4:** Add approval evidence listing generated IDs and source lineage.
- [x] **Step 5:** Run focused API/schema tests.

### Task 5: Connect the autocall UI to the proposal contract

**Files:**
- Modify: `apps/ops-console/src/app/instruments/autocalls/new/form.tsx`
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Modify: `apps/ops-console/src/lib/browser-api-client.ts`
- Create: `apps/ops-console/src/app/api/instruments/structured-products/route.ts`
- Create: `apps/ops-console/src/app/instruments/autocalls/new/payload.ts`
- Test: `apps/ops-console/src/app/instruments/autocalls/new/*.test.ts`

**Interfaces:**
- `buildAutocallDraftPayload(formState)` maps generated/draft rows to the API contract, preserving UI row IDs only as draft provenance.
- The save button submits the proposal and shows its pending/approved identifier; it does not imply direct DB writes.

- [x] **Step 1:** Add a failing payload-mapping test, including consolation and initial-fixing provenance.
- [x] **Step 2:** Implement mapper and browser API call with idempotency key.
- [x] **Step 3:** Replace the “coming next” action with “Submit draft proposal”, retaining a clear pending/approval status.
- [x] **Step 4:** Run focused frontend tests and typecheck.

### Task 6: Document the materialisation boundary and deferrals

**Files:**
- Modify: `docs/superpowers/specs/2026-09-08-structured-product-condition-groups-design.md`
- Modify: `ui/screen-specs/structured-product-autocall-builder.md`

- [x] **Step 1:** Document payload-to-table mapping, parent-action expansion, fresh child identities, and initial-fixing provenance.
- [x] **Step 2:** Document deferred payoff-base policy, explicit final payoff barrier, full calendar resolution, row add/delete/reorder, and pricing.
- [x] **Step 3:** Review the plan checklist against the implementation and report any remaining gaps.

### Verification record (2026-09-09)

- Alembic is applied through `20260909_33` in the local PostgreSQL container.
- A controlled `AUTOCALL_CONSOLATION` draft was submitted through the live API,
  appeared in `/v1/work-queue`, and was approved through the generic
  `/v1/reference-data-proposals/{id}/decision` route.
- The materialised graph was queried directly: one tenant-private parent,
  two fresh child option instruments, two initial-fixing rows, three actions,
  and parent `BETWEEN 65` (inclusive) / `90` (exclusive) barrier rules.
- Focused Python contract/API/schema tests pass (`12 passed`); focused frontend
  payload/schedule tests pass (`11 passed`) and TypeScript typecheck passes.
- `alembic check` still reports pre-existing metadata drift in unrelated fee,
  market-data, NAV, option, and tenant tables. It does not report the new
  barrier-bound columns as drift; resolving that wider baseline is deferred.
