# Swap booking execution log

2026-10-02: User approved design and native implementation. Baseline commit 768f6f4.
Using executing-plans and test-driven-development. Existing feature branch codex/enriched-trade-booking; only planning documents were dirty at start.
Ruling: retain the current checkout, per the user's earlier explicit current-checkout feature-branch preference. No new worktree or main-branch mutation.
Tasks: 1 convention/rules/migration; 2 context; 3 booking; 4 frontend/history; 5 full acceptance.
Preflight: quote is swap value per notional, not upfront. One trade; no payment generation. Existing cash-event UI is not delivered and stays outside this slice.

Task 1: RED 15 failures for missing arithmetic/convention; GREEN 36 focused rule tests. Additive migration 59 applied in isolated runner.
Tasks 2/3: RED convention approval returned 404 for unsupported SWAP. GREEN 59 swap/product/bond API tests (one pre-existing Pydantic header warning). One trade, no cash rows; stale funding and immutable snapshot verified.
Ruling: the focused loader returns swapDetails and maturity to the existing shared context assembler rather than duplicating the entire ProductBookingContextView constructor. Same public context; avoids two sources of convention/identity validation.
Frontend: RED eight missing behaviours in nine tests; GREEN 21 focused ticket tests. Typecheck exposed legacy hand-maintained economics union in lib/trades.ts.
Ruling: retain the existing typed history adapter and extend its amountKind union. ProductTradeEconomicsView is not exported in OpenAPI because the legacy trade response exposes economics as a generic dictionary; forcing export would require a circular contracts refactor outside this slice. Context facts still use the generated type. Cost: the local amountKind union remains a maintenance point.

Final frontend: 339 tests / 90 files passed with maxWorkers=2; TypeScript, OpenAPI export consistency and production build passed. Two existing tests timed out under unbounded concurrency, then passed without assertion/timeout changes under bounded workers. New BFF tests use the upstream RFC problem shape, not the browser error envelope.

Fresh read-only review identified incomplete schedule closure, retired autocall trigger eligibility and an unlocked underlying projection. RED confirmed three schedule/trigger failures, then GREEN 22 tests with one remaining lock failure; adding the underlying projection lock produced GREEN 82 swap/rules/product/bond tests. The component-owned coupon override event now changes the fingerprint. Draft/retired actions or groups do not qualify an autocall. Reviewer minor funding-schedule display expansion remains a documented UX gap; exact schedule facts are captured.

Browser acceptance: isolated database fortem_swap_browser_5fa240ec6af84b3a87e6d12a7e035ea5, API8002 / production UI3002, migration59. Approved synthetic swap63dcf8d6-4e1c-436a-b23b-55aee0e8a7b0. Tenant selection → Book trade → Swap → search → inherited readonly terms. BUY nominal1000000 quote0 survived review/back/edit and persisted as trade34d55a81-89b5-43dc-aa10-6897f4b5a519. SELL nominal1000000 quote-1.5 plus optional text property persisted as trade156c743f-48d9-4a84-b21c-d9402a149496; DB quantity-1000000, quote-1.5, history entry reference value15000GBP and saved property. Two swap rows, zero related other-subject cash rows, one BOOKED event each, no fees or settlement dates. No operating trades were created.

First broad Python run: 546 passed, 474 dependency/deprecation warnings, 890.53sec. This started before review regressions were added, so a second full run on reviewed code is required and in progress. Additional swap-only required-property and injected-persistence rollback tests were added during that run; record their separate fresh verification rather than claiming they were collected by the already-running suite.

Additional final swap run: 25 passed, 21.96sec. Required BOOLEAN false and DECIMAL zero are retained; missing required values reject booking. Injected persistence failure occurs after the trade insert and confirms transaction rollback. The first injection attempt targeted the caller module instead of the actual repository import; corrected the test boundary, without changing production code.

Generated contract regeneration is byte-for-byte stable (SHA256 comparison). The repository generate:check command compares against HEAD and therefore reports intentional generated differences before committing; it must be rerun after the feature commit. OpenAPI export check already passes.

Final reviewed-code full suite: 554 passed, 473 dependency/deprecation warnings, 860.48sec, exit0. The two late test-only cases also pass in the subsequent 25-test swap run. All Important review findings were fixed and reproduced RED→GREEN; the minor schedule-event UI expansion is explicitly deferred. No second reviewer was dispatched.

Execution adaptations: broader generic strategy/annotation/permission validation is reused rather than duplicating every invalid combination in swap-only tests; isolated swap tests target the new sign, context, visibility, schedule, locking, replay and rollback boundaries. Feature changes are committed as one cohesive delivery rather than one commit per original task. No push, PR, merge or operating activation. Temporary isolated acceptance servers and browser tab were closed after evidence was recorded; the synthetic acceptance database is retained for reproducibility.
