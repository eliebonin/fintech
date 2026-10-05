# Task 5 — Generic swap booking UI

Date: 2026-10-05. Base: `ad269670bc775c5a722b89217508dbcbb821d472`.

Status: implemented, self-reviewed, focused verification passed. This report is part of the Task 5 implementation commit. No push, runtime activation, deployment, migration, full-suite run, build, or browser verification was performed in this task. The coordinator explicitly reserved full suites and browser work for Task 6.

## Delivered behavior

- The existing dedicated product ticket and `/api/trades/swaps` booking BFF remain the entry and submission paths.
- Selecting an approved generic swap initializes positive editable booked nominal from its exact contractual notional string. This happens in the successful context-selection handler, never in a render/effect that overwrites edits.
- Ordinary rerenders, review, back to edit, subsequent edits, custom properties, party selection, classifications, tags, source references, and notes retain the execution draft. Instrument changes clear the prior draft before initializing the next contractual amount. Tenant changes invalidate lookup requests and clear instrument/results, draft, frozen payload, retry state and tenant-specific data.
- Late booking responses are ignored after tenant transitions, including tenant A → B → A. This does not cancel an already transmitted server request; the existing expected-tenant header and server booking checks remain authoritative.
- Common approved product identity and convention facts are preserved. Generic economics reuse the existing `SwapTermsFacts` component: contractual nominal, leverage, total/excess treatment, optional funding, additional-charge acknowledgement/evidence, independent reset/payment frequencies, custom schedules, observation method, dates, redemption/continuation rules and source evidence.
- No funding-dependent facts are fabricated for an unfunded generic swap. Legacy swap facts retain their existing display path.
- Entry reference value continues to use exact decimal arithmetic: signed booked nominal × executed whole-swap quote ÷ divisor. The 2x, 400000 nominal, quote 2, divisor 100 case displays 8000 GBP. BUY/SELL and zero/negative quotes apply side once; leverage is not multiplied again.
- History and details consume immutable snapshot economics and source facts. They show contractual and booked notionals, snapshot instrument/identity labels and entry reference value explicitly labelled as neither a payment nor verified MTM. Earlier generic snapshots missing the additive `bookedNotional` field fall back to absolute recorded trade quantity. Legacy snapshots receive no invented generic terms.

## Interfaces and files

No endpoint or backend schema changes. The existing `ProductBookingRequest.quantity`, expected terms fingerprint, immutable idempotency request/key and expected-tenant header remain intact.

- `apps/ops-console/src/app/trades/new/product-ticket.tsx`: conditional shared generic facts, explicit booked nominal label, selection-only prefill, draft/tenant reset, stale response guard.
- `apps/ops-console/src/app/trades/new/product-ticket-model.ts`: `createProductDraft()` centralizes a fresh blank product execution draft; existing payload/arithmetic/validation logic remains unchanged.
- `apps/ops-console/src/app/trades/new/swap-ticket.test.tsx`: generic no-funding/funded facts, total/excess acknowledgement and schedules, both notionals, whole-swap arithmetic and immutable custom/source payload tests.
- `apps/ops-console/src/app/trades/new/product-ticket-state.test.tsx`: prefill, rerender/edit/review retention, new-instrument reset, tenant clearing, late response handling; existing futures retry/idempotency tests retained.
- `apps/ops-console/src/lib/trade-history.ts`: `swapContextLabels(context)` reads names from approved context/snapshot `sourceFacts`; `bookedSwapFacts(trade)` returns generic snapshot facts and positive booked nominal with older-snapshot fallback. No current master-data request is made.
- `apps/ops-console/src/lib/trade-history.test.ts`: immutable snapshot labels/notionals, actual `dayCountConvention` source key, older/legacy snapshot compatibility.
- `apps/ops-console/src/lib/trades.ts`: additive optional `productEconomics.bookedNotional?: string | null` matches the backend view while preserving older payloads. This is the existing handwritten view type, not a generated artifact.
- `apps/ops-console/src/app/trades/page.tsx`: snapshot generic name, positive booked/contractual amounts, whole-swap convention and immutable entry-value display in existing columns.
- `apps/ops-console/src/app/trades/[tradeId]/page.tsx`: snapshot booked nominal and reuse of `SwapTermsFacts`; generic no-funding details avoid legacy placeholder funding fields.
- `apps/ops-console/src/app/trades/trade-history-page.test.tsx`: actual rendered generic history and detail assertions, including deliberate disagreement between a trade display field and its immutable booked snapshot.

The existing server `getSwapTermsLabels` is used by instrument inspection and fetches current catalogues. Booking/history labels instead derive from the context's immutable `sourceFacts`, sharing the same existing facts renderer without introducing current-master-data dependence into booked details.

## RED/GREEN evidence

