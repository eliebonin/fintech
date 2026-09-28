# Frontend and API state and quality review

**Review date:** 8 September 2026  
**Scope:** Next.js operations console, shared frontend packages, BFF route
handlers, TypeScript API clients and contracts, UI tests, Python FastAPI routes,
Pydantic response contracts, and the relationship between the UI and API.

## Executive conclusion

The frontend is a useful and increasingly capable exploratory operations
console. It demonstrates the principal workflows and makes several difficult
security-master concepts understandable: economic instruments versus listings,
provider/dataset/licence provenance, trade parties, index families, cryptoasset
currency roles, and UK/US valuation cuts.

It is not yet a stable production frontend/API boundary.

The principal issue is not visual design. The application currently uses three
different integration patterns:

1. server-rendered Next.js pages calling FastAPI directly;
2. browser components calling Next.js BFF routes; and
3. browser or server pages using local TypeScript fixtures.

Each pattern is valid in a controlled context, but their inconsistent use means
that tenant handling, errors, contract types, fallbacks and review workflows
depend on which page was implemented. This explains much of the repeated
dropdown, navigation, hydration and stale-data behaviour encountered during
the MVP work.

| Area | Assessment |
|---|---|
| Product exploration and visual communication | Good |
| Page coverage for the current demonstration | Good |
| Server-first architectural direction | Sound |
| BFF consistency | Weak |
| API contract governance | Prototype only |
| Authentication and tenant propagation | Local mock only |
| UI behavioural test coverage | Weak |
| Accessibility and responsive behaviour | Incomplete |
| Ready for internal demonstrations | Yes |
| Ready for authenticated client use | No |

The frontend contains approximately 80 TypeScript/TSX files and 4,679 lines in
`apps/ops-console/src`. The implementation is substantial enough to require a
more explicit frontend architecture rather than further page-by-page additions.

## What is already good

### Server-first direction

The selected Next.js App Router and BFF architecture fits the product. Sensitive
tenant context, provider credentials and database connectivity should remain on
the server. The current application does not connect to PostgreSQL directly.

Positive implementation choices include:

- `force-dynamic` and `cache: "no-store"` for tenant-sensitive pages and API
  calls;
- server-rendered initial data for search, market data, trades and P&L;
- a BFF seam for browser-side mutations and catalogue requests;
- local synthetic fallback restricted by environment on search and work queue;
- explicit source labels distinguishing live API results from fixtures on the
  home page;
- aborting superseded interactive search requests;
- backend Pydantic validation remaining authoritative over browser validation;
  and
- the correct MUI App Router cache provider around the application.

### Domain presentation

The UI communicates several domain decisions well:

- instrument and listing creation are separate workflows;
- a listing requires selection of an existing economic instrument;
- existing listings are shown to reduce duplicates;
- catalogues such as currencies, organisations, venues, day-count conventions,
  return profiles and index kinds are sourced from the database;
- cryptocurrency can be optionally included in a currency selector without
  hard-coding assumptions by instrument type;
- market-data views expose provider, dataset, licence, vintage, market date and
  receipt time;
- trades expose strategy, subject/listing, execution, parties, fees, external
  references and lifecycle events; and
- index families and concrete return variants are represented separately.

These are meaningful successes. The UI is already useful as a design-validation
tool for the database model.

## Current frontend/API coverage

