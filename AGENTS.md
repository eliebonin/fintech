# Repository guidance

## Scope and reading order

This file governs this repository. Read the more specific
[Operations Console guidance](apps/ops-console/AGENTS.md) before frontend changes.
Start with [documentation home](docs/README.md), the relevant feature in the
[register](docs/product/feature-register.md), and its capability record and
[implementation map](docs/product/feature-implementation-map.md).
Historical plans and archives do not establish current delivery.

Use [KNOWLEDGE.md](KNOWLEDGE.md) for the reviewed architecture and
[FIX.md](FIX.md) for evidenced open findings. These root documents supplement the
maintained domain references; they do not replace the capability register.

## Module boundaries and invariants

- `tooling/reconciliation_csv/` is an optional external-dataset convenience tool,
  not a product subsystem. Application packages and product tests must not import
  it. Keep source-specific adapters, mockup completion, operators and their tests
  there; use existing governed services without weakening validators. Do not add
  its execution to startup, migrations, product CI seeding or tenant endpoints.

- `apps/reference_api` owns access-checked reference reads, proposal workflow and
  database mutations. Its local header/session identity is not production
  authentication (BACKEND-001). `security_master_schema` owns schema/domain foundations;
  `alembic` owns migration history.
- `apps/ops-console` uses its Next.js server/BFF to propagate validated context;
  browser components must not access the database or choose authoritative tenant
  and actor identity through model-generated inputs.
- `market_data` owns acquisition and governed calendar/data evidence; `positions`
  reconstructs positions and `valuation` owns bounded economic P&L/review.
- Structured-product submission and approval are separate actions. Automated
  submission must retain tenant visibility and REFERENCE_PROPOSE authority;
  materialization still follows the approval workflow.
- Preserve decimal precision, explicit schedules, economic exceptions, source
  evidence and user corrections. Unknown economic inputs must not become zero
  when adding ingestion. A source ID does not itself establish tenant ownership.
- Strategy permissions bind action and scope within the same active group. Use
  `strategy_access.strategy_predicate` before pagination/count/aggregation and
  `require_strategy_action`/booking authorizers before writes and idempotent replay.
  Admin roles grant ACCESS_MANAGE, never a strategy bypass. ALL includes future
  strategies; empty SELECTED denies access. Unknown legacy resolution context is
  not shared. Read [strategy scope delivery](docs/delivery/strategy-access-scopes.md)
  before adding endpoints that expose trades, valuation evidence or scoped config.
- STRATEGY_CREATE is separate from STRATEGY_WRITE. Initial selected-group access
  is transactional; creators do not receive implicit ownership. API pool actor
  bindings must be cleared after a request; browser identity/scope inputs are not
  authoritative. Keep group revision/preview conflict checks and audit together.
- Update capability record, register and implementation map together when support
  changes. State static tests, live activation, browser and financial acceptance
  separately. Keep `docs/archive` immutable except for the explicitly recorded
  [17 October editorial anonymisation](docs/delivery/provider-neutral-repository-20261017.md).
  Repository naming policy is checked by `tests/test_repository_neutrality.py`.

## Verification and operational safety

