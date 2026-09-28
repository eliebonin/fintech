# Global database, API, and frontend review — 2026-09-10

## Executive conclusion

The project has a strong, coherent prototype foundation. The core domain decisions
are sound: a shared `financial_reference_node` identity, separate economic
instruments and venue listings, semantic subtype/terms tables, one precise
market-data series catalogue with immutable observations and provenance, and
tenant-scoped operational records. The current implementation also covers a
surprisingly broad instrument universe and has useful focused tests.

It is not yet a production multi-tenant valuation platform. The material risks
are now enforcement and reproducibility, rather than a missing instrument table:

1. tenant identity, database routing, and database-level isolation are documented
   but not wired into the running API;
2. the market-data resolver has the right inputs but its historic cut, calendar,
   and correction/vintage semantics are not yet fully implemented;
3. append-only version tables have no safe current-version transition mechanism;
4. Soft NAV remains a deliberately constrained same-currency proof of concept;
5. the API/frontend contract, authentication seam, and rendered UI test coverage
   are still prototype-grade.

The recommended next slice is a control slice: authenticated tenant routing and
database isolation, followed by a calendar-aware point-in-time resolver and
immutable observation/version rules. Do not add more product breadth before that
slice is demonstrably safe and replayable.

This review is deliberately non-destructive. It updates documentation only; it
does not change the schema, API, or frontend implementation.

## Scope and method

Reviewed:

* [SQLAlchemy models](../../security_master_schema/models.py) and Alembic revisions
  through `20260910_40`;
* the API application, tenant context, database lifecycle, contracts, and
  repository in `apps/reference_api`;
* the Next.js/MUI application, BFF routes, server clients, pages, and tests in
  `apps/ops-console`;
* the architecture notebook, hardening notes, prior project-quality reviews,
  and the deferred-decision records;
* focused static searches for effective dating, timestamps, correction/vintage
  handling, authentication, pagination, fallback, and hydration risks.

An internet review was made against primary or authoritative sources. The source
links and the narrow proposition supported by each source are recorded below.
The full Python and frontend test suites were not rerun because the project
instruction explicitly defers that unless requested. No runtime data was changed.

Severity used in this document:

| Priority | Meaning |
|---|---|
| **P0** | Must be solved before exposing client data or relying on historic valuation replay. |
| **P1** | Must be solved before a production pilot or a fund-manager operational service. |
| **P2** | Important hardening or scale work that can follow the control slice. |
| **Deferred** | Deliberate scope boundary; not a defect in the current prototype. |

## Scorecard

| Area | Current assessment | Why |
|---|---|---|
| Canonical identity | **Strong prototype** | UUIDv7 nodes, instrument/listing separation, identifiers and mappings are present. |
| Economic terms | **Strong breadth, incomplete enforcement** | Bonds, futures, options, FX forwards, swaps, ETPs, crypto, indices, and structured-product terms exist; cross-type applicability is mostly service-level. |
| Market data | **Good model, P0 replay gap** | Series, observations, vintages, licences, entitlements, and resolution snapshots exist, but the resolver does not yet apply every historic-cut rule. |
| Trades/cash | **Useful event model, incomplete lifecycle** | Trade UUIDs, external references, party roles, cash snapshots, and lifecycle events exist; correction and accounting impact semantics are not complete. |
| Soft NAV | **Intentional V1 proof** | It freezes selected inputs, but only supports same-currency positions and writes a minimal result. |
| Tenancy | **Documented, not operational** | Registry and membership tables plus pure routing helpers exist; the running API still uses one configured database and trusted headers. |
| API contract/security | **Exploratory** | Manual Pydantic/TypeScript contracts, local header trust, offset pagination, and string error details are not a production boundary. |
| Frontend | **Good operations demo** | The console exercises onboarding, work queue, market data, trades, P&L, and structured products; browser-level security and regression coverage are missing. |
| Delivery hygiene | **Prototype** | A pnpm lockfile exists, but Python dependencies are range-only, CI/linting is not evident, and runtime logs are present in the workspace. |

