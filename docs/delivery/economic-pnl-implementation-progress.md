# Economic P&L execution ledger — plan: docs/superpowers/plans/2026-10-09-economic-strategy-pnl.md

2026-10-09. Sequential execution, current `codex/enriched-trade-booking`
checkout as requested. Preserve pre-existing modifications. No commit/push.

## Pre-flight

- Task 1 -> 2: original selected value remains source-owned; calculation consumes
  a separate verified normalized value. FX conversion follows price normalization.
- Tasks 2–5 -> 6: frozen position-owned components and input lineage feed candidate
  amendments; no mutable total edits or compulsory trade allocations.
- Task 6 -> 7: server state/version IDs own actions; the UI does not compute P&L.
- Ruling: maintain a tracked delivery ledger instead of Bash-only scratch helpers
  on Windows — recoverable progress without requiring a new shell environment.
- Ruling: retain current checkout and focused tests, no full suite or automatic
  commits, per explicit user preferences and the approved plan.
- Ruling: final review remains sequential/self-review, honoring no-subagents.

## Progress

- Task 1: implemented, live provider acceptance gated. Migration 77 adds nullable
  economic requirements and immutable observation-linked proofs; legacy policies
  and retry fingerprints remain unchanged. Resolver normalizes before arbitration;
  valuation consumes normalized values and preserves source prices. Yahoo split
  events are retained but its chart response does not certify anchor/completeness.
  Ruling: ship the safe conversion boundary with Yahoo conversion blocked until
  sourced proof is established, as expressly permitted by the price-basis plan.
  Cost: real Yahoo valuation can still be blocked; no fabricated factor-one proof.
  Evidence: 52 pure/provider tests, 28 resolver/policy/priority tests, 38
  valuation/corporate-action/permission tests passed. UI 15 passed; typecheck
  initially exposed the required contract field, corrected in the builder.
- Task 2: implemented; broader acceptance remains in Task 8. Pure PRICE/FX/CROSS, direct and explicit reciprocal FX,
  independent policy selection, cached daily bridge orchestration implemented.
  Synthetic cross-currency execution-day regression passes; 38 focused FX/storage/
  evidence/service tests and 20 FX/price/close tests passed. UI 16 tests/typecheck passed.
- Task 3: immutable accrual input table/API and local/base reconciliation implemented;
  6 isolated input/API tests passed. Position integration pending product gates.
- Task 4: real typed ledger flows and economic totals implemented; first 19 focused
  flow/storage/repository tests passed. Booking/cancellation API and acceptance pending.
- Task 4: flow booking/cancellation API now included; 34 focused flow, storage,
  bond-booking and accrual tests passed after a legacy storage-shape regression fix.
- Task 5: pure product gates and clean/dirty quote normalization tested (29 pure
  position/product tests passed); new bond bookings freeze valuation conventions.
  Fund NAV selection and bond accrual integration added; end-to-end gates pending.
  Ruling: dirty execution quotes are normalized from frozen settlement amounts;
  dirty market quotes require their own assessed per-nominal evidence and remain
  blocked without it. A position accrual balance is not fabricated as a market quote.
  Ruling: accrued-receivable FX uses separately evidenced CARRY, not ACCRUAL;
  clean market FX remains separate. Cost: reports must label CARRY explicitly.
- Task 6: amendment request/version/publication controls implemented, focused
  test run in progress. Requests do not mutate original financial evidence.
- Tasks 7–8: pending.

## Final bounded-alpha checkpoint — 2026-10-09

- Tasks 3–7 are now integrated: daily source register, real typed flows,
  clean bond execution/market gates, canonical fund NAV selection, source and
  component corrections, stale requests, immutable candidates and independent
  publication. UI reads server totals/evidence; it does not calculate money.
- Regression exposed and fixed: monetary flows entering accrual reconstruction;
  fund listings looking for nonexistent listing NAV streams; source revision/
  publication race; replaced candidates leaving requests pending; obsolete
  unmounted UI callbacks. A test-fixture booking lock was corrected without
  changing operating transactions or weakening lifecycle checks.
