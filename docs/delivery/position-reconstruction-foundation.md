# Position reconstruction foundation — delivery report

Date: 2026-10-08. Implementation and targeted verification complete. **Operating schema activation complete**: on explicit user instruction, database `fortem_secm` was upgraded from `20261007_69` to `20261008_70 (head)`. Ownership columns, all four ownership/version constraints and both enabled lineage protection triggers were verified. Existing trade/result/batch counts remained 9/0/0; no financial calculation or publication was submitted.

## Delivered

- Independent `positions/` package: typed immutable ledger facts, compatible position keys, AS_OF/PERIOD reconstruction, signed native quantities, exact Decimal arithmetic, economic and information cutoffs, original definition/trade/event lineage, deterministic hashes and explicit incomplete-knowledge labeling.
- Scoped SQLAlchemy repository: strategy ownership checks and 500-trade keyset chunks, bounded lifecycle/definition reads, no total population limit. Present-day active flags and mutable listing multipliers do not reconstruct historical trades.
- Position-owned valuation method `listed-equity-position-market-pnl-v2`: opening holdings, every supported period execution and closing holdings reconcile through `closing - opening - signed executions`. Only nonzero boundary values request market marks. The single-currency market component is PRICE, with FX/CROSS zero.
- Flat-before-opening episodes create no financial result lines. Their facts still establish economic state and undergo corporate-action safety checks. The unclosed opening episode and all period executions own current financial lineage; old closed episodes are not copied into new result lineage.
- A round trip with zero opening/closing quantity retains P&L without market marks. Example: buy 2 at 100, sell 2 at 110 => P&L 20. Same-day closures/reopenings, partial sales, shorts, reversals, fractional quantities and incompatible convention buckets have explicit tests.
- Revision 70: mutually exclusive real trade/position ownership on attribution and review items, position version uniqueness, actual valued subject UUID, and separate immutable original trade/event lineage. Existing v1 rows remain untouched and readable; authoritative publication replaces the complete official population across formats.
- Existing operational attempts, independent review, publication reconciliation, stale-population protection, permissions, idempotency, stable input transactions and stale-worker recovery are reused. Completed result lineage cannot be amended by UPDATE/DELETE or late INSERT.
- UI: position labels, original trade links, financial scope limitations and explicit evidenced-zero results. Historical trade-owned rows remain identifiable. Current DISPLAY rights still guard provider-derived evidence; intrinsically execution-only/empty results have narrowly validated no-market-source handling.
- Safe operational telemetry distinguishes scanned facts, position buckets, executions, mark requests and output lines. CI compilation includes the new package. Production has one v2 calculation path; v1 replay/calculation is a frozen test-only equivalence fixture, not a fallback.

## Review corrections

1. Completed lineage INSERT was initially unprotected. A reproduced regression now verifies the locked parent attempt must still be RUNNING before insertion.
2. Empty/no-mark calculations initially bypassed policy validation. Explicit tenant/status/date/knowledge/strategy policy checks, known cut and active reporting currency now apply even with zero positions.
3. Malformed no-mark Decimal evidence initially leaked an arithmetic error. It now fails closed as evidence permission denial.
4. Initial result lineage included unnecessary closed pre-opening episodes. Those are trimmed from financial ownership while all period executions remain represented. Staging indexes source facts by trade instead of rebuilding membership sets/scanning history per position.
5. Raw historical +10/-10 across an unreplayed split can falsely look flat before the requested period. ALL historical raw exposure intervals are safety-checked before trusting zero boundaries; otherwise the new population shortcut would undo the earlier corporate-action fix. Ambiguous dates and unsupported transformations remain blocking.

## Verification

Lightweight first, disposable PostgreSQL afterwards; no full project suite rerun.

