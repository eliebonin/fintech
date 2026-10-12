# Market-only valuation and P&L attribution alpha

> Historical first-alpha checkpoint, superseded for current scope by [position reconstruction](position-reconstruction-foundation.md) and [economic v3 delivery](economic-pnl-implementation-2026-10-09.md). Use the [capability register](../product/feature-register.md) for implementation status; the single-currency TRADE-only restrictions below describe this dated slice.

Date: 2026-10-07. Status: implemented, verified and activated locally for the bounded market-only scope.

2026-10-08 superseding implementation: [position reconstruction foundation](position-reconstruction-foundation.md). New calculations use position-owned v2 attribution rather than historical trade-owned lines. Revision 70 was tested on disposable databases and subsequently applied to operating database `fortem_secm` on explicit user instruction; current revision and ownership/lineage protections were verified. No operating calculation/publication was submitted. The verification/activation records below describe the original v1 release, not a current full-suite or v2 browser-signoff claim.

## Delivered boundary

The dedicated `valuation` package replaces none of the retired demo endpoints. It uses historical immutable BOOKED/lifecycle evidence, frozen market-data selections and Decimal arithmetic. The HTTP layer is transport/authority only; the frontend displays backend results and performs no financial calculation.

Supported first scope: listed EQUITY and ETF bookings, SHARES/UNITS, one execution/mark/reporting currency, explicit RAW OFFICIAL_CLOSE PRICE semantics, governed exchange sessions and current-date prices. The resolver continues to enforce VALUATION-use data rights. No Yahoo personal-research permission is upgraded to valuation permission.

V2 reconstructs compatible opening/closing position buckets and all signed period execution movements. Only nonzero opening/closing values require market marks; round trips ending flat retain their trading P&L without a closing mark. The exact bridge is closing value minus opening value minus signed execution value. The current single-currency PRICE component equals market P&L, with FX/CROSS zero; multi-currency conversion remains deferred. Original trades and lifecycle events remain linked evidence, not invented attribution owners.

Unsupported products, missing original booking evidence, unknown lifecycle events, in-period removals needing lifecycle economics, missing/ambiguous prices, unknown calendars, unsupported precision and known unit-changing corporate actions fail closed. No failed line is silently omitted from a claimed complete market total. Income/dividends, cash, adjustments and full NAV are not included; the UI names these limits.

The [historical corporate-action safety correction](corporate-action-valuation-guard.md) extends the guard from the P&L period to each retained booking's execution-to-close interval, including pre-opening actions. Original trades remain immutable; automatic corporate-action position transformation remains deferred.

## Evidence and review

Additive migration `20261007_69` creates six `nav` tables: technical attempts, append-only run events, immutable attribution versions, review batches, selected attribution items and append-only review events. Frozen static migration DDL does not depend on future runtime metadata. Scope/ownership and component reconciliation are enforced in PostgreSQL as well as application code.

Attempt STARTED/FAILED evidence commits separately from financial work, retaining actionable safe failure reasons after rollback. Correlation IDs, timing/counts and selected review batch IDs are recorded. Wall-clock timestamps prevent events from appearing out of order across transactions. Configured API statement/lock timeouts also cover engine-owned transactions. The [follow-up hardening](valuation-follow-up-hardening.md) adds stable transaction snapshots, bounded serialization retries and explicit locked recovery of stopped stale workers; automatic supervision/background workers remain deferred.

Staging is AUTHORITATIVE only: a complete candidate population, not an incremental partial refresh. It does not change official results. Identical inputs reuse immutable versions/batches. Publication requires a different authorized administrator, a reason, no blocking validation and an unchanged official population hash. It independently reconciles the selected immutable versions with the review summary and opening/closing/execution bridge. Previous published selections remain available as superseded history. External comparison is explicitly NOT_COMPARED, never assumed MATCHED.

The `TRADE` subject uses a real foreign key. Broader subject types, income/cost allocation, controlled manual adjustment and external-comparison upload remain deferred. This implements the useful Fortem-core staged/official split, versioning and review principles without importing its float arithmetic or legacy integer-ID model.

## Access and UI