## What is already sound

These decisions should be preserved while the controls are hardened:

* **Identity:** internal UUIDv7 identity is independent of ISIN, FIGI, ticker,
  custodian code, bank code, or provider key. `ing.external_object_mapping` is
  the correct convergence point for those external namespaces.
* **Instrument versus listing:** an economic instrument may have zero, one, or
  many listings. Venue symbol, venue FIGI, trading currency, quote factor, and
  unit multiplier belong at listing level; OTC economic marks can target the
  instrument node.
* **Reference hierarchy:** structural node type, governed economic instrument
  type, and optional business taxonomy remain separate. Product labels such as
  “Athena” or “QIS” do not replace contractual terms.
* **Terms and schedules:** subtype tables hold economics; dates that repeat are
  represented by schedules/events. The structured-product graph, barrier rules,
  coupon programmes, and explicit payout multiplicity are a reasonable basis for
  onboarding without prematurely building a pricing engine.
* **Market-data domain:** `md.market_data_series` describes one economically
  precise observable stream; `md.market_data_observation` stores observations;
  `md.market_data_vintage` and raw payload references retain provenance; a
  resolution snapshot records the selected evidence. This is preferable to a
  generic “latest price” function or separate price tables for every asset class.
* **Tenant overlays:** the central/tenant split, tenant registry, membership,
  canonical-link evidence, dataset entitlement, and private-node promotion
  concepts are all present in the model and notebook.
* **Trade identity:** keeping a Fortem UUID on `trd.trade` and storing imported
  IDs in `trd.trade_external_reference` is scalable and preserves source
  traceability. The same pattern should be used for positions and cash feeds.
* **Cash and snapshots:** `trd.cash_balance`, position snapshots, market-data
  resolution snapshots, and NAV input snapshots correctly distinguish a state or
  frozen evidence set from a trade event or a raw observation.
* **Product breadth:** adding more instrument tables is not the immediate
  bottleneck. The existing model can represent the next products once the
  identity, effective-date, and resolver controls are real.

## Actual gaps and recommended solutions

### P0-1 — Tenant authentication, routing, and isolation are not live

**Evidence.** `apps/reference_api/tenant_context.py` accepts `X-Tenant-Id` and
`X-User-Account-Id`; the module itself describes those values as a trusted local
boundary. `apps/reference_api/config.py` exposes one `DATABASE_URL`, and
`apps/reference_api/db.py` caches one engine per URL. The pure
`security_master_schema.tenant_routing` helper validates a registry row, but no
API request uses it to open a tenant overlay connection. The migrations declare no
PostgreSQL RLS policies. The API checks membership in application code, using the
server's `date.today()`.

**Risk.** A header is not an authenticated identity. A UUID is not authorization.
The documented “one central database plus one logical tenant database” topology
therefore does not yet prevent a misrouted connection or a future query from
crossing tenants. This is the most important gap before client data is exposed.

**Recommended solution.** Implement in this order:

1. Validate the Auth0/OIDC access token at the edge/BFF, resolve its subject through
   `secm.auth_identity`, and derive the internal account and allowed tenant set.
   Never accept a client-selected database name or a browser-supplied tenant as
   authoritative.
2. Resolve `ten.tenant_database_registry` through a small control-plane service,
   allow-list the cluster/secret reference, and cache a bounded pool per active
   tenant route. Keep the central canonical connection read-only from tenant
   application roles; open the overlay connection only after route validation.
3. On every overlay transaction set a server-side session variable such as
   `SET LOCAL app.tenant_id = ...`. Add RLS `USING` and `WITH CHECK` policies to
   tenant-owned tables, use a non-owner runtime role, and use `FORCE ROW LEVEL
   SECURITY` where the owner must also be constrained.
4. Keep cross-database canonical links as UUID evidence, but validate them through
   the canonical API and store the canonical version/status observed at validation.
