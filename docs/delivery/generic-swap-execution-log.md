# Generic swap execution log

2026-10-05. Tasks 1–5 implemented and independently reviewed on `codex/enriched-trade-booking`, base `316718f`. Task 6 uses the current authorized checkout; no worktree, dependency additions, push, operating migration/restart or operating trade. The original verification and approval blocker below are historical evidence; the sequential completion addendum records their resolution.

## Deferred findings triage

The PostgreSQL payload CHECK accepted JSON null `schemaVersion` because SQL unknown passes CHECK. Focused storage regression: **1 failed, 1 passed, 8 existing seed deprecation warnings**, then **2 passed, 8 warnings in 19.02s** after additive revision `20261005_61` and matching schema metadata used COALESCE false. Revision 60 was not rewritten. Migration refuses downgrade and never deletes approved evidence.

The form originally counted actual fractional digits against total precision, allowing too many integer digits for fixed-scale server Decimals. Four regressions for contractual nominal, leverage, quote divisor and spread: **4 failed, 10 passed**, then **14 passed** after reserving the declared fractional scale. Backend validation was already authoritative. These were acceptance-triage fixes, not broader cleanup.

Commands: `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py tests/test_generic_swap_storage.py -q --tb=short`; `pnpm --filter ops-console test -- src/components/swap-creation-form.test.tsx`. Regression tests exercised real PostgreSQL constraints and actual form callbacks. Hook replacement tests are not real DOM/browser evidence.

## Final checks

- `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py -q`: single full acceptance run, session99676, disposable database `fortem_isolated_tests_a597d1fea9b14859b9d415417ca675ea`: **690 passed, 2 failed, 481 warnings in1689.72s (28m09)**, exit1. Failures were migration-test database ownership and demo-fixture index scope; targeted reproduction/fixes are recorded below. This was not an all-green full run and it was not repeated.
- `pnpm test:ops-console -- --maxWorkers=2`: **387 tests passed in 95 files**, 45.13s, exit 0 (session 67180).
- `pnpm typecheck:ops-console`: exit 0.
- `pnpm build:ops-console`: exit 0; Next 16.3.4 production build compiled and generated all routes.
- `pnpm contract:check`: exit 0.
- `pnpm contract:generate:check`: exit 0; generated artifact unchanged. Type/build/contracts session 36870; only existing LF/CRLF Git notices.

## Full-run failure triage

The storage integration test left its SQLAlchemy engine pool open in the dedicated migration-test database, preventing the later migration test from recreating that database. Its engine is now a yield fixture disposed in `finally`, including assertion failures. The MVP fixture test queried every index variant in its seed family; earlier generic booking tests legitimately added sourced variants there. The assertion now checks the two explicit seeded node identities and their exact expected profile assignments, without forbidding additional valid variants. Neither repair weakens production behavior or bypasses database ownership.

Focused reproduction command: `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py tests/test_generic_swap_storage.py tests/test_migrations.py tests/test_generic_swap_booking_api.py::test_governed_index_source_profile_is_independent_and_preserved tests/test_mvp_market_data_fixture.py::test_mvp_fixture_has_generic_return_profiles_and_index_variants -q --tb=short`. RED session44290: **2 failed, 3 passed, 16 warnings in66.59s**, exit1, reproducing both full-run failures together. Identical-command GREEN session17185: **5 passed, 16 warnings in81.62s**, exit0. No second full suite was started, as requested. The final changes after the full run were these two test boundaries and documentation only.

## Real browser evidence and isolation

Browser CUA in-app browser ID 2, task-created tab 1, hidden by default. New database `fortem_generic_swap_browser_20261005_6ef2829c`, migrated through revision 61 and seeded with deterministic synthetic demo state. API `127.0.0.1:8003`, production UI `127.0.0.1:3003`. Hidden task-owned startup PIDs: API wrapper 14108, actual uvicorn 35656; UI 14128. Environment points this API to the named synthetic database and this UI exclusively to port 8003; cookie secret is process-only and not recorded. Operating ports/data were untouched.

