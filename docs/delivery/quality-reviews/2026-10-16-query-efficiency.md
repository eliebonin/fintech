# Database query-efficiency remediation

**Status:** Implemented and verified within the reviewed scope  
**Owner:** Engineering  
**Reviewed:** 2026-10-16  
**Scope:** Existing database read paths; no financial-methodology or access-policy change.

[Implementation plan and rulings](../../superpowers/plans/2026-10-16-query-efficiency.md).

## Changes and preserved behavior

- `security_master_schema/market_data_resolver.py`: identify matching active
  subject/type/dimension series before fetching observations. The observation
  query explicitly constrains series IDs, using existing indexes. Every eligible
  candidate remains available to ranking: no top-one shortcut, trade cap, planner
  disable, provider restriction or loss of historical/current entitlement,
  correction-vintage, information-cutoff, official-close or date-rule predicates.
- `valuation/runner.py`: transaction-local resolution reuse during `calculate`
  inside its existing REPEATABLE READ transaction. Clear reuse before staging;
  each serialization retry gets a fresh snapshot/scope. Publication/current-access
  checks retain their own behavior.
- `market_data/rights.py`: one population read of profiles, datasets, requirements
  and grants instead of four reads per dataset/activity. The original conjunctive
  evaluator still decides rights. Exact display requests restrict the rights
  sweep to their datasets; unprofiled legacy behavior is unchanged.
- `valuation/storage.py`, `ledger_impacts.py` and the attempts endpoint: batch
  headers/source-health status and project only the evidence needed by the
  existing disclosure guard. Do not load lineage, review events or financial
  lines just to show a headline. Missing/foreign headers fail closed. Every batch
  still receives the existing current display check; no union-based authorization
  shortcut was introduced. Detail/publication keep full views and change logs.
- `security_master_schema/access_management.py`: batch tenant group grants,
  strategy assignments and roster memberships; keep the existing per-user
  permission resolver. Platform overview reads tenant entitlements/users once,
  retaining existing module-resolution and platform-authorization functions.
- `apps/reference_api/market_data_workspace.py` and `repository.py`: separate
  catalogue metadata from selective licensing predicates and materialize ACTIVE
  node ID sets within the SQL statement. Tenant/private-parent visibility, source
  rights, full count-before-page, search and permitted latest-mark rules remain.
  The legacy instrument-detail latest-three-per-series projection now uses one
  lateral query, preserving that existing per-series display window.
- `positions/holdings_repository.py`: parse retained events once and fetch cash
  definition types together per keyset page. Never substitute current terms or
  skip earlier flat episodes. Forward currency labels reuse a per-pair local read.
- `valuation/forward_measures.py`: load retained forward trades/BOOKED events in
  500-ID chunks with no total cap, then run unchanged per-fill normalization and
  agreement/quantity checks. Populations bind the complete request and transaction.
  Preview batches its selected forward buckets; pre-pagination flat checks batch
  only flat forward buckets. Both-leg and mixed-agreement safety remain intact.

## Measured evidence

Operating-data probes used explicit PostgreSQL READ ONLY / REPEATABLE READ
transactions with statement/lock budgets, then rolled back. No operating data,
statistics, indexes, source rights or planner settings were changed.

| Probe | Previous | Updated | Comparison boundary |
| --- | --- | --- | --- |
| TTE two-observation candidate SELECT | 898.863 ms; 1,349,890 shared hits | 5.933 ms; 1,683 hits | Same snapshot, predicates and two complete returned rows; only the explicit matching-series constraint differs |
| Catalogue service, 25 rows / 1,688 visible series | Earlier diagnosis: 23 SQL, 0.733 s | 6 SQL, 0.504 s | Dated local service samples, not a load benchmark |
| Catalogue page EXPLAIN | Earlier diagnosis: ~398–415 ms, 143,569 shared hits | 255.629 ms, 50,677 hits | Local plan samples; cache effects are not controlled |
| Three history financial/disclosure projections | 58 SQL, 0.155 s after the rights optimization | 42 SQL, 0.109 s | Same snapshot; identical health and financial/denial outputs; excludes common history/filter/auth queries |
| Tenant overview, 4 users / 4 groups | Earlier diagnosis: 40 SQL | 31 SQL, 0.041 s | Permission resolver deliberately retained |