5. Add negative integration tests: forged tenant headers, missing membership,
   cross-tenant object IDs, suspended entitlements, and a route whose schema
   version is behind the control-plane requirement.

This is defence in depth, not a choice between application checks and RLS. The
PostgreSQL documentation says that enabled RLS with no applicable policy is
default-deny, while table owners and `BYPASSRLS` roles normally bypass it; the
runtime role design therefore matters.

### P0-2 — Historic market-data selection is not fully point-in-time safe

**Evidence.** `security_master_schema/market_data_resolver.py` filters observations
by `received_at_utc <= market_data_as_of_utc`, but the correction anti-join rejects
an observation whenever any accepted correction exists, without checking whether
that correction had been received or published by the requested information cut.
The pure `market_data_vintages.is_vintage_eligible()` helper is not wired into the
query. `valuation_resolver.py` subtracts weekdays and explicitly says a production
calendar service is still to come. `md.market_data_resolution_snapshot` persists
the supplied UTC cut but not the resolved local timestamp, session date, roll rule,
calendar version, or DST resolution.

**Risk.** A correction received after a historic valuation can remove the original
value from a replay, while a vendor-restated history can be mistaken for what was
knowable on the original date. Weekend/holiday and DST behaviour can also differ by
caller. This directly affects the promised reproducibility of P&L and Soft NAV.

**Recommended solution.** Make the resolver a single server-side operation that:

* accepts tenant, valuation date, `valuation_cut_id`, valuation policy, use
  purpose, and (for replay) an explicit information-cut policy;
* resolves the named IANA timezone through `cal.market_calendar` and
  `cal.market_calendar_session`, applies DST and holiday/session rules, applies a
  governed roll rule, and returns the resolved UTC cut;
* records local date/time, UTC cut, offset, session/holiday decision, roll rule,
  calendar version, and resolver version on the resolution snapshot;
* considers an observation and its vintage eligible only when its receipt and
  provider publication facts are at or before that cut; a superseding correction
  is relevant only when the correction itself was known by that cut;
* applies the policy's series, dataset, entitlement, effective-date, staleness,
  and tie-break rules deterministically, and records the candidate set/selection
  reason or an explicit missing-data exception;
* has an idempotency/replay key so two requests for the same context either return
  the same snapshot or create an explicitly different run.

The existing tables are close enough for a narrow additive hardening migration;
the missing persisted resolver evidence is more important than creating another
price table.

### P0-3 — Immutable definition versions cannot safely become current

**Evidence.** Migration `20260901_07` creates immutable triggers on
`secm.instrument_definition_version` and `secm.listing_definition_version`, plus a
partial unique index for one approved `is_current` row. It does not provide a
stored procedure or event that retires the previous current row before inserting
the next one. The base `secm.instrument` and `secm.listing` projections remain
mutable, while only some API reads use the version rows. Many subtype term tables
also carry `is_current` without a common transition rule.

**Risk.** An amendment can either violate the current-row unique index or remain
non-current. A direct projection update can disagree with the immutable version
history. “Current” is both a mutable flag and an implied effective-date query.

**Recommended solution.** Choose and document one authority:

* preferred: immutable approved facts with `[effective_from, effective_to)` ranges;
  derive “current” in a view as the one approved row effective on the requested
  date, and use a controlled append operation to insert the next non-overlapping
  range; or
* if an operational current flag is required, expose only a transaction-safe
  versioning function that appends the new row, closes the prior range, records a
  lifecycle event, and updates a projection. No application code may update the
  version table directly.

Add overlap exclusion constraints and a one-current partial unique index to every
term table that truly versions. Keep draft rows outside the approved exclusion
constraint. Add reconciliation tests that compare projections with the selected
effective version.

### P1-1 — Soft NAV is still a constrained proof of concept

**Evidence.** `security_master_schema/soft_nav_service.py` raises
`FxConversionRequired` whenever selected data currency differs from reporting
currency, reads quote factor/unit multiplier from mutable `secm.listing` columns,
does not value cash, accruals, fees, liabilities, or approved valuation marks, and
writes `liabilities = 0`. The schema has price/FX input links, but the service does
not yet populate a complete cross-currency evidence graph. There is no production
Soft-NAV API or snapshot drill-down page.

