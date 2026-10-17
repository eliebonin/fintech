# Query efficiency without narrowing functionality

Status: bounded query remediation completed and verified. Sequential execution in
the existing dirty checkout; broader scale limits remain in the delivery report.

## Invariants

Preserve complete histories, correction/information cutoffs, every policy/date
convention, provider priority, layered licensing, tenant/private-parent visibility,
strategy permissions and frozen financial evidence. No trade caps, global planner
settings, cross-request authorization caches or operating-data changes.

## Work and verification

1. Select candidate series before observations; compare exact selected evidence
   and explain the emitted SQL. Keep every eligible observation, not a top-one shortcut.
2. Reuse stable resolution reads only inside the runner's existing repeatable-read
   calculation transaction; clear before staging and on retry/exception.
3. Batch dataset rights evidence; preserve the existing pure rights evaluator.
4. Batch history source health and load only disclosure-relevant evidence and
   summaries, not complete review/lineage views. Retain current display checks.
5. Batch tenant/platform access overview reads without changing effective permissions.
6. Remove redundant catalogue visibility work without weakening listing-parent checks.
7. Batch repeated holdings definition and forward-currency reads where safe.
8. Run focused disposable-database regressions, record query counts/plans and
   maintain a delivery report with remaining limitations. No full-suite requirement.

The baseline diagnosis found a two-row price lookup scanning over two million
unrelated observations (~0.77s), 104 SQL statements for three result-history rows,
40 statements for a four-user/four-group access overview, and repeated four-query
rights loads per dataset/activity. These are local diagnostics, not load benchmarks.

## Execution ledger

- Ruling: keep the existing per-user permission resolver. The safety reviewer
  rejected replacing permission-summary computation, and the user asked about
  consequences rather than approving that rewrite. Batch only roster reads;
  some per-user authority reads deliberately remain. Cost: less speedup, no new
  authorization algorithm. Strategy action/scope enforcement is unchanged.
- Tasks 1–3 implemented; first focused run passed the rights and candidate work
  budgets. A wider run caught an ad-hoc rule without a stored ID; fixed the new
  series-cache key to preserve that existing caller contract.
- Task 4 minimal history projections and batched source-health status implemented;
  focused tests pass disclosure revocation and late-ledger-change checks.
- Task 6: initial visibility-plan candidates were insufficient, and the safety
  reviewer required explicit approval. User approved guarded catalogue-query
  restructuring. The metadata projection and ACTIVE node sets are now materialized
  within each SQL statement; existing scope/parent/licensing predicates remain.
  Synthetic volume-plan and original-predicate equivalence tests pass.
- Task 7: user approved forward evidence batching provided it introduces no
  feature cuts. All proofs are loaded in complete chunks, with unchanged per-fill
  checks; populations bind request and transaction. The 502-fill boundary regression
  verifies no total cap. Holdings definitions and latest detail marks are batched.
- Ruling: retain per-batch current disclosure checks instead of the proposed union
  authorization optimization rejected by safety review. Cost: some repeated checks
  remain, but no new cross-dataset authorization decision or cache is introduced.
- Ruling: do not invent checkpoints or rewrite the complete access-matrix/explorer
  history in this fix. Record their remaining scale limits separately; no cap or
  omitted history is an acceptable substitute.
- Verification uses disposable databases only. No operating migrations or planner
  settings; no commits, pushes or subagent work are included in this task.
- Final review: author self-review, sequential as requested. Found and fixed
  literal-UUID visibility compatibility; retained the existing authorization
  resolver and per-batch display checks. Final expanded cohort: 232 passed and
  one stale 422/403 assertion; assertion corrected without changing enforcement,
  then the final query/policy cohort passed all 25 tests. Earlier storage/assurance
  fixture-isolation fix passed 19 tests. Full evidence, timings and limits:
  [delivery](../../delivery/quality-reviews/2026-10-16-query-efficiency.md).
