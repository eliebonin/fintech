# Regulatory Reporting Implementation Plan

> Execute sequentially with the executing-plans workflow. The user authorised
> implementation and previously opted out of plan approval and subagents.

**Goal:** Deliver a scoped legal-entity, execution-assessment, review and immutable
preparation-export workflow inside Regulatory Reporting.

**Architecture:** A dedicated regulatory_reporting package owns pure assessment,
contracts and retained records. The audited API enforces module/action/strategy
access; the console uses its existing BFF/context transport. An additive migration
registers the module without granting operational access.

**Tech Stack:** Python, Pydantic, SQLAlchemy Core/PostgreSQL, FastAPI, Next/React.

**Spec:** [workspace specification](../../delivery/specifications/regulatory-reporting-workspace.md).

## Global constraints and review focus

Preserve the dirty checkout, neutral naming, Decimal precision and current audit
boundaries. No production submissions or operating trade changes. Focus on cross-
tenant/strategy guesses, incomplete mapping, source changes after review, repeated
commands/downloads after revoked access, and human overrides surviving refresh.

## Tasks

- [x] 1. Add focused failing tests for assessment, strict contracts, financial
  precision, all instrument-family facts and source-change reassessment. Implement
  pure contracts/assessment in regulatory_reporting.
- [x] 2. Add migration 104, retained profiles/candidate revisions/export tables;
  register dedicated module/actions without automatic grants. Implement audited,
  scoped API preparation, review, pagination and frozen export/download commands.
  Verify tenant/action/strategy denials, stale revisions, audit atomicity and
  idempotent export using a disposable database.
- [x] 3. Add console menu, server access gate, allowlisted BFF and compact workflow
  UI with top how-to, profiles, report review and export history. Test status
  distinctions, permission controls, download handling and context propagation.
- [x] 4. Review boundaries and update capability/register/map and root knowledge/
  findings. Run focused Python/UI checks, typecheck and contract checks. Record
  verified scope, migration activation and remaining regulatory acceptance work.

No automatic commit/push, full Python regression or operating report generation.