The current display-only `portfolio_pnl()` query is a separate shortcut: it chooses
the UK/US cut from a portfolio-code suffix, uses the previous weekday rather than
the governed calendar, reads the latest observation directly, and silently returns
an identity FX rate for unsupported currency pairs. That is appropriate for a
labelled demo, but it must not become the production valuation path.

**Recommended solution.** Keep the scope explicit and add one controlled slice:

1. resolve effective listing conventions as of the valuation date;
2. resolve instrument price, FX, cash balance, accrued income, fees, and approved
   tenant marks through the same frozen resolver context;
3. require each valuation line to reference exactly one price input and, when
   needed, one FX input, both in the same `nav_input_snapshot`;
4. persist input hashes, policy/cut/calendar evidence, calculation version,
   exceptions, and reconciliation totals;
5. expose a read-only run/evidence API before adding a calculation editor.

This is the point at which the UK/US cutoff demo can become a real operational
control. It is not necessary to build a general pricing engine first.

### P1-2 — Raw observations are not database-immutable and lineage is permissive

**Evidence.** `md.market_data_vintage` has an immutability trigger, but
`md.market_data_observation` has no equivalent trigger. `market_data_vintage_id`
and `source_vintage_key` remain nullable for legacy rows, and the demo loader
backfills vintage IDs with an update. Dataset/provider consistency is represented
by separate foreign keys rather than a composite invariant. `market_data_series`
and several trade/cash lineage fields retain legacy free-text `source_system_id`
values. A series has no enforced natural key, so duplicate economically identical
series are possible.

**Recommended solution.** Keep the legacy rows readable, then:

* make new observations append-only in the database; corrections are new rows with
  `supersedes_observation_id`, never updates;
* require a source key or content hash for new ingestion and keep the current
  source payload/vintage lineage non-null after backfill;
* add a consistency check or composite foreign-key pattern for observation
  dataset/vintage/provider relationships;
* define a canonical series key (subject, observable, dimensions, cut, currency,
  and default dataset policy) and reject duplicate active definitions;
* add deterministic indexes for `(series_id, market_date, received_at_utc)` and
  correction lookup; benchmark before adding partitions.

### P1-3 — Trade corrections have an envelope, not a complete accounting lifecycle

**Evidence.** `trd.trade_lifecycle_event` is append-only and has sequence/source
identifiers, but `trd.trade.lifecycle_status` is still a directly mutable column;
there is no server-side transition matrix, effective-versus-recorded impact date,
rebook/novation link, accounting-period impact, or recalculation invalidation
record. The API currently exposes trade reads but no complete booking/correction
command surface.

**Recommended solution.** Treat the original trade and every correction as
immutable facts. Add a command service that validates the expected lifecycle state,
appends a typed event, and creates a replacement/reversal trade when economics
change. Store both `effective_at_utc` and `recorded_at_utc`, the impacted valuation
date range, source payload/message ID, and a link to affected NAV/P&L runs. Old
snapshots remain immutable; a correction marks later runs for recomputation and a
new run is produced. Add idempotent command keys and a transition table/test.

### P1-4 — API security and contract discipline are incomplete

**Evidence.** `apps/reference_api/main.py` is already a large application module,
while `repository.py` is about 4,800 lines. Pydantic contracts and TypeScript types
are maintained manually; `packages/api-contracts` is only a placeholder. Errors
are generally FastAPI `detail` strings, while the BFF has a separate envelope.
Reads use offset pagination. Proposal workflows do perform some idempotency-key
checks, but that protection is not a single durable replay contract across all
commands (notably decisions and trade corrections). There is no visible Auth0
token verification, rate limit, request-size/timeout policy, or ETag/`If-Match`
handling. The market-data list also caps observations at 1,000 per series and
reports the page size as `total`; trade-list metadata has the same page-count
limitation, so consumers cannot reliably know the full result set.

