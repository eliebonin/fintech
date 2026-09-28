# Financial Instrument Security Master - Architecture Notebook

This notebook captures the ongoing design of a PostgreSQL-backed canonical reference-data master for financial instruments. It deliberately separates settled decisions from open design work.

## Reading order

1. [Scope and principles](01-scope-and-principles.md)
2. [Reference identity model](02-reference-identity-model.md)
3. [Market data, marks, and trades](03-market-data-marks-and-trades.md)
4. [Derivatives, futures, and swaps](04-derivatives-futures-and-swaps.md)
5. [Dates and schedules](05-dates-and-schedules.md)
6. [Decision log and open questions](06-decision-log-and-open-questions.md)
7. [Entities and instrument parties](07-entities-and-instrument-parties.md)
8. [SP key terms and product applicability](08-sp-key-terms-and-product-applicability.md)
9. [Indices, FX forwards, and market-data architecture](09-indices-fx-forwards-and-market-data-architecture.md)
10. [Corporate actions and adjusted market data](10-corporate-actions-and-adjusted-market-data.md)
11. [Macro, commodities, cryptoassets, and exchange-traded wrappers](11-macro-commodities-crypto-and-exchange-traded-wrappers.md)
12. [Industry standards and integration boundaries](12-industry-standards-and-integration-boundaries.md)
13. [Additional instrument types roadmap](13-additional-instrument-types-roadmap.md)
14. [Geographic areas and market venues](14-geographic-areas-and-market-venues.md)
15. [Tenant overlays, client ingestion, and Soft NAV](15-tenant-overlays-client-ingestion-soft-nav.md)
16. [Database implementation plan](16-database-implementation-plan.md)
17. [Soft-NAV pricing-date resolution](17-soft-nav-pricing-date-resolution.md)
18. [Critical review and delivery choices](18-critical-review-and-delivery-choices.md)
19. [Tenant database topology and priorities](19-tenant-database-topology-and-priorities.md)
20. [Tenant routing and core API contract](20-tenant-routing-and-core-api-contract.md)
21. [Market-data coverage and provenance](21-market-data-coverage-and-provenance.md)
22. [Fees and charges](22-fees-and-charges.md)
23. [Automated reference-data onboarding](23-automated-reference-data-onboarding.md)
24. [External evidence and research register](24-external-evidence-and-research.md)
25. [Option strike resets and terms versioning](25-option-strike-resets-and-terms-versioning.md)
26. [Structured-product condition groups](26-structured-product-condition-groups.md)
27. [Structured-product terms and coupon memory](27-structured-product-terms-and-coupon-memory.md)
28. [Range accrual and supertracker research](28-range-accrual-and-supertracker-research.md)
29. [Structured-product correction pass](29-structured-product-correction-pass.md)
30. [Global database, API, and frontend review (2026-09-10)](../docs/architecture/global-db-api-frontend-review-2026-09-10.md)
31. [Fund, future, swap, and option onboarding UI design](../docs/superpowers/specs/2026-09-10-fund-future-swap-option-ui-design.md)

Structured-product condition groups, versioned terms, typed component
composition, coupon configuration, and payout-aware group actions are
implemented through Alembic revision `20260910_40`. The detailed execution record
and deferred follow-up decisions are in
[`docs/superpowers/plans/2026-09-08-structured-product-condition-groups.md`](../docs/superpowers/plans/2026-09-08-structured-product-condition-groups.md).

The current OTC FX-forward onboarding slice is documented in
[`docs/architecture/fx-forward-onboarding-2026-09-08.md`](../docs/architecture/fx-forward-onboarding-2026-09-08.md).

The cross-project product context transferred from the Spineoff discussion and
the prior Tech V2 knowledge-base review is recorded in
[`docs/architecture/spineoff-context-and-knowledge-transfer-2026-09-09.md`](../docs/architecture/spineoff-context-and-knowledge-transfer-2026-09-09.md).

The system is being designed as a central canonical reference-data and
market-data source of truth, with isolated tenant operational overlays for
trades, positions, cash and Soft NAV. It is not an official administrator NAV
or custody engine.

The latest UI-driven modelling review, implemented hardening scope, and
explicitly deferred decisions are recorded in
[`docs/architecture/schema-hardening.md`](../docs/architecture/schema-hardening.md).

External research is maintained separately from the decision log. See the
[external evidence and research register](24-external-evidence-and-research.md)
for source links, adopted design choices, and explicit research gaps.

The latest cross-layer quality checkpoint is
[Global database, API, and frontend review — 2026-09-10](../docs/architecture/global-db-api-frontend-review-2026-09-10.md).
It confirms that the identity and product model is a sound prototype while
tenant isolation, point-in-time market-data resolution, immutable version
promotion, and production API/frontend controls remain the next foundation
slice. The review is additive: it does not replace the detailed decision notes
or silently close their deferred choices.
