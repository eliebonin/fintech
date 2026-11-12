# Structured informational notifications implementation plan

> Execute sequentially using superpowers:executing-plans; lightweight failing tests first, then bounded regressions. No subagents, automatic commits or pushes.

**Goal:** Inform Ops about sourced structured schedules without assessing outcomes or creating financial tasks.
**Architecture:** Contract-preserving terms projection extraction below API; independent0/1 setting; scoped holdings/source read model; typed GET/BFF and shared native-modal inspection.
**Tech stack:** PostgreSQL/SQLAlchemy, Pydantic/FastAPI, React/Next, pytest/Vitest/Playwright.
**Spec:** [authorised scope and research](../specs/2026-11-11-structured-informational-notifications.md).

## Global constraints
INFORMATION only. No outcome/payment/financial/valuation changes or operating positive selections/grants. Distinguish held swap from observed contract. Reuse original ledger/allocation and visibility checks. Current linked sources only; absent evidence remains unknown. No dates/thresholds/percent conversion inferred.

## Review focus
Non-call periods versus actual autocall tests; current versus historical schedules; pre-holding/past/future and flat/cancelled/net0 holdings; private/deep/cyclic dependencies and changed frozen references; stale inspector context and read-only controls at every tier.

## Tasks
- [x] Add/run failing informational-state/eligibility/current-link contract tests. Extract existing terms projection with identical function AST/OpenAPI and add independent event/schema migration115.
- [x] Add native direct/swap mock booking fixtures; implement linked schedule discovery, scoped source/position inspection and full-population filters. Verify no writes, no pre-holding history, current/frozen relevance, private references, counts/page and downgrade/DB caps.
- [x] Add failing BFF/mounted tests; implement informational filter/labels, per-strategy selection, read-only condition inspector and help. Generate/verify contracts, mobile/focus/stale reads and existing lifecycle journeys.
- [x] Review bounded affected tests/diff, activate migration115/API, reconcile delivery/register/map/root docs, and verify cleanup without operating financial/configuration changes.

- [x] Follow-up: reproduce enabled FCPGF timeout, preserve full result/proof parity with request-local lookup reuse, bound the heavy GET separately, correct read-only error guidance, and verify live BFF/API reads. See delivery read-timeout correction.