**Recommended solution.**

* publish a versioned OpenAPI 3.1 document from FastAPI and generate the TypeScript
  client/types from it; add runtime response validation at the BFF boundary;
* standardise `application/problem+json` errors with a stable type/code,
  correlation ID, field errors, and safe detail;
* replace trusted headers with OIDC/Auth0 verification and object-level/function-
  level authorization on every ID-taking endpoint;
* add a server-side idempotency table/result replay for POST commands, optimistic
  concurrency with ETag/`If-Match` where resources are amended, and cursor-based
  pagination for observations, trades, and work queues;
* enforce body/page limits, timeouts, rate limits, and bounded upstream calls;
* split routers, command services, query services, and mapping/validation modules
  gradually. Do not rewrite the domain model to achieve this.

### P1-5 — Frontend integration and regression controls are inconsistent

**Evidence.** The BFF and server-only clients are a good direction, but some
server pages call the API directly through local tenant context, while client
islands call BFF routes and local fixture fallbacks remain available in the home,
search, and work-queue flows. `new Date()` is used to initialise several client
forms. The project previously observed a Next.js hydration mismatch. Tests are
mostly pure/source-string tests; Playwright/React Testing Library/axe coverage is
not present. Market-data detail views intentionally limit observations for the MVP,
and the UI does not yet expose a full frozen Soft-NAV evidence drill-down.

**Recommended solution.** Keep server rendering for data-heavy pages, but give all
browser-visible data one authenticated BFF seam. Make fixture mode an explicit
development configuration and show its source in every view. Pass a deterministic
server date or require the user to choose a date instead of rendering different
`Date()` values on server and client. Add a small Playwright smoke suite for
authentication, tenant denial, onboarding, work-queue drill-down, market-data
history, and P&L cutoff selection; add component tests for loading/error/empty
states and an automated WCAG/axe check. Standardise cursor pagination and a detail
drawer for provider, dataset, licence, vintage, cut, and observation lineage.

### P1-6 — Effective-date and catalogue rules are not uniformly enforced

**Evidence.** The model has excellent comments and several useful checks, but
many high-value roles/statuses/types remain strings. `ing.external_object_mapping`
has a period exclusion constraint, while other definition, identifier, fee,
relationship, and scope tables do not all prevent overlapping effective periods.
Subtype tables generally rely on repository validation rather than a database check
that their parent node has the required structural/economic type. Country codes and
some source-system IDs are also duplicated as plain text.

**Recommended solution.** Do not introduce a universal rules engine now. Add only
the high-value governed catalogues and constraints:

* role/status/series/party and instrument-type catalogues for values used in
  authorization, valuation selection, or cash movement;
* effective-range exclusion plus a one-current index on tables where overlapping
  approved rows would change a result;
* narrow service/database checks for bond, option, index, ETP, crypto, and swap
  parent-type compatibility;
* canonical country/venue/source-system foreign keys on new columns, with a
  measured migration of legacy strings.

Keep field-level tenant overrides and a generic applicability/rules engine as
separate later decisions.

### P2-1 — Scale, observability, and delivery hygiene need a production baseline

**Evidence.** The observation, trade, and lifecycle tables are not partitioned and
there is no captured load/`EXPLAIN` baseline. Correlation IDs exist, but no
OpenTelemetry traces/metrics/log correlation is wired. Python dependencies use
range specifiers in `requirements.txt`; the frontend has a pnpm lockfile. No
repository CI/lint configuration is evident, and runtime `.log` files are present
at the repository root. The current workspace has no committed baseline.

**Recommended solution.** Before scale work, add a small delivery baseline: a
tracked initial commit/branch, CI for focused Python/TypeScript checks, Python
locking and lint/type checks, frontend lint/type/build checks, secret/log hygiene,
and a migration smoke database. Add OpenTelemetry trace/span IDs to API/BFF,
database, ingestion, resolver, and NAV logs with PII redaction. Measure query
plans and row counts first; introduce time/range partitioning and archival only
when observations/trades justify it.

