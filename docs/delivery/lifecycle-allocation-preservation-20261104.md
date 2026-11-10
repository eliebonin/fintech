# Allocation-preserving maturity bookings

**Status:** Implemented and locally activated; focused and synthetic browser acceptance passed.
**Scope:** F20, F24 and F51; plain bond redemption and deliverable FX-forward maturity only.
**Reviewed:** 4 November 2026.

## Business behavior

A tenant can designate any existing governed custom field, or combination of fields,
as a position allocation dimension. No field code, label or instrument taxonomy is
hardcoded as a dimension. One maturity event can create several linked closing
entries. Each inherits its allocation values and closes its signed remaining quantity.

For example, Alpha +800,000 and Beta +500,000 produce closures -800,000 and -500,000.
Alpha +1,000,000 and Beta -1,000,000 also require two closures, despite a zero economic
total. An unclassified sale remains unclassified; no FIFO or proportional allocation
is invented. The economic instrument/listing, currency and native conventions remain
separate identities.

## Configuration and Ops journey

In **Tenant profile → Trade configuration → Custom fields → Lifecycle allocation rules**:

- **Preserve position allocation:** partition positions by the combined selected
  field values and inherit those classifications read-only on each closure.
- **Inherit when sources agree:** prefill non-allocation metadata only when the
  contributing sources agree; Ops can supply a replacement value if needed.
- **New booking input:** collect applicable values for the lifecycle entry; this
  does not divide the position. This is the default for unconfigured fields.

The policy is tenant-owned, audited, append-only and revisioned. Configuration retains
TRADE_CONFIGURE authority; it does not grant lifecycle rights. Activating different
dimensions checks historically closed position scopes for inconsistent allocations
and refuses silent historical reclassification.

In **Trades → Lifecycle**, select the strategy and bond/forward, then load inputs.
The allocation breakdown displays before quantity, closing movement, proposed zero,
principal/quote equivalent, inherited labels and applicable fresh property inputs.
After editing, **Validate allocation inputs** refreshes the proposal and its hash.
Missing required values prevent preparation/booking. A confirmed booking remains
confirmed if a subsequent history refresh fails; the UI asks for a read refresh rather
than offering a second booking. A missing required allocation
classification requires source remediation, not an arbitrary value on the unwind.

Governed reference inputs retain tenant/catalogue scope and paged search. Ops lookup
must not borrow configuration-admin permission. Lifecycle action/strategy permissions,
independent selected-user/real-operator approval and Ops-controlled booking timing
remain unchanged. This increment does not redesign assistance modes or implement the
notification dashboard.

## Implementation and evidence

- [Pure contracts](../../security_master_schema/allocation_contracts.py) distinguish
  stable catalogue record identity from its retained version ID.
- [Allocation projection](../../positions/allocations.py) partitions before replay
  and lineage pruning, reusing existing recognition/cancellation semantics. Ordinary
  economic position aggregation is unchanged.
- [Annotation sources](../../trading/annotation_snapshots.py) batch immutable scalar
  and reference reads through tenant-owned trades. [Policy service](../../trading/allocation_policy.py)
  retains field behaviors and checks activation impact.
- [Lifecycle annotation preparation](../../lifecycle/allocations.py) reuses governed
  trading validation/persistence; no weakening of ordinary booking validators.
- [Bond service](../../lifecycle/bond_service.py) and [FX service](../../lifecycle/fx_service.py)
  retain product-specific economics, source checks and permissions. All generated
  trades, annotations, events and posting receipt succeed or roll back together.
- [Movement evidence](../../security_master_schema/maturity_evidence.py) identifies
  the exact entry represented by each generated trade. Source-event identities are
  unique per tenant/request/movement; one request receipt covers the complete event.
  Existing single-movement evidence remains readable, without inventing allocations.
- Fingerprints bind source annotations, selected rules, required field state and
  supplied metadata. Material changes require preparing again. Approval uses retained
  inputs, and cancellation reopens the same allocations.

Migration [110](../../alembic/versions/20261104_110_lifecycle_allocations.py) adds
`trd.lifecycle_allocation_policy`; it does not alter original trade property rows,
BOOKED payloads or published valuations. New closures use the existing trade property
and reference tables. API and generated TypeScript contracts include typed per-movement
property inputs. Ordinary booking retries without new metadata retain their previous
request fingerprint shape.

