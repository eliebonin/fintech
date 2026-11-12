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
The [architecture atlas](docs/architecture/atlas/README.md) separates current
database references, code dependencies and processing flow. Its dated inventory
is not a runtime call graph or a guarantee of production feature completion.

## Module boundaries and invariants

- Performance evidence must distinguish SQL count, measured database/driver time, complete service time and HTTP/BFF time. State the dataset, warm-up and measurement boundary; lower query count alone does not establish a latency bottleneck. Keep proposed permission-context reuse distinct from implemented authority checks.

- Lifecycle discovery source batches are request/tenant/connection/transaction scoped. Historical identity batching must retain original BOOKED uniqueness/fingerprint/date/currency/venue checks and cancelled-snapshot handling. FX batches must use exact strategy/instrument pairs, native exposure validation, root-isolated annotation checks and full pending-preparation revalidation. No discovery batch or global cache replaces financial command authority. See [reader optimisation](docs/delivery/lifecycle-reader-batching-20261111.md).

- Lifecycle date proximity is display-only, added after pagination. Preserve the distinction between configured holiday calendars, explicit weekday estimates and unknown source coverage. Never roll contractual dates, infer payment/approval or change financial eligibility from a colour. Calendar reads remain scoped and batched; relative dates use report recording time rather than browser time.

- `lifecycle.worklist` is a read model: scope candidates before positions/counts,
  retain nonzero allocations at net0, expose unknown evidence and never post on
  discovery/navigation. Full pending-source checks reuse the native candidate
  fingerprint. Stable event keys are not persisted task or financial authority.
  Bond/FX maturity and sourced coupon notices are delivered; use native commands for effects.
  Coupon inspection is read-only at every tier and currently shares bond notification visibility.
  Futures/option deadlines use independent `FUTURE_EXPIRY`/`OPTION_EXPIRY` manual0/notification1 selections; never route
  those events to native financial commands. Keep last-trading instants distinct from expiry,
  settlement and delivery dates; first-notice/broker deadlines and AM/PM option fixing remain unmodelled.
  `STRUCTURED_OBSERVATION` is independent0/1 and always INFORMATION. Use current-linked
  schedules and source-defined thresholds; never infer barrier outcomes, coupon entitlement
  or financial actions. Distinguish held swaps/quantities from observed structured references.
  Historical windows use current approved source knowledge, not a reconstructed past source state.
  Structured contractual sources use the scoped `TermsScheduleBatch` graph/table reader;
  keep per-root rendering SQL-free. Batch schedule/identifier reads and merge chunks in
  source order. Never introduce a global visibility cache, skip full-history counts, or
  bypass per-root private-reference, depth/cycle and evidence checks. Query-budget tests
  must use many distinct contracts, not only many strategies sharing one contract.
  Option expiry does not prove exercise, assignment or lapse. Withhold inaccessible underlying
  names/IDs; compare current sources against original BOOKED facts without rewriting them.
  Review due is not unpaid; never infer cash representation, entitlement or income from a notice.
  Current ledger knowledge uses `lifecycle.recording_clock.recording_now`, including
  fresh post-write closure checks; preserve explicit economic/historical cutoffs.
  The worklist drawer reuses native commands and must retain uncertain-request identity.
  See [worklist boundary](docs/delivery/lifecycle-worklist-20261105.md).

- `lifecycle.entitlements` owns the platform subscription ceiling; `lifecycle.assistance`
  owns scoped strategy/event choices; `assistance_transitions` owns reviewed tenant
  downgrade preparation. Purchase grants no actions or independent-review bypass.
  Preserve selected values above a reduced ceiling as blocked, never silently clamp.
  Acquire the tenant lifecycle shared/exclusive transaction lock before native locks.
  Prepared custom and standard inputs must both survive native revalidation; never drop standard fields when rebuilding an immutable preparation.
  Tier2 non-REVIEW confirmation needs a retained proposal; no-proposal DIRECT needs
  selected3 and ceiling3. Maturity discovery remains read-only; other detectors/billing remain deferred. See
  [delivery](docs/delivery/lifecycle-assistance-entitlements-20261105.md).

- Lifecycle maturity must preserve tenant-selected joint allocation dimensions before
  economic netting. `positions.allocations` reuses ledger recognition/cancellation;
  `trading.allocation_policy` and immutable annotation sources own classification
  rules. Preserve nonzero opposing allocations even when the instrument total is zero.
  Generated entries require governed annotations, exact movement identity, source-bound
  fingerprints and atomic all-entry posting/cancellation. No guessed FIFO, historical
  relabelling or payment creation. See [delivery](docs/delivery/lifecycle-allocation-preservation-20261104.md).

