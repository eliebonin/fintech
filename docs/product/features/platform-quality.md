# Platform quality — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Engineering/platform operations  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). Test pass, local activation, visual acceptance, financial reconciliation and production certification are different claims.

## F48 API and operational hardening

- **Desired:** Consistent authorized/replay-safe APIs, generated contracts, safe logs and scalable recovery/operations.
- **Status / backend / frontend:** PARTIAL. Authority/tenant checks, budgets, transactions, idempotency, safe RFC problem responses/request IDs and generated OpenAPI/TypeScript; BFF stale-context/uncertain-result handling and readable operational errors.
- **Cuts/trade-offs:** Synchronous local alpha, targeted resource budgets and compatibility aliases; independent operational evidence survives failed financial work. Tests reject the operating DB; CI migrates/seeds an isolated DB.
- **Weaknesses:** Large API/repository files, history-scaling costs, supplemental audit durability, dependency warnings, no fully accepted distributed worker/SLO/deployment security model. A staged secret scan is not a full security audit.
- **Remaining:** Production identity/audit/recovery/monitoring, representative performance acceptance and selective boundary decomposition. Preserve focused-first tests; broad runs use owned databases and accurately report failures/reruns.
- **Evidence:** [API hardening](../../delivery/api-boundary-hardening.md), [merge verification](../../delivery/tenant-access-administration-progress.md#completed-remediation-verification), [CI](../../../.github/workflows/quality.yml), [error contract](../../../apps/reference_api/problem_details.py).

## F49 Frontend acceptance

- **Desired:** Consistent, permission-aware and accessible tenant, reference, booking, data and P&L workflows with realistic user walkthroughs.
- **Status / backend / frontend:** PARTIAL. Working pages/BFF, native workspace styling, scoped action controls, tests/typechecks/build. Earlier trade-side synthetic browser journeys are recorded; latest access/P&L visual sign-off is not complete.
- **Cuts/trade-offs:** Component/HTTP tests are not visual acceptance. Existing MUI dependency does not mean all new pages use MUI. Dedicated operations/booking/profile pages avoid overloading instrument/strategy screens.
- **Weaknesses:** Dense tickets, heterogeneous page patterns, incomplete latest mobile/keyboard/screen-reader and chart-interaction acceptance. Browser tool failures explain missing evidence, not a successful walkthrough.
- **Remaining:** Sign off current context/Users/Groups, market-data chart basis/date refresh and economic-P&L inputs/review with realistic trades. Record defects and scope rather than general “UI done”.
- **Evidence:** [Style review](../../delivery/frontend-style-review-2026-10-08.md), [trade walkthroughs](../../delivery/trade-side-acceptance-2026-10-06.md), [access evidence](../../delivery/tenant-access-administration.md), [economic acceptance limits](../../delivery/economic-pnl-implementation-progress.md).

## F50 Automated reference onboarding

- **Desired:** Multi-provider enriched reference ingestion with mappings, validation, proposals and controlled promotion.
- **Status / backend / frontend:** FOUNDATION. Sources/payloads/mappings/proposals, some provider enrichment paths and curated seed operators exist; manual request review UI, no complete generic automated onboarding control plane.
- **Cuts/trade-offs:** Bounded operators/adapters instead of guessing all issuer terms from a ticker; sparse bond proposals may need enrichment.
- **Weaknesses:** Automated provider reconciliation, duplicate/conflict stewardship, commercial adapters and operational exception tooling incomplete.
- **Remaining:** Provider-specific validated contracts, enrichment/conflict workflow, mapping review and monitored jobs when prioritized. Ingestion cannot bypass approval or source rights.
- **Evidence:** [Onboarding direction](../../../security-master-notes/23-automated-reference-data-onboarding.md), [onboarding index](../onboarding/README.md), [public seed](../../delivery/index-universe-seed-2026-10-06.md).