| Capability | FastAPI | Next BFF | UI | Assessment |
|---|---:|---:|---:|---|
| Instrument search | Yes | Yes | Yes | Working MVP path |
| Instrument detail | Yes | No | Yes, live server-rendered page with explicit opt-in fixture fallback | Remediated |
| Equity proposal | Yes | Yes | Yes | Submission only |
| Equity approval/rejection | Yes | Yes (generic) | Yes | Generic review/decision shell |
| Listing proposal | Yes | Yes | Yes | Submission only |
| Bond proposal | Yes | Yes | Yes | Browser now uses same-origin BFF |
| Bond approval/rejection | Yes | Yes (generic) | Yes | Generic review/decision shell |
| Cryptoasset proposal | Yes | Yes | Yes | Most complete workflow |
| Cryptoasset review/decision | Yes | Yes | Yes | Specialized page retained; generic shell is now preferred |
| Index-family proposal | Yes | Yes | Yes | Submission plus generic review path |
| Index-family decision | Yes | Yes (generic) | Yes | Generic review/decision shell |
| Index proposal | Yes | Yes | Yes | Browser now uses same-origin BFF |
| Index approval/rejection | Yes | Yes (generic) | Yes | Generic review/decision shell |
| Mapping proposal/decision | Yes | Yes (generic) | Queue link plus generic review/decision shell | Remediated |
| Generic proposal review/decision | Yes | Yes | Yes for supported proposal types | New shared workflow |
| Market-data series/history | Yes | Yes | Yes | Useful but demo-oriented |
| Trades list/detail | Yes | Not used | Yes, server-direct | Read-only MVP |
| Portfolio P&L | Yes | Exists but not used by page | Yes, server-direct | Demonstration only |
| Soft-NAV run review | Schema/API queue evidence only | No | No | Deferred |
| Trade booking/correction | No complete write API | No | No | Deferred |
| Entitlement/tenant administration | No usable UI API | No | No | Deferred |

The cryptoasset proposal/review/decision flow is currently the best template for
future controlled workflows.

## Critical findings

### P0. Browser-to-API security boundary is inconsistent — remediated for the current workflows

The intended architecture is:

```text
browser -> Next.js BFF -> FastAPI -> database/service
```

The original review found that bond and index client components invoked the
direct FastAPI client while cryptoasset and index-family forms used the BFF.
That asymmetry has now been removed. All current browser mutation/catalogue
paths use `browser-api-client.ts` and same-origin `/api/*` routes; direct API
clients and the local tenant helper are marked `server-only`.

In a client bundle, the direct pattern can expose or hard-code tenant/account
identifiers, depend on a browser-accessible FastAPI URL, introduce CORS
requirements, and bypass the intended session-derived BFF boundary. The local
tenant helper always returns a mock local session; it is not an authentication
implementation.

Required rule:

- Server components may call the server-only FastAPI client.
- Client components may call only same-origin BFF routes.
- The tenant context helper and direct FastAPI client must be marked and
  structured as server-only modules.
- BFF handlers derive tenant and actor from an authenticated session; no client
  payload or browser-visible constant may select them.

The BFF still uses a local development tenant seam (`resolveLocalTenantContext`)
until the authenticated session/tenant registry is connected. That is an
explicit security follow-up, not a browser exposure in the current bundle.

### P0. API contracts are manually duplicated

The architecture calls for generated TypeScript contracts and a generated
client from versioned OpenAPI. The `packages/api-contracts` package currently
contains only a README and package manifest.

Actual response and request shapes are manually recreated in:

- Python Pydantic models in `apps/reference_api/contracts.py`;
- TypeScript declarations in `apps/ops-console/src/lib/reference-api-client.ts`;
- additional independent types in `market-data-series.ts`, `trades.ts` and
  `portfolio-pnl.ts`; and
- untyped `Record<string, unknown>` mutation payloads.

This permits silent API/UI drift. Type assertions after `response.json()` do not
validate runtime data.

The next contract slice should:

1. publish a versioned OpenAPI document from FastAPI;
2. generate TypeScript schemas and a typed client into `packages/api-contracts`;
3. expose one common error envelope;
4. add consumer contract tests; and
5. prohibit handwritten duplicates for generated API objects.

Runtime validation at the BFF boundary is advisable for high-risk responses.

### P1. Standalone instrument detail is not live — remediated

The original standalone route used the static `instrument-data.ts` fixture even
though FastAPI already exposed `GET /v1/instruments/{instrument_id}`. The route
now loads that endpoint server-side with `force-dynamic` and `cache: "no-store"`.

