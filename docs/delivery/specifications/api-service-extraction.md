# API service extraction: phases 1–3

**Accepted scope:** 29 October 2026. Implementation refactor; no new product rules.

The HTTP adapter should own request context, wire models, error translation and
audited transaction wiring. Shared workflows must be callable by both HTTP and
operator tools without importing the API. Keep the current SQLAlchemy Core
Connection contract; do not add a repository framework, service process or schema.

1. Characterize canonical evidence, finite-Decimal errors, command schemas,
   frozen financial results, idempotency and atomic request audit before moving code.
   Add import guards around the extracted owners and migrated consumers.
2. Import existing booking/visibility owners directly. Move the exact canonical
   evidence/Decimal implementation to a dependency below valuation, market data
   and positions. Preserve old public imports as identity re-exports, not copies.
3. Extract pricing-policy command contracts, business validation, versioning,
   retry fingerprints and record loading into market_data. Keep API response
   models and HTTP errors in the adapter. Migrate the Yahoo FX operator caller.

Authority must still apply before writes and idempotent replay. Strategy-bound
commands must enforce the same current action/scope for non-HTTP callers.
Preserve canonical hashes, advisory-lock namespaces, version history, alias JSON,
private listing-parent checks, source/calendar validation and function-scoped
audit rollback. No service may commit its caller's transaction.

Acceptance: unchanged OpenAPI; fixed pre-refactor hash/schema vectors; targeted
financial regressions; isolated policy create/replay/conflict/revocation and
audit-failure tests; no API imports from the new service or its operator caller.
No operating prices, rights, policies, trades or valuations will be changed.

## Basis and tradeoffs

Read 29 October 2026: [Cosmic Python service layer](https://www.cosmicpython.com/book/chapter_04_service_layer)
supports sharing orchestration between HTTP and CLI. Its abstraction stack is
optional; this project retains Core connections. [Fowler's incremental migration](https://martinfowler.com/bliki/BranchByAbstraction.html)
(2014) supports small working extractions with boundary tests. Compatibility
exports remain only where current callers need the public import; new domain
callers must use the lower owner. Remove exports after those imports are migrated
and documented consumers no longer require them.

[SQLAlchemy 2.1 transaction guidance](https://docs.sqlalchemy.org/en/21/core/connections.html#connect-and-begin-once-from-the-engine)
supports explicit commit/rollback ownership (installed 2.1.1; current docs 2.1.6).
[FastAPI router guidance](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
supports modular adapters in one application. Preserve this application's custom
audited router and transaction dependency rather than copying a plain-router example.
These are engineering recommendations, not regulatory requirements.

Deferred: broad reference/booking decomposition, source-catalogue read extraction,
metadata registration redesign, production authentication and performance tuning.
