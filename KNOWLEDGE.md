# Reviewed repository knowledge

**Status:** Maintained scoped review  
**Content type:** Reference  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-16 (frontend and scoped backend remediation; dated reviews retained)

Analyzed root: `C:/Users/forte/Elie/projects/python/fintech`. This is the implementation
repository; `C:/Users/forte/Documents/ChatGPT/Tech V2` is a separate workspace.

## Backend remediation — current October 16 follow-up

[Delivery, tests, research and remaining boundaries](docs/delivery/quality-reviews/2026-10-16-backend-remediation.md)
supersede the original defects described in the dated audit below. New structured
proposals use strict economic models, reconciled period rows and visible sealed
calendar/dependency checks at submission/replay/approval. Generated payment dates
come from assessed server calendar days; explicit sourced schedules remain distinct.

`security_master_schema/governance_clock.py` owns the request-pinned UTC authority
date. Middleware offloads a complete synchronous authorization transaction after
body parsing and applies DB budgets. `command_audit.py` owns lower-level request
intent; `request_audit.py` captures endpoint resources before the effect transaction
commits. Ordinary commands audit atomically; independently committed calculations
audit REQUEST_ACCEPTED with the retained attempt rather than claiming completion.

Monetary previews now share REPEATABLE READ inputs, then release the connection
before fresh current strategy/display-rights checks. Resolver reuse is scoped to
that transaction/request, not a cross-user cache. The measured synthetic SQL
reduction does not certify operating latency or full-history scalability.

Valuation selectors have authorized search/count/page/selected-ID retrieval and
primary paged UI controls. Legacy `/options` no longer silently truncates, but
still materializes its bootstrap register. Reusable errors, booking controls,
reference authority/visibility and forward-reference loading now live below HTTP
with API compatibility imports. After explicit user approval, `ConventionBase` and
`FutureConvention` moved to `security_master_schema/booking_conventions.py`, and
`GenericSwapTerms`, `Frequency` and the spread conversion helper to
`security_master_schema/swap_terms.py`. API modules re-export the same classes;
valuation imports the lower definitions directly. The architecture regression is
now mandatory, not an expected failure. Whole-API schema and representative frozen
JSON fingerprints match the pre-move baseline. BACKEND-009 still covers broader
decomposition (including remaining compatibility imports in accrual/amendment/bond
lifecycle services); MEASURES-005 remains partial. Production identity is unchanged.

[Query-efficiency follow-up](docs/delivery/quality-reviews/2026-10-16-query-efficiency.md)
adds explicit candidate-series selection, batched licensing/history/roster reads,
statement-local catalogue populations and complete chunked forward proof loading.
The runner now uses the stable resolution scope during calculation and clears it
before staging. Local read-only probes show identical two-row price candidates
at ~6 ms versus ~899 ms for the old shape; an eleven-position scoped read phase
took ~0.53 s. These are not HTTP/concurrency guarantees. Effective per-user
permission resolution and current per-batch display authorization remain intact;
full-history/checkpoint and explorer-history scaling remain open.

The following October 15 audit is preserved as dated evidence, not current claims
that fixed defects still exist or that the remediation changed operating services.

<a id="backendapi-audit--15-october-2026"></a>

## Backend/API audit — 15 October 2026

### Scope, method and confidence

Reviewed the working checkout on `codex/tenant-access-transparency`, HEAD
`550399f`, with 358 pre-existing changed/untracked files. This is evidence about
that working snapshot, not certification of pushed main. This audit changes only
root review/guidance Markdown; no backend fixes, operating data writes, migrations,
provider downloads, permission changes or service restarts were performed.

Inventory and AST inspection covered 190 Python modules and 29,662 nonblank lines:

| Area | Modules | Nonblank lines | Responsibility |
| --- | ---: | ---: | --- |
| `apps/reference_api` | 64 | 13,960 | HTTP contracts, access boundary, reference and booking commands |
| `security_master_schema` | 38 | 8,012 | Schema, access foundations, retained domain services |
| `market_data` | 33 | 2,666 | Rights, selection, calendars and provider evidence |
| `valuation` | 28 | 2,747 | Calculation, monetary previews, staging and publication |
| `positions` | 10 | 751 | Ledger selection, reconstruction and corporate-action projection |
| `lifecycle` | 8 | 638 | Bond/forward closure, coupon schedules and confirmations |
| `apps/market_data_ingestor` | 9 | 888 | Acquisition orchestration, jobs and outcomes |

All modules were mapped and parsed; detailed manual tracing concentrated on shared
boundaries and high-risk paths, not every line of every method. Traces included
tenant/strategy authorization, source and calendar references, submission/approval,
booking/replay/correction, rights and policy resolution, split projection, valuation
inputs and evidence, publication authority, reassessment, cash/interest and lifecycle
posting. Migration head and selected protections/indexes were inspected. Tests,
CI configuration and maintained domain documentation were cross-checked.

Offline OpenAPI generation exposed **180 operations on 163 paths**. The route/action
inventory found no unmapped ordinary `/v1` operation outside explicit platform,
session and workspace exceptions. That is routing coverage, not proof that every
object query is scoped: BACKEND-004 illustrates the distinction.

### What is sound, and what has drifted