The previous fixture path could make a newly approved instrument differ from
the database, or fail to provide a dependable canonical-record drill-down.
Those consequences are removed for the live path; the explicit development
fallback is retained only for offline fixture demonstrations.

404 responses become a not-found page; authorization and service failures are
shown distinctly. A local fixture is used only when development explicitly sets
`ALLOW_FIXTURE_FALLBACK=true`; production never silently falls back.

### P1. Proposal workflows are asymmetrical — remediated for supported types

The API supports decisions for mappings, equities, bonds, cryptoassets, indices
and index families. The original UI exposed a complete review page only for
cryptoassets, leaving most queue records as inventory. The work queue now emits
one generic review path for every supported proposal type (including mappings),
and the Next app provides a shared review/decision shell.

The generic shell is now implemented as:

```text
proposal header
  + submitted facts
  + source and duplicate evidence
  + validation/enrichment exceptions
  + proposed canonical materialisation
  + approve/reject controls with reason
  + final decision evidence
```

The API dispatcher still delegates approval to the type-specific repository
validator/materialiser, so the generic page cannot bypass domain rules.

### P1. Error semantics are inconsistent and often misleading — BFF baseline remediated

The original BFF handlers used different shapes:

- `{ error: { code, message } }`;
- `{ detail: message }`; and
- generic HTTP 503 responses for any caught error.

Server-rendered pages frequently catch every failure and display “API
unavailable,” even when the real result may be 400, 401, 403 or 404. The trade
detail page similarly collapses not-found, unauthorized and service failure into
one message.

FastAPI validation errors may return a structured `detail` array, while the
TypeScript client assumes `detail` is a string.

All current BFF catalogue, proposal, market-data, search, queue and P&L routes
now use a shared `bffErrorResponse` helper. It emits one structured error
contract containing:

- stable error code;
- human-safe message;
- correlation ID;
- field errors where applicable;
- retryable flag; and
- HTTP status preserved by the BFF.

The live detail and generic review pages distinguish not-found, authorization
and service-unavailable states; browser mutation clients retain status,
correlation ID, retryability and field errors through `BffApiError`. More
fine-grained page-specific rendering (stale/validation panels) remains a later
UI slice.

### P1. Idempotency is not completed through the browser workflow — transport remediated; persistence remains backend work

Manual forms now generate one key on the first submit and send it through the
BFF as `Idempotency-Key`; retries within that draft reuse the key. The backend's
current uniqueness rule is source-scoped, so a future authenticated/session
implementation must persist the browser key in the proposal command (or add a
dedicated request-id scope) before this can be called end-to-end complete.

An intentional new draft receives a new key. The generic decision route follows
the same browser transport convention; durable replay handling is explicitly
deferred to the API command layer.

### P1. Market-data and P&L views show facts without complete resolution evidence

The market-data page is useful, but it is an observation browser rather than the
governed valuation resolver UI:

- its default window is fixed to one week in August 2026;
- labels and badges remain demonstration-specific;
- series access is checked using current entitlement dates in the API rather
  than a requested historic entitlement context;
- pagination is not exposed for long histories; and
- the chart has no selection, scale, tooltip or correction/vintage comparison.

The P&L page displays opening/closing prices and FX rates, but does not expose:

- opening market date and observation ID;
- closing market date alongside the existing ID;
- FX series and observation IDs;
- information cut resolved in UTC;
- policy/rule ID;
- staleness or fallback state; or
- the frozen NAV/P&L input snapshot.

The label showing quantity followed by `localCurrency` is also semantically
misleading for equities, ETFs and futures: that currency is the price/local
valuation currency, not a quantity currency.

The P&L UI should remain labelled as demonstration-only until it consumes frozen
resolver evidence rather than selecting observations through the display query.

### P1. Frontend tests do not protect real user behaviour