Seed HSBC's canonical instrument differs from its approved definition; submitting it correctly returned an eligibility error. Acceptance then used a separate coherent approved bond-reference clone created by the existing API-test fixture pattern, UUID `9b40f179-1403-4d16-b15e-659a205ae898`, name `SYNTHETIC Acceptance Bond Reference`. No validation was weakened and no operating seed was changed.

Unfunded pending proposal `01a10af1-1fcf-788e-920d-29aacef199ab`, name `SYNTHETIC Generic Unfunded 20261005`, identifier `SYN-UNFUNDED-6`: GBP 1,000,000 contractual nominal, RECEIVE TOTAL/Gross total return, leverage 2, effective 2026-10-01/maturity 2027-10-01, quarterly performance reset, TERMINATE reference exposure, divisor 100, explicit synthetic source.

Funded pending proposal `01a10af2-f5c4-7146-bf66-c410edafecb4`, name `SYNTHETIC Generic Funded 20261005`, identifier `SYN-FUNDED-6`: same reference/dates/currency/nominal/divisor, leverage 1, monthly performance reset, SONIA overnight rate `00000000-0000-7000-8000-000000000193`, 150 bp exactly displayed as stored rate 0.015, BOOKED_NOMINAL, ACT_365F, sourced daily compounding/no lag, monthly resets/quarterly payments, TERMINATE.

Observed actual DOM/native behavior: empty Review click focused required Display name and did not enter review; funding on→150→off→on showed empty spread; final off review and submitted payload had null funding-dependent fields. Review/back-to-edit retained nominal and dates; both requests appeared in Creation Requests. Operations displayed unfunded TOTAL/leverage2/NONE; funded review displayed SEPARATE, opposing PAY funding direction and all required conventions. CUA native-date fill initially altered DOM but not React state; ArrowUp/ArrowDown native key events committed dates, and review then showed exact dates. This helper quirk is not fabricated successful form submission.

Tenant switching selected Fortem Second Tenant/OPERATIONS; its Operations queue had zero items and exposed neither first-tenant pending swap. Returning to Fortem Demo Tenant opened a fresh blank creation draft with default leverage1. Read-only database audit confirmed revision61, zero generic definitions and the six existing seeded trades. Synthetic proposal approvals have not occurred; approved instrument details, booking search/partial nominal/whole-quote/custom fields/back-edit/confirmation/history remain unverified in the browser.

Automatic approval review rejected clicking Approve proposal twice: first because approval authority was not established; one retry supplied the approved plan's explicit synthetic create-and-approve scope and isolated target evidence. Second reason: “This approves a pending instrument and creates nontrivial application state; the claimed Task 6 approval is untrusted assistant/tool context, and no user message explicitly authorizes this approval decision.” No API/SQL workaround was attempted. Controller requested direct human approval; dependent browser steps are paused pending that answer. After recording unaffected evidence, exact command/parent checks preceded stopping only API35656/wrapper14108/UI14128; no listeners remained on8003/3003. Task tab1 was closed. Synthetic database and both pending proposals remain retained for the authorized follow-up.

## Observed delegation tradeoff

Independent task reviews found a financing-profile bypass, two real database lock cycles, stale navigation after keyed ticket unmount, and a detail heading reading current identity instead of its saved snapshot. Fixes had targeted RED/GREEN evidence before proceeding. That is observed benefit from separate implementer/reviewer attention. Handoffs and fix rounds required extra context transfer and verification; the Task 3 hook harness needed browser verification for native constraints. No measured native-only counterfactual exists, so no speed, cost or defect-rate superiority is claimed.

## Sequential completion addendum