- Final pure bundle: **75 passed in 0.77s**. Files: position reconstruction/bridge, evidence permissions, frozen v1 replay reference, economic kernel, corporate actions, selection identity. Includes hand-derived values and compatible long/short/fractional v1-v2 equivalence controls.
- Final disposable DB/API/review/migration bundle: **67 passed, 8 existing seeding deprecation warnings, 88.26s**, runner exit 0 and owned-database cleanup. Command:

  `.venv/Scripts/python.exe -u scripts/run_isolated_python_tests.py tests/test_position_repository.py tests/test_position_attribution_storage.py tests/test_position_valuation_acceptance.py tests/test_valuation_service.py tests/test_valuation_storage.py tests/test_valuation_api.py tests/test_valuation_acceptance.py tests/test_valuation_follow_up.py tests/test_valuation_migration.py -q --tb=short`

  Log: `logs/position-foundation-safety-final.log`. Covers 1,002 trades, chunk counts, tenant/time filtering, absent lifecycle evidence, flat round trips, pre-opening and period corporate actions, actual position ownership, immutability, zero-result HTTP/retry/self-review, v1/v2 replacement, source-rights revocation, concurrent identical requests, recovery, and migration upgrade/downgrade/upgrade.
- Frontend: **11 passed**, component/page/BFF; TypeScript exit 0. Logs: `logs/position-ui-green.log`, `logs/position-typecheck-final.log`.
- Scaling controls: **3 passed**, 201/2,001/10,001 scanned facts each yielded one priced position, one execution and one mark request. With tracemalloc, initial measured elapsed 0.1499/1.4073/13.3092 seconds and peak 1.48/10.71/40.54 MiB. These are traced synthetic reconstruction measurements, not database throughput, production timings or bounded-memory certification.
- Git whitespace check exit 0 (existing CRLF warnings). Verification was sequential author review, **not independent review or browser signoff**.

The intermediate runs are not represented as passes: initial integration 28 passed/3 failed (missing empty-policy validation plus two old fixtures relying on empty-strategy rejection); later 65 and 66 passed before the final safety case; UI initially 3 passed/2 failed before rendering changes. Terminal-lineage INSERT, malformed evidence, financial-lineage trimming and historical split pruning each had a reproduced RED. The first repository run reached collection after its implementation and is explicitly a GREEN-only adapter verification, not claimed RED/GREEN.

## Rulings and boundaries

- Work remained in the approved dirty feature checkout because the uncommitted preceding foundation is required. No automatic commits/pushes; unrelated work preserved.
- Existing review/storage tables were extended instead of creating a parallel financial engine. The existing `storage.stage` remains the integration contract; the position-line adapter implements position-owned staging behind it.
- Skill scratch-script bookkeeping was replaced by the maintained [execution ledger](position-reconstruction-progress.md). Sequential author review replaces subagent review at the user's request.
- Conservative historical corporate-action validation is necessary before pruning apparently closed raw positions. Its cost is that unresolved historical unit/identity changes can still block apparently flat histories until governed replay exists.
- Only compatible listing/subject, unit, currency and frozen factor/basis buckets net. There is no automatic cross-listing/currency conversion, FIFO/LIFO accounting or trade mutation.

## Remaining work

- Historical I/O and projection/evidence materialisation still grow with ledger history. Versioned checkpoints with backdated-correction/information-cut invalidation, large-universe action-query batching and asynchronous jobs are separate scaling work, not secretly implemented or claimed here.
- Corporate-action transformations and in-period cancellation/supersession economics remain deliberately unsupported, rather than inferred as sale/cash events.
- ETF subtype identification retains the existing effective-dated ETP-terms adapter. Dedicated frozen subtype/term-version linkage in booking evidence is further reference-data governance hardening; this delivery does not redesign booking snapshots.
- Valuation remains listed equity/ETF, single currency, market-only. Cash, income, fees, settlement/accounting, derivative valuation, multi-currency FX and full NAV are not included.
- Revision 70 is now applied to the operating database. Downgrade refuses to discard populated v2 financial history; it is not a casual undo command. No app restart or new browser acceptance was performed during schema activation.

See the [design](../superpowers/specs/2026-10-08-position-reconstruction-foundation-design.md) and [plan](../superpowers/plans/2026-10-08-position-reconstruction-foundation.md).
