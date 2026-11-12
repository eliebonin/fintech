# Lifecycle checkpoint and local shutdown — 12 November 2026

This checkpoint collects the previously unpushed lifecycle/domain, UI, generated-contract and local PostgreSQL configuration work on `codex/pnl-ops-review`. The user requested updated documentation, a commit/push, then shutdown of project development services and its database container. No merge to main, force push, container deletion or volume deletion is part of this request.

## Delivered and documented

- [Local database port recovery](../local-postgres-port-recovery-20261111.md): PostgreSQL uses15432, preserving existing data and avoiding Toolhive ports. Private configuration stays ignored.
- [FX-forward maturity discovery](../fx-maturity-worklist-20261111.md), [coupon information](../coupon-notifications-20261111.md), [futures deadlines](../future-lifecycle-notifications-20261111.md), [option deadlines](../option-lifecycle-notifications-20261111.md) and [structured observations](../structured-informational-notifications-20261111.md) retain their explicit financial/information-only boundaries. Additive migrations113–115 are included with their contract changes.
- [Structured source batching](../structured-lifecycle-batch-reads-20261111.md) and [other lifecycle reader batching](../lifecycle-reader-batching-20261111.md) preserve full source/permission/allocation checks. The latter records exact option query breakdown and local permission timings; further context/evidence consolidation remains pending, not implemented.
- [Event-column and assistance wording](../lifecycle-worklist-20261105.md): instrument and event columns are separate; repeated subscription-ceiling labels are removed from operational summaries but retained in management settings and backend enforcement.
- [Business-day badges](../lifecycle-business-day-colours-20261111.md): configured calendar/holiday evidence, explicit weekday estimates and unknown coverage remain distinguishable. Upcoming information-only notices receive proximity colours; past informational/completed entries are neutral.
- [Production-mode comparison](../local-production-frontend-20261112.md): successful isolated build, authenticated browser hydration, measured HTML/data response times and subsequent production stop. Generated type imports use the normal dev output path, not a retired acceptance output.

## Verification scope

The complete frontend suite passed:1182 tests across252 files. TypeScript and deterministic API export checks passed. The additional focused disposable-database run passed43 tests covering local database configuration, Yahoo CLI guards/operations, index-universe seeding and workload admission; its owned database was removed by the runner. Prior scoped lifecycle backend and browser results remain linked in the delivery records; they are not represented as a new complete Python-suite sign-off. The exact staged files were checked for private configuration/credential leakage, missing local Markdown targets and whitespace. No private environment files, database exports, logs, benchmark artifacts or secret files are committed.

## Shutdown boundary

After a successful push, stop only the verified project-owned dev frontend3001 and API8000, then stop `platform-postgres`. Confirm those ports are closed, the database container is stopped, its mounted persistent volume still exists and Toolhive's running-container inventory is unchanged. Production3008 was already stopped. Do not stop Docker Desktop, remove images/containers/volumes or stop Toolhive. The observed stop/push receipt is retained in ignored task/process metadata rather than treating this dated source checkpoint as a live service-status page.
