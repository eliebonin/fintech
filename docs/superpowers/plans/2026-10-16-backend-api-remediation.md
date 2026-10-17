# Backend/API audit remediation implementation plan

**Goal:** Resolve the five agreed repair workstreams against current code, preserving financial evidence and local alpha workflows.
**Execution:** Native/sequential in the existing feature checkout, as explicitly requested previously. No extra approval gates, commits/pushes or operating-data writes. Focused tests first; disposable PostgreSQL only.
**Specification:** The user's five-point backend discussion and stable findings BACKEND-002–010, FIX-SP-001–003 and MEASURES-005 in root FIX.md. BACKEND-001 remains a deployment-identity gate, not an instruction to implement a new identity provider. Integrated AI ingestion, accounting and new valuation instrument coverage are not added.

## Design and evidence

Existing PostgreSQL/SQLAlchemy services remain synchronous. Extract small shared contracts below HTTP, not a whole-stack async rewrite. Validate explicit contract terms and referenced evidence at submission and approval. Use one UTC governance clock, transactional command audit, bounded thread offload for middleware, and stable financial preview snapshots with separate current-access checks. Optimize from query evidence; never remove entitlement checks or arbitrarily cap trade history.

Research checked 2026-10-16 against installed Pydantic 2.13.5, SQLAlchemy 2.1.1, FastAPI 0.141.1, Starlette 1.7.0 and PostgreSQL 18:

- [Pydantic extra fields](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra): reject unmodelled contract data rather than silently discard it.
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/): cross-field reconciliation supplements field typing; unknown economics are not zero.
- [OWASP object authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/): resolve every referenced object within its actual scope, not merely by UUID existence.
- [Starlette thread pool](https://starlette.dev/threadpool/): synchronous database units must not execute directly in async request middleware. Do not move a live connection across concurrent tasks.
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html), [SQLAlchemy 2.1 connections](https://docs.sqlalchemy.org/en/21/core/connections.html): establish isolation before queries; stable snapshots do not replace current-rights checks.
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html): inspect measured plans before inventing indexes or caches.
- [Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): commit durable audit intent with a command; avoid an ambiguous second-write success/failure contract. Prefer existing transactional audit when sufficient over introducing a broker.

These sources establish technical principles, not universal financial product conventions. Exact validation and compatibility choices below are project decisions.

## Tasks / completion ledger

### 1. Instrument integrity — FIX-SP-001/002/003; BACKEND-002/003

- [x] Strict nested/top-level structured draft fields; reject absent/non-finite required economic inputs while preserving explicit zero where contractual.
- [x] Reconcile headline and explicit schedule economics, including variable/step-up cases without forcing one flat coupon onto them.
- [x] Extract dependency validation into `apps/reference_api/structured_product_dependencies.py`: source pairing/scope, fixing instrument/date/value/basis and market-data rights; calendar visibility/publication/eligibility. Call at proposal submission and approval before materialization.
- [x] Governed calendar-backed payment-date generation/validation, preserving explicit sourced exceptions and existing immutable approved history. Unknown day coverage must block generated dates.
- [ ] Focused pure contract and disposable integration tests: unknown terms; missing vs zero; inconsistent coupon; foreign/mismatched source/observation/snapshot; foreign/unsealed calendar; weekday holiday; approval-time revocation; valid manual/sourced and variable schedules.

### 2. Strategy isolation — BACKEND-004

- [x] Use strategy predicates for NAV queue rows and counts before pagination, or explicitly retire the legacy category without deleting historical data.
- [x] Disposable tests: selected/empty/ALL groups, reference-only actor, inaccessible strategy IDs and mixed counts/pages.

### 3. Request reliability — BACKEND-005/006/007

- [x] Extract synchronous authorization unit; read body before opening database connection, offload complete unit, apply middleware transaction budgets.
- [x] Transactional command audit provenance and truthful supplemental failure behavior; no loss of required audit, no committed-command false rejection. Test rollback, replay and fault injection on isolated commands.
- [x] Shared lower-level UTC governance date across membership, module, strategy and dataset checks; preserve explicit exchange/contract zones. Midnight/non-UTC and worker propagation tests pass; dedicated DST coverage remains additional work.
- [ ] Concurrency/pool budget and safe correlated errors tested without operating services.

### 4. Measured resolution performance — MEASURES-005

- [x] Reproduce representative synthetic preview and capture SQL counts/phase timings/query plans.
- [x] Bound entitled observation selection by actual requested dates and reuse immutable policy/calendar and request-scoped rights decisions under complete scope keys.
- [ ] Reduce repeated display checks and forward proof reads without weakening current rights, both-leg flat safety or backdated-correction evidence.
- [x] Assert identical values/hashes and fewer SQL statements on a fixed synthetic workload; disclose remaining large-history benchmark limits separately.

### 5. Completeness, snapshots and boundaries — BACKEND-008/009/010

- [x] Searchable/paged valuation options with count/page metadata and selected-ID retrieval; update BFF/UI consumers if required. Read/calculate scopes remain separate; no silent 500 cap.
- [x] Stable financial preview transaction boundary with separately current authority/display revalidation; deterministic two-connection mutation/revocation tests.
- [x] Move the reviewed reusable governance/dependency/booking-proof contracts below HTTP adapters; preserve compatibility surfaces and historical evidence. Mandatory architecture regressions cover the five reviewed services; broader decomposition remains separate.