- Product monetary previews validate original bookings below HTTP. Option strike
  notional is not premium value or delta exposure; note face/funded value is not
  payoff look-through. CLEAN notes require their assessed closing bridge with
  original hash and matching nominal/currency; do not send them through bond
  coupon reconstruction. Missing risk inputs never erase an independently
  supported reference or market value. Whole-swap marks already embed funding,
  orientation and leverage. See [coverage](docs/delivery/expanded-position-measures-20261103.md).

- `valuation.source_dependencies` owns frozen non-ledger source scopes and the
  shared detail/history/worklist/publication comparison. Price windows follow
  requested/used marks, not merely economic dates; policy/calendar versions stay
  pinned. Preserve explicit nested batch correlation and SQL filtering before
  pagination. Source changes never rewrite published financial amounts. Bond
  monetary previews use exact-date current maintained stocks, preserve DIRTY
  precedence and never allocate an instrument stock across listings implicitly.

- Daily interest Ops review uses immutable daily/balance receipts. Review drafts
  must not change financial inputs. Balance review requires a current validated
  daily receipt; whole-population writes require scoped VALUATION_REVIEW, not RUN.
  Explicit gaps remain unknown and create no zero inputs. See
  [two-stage maintenance](docs/delivery/interest-daily-review-20261103.md).

- Accrued maintenance has three stages: validated daily sources, explicit local
  history update, valuation FX consumption. `valuation.balance_history` owns stock
  inputs/builds; per-attempt `accrued_interest_balance` remains output evidence.
  Never reconstruct missing bond stocks inside valuation, assume scheduled coupons
  were paid, erase new-period accrual or turn unknown into zero. Verify original
  sources before checkpoint reuse. See [current rules](docs/architecture/market-data-and-valuation/accrued-balance-fx.md).

- `regulatory_reporting` owns reporting-entity assessment, retained execution
  preparation/review and PREPARATION_ONLY exports. REPORTING actions/module and
  strategy scope are independent of trading/valuation. Never label local READY
  or an export as FCA schema acceptance, submission or acknowledgement. Preserve
  execution units/time/Decimal facts, human decisions, source-change reassessment
  and immutable export membership. See the [capability and limits](docs/product/features/regulatory-reporting.md).

- `tooling/reconciliation_csv/` is an optional external-dataset convenience tool,
  not a product subsystem. Application packages and product tests must not import
  it. Keep source-specific adapters, mockup completion, operators and their tests
  there; use existing governed services without weakening validators. Do not add
  its execution to startup, migrations, product CI seeding or tenant endpoints.

- `apps/reference_api` owns HTTP context, contracts, error mapping and audited
  transaction wiring; reference/booking orchestration is still partly API-owned.
  Shared workflows belong below that adapter. Protected local requests require
  verified opaque sessions; session bootstrap requires the server-only operator
  capability. Never restore header/demo-user authentication or a non-local startup
  bypass. [Local safeguards](docs/platform/local-identity-safeguard.md) remain
  distinct from deferred production authentication (BACKEND-001).
  `security_master_schema` owns schema/domain foundations;
  `alembic` owns migration history.
- `apps/ops-console` uses its Next.js server/BFF to propagate validated context;
  browser components must not access the database or choose authoritative tenant
  and actor identity through model-generated inputs.
- `market_data` owns acquisition and governed calendar/data evidence; `positions`
  reconstructs positions and `valuation` owns bounded economic P&L/review.
- `trading` owns the listed-cash command, its command models/store and the shared
  reference/annotation/recognition/linked-correction dependency closure. API and
  file confirmation call `trading.booking.book_cash_trade`; API detail DTOs stay
  in the adapter. Preserve current authority before replay, historical retry
  fingerprints and BOOKED bytes. The command owns only its effect savepoint;
  callers own outer commit/audit and all-or-nothing import receipts. Keep API
  projection failure within its enclosing savepoint. Other product writers and
  cancellation orchestration are still API-owned. See [cash extraction](docs/delivery/cash-booking-service-extraction-20261029.md).
- Fund-unit TRANSFER/REINVESTMENT commands are separate from positive-price
  purchases. Preserve frozen quantity/classification proof, native authority and
  caller audit. Daily policy NAV excludes moved principal from market gains;
  unconfirmed reinvestment income stays explicit. Never turn a source zero into
  a purchase or generated income. See [movement conventions](docs/delivery/fund-unit-movements-20261030.md).