- Latest broader relevant disposable command used economic acceptance,
  amendments, accruals, flows, FX, storage, valuation API, evidence access,
  position attribution, recognition retry and input API files: **58 passed**.
  Final extended economic acceptance (bond + dividend, canonical lagged fund,
  flow-only dividend/reset/fee/payment-only coupon): **3 passed**.
- Focused UI command covers feature components, valuation console/price/failure
  evidence, page, BFF and date/recognition helpers: **30 passed**. Typecheck passed;
  final post-cleanup verification is recorded in the tool results. No full suite.
- Task 8 browser gate remains incomplete: two desktop browser initialization
  failures. Isolated API returned HTTP 200, but no actual browser walkthrough
  is claimed. Owned temporary UI/API processes were stopped and the exact
  disposable acceptance database removed; synthetic records are intentionally
  unrecoverable test data. Operating processes/database were not stopped/changed.
- Ruling: ship only tested product scope. Cash stock balances, redemption/final
  derivative economics and unproved dirty-market/Yahoo normalization stay blocked.
  Native fund NAVs require unit/quote factor one until separate normalization proof.
- Migrations 77–81 remain pending on the operating DB. No financial activation,
  operating publication, commit or push. See
  [delivery report](economic-pnl-implementation-2026-10-09.md).

## Owner-approved local activation — 2026-10-09

The user explicitly approved backup, migrations and restart. A full local DB
backup was retained under `logs/fortem-secm-before-economic-pnl-20261009-114809.dump`.
Operating head is now 81; API/UI were restarted on 8000/3000. Health/OpenAPI checks
passed; frontend unauthenticated access correctly redirects to tenant selection
and returns HTTP 200. No financial calculation/publication was performed.
Earlier pending operating activation notes are historical; browser/financial
acceptance and source-proof/product limitations remain outstanding.

## Review authority and delegated permissions — 2026-10-12

User requested fixes for the three review findings. Sequential execution in the
existing dirty checkout; no subagents, operating writes, migration, restart,
commit or push. Retained immutable run events hold real-operator authority so the
fix needs no schema migration. Legacy parent/request evidence remains readable;
incomplete operator history blocks impersonated review until recalculation.

RED: booking-only flow cancellation was wrongly accepted; correction-only
cancellation was wrongly denied; delegated valuation calculation controls were
absent; the original operator was not detected on an amended candidate. Each
regression was observed before its correction. The initial UI run also exceeded
the existing five-second cold-import budget; final runs used a 30-second budget.

GREEN: domain and HTTP cancellation use `TRADE_CORRECT`; calculation/request UI
uses `VALUATION_RUN`; decision/publication UI uses `VALUATION_REVIEW`. Attempts,
amendment requests and review decisions retain real-operator evidence in immutable
valuation events. Amended candidates carry calculator/requester contributors;
transactional publication checks cannot be bypassed by selecting another user.
Unchanged retries pass, and another real operator cannot borrow a request key.

Final backend command:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_valuation_flows.py tests/test_valuation_amendments.py tests/test_access_api.py tests/test_access_management.py tests/test_access_session.py tests/test_valuation_api.py tests/test_valuation_storage.py tests/test_position_attribution_storage.py tests/test_valuation_recognition_storage.py tests/test_economic_pnl_acceptance.py tests/test_valuation_acceptance.py -q --tb=short -p no:cacheprovider
```

Result: **78 passed**, nine pre-existing deprecation warnings. An earlier broader
run had 77 passes and one obsolete self-review HTTP-status assertion. The earlier
33-test run had one obsolete module-denial message assertion. Both now assert the
central permission boundary's 403 behavior; neither earlier run is claimed green.
The successful HTTP acceptance additionally exercises real context switching,
independent amendment approval/publication and display-right revocation.

Frontend: `pnpm --filter ops-console test -- --maxWorkers=2 --testTimeout=30000`
passed **768 tests across 164 files**. `pnpm --filter ops-console typecheck` and
`.venv/Scripts/python.exe -B scripts/export_openapi_contract.py --check` passed.
Changed backend modules parsed successfully, and scoped whitespace checks passed.
No full Python suite, new production build or browser visual signoff is claimed.
The test wrapper owned the disposable databases; operating records were untouched.
