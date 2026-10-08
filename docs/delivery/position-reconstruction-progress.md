# Execution ledger — position reconstruction foundation

Plan: docs/superpowers/plans/2026-10-08-position-reconstruction-foundation.md
Spec: docs/superpowers/specs/2026-10-08-position-reconstruction-foundation-design.md

## Setup and rulings

- User approved implementation on 2026-10-08; sequential execution and focused tests remain binding.
- Ruling: continue in the approved current feature checkout (`codex/enriched-trade-booking`), preserving existing uncommitted work. A new worktree would omit the uncommitted foundation dependencies. No commits/pushes or operating migrations.
- Ruling: maintained delivery ledger replaces shell-only skill scratch scripts on Windows; retain it rather than deleting the execution record. No subagent review per user preference; final review will be an explicit author review.
- Pre-flight: tasks 1/2 share LedgerFact/ProjectionRequest; tasks 1/3 share PositionProjection; tasks 3/4 share typed position result; tasks 4/5 share versioned batch DTO. Scope and cutoff fields must remain identical across adapters.
- Ruling: v2 result ownership must be position-based; no synthetic trade owners. Additive schema and dual-format historical readers are required before production dispatch changes.

## Progress

- Task 1: complete — 19 pure reconstruction checks passed after absent-package RED; contracts and exact cutoff-aware reference projection implemented.
- Task 2: reader implemented; 3 disposable DB checks passed. Initial run reached collection after implementation, so this is a GREEN-only adapter check, not claimed RED→GREEN. Additional reader regressions pending.
- Task 3: pure grouped bridge implemented; 37 reconstruction/bridge/economics checks passed after absent-bridge RED; orchestration and safety integration pending.
- Task 4: initial schema/storage bundle 18 passed (position and legacy storage). Additional terminal-lineage INSERT test reproduced a real gap; RUNNING-parent gate added to the migration, awaiting re-verification.
- Task 5: UI RED 2 failed/3 passed (missing position/empty presentation), then GREEN 11 passed across component/page/proxy. HTTP RED confirmed old runner returned TRADE_V1; dispatcher now switched to v2, awaiting GREEN.
- Task 6: pending.

- Ruling: extend existing immutable attribution/review tables with explicit mutually exclusive position/trade ownership, rather than create a parallel financial storage system. Add a separate immutable trade/event lineage table. This preserves existing review/publication controls and historical v1 readers; cost if wrong: additive schema correction, not ledger mutation.
- Root cause: lineage UPDATE/DELETE protection did not prohibit later INSERT. The completed parent attempt is now the insertion boundary, with a database lock preventing concurrent completion/append races.
- Integration run: 28 passed/3 failed. Empty-policy RED was already addressed after that worker imported code. Two existing API failure-path fixtures assumed an empty strategy must fail; updated them to deliberately missing-policy inputs, preserving failure-status/diagnostic assertions. Valid empty output has its own acceptance checks.
- Cutover: production calculate now has only the v2 path. Frozen v1 replay/calculation lives under tests/ solely for equivalence and historical-reader verification. Old result rows are not changed.
- Benchmark with tracemalloc: 201/2,001/10,001 scanned facts each produced one position, one execution and one mark requirement; elapsed 0.1499/1.4073/13.3092 seconds and peak 1.48/10.71/40.54 MiB. Historical scanning/materialisation remains linear and is explicitly not checkpoint-optimised.
- Final author review: malformed no-mark Decimal evidence reproduced an InvalidOperation leak (3 passed/1 failed); now becomes permission denial. Old flat pre-opening episodes were unnecessarily copied into current result lineage (19 passed/1 failed); financial lineage now retains the unclosed opening episode and all period executions. Indexed staging avoids repeatedly constructing membership sets/scanning the whole ledger for each line.
- Final author review: raw historical +10/-10 across a split can appear flat before the P&L period (RED reproduced). Ruling: guard ALL historical raw exposure intervals before trusting any zero boundary. These intervals do not request historical market marks or create financial lines. Cost: histories with unresolved unit-changing actions remain blocked until replay is implemented, even if their raw quantities appear closed. This preserves the earlier corporate-action fail-closed safety.

## Final task outcomes

- Task 1: complete; pure reconstruction, scoped identities, deterministic cutoff evidence and relevant financial lineage.
- Task 2: complete; bounded keyset repository, uncapped population, scope/time/query-count checks. Stable transaction behavior rechecked in the shared runner regressions.
- Task 3: complete; grouped bridge, minimal mark requirements, all-history corporate-action safety and v1 equivalence controls.
- Task 4: complete; revision 70, explicit position ownership, immutable terminal lineage, historical readers, complete authoritative replacement and zero-result publication.
- Task 5: complete; one v2 runner path, counters, scoped API acceptance and dual-format review UI.
- Task 6: complete; performance evidence, v1 calculation/replay moved under tests, delivery documentation and targeted signoff.
- Final pure run: 75 passed/0.77s. Final DB/API/migration run: 67 passed/8 existing warnings/88.26s, exit 0/cleanup. UI 11 passed, final TypeScript exit 0, whitespace exit 0. Full suite not rerun.
- Final review: author self-review only per sequential/no-subagent instruction. No unresolved critical findings in the targeted scope. Deferred scaling and existing ETF subtype-version linkage limitation are explicit in the delivery report.
- Activation: operating Alembic current read-only verified 20261007_69; migration 70 NOT applied. No operating financial writes, restart, commit or push.

## Operating schema activation — 2026-10-08

- User explicitly requested migration 70. Verified target `fortem_secm` and starting revision `20261007_69`, then ran `alembic upgrade 20261008_70` successfully.
- Fresh `alembic current`: `20261008_70 (head)`. Verified the attribution/review ownership columns, four ownership/version constraints, and both enabled lineage protection triggers.
- Before/after counts: trades 9, attributions 0, review batches 0; new lineage table empty. No financial calculation/publication, app restart, commit or push. This supersedes the earlier pending-activation record, not the prior test evidence or browser-signoff limitations.
