# Flexible/strict pricing policies

## Approved scope

STRICT uses explicit rules only. FLEXIBLE tries explicit rules first, then
configured defaults for unmatched subjects. A matched rule with missing eligible
data never falls through. Source priority remains subject to convention, rights,
calendar and information-time eligibility. Existing versions remain STRICT.

Defaults are real immutable rule rows, not hidden resolver heuristics. Their
series, basis, subject scope and freshness must be visible. Session-close is the
initial default template: LISTING / OFFICIAL_CLOSE / RAW / SAME_DAY / zero stale
sessions / FAIL. Latest available means an explicitly configured PRIOR_AVAILABLE
date rule within the chosen convention and a finite tolerance, not any timestamp
or any substitute fixing. No generic cross-convention last-price algorithm.

Valuation may accept explicitly bounded carry-forward under existing supported
RAW official-close economics. Closed-day previous expected sessions remain
current. No changes to trade recognition, settlement, licensing or instrument
coverage. Existing execution-price bridges and position lineage are retained.

## Execution plan

1. RED tests for modes/default precedence, validation, immutable API round trips,
   legacy idempotency, bounded freshness and missing explicit observations.
2. Add migration 75 and matching metadata; extend contracts and version creation;
   resolve explicit-before-default and freeze mode/origin in all outcomes.
3. RED UI tests; expose mode and editable defaults, bounded latest-date selection,
   preserve defaults on version cloning; improve readable price provenance.
4. Focused regression, contract regeneration, typecheck; apply additive migration
   and restart API; read-only acceptance. Document evidence and limitations.

## Execution ledger

Ruling: reuse the current approved feature checkout and do not commit or push —
preserves operating app changes and the user's sequential workflow.
Ruling: no full suite or subagents — explicit user preferences take precedence;
focused tests and self-review provide narrower assurance.
Ruling: latest available stays within a configured convention — prevents a daily
bar substituting for a required fixing; unsupported generic latest-price support
would require a separate precise timing contract.

Backend: mode/default precedence and versioned API implemented; initial isolated
run 26/26 passed. New valuation allowance test failed on the previous unconditional
CURRENT guard, then passed after bounded rule enforcement. New execution evidence
test failed on absent executionInputs, then passed after frozen-input persistence.

Frontend: mode/default and readable-price tests observed RED, then 16/16 passed.
Typecheck passed. Combined isolated backend regression: 62/62 passed across modes,
composite selection/API, source priority, valuation orchestration and staging.

Ruling: group executions once by position key — avoids introducing quadratic
evidence collection when enriching position results; no new financial calculation.
Ruling: priceEvidenceVersion in attribution identity creates a new retained version
when enriched evidence is first calculated, without rewriting historical results.

Local activation: migration 75 applied, API restarted; policy page and BFF HTTP200,
mode selector visible, old policy still STRICT / two explicit rules / zero defaults.
OpenAPI check and byte-identical TS regeneration passed; typecheck and 16 UI checks
passed after activation.

Expanded regression: 84 passed / one timing-dependent source-priority test failed.
Investigation measured database clock 0.46s behind host. Ruling: test the boundary
against the database's saved createdAt ± explicit interval, not host wall time —
deterministic evidence, no production selection behaviour weakened.

Complete: final expanded isolated regression **85/85 passed**, with 41 existing
SQLAlchemy/Starlette deprecation warnings. No full suite was run. Final author
self-review covered API authority/idempotency, defaults, missing-data and freshness
branches, immutable evidence and UI display guards; no critical/important findings
remain. Browser click-through signoff and independent review remain unperformed.