The [2026-10-15 backend/API audit](KNOWLEDGE.md#backendapi-audit--15-october-2026)
is dated evidence. The [October 16 remediation](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md)
records current fixes and remaining partial work; do not reintroduce the original defects.
When extending those boundaries:

- Resolve nested source/observation/snapshot references with tenant scope and
  economic agreement at submission and approval. A global foreign key or a
  top-level source check does not validate nested provenance.
- Validate calendar visibility and contractual eligibility, not merely ACTIVE
  status. Pin approved dependencies without rewriting historical evidence.
- Apply strategy predicates to secondary queues, counts and pagination as well
  as primary detail endpoints; tenant scope alone is insufficient.
- Do not perform blocking synchronous database work directly inside async
  middleware. Budget every connection path and preserve atomic command/audit and
  idempotent retry semantics. Use one documented governance clock for authority
  dates, distinct from instrument/session time zones.
- Profile SQL counts and phase timings before optimizing shared selection.
  Request-scoped reuse must preserve actor, tenant, action, policy and evidence
  boundaries; cross-request caches require explicit revocation semantics.
- Keep matching-series constraints before broad observation scans, and retain
  every eligible candidate for policy/provider ranking. Forward proof batches
  must bind the request and transaction and consume every chunk; their 500-ID
  chunk size is not a total limit. Keep current per-batch disclosure and existing
  per-user permission resolution when optimizing presentation reads. See the
  [query-efficiency delivery](docs/delivery/quality-reviews/2026-10-16-query-efficiency.md).
- Keep shared economic/authority contracts below HTTP adapters. Incremental
  extraction needs focused regressions; do not replace legacy retained evidence
  simply because its active workflow is being retired.
- Shared `FutureConvention`/`ConventionBase` live in
  `security_master_schema.booking_conventions`, and `GenericSwapTerms` in
  `security_master_schema.swap_terms`. Financial services import those owners;
  API modules retain compatibility exports. Preserve alias serialization and
  existing validation when moving models; run the schema/frozen-JSON parity and
  architecture tests rather than regenerating changed contracts without review.
- Use `security_master_schema.governance_clock` for current authority/licensing
  dates; never substitute host-local dates for explicit economic/session dates.
  Keep complete sync DB units off the async event loop. New tenant command routers
  must use the audited route adapter and retain audit inside the effect transaction;
  independent transactions must retain acceptance provenance with their durable work.
- Monetary preview read reuse requires a single REPEATABLE READ transaction and
  full request scope. Clear scoped caches and actor bindings before pool reuse;
  fresh current-access release checks must not read that cache or hold two pool
  connections simultaneously. Query/count/selected-ID filtering precedes paging.

For valuation work, read the [methodology matrix](docs/architecture/market-data-and-valuation/valuation-methodology.md)
and linked numerical tests. Keep execution economics, boundary marks, economic
date, actual price date and information availability distinct. Applied rules
explain frozen facts only; never reprice in presentation code or backfill old
financial evidence. Daily earnings are not the accumulated accrued stock; dated
cash snapshots are separate stocks. Booking support is not valuation readiness.
Monetary-measure previews must check selected price dates against replayed share
units, normalize booked fund-share-class types and retain canonical NAV identity.
Mock data must remain explicitly synthetic; never grant third-party source rights
or rewrite existing policy versions merely to make a preview pass.
Futures monetary notional is not contract MTM or a NAV asset. Booked CONTRACTS
already count canonical contracts: apply the frozen monetary multiplier once,
not again through listing metadata. Missing clearing/variation-margin evidence
must remain unavailable, never an assumed zero market value.
Deliverable-forward monetary previews show two signed contractual currency legs,
not discounted currency exposure or MTM. Their quote obligation uses frozen agreed
rate, not the closing P&L execution rate. Do not filter a base-flat mixed-agreement
forward before checking both obligations; retain an exception rather than invent
an average rate. See the [cross-measure review](docs/delivery/quality-reviews/2026-10-15-position-measures-review.md).
Daily-interest writers must persist typed `daily_earned_interest` and `currency_id`
with date/bond/tenant/strategy scope and matching retained source evidence. Missing
optional balance evidence must not become a zero balance or zero receivable FX.
See [FIX.md](FIX.md) for reviewed limitations.

Coupon schedules describe expected contractual events; actual payment confirmations
are separate retained facts. Neither writes daily earnings, trades or cash balances.
Do not infer entitlement, full settlement or new P&L from a scheduled/confirmed date.
See [coupon boundary](docs/delivery/bond-coupons-20261015.md).

Use focused tests first. Never run database tests against the operating
`platform_secm` database. Follow the
[owned disposable PostgreSQL runner](docs/delivery/README.md#safe-postgresql-verification).
Do not migrate/seed operating databases, restart services or call live extraction
providers merely to verify documentation or pure draft logic.

Confirmed offline command from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
./.venv/Scripts/python.exe -B -m pytest tests/test_structured_product_draft.py tests/test_structured_product_api.py -q -p no:cacheprovider
```

Configured frontend/contract commands are defined in [package.json](package.json):
`pnpm test:ops-console`, `pnpm typecheck:ops-console`, `pnpm contract:check`, and
`pnpm contract:generate:check`. Their existence is not evidence that they passed
for a new change. Consult installed Next.js guidance required by the app's local
AGENTS.md before editing frontend behavior.

Preserve unrelated working changes. Keep fixes and their regression evidence
separate from documentation-only reviews, and do not claim real-termsheet accuracy
from synthetic fixtures.

## Frontend review and extension guidance

The [October 16 remediation](docs/delivery/quality-reviews/2026-10-16-frontend-remediation.md)
implements the shared write-context, recovery and display protocols implicated in
FRONTEND-001–010. Use `browserFetch` for same-origin browser BFF mutations; do not
replace the document stamp with freshly fetched identity or bypass Next Proxy.
The fingerprint is intent correlation, never authentication. Keep endpoint authority.
Retain exact request/key on uncertainty; a failed follow-up read is not a failed write.
Run `pnpm --filter ops-console test:browser` for DOM/navigation-sensitive changes,
using its isolated synthetic servers, not operating databases.

See the [frontend audit](KNOWLEDGE.md#frontend-audit-2026-10-15) and its linked
findings before extending an existing form. These are guidance, not claims that
all older flows already comply:

- BFF writes must verify the tenant/actor context in which the form was prepared,
  in addition to authorizing the current session. A switch in one tab does not
  invalidate another tab's draft automatically.
- Keep reviewed payload, idempotency key and intent together through uncertain
  outcomes. Differentiate committed-but-refresh-failed from command rejection;
  retrying a read is not resubmitting a write.
- Preserve upstream request IDs through error translation. Use decimal-string
  formatting for financial values; rounded displays need exact inspection and
  must not imply that small nonzero values are zero.
- Represent loading, forbidden, unavailable and successfully loaded-empty
  separately. Cross-tab links must activate the destination and manage focus.
- Prefer typed boundary adapters and small feature modules to duplicated
  request/state helpers. Keep permission and financial evidence checks on the
  server; display-only reuse must respect current identity and rights.
- Hook-mocked/static-render/source-text tests do not establish browser focus,
  native form validation, hydration or responsive/assistive acceptance. Preserve
  cheap tests and add isolated real-browser journeys where those risks matter.
- Consult the installed Next docs, not remembered APIs. In installed 16.3.4,
  the error-boundary `retry` prop is supported. Avoid a speculative reset rewrite.