The test suite contains useful pure-function and HTTP-client tests. However,
many UI tests read source files as strings and assert that particular text is
present. For example, they verify that a component source contains a state
variable or a MUI prop rather than rendering the component and interacting with
it.

These tests can pass while:

- a dropdown remains empty;
- labels overlap input text;
- a queue row cannot be opened;
- SSR hydration fails;
- a live API contract has drifted; or
- navigation reaches a fixture-only page.

No configured browser end-to-end suite, accessibility test suite or rendered
component testing framework was found in the application package.

The next testing layer should include:

1. rendered component tests for forms, catalogues and error states;
2. BFF contract tests against the FastAPI OpenAPI contract;
3. Playwright smoke tests for the principal workflows;
4. SSR/hydration tests for the shared shell; and
5. basic automated accessibility checks.

## Additional quality findings

### Navigation state and counts

- The work-queue link still points to a hash on `/`; the shared shell now reads
  the hash after hydration so the Work queue section is shown as active without
  introducing a fake route.
- Sidebar counts are no longer hard-coded. Counts are owned by the work-queue
  response; the sidebar intentionally omits them until a live count projection
  is added.
- The work-queue fallback no longer adds a synthetic NAV review record; the
  queue page shows only records returned by the live API (or its clearly marked
  local mapping fixture).

Counts should be live or omitted. A hash link should not pretend to be a
separate route-level workspace state.

### Responsive behaviour

The shared shell includes a mobile drawer and responsive MUI breakpoints. The
global `body { min-width: 1120px; }` rule has been removed so narrow-window
behaviour is no longer masked by a document-wide overflow constraint.

For an internal desktop console, a recommended minimum viewport may be stated,
but the page should still degrade safely rather than enforcing a document-wide
minimum width.

### Accessibility

The queue rows already had keyboard handling. The original audit found that
instrument search result rows were clickable layout boxes without equivalent
button/list semantics or keyboard activation. They now expose button semantics,
keyboard activation and focus styling. Tables still lack captions and charts
have minimal accessible descriptions; reusable primitives and an automated
accessibility suite remain follow-up work.

### Date and display semantics

- Several pages use hard-coded August 2026 defaults rather than deriving the
  latest available business date or retaining a user-selected valuation
  context.
- Client-side `today()` uses UTC date, which can differ from the user's local
  business date around midnight.
- The market-data, trades and P&L pages now show `LIVE API · DEMO DATA` only
  after a successful live read, and `API UNAVAILABLE` on failure. “Live API” and
  “licensed production data” are not equivalent, so source, environment and data
  classification should remain separate labels as production entitlements are
  introduced.

### Maintainability

`reference-api-client.ts` is approximately 685 lines and repeats request,
header and error parsing logic. This is an early symptom of the missing
generated contract/client package.

The onboarding pages also repeat:

- catalogue loading state;
- currency-group toggles;
- native-select configuration;
- message handling;
- optional-string conversion; and
- proposal submission state.

These should become focused application primitives after the API boundary is
normalised. They should not be promoted into the general shared UI package
until their semantics are stable.

The workspace packages for `auth`, `api-contracts`, `ui` and `test-fixtures`
are currently placeholders. Their intended boundaries are sensible, but their
existence should not be counted as implemented capability.

## Relationship to the backend review

The frontend has correctly exposed several backend weaknesses:

- dropdown failures reveal catalogue/API startup coupling and inconsistent
  client paths;
- the P&L page reveals that display calculations are not frozen resolver runs;
- history views expose the difference between series coverage and returned
  observations;
- review screens reveal the conflict between immutable facts and mutable
  approval status; and
- standalone detail views reveal that canonical write workflows need a common
  live read model.

The UI should not compensate for these problems with additional fixture logic
or local business rules. The API must provide authoritative, view-oriented
contracts and explicit lifecycle operations.

## Deferred work assessment

### Frontend/API items that are now foundation work

