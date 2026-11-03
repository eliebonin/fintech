# Standard cash FX P&L implementation plan

> Execute sequentially with test-first/verification skills. User explicitly asked
> for implementation, no opt-out and no historical compatibility work. Preserve
> unrelated changes; no automatic commit/push or destructive history purge.

**Goal:** Assess cash for every calculation; missing snapshots are visible,
non-blocking omissions, never zero. No UI/API exclusion flag.

**Architecture:** Reuse cash loader/typed storage/coverage and publication source
checks. Remove the optional switch throughout transport, domain, UI and source
health. Do not introduce a second calculator or replay old request defaults.

**Tech stack:** Python/Decimal/PostgreSQL; FastAPI; Next/React/TypeScript.

## Approved specification and boundaries

The user's 25 October instruction supersedes the opt-in choice in the original
cash design. Cash is always assessed. A cash source row remains visible even
when absent, explains its omission from totals, and does not prevent independent
publication. Supplied nonzero foreign balances still require eligible FX. Stale
sources, invalid evidence, current permissions and review independence still block.
No historical numeric rewrite, blind financial deletion or compatibility adapter.

The existing internal timestamp valuation entry point is not removed by this
cash change. With no complete cash pair, missing cash remains a non-blocking
omission. Supplied EoD cash pairs require EoD boundaries; they cannot be silently
inserted into an intraday calculation. Standard UI requests already use dates.

## Review focus

- No way to opt out through UI, payload or recalculation of a former opt-out.
- No balances/accounts and partially missing dates can stage/publish with warning.
- Supplied balance without required FX fails; missing is never assessed zero.
- Newly supplied/corrected cash after staging still requires recalculation.
- Old results without cash proof are not silently declared complete/publishable.

## Tasks

- [x] RED: transport rejects the removed flag; native calculation includes cash
  without one; missing-account/date inputs can publish. Update focused UI tests
  to require no cash checkbox and a visible non-blocking missing cash source.
- [x] GREEN: remove `include_cash_balances` / `includeCashBalances` from service,
  contracts, request builder, reassessment and cash source-health gating. Always
  assess cash; preserve exact source checks and typed ownership.
- [x] Update source report/form/browser tests; preserve the accrual option layout.
  Test new/corrected tickets, automatic cash inclusion and missing-cash publication.
- [x] Focused Python/disposable-DB, UI/browser, TypeScript and generated contracts.
  Update capability/register/map/methodology and delivery; author review.
- [x] Restart only API 8001, verify schema/health. No operating financial writes.

## Execution ledger

- Preflight: single inclusion switch currently crosses API/domain/retry, source
  health, report and UI. Removing it at all boundaries avoids an API-only bypass.
- Ruling: no physical purge is needed to implement the request. Immutable old rows
  may remain retained, but missing source proof cannot publish and no compatibility
  opt-out path is retained. Cost: those old results require a fresh calculation.
- Ruling: preserve internal timestamp entry points; assess absent cash without
  blocking, but reject supplied EoD pairs at intraday cuts. Cost: populated intraday
  cash needs a separately defined methodology; no hidden exclusion is offered.
- Test-first: pure transport/form tests failed on the retained switch; native
  storage/governance tests failed on excluded cash. After removal, focused core
  46 passed. Missing account/date cases independently publish with cashFxPnl null.
- Retry review: an old cashless idempotency key initially returned the obsolete
  attempt (regression RED). Request identity now pins calculation contract
  `economic-pnl-standard-cash-v1`; the key is rejected instead of returning it.
  No compatibility branch or rewritten historical result is introduced.
- Final focused run: **149 Python tests passed**, including current disclosure,
  cash omission publication, old-key rejection, stale-source rejection, amendments,
  current permissions and naming. No full Python suite was run.
- UI: **97 tests passed**; **six browser journeys passed**, including automatic
  cash, missing-cash publication and new/corrected form sizing. Types, OpenAPI
  and generated contract checks passed; opt-out absent from active product code.
- Author self-review, sequential as requested: checked non-blocking missing inputs
  versus blocking stale/invalid/required-FX cases, source-proof-less old records,
  empty population disclosure and unchanged investment market bridge. No unresolved
  important finding in this change. Existing SCHEMA-DOC-001 is unrelated/unchanged.
- Activation: API 8001 restarted; health passed and live OpenAPI has no cash flag.
  UI 3001 returned 200. No migration, balance upload, trade, valuation calculation,
  publication, permission change or history purge was performed in operating data.
  Final targeted UI smoke 18 passed; final TypeScript check passed. No commit/push.

## Valuation-window coverage correction — 25 October

The user rejected continuing missing-data warnings inferred solely from past
cash bookings. Scope discovery, validation, source hashing and reassessment now
use only opening-through-closing dates, inclusive. Account inventory is not an
upload obligation. A day with neither snapshot is skipped; one-sided supplied
pairs remain disclosed, not zero/carried. Request identity advances to cash v2;
existing frozen results are not rewritten.

- [x] RED: historic-only scopes, discontinued currencies on current accounts,
  neither-boundary days, unrelated historical source changes and obsolete UI
  account-inventory messages reproduced failures.
- [x] GREEN: date-bound loader/hash/health/queue, remove inferred account inventory
  fields/messages, retain opening-boundary corrections and one-sided gap checks.
- [x] Update delivery, methodology and capability/register/map.
- [x] Focused database/UI verification, author review and scoped API activation.

Verification: four native regressions failed for the intended reasons before
the fix; the unchanged opening-boundary guard already passed. Final disposable
database run: **43 passed** across cash storage/governance, presentation and
reassessment. UI: **78 passed in 14 files**; TypeScript and `git diff --check`
passed. No full suite or new browser journey was run for this bounded change.
Sequential author review checked missing-versus-zero, actual partial pairs,
source-window parity, scoped names and retained publication guards.

API 8001 restarted healthy; UI 3001 returns 200. An explicitly read-only source
selection for FCAGF, 19–20 October, finds **5 scopes / 10 snapshots / 0 incomplete
pairs**, rather than eight scopes with three historical-only gaps. No operating
calculation, publication, balance upload, financial rewrite or migration occurred.
Existing frozen results require a new calculation to show the corrected coverage.
