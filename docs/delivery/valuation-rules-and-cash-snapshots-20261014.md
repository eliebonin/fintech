# Valuation decisions and dated cash snapshots

## Approved intent and scope

Implement the October 14 discussion sequentially: readable applied-rule evidence,
methodology/acceptance checks, then uploaded company/account-scoped cash balances.
Lifecycle closing entries and derivative pricing remain deferred. No automatic
cash booking is generated from a security trade. No full NAV claim is made.

Cash is a signed balance snapshot valid only on its declared date, never a
movement or a cumulative trade. Reuse `trd.cash_account` and `trd.cash_balance`.
The account identifies its strategy and maintaining organisation; an account
label distinguishes multiple accounts at the same company. Currency includes
active cryptocurrency currencies. Notes are optional and not economic inputs.
Corrections append a revision, with a separate mandatory reason and predecessor.

## Implementation plan / execution ledger

Execution: current feature checkout, sequential native implementation, preserving
existing unrelated changes (user previously chose this checkout). No commit,
push, operating-data writes or migration activation without explicit direction.

1. [x] Add deterministic versioned applied-decision records to new frozen result
   evidence and render readable explanations; do not mutate historical evidence.
   Files: `valuation/decisions.py`, `valuation/service.py`,
   `valuation/position_storage.py`, `valuation-price-evidence.tsx`.
   Verify pure tests for fund price/FX date independence, new executions,
   same-currency identity, payment-only flows, split decisions and old evidence.
2. [x] Document the product/lifecycle matrix with current admissions and limits;
   retain numerical FX bridge tests and add combined decision scenarios.
3. [x] Add migration 89 extending existing cash tables with label, revision,
   predecessor, reason, note and idempotent submission evidence. Implement
   strategy-scoped account/list/upload APIs with exact decimal strings and atomic
   bounded JSON row uploads; CSV is parsed into that same contract in the UI.
   Verify dates, precision, duplicate rows, revision conflicts and isolation.
4. [x] Add a dated cash register and explicit valuation preview. Resolve and retain
   policy-selected FX evidence for the requested date; no carry-forward, no
   balance-change-as-profit. Cash values remain a separate report, not added to
   investment P&L or represented as complete NAV. Verify focused backend/frontend
   tests, typecheck, generated contracts and scoped diff; update capability records.

## Methodology matrix

| Case | Current intended treatment | Limit |
|---|---|---|
| Existing equity/ETF | Closing value minus opening value minus period execution value | Reviewed basic share ratios only |
| New execution | Actual booked execution cost; no fabricated opening market mark | End-of-economic-day execution FX, not intraday FX |
| Partial sale / round trip | Signed execution proceeds and reconstructed remaining quantity | No market mark needed for a zero boundary |
| Foreign holding | Price, FX and price–FX cross components reconcile to value bridge | Direct or explicitly permitted reciprocal FX; no triangulation |
| Fund | Canonical share-class NAV, governed session lag and publication/information cutoff | Native per-unit NAV only; FX independently uses valuation date |
| Bond | Clean market mark plus assessed daily earned interest and receivable FX | Native nominal/100; dirty market marks need separate proof |
| Bond maturity | Block remaining exposure without supported redemption | Lifecycle closing workflow deferred |
| Dividend/reset/coupon | Typed income or payment-only record; payment does not earn income twice | Unbooked income excluded; derivative reset reconciliation incomplete |
| Share ratio | Reviewed event changes derived quantity; original trade retained | Complex actions and fractional cash-in-lieu not inferred |
| Cash snapshot | Exact-date signed balance translated at governed FX | Not cash-movement P&L; no automatic trade-generated balances |
| FX forward/future/option/swap/structured | Booking does not imply valuation readiness | Live position valuation blocks unsupported economics |

## Design decisions and limitations

- Applied rules are generated from frozen backend facts with stable codes and
  versions. Human-readable text is not editable financial authority.
- A dated cash preview freezes balance revisions and FX observations in its
  response; it is not a staged/published financial batch. A future cash P&L module
  must explicitly model movements before attributing balance changes to profit.
- Accounts and balances require strategy action checks, not tenant-admin bypass.
- Existing legacy snapshots are preserved; only the new EOD upload convention is
  admitted by the new register. Missing is never silently zero or carried forward.
- Sources: [FCA valuation review, section 2.4](https://www.fca.org.uk/publications/multi-firm-reviews/private-market-valuation-practices)
  supports consistent methodology, input and change explanations. Its regulated
  private-market scope is guidance for this personal alpha, not certification.

## Verification and activation

Implemented in the feature checkout. Final focused disposable PostgreSQL checks passed
48 tests across cash APIs, source-date contracts, audit rules, existing economic
P&L, FX, flows, accruals and position storage. Includes a combined fund/new-trade FX
scenario and normalized-price/share-ratio/same-currency explanation checks.
Frontend affected checks passed 24 tests across six files; TypeScript and OpenAPI
consistency passed. Final verification is recorded separately below.

After explicit user approval, verified operating `platform_secm` was already at
migration 88; applied migration 89 and restarted only the verified API process
on port 8000. API logs: `logs/api-cash-snapshots-20261014.*.log`.
Read-only browser acceptance: cash page renders, readable strategies load,
Strat Testing exact-date empty state explains missing is not zero, account/CSV/note
controls exist, BTC/ETH/USDC currencies remain selectable, and save/preview are
disabled until required account/balance inputs exist. No live tenant cash balances,
financial publications, role grants or seed trades were created. Populated browser
upload/correction/FX preview acceptance remains unperformed. Existing result versions remain readable; recalculation
creates evidence-v2 position versions rather than rewriting evidence-v1 rows.

Rulings: use the user-selected dirty feature checkout rather than dropping earlier
uncommitted work; retain sequential execution and focused suites, not subagents or
full regression. Separate dated cash-value preview from authoritative investment
P&L; movements and persisted cash staging/publication remain explicit gaps.

Final review: author self-review, honoring the user's sequential/no-subagent
preference. Fixed real share-ratio evidence references and normalized price
explanation values under failing-then-passing regressions. Existing Starlette/httpx
deprecation warning remains; no unrelated dependency upgrade. No full suite run,
commit, push, or physical settlement/accounting implementation.