## Boundaries and trade-offs

- No tax-lot/cost accounting, general reclassification engine, allocation-weight or
  per-bucket P&L report is introduced. Normal strategy positions still aggregate by
  economic identity; persisted closure annotations support correctly grouped consumers.
- Retired/unavailable inherited fields or values are not silently replaced. They can
  require explicit remediation/review before a new closure passes current validation.
  Defining an inheritance-only historical-reference exception is separate work.
- Classification profile changes do not repair old unclassified maturity entries;
  such history requires explicit logged correction/reconciliation.
- Source snapshot cloning remains bounded by existing product conventions; entry-specific
  annotations and movement identities are newly frozen. Broader booking consolidation
  and editing common party/fee fields on lifecycle entries are outside this increment.
- One event may generate many entries; full event evidence is retained in their snapshots.
  Policy activation examines historical closed scopes and may be costly for very large
  tenants. Admission/transaction budgets must protect that work; no financial history is
  truncated to make it convenient.
- Coupon/payment confirmations, cash movements, instrument terms, price selection and
  P&L formulas remain their existing separate workflows. Option, future and structured-note
  lifecycle writers are not enabled by this foundation.

## Verification

A combined 155-test focused Python run passed, covering allocation, bond/FX service/API,
authority, reconstruction, affected economic P&L, workload admission and domain boundaries.
A subsequent 13-test allocation-store run passed, including three additional checks for
retained independent approval inputs, historical activation guard and unchanged retired
policy fields. No full Python suite was run.

All 37 touched frontend unit/BFF checks passed, as did TypeScript/API contract
checks, two repository-neutrality checks, whitespace and delivery/plan link checks. Fifteen
browser regressions passed using installed Edge; bundled Chromium was unavailable. A
stale browser assertion was updated to inspect the existing quiet coverage disclosure
and its exact missing-date instrument link, without changing financial behavior.

Separately, native-browser acceptance in an owned disposable database configured rules,
validated mandatory governed values, posted bond and FX maturity and inspected native
trade details. Four generated entries retained their required properties; all four
instrument/allocation balances were zero. Independent approval, unchanged retries,
cancellation, source changes and second-entry rollback were exercised by service/API
checks, not claimed as native-browser scenarios. No operating trades were booked.

Migration 110 was applied to the local app database on 4 November; the normal API was
restarted and health/OpenAPI returned HTTP 200. No operating tenant allocation fields
were inferred or configured. The owned acceptance app/database were removed; normal
frontend/API remain running. Re-select the workspace if a disposable browser session
caused the local app to request context again.

Focused files: [allocation projection](../../tests/test_lifecycle_allocations.py),
[database/posting/atomicity](../../tests/test_lifecycle_allocation_store.py),
[HTTP contracts](../../tests/test_lifecycle_allocation_contracts.py),
[HTTP authority/picker](../../tests/test_lifecycle_allocation_api.py), plus existing bond,
FX, lifecycle authority, position reconstruction and financial staging tests.

## Allocation editor layout correction — 4 November

The editor now has [scoped styles](../../apps/ops-console/src/components/lifecycle-allocation-policy.module.css)
instead of inheriting compact evidence-disclosure typography and paragraph widths.
A borderless, spaced fieldset separates field selection from the audited save controls.
The three behaviors have a short guide; custom fields use row headers and labelled
selects. On narrow screens, each row stacks without inheriting the generic report-table
780px minimum. Long names and controls stay inside the panel. The reason helper is an
accessible description, not part of the field's label.

The [browser regression](../../apps/ops-console/browser-tests/lifecycle-allocation-layout.spec.ts)
reproduced the original fieldset/layout failure, then passed at 1280px and 390px.
It also verifies that both the required reason and acknowledgement still block invalid
submission, and checks the unchanged typed save payload. Seven browser checks (including
adjacent style regressions), 18 configuration component checks and TypeScript passed.
These checks use real product components with isolated synthetic API responses; no
operating policy or financial data was changed by visual verification.

## Research and intent

[FINOS CDM event model](https://cdm.finos.org/docs/event-model/) motivates retained
before/after states and source lineage. Selecting joint custom allocation dimensions
is this platform's design decision, not a claim that CDM prescribes these particular
fields. See the [approved implementation plan](../superpowers/plans/2026-11-04-allocation-preserving-lifecycle.md).
