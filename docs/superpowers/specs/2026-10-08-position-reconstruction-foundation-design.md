# Position reconstruction foundation

Status: implemented and targeted-tested on 2026-10-08; operating schema upgraded to revision 70 on explicit user instruction and verified. See `docs/delivery/position-reconstruction-foundation.md` for execution rulings and measured evidence; schema activation does not imply new browser or financial signoff.

## Intent

Replace valuation's historical-booking population with one reusable, price-independent position reconstruction foundation. Preserve the immutable booking ledger, historical knowledge cutoffs, frozen conventions, tenant isolation, corporate-action safety, and reviewed financial evidence. The legacy fortem_core open-position/holding-episode implementation informs requirements; its queries and pandas trimming are not the new architecture.

## Decision and alternatives

Recommended: reconstruct position state plus period movements, then let valuation consume that projection. This separates ledger truth, economic reconstruction, and market pricing.

Alternatives: trim historical trades to current holding episodes (less change but fragile around intraperiod closures/reopenings and mixed conventions); build persisted checkpoints immediately (faster reads but introduces invalidation and historical-correction complexity before the reconstruction is proven). Neither is selected for this delivery.

## Scope and contracts

Create a top-level `positions/` package independent of `valuation`, market-data providers, HTTP, and pandas. Its pure engine consumes typed ledger facts and emits a deterministic projection for either AS_OF or PERIOD mode. A database repository supplies facts; product adapters interpret frozen booking conventions. Valuation remains responsible for pricing and P&L, not the position engine.

`ProjectionRequest` contains tenant_id, strategy_id, closing_cutoff, information_cutoff, optional opening_cutoff, and mode. All timestamps are aware UTC. AS_OF requires no opening cutoff; PERIOD requires opening < closing. Events are selected at economic time <= closing and recorded time <= information. Unlike the current valuation API, the foundation may represent an incomplete historical view with information < economic cutoff; it must label that basis, not pretend all events are known. The existing API cutoff constraint remains unchanged in this delivery.

PERIOD opening state includes effects <= opening; period effects are (opening, closing]. Each effect retains trade/event identifiers, effective/recorded times, signed quantity, and frozen conventions. Records beyond either applicable cutoff do not participate. Reconstruct corrections using lifecycle history, not present-day active flags. Retain existing fail-closed behavior for economically unsupported in-period cancellation/supersession or other lifecycle transformations; this foundation does not silently treat them as sale trades.

`PositionKey` includes tenant, strategy, traded subject UUID, quantity unit, quote currency UUID, and a fingerprint of economically relevant frozen conventions (product basis, unit multiplier, quote factor). Initially a subject is the exact listing/traded subject, not automatically its canonical parent. Different listings, currencies or conventions cannot be netted without an explicit conversion policy. A definition-version change alone does not necessarily create a new economic bucket; the fingerprint is of the relevant frozen values. Keep all original definition IDs in lineage.

`PositionProjection` includes opening/closing buckets, period execution effects, lifecycle evidence, required safety inputs, lineage, cutoffs, engine version and input hash. Quantities are native signed quantities per compatible bucket; normalised units are calculated explicitly by the product adapter. Never use float, ROUND(quantity), an epsilon, or a numerical population cap. Deterministic ordering uses effective time, event-kind dependencies, per-trade sequence and immutable identifiers. Cross-trade ties have no effect on aggregate results; do not infer a global chronology from trade UUIDs.

## Relevance and marking

AS_OF needs nonzero closing positions and their reconstruction lineage. PERIOD needs nonzero opening positions, all supported period movements, and nonzero closing positions. Fully closed pre-opening episodes do not become financial calculation lines or require marks, though their facts may have been read to establish state. A period with no positions/movements is a legitimate evidenced zero result, distinct from missing/incomplete ledger evidence.

Market marks are required only for nonzero opening/closing value buckets, at their respective cutoffs. Period executions retain execution price and execution FX requirements even when closing position is zero. Closed round trips do not require a closing market price. Corporate actions and unknown economic effects must be evaluated over relevant exposure intervals, including intraperiod closed positions, before accepting any net-zero shortcut. The existing corporate-action guard is retained or extended conservatively, never weakened through netting. Do not use original old trade dates to claim uninterrupted exposure across a flat interval; evidence ambiguity blocks or conservatively guards.

Holding episodes are diagnostic lineage, not the authoritative relevance rule. A long-to-short reversal is a boundary even if cumulative quantity never equals zero; no FIFO/LIFO cost allocation is needed for the aggregate period bridge. Unsupported corporate-action quantity/identity transformations remain blocked. No settlement, cash ledger, income, fees, tax, derivative valuation, multi-currency valuation or NAV expansion is included.

## Valuation and attribution

For the supported single-currency equity/ETF scope:

`market P&L = closing securities value - opening securities value - signed period execution value`.

Values use each compatible bucket's frozen unit multiplier and quote factor. Buy execution values are positive and sells negative. Example: opening zero, buy 2 at 100, sell 2 at 110, closing zero => P&L 20, with no opening/closing market marks.

Result ownership becomes position bucket plus calculation period, not arbitrarily a historical trade. Store position-level immutable attribution and separate execution/ledger lineage links; do not invent a trade ID to fit the existing mandatory trade-owned schema. Preserve v1 results and review history readably; new runs use a versioned v2 method/result format. Existing permissions, publication checks, idempotency, transaction snapshot, recovery and financial immutability remain applicable to both result formats.

The first v2 market component decomposition is single-currency PRICE; FX/CROSS are zero, not estimated. Grouped attribution must reconcile exactly with the period bridge. Per-trade realised/unrealised cost-basis accounting is not promised. For fully closed pre-opening positions, no v2 attribution lines are manufactured merely to cancel one another.

## Scaling

First prove an uncapped reference reconstruction with deterministic chunked database reads in one stable transaction. Count/timing telemetry distinguishes facts scanned from positions/lines priced. No claim of bounded historical I/O: facts must still be read to establish state. Database filtering/indexing and later immutable, versioned checkpoints optimise this same contract, not create a second reconstruction algorithm. Checkpoint delivery is deferred until backdated corrections and knowledge-cut invalidation rules are designed and benchmark evidence warrants it.

## Acceptance and rollout

Pure tests first: longstanding holdings; flat before opening; round trip; closure/reopening; partial disposal; short/reversal; fractional quantity; mixed conventions; exact boundaries; same-time trades; historical corrections; knowledge cutoff; malformed/missing lifecycle; genuinely empty population.

Then disposable DB/API tests: tenant isolation, uncapped reads beyond 1,000, deterministic batching, snapshot consistency, safety on closed intraperiod exposures, rights revocation, immutable v1/v2 history, authoritative publication replacing the old result population atomically, duplicate retry and permission-aware result rendering.

Compare v1 and v2 only on v1-supported scenarios; use independently asserted bridge totals for cases v1 cannot represent. No hidden parallel production engine or fallback. Activate v2 after targeted acceptance; preserve read access to historical v1 evidence and remove its execution path. No full-suite rerun by default, operating-data mutation, automatic commit/push, or subagents.
