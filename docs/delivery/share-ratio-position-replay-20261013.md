# Reviewed share-ratio position replay

**Status:** Implemented bounded alpha; locally activated  
**Content type:** Delivery record  
**Owner:** Positions / valuation engineering  
**Last reviewed:** 2026-10-13

## Delivered

Original booked quantities, prices and execution dates remain authoritative and unchanged. `positions.reconstruct(..., splits=...)` replays reviewed positive share ratios chronologically into derived opening/closing quantities. Unchanged execution notionals enter the existing RAW-price value bridge. A 100-share holding with an 11:10 allocation becomes 110; a 2:1 split with a price halving produces no mechanical market P&L.

Supported scope is same-canonical-security EQUITY/ETF SHARES/UNITS: basic bonus allocations, splits/reverse splits, shorts, multiple dated actions, partial sales, flat/reopening histories and deferred recognition. Daily recognition uses the reviewed economic date; actual execution timestamps determine exposure and whether an acquisition precedes the action. Exact execution/action equality blocks. No original trade rewrite, automatic cost-accounting transaction or fabricated income/cash flow.

## Governance and safety

- Migration **86** adds append-only `secm.corporate_action_replay_decision`. Active platform reference administrators publish/revoke decisions through controlled operator functions; ingestion does not auto-approve them.
- Each approval freezes source version, ex-date/timezone/boundary convention, exact numerator/denominator and ratio, fraction policy, reviewer, source references and source/payload scope/hash. ANNOUNCED provider facts remain ANNOUNCED, with a separate reviewed decision.
- The latest source identity/version and latest decision visible at the information cutoff win. New source versions require review; cancellations cannot resurrect older announcements. Conflicting same-date/provider identities are not silently compounded.
- An unreviewed source cancellation, changed event type or moved date cannot erase an already-reviewed historical unit change. Its retained historical guard remains until a valid reviewed successor replaces it. A complete cancellation/non-occurrence adjudication workflow is not introduced.
- Approved action headers and child dates/effects become database-immutable. Corrections require a new source version; revocation never unfreezes historical sources. Before approval, legacy source-date/effect rows still lack independent recording timestamps: this is not a universal corporate-action bitemporal model.
- Tenant-private source systems and payloads are not shared across tenants. Existing strategy, price/FX data rights, operator identity and financial review controls remain in place. Public issuer links are review references, not a commercial provider-licensing certificate.
- Integer-only allocations block fractional entitlements, without rounding or inferring cash-in-lieu. Fractional units require an explicit reviewed convention. Rounded repeating ratios are not treated as exact.
- Freshness permission cannot mix a pre-action RAW mark with post-action holdings: a stale mark crossing the unit-change date blocks rather than manufacturing a normalized price.
- Unreviewed splits and unsupported mergers, spin-offs/security replacements still fail closed, including nominally flat histories.

## Financial evidence and UI

The `position-reconstruction-v2` projection hash contains reviewed events and before/after adjustments. Staged-line identity/evidence includes `splitEvents` and `splitAdjustments`, with event/review identity, timing, source snapshot and original ledger lineage. The economic engine remains `economic-position-pnl-v3`; no second calculator was added. No-action projections retain v1 identity.

The position inspector exposes **Share quantity adjustments**, showing exact server-returned quantities and review identity. Existing DISPLAY denial still suppresses quantities, prices, P&L, evidence and ledger links. Historical snapshots are not rewritten; use a fresh calculation/information cutoff after a new approval.

## Air Liquide research activation

The [issuer](https://www.airliquide.com/free-shares-attribution) specifies a basic one-free-share-per-ten allocation, delivered June 10, 2026. [Euronext notice listing](https://live.euronext.com/en/ajax/getNoticePublicData/FR0000120073-XPAR?alias=1&pageNum=1&pageSize=25) identifies `PAR_20260604_15132_EUR`, effective June 8. Reviewed October 13, 2026. Source-backed distinction: ex-date pricing units versus delivery. Project convention: reviewed local ex-date start for bounded economic-position replay, not settlement accounting.

The issuer distinguishes loyalty premiums and fractional rights. These require custody/registration/account entitlements and are **not** inferred. The October 2024 mock acquisition cannot satisfy two full registered calendar years for the 2026 loyalty premium. This delivery reconstructs its basic integer-share allocation only, not full corporate-action entitlements/payments.

Applied event `01a120af-e8c7-7730-837e-2b9527372d82`; review `01a136aa-193b-7787-a486-5f1265e8c4be`; ratio 1.1; economic date June 8; reviewed UTC boundary June 7 at 22:00 (Paris midnight).

The temporary July 2026 mock was replaced through the normal correction API by `c37f364b-9b75-432a-9d3b-2a6ab37f5d5e`, retaining the original October 15, 2024 quantity 100 and execution price 171.819996643066. Both earlier records remain superseded audit history; none was reactivated or rewritten. [Bounded restoration utility](../../scripts/restore_air_liquide_replay_fixture.py) checks fixture IDs, actor, subject, quantity, status and expected sequence before normal API submission.

Fresh normal API calculation for Strat Testing, October 7–8, FLEXIBLE_EOD v3, GBP:

- Attempt `01a136ae-297a-7bc1-8dda-c3ad4264bb69`: COMPLETED.
- Batch `01a136af-6a22-7e76-ba1d-4a9a520d7798`: **STAGED**, not published.
- Nine positions, three period executions, 38 scanned facts, 18 mark requests.
- Air Liquide opening/closing quantity **110**, frozen historical adjustment **100 → 110**, linked unchanged 100-share booking; its GBP market P&L is -50.959493659909 for this period.
- Total staged market P&L 18183.780538948516 GBP. Not an independent custodian reconciliation or full NAV/income sign-off.
- Calculation took 81.2 seconds; the 60-second client timed out but the worker completed. The retained attempt was read through the normal API; no duplicate calculation was started. Input-selection latency/asynchronous progress remain operational work.

## Verification

- Final pure reconstruction/action/FX/recognition/fixture checks: 64 passed, one DB-backed service test excluded from that pure command (includes two restoration-utility tests).
- Final affected disposable PostgreSQL suite: 109 passed in 45.84s, covering replay decisions/source immutability, successor/cancellation safety, staging, guards, FX, recognition, Yahoo events, repository and scaling. Never run against the operating DB.
- Valuation-workspace component tests: nine passed across three files; frontend typecheck passed. A new manual browser walkthrough is not claimed.
- Live normal correction and calculate/stage API acceptance passed after migration/restart. No official publication, permission broadening, full-suite run, commit or push.

Sequential author review caught and fixed the unreviewed-successor undo path through three failing regressions and a passing reviewed-successor case. This is not an independent code/security audit.

Remaining: action-decision review UI and cancellation adjudication; registered/loyalty/account-specific entitlements, cash-in-lieu, dividend/payment reconciliation, complex transformations, corporate-action dataset-rights certification for commercial deployment, checkpointing and input-selection/job performance. This is reviewed basic share-unit replay, not universal corporate-action support.

See [design](../superpowers/specs/2026-10-13-share-ratio-replay-design.md), [plan and ledger](../superpowers/plans/2026-10-13-share-ratio-replay.md), [review command](../../scripts/review_share_ratio.py) and [review manifest](../../data/air-liquide-basic-share-ratio-20260608.json).