`/v1/valuation` exposes options, paginated attempts, attempt detail, calculation, review explanations and publication. Both VALUATION and MARKET_DATA module access are required; writes additionally require TENANT_ADMIN. Tenant membership is server-verified and foreign objects are opaque. No module/right grant or self-review exception is created.

`/valuation` offers calculation inputs, safe same-key retry after uncertain responses, run history, operational logs, frozen financial evidence, explanations and independent publication. A complete, valid empty v2 population is an explicitly evidenced zero and can be independently reviewed/published; missing ledger evidence or invalid policy scope still blocks. Periods are bounded to 31 days. There is no historical-trade population cap. Keyset-batched reads, query/lock budgets and separate scanned/valued population counts remain; large-population performance is not certified. Financial evidence is protected, not general-purpose log output.

## Verification record

Initial lightweight RED/GREEN tests covered exact Decimal decomposition and historical replay. Isolated PostgreSQL tests cover frozen resolver selection, unsupported inputs, corporate actions, idempotency, stale publication, independent review, immutable evidence, opaque tenants and rollback-surviving failures. Regression review also caught negative-zero hashing and transaction-start timestamp ordering.

Final combined focused suite: 78 Python checks passed in 77.85s, including module authority, transaction budgets, migration round trip, economic/session cutoff ordering and publication-summary reconciliation. Frontend: 607 tests/129 files passed in 33.25s with two workers; one earlier unconstrained run timed out in an existing trade-history test. Ops-console and generated-contract TypeScript checks passed. Exported OpenAPI consistency passed; regenerating TypeScript produced the same SHA256. `generate:check` compares generated content against Git HEAD and therefore reports the expected uncommitted contract changes; that is not a generation mismatch. Git whitespace check passed after removing a documentation trailing-space issue.

Self-review was sequential and is not independent signoff. Browser access-denial acceptance passed; no operating financial records were created or published.

The first full run found 11 fixture-isolation failures (1,151 passed, 482 warnings, 1,099.40s): earlier booking tests populated the shared demo strategy with unsupported products. Production rejection was correct. Valuation fixtures now own separate synthetic strategies, with database-name guards and rollback-scoped financial rows. A swap-booking→valuation regression passed all 43 tests with one warning in 49.18s. No failure was hidden by weakening the product allowlist.

Additional successful HTTP acceptance passed (one test, eight existing seeding warnings, 53.65s) on a separate child database: calculate/stage, exact 109.877 market P&L, same-key attempt/batch reuse, evidence retrieval, Ops explanation and independent-review enforcement. The child database was removed in test cleanup. A resumed frontend rerun again timed out during the existing trade-history page's cold dynamic import; the final run below resolved the test-runner timing constraint.

Final resumed frontend verification: 607 tests/129 files passed in 159.83s using one worker and a 15-second bounded cold-import allowance (`logs/valuation-frontend-final.log`); no application code, assertions or test skips were changed to obtain that result. TypeScript, exported OpenAPI consistency and whitespace checks passed again.

Full isolated Python rerun: 1,167 passed, 482 warnings, 1,855.44s; runner exit0 and database cleanup (`logs/valuation-python-full-final.log`). Warnings are existing SQLAlchemy deprecations and Pydantic field-metadata warnings; passing does not certify warning-free code.

Local activation: Alembic current verified `20261007_68` before upgrade and `20261007_69 (head)` afterwards. The live `/valuation` page displays MARKET-ONLY ALPHA, tenant-aware calculation controls and run history. Browser acceptance was read-only after selecting existing tenant access; no operating calculation/publication was submitted. Existing trades, prices and licensing rights are unchanged. No automatic commit or push was performed.

## Research and implementation references

See the [design and dated primary-source research](../superpowers/specs/2026-10-07-valuation-pnl-design.md), [execution plan](../superpowers/plans/2026-10-07-valuation-pnl.md) and [broader attribution ownership direction](../architecture/market-data-and-valuation/pnl-attribution-subjects.md). The reference implementation is Fortem-core `data/sources/ops/pnl_attributions`; its staged/official selection and immutable review history are inspiration, not a runtime dependency.