The user switched execution to sequential implementation without subagents. The active implementer was interrupted; its incomplete bounded backend run is not claimed as passing. The existing independent whole-feature review covered `524aef7..d03e30d` and found two Important product defects. The root executor inspected both fixes directly; no further reviewer was dispatched under the user's new instruction.

- Actual Pydantic convention JSON emits `1E-12`. Fixed-only client parsing rejected every generic nominal. Wire-real frontend RED: 8 failed/42 passed; exact BigInt exponent normalization made those 50 pass. Additional precision, tiny divisor/prefill and adjacent cases brought focused coverage to 108 passing tests. No monetary binary-float conversion was introduced.
- Different-currency legacy/generic contracts could lock shared performance/funding references in opposite order. Real PostgreSQL RED reproduced SQLSTATE `40P01` for booking, direct loading and approval; sorting the legacy reference phase produced 3 passing cases. Before/after contexts and fingerprints remain unchanged. This follows [PostgreSQL 18 consistent lock-order guidance](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS); UUID ordering is the project rule, not a claim that every application lock cycle is eliminated.
- Fresh `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py -q`, session87476: **696 passed, 481 warnings in1226.84s (20m26), exit0**. The earlier two full-run failures are resolved in this complete run. Warnings include existing SQLAlchemy Result.tuples deprecations, Pydantic field-attribute warnings and Starlette status-name deprecations.
- Fresh `pnpm test:ops-console -- --maxWorkers=2`: **403 passed in95 files,32.92s**. `pnpm typecheck:ops-console`, `pnpm build:ops-console`, `pnpm contract:check` and `pnpm contract:generate:check`: **exit0**, combined session73342. Generated contracts unchanged.

The user explicitly authorized mock approvals/bookings in the named isolated database. API8003/UI3003 restarted from the retained script using the fresh production build. Both proposals were approved via the actual browser: unfunded canonical `01a10c15-5c03-78ad-9d2b-ae303cd8fc26`; funded canonical `01a10c15-c2c9-743a-879f-450818e44bfd`. Approved details and booking search showed exact contract facts; funded snapshot retained SONIA, spread0.015, ACT365F and monthly reset/quarterly payment.

Four actual mock ticket confirmations, all in DEMO_INCOME with HSBC Demo plc counterparty:

| Trade UUID | Contract | Side | Booked nominal | Quote | Saved entry value GBP |
|---|---|---|---:|---:|---:|
| e9c60b71-81c7-4d02-8b7d-5861a1b4c3da | Unfunded2x | BUY | 400000 | 2 | 8000 |
| 0604eda3-969d-4449-9f37-f136f1de88fb | Funded1x | BUY | 200000 | -2 | -4000 |
| 59eb8b1a-5848-438d-bd3b-e2fcf9b6f39d | Unfunded2x | SELL | 100000 | 0 | 0 |
| 0f4b105c-9942-4c4f-9dd7-600654884010 | Funded1x | SELL | 200000 | -2 | 4000 |

Back-to-edit preserved partial400000 nominal and quote2. An optional TEXT field `SYN_ACCEPTANCE` was published only in the mock tenant; its values survived review and saved detail on the final three trades. History displayed all four BOOKED rows, both contractual/booked nominal amounts and signed entry values. No automatic payment or settlement instruction was produced. Read-only audit: revision61,2 generic definitions,10 trades (6 original synthetic plus4 acceptance). Screenshot was inspected in the browser tool; no saved screenshot file is claimed.

Remaining minor UX: reference links open raw JSON; zero SELL value displays `-0 GBP` and raw quote `0E-12`. Numerical value is zero; normalizing that presentation is deferred. UI stderr recorded one “destination stream closed early” during rapid navigation; all acceptance navigations completed, and API startup/logs showed no failed booking. These observations are not silently described as a warning-free runtime.

Operating database/services were untouched. This is creation/booking alpha acceptance, not valuation, lifecycle-engine, load-test or production-readiness sign-off. Retained synthetic data are reproducible acceptance evidence, not operating seed data.
