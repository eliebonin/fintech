# Cash booking and approval integrity — 2026-10-05

**Status:** Implemented and verified locally; no deployment/restart included

**Scope:** Cash integrity and FX-forward/bond/ETP approval revalidation from the [instrument integrity review](2026-10-05-instrument-integrity.md). Sequential implementation in the existing feature checkout; previous FX scope work preserved. [Execution plan](../../superpowers/plans/2026-10-05-cash-and-approval-integrity.md).

## Cash booking boundary

`cash_booking_integrity.load_cash_booking_listing` now runs inside the authoritative cash writer after authorized replay lookup and before any new trade is inserted. Frontend filtering remains convenience, not authorization.

- Listing and economic parent must be active and tenant-visible; explicitly scoped records must have ACTIVE scope. Legacy unscoped references retain the established shared treatment.
- The listing must be tradable and the parent current. **The parent need not be directly tradable:** the seeded canonical equity deliberately uses `is_tradable=False`, while its listing is tradable. Requiring both would wrongly reject valid listing-backed trades.
- Each needs exactly one current APPROVED definition; a pending draft does not shadow an approved definition. The operational fields must agree with approval, including type/currency/issuer, listing venue/symbol, quote factor and unit multiplier. Execution date must fall within the approved periods.
- Legacy null operational start dates defer to the explicit approved-definition start. No operating date is fabricated or rewritten. Current-approved-definition coverage is required; this is not a version-resolution engine for all historical contracts.
- Selected currencies, reference types, product type, venue and supplied issuer must be active. Scope/reference/definition/catalogue rows are locked and discovered parent/currency IDs are reread to refuse changes during lock acquisition.
- Supported cash types are explicit: EQUITY, ETF, ETC, ETN, ETV, ETI, DIGITAL_ASSET, FUND, FUND_SHARE_CLASS, EXCHANGE_TRADED_VEHICLE and EXCHANGE_TRADED_CERTIFICATE. Unknown types and specialist derivatives/bonds cannot fall through. Frontend type filtering matches this list; it does not certify full booking readiness.
- Quotes remain in their entered native convention. Positive approved quote factors and multipliers are accepted, including the existing factor 100 equity fixture. This slice does not silently normalize execution price, change quantity units, redesign cash consideration previews or implement valuation.
- New CASH_BOOKING evidence stores approved definition IDs, quote factor, multiplier and price currency in the existing BOOKED event payload. Historical trades/events are not backfilled. Exact authorized retries return their original saved trades before current reference checks; fingerprints and replay keys are unchanged.

## Approval revalidation and atomicity

The three existing approval services own a savepoint. Aggregate insertion, relationships, decision evidence and proposal state succeed together; a direct caller catching a late failure cannot retain partial materialization. No helper commits the caller's outer transaction.

Locked approval-time validation rechecks:

| Workflow | Required dependency checks |
|---|---|
| FX forward | Active base/quote currencies and optional fixing currency; coherent pair/effective/maturity/settlement dates; active target configuration |
| Bond | Active supplied base currency, issuer and day-count convention; existing enrichment readiness; active target configuration |
| ETP | Active supplied currency and issuer; visible active reference node/scope; current approved effective consistent definition for instrument references or active index terms; active reference/target types |

Sparse ETP fields remain optional; missing optional references are not invented. A rejection does not require dependencies to remain active. Refused approval leaves the proposal PENDING with no decision or aggregate fragments. Existing HTTP error mapping is retained; this is not new approval authorization/authentication infrastructure.

## Concurrency and limits

Cash takes selected currencies in UUID order, reference identities/scopes in UUID order, then projections/definitions and shared catalogue phases. Approval takes selected currencies before its reference identity/projection checks and catalogue dependencies. Both complete the reference-type phase before acquiring product types; IDs within each phase are sorted. The ETP phase includes both its reference instrument type and its target type, avoiding late reverse-order acquisition. Scope and active dependency locks last only through the transaction, not user review time.

The scheduled catalogue regression first failed for both writers: while a separate transaction held the INSTRUMENT reference-type row, the waiting writer retained the EQUITY product-type row (`FOR UPDATE NOWAIT` returned lock-not-available). That is a demonstrated lock-order inversion risk, not an assertion that the test observed a complete deadlock. After correcting phases, both tests pass: the later product type remains available while the earlier reference-type phase is blocked.

