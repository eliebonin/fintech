# API service extraction — phases 1–3

**Date:** 29 October 2026. **Scope:** completed incremental source extraction;
broader API decomposition remains partial (BACKEND-009).

## Result

1. Fixed pre-move hash/schema vectors and dependency guards protect the extraction.
   Existing frozen product/attribution tests and transaction fault injection remain.
2. Canonical evidence, SHA-256 identity and finite-Decimal validation now belong to
   `security_master_schema.evidence`. Positions, market-data and lifecycle import
   that owner; `valuation.economics` retains identical public exports and its
   economic formulas. Accrual visibility and amendment/bond-maturity locks import
   their existing lower owners directly.
3. `market_data.pricing_policy_contracts` owns the original command models and
   validators. `pricing_policies` owns creation, reference/calendar checks,
   fingerprints, advisory locking, versioning/activation and a business definition
   projection. API wrappers map that result to unchanged response DTOs and errors.
   The Yahoo FX setup operator uses the shared command/models, preserving its
   existing personal-data, platform, calendar and licensing checks.

The catalogue's optimized subject/parent visibility predicate moved unchanged to
`security_master_schema.market_data_visibility.catalogue_subject_clause`; its API
import remains an identity alias. The existing resolver predicate is unchanged.
This avoids importing the large API repository into the new service.

No endpoint, OpenAPI schema, database schema, economic formula, source entitlement
or operating record changed. Shared commands use the supplied Core Connection;
they do not commit, acquire an engine or replace the request's audited transaction.
Creation rechecks current module/action rights before replay. Direct strategy-bound
creation additionally applies the same STRATEGY_WRITE scope already enforced by
HTTP, before idempotency lookup. This is deliberate entry-point parity, not a new
administrative bypass. `policy_definition` is an internal tenant-filtered query;
its caller must establish module authority, and bound request strategy checks remain.

## Verification

- Before moving code: **79 focused offline tests passed**, including new fixed
  vectors, frozen future/option/swap conventions and outer-commit failure checks;
  **12 disposable PostgreSQL policy/audit/operator tests passed**. OpenAPI check passed.
- Structural RED run: **14 failures / 21 passes**, identifying the targeted reverse
  imports and missing lower owners. No unrelated assertions were weakened.
- After extraction: **97 focused offline tests passed**, covering fixed hashes,
  unchanged command schemas, original economic tests, frozen conventions and
  dependency guards. Follow-up **22 passed** for export identity/runtime isolation
  and OpenAPI remained unchanged. After lifecycle import cleanup, **77 focused
  offline tests passed**, including the structural guards and maturity kernels.
- Disposable integration pass: **82 passed**, with two failures in new test fixtures
  (internal-vs-wire alias comparison; a policy date before the seeded strategy's
  effective date). Corrected only those fixtures. Follow-up **24 passed**, covering
  all 11 shared-command tests plus affected bond/FX maturity and coupon services.
  Together these runs validate all 84 original integration cases and 13 additional
  lifecycle cases; counts are not summed as if repeated tests were distinct.
- Assertions cover exact HTTP/direct-command replay, current permission/scope
  revocation, conflicts, concurrent same-key deduplication and code-version
  serialization, private subject/listing-parent visibility, flexible defaults,
  source validation, rollback of caller-owned writes and request-audit failure
  after the route's savepoint has been released. The FX operator test uses synthetic
  retained observations and rights; no provider fetch or operating activation.
- Exact AST comparison against a pre-change source snapshot confirms the three
  evidence functions, both command models, optimized visibility predicate and
  authority implementation are unchanged. Creation flow differs only by the
  documented strategy guard, type/doc annotations and result-projection call.
  All **1,395 local links** in the scoped Markdown set resolve; embedded and
  standalone code diagrams match, and refreshed SVG/PNG rendering had no browser
  errors. Repository neutrality and whitespace checks pass.

Existing Starlette test-client/deprecated-422 warnings remain unrelated. The full
Python suite and browser suite were not run: no UI behaviour changed. Tests used
owned disposable databases, including their normal migrated synthetic fixtures;
the operating database was not migrated or changed. No restart, commit or push.

## Remaining boundaries and tradeoffs

This is one pilot, not a fully thin API: reference/proposal/booking orchestration,
policy catalogue/options/preview adapters and broader command/query extraction
remain. The shared schema/resolver package and late intake metadata registration
still need a separate foundation change. Production identity and scale acceptance
are independent of this refactor. No new repository/UoW framework, microservice,
duplicate validation schema or permanent feature switch was introduced.

Compatibility exports keep existing public imports working as the same objects.
New domain callers must import their actual owner; remove an export only after
the remaining documented callers have migrated. Retained request-fingerprint
compatibility is financial retry behaviour, not a second active implementation.
The [atlas](../architecture/atlas/README.md) updates current owner arrows while
preserving the pre-extraction machine inventory as dated evidence.

See the [accepted scope and primary sources](specifications/api-service-extraction.md),
[sequential plan](../superpowers/plans/2026-10-29-api-service-extraction.md),
[current knowledge](../../KNOWLEDGE.md#shared-services-below-the-api--29-october-2026)
and [remaining finding](../../FIX.md#backend-009--p3--domaintransport-boundaries-and-legacy-interfaces-have-drifted).
