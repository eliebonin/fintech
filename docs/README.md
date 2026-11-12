# Project documentation

12 November: [Lifecycle closeout checkpoint](delivery/checkpoints/2026-11-12-lifecycle-closeout.md) collects delivered features, open optimisation limits, verification scope and the user-authorised post-push shutdown boundary.

12 November: [Local production frontend comparison](delivery/local-production-frontend-20261112.md) records the isolated3008 production build, retained3001 dev app, authenticated browser smoke check and warm-response measurements.

11 November: [Lifecycle business-day date colours](delivery/lifecycle-business-day-colours-20261111.md) explains proximity bands, holiday-calendar evidence, explicit estimates and verification.

11 November: [Lifecycle readers: FX, futures, options, bonds and coupons](delivery/lifecycle-reader-batching-20261111.md) records paired full-evidence comparisons, query budgets and preserved financial controls.

**Status:** Accepted  
**Content type:** Documentation home  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-11-11 (scoped lifecycle navigation reconciliation)

This is the maintained entry point for the project. Historical material is preserved in the [pre-reorganisation archive](archive/2026-09-10-pre-reorganisation/README.md).

## Start here

11 November: [Structured lifecycle batch-read correction](delivery/structured-lifecycle-batch-reads-20261111.md) records query budgets, complete source/result parity, local timings and activation without financial/configuration changes.

11 November: [Structured informational notices](delivery/structured-informational-notifications-20261111.md) adds sourced observation/contract dates and read-only conditions, including structured performance references of held swaps. Passed dates do not confirm outcomes or create financial actions.

11 November: [Option deadline notifications](delivery/option-lifecycle-notifications-20261111.md) extends Lifecycle with independent notifications-only settings and read-only option terms/positions. A date never confirms exercise, assignment or settlement.

- **What do we want, what works, and what is missing?** [Feature register](product/feature-register.md): stable capability IDs, status, trade-offs, weaknesses and remaining work. Its [implementation and test map](product/feature-implementation-map.md) links each ID to concrete backend symbols, frontend surfaces and focused tests (or records their absence).
- **How is the current implementation organised?** [System overview](architecture/system-overview.md) and the domain indexes below. These describe the alpha, not a deployed production target.
- **Which document should I trust?** [Documentation map and precedence](governance/documentation-map.md).
- **What changed in the reconciliation?** [October 12 documentation review](delivery/quality-reviews/2026-10-12-documentation-reconciliation.md).

No “implemented” label implies commercial data rights, universal instrument support, complete fund NAV, latest browser acceptance or production readiness.

11 November: [Futures milestone notifications](delivery/future-lifecycle-notifications-20261111.md) adds an independent manual/notifications-only setting and read-only inspection; no future closure, roll or delivery automation. First-notice coverage remains an explicit gap.

11 November: Lifecycle now includes [bond/FX maturity discovery and native actions](delivery/fx-maturity-worklist-20261111.md) and [read-only coupon notices](delivery/coupon-notifications-20261111.md). Coupon review does not establish unpaid cash, entitlement or additional income; other product detectors remain deferred. The [side-panel delivery](delivery/lifecycle-action-panel-20261110.md) records isolated financial acceptance and audit boundaries.

5 November: [Lifecycle worklist](delivery/lifecycle-worklist-20261105.md) adds current bond-maturity discovery, scoped event filtering and native processing handoff under the configured assistance tiers.

5 November: [Lifecycle assistance entitlements](delivery/lifecycle-assistance-entitlements-20261105.md) adds platform ceilings, strategy/event settings and reviewed downgrades for the existing bond/FX workflows; bond discovery follows in the linked worklist delivery.

4 November: [Tenant reference data and strategy trade profiles](delivery/tenant-reference-data-trade-profiles-20261104.md) separates shared source maintenance, immutable field meaning and explicit strategy configuration.

## Reading paths

1. **Understand the platform** — [system overview](architecture/system-overview.md), [security master](architecture/security-master/README.md), [market data and valuation](architecture/market-data-and-valuation/README.md), and [tenancy](architecture/tenancy-and-entitlements/README.md).
2. **Build or integrate** — [API](platform/api/README.md), [frontend](platform/frontend/README.md), and [data and schema](platform/data-and-schema/README.md).
   [Visual architecture atlas](architecture/atlas/README.md): current database,
   code and data-flow diagrams, exact dependency register and coupling assessment.
3. **Operate data** — [product onboarding](product/onboarding/README.md), [trading and operations](architecture/trading-and-operations/README.md), and [integration/data rights](architecture/integrations-and-data-rights/README.md).
4. **Evaluate product modules** — [fintech modules](product/fintech-modules/README.md).
   [Regulatory Reporting](product/features/regulatory-reporting.md) documents the
   first UK transaction-preparation slice and the unimplemented submission work.
5. **Plan delivery** — [specifications](delivery/specifications/README.md), [implementation plans](delivery/implementation-plans/README.md), [quality reviews](delivery/quality-reviews/README.md), [decisions](governance/decisions/README.md), and [research](research/evidence-register.md).

## Code-adjacent documentation

October 14 root-document follow-up adds [supported valuation methodology assurance](delivery/valuation-methodology-assurance-20261014.md) to the earlier scoped reviews; it is not an exhaustive whole-repository audit.

- [Repository guidance](../AGENTS.md), [reviewed knowledge](../KNOWLEDGE.md), and [open scoped findings](../FIX.md): October 13 review focused on structured-product creation and termsheet-ingestion readiness; not an exhaustive source audit.
- [Operations Console](../apps/ops-console/README.md)
- [Reference Data API](../apps/reference_api/README.md)
- [API contracts](../packages/api-contracts/README.md)
- [Authentication helpers](../packages/auth/README.md)
- [Shared UI package](../packages/ui/README.md)
- [Synthetic test fixtures](../packages/test-fixtures/README.md)
- [Mock-up data](../data/mockup/README.md)

## Documentation governance

The [provider-neutral repository update](delivery/provider-neutral-repository-20261017.md)
includes editorial anonymisation of archived operator names. Historical dates,
evidence limitations and delivery status are retained; Git history is unchanged.

Read [documentation governance](governance/documentation-governance.md) before adding or materially changing a canonical page. Shared vocabulary is in the [glossary](governance/glossary.md).