1. Enforce browser-to-BFF-only access for client components.
2. Replace the local tenant helper with an authenticated server session seam.
3. Generate the TypeScript contract/client package from versioned OpenAPI.
4. Standardise the error envelope and preserve upstream statuses.
5. Make standalone instrument detail live and tenant-aware.
6. Build the generic proposal review/decision workflow.
7. Carry idempotency keys through all browser mutations.
8. Add rendered component and browser workflow tests.
9. Expose frozen valuation evidence rather than recomputing display-only P&L.
10. Remove or clearly isolate fixture-only paths from live paths.

### Work that can remain deferred

- client-side query/cache library;
- real-time streaming and intraday charts;
- a second public or client portal;
- broad shared design-system extraction;
- advanced table personalisation;
- mobile-first optimisation;
- UI administration for every reference catalogue; and
- creation forms for every modelled derivative type.

## Recommended implementation sequence after the remediation

### Milestone 1: normalise the transport boundary — completed for current routes

- Direct FastAPI clients and tenant-session helpers are server-only.
- Current browser mutations use same-origin BFF routes with a common error
  envelope and correlation ID.
- Bond and index client components no longer call FastAPI directly.
- The P&L BFF route normalises the `uk`/`us` aliases to canonical portfolio
  codes.

### Milestone 2: establish executable contracts

- Export the FastAPI OpenAPI document in a controlled build step.
- Generate TypeScript request, response and error types.
- Replace `Record<string, unknown>` request payloads.
- Add an API compatibility check to CI.

### Milestone 3: complete one Operations workflow — completed for supported proposal types

Use reference-data proposals as the vertical slice:

```text
search or create
    -> pending proposal
    -> work queue
    -> review submitted and matched evidence
    -> approve or reject with reason
    -> live canonical detail
```

It is implemented generically for equity, bond, index, index family,
cryptoasset, listing and external mapping proposals. Domain-specific panels and
durable replay handling remain follow-up work.

### Milestone 4: test the actual browser experience

Add browser tests for:

1. database-backed catalogue loading;
2. economic instrument creation;
3. proposal appearance in the queue;
4. review and approval;
5. approved record appearing in live search and detail;
6. listing creation with duplicate-warning context;
7. unauthorized and unavailable API states;
8. refresh/retry idempotency;
9. market-data date-range navigation; and
10. hydration without console errors.

### Milestone 5: connect valuation views to frozen evidence

After the backend resolver corrections, make the portfolio/NAV UI consume a
calculation run and input snapshot. Show the exact price and FX observation,
market date, named cut, resolved UTC cut, dataset/licence, policy rule,
staleness and exception decision for every line.

## Final verdict after remediation

The frontend is good enough to continue using as an internal product-design and
schema-validation tool. It has already provided valuable feedback on the
security-master and market-data model.

It should not yet be treated as a production client application. The principal
browser-boundary inconsistency is fixed for the current workflows, but
authenticated tenant propagation, generated contracts, durable command
idempotency and browser-level verification are still absent—not the choice of
Next.js, React or MUI.

The selected technology and server-first direction remain appropriate. A broad
frontend rewrite is unnecessary. The right next moves are to connect the
authenticated tenant/session seam, generate contracts from versioned OpenAPI,
complete frozen valuation evidence, and add real browser-level verification
before expanding to further instrument types.

## Remediation ledger — 8 September 2026

The audit findings above were reviewed and the following implementation changes
were made in the current workspace. The original findings remain useful as the
baseline; rows marked “remediated” describe the current state after the fixes.

### Transport and security boundary

- Added `src/lib/browser-api-client.ts` as the browser-only request seam. It
  provides same-origin BFF GET/POST helpers, structured error parsing and a
  stable `Idempotency-Key` header for browser mutations.