The eleven-position monetary read phase took **1.135 s / 338 SQL unscoped** and
**0.528 s / 239 SQL scoped**, with identical complete output/evidence on the same
snapshot. This excludes HTTP authorization, UI/network and fresh release checks;
it is not a promised page-load time. Earlier nine-position and 42-second samples
are historical comparisons, not identical-population speedup ratios.

The synthetic catalogue planner fixture updates statistics only in its owned
disposable database after inserting 200 nodes/series. A simple IN rewrite and
materializing only ACTIVE nodes were insufficient: the metadata join still
rescanned. The final projection fixes both sources of repeated master scans.

## Verification

`tests/test_query_efficiency.py` checks budgets, original visibility equivalence,
tenant/strategy separation, foreign/incomplete disclosure, rights revocation,
late source changes, full forward proofs and the 502-fill chunk boundary.
The 36 subject/parent scope combinations are checked for two tenants against the
original EXISTS predicate; inactive parents remain hidden. Existing tests cover
policy conventions, provider ranking, source packages, corrections, maturity,
partial closure, mixed agreements and cancellation.

Verification record (overlapping counts must not be added):

- A 23-module affected run: **202 passed, 1 failed**. The failing split-safety
  fixture deleted all observations on a date, including earlier tests' retained
  snapshot sources. Replaced global deletion with an owned series; the storage
  and measure-assurance rerun passed **19 tests**. No production constraint changed.
- The expanded 27-module cohort: **232 passed, 1 failed** in 177.20 seconds.
  The failure was an old policy-API expectation of 422 for an unknown strategy;
  the pre-existing central strategy guard correctly returns 403. Updated only
  that assertion, adding a no-policy-created check. No authorization code changed.
- Final rerun of `test_composite_policy_api.py` and `test_query_efficiency.py`:
  **25 passed** in 19.80 seconds, covering the previously failing case and all new
  efficiency regressions. An additional **36-test** query/domain-contract/read-scope
  run passed before the final literal-UUID compatibility regression was added.
- Self-review caught the visibility helper's literal UUID callers in policy
  validation. A failing regression reproduced the incompatibility; parameterized
  UUID coercion fixed it. Both literal and column callers are covered in the final
  rerun; policy lifecycle and current-rights snapshot checks ran in the wide cohort.
- Whole OpenAPI SHA256 remains
  `f968cfe14baef5eaaf2f526ac5ad90585a7193dffed0cdfe1a339c87e45d093c`.
  Changed Python files parsed, report links resolve, and scoped `git diff --check`
  passed. The wide run emitted one existing Starlette/httpx TestClient deprecation
  warning. No full repository or frontend suite was run for this backend-only task.

The catalogue HTTP budget is 19 on this checkout with both the old
and new rights loaders; the earlier 17-query ceiling predates current request
controls. The regression retains constant counts across page sizes and compares
the previous rights loader independently.

Confirmed final focused command, from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
./.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_composite_policy_api.py tests/test_query_efficiency.py -q -p no:cacheprovider --tb=short
```

## Deliberate limits and remaining work

- No new market-data, product, date, quantity, booking, accounting or valuation
  restrictions were introduced. No schema migration is required.
- Per-user effective permission resolution remains; replacing it was not approved.
  Access-matrix/preview still materializes the full user × strategy explanation.
- Complete ledger-history reconstruction still grows with history. Versioned
  checkpoints need correction/information-cutoff invalidation; none was improvised.
- Full explorer history still performs per-series count/page/chart reads. The
  compact catalogue and instrument-detail latest marks are the batched paths.
- Current disclosure remains per batch/context, not a cross-request permission
  cache. Large result pages can therefore still perform repeated current checks.
- Representative concurrent/cold-cache load and memory benchmarks remain pending.
  These optimizations do not establish production capacity or financial sign-off.
- No operating migration, seed, write, provider call, service restart, commit or
  push; no frontend change or new browser acceptance was included.
- Activation is a normal API reload/restart; this task did not restart services.
