# Full bond cashflow schedule — 27 October 2026

The [maintained reference](../architecture/trading-and-operations/bond-cashflow-schedules.md)
defines delivered contracts, units, permissions and deliberate limits. This
extends the [15 October coupon slice](bond-coupons-20261015.md).

## Change

- One versioned schedule holds COUPON and PRINCIPAL, same-day final coupon and
  redemption, principal-only zero bonds and explicit principal instalments.
- Exact amounts per 100 original nominal, retained currency, sourced formulas
  and optional conventions. Unknown amounts stay unknown.
- Lifecycle table/editor displays payment types and relevant fields. Principal
  cannot be selected or inserted as a coupon receipt. Help explains the boundary.
- Forward-only migration 100 preserves old schedule/row/payment IDs, hashes,
  amounts and revisions; migration 94 is frozen to its original schema.
- Daily valuation, cash snapshots and maturity-booking economics are unchanged.

## Verification record

Initial offline contract RED→GREEN: 10 checks. Initial focused disposable database
run: 19 passed, including those 10 contracts, service/API scope, immutable evidence,
inert financial counts and migration from v94 with an old receipt corrected and
reversed after upgrade. Initial UI component run: 4 passed. TypeScript passed
after API contract regeneration.

The initial browser run exposed an ambiguous test locator matching
multiple status regions; it was narrowed to the saved-status message. No failed
financial command was involved.

Final adjacent disposable run: **31 passed**, covering the mock bond valuation
cycle, plain redemption/service, zero-coupon interest applicability and domain
import boundaries. Together with the initial 19, 50 backend checks passed; the
full Python suite was not run. Existing Starlette/SQLAlchemy deprecation warnings
were observed, not introduced or suppressed by this change.

Frontend regression: **1,053 passed across 213 files**. Browser acceptance:
**14 passed** (2 schedule journeys plus 12 existing critical journeys). A subsequent
2-journey run in the actual workspace CSS verified mobile overflow and conditional
inputs. Screenshot review caught punctuation encoding in existing console text;
it was corrected, followed by **28 focused UI checks** and TypeScript passing.
Final browser run after punctuation correction: **3 passed**, including both
schedule journeys and the existing coupon pending/empty-state regression.
Desktop/mobile screenshots are retained under ignored `apps/ops-console/test-results/`.

OpenAPI export/check and TypeScript passed. The generated TypeScript was rebuilt.
`pnpm contract:generate:check` uses `git diff --exit-code`, so it reports the
intentional uncommitted API changes as a failure; it does not establish generation
drift in this dirty checkout. Deterministic regeneration is checked separately
without committing unrelated changes and was byte-for-byte identical. All 1,164
local file-link targets across 15 updated documentation files resolved; diff
whitespace validation passed.

## Local activation

Verified the app database was at migration 99 before applying **100**. It had no
stored coupon schedules/periods/confirmations; all three counts remained zero.
Four immutable/scope triggers remained installed. No permissions or financial
records were created. Old nonempty evidence preservation is established by the
separate disposable migration regression, not by these empty operating tables.

API `127.0.0.1:8001` and frontend `localhost:3001` started successfully; health and
context-selector reads returned 200. A direct read as the default demo actor
returned the existing lifecycle-authority 403. This check does not justify new
grants or a bypass; users need explicit strategy-scoped LIFECYCLE_READ, with
REFERENCE_APPROVE for maintenance. Permission-enabled HTTP/browser journeys were
verified in isolation.

## Remaining scope

No lifetime-completeness certification, generated schedules/fixings, automatic
interest, accrued-stock reconstruction, receivable reconciliation, DCF pricing,
principal payment confirmation or extension of automated amortising redemption.
Activation alone creates no financial records or permissions.