- Added `src/lib/api-errors.ts` and `src/lib/bff-error.ts`. BFF routes now return
  `{ error: { code, message, correlationId, retryable, fieldErrors? } }`, keep
  upstream HTTP status where available, and emit `X-Correlation-Id`. Unknown
  server exceptions are mapped to safe fallback text rather than reflected to
  the browser.
- Marked `tenant-context.ts`, `reference-api-client.ts` and
  `mvp-api-client.ts` as `server-only`. Bond, index, cryptoasset,
  index-family, listing and catalogue client paths no longer import the direct
  FastAPI client or local tenant context.
- Kept `resolveLocalTenantContext()` only as a development seam. Replacing it
  with an authenticated session/tenant registry is still required before any
  client-facing deployment.

### Live data and workflow completion

- Replaced the standalone fixture-only instrument detail route with a dynamic
  server-rendered call to `GET /v1/instruments/{id}`. 404, authorization and
  service failure are distinct; fixture fallback requires the explicit
  non-production flag `ALLOW_FIXTURE_FALLBACK=true`.
- Added tenant-scoped `GET /v1/reference-data-proposals/{id}` and
  `POST /v1/reference-data-proposals/{id}/decision` plus the corresponding
  Next BFF route and browser client wrappers.
- Added a generic `/reference-data/review/[proposalId]` page. It displays the
  proposal metadata, raw structured payload, decision evidence and reason, and
  provides approve/reject controls. The API dispatcher delegates to the
  existing equity/listing, bond, cryptoasset, index, index-family and mapping
  workflows, preserving their domain validation and materialisation rules.
- Work-queue review links now point to the generic page for all supported
  proposal types, including external-identifier mappings. The queue no longer
  fabricates a synthetic NAV review item.
- Browser drafts now reuse one idempotency key for retries. Durable replay
  semantics for manual proposals remain an API command-layer follow-up because
  the current database uniqueness constraint is source-scoped.

### UI correctness and responsive behaviour

- Work-queue hash navigation is reflected in the active sidebar state after
  hydration; hard-coded sidebar counts were removed.
- Search-result records have keyboard/button semantics and focus styling.
- Removed the global `body` minimum width that prevented safe narrow-window
  behaviour.
- Market-data, trades, trade-detail and P&L headers now distinguish live API
  reads of demo data from API-unavailable states; P&L quantity cells no longer
  imply a quantity currency and instead label the local price/FX currencies.

### Verification performed

The following focused checks passed after the changes (the complete suites were
not run, per the standing instruction):

| Check | Result |
|---|---:|
| `tests/test_reference_api_proposal_review.py` | 2 passed |
| Related crypto/onboarding, queue and mapping API tests | 8 passed |
| Ops-console focused Vitest set (8 files) | 25 passed |
| `pnpm --filter ops-console typecheck` | passed |
| `pnpm --filter ops-console build` | passed; generic review/BFF routes included |

The focused API test covers proposal read, approval, decision evidence,
tenant-scoped not-found behaviour and rejection of a second decision. The
frontend tests cover BFF error/idempotency transport, server-boundary imports,
live instrument detail request construction, navigation state and existing
catalogue/client contracts.

### Remaining explicit gaps

These were not silently treated as fixed and remain planned work:

- generated TypeScript/OpenAPI contracts and runtime response validation;
- authenticated Auth0/session-derived tenant context and tenant registry;
- durable idempotency/replay handling in the API command layer;
- historic entitlement/vintage-aware market-data resolution;
- frozen NAV/P&L input snapshot evidence in the UI;
- rendered component, Playwright and automated accessibility coverage; and
- review panels for validation/enrichment exceptions beyond the generic payload
  and evidence view.

## Verification note

This review was performed through static inspection of the frontend, BFF,
FastAPI routes, Python and TypeScript contracts, frontend specifications and
existing tests. The complete Python and frontend test suites were not rerun, in
accordance with the standing instruction not to run broad suites unless
explicitly requested. The remediation ledger records the targeted
implementation and verification performed after the original audit snapshot.