The reviewed paths have substantial alpha foundations: immutable booked economics,
correction/idempotency checks, action-and-strategy predicates, retained input/rights
evidence, corporate-action quantity projection, staged financial results and explicit
publication authority. The valuation runner uses a repeatable-read calculation
boundary; operational failures do not pretend a staged result exists. Cash snapshot
stocks, daily interest earnings, coupon schedules and payment confirmations are
separate concepts rather than automatically generating duplicate P&L.

Those strengths are not uniform across older paths. Structured-product nested
provenance/calendar checks have not caught up with newer scoping foundations;
the legacy NAV queue does not reuse strategy filtering. Older draft defaults still
silently discard an unknown input or accept conflicting coupon economics. Domain
code imports API-owned helpers, and large repository/composition files mix multiple
products. Legacy Soft NAV, current economic P&L and monetary-stock previews must
remain explicitly distinguished in documentation and code; they are not three
names for the same engine.

See [prioritized findings and repair order](FIX.md#backendapi-audit--15-october-2026).
New findings BACKEND-001–010 separate reproduced behaviour, static defects and a
suspected preview-concurrency risk. Previously identified weaknesses remain under
their original IDs rather than being duplicated or declared fixed by documentation.
Notably, deployed authentication remains an explicit release gate: the local
actor-header/context selector is not a verified production identity boundary.

Refactor incrementally around tested domain services: move shared economic and
authority contracts below HTTP, keep route adapters thin, split repositories by
capability, then introduce typed responses at stable seams. File size alone is not
a reason for a rewrite. Preserve old financial evidence and compatibility reads
when retiring legacy workflows; do not delete historical tables to tidy imports.

### Performance evidence and scale limits

The earlier read-only profile in this session measured the populated monetary
preview, not a fresh audit load benchmark: 11 positions took **42.63 seconds**,
including **1,796 SQL statements / 38.61 seconds SQL time**. Holdings reconstruction
was about 0.19 seconds; repeated governed mark/FX selection dominated. Resolver,
entitlement and display-check profile timings overlap and must not be added.
The probe used an explicit read-only transaction and rollback. This audit did not
repeat operating DB access.

MEASURES-005 now distinguishes that measured input-resolution bottleneck from
still-unbenchmarked full-history/multi-user scaling. Inspect query plans and
date-window breadth, batch repeated selection and reuse request-scoped decisions
before considering wider caches. Existing accepted-observation/catalogue indexes
were found; no EXPLAIN was run, so a missing-index root cause is not established.
Never improve speed by removing rights, evidence or quantity-basis checks. Wider
caches need tenant, actor/action, policy, date and evidence/revocation semantics.

### Verification performed

Installed runtime metadata: FastAPI 0.141.1, Starlette 1.7.0, SQLAlchemy 2.1.1,
Pydantic 2.13.5, psycopg 3.3.6, pytest 8.4.2 and httpx 0.28.1. Read-only migration
graph inspection reported `20261015_94` as the single head; this is not a statement
that every environment has applied it.

**76 offline checks passed (2.95 seconds):**

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/test_structured_product_draft.py tests/test_reference_api_problem_details.py tests/test_market_data_rights.py tests/test_calendar_composition.py tests/test_fx_forward_measures.py tests/test_future_measures.py -q -p no:cacheprovider
```

**58 disposable-PostgreSQL checks passed (124.08 seconds); cleanup completed:**

```powershell
./.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_strategy_scopes_api.py tests/test_api_resource_bounds.py tests/test_market_data_display_rights.py tests/test_bond_coupons_api.py tests/test_fx_forward_measure_inputs.py tests/test_trade_corrections.py -q -p no:cacheprovider
```

There were 11 warnings, including Starlette TestClient/httpx deprecation,
SQLAlchemy 2.1 `Result.tuples()` deprecation and Pydantic alias-attribute warnings.
These are compatibility maintenance work, not failed financial assertions.

Additional synthetic draft probes reproduced discarded unknown input, a missing
coupon becoming zero, and a 1.25 headline coupon coexisting with 6.5 schedule rows
(FIX-SP-001/002). Existing passing tests do not cover those adverse assertions.
An offline ASGI probe injected two 150-ms blocking connection waits into the real
authorization middleware: concurrent requests took 0.352 seconds, both returning
403, without connecting to a DB. This confirms blocking middleware execution;
it is not a production throughput benchmark or evidence of a successful attack.

No full regression suite, concurrent financial-write stress test, every historical
migration/downgrade, exhaustive penetration/SAST audit, provider availability test,
production identity/deployment review, licensing legal review or independent
custodian/model reconciliation was performed. No finding is marked resolved by
these documentation edits. Deferred derivative MTM, accounting and risk weights
remain product boundaries, not newly discovered implementation bugs.

### Primary-source best-practice check

Sources searched and opened on 2026-10-15; recommendations are applied to the
observed code rather than treated as universal mandates:

- [OWASP API1: object-level authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/): validate referenced objects and scoped collections, not just endpoint permissions. Applies to nested fixings, calendars and legacy queue rows.
- [OWASP API2: authentication](https://api-security.owasp.org/editions/2023/en/0xa2-broken-authentication/): verified identity is a separate boundary from authorization. Local header impersonation is not suitable for untrusted deployment.
- [OWASP API4: resource consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/): bound request work and selectors without silently hiding eligible records or reintroducing a trade-count correctness cap.
- [FastAPI async guidance](https://fastapi.tiangolo.com/async/): normal synchronous routes are offloaded, but blocking calls inside async middleware are not automatically made nonblocking.
- [SQLAlchemy profiling guidance](https://docs.sqlalchemy.org/en/20/faq/performance.html): distinguish database execution, result processing and repeated application work before optimizing. This is shared Core guidance from the 2.0 documentation; attempts to open the 2.1 page timed out, so it is not a 2.1-specific compatibility certification.
- [Pydantic model guidance](https://pydantic.dev/docs/validation/latest/concepts/models/): extra fields default to being ignored; financial command contracts should deliberately choose rejection/forward-compatibility behaviour, not silently lose economic intent.
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html): READ COMMITTED snapshots change per statement; pinning information time alone does not pin a multi-query financial snapshot. The preview concern remains suspected until a controlled concurrency test establishes its actual effect.
- [PostgreSQL statement timeout](https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-STATEMENT-TIMEOUT): individual statement limits do not impose a total request budget over thousands of successful statements. Retain transaction/locking and truthful retry semantics when adding limits.

<a id="frontend-audit-2026-10-15"></a>

## Frontend audit — 15 October 2026

**Current status — October 16:** The ten frontend findings below now have
[implemented resolutions and verification](docs/delivery/quality-reviews/2026-10-16-frontend-remediation.md).
The dated audit and first strategy-only repair remain historical evidence, not the
current open backlog. Shared document-bound writes, exact retry/error/display
protocols, truthful registers, correction focus and bounded read reuse are in place.
Final frontend verification: 911 tests / 195 files; ten isolated Edge browser cases;
TypeScript and isolated production build passed. Browser CI is configured but its
Linux execution has not been observed. Broader visual/assistive acceptance and the
backend/API findings remain separate; this does not certify the whole project.

### Scope and architecture

Reviewed `apps/ops-console`, its Next BFF and handwritten interfaces in
`packages/api-contracts`, in the same working checkout as the backend audit above.
The 358 pre-existing changed/untracked files were preserved. Only the three root
review/guidance Markdown files were edited; no source fixes, dependency installs,
operating data access/writes, browser actions, restarts or migrations were performed.
Vitest required normal temporary config/cache writes outside the restricted cwd;
no application configuration was changed to enable verification.

Inventory: **296 Operations Console source/style files and 187 source test files**,
including **49 page entry points and 72 BFF route handlers**. Adding handwritten
shared contract source/tests gives **299 source/style files (16,318 physical lines)
and 190 test files (6,742 physical lines)**. Generated contracts, dependencies,
build output and caches are excluded from those counts; their interfaces/version
metadata were inspected. The console test run also includes its root config test.

This is a whole-tree inventory and detailed shared-boundary/representative-journey
review, not a claim that every JSX line and CSS rule was manually read. Traces:

| Journey | Main code traced | Reviewed concerns |
| --- | --- | --- |
| Context, tenant/admin access | session helpers, access proxy/loader, selector, profile, groups, platform tenants, strategy matrix | cookie context, expected identity, revision/impact review, stale state |
| Reference creation/review | creation hub, equity/listing/ETP, structured draft/schedules/payload, swap/future/product interfaces, catalogue | intent/defaults, calendar generation, duplicate/replay, source evidence, errors |
| Booking and corrections | cash/forward/option/product tickets and models, shared parties/properties/review, BFF write guards, history/detail | decimal strings, recognition/settlement, readiness, frozen retries, navigation and correction lineage |
| Market data | explorer/history/chart, coverage/resolution, providers/priorities, policies and calendars | date/basis identity, rights presentation, version selection, pending/error/empty states |
| Strategies/measures | register, detail route, positions/movements/chart, calendars and monetary report | exact quantities, grouping/paging, scope, unavailable versus zero, repeated selection |
| Valuation/operations | tab console, input/cash registers, run report, results/evidence, publication/review/reassessment, bond/forward closure and coupons | server filtering, staged versus published, current permissions, side effects and error recovery |
| Infrastructure | root providers/styles/errors, workspace shell/navigation, API contracts, package/config/CI/tests | server/client separation, version applicability, interface drift and assurance limits |

Server Components resolve active workspace and call the private Python API. Client
islands send same-origin BFF requests; they do not access PostgreSQL. Generated
OpenAPI types/openapi-fetch coexist with handwritten view types, casts and clients.
`server-only` guards, no-store reads and same-origin checks on local access commands
are useful boundaries. The local opaque session is forwarded only to the configured
API origin. Production authentication is still BACKEND-001, not supplied by a
signed tenant cookie or by hiding unauthorized buttons.

Booking tickets retain decimal input strings and reviewed immutable payload/key
envelopes. Readiness is rechecked on selection and authoritative server booking;
correction/cancellation is distinct from economic maturity/payment. Valuation tabs
remain mounted to retain native form values and uncertain requests. Results/history
use server-side filters/counts; readable strategies are not restricted to calculators.
Publication retains independent-operator/self-review checks on the server. Monetary
preview clearly distinguishes unavailable values from zero and derivatives from
NAV assets. These are strengths to preserve, not reasons to bypass backend checks.

The gaps are concentrated where older forms/helpers have not adopted those newer
contracts. [FRONTEND-001–010](FIX.md#frontend-audit-2026-10-15) give triggers, confidence,
repair direction and regression cases. Existing FIX-SP-001/002/003 still cover
structured numeric defaulting, conflicting terms and weekday-only schedule payment
lags. Cash ticket T+2 weekdays is explicitly labelled an alpha convenience and
does not claim to be an exchange holiday settlement engine.

### Reproduced defects and design drift

Offline probes evaluated current source with injected handlers/state and no live
API/DB. They are deliberately narrower than browser end-to-end acceptance:

- **Stale context:** strategy POST accepted a request carrying expected old tenant
  while resolving a different current tenant, forwarded the new tenant and returned
  the fake upstream's 200. Expected tenant is not enforced on this route.
- **Error identity:** `ReferenceApiError.requestId='upstream-request-123'` became a
  newly generated BFF correlation ID. This breaks the intended upstream log link.
- **Committed write / failed refresh:** `useAccessData.command` returned true while
  keeping old data and recording the synthetic reload failure. Callers can announce
  success without a trustworthy current-state display.
- **Decimal display:** direct execution of `formatTradeNumber` changed valid input
  `9007199254740993.123456` into `9,007,199,254,740,994`; exact formatting preserved
  `9,007,199,254,740,993.123456`. The defect is presentation, not stored arithmetic.

Static traces additionally establish mismatched proposal key lifetimes, loading
versus empty ambiguity, a source-correction fragment targeting a hidden Input tab,
and Yahoo raw/adjusted explanatory copy that is provider-wide rather than series-
specific. Browser races/focus/assistive behaviour remain unverified.

Refactoring should start with shared identity/write-state/error contracts, then
extract bounded feature modules and reusable presentation primitives. Do not
rewrite every page or mandate replacing native HTML with MUI. The structured
creation form (1,109 lines) and handwritten server client (944 lines) are expensive
review seams; duplication and dense one-line JSX make behavioural divergence hard
to spot. Styles span MUI, shared native workspace CSS and scoped feature CSS;
consolidate tokens and eliminate proven collisions incrementally, not by assuming
every heterogeneous style is broken.

Measured server latency remains MEASURES-005. Display-currency GET submission reruns
financial selection despite both amounts already being returned; shell hydration
can repeat workspace reads, and result labels fan out by displayed subject. These
paths merit request-count/phase measurement, not a claim that rendering causes the
42-second backend profile. A 60-second preview deadline is bounded waiting, not a
performance fix. No new bundle, browser paint or network-waterfall benchmark was run.

### Frontend verification and limits

Installed versions: **Next.js 16.3.4, React 19.2.8, MUI 9.4.0, TypeScript 7.0.2,
Vitest 4.1.11**. The installed Next error-file reference was read: `retry` became
stable in 16.3.0, so its use in root error boundaries is correct, not a mistaken
rename of `reset`. This is why current local/versioned guidance matters.

Checks performed:

- First console run: **880 passed, 2 timed out, 188 files**, 30.71 seconds. Both
  failures were page-import tests hitting the existing 5-second timeout under the
  default worker count. An isolated one-worker rerun passed **25/25** tests in
  those two files (10.52 seconds), without changing assertions/timeouts.
- A complete bounded rerun, `pnpm --filter ops-console test -- --reporter=dot --maxWorkers=2`,
  passed **188/188 files and 882/882 tests**, 88.67 seconds. The initial default-
  worker timeout remains recorded; no CI worker setting was changed by this audit.
- Console typecheck: passed using the installed compiler directly with
  `node apps/ops-console/node_modules/typescript/bin/tsc --noEmit --incremental false -p apps/ops-console/tsconfig.json`.
  The restricted shell's `pnpm ... exec tsc` lookup failed before this direct check;
  no dependency reinstall or compiler downgrade was performed.
- Shared contract tests: **3 files / 3 tests passed**, 1.05 seconds, with two workers.
- `.venv/Scripts/python.exe -B scripts/export_openapi_contract.py --check`: passed.
  Generation was not rerun because that command overwrites generated files and the
  checkout already contains unrelated contract changes. Export parity is not proof
  that every handwritten cast is runtime-validated.
- Local Markdown target and whitespace checks are performed for the three review
  files. Test results do not close the reproduced findings; new adverse regressions
  belong to subsequent implementation work.

No production build was run by this audit: it can generate files and invoke route
build-time work, and typechecking is not a substitute for build success. No live
browser/screenshot, hydration, mobile, screen-reader, comprehensive accessibility,
CSP/CSRF penetration or memory/load acceptance is claimed. Existing historical
walkthroughs remain in delivery documents; source-level and hook-mocked tests do
not replace current real-browser coverage. The capability register's F49 remains
partial. No backend regression suite was rerun for frontend documentation.

### Frontend primary-source check

Searched and opened on 2026-10-15. Online Next documentation identified itself as
16.4.1; recommendations below use shared App Router principles, with installed
16.3.4 documentation checked for concrete API differences. No upgrade is prescribed.

- [Next authentication](https://nextjs.org/docs/app/guides/authentication) and
  [data security](https://nextjs.org/docs/app/guides/data-security): enforce identity
  and authority at data/mutation boundaries; UI visibility is supplementary.
  Expected-context checks prevent stale intent, not authentication by themselves.
- [React Effect fetching](https://react.dev/reference/react/useEffect) and
  [state identity](https://react.dev/learn/preserving-and-resetting-state): reject
  obsolete responses and deliberately reset/reconcile state when context changes.
  Several current tickets already use generation guards; apply the same contract
  to older supporting workflows without assuming cancellation undoes writes.
- [Next fetching guidance](https://nextjs.org/docs/app/getting-started/fetching-data):
  measure waterfalls, parallelize independent work and share appropriate reads.
  Do not cache tenant financial data without complete authorization/evidence keys.
- [Next error boundary reference](https://nextjs.org/docs/app/api-reference/file-conventions/error):
  retain supported recovery callbacks and safe error references. Generic internal
  errors must not expose secrets; correlation must still connect to upstream logs.
- [WAI tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/): selected state,
  keyboard focus and visible panel must agree; a hash into a hidden panel is not
  complete cross-tab navigation. Valuation/access tabs already implement much of
  the pattern, which still needs real-browser acceptance.
- [WCAG status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
  and [error identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html):
  communicate pending/success/error states without relying only on visual styling.
  These are standards-based assessment criteria, not a claim of conformance.
- [Vitest Browser Mode](https://vitest.dev/guide/browser/): real-browser rendering
  supplies DOM/platform behaviour absent from element-tree and mocked-hook tests.
  A small synthetic critical-journey suite is recommended; it is not necessary to
  replace all existing inexpensive unit/contract tests.

## Strategy-creation stale-context remediation — 16 October 2026

The first bounded FRONTEND-001 repair binds `/strategies/new` to its server-
prepared tenant/user pair. The POST BFF invokes
[`readWriteContext`](apps/ops-console/src/lib/server/write-context.ts), requiring
both expected headers and using the resolved session only for authoritative
upstream identity. Missing headers return 400; tenant/user mismatch 409; absent,
forbidden and unavailable session context remain 401/403/503 respectively.
No request is forwarded on those failures. GET behaviour is unchanged.

The creation form preserves its draft, exposes an alert and disables further
submits after a context/access rejection; a full-page reload obtains fresh
context. Reload copy does not deny that an earlier uncertain attempt may have
committed. No automatic resubmission, permission grant, financial calculation or
operating DB write is performed. The shared helper has only been integrated with
strategy creation so far: the broader audit finding remains open for other forms.

Verification: new BFF tests reproduced seven expected failures and two client-
handler checks reproduced missing binding/conflict blocking before implementation;
27 focused strategy/context checks then passed. The client checks exercise actual
handlers with controlled hook state, not DOM/browser acceptance. Root audit
documents and the strategy capability record track the limited rollout.

Final verification: TypeScript passed. The full two-worker frontend run passed
891 tests and timed out in two existing import-heavy checks:
`trade-history-page.test.tsx` (correction lineage) and `valuation/page.test.tsx`
(bounded workflow). They are the same timeout cases recorded in the prior audit.
A one-worker rerun of those two files plus the new strategy tests passed all
37 tests in 11.45 seconds, without changing timeout settings or assertions.
The full run itself was not green; no backend regression, operating write,
production build or browser end-to-end claim is made. Scoped whitespace and
local documentation-link checks passed. No commit/push/restart was performed.

## Earlier scope and evidence boundary

October 15 [position report UI](docs/delivery/position-values-report-ui-20261015.md)
reuses `view=measures` as **Position values & exposure**. Presentation is split into
`position-measures-report.tsx` and `strategy-measure-details.tsx`, with the existing
import surface retained. Currency display modes never change authoritative strategy
currency or recompute amounts. Additive backend reason codes separate deferred
support, missing input, missing FX and invalid contract; financial methods and scoped
use/display checks are unchanged. Current verification/activation is in the delivery.
Populated-data follow-up uses decimal-string/BigInt formatting for two-decimal scan
amounts (tiny non-zero values are explicit), with exact values retained in Inspect.
The disclosure is a small client wrapper around server-rendered financial content;
it opens a full-width evidence row, not an expanding table cell. No amounts/hashes
are persisted or altered by the display convention.

October 15 [cross-product three-measure review](docs/delivery/quality-reviews/2026-10-15-position-measures-review.md)
traces every currently implemented preview branch through API, holdings, governed
marks/FX and UI. The new [forward adapter](valuation/forward_measures.py) reuses
frozen booking validation and returns signed base notional plus two undiscounted
contractual currency legs, independently translated into strategy currency. It does
not provide discounted MTM, delta, cash balances or new P&L. Base-flat mixed-rate
exceptions survive filtering; ordinary maturity closure removes both obligations.
The review retains deliberate derivative coverage gaps and full-history/per-bucket
query scaling limits (MEASURES-005), distinct from fixed safety defects. This is an
author's self-review, not independent model validation. Verification/activation
boundaries are recorded in the linked report; earlier dated evidence below stands.

October 15 monetary-measures review traces the strategy `/measures` endpoint,
quantity-only holdings adapter, governed selection/FX adapter and Measures tab.
This is a read-only monetary-stock preview, not P&L, weights or persisted NAV.
Isolated checks reproduced and then fixed missing post-split price/unit safety
and fund-share-class recognition (resolved MEASURES-001/002 in FIX). Preview
canonical NAV identity uses frozen BOOKED IDs, including listed share classes.
The authorized mock setup adds two retained synthetic index histories under
existing owned rights and a separately named, strategy-specific policy. Live API
acceptance on 2026-10-08 returns native and GBP amounts for all 11 positions,
including both SPX/UKX swaps. Existing policy versions and third-party grants are
unchanged; USD/GBP historical valuation coverage starts October 8, not October 7.
111 affected backend checks and 15 UI checks passed; TypeScript and contract
freshness passed. No full suite or independent custodian acceptance is claimed.
[Delivery and checks](docs/delivery/position-monetary-measures-20261015.md#remediation-and-local-acceptance)
retain the original findings and the separate remediation/activation evidence.

October 15 [mock valuation-cycle acceptance](docs/delivery/mock-valuation-cycle-20261015.md)
adds a connected HTTP/database scenario and supporting coupon/maturity/review/FX/
cash checks. It does not add production behavior. An intermittent maturity-rebook
409 remains open as FIX-VAL-004 despite later successful runs; browser and external
financial acceptance remain distinct.

The October 14 follow-up inventories `valuation/` and traces current calculation,
position bridge/staging, product guards, FX, accrual/flow inputs, maturity and
reassessment/publication boundaries, with focused test assertions and the existing
applied-rule UI consumer. It does not re-audit every source folder, migration,
frontend page or unrelated structured-product finding.

## Supported valuation methodology — 14 October 2026

October 15 [futures monetary exposure](docs/delivery/future-position-measures-20261015.md)
adds a preview-only FUTURE branch. Linear cash-settled INDEX_POINTS contracts
use current exact-expiry RAW close/settlement price × canonical contracts × frozen
monetary multiplier ÷ divisor for both reference notional and exposure, with
separately governed strategy FX. Contract MTM remains unavailable without clearing
evidence; no P&L, margin/cash or physical/crypto booking is enabled. Future price
streams must identify the dated contract, quote basis and divisor; expiry does
not silently remove holdings. This supplements, not expands, the P&L method below.

October 15 scoped coupon extension: [delivery](docs/delivery/bond-coupons-20261015.md)
traces `lifecycle/coupon_*`, coupon API/BFF and lifecycle UI. Tenant-owned sourced
schedules and immutable actual-payment revisions are deliberately outside the
valuation writer: no new income, automatic accrued reset, trade or cash change.
Existing daily interest remains position-level. Migration 94 passed in disposable
tests; operating migration 94/API are active with approval, browser acceptance pending. This is a
coupon-focused extension, not a fresh repository-wide audit.

Later [typed daily-interest update](docs/delivery/typed-daily-interest-20261014.md)
adds explicit NUMERIC earnings/currency to `nav.daily_accrual_input`; mandatory
date/bond/tenant/strategy scope and immutable revision history remain. JSONB keeps
supplementary details. Minimal inputs need no balances, nominal or pricing context;
valuation resolves FX from its own frozen context. Such results disclose unassessed
accrued-stock/receivable FX rather than infer zero. Detailed balance inputs still
reconcile. Migration 93 preserves existing source hashes/payloads; activation status
and focused checks are retained in the delivery record.

The [methodology matrix](docs/architecture/market-data-and-valuation/valuation-methodology.md)
is the starting point for economic conventions and edge cases. Current
`economic-position-pnl-v3` reconstructs immutable ledger facts, reviewed basic
share ratios and valid historical record corrections. Only nonzero boundaries
need marks. Actual signed execution value bridges opening/closing values; a
closure retains its T P&L. Foreign multi-day calculations aggregate daily bridges.
FX translates trade-price currency into reporting currency independently of fund
NAV date. Supported holdings are equity/ETF, native fund NAV, clean bonds and
deliverable forward outright-rate differences; this is not discounted model MTM.

Daily assessed bond interest adds earnings, not the accumulated stock. Bought/sold
accrual and coupon/balance movements reconcile separately. PAYMENT_ONLY does not
recognize income again. Cash balances are a separate exact-date stock register
with a translated preview, not cash P&L, persisted NAV or automatic countercash.

`valuation.decisions.applied_decisions` explains existing frozen inputs only.
`service.calculate_position` now supplies all line economic evidence, fixing the
missing calculation-level daily-interest rule. `position_storage.stage_line`
retains its existing full identity when deriving readable clean-bond and value-
bridge rules. Selection rules retain requested/used dates, source publication,
receipt and staleness. New results carry these rules; historical rows are not
rewritten. Existing UI renders rule explanations/evidence without repricing.

Migration 92 was previously activated with approval. Trade-ledger changes produce
separate source-health warnings and block stale staged publication; explicit
recalculation stages a successor. Published figures stay immutable. Non-ledger
impact fan-out and automatic reapplication of manual amendments are not delivered.
Independent review, real-operator lineage and controlled self-publication remain
unchanged by this follow-up.

Verification: 64 affected pure tests and 63 focused disposable-DB tests passed.
The first integration run exposed a stale legacy-publication fixture (62 pass/1
fail); it now asserts unverified new publication denial and explicitly represents
an already-published historical row before verifying real supersession. No safety
guard was weakened. No full suite or independent financial/provider reconciliation
was performed. [Delivery evidence](docs/delivery/valuation-methodology-assurance-20261014.md)
records the scope, sources and activation boundary.

The repository inventory and maintained architecture references were reviewed,
with detailed tracing of structured-product creation, frontend schedule/payload
generation, Python validation, proposal submission/approval, retries, source
payload schema and governed calendar interfaces. This is not an exhaustive audit
of trading, valuation, every migration or every frontend page.

Original reviewed code baseline: `550399f` plus existing desired-feature documentation
changes. Subsequent access implementation in the same checkout is described below;
termsheet ingestion remains unimplemented. The current
feature status remains in the [register](docs/product/feature-register.md).
Open findings are in [FIX.md](FIX.md).

Current access activation: revision `20261013_85`, with explicit group scopes and
separate strategy creation. The [delivery record](docs/delivery/strategy-access-scopes.md)
includes preserved 13-persona access, 110/57 focused backend checks, 42 frontend
checks and build/type/HTTP evidence. Three root documents were reconciled using
md-document; unrelated intake defects remain in FIX. Browser/production sign-off
and exhaustive repository audit are not implied.

## Architecture map

Supplemental 2026-10-13 implementation review: platform/group action authority,
strategy scopes, strategy creation, booking/correction entry points, valuation
transport/evidence, pricing/calendar context, migration 85, access UI and focused
test assertions were traced. This expands the scope below; it does not imply an
exhaustive financial/economic audit. See [current delivery](docs/delivery/strategy-access-scopes.md).

| Area | Observed responsibility | Principal reference |
| --- | --- | --- |
| `apps/reference_api` | FastAPI routes, request contracts, context, reference/proposal workflows and transactional DB boundary | [API README](apps/reference_api/README.md) |
| `apps/ops-console` | Next.js UI, server context/BFF, reference and operations screens | [Console README](apps/ops-console/README.md) |
| `security_master_schema`, `alembic` | SQLAlchemy table/domain foundations and versioned PostgreSQL migrations | [Data/schema](docs/platform/data-and-schema/README.md) |
| `market_data` | Acquisition/provider adapters, governed visibility, calendar evidence and resolution | [Ingestion boundary](docs/delivery/market-data-ingestion-boundary.md) |
| `positions`, `valuation` | Position reconstruction and bounded economic P&L/review; not universal derivative valuation or full NAV | [System overview](docs/architecture/system-overview.md) |
| `packages/api-contracts` | Generated API contract consumer package | [Contract README](packages/api-contracts/README.md) |

Dependencies include FastAPI/Pydantic, SQLAlchemy, psycopg, Alembic and httpx on
Python; the console declares Next.js, React, TypeScript, MUI and Vitest. Exact
versions are governed by the repository requirement and package/lock files.

## Structured-product creation as it exists

The [creation form](apps/ops-console/src/app/instruments/autocalls/new/form.tsx)
holds economic inputs and selected underlyings. It chooses the autocall,
composed-option, range-accrual or supertracker generator. The
[schedule draft](apps/ops-console/src/app/instruments/autocalls/new/draft.ts)
tracks generated/added/edited/deleted rows and validates editable fields.
[Payload conversion](apps/ops-console/src/app/instruments/autocalls/new/payload.ts)
builds the `AutocallDraftRequest` projection. Generation is currently in the
browser, not a shared server builder; schedule payment lag counts weekdays only.

The [BFF POST route](apps/ops-console/src/app/api/instruments/structured-products/route.ts)
requires reference tenant context and calls the Python
`POST /v1/structured-product-proposals` endpoint. The
[typed contract and domain validator](apps/reference_api/structured_product_contracts.py)
cover graph/cardinality/template invariants, action targets, range predicates and
KIP/final-redemption structure. It requires internal currency/calendar/underlying
UUIDs, positive initial fixing levels and explicit rows. It accepts decimal
numbers or strings; the browser currently emits JavaScript numbers.

Supported draft subtype literals are AUTOCALL, AUTOCALL_CONSOLATION, PHOENIX,
ATHENA, VANILLA_SPREAD_KIP, VANILLA_KIP, DIGITAL_KIP, RANGE_ACCRUAL and SUPERTRACKER.
Although BASKET/EACH_UNDERLYING are scope literals, the domain rejects their
aggregation until explicit terms are supported. Template availability does not
imply arbitrary termsheet or OTC ingestion.

[Submission](apps/reference_api/repository.py),
`submit_structured_product_proposal`, requires REFERENCE_PROPOSE, validates the
graph, checks active currency/calendar references and visible underlyings, and
stores a tenant-scoped CREATE_STRUCTURED_PRODUCT proposal as PENDING. AUTOMATED
requires sourceSystemId. Source payload, confidence and idempotency metadata are
supported; they do not authorize approval.

[Retry handling](apps/reference_api/proposal_retries.py), `find_proposal_replay`,
locks a tenant/source/key and compares normalized request and schema version;
matching retries reuse the proposal and changed requests conflict.
`decide_structured_product_proposal` requires REFERENCE_APPROVE, locks a tenant's
pending proposal, validates again and materializes a tenant-private parent and
component graph only on APPROVED. Rejection does not materialize an instrument.
This workflow creates reference instruments, not portfolio trades.

## Source and calendar interfaces

[Schema models](security_master_schema/models.py), `source_payload`, retain source
system, nullable tenant ownership, format, locator, digest and processing state.
Structured-product submission now matches sourcePayloadId against active
tenant/shared source-system and payload scope, including replay. See resolved
FIX-SP-004; the earlier missing-check description no longer applies.

[Calendar store](market_data/calendar_store.py), `visible_calendar` and
`calendar_days`, exposes tenant-visible calendar definitions and dated evidence.
Unknown/out-of-coverage dates remain UNKNOWN. The browser schedule does not yet
consume these interfaces; calendar-aware generation is proposed, not delivered.

## AI ingestion direction

[F54](docs/product/features/future-modules.md#f54-ai-assisted-termsheet-parsing-and-instrument-creation)
has been prioritized for implementation. The
[approved design](docs/superpowers/specs/2026-10-13-structured-product-termsheet-ingestion.md)
covers assisted editing and unattended submission through a shared server builder,
strict extraction/evidence contracts and readiness gates. No reviewed integrated
intake, extractor, persisted ingestion draft or unattended orchestrator exists yet.
Provider activation, real-termsheet accuracy and browser acceptance are unverified.
The user explicitly confirmed full instrument terms, including underlying
instruments, issuer, dates and amount; the
[execution plan](docs/superpowers/plans/2026-10-13-structured-product-termsheet-ingestion.md)
is proposed for review before implementation.

## Verification performed

### Subsequent access implementation and review

The [permission resolver](security_master_schema/access_control.py) grants admins
ACCESS_MANAGE only; operations require explicit groups. Migration 84 preserved
existing admin operations in ordinary editable groups. Strategy scopes add ALL or
SELECTED per group; [strategy predicate](security_master_schema/strategy_access.py)
requires action and scope from the same group, with current module and membership
bounds. Empty selected scope denies; unrelated broad read grants do not widen writes.

[API target checks](apps/reference_api/strategy_boundary.py) resolve trade and
valuation IDs to their authoritative strategy. Explicit read predicates constrain
strategy/trade/valuation lists and totals; actor/action bindings are cleaned from
pooled API connections. Domain booking/correction checks run before replay.
Trusted internal calculation reads are not truncated by a UI user's query scope.

[Group preview/matrix](security_master_schema/strategy_access_admin.py) materializes
administrative access metadata. Preview uses a rolled-back savepoint, and confirms
against group revision plus a canonical access-state fingerprint supplied by the UI.
Authorized direct API clients do not require the UI preview. Admins can still grant
themselves operational access; this is recorded as a deferred policy control in FIX.

[Creation access](security_master_schema/strategy_creation_access.py) uses separate
STRATEGY_CREATE and atomic explicit initial groups. ALL includes new tenant
strategies; selected groups only include them after assignment. Migration 85 retains
snapshot strategy context; unknown legacy context is not automatically unrestricted.

Focused scope/access/booking/correction/valuation regression run: 110 backend tests
passed on an owned disposable database. Frontend scope/preview and existing access
checks plus TypeScript passed. Full-suite, independent security audit and interactive
browser sign-off are not claimed. [Delivery](docs/delivery/strategy-access-scopes.md)
records activation/build evidence and the inspected boundaries. Original structured-
product review findings and verification below remain a separate historical scope.

### Original structured-product documentation review (historical)

On 2026-10-13 the focused offline command in [AGENTS.md](AGENTS.md) passed
**26 tests**: `tests/test_structured_product_draft.py` and
`tests/test_structured_product_api.py`. The latter asserts published routes and
importable workflow functions; it is not end-to-end DB ingestion coverage.
Two pure contract probes reproduced ignored unknown fields/default zero coupon
and accepted headline/row coupon disagreement (FIX-SP-001/002).

No database connection, operating migration/seed, live provider call, browser
walkthrough, frontend suite or complete application suite was performed in this
original documentation review. These limits are distinct from the subsequent
access implementation/verification described above.


## Reviewed Citi wrapper data load — 2026-10-14

XS3446382098 and its Class 1562 share LU3210286756 were tested and loaded after
explicit user review. Original-ancestry wrapper migration 20261014_88 and additive
schema metadata are installed. Both instruments are ACTIVE; proposal APPROVED.
General AI ingestion/provider integration remains unimplemented in this checkout.
See [Citi load](docs/delivery/citi-class-1562-seed-2026-10-14.md).


## All four reviewed autocalls loaded — 2026-10-14

The user authorized all four with documented best guesses. All four note/share
bundles are ACTIVE in the personal/demo app DB with APPROVED proposals. Original
instrument lookup also verified the earlier two Phoenix notes: all six supplied
PDF products are loaded. Three new bundles were committed and Citi Class 1562
reused; replay reused all four IDs. 40 focused disposable tests passed. HSBC/BNP
use GBP 1 initial-value defaults, BNP keeps an UNCONFIRMED internal share identity,
and Citi Class 1571 uses source trade date for catalogue validity while retaining
future legal issue dates. No new migration/provider activation/restart/trades.
See [all-four delivery](docs/delivery/all-reviewed-autocalls-loaded-2026-10-14.md). Earlier unloaded-state notes are historical.


## Seeded note booking readiness — 2026-10-14

The cash-listing ticket intentionally excludes STRUCTURED_PRODUCT instruments.
Structured OTC search found BNP but lacked approved booking conventions. All six
PDF parent notes now have approved unit/PCT_OF_PAR dirty OTC conventions and
report READY in original app readback, including BNP on 5 October. 15 focused
tests passed; replay reused six approvals and no trades were created.
See [booking readiness](docs/delivery/termsheet-note-booking-readiness-2026-10-14.md).

## Terms & Schedule — 14 October 2026

Open structured-product or swap details, then Terms & Schedule. `/v1/instruments/{instrument_id}/terms-schedule` reads approved current terms independently of booking readiness and resolves visible swap → note → share layers. See [delivery](docs/delivery/instrument-terms-schedule-2026-10-14.md). All six operating notes were read back; BNP browser inspection passed with the existing read-only demo user.