This does not certify application-wide deadlock freedom, add immutable parent-association versioning, or harden every historical onboarding path. Safe amendments, general historical eligibility policy, post-booking corrections/lifecycle and valuation/P&L remain separate.

## Verification record

All PostgreSQL tests use disposable migrated/seeded databases via `scripts/run_isolated_python_tests.py`; operating tenant records are untouched. Logs are retained locally under `.superpowers/sdd/2026-10-05-instrument-integrity/`.

- Initial RED: **35 failed, 1 passed** in 2.01s. This characterized missing cash/approval checks plus the existing partial-bond failure. The initial parent-tradability expectation was then corrected against the canonical/listing semantics, not by editing fixture data.
- Initial cash GREEN after that correction: **65 passed, 40 warnings** in 83.78s (`cash-focused.log`). Cash buy/sell, enrichment, strategy authorization, late failure and replay compatibility covered.
- Initial approval GREEN: **19 passed** in 14.99s (`approval-focused.log`). FX/bond/ETP onboarding and refusal/atomicity covered.
- Expanded cash/approval checks: **43 passed** in 17.59s (`cash-approval-expanded.log`), before the additional waiting-order and late-response-failure checks.
- Frontend RED: the new unknown/unsupported product-filter test failed before filter changes.
- Full frontend first run: **435 passed, 2 timed out**, 98 files. Failures were `fx-forward-pnl-page.test.tsx` (unsupported valuation domain boundary) and `trade-history-page.test.tsx` (generic notionals/whole-swap snapshot rendering), each at the existing 15-second limit.
- Full frontend retry with `--maxWorkers=2`, unchanged timeouts: **437 passed, 98 files** in 23.41s (`cash-ui-retry.log`). No unrelated UI or timeout changes.
- `pnpm --filter ops-console typecheck`: exit 0.
- `scripts/export_openapi_contract.py --check`: exit 0; no API contract drift.
- `git diff --check`: exit 0.

- Final focused backend run, including scheduled lock order, cash revocation while waiting and late approval response failure: **47 passed** in 6.79s (`cash-approval-final-focused.log`).

Full Python verification exposed a test-execution mistake: two full runs overlapped on the same PostgreSQL server. Separate application-test databases did not isolate connection slots or the legacy migration test database name. The earlier run returned **5 failed, 751 passed, 20 errors, 417 warnings** in 817.73s; every reported failure/error was `too many clients already`. The final-code overlapping run returned **5 failed, 772 passed, 1 error, 439 warnings** in 677.19s: four strategy checks exhausted connection slots and two migration checks encountered the shared test database in use. Neither result is clean acceptance, and production checks were not weakened to accommodate these infrastructure failures. Both processes exited and their disposable application databases were cleaned up by the runner.

A fresh **single full-suite run**, with no overlapping test process, passed: **778 passed, 481 warnings in 607.31s (10m07s), exit 0** (`cash-approval-serial-full.log`). This includes all 47 new integrity/locking regressions and the existing booking, onboarding, migration and history checks. The disposable application database was removed by the runner. Warnings include SQLAlchemy deprecations in seed/demo helpers, Pydantic field-alias warnings and Starlette status-name deprecations; this work does not claim a warning-free suite.

No schema migration, operating data edits, application restart or GitHub push included. No independent subagent sign-off: author self-review and real boundary/concurrency tests are the assurance supplied. Systematic-debugging/TDD guided the failing boundary tests and lock-order correction; verification-before-completion kept overlapping infrastructure failures distinct from final acceptance.

## Remaining separate work

- Follow-up implemented: [booking readiness frontend](../booking-readiness-alpha.md) surfaces approved versus bookable readiness and actionable refusal reasons in instrument selection; follow that record for its separate verification and limits.
- Agree historical-date eligibility and safe reference amendment/versioning policy across products.
- Address cash quotation/consideration UX explicitly before expanding convention support.
- Post-booking correction and lifecycle workflows remain separate; valuation/P&L is intentionally deferred.
