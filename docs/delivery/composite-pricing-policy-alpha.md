# Composite pricing policies — alpha delivery

**Owner:** Market-data engineering  
**Date:** 2026-10-07  
**Scope:** Market-data input selection, configuration and reproducible evidence. Not valuation, P&L, settlement or accounting.

## Delivered behaviour

One tenant-shared or strategy-scoped, immutable policy version can combine different market conventions. A single UTC **information cutoff** controls eligible receipts, publications and revisions; the **pricing target** is calculated separately for each rule.

For example, on 2026-08-28 a synthetic mixed-market acceptance fixture selects London 16:30 / New York 16:00 / Paris 17:30 closes and a separate London 16:00 fixing. The targets are respectively 15:30 / 20:00 / 15:30 / 15:00 UTC, with one information cutoff at 22:00 UTC. Before the US close the US input is unresolved while the other completed targets can be selected.

- `SESSION_CLOSE`: uses the explicitly selected listing's venue/calendar and dated close, including early closes. A canonical instrument does not cause an automatic listing guess. Series `market_date` is used, not a source daily-bar opening timestamp. Marks reported before their session completes are not accepted as closing marks.
- `NAMED_FIXING`: requires exact `FIXING_CODE` series identity, matching series cut, non-conflicting observation cut and the actual fixing timestamp. Daily-bar timestamp semantics are rejected. A Yahoo daily FX bar cannot become a London fixing merely by relabelling the policy.
- `EXPLICIT_TIME`: selects eligible timestamped observations at or before the named local target; rejects daily-bar timestamp semantics.
- `LEGACY`: preserves existing date-only behaviour, including existing weekday arithmetic. New managed versions cannot silently apply unsupported composite time/basis fields in this mode.

Rule specificity is exact series → exact subject → venue plus instrument type → venue → instrument type → default, followed by rule sequence. A missing specific rule never falls through to a broader one. Dataset and value-basis filters are explicit. New conventions preserve database decimal precision.

## Calendars and missing data

Subsequent delivery: [Tenant fund and strategy calendars](tenant-fund-and-strategy-calendars-alpha.md) adds version-pinned tenant schedules, strategy/NAV expectation decisions and `NAV_DATE` for fund-session lag/staleness. Governed reference holidays now participate alongside dated sessions; conflicting holiday/open-session evidence is unresolved. The earlier four conventions and migration67 activation recorded below remain historical delivery evidence, not the current schema head.

Dated governed sessions take precedence. Missing calendar coverage is an explicit exception, never a weekday guess. Without governed sessions, supported listing MICs may use pinned/versioned exchange schedules for NYSE, Nasdaq, LSE, Paris and Amsterdam, labelled **non-authoritative comparison evidence**. Unsupported MICs and empty unrelated custom calendars are not assessed.

Known closed dates roll to the previous session; that does not itself count as a stale price. Missing open-session data follows SAME_DAY / PRIOR_AVAILABLE / FIXED_LAG, trading-session lag and the stated staleness limit. FAIL/WARN never fabricate a value; MANUAL_OVERRIDE records a need for override, not a new override workflow. Ambiguous and nonexistent local DST times fail explicitly. New selection/calendar lookback is bounded to 1,100 calendar days; absence beyond assessed coverage is unresolved, not certified complete history.

## Configuration, API and UI

Open **Market data → Pricing policies** (`/market-data/policies`). Inspect saved versions, create a new version from a saved configuration, add/remove rules and preview explicit listing/reference UUIDs. Preview uses the saved version, not unsaved edits. IDs distinguish duplicate legacy option names. This alpha uses exact UUID entry for subject/series filters and preview subjects; a searchable instrument picker is a later UX improvement. Subject-type-only filtering is available through the API but not exposed as a separate editor control.

