# Frontend findings as recorded — 15–16 October 2026

Historical evidence, retained before the October 16 shared remediation. This records the original defects and the first strategy-only patch; it is not the current open backlog. See [current resolutions](2026-10-16-frontend-remediation.md) and [current findings](../../../FIX.md).

## FRONTEND-001 — P2 — Stale forms can write into the newly selected tenant

**Evidence status:** Confirmed (offline handler reproduction and static).

**Partial remediation — 2026-10-16:** Strategy creation now supplies the server-
prepared tenant/user pair and uses `readWriteContext` to reject missing/stale
identity before any upstream write. The UI retains the draft, announces the
conflict and blocks resubmission until reopening. Missing/forbidden/unavailable
context is distinguished. Focused tests went red before implementation, then
27 strategy/context checks passed. This finding remains **open** for the other
listed write surfaces; no universal cross-tab invalidation was introduced.
TypeScript passed; full frontend verification recorded 891 passes and the two
known import-timeout cases, then a 37-test one-worker rerun passed. See the
[remediation record](../../../KNOWLEDGE.md#strategy-creation-stale-context-remediation--16-october-2026)
for exact limits. No operating-data or browser acceptance is implied.

- **Source/function:** [strategy BFF](../../../apps/ops-console/src/app/api/strategies/route.ts),
  `POST`; [creation form](../../../apps/ops-console/src/app/strategies/strategy-console.tsx);
  [ETP BFF](../../../apps/ops-console/src/app/api/instruments/etps/route.ts), calendar/source
  configuration BFFs. Contrast [booking guard](../../../apps/ops-console/src/lib/booking-write-guard.ts)
  and access-administration expected tenant/user checks.
- **Trigger:** Leave a form open in tab A, switch identity/tenant in tab B, then
  submit A. Full navigation clears B's state, not A's existing state.
- **Impact/evidence:** At audit time, strategy creation resolved cookie context
  without sending/checking expected tenant/user identity. A fake-handler probe
  with expected `old-tenant` and current `new-tenant` returned 200 and forwarded
  `new-tenant`. No DB connection or persisted cross-tenant write was attempted.
  This is unintended placement under a currently authorized identity, not an
  authorization bypass. Referenced strategy IDs protect some other commands,
  but tenant-wide creation cannot rely on that safeguard.
- **Fix direction:** Common write envelope with expected tenant and actor/context
  generation; mismatch blocks before forwarding. Invalidate stale tabs and present
  the selected user/tenant consistently. Browser notification is supplementary,
  not a substitute for server-side comparisons.
- **Regression:** Two contexts, same/different tenant and user, write versus read,
  expired session and uncertain retry; no command reaches upstream on mismatch.

## FRONTEND-002 — P2 — BFF errors discard the upstream request identifier

**Evidence status:** Confirmed (reproduced).

- **Source/function:** [ReferenceApiError](../../../apps/ops-console/src/lib/reference-api-client.ts),
  `postBookedTrade`/search error parsing; [BFF envelope](../../../apps/ops-console/src/lib/bff-error.ts),
  `bffErrorResponse`.
- **Trigger:** Upstream RFC problem includes `requestId`, converted into
  `ReferenceApiError.requestId`, without a separate correlation ID on the incoming request.
- **Impact/evidence:** Envelope reads `correlationId`, not `requestId`, and generates
  a new identifier. Offline probe with `upstream-request-123` returned a different
  ID. Users cannot reliably correlate the displayed reference with Python logs.
  Existing envelope test exercises an incoming correlation header, not this path.
- **Fix direction:** Preserve distinct upstream request and end-to-end correlation
  IDs explicitly through error adapters and headers; normalize all BFF error paths.
  Do not reflect arbitrary upstream/internal exception text to improve diagnostics.
- **Regression:** Real-shaped 422/403/500 problems, missing/malformed bodies and
  incoming correlation headers; browser and upstream identities remain traceable.

## FRONTEND-003 — P2 — Access saves can report success with stale configuration

**Evidence status:** Confirmed (offline hook-handler reproduction).

- **Source/function:** [access loader](../../../apps/ops-console/src/components/access-loader.ts),
  `reload`/`command`; [tenant access console](../../../apps/ops-console/src/components/tenant-access-console.tsx),
  `save` and `UserAccessEditor` local selected/role state.
- **Trigger:** Mutation succeeds, follow-up reload fails; or refreshed membership
  changes while an editor with the same user ID remains mounted.
- **Impact/evidence:** `reload` catches its own failure; `command` still returns true.
  The probe retained `{version:'old'}`, set a refresh error and returned success.
  The caller can close its editor/show success against stale grants. Same-key user
  editor state also initializes once, rather than reconciling subsequent server state.
- **Fix direction:** Model committed-but-refresh-failed separately from rejected
  mutation; mark displayed data stale, offer read retry, and avoid resubmitting the
  committed command. Reconcile editor revisions without discarding unsaved work.
- **Regression:** Successful write plus failed reload, retry read only, external
  membership update and partial role/group changes; no false current-state claim.

## FRONTEND-004 — P2 — Proposal and supporting-input retries are inconsistent

**Evidence status:** Confirmed (static); no duplicate operating write attempted.

- **Source/function:** [listing form](../../../apps/ops-console/src/app/instruments/listings/new/page.tsx),
  `submit`; [ETP form](../../../apps/ops-console/src/app/instruments/etps/new/page.tsx);
  [structured form](../../../apps/ops-console/src/app/instruments/autocalls/new/form.tsx),
  `submitDraft`/`reset`; [cash register](../../../apps/ops-console/src/features/valuation/cash-register.tsx),
  `upload`; [proposal replay](../../../apps/reference_api/proposal_retries.py).
- **Trigger:** Successful/uncertain proposal followed by draft edits and submission;
  uncertain supporting-input write followed by editing, resetting or leaving.
- **Impact/evidence:** Listing/ETP retain one key for the whole mounted form, even
  when payload changes; server replay correctly rejects changed intent. Structured
  Reset clears its key, including after uncertain submission. Cash upload retains
  only signature/key and allows editing after failure instead of retaining an
  immutable retry envelope. Backend uniqueness/revision/fingerprint checks limit
  damage; this is not proof of duplicate financial postings.
- **Fix direction:** Standardize editing/review/sending/uncertain/confirmed states.
  Freeze payload and key on send; retain uncertain intent until reconciled; begin
  an explicit new intent only after a known outcome. Use intent-aware keys after
  confirmed success rather than reusing the old key or blindly generating another.
- **Regression:** Lost response, malformed success body, changed payload, double
  submit, successful next proposal, refresh failure and navigation/reload recovery.

## FRONTEND-005 — P2 — Cash trade/fee displays still lose decimal precision

**Evidence status:** Confirmed (reproduced display-only defect).

- **Source/function:** [trade formatting](../../../apps/ops-console/src/lib/trades.ts),
  `formatTradeNumber`; [history](../../../apps/ops-console/src/app/trades/page.tsx) and
  [detail](../../../apps/ops-console/src/app/trades/[tradeId]/page.tsx).
- **Trigger:** Fractional equity/ETF quantities/prices or fees with more precision
  than four decimals, or sufficiently large valid decimal amounts.
- **Impact/evidence:** Cash/fee branches still convert to Number then format to at
  most four decimals. `9007199254740993.123456` displayed as
  `9,007,199,254,740,994`, while the exact formatter retained every digit. Small
  nonzero quantities/prices can look like zero. Stored/API economics are unchanged;
  this is not a calculation precision defect.
- **Fix direction:** Decimal-string display consistently across product types;
  explicit rounding/tiny-value indication and exact inspection where rounding is
  intentional. Do not round submitted quantities/prices to match the display.
- **Regression:** Large valid decimals, tiny nonzero and negative values, cash,
  options, derivative conventions and fees; history/detail/review agree.

## FRONTEND-006 — P2 — Empty register copy is displayed during pending reads

**Evidence status:** Confirmed (static).

- **Source/function:** [cash register](../../../apps/ops-console/src/features/valuation/cash-register.tsx),
  strategy/value-date effect and balance table; [coupon console](../../../apps/ops-console/src/components/bond-coupon-console.tsx),
  schedule/payment effects and table.
- **Trigger:** Select a strategy/date/bond with a slow or failed read.
- **Impact/evidence:** Arrays/schedule are cleared without a distinct loading or
  successfully-loaded flag. Cash immediately says "No balances uploaded" and
  coupons show an empty payment table before evidence arrives. Warnings correctly
  say missing balances do not mean zero, but the claimed absence is still unverified.
- **Fix direction:** Distinguish loading, denied, unavailable, loaded-empty and
  loaded-populated. Announce pending/status changes and disable dependent writes
  until their required configuration is known; preserve explicit unknown semantics.
- **Regression:** Deferred reads, rejection after a previous success, date changes
  mid-read and loaded-empty success; no unsupported absence/zero claims.

## FRONTEND-007 — P2 — Source-correction navigation and scope copy drifted

**Evidence status:** Confirmed (static).

- **Source/function:** [review workspace](../../../apps/ops-console/src/features/valuation/review-workspace.tsx),
  `#valuation-input-register`; [valuation console](../../../apps/ops-console/src/components/valuation-console.tsx),
  hidden Input panel and closed Daily input register disclosure;
  [MD history](../../../apps/ops-console/src/features/market-data/history-page.tsx).
- **Trigger:** Open a result's Correct source inputs link; inspect Yahoo reconstructed
  RAW data or read current valuation scope text.
- **Impact/evidence:** A fragment alone cannot activate the hidden Input tab and
  open its parent disclosure. Operators are sent to a hidden correction destination.
  Yahoo history blanket copy says close is split-adjusted/neither raw, even for
  reconstructed RAW series. The valuation audit's "stock cash balances are not
  enabled" note also needs to distinguish result scope from the separate cash
  snapshot workspace; this is not a claim that cash P&L has been implemented.
  These labels blur current support versus historical result scope; no stored
  evidence is changed.
- **Fix direction:** Explicit tab/disclosure navigation with focus and preserved
  context. Generate basis/scope explanations from the selected series/run contract,
  distinguishing reconstructed RAW provenance and separate cash preview from P&L.
- **Regression:** Keyboard/click cross-tab correction link reaches visible target;
  raw/adjusted Yahoo and historical/current result copy remain truthful.

## FRONTEND-008 — P2 — Interaction/accessibility assurance remains incomplete

**Evidence status:** Confirmed (static coverage boundary); no blanket WCAG failure claimed.

- **Source/function:** [Vitest config](../../../apps/ops-console/vitest.config.ts),
  [strategy test](../../../apps/ops-console/src/app/strategies/strategy-console.test.ts),
  [publication interaction test](../../../apps/ops-console/src/features/valuation/publication-action.interactions.test.tsx),
  [run report tests](../../../apps/ops-console/src/features/valuation/run-report.test.tsx),
  [CI](../../../.github/workflows/quality.yml).
- **Trigger:** Hydration, native validation, actual focus/keyboard behaviour,
  navigation interception, responsive tables/charts or browser request races.
- **Impact/evidence:** Valuable pure/HTTP/static-render tests coexist with source
  substring assertions and hook-mocked element-tree tests. Those tests cannot
  establish real React effect ordering, DOM focus, native submit behaviour or
  screen-reader announcements. Current CI does not execute a browser acceptance job.
  Earlier isolated walkthrough evidence exists; it does not cover every new flow.
- **Fix direction:** Keep cheap tests; add a small real-browser, synthetic-data
  critical-journey suite: context isolation, booking uncertain outcomes, corrections,
  policy selection, result inspection/publication and cash/coupon input recovery.
  Include keyboard/mobile/assistive checks; do not install a new stack merely for
  this report or equate automated a11y checks with complete conformance.
- **Regression:** Assert user-visible outcomes, requests and focus under real
  rendering; no financial mutations against operating data for acceptance.

## FRONTEND-009 — P3 — Duplicated clients and form/state conventions have drifted

**Evidence status:** Confirmed (static); incremental refactoring recommendation.

- **Source/function:** [API client](../../../apps/ops-console/src/lib/reference-api-client.ts),
  browser client, BFF adapters; [structured creation](../../../apps/ops-console/src/app/instruments/autocalls/new/form.tsx),
  1,109 lines; [styles](../../../apps/ops-console/src/app/native-workspace.css),
  [MUI provider](../../../apps/ops-console/src/app/providers.tsx).
- **Trigger/impact:** Adding another workflow requires choosing among handwritten
  casts, generated contracts, ad hoc error parsing, multiple request helpers and
  duplicated ticket navigation/state machinery. Dense one-line forms and parallel
  MUI/native styles increase review difficulty. Bugs 001–007 show actual divergence;
  merely using both MUI and native HTML is not itself a defect.
- **Fix direction:** Shared error/identity/write-state protocol first, then bounded
  feature modules and typed adapters. Extract reusable presentation primitives and
  style tokens without a blanket rewrite/design-system migration. Retire unused
  demo-context/client helpers only after consumer checks; retain historical docs.
- **Regression:** Contract parity and same error/retry/access behaviour across
  products; formatting and token changes retain accessible markup and exact inputs.

## FRONTEND-010 — P2 — Repeated reads amplify the shared resolver bottleneck

**Evidence status:** Confirmed (static repeated-work paths); frontend latency not newly benchmarked.

- **Source/function:** [strategy route](../../../apps/ops-console/src/app/strategies/[strategyId]/page.tsx),
  [monetary form](../../../apps/ops-console/src/components/position-measures-report.tsx),
  [workspace shell](../../../apps/ops-console/src/components/workspace-shell.tsx),
  [result labels](../../../apps/ops-console/src/features/valuation/result-workspace.tsx).
- **Trigger:** Change display currency, navigate between same-session pages or
  inspect a 20-position attribution page.
- **Impact/evidence:** Display currency is a GET navigation that reselects measures;
  incomplete shell props trigger another workspace fetch; labels use up to one
  reference request per unique displayed subject. Backend MEASURES-005 measured
  expensive governed resolution, not a client rendering bottleneck. Increasing
  the preview read deadline to 60 seconds bounds waiting but does not optimize it.
- **Fix direction:** Reuse already-authorized local/strategy amounts for display-
  only changes, pass a coherent server workspace snapshot and bulk visible labels.
  Measure end-to-end/SQL/bundle phases separately. Reuse only within correct
  tenant/actor/policy/information and current-rights boundaries; do not cache
  restricted financial data globally or conceal selection failure with fixtures.
- **Regression:** Display toggle sends no extra financial selection; batch label
  request and request counts recorded; context change/revocation invalidates reuse.
