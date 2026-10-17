# Backend/API remediation — 16 October 2026

**Status:** Implemented in the reviewed scope; bounded work remains
**Content type:** Delivery and verification record  
**Owner:** Backend/API engineering  
**Last reviewed:** 2026-10-16

Working checkout: `codex/tenant-access-transparency`, with substantial unrelated
uncommitted work preserved. This implements the agreed audit repair workstreams,
not a whole-codebase rewrite or production sign-off. No operating data, permissions,
policy versions or retained financial evidence were modified; no app restart,
migration, commit or push was performed. Tests use owned disposable databases.
The user explicitly approved the shared middleware/audit and UTC-clock rollouts.

## Current outcomes

| Findings | Implemented change | Evidence / remaining boundary |
| --- | --- | --- |
| FIX-SP-001/002 | Strict root/nested draft models, finite contractual values, explicit missing-versus-zero semantics, coupon-period reconciliation/persistence and supplied barrier-summary checks. Variable schedules remain variable. UI excludes irrelevant hidden controls and drops stale generator summaries after explicit review. | [Pure intake tests](../../../tests/test_backend_structured_integrity.py), [persistence tests](../../../tests/test_backend_structured_persistence.py), [payload tests](../../../apps/ops-console/src/app/instruments/autocalls/new/payload.test.ts). Not a general termsheet/payoff evaluator. |
| FIX-SP-003; BACKEND-003 | New contracts pin a visible sealed eligible calendar. Server payment preview counts assessed OPEN dates; unknown coverage blocks generation. Submission/approval recheck generated dates. Published options replace hardcoded UI IDs. Explicit sourced dates remain separate from generated dates. | [Dependencies](../../../apps/reference_api/structured_product_dependencies.py), [holiday tests](../../../tests/test_structured_payment_calendar.py). Existing imported EXPLICIT API requests remain compatible without a newly mandatory reason; edited UI schedules require a retained reason. The legacy client weekday generator is provisional, not authoritative. |
| BACKEND-002 | Nested source/payload ownership and pairing; observations reconcile subject/date/value/RAW basis/units/quality, supersession and current dataset display rights. Snapshot references require tenant/strategy visibility and a matching observed item. Rechecked at submission, replay and approval before materialization. | [Source scope](../../../tests/test_source_payload_scope.py), [nested dependency tests](../../../tests/test_backend_structured_persistence.py). MANUAL/PROVIDER values are retained operator assertions, not independently verified quotes. Unsupported DERIVED fixings fail closed. Missing-reference and raw-observation cases have stronger executable coverage than all snapshot permutations. |
| BACKEND-004 | Legacy NAV queue rows and counts use the same strategy predicate before pagination. | [Scoped queue tests](../../../tests/test_backend_queue_scopes.py): selected, empty, ALL and reference-only actors. Historical NAV records are retained. |
| BACKEND-005 | Async middleware reads the bounded body before opening a connection, offloads the complete synchronous authorization unit, and applies transaction-local statement/lock budgets. | [Execution tests](../../../tests/test_access_boundary_execution.py), [budget tests](../../../tests/test_api_execution_budget.py). Sync services remain sync; threadpool/pool capacity is not unlimited. |
| BACKEND-006 | Generic tenant command audit commits with ordinary writes. A failed audit rolls back the command. Real operator, selected subject, permission, resource IDs and request ID are retained. Multi-transaction valuation/reassessment retains REQUEST_ACCEPTED with its durable attempt/request; existing events describe later financial outcome. | [Fault-injection HTTP tests](../../../tests/test_request_audit_atomicity.py), [lower audit context](../../../security_master_schema/command_audit.py), [HTTP result adapter](../../../apps/reference_api/request_audit.py). No response-body draining or second post-commit generic audit write. Network uncertainty still requires unchanged idempotent recovery. |
| BACKEND-007 | Shared UTC governance date replaces host-local authority/licensing dates across the reviewed backend modules. Request scope pins one date and propagates into sync workers; explicit financial dates and exchange zones remain unchanged. | [Clock](../../../security_master_schema/governance_clock.py), [timezone/thread tests](../../../tests/test_governance_clock.py), [host-date mismatch integration](../../../tests/test_governance_authority_dates.py). Outside requests, the same helper uses current UTC. |
| BACKEND-008 | Typed server search/count/page/selected-ID endpoint for strategies, policies and currencies; scope precedes count/pagination/selected lookup. Native UI selections support server search/load-more and retain off-page choices. Calculation filters remain distinct from readable Results. | [501-strategy HTTP tests](../../../tests/test_valuation_option_pages.py), [paged control](../../../apps/ops-console/src/features/valuation/paged-choice.tsx), [browser journey](../../../apps/ops-console/browser-tests/critical.spec.ts). Legacy `/options` now has no silent cap but still returns a full bootstrap register for older consumers; this is an acknowledged large-register cost. |
| BACKEND-010 | Measures use REPEATABLE READ from the first query. After releasing that connection, a fresh budgeted transaction checks current strategy/action/display rights before response release. | [Two-connection mutation/revocation and pool-size-one tests](../../../tests/test_measure_snapshot_boundary.py). No two simultaneous pool connections are needed. |
| MEASURES-005 | Bounded SAME_DAY observation selection and request/transaction-local reuse reduce repeated rights/calendar/priority/display reads. Cache copies cannot be mutated by callers; reuse requires REPEATABLE READ and is cleared at scope exit. Current release checks never reuse the financial snapshot cache. | [Measured SQL regression](../../../tests/test_resolution_read_performance.py), [reuse lifecycle tests](../../../tests/test_resolution_read_scope.py). No cross-request cache, weaker rights, trade-history cap or speculative index was introduced. Full-history checkpoints and representative multi-user load remain open. |
| BACKEND-009 | Shared errors, reference authority/visibility, booking controls, forward-reference loading and approved Future/Swap term models moved below HTTP, retaining API compatibility imports. All five reviewed financial services now import their lower foundations directly. | [Mandatory architecture guard](../../../tests/test_financial_domain_boundaries.py), [schema/frozen JSON parity](../../../tests/test_shared_financial_contract_parity.py) and [follow-up](#shared-term-model-follow-up). The earlier expected failure is removed. Broader repository decomposition and universal typed-response conversion are not claimed. |

## Performance evidence

The fixed disposable workload adds 1,000 historical observations and five unrelated
provider profiles. It compares the same preview with/without scoped reuse and
asserts identical values/evidence hashes. After date-bounding, uncached/scoped
SQL counts were **156 / 99**, with **two candidate rows transferred** rather than
the earlier probe's 3,040. Observed scoped elapsed time was about **0.29–0.42 s**
versus **0.59–0.75 s** uncached on this synthetic workload. Actual emitted-query
`EXPLAIN (ANALYZE, BUFFERS)` returned one row, 21 shared buffer hits and roughly
0.27–0.46 ms execution. These are observations, not service-level guarantees.

The earlier operating eleven-position result of 42.63 s / 1,796 statements is not
re-benchmarked here. Prior/lagged selection still has a bounded wider diagnostic
window; forward proof/history and access-matrix scaling need separate profiling.
Do not extrapolate the synthetic speedup into a guaranteed operating latency.

## Verification and limits

- Combined remediation regression: **131 passed**, two dependency deprecation warnings,
  using `scripts/run_isolated_python_tests.py` with explicit affected test modules.
- Broader affected access/rights/resolver/booking/coupon/architecture cohort:
  **161 passed, one strict expected failure**, 26 existing dependency warnings.
  These cohorts overlap; their counts must not be presented as distinct unique tests.
- Subsequent pure integrity/reuse/architecture check: **45 passed, one strict expected
  failure** for the explicitly approval-gated term-model move.
- Final contract/condition-group/reuse/architecture regression after the serialization
  fix: **53 passed, one strict expected failure** for that same model move.
- Initial full frontend run: **920 passed, one outdated parent-component assertion
  failed** after replacing its selector. The corrected assertion's seven-test file
  passes. Later final reruns are recorded below, not inferred from this initial run.
- Initial browser run: **10 passed, one failed** because the synthetic journey clicked
  before async option validation completed. Waiting for native validity made that
  journey pass; no fixed sleep or disabled validation was added.
- Final frontend rerun: **921 passed across 196 files**. Final complete isolated
  browser rerun: **11 passed**, including off-page selection/server search and the
  calculation-to-staged-to-explicit-publication journey. No operating publication.
- TypeScript, OpenAPI export/check and byte-identical repeated TypeScript generation
  passed. `contract:generate:check` compares against committed Git content and reports
  the checkout's outstanding generated changes; it is not claimed clean before commit.
- No complete Python suite, operating strategy revaluation, independent financial
  reconciliation, real termsheet acceptance or production identity verification.

Final review was a sequential self-review, following the user's no-subagent direction.
It checked the effect/audit teardown, cache keys/lifetime, current-rights release,
calendar eligibility parity, selection semantics and compatibility imports. This
is weaker than an independent review. It caught calendar-preview eligibility drift
(a new pure regression first failed, then passed), plus normalized explicit-graph
round-trip rejection. Explicit rows remain authoritative after serialization;
generated schedules still enforce inheritance. The legacy default flag itself was
preserved rather than changed incidentally. No merge sign-off
for the whole dirty checkout is implied.

## Decisions and remaining work

- Native/sequential work in the existing checkout follows the user's direction;
  no subagents, new worktree, automatic commits or operating activation.
- Compatibility API imports and explicit sourced schedules are retained. Unknown
  contractual numbers are not zero; variable periods are not flattened for convenience.
- Ordinary writes and multi-transaction calculations have different audit phases;
  REQUEST_ACCEPTED must not be displayed as a completed or published valuation.
- The approved shared term-model extraction is implemented; see the follow-up below.
  Other decomposition remains incremental, rather than a wholesale rewrite of large
  files. Remaining compatibility imports in `valuation/accruals.py`,
  `valuation/amendments.py` and `lifecycle/bond_service.py` are not claimed removed.
- Retain BACKEND-001 as a non-local deployment gate. Also retain existing independent
  reconciliation, source-impact fan-out, broad lifecycle/valuation and history scaling
  gaps. None is solved merely by passing these repair tests.

## Shared term-model follow-up

The user approved the previously gated move after a separate explanation of its
scope. This is ownership cleanup, not changed economics or a database migration:

- [Booking conventions](../../../security_master_schema/booking_conventions.py)
  own the existing `ConventionBase` and `FutureConvention` definitions.
- [Swap terms](../../../security_master_schema/swap_terms.py) own the existing
  `GenericSwapTerms`, frequency type and basis-point conversion helper.
- Existing API import paths export the **same class objects**, not copied/wrapped
  models. HTTP proposal envelopes and product-specific routes remain API-owned.
  Other API convention types still inherit the same shared base class.
- Valuation imports the lower models directly. The former architecture xfail is
  removed; all five reviewed service guards and two shared-module guards must pass.
- Pre-move validation/serialization schema fingerprints, representative exact frozen
  JSON bytes (future, nominal swap, leveraged unit swap), Decimal behavior, legacy
  omitted fields and round trips pass. The complete OpenAPI fingerprint is unchanged:
  `f968cfe14baef5eaaf2f526ac5ad90585a7193dffed0cdfe1a339c87e45d093c`.
- Initial test-first run reproduced four ownership/import failures; after the move,
  the focused boundary/parity/swap/future/booking-rule cohort passed **75 tests**.
  Adding guards on the two new lower modules gave **77 passed** in the final pure run.
- The affected integration cohort passed **166 tests, no skips/xfails**, with nine
  Pydantic/SQLAlchemy warnings. It covers product/future API conventions, generic swap
  creation/booking/replay, unit swaps, persistence round trips, futures/other supported
  monetary inputs and parity/import checks. It took 610.28 s; this was a scoped
  integration run, not the complete Python suite. The cohorts overlap.
  The normal runner used its owned disposable database; the legacy storage migration
  fixture additionally recreated its dedicated `platform_secm_migration_test` database.
  Neither is the operating database. No new schema migration was authored or applied
  to operating data.
- Sequential self-review confirmed the definitions were moved without logic edits,
  API exports are identical class objects, all seven import guards pass, and no
  financial formula or permission check was removed. No independent reviewer or
  frontend/browser rerun was used for this backend-only, wire-compatible extraction.
- Documentation verification: all **868 local link targets** checked across nine
  touched documents resolve; scoped whitespace checks pass.

Earlier expected-failure counts in this report remain historical results, not the
current status. No frontend change, generated contract update, operating financial data edit,
operating restart or new permission was needed. Broader BACKEND-009 decomposition
remains open; this extraction is not a claim that every backend domain is decoupled.

## Best-practice basis

Checked 2026-10-16 against the installed versions recorded in the
[implementation plan](../../superpowers/plans/2026-10-16-backend-api-remediation.md):
[Pydantic strict extras](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra)
and [validators](https://docs.pydantic.dev/latest/concepts/validators/),
[OWASP per-object authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/),
[Starlette threadpool](https://starlette.dev/threadpool/),
[PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html),
[SQLAlchemy connections](https://docs.sqlalchemy.org/en/21/core/connections.html),
[PostgreSQL EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) and
[transactional audit/outbox principle](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).
The chosen contractual conventions and compatibility boundaries are project decisions,
not universal financial-market rules imposed by those technical sources.
