# Frontend audit remediation — 16 October 2026

**Status:** Implemented; verification recorded below  
**Scope:** Operations Console / BFF, FRONTEND-001–010  
**Checkout:** `codex/tenant-access-transparency`, with substantial pre-existing work

This is the resolution record for the [frontend findings](../../../FIX.md#frontend-audit-2026-10-15), not a new whole-project certification. Work was sequential in the existing checkout, as requested. No operating trades, source rights, permissions, database migrations or valuations were changed. The user explicitly approved the shared transport rollout. No commit/push was requested.

## What changed

| Finding | Resolution | Implementation / executable evidence |
| --- | --- | --- |
| FRONTEND-001 | Same-origin BFF mutations must echo the document's context-cookie fingerprint. A stale document is rejected before forwarding, even if the new session would otherwise authorize the write. Session selection/reset remains exempt. Endpoint authorization and existing expected-tenant/user checks remain. | [Next Proxy](../../../apps/ops-console/src/proxy.ts), [fingerprint](../../../apps/ops-console/src/lib/server/context-fingerprint.ts), [browser transport](../../../apps/ops-console/src/lib/browser-fetch.ts), [actual Next browser case](../../../apps/ops-console/browser-tests/context-guard.spec.ts), [proxy unit cases](../../../apps/ops-console/src/proxy.test.ts) |
| FRONTEND-002 | BFF error JSON and `X-Request-Id` retain upstream request identity; incoming correlation stays distinct. Unknown errors still use safe messages. | [Error boundary](../../../apps/ops-console/src/lib/bff-error.ts), [regression](../../../apps/ops-console/src/lib/bff-error.test.ts) |
| FRONTEND-003 | A committed access command followed by failed refresh reports saved-but-stale, returns failure to the editor and disables stale editing. Recovery is a GET, not command replay. Known validation errors retain their explanations. User editors remount from refreshed role/status/group membership. | [Access loader](../../../apps/ops-console/src/components/access-loader.ts), [tenant editor](../../../apps/ops-console/src/components/tenant-access-console.tsx), [loader regression](../../../apps/ops-console/src/components/access-loader.test.ts), browser recovery case |
| FRONTEND-004 | Listing, ETP, structured-product and cash requests retain exact JSON intent/key through uncertainty. Edited intent is blocked; confirmed success permits a new key. Malformed proposal success is not confirmation. The older proposal-key adapter also blocks edits until confirmation/definite rejection. Explicit original-request recovery is available on the older forms/cash register. | [Retained mutation](../../../apps/ops-console/src/lib/retained-mutation.ts), [proposal adapter](../../../apps/ops-console/src/lib/proposal-retry.ts), [navigation warning](../../../apps/ops-console/src/lib/use-retained-navigation.ts), [retry tests](../../../apps/ops-console/src/lib/retained-mutation.test.ts), [proposal tests](../../../apps/ops-console/src/lib/proposal-retry.test.ts) |
| FRONTEND-005 | Cash trade and fee formatting uses decimal strings rather than `Number`/four-decimal rounding. Large, tiny and negative amounts retain their digits. Monetary preview scan rounding remains explicit, with exact inspection. | [Formatter](../../../apps/ops-console/src/lib/trades.ts), [large/tiny/negative tests](../../../apps/ops-console/src/lib/financial-display.test.ts) |
| FRONTEND-006 | Cash and coupon registers distinguish pending/unavailable from successfully loaded empty. Read keys prevent a previous selection being reported as current. Dependent write controls require loaded configuration; failed refresh has explicit recovery. | [Cash register](../../../apps/ops-console/src/features/valuation/cash-register.tsx), [coupon console](../../../apps/ops-console/src/components/bond-coupon-console.tsx), deferred/error/empty browser cases |
| FRONTEND-007 | Source correction selects Input, preserves the recorded strategy/policy/currency, opens the disclosure and focuses the register. An unresolved calculation must be reconciled before its context changes. Yahoo descriptions follow stored observation basis; reconstructed RAW is not described as split-adjusted or an official tape. Cash snapshot preview is distinguished from trading P&L scope. | [Navigation](../../../apps/ops-console/src/lib/valuation-navigation.ts), [review](../../../apps/ops-console/src/features/valuation/review-workspace.tsx), [basis explanation](../../../apps/ops-console/src/lib/series-basis-description.ts), focused tests and mobile keyboard browser case |
| FRONTEND-008 | Added an executable real-browser layer and CI command alongside the cheap tests, with synthetic data only. Fixed two cold-import timeout cases by importing pages during module collection rather than inside a five-second test body; no blanket timeout increase. | [Browser suite](../../../apps/ops-console/browser-tests/critical.spec.ts), [configuration](../../../apps/ops-console/playwright.config.ts), [CI](../../../.github/workflows/quality.yml) |
| FRONTEND-009 | Consolidated browser transport and access error parsing; removed duplicate browser catalogue implementations from the server client through compatibility re-exports. Shared retained-intent/recovery/navigation and currency-display components replace divergent implementations on the affected paths. | [Browser client](../../../apps/ops-console/src/lib/browser-api-client.ts), [compatibility exports](../../../apps/ops-console/src/lib/reference-api-client.ts), [recovery presentation](../../../apps/ops-console/src/components/uncertain-request.tsx), [currency display](../../../apps/ops-console/src/components/measure-currency-display.tsx) |
| FRONTEND-010 | Currency display is local React state over already selected amounts. Server-rendered shells receive their known permission/user/actor snapshot. One bounded browser label request serves up to 20 visible subjects; the BFF reuses one workspace/client and restricts returned labels to exact requested IDs. | [Measures report](../../../apps/ops-console/src/components/position-measures-report.tsx), [labels BFF](../../../apps/ops-console/src/app/api/market-data/references/route.ts), [label bounds/access tests](../../../apps/ops-console/src/app/api/market-data/references/route.test.ts), browser request-count cases |

## Write context and recovery contract

- The root layout hashes opaque HTTP-only session/legacy-tenant cookie values. Only the non-credential fingerprint reaches the page. It does not grant authority or replace authentication, CSRF/XSS controls, membership or scoped action checks.
- Client writes use `browserFetch`, including the shared browser clients. Reads and external requests do not acquire this header. Mutations without a current matching stamp fail closed; the only explicit exemptions are `/api/session/context` and `/api/session/active-tenant`.
- Context selection uses full navigation so the new document receives a fresh fingerprint. Older documents retain their original stamp and must reload before saving. Existing drafts are not automatically submitted under a new identity.
- Retained financial payloads stay in memory, not local/session storage. Unknown-result navigation/close warnings protect accidental loss. A user who deliberately leaves or force-closes must inspect retained server history before submitting a new request; durable cross-reload command recovery is not claimed. No automatic write replay was introduced.
- Known validation rejection is distinct from timeout/throttling/conflict/server uncertainty. Cash writes report confirmation before the separate refresh; failed refresh never advises resubmitting a committed upload.

## Browser acceptance scope

Ten isolated headless-Edge cases cover:

1. Actual Next Proxy: an HTTP-only synthetic actor-cookie switch rejects the older tab.
2. Display currency changes issue zero additional financial/data requests.
3. Twenty displayed subjects use one bounded browser label lookup.
4. Delayed/failed cash reads do not imply empty or zero balances.
5. Pending coupon confirmations become loaded-empty only after successful read.
6. Saved access command plus failed refresh locks editing; a GET recovers it.
7. Native form validation, uncertain exact payload/key retry and page-context header.
8. Cancelled browser close preserves an uncertain request and its retry state.
9. Keyboard/mobile cross-tab input activation, disclosure visibility and DOM focus.
10. The actual valuation component selects a versioned policy, stages, inspects a staged-not-published result and explicitly confirms publication. Native required review text prevents an empty publication request.

The small ticket/access/navigation fixtures exercise shared production protocols; they are not claims that every product booking form received a full financial end-to-end walkthrough. The valuation, cash/coupon and result components are rendered directly. The context case additionally runs the real Next root layout and Proxy on an unknown route with no API handler. Both test servers point away from operating APIs; browser financial responses are synthetic interceptions.

## Verification

- Focused assertions were observed failing before their fixes for context mismatch, upstream identity, exact decimals, access refresh, retained intent, basis descriptions, correction focus, coupon loading, currency display, labels and malformed success.
- Headless Edge: **10/10 browser cases passed**, 39.4 seconds on the final browser snapshot. CI is configured to install/run Chromium; that Linux CI run has not been observed locally.
- TypeScript: passed using the installed compiler with `--noEmit --incremental false`.
- Isolated production build: passed, including the active Next Proxy; latest compile phase 14.1 seconds. No operating cache was replaced.
- Full frontend regression: final rerun outcome is recorded in the completion ledger below. Earlier runs exposed corrected assertion fixtures, hook-only drivers and two import-timeout cases; those failures were not silently excluded.

Confirmed commands (repository root, PowerShell):

```powershell
pnpm --filter ops-console test -- --reporter=dot --maxWorkers=2
node apps/ops-console/node_modules/typescript/bin/tsc --noEmit --incremental false -p apps/ops-console/tsconfig.json
$env:PLAYWRIGHT_CHANNEL='msedge'
pnpm --filter ops-console test:browser
$env:NEXT_DIST_DIR='.next-frontend-audit-build'
pnpm --filter ops-console build
```

On a fresh CI machine, install the browser first with `pnpm --filter ops-console exec playwright install --with-deps chromium`; omit `PLAYWRIGHT_CHANNEL` there. Synthetic servers bind only loopback ports 3118/3119 and do not reuse an existing service. The actual Next case has a bounded cold-compilation allowance, distinct from five-second UI assertions.

## Deliberate remaining boundaries

- No universal WCAG, screen-reader, cross-browser, visual-density or financial-production sign-off. F49 remains PARTIAL for that broader acceptance.
- The BFF label batch still performs authorized upstream lookups (bounded concurrency four). It removes browser fan-out and repeated client setup, not all SQL work. Backend MEASURES-005 and other API audit findings remain separate/open.
- Large structured-product composition and mixed MUI/native styling remain candidates for incremental decomposition. This delivered the shared protocols implicated in the audit; it is not a blanket design-system rewrite.
- Local context impersonation is still the accepted alpha mechanism, not deployment authentication. No data licence, entitlement or financial evidence was relaxed.
- No backend/Python regression suite was needed or run for this frontend scope. No independent subagent review was used, per the user's sequential-work instruction; final review is a scoped self-review plus executable regressions.

## Completion ledger

- Final full frontend run: **911 tests in 195 files passed**, 97.42 seconds.
- The intermediate hook-only driver failures in `future-expiry-form.test.tsx` and
  `swap-creation-form.test.tsx` were corrected explicitly: they isolate the new DOM
  navigation hook, whose behavior is independently exercised in the browser. The
  swap retry assertion now requires changed intent to be blocked, not a fresh key.
- Final self-review checked Proxy exemptions, absence of raw cookie exposure,
  retained payload/key release, committed-refresh handling, read liveness, display
  precision, current-context metadata reads and production build inclusion.
- Documentation check: 885 local targets across eleven reconciled Markdown files
  resolve after URL-decoding bracketed route names; scoped whitespace check passed.
  Historical findings were retained separately rather than silently erased.