### P2-2 — Licensing and regulatory operating boundaries are modelled but not enforced

**Evidence.** Provider, dataset, licence, assignment, entitlement, and provenance
tables exist, which is the right shape. The API does not yet enforce provider
contract clauses such as internal-only versus client redistribution, nor does it
attach a legal approval to every derived/client-facing output. UCITS/benchmark and
outsourcing responsibilities remain explicitly open in the notebook.

**Recommended solution.** Make dataset use-purpose, tenant entitlement, output
audience, and licence validity inputs to every export/valuation/read policy. Add a
legal/compliance review gate for each licensed provider and for the intended Soft
NAV/UCITS service; retain approval evidence and do not infer redistribution rights
from physical storage.

## Deliberate non-gaps and safe deferrals

The following are not reasons to redesign the current model:

* a second generic price table for bonds, equities, FX, curves, or volatility;
  `market_data_series` plus observations is the right common storage boundary;
* a duplicate `secm.index` identity table; index nodes, `index_terms`,
  `index_family`, return profiles, and methodology versions already express the
  agreed model;
* putting Athena, Phoenix, consolation, range accrual, or supertracker labels in
  the canonical hierarchy; the existing structured-product terms/condition/action
  graph is the correct place;
* a universal payoff/pricing/rules engine, volatility cube, blockchain custody
  ledger, wallet/transfer model, or full benchmark calculator;
* a full custody-grade corporate-action entitlement/election engine, premium
  cashflow engine, or adjusted-option deliverable engine;
* editing old NAV or market-data snapshots after a correction. The standard path
  is to preserve the old run and create a new run from corrected facts.

These remain explicit future scope in the notebook; they should not be pulled into
the control slice simply because the schema can accommodate them.

## Internet and standards review

The following sources were reviewed on 2026-09-10. They support implementation
principles, not a claim that the source mandates the whole platform schema.