1. Initial RED:
   `pnpm --filter ops-console test -- src/app/trades/new/swap-ticket.test.tsx src/app/trades/new/product-ticket-state.test.tsx src/lib/trade-history.test.ts`
   Exit 1; `Test Files 3 failed (3)`; `Tests 14 failed | 25 passed (39)`.
   Expected failures: absent generic terms/nominal labels, empty prefill, stale instrument/tenant draft and missing snapshot reader. Arithmetic expectations themselves already passed, establishing the existing exact quote formula needed no change.
2. Initial GREEN, same command:
   Exit 0; `Test Files 3 passed (3)`; `Tests 39 passed (39)`.
3. Rendered history/details RED:
   `pnpm --filter ops-console test -- src/app/trades/trade-history-page.test.tsx -t 'generic'`
   Exit 1; `Test Files 1 failed (1)`; `Tests 2 failed | 14 skipped (16)`.
   Both tests failed for missing booked snapshot display. An earlier unfiltered run had one cold-import 5000 ms timeout; its test timeout was increased to the existing page-test pattern of 15000 ms and RED rerun confirmed the intended assertions.
4. Rendered GREEN with the three original focused files plus `src/app/trades/trade-history-page.test.tsx`:
   Exit 0; `Test Files 4 passed (4)`; `Tests 55 passed (55)`.
5. Self-review RED, history helper + ticket state + history page:
   Exit 1; `Test Files 3 failed (3)`; `Tests 3 failed | 34 passed (37)`.
   Caught the backend's actual `dayCountConvention` key, current name used in generic history, and an old booking response incorrectly accepted after A → B → A. All fixed and included in final GREEN.
6. Additional targeted RED checks:
   `pnpm --filter ops-console test -- src/app/trades/new/swap-ticket.test.tsx -t 'full approved generic no-funding'`
   Exit 1; `Tests 1 failed | 18 skipped (19)`; caught loss of selected product identity when generic facts replaced the common facts block. Shared terms now accompany common approved facts.
   `pnpm --filter ops-console test -- src/app/trades/trade-history-page.test.tsx -t 'shows both generic nominal'`
   Exit 1; `Tests 1 failed | 15 skipped (16)`; caught history using a trade display quantity rather than explicit immutable booked nominal. Snapshot quantity and quote labels now take precedence.

## Final verification commands and exact result summaries

```text
pnpm --filter ops-console test -- src/app/trades/new/swap-ticket.test.tsx src/app/trades/new/product-ticket-state.test.tsx src/app/trades/new/product-ticket-model.test.ts src/app/trades/new/bond-ticket.test.tsx src/app/trades/new/trade-ticket.test.tsx src/lib/trade-history.test.ts src/app/trades/trade-history-page.test.tsx

 RUN  v4.1.11 C:/Users/forte/Elie/projects/python/fintech/apps/ops-console
 Test Files  7 passed (7)
      Tests  88 passed (88)
   Start at  08:00:35
   Duration  3.71s (transform 974ms, setup 0ms, import 2.89s, tests 3.45s, environment 1ms)
Exit 0

pnpm --filter ops-console typecheck
> ops-console@0.1.0 typecheck C:\Users\forte\Elie\projects\python\fintech\apps\ops-console
> tsc --noEmit
Exit 0

pnpm contract:check
> platform-workspace@ contract:check C:\Users\forte\Elie\projects\python\fintech
> .\.venv\Scripts\python.exe scripts/export_openapi_contract.py --check
Exit 0

pnpm contract:generate:check
> api-contracts@0.1.0 generate:check C:\Users\forte\Elie\projects\python\fintech\packages\api-contracts
> pnpm generate && git diff --exit-code -- src/generated.ts
> openapi-typescript openapi/reference-data-api.v1.json -o src/generated.ts
✨ openapi-typescript 7.10.1
🚀 openapi/reference-data-api.v1.json → src/generated.ts [1.2s]
Exit 0; no generated artifact diff

git diff --check
Exit 0; no whitespace errors
```

An intermediate TypeScript run identified four TS7053/TS2339 errors while narrowing arbitrary JSON source rows. Explicit `Record<string, unknown>` narrowing with runtime field checks fixed them; both subsequent typechecks passed. Git emitted only the existing LF→CRLF working-copy notices.

## Self-review and remaining verification

Re-read the Task 5 brief and approved booking spec; checked conditional funding, source evidence, nominal separation, side/quote arithmetic, selection timing, stale tenant/instrument state, retry immutability and snapshot compatibility. No review agents/helpers were spawned. No party/property/navigation subsystem or second BFF was added.

Targeted tests use the repository's existing state-hook harness and real ticket event handlers plus server-rendered facts/history/details. They do not constitute browser evidence. Full frontend/Python suites, build and browser/integration verification belong to Task 6 as directed; no running-app activation claim is made. Lifecycle/schedules, cash generation/settlement, valuation/exposure and contractual-capacity enforcement remain outside scope.