### Final verification / documentation

- [x] Focused RED→GREEN evidence per task; affected domain regressions in disposable DB; OpenAPI/generated-contract checks and necessary frontend tests.
- [x] Broader backend regression once changes stabilize, not after every tiny edit. Record failures and reruns accurately.
- [x] Reconcile FIX.md, KNOWLEDGE.md, AGENTS.md and capability records/register/map. Preserve original findings and distinguish fixed, bounded, suspected and deferred deployment gates.

## Review focus

Revalidation must not rewrite old financial evidence; publication/approval must not use a stale authorization cache; optional economic fields cannot disappear during normalization; failed refresh/audit is not an uncommitted command; all rights and strategy predicates apply before aggregation/count/pagination. Preserve the dirty checkout. No automatic local migrations or seed changes.

## Progress

### Approved shared-model follow-up

The user approved the remaining term-model extraction after its rationale was
explained. `ConventionBase`/`FutureConvention` moved to shared booking conventions;
`GenericSwapTerms`/`Frequency`/spread conversion moved to shared swap terms. API
imports re-export identical classes and valuation now imports domain owners.
Removed the strict architecture xfail. Watched four ownership/import failures,
then all 75 focused parity/rule tests passed; entire OpenAPI and frozen alias JSON
fingerprints are unchanged. No operating migrations/changes or frontend work.
Ruling: move the common convention base with the future model, not a duplicate base
copy — preserves API subclass identity and prevents divergent validation; no change
to other API envelopes or product support. Keep remaining unrelated compatibility
imports/decomposition explicit under BACKEND-009, rather than broadening this move.
Final verification: 77 pure checks passed; affected integration cohort 166 passed,
zero skips/xfails and nine dependency warnings (610.28 s). The new module guards
extend the existing five service checks. OpenAPI remains byte-equivalent under its
canonical fingerprint. Sequential self-review and 868-target documentation link
check passed. See the delivery record for the dedicated legacy migration-test DB
fixture, warning and scope limitations. No operating activation or commit/push.

### Earlier verification chronology (superseded where noted above)

Current handoff supersedes earlier chronological notes: [delivery/verification record](../../delivery/quality-reviews/2026-10-16-backend-remediation.md).
131-test remediation cohort and 161-test broader cohort passed (overlapping counts);
one strict architecture xfail records the explicitly approval-gated Future/Swap
term-model move. All 921 frontend and 11 browser cases pass. TypeScript/OpenAPI and
deterministic generation pass; Git-clean generated check fails on uncommitted
checkout changes, not regeneration drift. No operating activation/commit/push.

Ruling: retain existing EXPLICIT API schedule compatibility and the legacy default
inheritance flag; new edited UI schedules require a reason and graph rows supersede
generator summaries — avoids rewriting approved history or incidental defaults;
cost is weaker mandatory reason coverage for older direct clients.
Ruling: preserve uncapped full `/options` bootstrap for older consumers while primary
selectors page/search — prevents missing valid choices; cost is large-register
bootstrap work until those secondary consumers migrate.
Ruling: current preview rights check runs after releasing the financial connection —
pool-size-one regression reproduced the nested-checkout failure; no two connections
are held simultaneously. Access can still change after any completed authorization
decision; no global lock on permission administration is implied.
Ruling: smaller lower-domain extractions proceed, but shared Future/Swap contracts
remain untouched after the safety rejection pending specific approval. A strict
xfail makes that exact architecture debt explicit rather than hiding a failed test.
Final review: self-review, per explicit sequential/no-subagent user direction.
Final fix pass: noncontractual calendar-kind preview and explicit-graph serialization
round trip each reproduced RED then passed GREEN. Final affected pure cohort:
53 passed, one strict expected architecture failure. Generated inheritance remains
enforced; explicit schedule serialization does not silently change its meaning.
Remaining unchecked tests include exhaustive snapshot permutation and dedicated DST/
concurrent-timeout fault coverage. Forward proof batching, full-history checkpoints,
representative operating/multi-user benchmarks and broad decomposition remain open.

- Contract intake RED→GREEN: 34 focused tests pass (strict root/nested fields, finite decimals, explicit zero, missing/flat/variable coupon reconciliation). Eight existing isolated source-scope tests also pass. Persistence and nested dependency/calendar checks remain in progress; no whole-workstream completion claimed.
- Further integrity checks: 37 pure API/draft tests; 22 disposable persistence/source tests; three payment-calendar tests pass in separate runs. Variable period rates now persist individually; KIP barriers reconcile; missing summary barriers stay absent. New published-calendar options/payment-date preview and form integration typecheck; 18 focused frontend tests pass. Expanded browser/BFF acceptance and headline-summary review still pending.
- Queue strategy predicate: reproduced SELECTED/empty metadata leak, then seven queue/scope regressions passed. Rows and counts now share the pre-pagination predicate.
- Middleware offload/budgets explicitly approved after safety gate. Nine pure clock/execution tests pass; slow body no longer spans an auth connection. Transactional audit still pending. Wider UTC clock adoption separately awaiting safety approval; its regression currently reproduces the host-date mismatch.
- Initial code inspection confirms the recorded middleware blocking, NAV queue predicate omission and options cap. Research and design recorded; implementation not yet claimed.
- This maintained plan doubles as the sequential ledger. Existing user directions override skill defaults for separate approval gates, subagents, worktree creation and automatic commits.
