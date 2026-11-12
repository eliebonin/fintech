# Structured lifecycle batch-read implementation plan

> Execute sequentially using superpowers:executing-plans. No subagents, automatic commits or pushes. Current checkout preserves earlier authorised work.

**Goal:** Eliminate per-contract database round trips without changing complete visible results or evidence.
**Architecture:** A scoped breadth-first, chunked source store feeds one existing projection renderer. Bulk worklist loading and search/status reads consume the store; single-instrument API contracts remain unchanged.
**Stack:** PostgreSQL/SQLAlchemy, Pydantic/FastAPI, pytest and existing frontend/BFF.
**Spec:** [Preserved contracts and boundaries](../specs/2026-11-11-structured-batch-reads.md).

- [x] Freeze pre-change readers and add failing distinct-contract query-budget and semantic tests.
- [x] Implement chunked scoped graph/table reads and share the renderer; batch worklist statuses/search without SQL in per-root/event loops.
- [x] Verify all affected native/scope/source/API cases, chunks, root isolation and complete real-data result/inspection equality; measure repeat timings/counts.
- [x] Review the diff, document exact evidence and limits, restart only the owned API and verify real frontend reads; retain operating financial/configuration state.

Ruling: Keep the user's existing checkout and branch because the running app and uncommitted previous deliveries depend on it. Freeze the exact current readers as ignored comparison artifacts before editing. Do not introduce a second production legacy renderer or relax any source/authority guard.

Verified: current FCPGF89 queries/1.310-second median; all270 events/87 source views and available inspection proofs equal; native distinct breadth102→102 queries (104 searched), graph/chunk/privacy regressions green; live BFF200 in1.796seconds. No migration or operating financial/configuration change.
