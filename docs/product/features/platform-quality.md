# Platform quality — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Engineering/platform operations  
**Last reviewed:** 2026-10-30 (local identity and dependency follow-ups)

[Feature register](../feature-register.md). Test pass, local activation, visual acceptance, financial reconciliation and production certification are different claims.

## F48 API and operational hardening

30 October [shared admission](../../delivery/dataset-rights-and-workload-20261030.md)
adds nonblocking process/global/tenant limits across workers, dedicated control
connections, safe busy responses and preserved manual retry. Ordinary status
reads and complete financial populations remain. F48 stays PARTIAL for durable
workers, job OS budgets, production authentication and capacity acceptance.

30 October [database/audit/browser controls](../../delivery/security-controls-20261030.md)
separate the runtime login, preserve the database while restricting its port and
credentials, enforce append-only access audit, log safe denials, activate default
secret rules and add nonce CSP/HTTPS cookie safeguards. Missing profiles and
admission are addressed by the follow-up above; external retention and production
identity remain open. [Setup](../../platform/security-controls.md).

30 October [local identity containment](../../delivery/local-identity-safeguard-20261030.md)
requires sessions and guarded bootstrap, removes demo fallbacks and blocks
non-local startup. It contains the local header-impersonation gap; production
identity-provider integration remains a deployment blocker.

30 October [dependency-security remediation](../../delivery/dependency-security-20261030.md)
updates affected complete locks and adds read-only PR/main/manual/weekly audits.
Local compatibility and advisory checks are distinct from remote execution and
production security sign-off. [Maintenance](../../platform/dependency-security.md).

October 16 [query-efficiency delivery](../../delivery/quality-reviews/2026-10-16-query-efficiency.md)
records measured read-only gains, preserved authority/evidence boundaries and
remaining full-history/concurrency limits. No production-capacity certification.

- **Desired:** Consistent authorized/replay-safe APIs, generated contracts, safe logs and scalable recovery/operations.
- **Status / backend / frontend:** PARTIAL. Authority/tenant checks, budgets, transactions, idempotency, safe RFC problem responses/request IDs and generated OpenAPI/TypeScript; BFF stale-context/uncertain-result handling and readable operational errors.
- **Cuts/trade-offs:** Synchronous local alpha, targeted resource budgets and compatibility aliases; independent operational evidence survives failed financial work. Tests reject the operating DB; CI migrates/seeds an isolated DB.
- **Weaknesses:** Large API/repository files, history-scaling costs, supplemental audit durability and no fully accepted distributed worker/SLO/deployment security model. Dependency advisories require recurring review; a clean dated audit or staged secret scan is not a full security audit.
- **Remaining:** Production identity/audit/recovery/monitoring, representative performance acceptance and selective boundary decomposition. Preserve focused-first tests; broad runs use owned databases and accurately report failures/reruns.
- **Evidence:** [API hardening](../../delivery/api-boundary-hardening.md), [merge verification](../../delivery/tenant-access-administration-progress.md#completed-remediation-verification), [CI](../../../.github/workflows/quality.yml), [error contract](../../../apps/reference_api/problem_details.py).

## F49 Frontend acceptance

26 October [HTML/console integrity review](../../delivery/quality-reviews/2026-10-26-frontend-console-integrity.md)
fixes supplied-interest disclosure nesting and group/import native validation
patterns. Browser journeys now fail on application console warnings/errors and
uncaught page errors. Source inventory and synthetic regression evidence remain
distinct from every live-page/data combination and full assistive sign-off.

October 17 [contextual workflow help](../../delivery/page-contextual-help-20261017.md)
adds page-specific purpose/steps/terms/impact disclosures across complex workflows,
without moving required warnings or changing authority. Latest verification:
957 frontend tests, 21 isolated browser journeys, types and optimized build pass;
live structured-product guide inspected read-only. Full assistive acceptance is
still open.

October 17 [visual consistency/density delivery](../../delivery/quality-reviews/2026-10-17-frontend-visual-consistency.md)
adds shared presentation tokens, policy task tabs, structured-product outline and
shell skip navigation. Whole-project source inventory is distinct from bounded
visual samples; 932 unit tests, 20 isolated browser cases, types and production
build pass. F49 remains PARTIAL: full live-page and assistive acceptance is open.

October 16 backend-integration follow-up adds server-paged valuation selectors and
governed contractual calendar preview. [Verification and remaining limits](../../delivery/quality-reviews/2026-10-16-backend-remediation.md)
are separate from the earlier frontend remediation; F49 remains PARTIAL.

- **Desired:** Consistent, permission-aware and accessible tenant, reference, booking, data and P&L workflows with realistic user walkthroughs.
- **Status / backend / frontend:** PARTIAL. Working pages/BFF, scoped actions, shared context/retry/error/display protocols and contextual guides. October 17 help follow-up passes 957 frontend regressions, 21 synthetic browser cases, TypeScript and production build. Broader access/P&L visual and assistive sign-off remains incomplete.
- **Cuts/trade-offs:** Component/HTTP tests are not visual acceptance. Existing MUI dependency does not mean all new pages use MUI. Dedicated operations/booking/profile pages avoid overloading instrument/strategy screens.
- **Weaknesses:** Dense tickets, heterogeneous page patterns, incomplete latest mobile/keyboard/screen-reader and chart-interaction acceptance. Browser tool failures explain missing evidence, not a successful walkthrough.
- **Remaining:** Sign off current context/Users/Groups, market-data chart basis/date refresh and economic-P&L inputs/review with realistic trades. Record defects and scope rather than general “UI done”.
- **Evidence:** [October 16 remediation and browser evidence](../../delivery/quality-reviews/2026-10-16-frontend-remediation.md), [style review](../../delivery/frontend-style-review-2026-10-08.md), [trade walkthroughs](../../delivery/trade-side-acceptance-2026-10-06.md), [access evidence](../../delivery/tenant-access-administration.md), [economic acceptance limits](../../delivery/economic-pnl-implementation-progress.md).

## F50 Automated reference onboarding

- **Desired:** Multi-provider enriched reference ingestion with mappings, validation, proposals and controlled promotion.
- **Status / backend / frontend:** FOUNDATION. Sources/payloads/mappings/proposals, some provider enrichment paths and curated seed operators exist; manual request review UI, no complete generic automated onboarding control plane.
- **Cuts/trade-offs:** Bounded operators/adapters instead of guessing all issuer terms from a ticker; sparse bond proposals may need enrichment.
- **Weaknesses:** Automated provider reconciliation, duplicate/conflict stewardship, commercial adapters and operational exception tooling incomplete.
- **Remaining:** Provider-specific validated contracts, enrichment/conflict workflow, mapping review and monitored jobs when prioritized. Ingestion cannot bypass approval or source rights.
- **Evidence:** [Onboarding direction](../../../security-master-notes/23-automated-reference-data-onboarding.md), [onboarding index](../onboarding/README.md), [public seed](../../delivery/index-universe-seed-2026-10-06.md).
