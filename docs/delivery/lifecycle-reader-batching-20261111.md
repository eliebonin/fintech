# Remaining lifecycle readers: measured batching

**11 November 2026. Implemented, verified and locally activated.**

## Scope and result

Following the structured-worklist correction, review covered bond maturity, bond coupons, FX-forward maturity, futures and options. Bond/coupon source reads were already batched and were retained. The repeated FX exposure/annotation queries and historical option/future/structured-note identity reads are now batched below HTTP. No SQL index, migration, subscription selection, grant, operating financial entry or valuation was changed. Creation, pricing and financial command semantics are unchanged.

## Current checkpoint

| Work | Status | Evidence / remaining work |
| --- | --- | --- |
| Structured lifecycle source batching | Implemented and activated | [Separate delivery](structured-lifecycle-batch-reads-20261111.md): 4458 → 89 queries; complete source/result equality. |
| Other lifecycle readers | Implemented and activated | FX-forward, futures and option batching; bond/coupon source reads were already batched. Measurements and preserved controls below. |
| Separate Instrument and Event columns | Implemented and checked | [UI delivery](lifecycle-worklist-20261105.md#event-column-readability--11-november-2026): readable milestone/family labels; 5 focused tests, typecheck and 3 existing browser cases passed. |
| Explain the option request's 55 calls | Analysis complete | One date query already covers all selected options. The total includes authority, holdings, current/historical sources and allocation data. Exact breakdown below. |
| Measure repeated permission resolution | Analysis complete | Five reads cost 6.620 ms median locally; four resolutions cost 26.809 ms. Measurements below. |
| Reuse authority context and booking evidence; consolidate further source reads | Not implemented | Preserve scope, source ambiguity checks and deliberate permission freshness. [Open finding LIFECYCLE-READ-REDUNDANCY-003](../../FIX.md#lifecycle-read-redundancy-003--fixed-option-worklist-overhead-remains-after-batching). |

This checkpoint documents the delivered optimisation and subsequent investigation. It does not claim that 55 queries are a minimum or that the pending context/evidence consolidation has been implemented.

## Paired measurements

Local PostgreSQL on port15432; three alternating before/after trials per scenario, same database transaction, frozen recording time and complete event **and internal inspection/position evidence** equality. Counts include the worklist calculation but exclude acquisition of the shared recording clock and HTTP/authentication. These are local measurements, not latency guarantees. The earlier one-shot profile included the clock, hence its counts are one higher. Disabled operating futures/options are not used as performance evidence.

| Scenario | Before queries | After queries | Before median seconds | After median seconds | Matching events |
| --- | ---: | ---: | ---: | ---: | ---: |
| FCPGF bond maturity | 52 | 52 | 0.2837 | 0.1625 | 17 |
| FCPGF bond coupons | 49 | 49 | 0.1576 | 0.1622 | 18 |
| FCPGF FX maturity | 155 | 49 | 0.3558 | 0.1426 | 8 |
| Synthetic futures,13 distinct contracts | 101 | 53 | 0.2215 | 0.1423 | 39 |
| Synthetic physical options,13 contracts/21 trades | 135 | 55 | 0.2397 | 0.1528 | 26 |
| Synthetic cash options,13 contracts/21 trades | 135 | 55 | 0.2439 | 0.1417 | 26 |
| Synthetic FX forwards,13 distinct contracts | 230 | 49 | 0.4424 | 0.1412 | 13 |

Operating window:2026-10-12→2028-12-11, earlier overdue included. Synthetic paired window:2026-01-01→2028-12-31. Native query-budget tests additionally use their established product-specific helpers: options56→56, futures54→54 and FX80→80 as the number of distinct contracts grows from1 to13. Different windows/filters explain the difference between the FX paired and budget counts. All original8 operating FX blocked states and reasons are retained; a faster read does not resolve operating configuration/evidence gaps.

## Implementation and preserved controls

- [Historical identity sources](../../positions/identity_sources.py) are lazy and bound to the existing ledger page, strategy, connection and transaction. They read complete original APPROVED/SUPERSEDED definitions and listings, conventions, currencies and term/family identities in500-ID chunks. Existing normalizers still enforce original BOOKED fingerprints, date/currency/venue compatibility, factors and unique matching. Strategy ownership is checked at ledger entry. Cancelled legacy payloads are not parsed to prefetch identity inputs. Ordinary bond/coupon/cash paths incur no eager identity SQL.
- [FX maturity sources](../../lifecycle/fx_read_sources.py) verify tenant/strategy ownership and read exact strategy/instrument **pairs**, trades and recorded lifecycle chains in chunks. [Discovery](../../lifecycle/worklist_fx.py) still invokes the native per-trade exposure validator with the same cutoffs, obligation reconstruction, cancellation/supersession and allocation rules. Policy and annotations are fetched once per strategy. Full native pending-preparation candidate/fingerprint revalidation is retained.
- [FX term batch](../../security_master_schema/fx_forward_reference.py) uses the existing visibility query and terms validator. If legacy joins produce several candidates for one instrument, it falls back to the original single loader to preserve native first-row semantics. This exceptional path may cost an extra query; it is not a new interpretation of ambiguous master data.
- [Annotation batch](../../trading/annotation_snapshots.py) retains original tenant joins, curated record identity, aliases and standard COMMENT/TRADER/COUNTERPARTY/EXECUTING_BROKER fields. Raw rows are grouped by trade once; validation runs on each root's subset, so a conflict on one instrument cannot incorrectly block another. Scope reuse across tenants/connections/transactions or uncovered identities is rejected.
- Native financial commands do not pass discovery batches. No new global cache, stale cache lifetime, current-only historical lookup, row cap or simplified economic validator was introduced.

## Verification

- [Query budgets and page/scope parity](../../tests/test_lifecycle_query_budgets.py): real native bookings over distinct contracts and repeated option trades; physical/cash options; identical facts with2-row historical pages; covered source/strategy guards. The red baseline reproduced56→136 option queries,54→102 futures and81→261 FX under those native helpers before implementation.
- [Annotation subset regression](../../tests/test_annotation_read_batches.py): standard values retained; conflicting aliases isolated; no rendering SQL; cross-tenant/uncovered source denied.
- Affected central regressions:111 passed across position repository, frozen option/future valuation, structured-note valuation/notifications, allocation store, trade-profile guards and option/future worklists. Strengthened the direct-note regression to require an assessed nonempty quantity, avoiding vacuous checks on failed projections.
- Native FX read/command checks:21 passed across discovery, preparation/posting, replay, cancellation and annotations. Final affected rerun:39 passed, covering all read budgets,2-row physical/cash option identity pages, annotations, allocation store and native FX service/worklist controls after the final subset-index change.
- Four separate synthetic full before/after benchmarks passed; three operating full before/after comparisons also matched every retained result/proof.
- Full project suite was not run: verification is bounded to affected readers, economics, tenancy and native lifecycle controls.

Machine-readable local evidence and frozen readers are retained in ignored `.superpowers/sdd/2026-11-11-lifecycle-readers/`. The maintained product does not import these benchmark scripts. No operating subscriptions were enabled merely to make synthetic tests pass.

## Remaining limits

Query counts grow by source/keyset chunks and scoped strategies, not unbounded per-trade identity reads. CPU still evaluates every relevant trade/source; ledger history size, many strategies and many retained preparations can add work. Native pending-source reassessment intentionally remains complete. This is a lifecycle-read optimisation, not an audit or performance certification of every creation, booking, valuation or market-data endpoint. Futures/options/structured schedules remain informational at their existing supported tiers; no new lifecycle financial handlers are implied.

## Activation

Final focused rerun39 passed; earlier central regression group111 passed. Four final synthetic full comparisons and three final operating comparisons retain complete result/evidence equality. OpenAPI contract check, maintained local Markdown links and `git diff --check` pass (existing generated-file line-ending warnings only).

Owned API8000 restarted; frontend3001 healthy. Schema remains115 and retained trade, strategy-assistance, subscription and audit counts were unchanged by restart. Live authenticated BFF reads returned200 with17 bond maturities(0.481s),18 coupons(0.305s),8 FX maturity events(0.308s) and270 structured events(1.495s). Structured inspection also returned200. These are single local HTTP samples and include BFF/authentication overhead, unlike the paired calculation medians above. All8 FX rows retain their prior BLOCKED states; no blocked event was hidden or made actionable by the optimisation. The temporary verification session was revoked. No operating financial/configuration changes or Toolhive changes were made.

## Option follow-up: what the55 queries contain

A separate SQL-callsite trace reproduced the same13-contract/21-trade physical-option workload:55 queries and26 matching events. The sole `instrument_dates IN (...)` query already loads every selected option's dates. This is the full calculation count, excluding HTTP/authentication and recording-clock acquisition.

| Responsibility | Queries |
| --- | ---: |
| Tenant/user permission context resolved four times,5 queries each | 20 |
| Other strategy ownership/access, subscription, assistance and locks | 8 |
| Identify held option candidates | 1 |
| Current option/reference source batches, including1 date query | 7 |
| Ledger, historical identity and BOOKED evidence reads | 9 |
| Trade profile, allocation rules and annotations | 10 |
| Total | 55 |

Remaining improvement candidates are confirmed: the20 permission-context calls repeat the same resolution four times, current sources use separate bulk table reads, and option inspection reloads BOOKED payloads after the ledger has already read its lifecycle chains. The prior change removed per-trade growth;55 is not asserted to be an irreducible or fully consolidated endpoint budget. A follow-up can establish one appropriately scoped authority context, reuse already-validated booking source payloads and consolidate compatible reference reads. It must retain same-group strategy predicates, ambiguity/version detection, visibility, original BOOKED matching and a deliberate authority/transaction consistency boundary. Do not remove validations to meet an arbitrary query count.

Trace evidence is ignored `.superpowers/sdd/2026-11-11-lifecycle-readers/option-query-breakdown.json`; the isolated diagnostic test passed and its owned database was removed. No product implementation was changed by this analysis.

## Permission lookup timings

Measured against the existing first tenant/Ops user on local PostgreSQL port 15432, inside a strictly read-only transaction. One warm-up was followed by 20 groups of four sequential resolutions. Individual SQL timing includes driver/local round-trip time; full-resolution timing also includes result consumption and application work.

| Measurement | Median |
| --- | ---: |
| Tenant membership query | 0.979 ms |
| Tenant modules query | 0.935 ms |
| Group permissions query | 1.017 ms |
| User status query | 0.894 ms |
| Platform role query | 0.890 ms |
| Complete five-read resolution | 6.620 ms |
| Four repeated resolutions | 26.809 ms |
| Repeated three resolutions alone | 19.718 ms |

The first observed resolution took 31.941 ms; this is not a controlled cold-cache measurement. Warm local query medians are approximately 1 ms each. Removing repeated resolution could avoid about 20 ms in this measured workload, but does not explain seconds of page-loading delay. Remote database latency, larger memberships and concurrent load can change the result; these measurements do not establish their performance.

The four callers serve different enforcement purposes: initial tenant authority, selected-strategy access, enabled assistance selection and held-option candidate filtering. Reusing common data must retain all four decisions and the same-group action/scope requirement. No process-wide permission cache or removal of checks is proposed.

Machine-readable evidence is retained in ignored `permission-context-timing.json` beside the query trace. Neither this timing investigation nor this documentation checkpoint changed product code, permissions or operating financial data. The repeated resolution remains an open, lower-priority performance/maintainability finding; it was not fixed during the analysis.