- Rate-exchange swaps retain two opposing floating legs below HTTP in
  `security_master_schema.rate_swap_terms` and `trading.rate_swaps`. Keep separately
  priced components as separate instruments/trades/series; whole-mark P&L applies
  signed booking quantity once, without repricing or multiplying by leg notionals.
  First-time completion of sourced private shells is not general term amendment.
  See [scope and limits](docs/delivery/rate-exchange-swaps-20261030.md).
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

- Missing required valuation marks may stage partial results only under explicit
  WARN/MANUAL_OVERRIDE rules. Preserve the full original projection/cash snapshots
  and unavailable contributions; numeric subtotals contain only calculated rows.
  Required-mark incompleteness blocks ordinary/self publication and survives
  amendments. Reviewed exact marks live in `valuation.mark_overrides`, require
  independent real operators, current source rights and a new calculation;
  never insert them as provider observations. Optional interest/cash snapshots
  retain their separate nonblocking semantics. See [delivery](docs/delivery/incomplete-price-review-20261031.md).

- `tenant_reference` owns shared source discovery/curation; `trading.profiles` owns immutable profile rules, strategy assignments and their impact checks. All booking/import/correction/lifecycle consumers resolve one pinned strategy version. Publishing must never upgrade assignments or the creation default. Do not restore global-required or missing-assignment fallbacks. Preserve config-before-strategy/source lock order, exact source inheritance proof and native required economics. Source usage and assignment counts apply strategy scope before pagination. See [profile delivery](docs/delivery/tenant-reference-data-trade-profiles-20261104.md).

## Verification and operational safety

Database setup uses private `scripts/configure_local_database.py` configuration;
normal API startup must use a non-owner runtime login. Use
`scripts/migrate_database.py` for local maintenance and
`scripts/run_isolated_python_tests.py tests/... -q` for owned disposable tests.
Preserve existing Compose project/database/volume names; never reseed to satisfy
new defaults. Keep audit append-only and denial logs free of tokens/raw inputs.
Retain nonce CSP, HTTPS cookie attributes and local HTTP testing. See
[security setup and limits](docs/platform/security-controls.md).

All market-data use requires an explicit active profile/activity and appropriate
tenant purpose, including current DISPLAY checks on old financial evidence.
SYNTHETIC evidence applies to invented data only, never personal/commercial feeds.
Do not restore missing-profile or display-purpose fallbacks. Expensive HTTP work
uses `workload_admission` inside verified identity and before domain dependencies;
its separate coordination pool must not borrow the financial pool's only slot.
Keep admission through actual work/response cleanup, preserve manual unchanged-key
retry and ordinary status/log reads, and classify/test new expensive routes.
Never use concurrency controls to truncate financial populations. See
[governance and admission](docs/platform/dataset-rights-and-workload.md).

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
- Canonical evidence encoding, evidence hashes and finite-Decimal validation live
  in `security_master_schema.evidence`. New shared consumers import that owner;
  `valuation.economics` retains identity re-exports for existing callers and owns
  the P&L formulas. Preserve exact bytes, rejection messages and precision limits.