| Source | Narrow conclusion applied here |
|---|---|
| [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | RLS can restrict `SELECT`/`INSERT`/`UPDATE`/`DELETE`; enabled tables with no applicable policy are default-deny, but owners/superusers can bypass it. Use a constrained runtime role and `FORCE` where appropriate. |
| [PostgreSQL declarative partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html) | Range/list/hash partitioning and pruning are useful for genuinely large time-series tables; measure first rather than partitioning the MVP by habit. |
| [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) | Repeatable-read/serializable transactions provide stable snapshots or enforce retryable serial execution for concurrent invariants; use them around version promotion and replay commands where needed. |
| [RFC 9457 — Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) | `application/problem+json` gives clients a standard machine-readable error shape; internal stack traces should not be exposed. |
| [RFC 9110 — HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html) | Conditional requests such as `If-Match`/ETag are the standard way to prevent lost updates on amendable resources. |
| [OpenAPI specification](https://spec.openapis.org/oas/) | A versioned contract can drive generated clients, fixtures, and contract tests; the current manual type duplication should converge on it. |
| [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) and [BOLA guidance](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) | UUIDs do not provide authorization. Every ID-taking endpoint needs object-level and function-level authorization, plus resource limits. |
| [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0-18.html) | Auth0/OIDC claims are an authentication input that must be mapped to internal accounts and tenant memberships; they are not themselves the canonical party identity. |
| [Next.js hydration error guidance](https://nextjs.org/docs/messages/react-hydration-error) | Browser-only APIs, time-dependent rendering, invalid nesting, and CSS-in-JS configuration can cause mismatches; render deterministic initial HTML and move client-only state to effects/islands. |
| [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components) | Server components are a sensible default for data fetching, with client components reserved for interaction; the authentication/BFF seam must remain consistent. |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Keyboard focus, name/role/value, errors, and accessible status messages should be tested in the operations console, not left to visual inspection. |
| [OpenTelemetry concepts](https://opentelemetry.io/docs/concepts/signals/) | Traces, metrics, and logs should share propagation context so a browser request can be followed through BFF, API, database, resolver, and NAV run. |
| [FCA COLL](https://www.handbook.fca.org.uk/handbook/COLL/6/3.pdf) and [IOSCO Principles for Financial Benchmarks](https://www.iosco.org/library/pubdocs/pdf/ioscopd409.pdf) | Valuation-source reliability, governance, and documented methodology are operating obligations to validate with counsel; they do not prescribe this relational schema. |

## Prioritised implementation plan

### Slice 0 — contract and delivery baseline

* freeze the current API surface as a versioned OpenAPI artifact;
* generate TypeScript types/client and add contract tests for the existing BFF;
* standardise problem details, correlation IDs, request limits, and fixture-mode
  flags;
* add CI/focused checks and dependency/log hygiene.

### Slice 1 — tenant control plane

* Auth0/OIDC verification and internal account/tenant derivation;
* registry-backed central/overlay routing with secret allow-listing;
* tenant session context plus RLS policies and negative isolation tests;
* canonical UUID validation across the database boundary.

### Slice 2 — replay-safe market data

* calendar/timezone/DST/holiday/roll resolver;
* correction/vintage eligibility at the information cut;
* immutable observation trigger and lineage backfill;
* persisted resolved-cut evidence and snapshot idempotency.

### Slice 3 — version and valuation controls

* one authoritative effective-version/current-view pattern;
* Soft-NAV price/FX/cash/fee/mark evidence with cross-currency conversion;
* immutable NAV run/result/reconciliation records and a read-only evidence API;
* trade lifecycle command/correction/rebook semantics linked to impacted runs.

### Slice 4 — operations console quality

* authenticated BFF-only browser data access;
* evidence drill-down for market data and Soft NAV;
* deterministic dates, cursor pagination, loading/error/empty states;
* Playwright, component, accessibility, and tenant-negative tests.

### Slice 5 — measured scale and governed extensions

* query-plan/volume baseline, then partition/archival decisions;
* OpenTelemetry and operational dashboards;
* provider licence/output-audience enforcement;
* only then add custody-grade corporate actions, richer payoff evaluation,
  volatility surfaces, or additional product families.

## Deferred decisions retained after this review

The following remain open by design and should be tracked rather than silently
implemented:

* field-level tenant override precedence and promotion evidence;
* production tenant provisioning, migration orchestration, and exact central/core
  versus overlay foreign-key strategy;
* calendar source ownership and provider-specific holiday/session licensing;
* provider correction, finality, vintage, and redistribution semantics;
* the complete trade transition matrix and accounting/P&L impact rules;
* the Soft-NAV mark/override approval model and full fee/accrual treatment;
* role/type catalogue ownership and subtype applicability rule governance;
* FpML/FIX/ISO 20022/SDMX adapter conformance scope;
* corporate-action custody entitlements/elections and adjusted derivatives;
* benchmark-administrator governance for proprietary/QIS indexes;
* custody/wallet/on-chain crypto operations;
* production partitioning, retention, disaster recovery, and RTO/RPO targets.

## Documentation change log

* Added this global review and implementation plan on 2026-09-10.
* Confirmed the existing canonical-node/instrument/listing and common-series
  decisions; no broad model replacement is recommended.
* Reclassified tenant routing, point-in-time resolution, and definition-version
  promotion as foundation blockers rather than optional polish.
* Preserved the existing Soft-NAV, product-breadth, and UI deferrals.

## Verification record

The review was based on source inspection and official-source research. No full
test suite was run in this pass, in accordance with the explicit project
instruction. A focused frontend TypeScript check (`npm --prefix
apps/ops-console run typecheck`) passed on 2026-09-10, and a documentation
structure/link-target check passed for this report, the architecture note, the
knowledge-base index, and the research register. Before implementing Slice 0,
run the focused migration/API/frontend checks and record their fresh output
alongside that slice.
