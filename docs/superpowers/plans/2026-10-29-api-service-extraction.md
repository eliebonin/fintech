# API service extraction implementation plan

> Execution: sequential, as authorised by the user; no separate approval loop.

**Goal:** complete phases 1–3 of the [accepted scope](../../delivery/specifications/api-service-extraction.md).
**Architecture:** shared exact evidence primitives and market-data policy commands,
with the existing HTTP/audit/SQLAlchemy transaction adapters retained.

1. Capture fixed canonical/schema vectors and baseline OpenAPI. Run focused pure
   and owned disposable PostgreSQL policy/audit regressions. Add structural guards.
2. Move evidence primitives unchanged; re-export their original public names.
   Migrate positions/market-data consumers and the three residual API-helper imports.
   Keep economic kernels and transaction boundaries where they are.
3. Extract policy command models and creation/versioning/validation with a business
   result projection. API maps that projection to its existing wire model. Move
   the operator caller to the shared service and preserve its existing rights checks.
4. Verify vectors, no reverse dependencies, HTTP/command parity, current authority
   on replay, foreign references, flexible defaults, concurrent versioning, rollback
   and audit retention. Run related financial tests only; no full Python suite.
5. Reconcile root AGENTS/KNOWLEDGE/FIX, delivery/reference/atlas guidance and links.
   State remaining boundary work and verification limits. No operating migration,
   provider run, financial mutation, automatic restart, commit or push.