- Pricing-policy commands/models live in `market_data.pricing_policies` and
  `pricing_policy_contracts`. Creation checks current module/action/strategy scope
  before retry lookup. Pass the caller's Connection; never commit or open a new
  engine inside the command. `policy_definition` is an internal read projection,
  not an independently authorised endpoint. API wrappers retain response models,
  errors and atomic audit; operator workflows retain their own authority checks.
  See the [phases 1–3 extraction](docs/delivery/api-service-extraction-20261029.md).
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
and [cross-layer state review](docs/delivery/quality-reviews/2026-10-27-valuation-state-review.md)
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
Daily futures P&L is a separate price-variation bridge, translated at each
economic day's closing FX; margin cash remains in cash snapshots. Preserve the
explicit futures variation term in batch reconciliation and null per-position
asset values. See [delivery](docs/delivery/futures-daily-pnl-20261027.md).
The [linear crypto extension](docs/delivery/linear-futures-extension-20261028.md)
reuses that bridge for approved UNDERLYING_UNIT cash/physical contracts. Shared
capability checks live below HTTP; active governed asset/currency roles replace
index-only reference checks. Preserve ordered quote/asset currency locks and the
frozen original convention. Physical settlement does not authorize automatic
expiry, delivery, token receipts or post-cutoff executions. Monetary-preview
coverage remains separate from daily P&L.
Fully funded note P&L uses whole-note marks and frozen denomination/divisor once.
Keep CLEAN/DIRTY/NONE explicit in source/execution evidence. Only CLEAN adds
separate assessed daily interest and accrued-stock FX; DIRTY/NONE must not add
embedded accrued again. Notes are not bonds: do not reuse bond coupon-receipt
replay to invent conditional coupons or detached receivables. Preserve the bond
payment-only guard when recognizing explicit note coupon income. See the
[bounded note delivery](docs/delivery/structured-note-pnl-20261028.md).
Cash-product classification belongs in `security_master_schema.cash_products`.
Preserve concrete wrapper/spot types; generic ETP requires effective terms, never
an ETF default. Normalize historical SHARES labels to UNITS for wrapper/token/fund
counts only in projections, preserving original evidence and factors. Crypto uses
the selected listing and trade quote currency, with no assumed stablecoin peg.
Its calendar must cover each requested price day as open; bank weekends cannot
silently become Friday. Native RAW is not token share-split proof. See
[ETP/spot delivery](docs/delivery/etp-spot-crypto-pnl-20261028.md).
Deliverable-forward monetary previews show two signed contractual currency legs,
not discounted currency exposure or MTM. Their quote obligation uses frozen agreed
rate, not the closing P&L execution rate. Do not filter a base-flat mixed-agreement
forward before checking both obligations; retain an exception rather than invent
an average rate. See the [cross-measure review](docs/delivery/quality-reviews/2026-10-15-position-measures-review.md).
Plain-bond DIRTY market quotes require their exact observation-paired per-100
quoted accrued component before conversion to CLEAN. The component inherits
source rights and currency; it is neither daily earnings nor a strategy stock.
Preserve RAW/share basis separately, source/cutoff dates and component-only
corrections. Revalidate paired selections before publication; monetary previews
still use original DIRTY values. See [delivery](docs/delivery/bond-dirty-to-clean-20261028.md).
Daily-interest writers must persist typed `daily_earned_interest` and `currency_id`
with date/bond/tenant/strategy scope and matching retained source evidence. Missing
optional balance evidence must not become a zero balance or zero receivable FX.
See [FIX.md](FIX.md) for reviewed limitations.

Coupon schedules describe expected contractual events; actual payment confirmations
are separate retained facts. Neither writes daily earnings, trades or cash balances.
Do not infer entitlement, full settlement or new P&L from a scheduled/confirmed date.
See [coupon boundary](docs/delivery/bond-coupons-20261015.md).

Bond schedules contain typed COUPON and PRINCIPAL cashflows. Keep final coupon
and principal separate, with sourced dates and per-100-original-nominal amounts.
A principal row is not a coupon confirmation or automatic redemption. Preserve
old evidence IDs; see the [full schedule reference](docs/architecture/trading-and-operations/bond-cashflow-schedules.md).

Accrued-stock FX is a separate CARRY component, using opening monetary stock and
policy FX. Preserve unknowns, source anchors and actual receipt revisions; a
scheduled coupon never proves settlement. Derived `nav.accrued_interest_balance`
rows are immutable output evidence, not future source inputs. Unpaid receivables
after sale must retain their explicit scope guard and every dependent FX source.
See [rules and limits](docs/architecture/market-data-and-valuation/accrued-balance-fx.md).

Keep optional-coverage warnings concise and discoverable: shared collapsed review
summary, scoped row notes and full-result Attention filtering; genuine publication
blockers remain separate. Cash-only actual-window gaps count as partial, never
historical/disappeared cash scopes. Reporting-stock read projections use only
frozen boundary conversions and preserve independent availability, exact amounts
and original evidence; no current-FX query. See [review delivery](docs/delivery/valuation-review-signals-20261029.md).

Use focused tests first. Never run database tests against the operating
`platform_secm` database. Follow the
[owned disposable PostgreSQL runner](docs/delivery/README.md#safe-postgresql-verification).
Do not migrate/seed operating databases, restart services or call live extraction
providers merely to verify documentation or pure draft logic.

Dependency changes retain both complete committed locks and Python hashes. Run
the [dependency checks](docs/platform/dependency-security.md), inspect actual
transitive versions and keep advisory/service failures visible. Use supported
Node 24 for frontend verification, matching CI; preserve generated-contract
bytes and existing financial/authority behaviour during tooling upgrades.

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