MARKET_DATA members may inspect and preview. MARKET_DATA tenant administrators may create versions. The API rechecks tenant membership/module authority; strategy ownership/effectiveness, subject visibility (including a listing's private parent) and configuration references are validated. Existing active-policy and snapshot routes also enforce the module boundary.

Endpoints:

- `GET /v1/market-data/valuation-policy-options`
- `GET /v1/market-data/valuation-policies?valuationDate=...`
- `GET /v1/market-data/valuation-policies/{policy_id}`
- `POST /v1/market-data/valuation-policies` — stable `Idempotency-Key`; exact replay returns the same version, changed-payload reuse is 409; a fresh submission for the same code creates the next version.
- `POST /v1/market-data/resolution-preview` — bounded 1–50 distinct subjects, no snapshot/price/trade writes.
- Existing snapshot POST/GET — frozen `pricingEvidence` is exposed; legacy null evidence is not reconstructed.

Version creation is atomic, attributed, tenant/code serialized and protected against later policy/rule mutation. Legacy configurations remain distinguishable. Snapshot creation preserves historical idempotency fingerprints when optional strategy context is absent. The ops console uses generated API contracts and the selected tenant, not a demo fallback or cookie-losing internal loopback for snapshot detail.

## Rights and remaining prerequisites

No licence or activity grant was activated. Selection remains NON_DISPLAY consumption even if data can be displayed. The Yahoo personal dataset's existing rights remain unchanged; this delivery does not make it eligible for valuation consumption or grant commercial/redistribution rights.

Still required for actual valuation inputs: appropriately permitted NON_DISPLAY data, genuine named FX fixing feeds/identities, reviewed historical source continuity, chosen adjustment basis/corporate-action treatment, and authoritative calendar governance where required. Real provider fixing ingestion is not part of this delivery. Policy creation does not resolve those prerequisites or implement valuation/P&L.

## Implementation and verification evidence

Migrations 66–67 are additive. Existing snapshot evidence remains null; new managed-policy audit timestamps do not claim historical creation evidence for legacy rows. No operating policy seed, price repair or trade creation was performed.

Lightweight temporal tests ran RED/GREEN before SQL changes; real isolated resolver/API tests cover early closes, closed dates, unknown calendars, missing specific rules, premature marks, mixed US/UK/Paris/FX targets, fixing identity/time/cut conflicts, value basis, decimal precision, readonly preview, idempotency, immutable versions, permissions and legacy replay. Frontend tests cover payloads, permissions, selected-tenant snapshot reads and stable keys. Final full regression results are recorded below.

Local operating migration is `20261007_67`. Before/after counts: trades 9; lifecycle events 9; strategies 50; cash accounts/balances 0; observations 1,358,477. Browser acceptance opened the page, loaded a legacy policy and obtained a read-only PARTIAL preview with no client errors; this is not a claim that its sample inputs are valuation-ready. Configuration writes were verified in disposable test databases, not operator data.

Review is a separate **author self-review**, not independent signoff, in accordance with the requested sequential workflow. It added regression coverage and fixes for premature session marks, unrelated empty calendars, conflicting fixing cuts, module authority and unsupported composite fields in managed legacy rules. The first full run also exposed a legacy partial-rule dictionary compatibility regression; the correction passed the existing rights tests before the final full rerun.

Final verification:

| Check | Result | Evidence |
| --- | --- | --- |
| Final composite resolver/API plus existing rights regressions | 26 passed, 64.55s | `logs/composite-policy-rights-and-review-green.log` |
| Full frontend suite | 124 files, 593 tests passed, 28.74s | `logs/composite-policy-frontend-final-2.log` |
| Ops-console and generated contract typechecks | Passed | `logs/composite-policy-types-final-2.log` |
| OpenAPI export consistency / Git whitespace | Passed | Export check and `logs/composite-policy-whitespace-final.log` |
| Full isolated Python rerun | 1,096 passed, 488 warnings, 827.04s; exit 0 | `logs/composite-policy-full-python-final.log` |

The warnings include SQLAlchemy deprecation and Pydantic field-metadata warnings; a passing suite is not a claim of warning-free code. All database regression execution used the disposable-database runner, which exited successfully and cleaned up its owned test database.

The running API already uses the repository virtual environment, which includes the required pinned calendar package. Its underlying Windows Anaconda child process is not evidence of a different environment. No app restart or global dependency installation was necessary.

## Sources and design references

[NYSE auction conventions](https://www.nyse.com/trade/auctions) and [LSEG WMR fixing conventions](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks) informed the separation of exchange closing sessions and named FX fixings. They do not grant data-acquisition rights. Installed Next.js route-handler and server/client-component guidance informed server-derived tenant context and bounded BFF routes.

Approved [spec](../superpowers/specs/2026-10-07-composite-pricing-policy.md) and [execution ledger](../superpowers/plans/2026-10-07-composite-pricing-policy.md).
