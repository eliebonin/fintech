# Futures daily P&L implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially, following the user's current-checkout and no-subagent preferences.

**Goal:** Enable the already-bookable linear cash-settled index futures in daily economic P&L, with existing source/review controls.

**Architecture:** Recover exact original booking identities from retained context fingerprints; freeze compatible contract units, multiplier, divisor and dates. Calculate local price variation from opening holdings plus signed period executions, translate at each economic day's closing FX, and retain it separately from the investment-asset value bridge. Reuse existing attribution ownership, immutable versions, policy selection, amendments and publication.

**Tech stack:** Python Decimal, SQLAlchemy/PostgreSQL, FastAPI, React/Next.js.

## Design and constraints

- Scope is the existing cash-settled INDEX_POINTS booking slice. Creation-only physical/crypto contracts remain outside booking/P&L scope.
- Local variation = multiplier / quote factor × (closing quantity × closing price − opening quantity × opening price − sum(signed execution quantity × execution price)). New/closed boundary zero needs no mark.
- Reporting variation uses that day's closing reporting-per-price-currency FX. No FX on gross futures notional; actual margin cash remains in dated cash balances. No generated cash posting or assumed zero contract MTM.
- Add an explicit futures-variation term to period reconciliation; do not manufacture investment values or execution cash to force the old asset bridge to fit.
- Price dimensions must bind exact canonical expiry, quotation basis and divisor. Preserve rights, sealed calendars, RAW semantics and freshness.
- Existing booked evidence must remain unchanged; original context fingerprint must match recovered identities. Reject ambiguous or altered evidence.
- Existing feature branch contains prior uncommitted work; preserve it. No automatic commit/push, permission grants or operating financial commands.

## Tasks and execution ledger

- [x] 1. RED→GREEN pure futures tests: held/new/partial/full/round-trip/short; multiplier once; FX on variation; invalid conventions/expiry.
- [x] 2. Frozen booking normalization and governed contract-price selection. Real existing booking regression; wrong expiry/divisor denied.
- [x] 3. Stage/publish and multi-day reconciliation; retain exact variation evidence, source rights and amendment lineage. Disposable database tests only.
- [x] 4. Read-only futures inspection and applied rules; native variation, multiplier, execution prices and closing FX before technical proof. Focused component/browser checks.
- [x] 5. Reconcile capability/methodology/docs and run adjacent focused regressions, contract/type checks and final source review.

### Verification ledger — 27 October

- Initial 10 numerical cases RED on unsupported futures units, then GREEN.
- Main focused pure/database run: **60 passed** (88.56 s), including futures, unchanged monetary previews, swap/forward P&L, position storage and accrued-stock integration.
- Final futures integration after adding fee-amendment/publication: **5 passed** (47.14 s).
- Final offline bridge/frozen-evidence/adjacent tests: **85 passed** (11.27 s).
- Focused frontend: **35 passed** in four files; TypeScript and OpenAPI parity passed.
- Isolated browser: **3 passed**, then final actual-date futures walkthrough **1 passed**; screenshot inspected, mobile/close checks passed.
- Final review added RED→GREEN guards for cached per-trade venue validation, later-effective convention filtering and calculation-level applied rules. No operating financial commands or schema migration.
- Ruling: reuse the existing immutable attribution schema and add an explicit variation term to review reconciliation; do not mislabel gross futures notional or fabricate execution cash. Existing current-checkout/user preferences take precedence over automatic worktree/commit/subagent steps.

## Acceptance and deliberate limits

Prove ES-style multiplier 50 applies once, full closure contributes on T, and foreign unchanged contract price creates zero futures P&L despite moving FX. Mixed security/futures batches must still reconcile and publish with ordinary authority. Futures MTM/exposure preview is unchanged. No delivery, rolling, margin ledger, broker-specific cash rounding reconciliation or derivatives pricer is introduced.

Primary basis: [CME money-calculation guidance](https://www.cmegroup.com/clearing/files/CME-Money-Calculations-Futures-and-Options.pdf), reviewed 27 October 2026. Its opening-position plus execution-to-settlement decomposition informs the bridge. Existing exact economic amounts/12-place storage remain; this is not a claim of penny-for-penny clearing statement reconciliation.
