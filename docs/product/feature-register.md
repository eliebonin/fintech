# Desired features and implementation register

**Status:** Maintained current reference  
**Content type:** Product capability register  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-12  
**Code baseline:** main `76f6292` (including implementation `c96c614`)

This is the single starting point for **what we want versus what exists**. Each stable ID links to a Markdown capability record containing the desired outcome, backend/frontend evidence, deliberate shortcuts/trade-offs, weaknesses, and remaining work. The [implementation and test map](feature-implementation-map.md) adds the concrete backend symbols, frontend routes/components and focused test files for the registered capability IDs, explicitly marking absent workflows or tests. Update the record and this summary together. Dated specs, plans and successful tests are evidence, not automatic proof of a delivered end-to-end feature.

## Status vocabulary

16 October [query-efficiency follow-up](../delivery/quality-reviews/2026-10-16-query-efficiency.md)
improves F02/F27/F32/F34/F36/F37/F48 reads without changing capability classifications,
financial formulas or rights. Full-history/concurrent scaling remains open.

16 October backend/API follow-up: [remediation, evidence and bounded gaps](../delivery/quality-reviews/2026-10-16-backend-remediation.md)
hardens F02/F04/F09/F15/F37/F39 without upgrading their capability classifications.
Strict schedule/dependency/calendar intake, scoped queues, UTC authority, atomic
request audit, paged selectors and coherent previews are implemented. Shared Future/
Swap term-model extraction is now approved and implemented with API/frozen-JSON
compatibility checks; broader decomposition, representative full-history/multi-user
scaling and production identity remain open. No operating activation in this task.

15 October F38: [coupon schedules and actual payments](../delivery/bond-coupons-20261015.md) are separate evidence with zero additional income/cash/accrual mutation. Migration 94/API active with approval; browser acceptance pending. No automatic entitlement, accrual generation or accounting reconciliation. F38 remains PARTIAL.

14 October F38 follow-up: [typed daily earned interest](../delivery/typed-daily-interest-20261014.md), minimal amount/currency submissions and optional balance reconciliation. Existing PARTIAL status remains: assessed inputs, not automatic coupon accrual generation or full NAV.

14 October F36–F39 methodology assurance: [matrix and current limits](../architecture/market-data-and-valuation/valuation-methodology.md), [implemented/tested evidence improvements](../delivery/valuation-methodology-assurance-20261014.md). Numerical methods unchanged; daily-accrual rules, frozen bridge and availability facts are explained in new results. Existing ALPHA/PARTIAL status remains appropriate.

14 October follow-up — F36/F37/F39: [historical booking corrections and explicit valuation reassessment](../delivery/trade-corrections-valuation-reassessment-20261014.md) implemented with focused tests and disposable FX browser acceptance. Published figures remain immutable; source warnings, staged recalculation and stale-publication guards are locally activated through approved migration 92/API restart. No operating recalculation/publication performed. Existing ALPHA/PARTIAL capability classifications remain unchanged.

| Status | Meaning |
| --- | --- |
| ALPHA | A bounded working backend/frontend path exists; its restrictions and acceptance gaps still apply. Not production certification. |
| PARTIAL | Useful implementation exists, but a substantial part of the desired workflow is missing. |
| FOUNDATION | Schema, resolver, contract or reference model exists; the desired operational workflow is not delivered. |
| DEFERRED | Deliberately postponed by the user. Existing prototypes do not make it signed off. |
| NOT IMPLEMENTED | No reviewed end-to-end implementation for the desired feature. A module/profile label is not implementation. |

These are capability states, not permission states. A module can be enabled even when its product workflow is incomplete. Browser sign-off, local activation, financial acceptance and production readiness are separate evidence dimensions in the linked records.

## Platform and tenant workspace

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F01 | [Platform tenant administration](features/access-and-strategies.md#f01-platform-tenant-administration) | ALPHA | Local control plane; commercial provisioning/offboarding absent. |
| F02 | [Tenant users, groups and delegated actions](features/access-and-strategies.md#f02-users-groups-and-delegated-actions) | ALPHA | Action-bound scopes, readable group/editor UI, filtered access matrix and versioned impact preview. Admin self-assignment remains possible; backend matrix scaling and production identity remain open. |
| F03 | [Platform/tenant/user context switching](features/access-and-strategies.md#f03-context-switching) | ALPHA | Research-only impersonation; production identity is separate. |
| F04 | [Module entitlements and tenant profile](features/access-and-strategies.md#f04-module-entitlements-and-profile) | ALPHA | Access view separates subscription, permission and maintained delivery status; future modules remain undelivered. |
| F05 | [Tenant strategy workspace and classification](features/access-and-strategies.md#f05-strategies) | ALPHA | Register/create/detail, grouped signed holdings, frozen contract dates and as-of attention indicators, movements/chart, calendars; scoped actions retained. No automatic closure, tax/FIFO/financial valuation. |
| F06 | [Production identity and isolation deployment](features/access-and-strategies.md#f06-production-identity-and-isolation) | FOUNDATION | Local sessions/header trust are not production authentication. |
| F58 | [Shared directory and tenant organisations](features/organisation-management.md#f58-shared-directory-and-tenant-organisations) | PARTIAL | Trading-only register/private settings and original-list counterparty/broker editing implemented and isolated-tested. Migration 95 applied locally; live register loading verified. GLEIF and issuer/custodian workflows deferred. |

## Reference data and instrument management

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F07 | [Instrument search, catalogue and details](features/instrument-management.md#f07-catalogue-and-details) | ALPHA | Page-size limits are read budgets, not a complete universe snapshot. |
| F08 | [Canonical instruments and contextual listings](features/instrument-management.md#f08-canonical-instruments-and-listings) | ALPHA | Product/date/convention eligibility remains explicit. |
| F09 | [Creation requests, approval and Operations queue](features/instrument-management.md#f09-requests-and-approval) | ALPHA | Not universal reference stewardship or contractual lifecycle. |
| F10 | [Custom instrument taxonomy](features/instrument-management.md#f10-instrument-taxonomy) | FOUNDATION | Reference classification model; general tenant taxonomy UI absent. |
| F11 | [Safe instrument amendments/version lifecycle](features/instrument-management.md#f11-instrument-amendments-and-lifecycle) | PARTIAL | Historical definitions exist; complete amendment/promotion UX does not. |

## Instrument-specific creation and booking

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F12 | [Plain listed cash booking](features/product-booking.md#f12-plain-listed-cash) | ALPHA | Explicit eligible listing allowlist, not arbitrary cash/derivatives. |
| F13 | [Deliverable FX forwards](features/product-booking.md#f13-deliverable-fx-forwards) | ALPHA | Booking, maturity closure and bounded rate-based P&L; no NDF, discounted model MTM or signed-off delivery. |
| F14 | [Listed options](features/product-booking.md#f14-listed-options) | ALPHA | OPEN/CLOSE is intent, not inventory validation or exercise. |
| F15 | [Listed/OTC structured securities](features/product-booking.md#f15-structured-securities) | ALPHA | Booking supported; payoff/lifecycle/valuation engine not implied. [Seeded-note readiness](../delivery/termsheet-note-booking-readiness-2026-10-14.md): six PDF parent notes have approved unit/PCT_OF_PAR dirty OTC conventions; 15 focused tests and app readiness verified. [Terms & Schedule](../delivery/instrument-terms-schedule-2026-10-14.md): read-only approved structured schedules, distinct note/share dates and swap performance-reference look-through are available; lifecycle processing remains separate. |
| F16 | [Future family → contract → listing → booking](features/product-booking.md#f16-futures) | ALPHA | Physical/crypto remains creation-only. Cash-settled index futures also have a monetary notional/exposure preview, not contract MTM, P&L or margin processing. |
| F17 | [Bond CLEAN/DIRTY booking](features/product-booking.md#f17-bonds) | ALPHA | Assessed accrual needed; no automatic coupon/redemption engine. |
| F18 | [Generic swap creation and booking](features/product-booking.md#f18-generic-swaps) | ALPHA | Nominal or unit-based whole-swap quote; separate funding reference notional. No swap valuation or generated cash. |

## Trade operations

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F19 | [Dedicated enriched booking and readiness](features/trade-operations.md#f19-booking-console-and-readiness) | ALPHA | Advisory readiness; writer remains authoritative. |
| F20 | [Tenant-governed properties and catalogues](features/trade-operations.md#f20-governed-trade-properties) | ALPHA | Flexible field schema, with a 1,000-active-definition quota per tenant; immutable meanings and manual curation. |
| F21 | [Trade history and frozen detail](features/trade-operations.md#f21-history-and-detail) | ALPHA | Not a complete settlement/accounting or export workspace. |
| F22 | [Cancel/replace erroneous bookings](features/trade-operations.md#f22-record-corrections) | ALPHA | Record correction is not a market unwind; P&L replay is bounded. |
| F23 | [Historical booking and valuation recognition date](features/trade-operations.md#f23-historical-and-recognition-dates) | ALPHA | Explicit date override; information cutoff still matters. |
| F24 | [Contractual delivery, expiry, reset and redemption](features/trade-operations.md#f24-contractual-lifecycle) | PARTIAL | Plain-bond redemption and deliverable FX maturity closure feed bounded P&L; cash/delivery separate, notifications deferred. |
| F51 | [Tenant lifecycle handling modes](features/trade-operations.md#f51-tenant-lifecycle-handling-modes) | ALPHA | Separate bond/FX retained modes and prepare/approve/book/cancel workspace; explicit scoped grants, no unattended booking or notification dashboard. |

## Market data

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F25 | [Shared S&P 500/CAC 40 reference universe](features/market-data.md#f25-public-reference-universe) | ALPHA | Dated seed, not continuously current membership/history service. |
| F26 | [Segregated, durable ingestion](features/market-data.md#f26-ingestion-boundary-and-operations) | ALPHA | Operator CLI/jobs; no scalable scheduled worker service. |
| F27 | [Layered licences and scoped tenant rights](features/market-data.md#f27-licensing-and-scoped-rights) | PARTIAL | Enforcement exists; commercial entitlement administration/reviews do not. |
| F28 | [Provider/scope catalogue and source priority](features/market-data.md#f28-provider-catalogue-and-priority) | ALPHA | Priority never bypasses semantics, rights or freshness. |
| F29 | [Yahoo historical EoD equity and GBP FX data](features/market-data.md#f29-yahoo-historical-data) | ALPHA | Personal-project source; coverage/precision/timing limits. |
| F30 | [As-traded RAW prices and adjustment evidence](features/market-data.md#f30-price-basis-and-raw-reconstruction) | ALPHA | Derived RAW relies on explicit Yahoo-method evidence/assumptions. |
| F31 | [Corporate-action ingestion and position replay](features/market-data.md#f31-corporate-actions) | PARTIAL | Reviewed basic equity/ETF quantity ratios replay; complex/account-specific entitlements, cash-in-lieu and general review UI remain absent. |
| F32 | [Flexible/strict pricing policy rules](features/market-data.md#f32-pricing-policies) | ALPHA | Flexible coverage does not mean missing-input fallback. |
| F33 | [Exchange and tenant fund/strategy calendars](features/market-data.md#f33-calendars) | ALPHA | 21 sealed 2026 research schedules, 16 active; seven equity venues connected. Five require review; annual/historical maintenance absent. |
| F34 | [Data inspection, coverage and price validation](features/market-data.md#f34-inspection-and-validation) | PARTIAL | Inspection/eligibility exist; full pre-valuation validation sign-off does not. |
| F35 | [Tenant-supplied time-series upload](features/market-data.md#f35-tenant-time-series-upload) | FOUNDATION | Ownership/source model exists; general upload API/UI absent. |

## Valuation and P&L

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F36 | [Relevant positions from immutable trade history](features/valuation-and-pnl.md#f36-position-reconstruction) | ALPHA | No total 1,000-trade cap; reviewed basic share-ratio replay. Complex entitlements/transformations and historical scaling remain bounded. |
| F37 | [Market P&L and position monetary measures](features/valuation-and-pnl.md#f37-economic-valuation) | PARTIAL | Existing P&L scope unchanged; Position values & exposure reports native/fund amounts, forward currency legs and linear index-futures exposure with explicit missing/deferred status, not forward/futures MTM. Compact scan amounts retain exact values in full-width input inspection. Equity/fund/bond and bounded index-swap boundaries remain. No weights, measure publication, interim resets or generic derivative pricer. |
| F38 | [Daily bond accrual and economic income/cost flows](features/valuation-and-pnl.md#f38-accruals-and-economic-flows) | PARTIAL | Assessed inputs/manual recognition; no automatic generation/reconciliation. |
| F39 | [Stage → amendment → governed publication](features/valuation-and-pnl.md#f39-review-and-publication) | ALPHA | Filtered reports and dual statuses; independent publication by default, explicitly scoped/opted-in self-publication with reason/expiry/audit. Financial acceptance, per-user expiry and broader ownership pending. |
| F40 | [Full strategy/fund NAV and cash balance valuation](features/valuation-and-pnl.md#f40-full-nav-and-cash-balances) | PARTIAL | Dated balance register/translated preview active on migration 89. No movement P&L or staged cash/full fund NAV. |

## Broader product directions and deferred operations

These are discussed or documented product directions, **not new scope commitments from this review**. Shared foundations do not constitute a complete specialist module.

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F57 | [Valuation purpose and descriptive tags](features/valuation-and-pnl.md#f57-valuation-purpose-and-descriptive-tags) | DEFERRED | Parked 2026-10-14; controlled purpose versus optional tags, with separate publication/replacement boundaries still to specify. |
| F41 | [AMC management](features/future-modules.md#f41-amc-management) | FOUNDATION | Profile/module/strategy labels only, no complete AMC operations. |
| F42 | [Fund operations and operational feed mappings](features/future-modules.md#f42-fund-operations) | FOUNDATION | Mapping schema/resolver exists; complete feed/workflow module absent. |
| F43 | [Structured-product management module](features/future-modules.md#f43-structured-product-management) | PARTIAL | Reference terms and booking exist; event/valuation management incomplete. [Terms & Schedule](../delivery/instrument-terms-schedule-2026-10-14.md): read-only approved structured schedules, distinct note/share dates and swap performance-reference look-through are available; lifecycle processing remains separate. |
| F44 | [Structured-product distribution](features/future-modules.md#f44-structured-product-distribution) | NOT IMPLEMENTED | Module/profile label is not distribution/client workflow. |
| F45 | [UCITS/AIF and liquidity controls](features/future-modules.md#f45-ucits-aif-and-liquidity-controls) | NOT IMPLEMENTED | Research and module metadata, not monitored regulatory controls. |
| F52 | [Strategy and pre-trade UCITS assessment](features/future-modules.md#f52-strategy-and-pre-trade-ucits-assessment) | NOT IMPLEMENTED | Desired as-of strategy checks and assessment of a proposed trade list; specification postponed. |
| F53 | [Regulatory reporting across jurisdictions](features/future-modules.md#f53-regulatory-reporting-across-jurisdictions) | NOT IMPLEMENTED | Desired UK/FCA, EU and Swiss reporting, including daily reporting where applicable; specific regimes and specification postponed. |
| F54 | [AI-assisted termsheet parsing and instrument creation](features/future-modules.md#f54-ai-assisted-termsheet-parsing-and-instrument-creation) | NOT IMPLEMENTED | Full-instrument assisted editing and unattended submission into checking prioritized 2026-10-13; design approved, execution plan proposed for review, real-termsheet acceptance unverified. [All-four reviewed load](../delivery/all-reviewed-autocalls-loaded-2026-10-14.md): all four note/share bundles plus two Phoenix notes ACTIVE in app DB; 40 focused tests and replay/lookup verified. Explicit operator seed, not integrated AI ingestion. |
| F55 | [AI-assisted portfolio and investment-idea recommendations](features/future-modules.md#f55-ai-assisted-portfolio-and-investment-idea-recommendations) | NOT IMPLEMENTED | Desired recommendations from current portfolio/guidelines or textual hints/ideas; specification postponed. |
| F56 | [Option and structured-product Greeks with cross-asset look-through risk](features/future-modules.md#f56-option-and-structured-product-greeks-with-cross-asset-look-through-risk) | NOT IMPLEMENTED | Desired Greeks feeding cross-asset risk and underlying look-through analytics; models, coverage and specification postponed. |
| F46 | [Portfolio risk and solution diagnostics](features/future-modules.md#f46-portfolio-risk-and-diagnostics) | NOT IMPLEMENTED | Commercial research, not a validated analytics engine. |
| F47 | [Settlement and accounting](features/future-modules.md#f47-settlement-and-accounting) | DEFERRED | Explicitly postponed; no posting engine or reconciliation module. |
| F48 | [API quality and production operations](features/platform-quality.md#f48-api-and-operational-hardening) | PARTIAL | Alpha controls/tests; scalable production operations still pending. |
| F49 | [Frontend usability/accessibility acceptance](features/platform-quality.md#f49-frontend-acceptance) | PARTIAL | Shared styles and contextual workflow guides: 957 frontend tests and 21 isolated browser cases pass. Broader live visual/assistive sign-off remains open. |
| F50 | [Automated reference/provider onboarding](features/platform-quality.md#f50-automated-reference-onboarding) | FOUNDATION | Proposals/mappings exist; complete multi-provider onboarding absent. |

## Adding a desired feature

1. Append the next unused `Fnn` ID; never recycle or renumber IDs.
2. Add a capability section to the relevant `features/*.md` record (or a new focused file).
3. State desired outcome and origin: user agreement, documented direction, or proposed idea. A proposal is not approved implementation scope.
4. Record status, backend and frontend separately, evidence links, deliberate cuts/trade-offs, weaknesses, and concrete remaining work. Use “not verified” where evidence is absent.
5. Add the summary row here, with an actual Markdown link to the detailed record and its principal boundary. Review both after implementation; retain dated evidence rather than rewriting history.

## Review and evidence boundary

See the [documentation reconciliation report](../delivery/quality-reviews/2026-10-12-documentation-reconciliation.md) for inspected scope, discovered drift, research and verification. No application tests, database writes, deployment, commit or GitHub push are implied by a documentation update. Prior merge verification is retained in the [merge record](../delivery/tenant-access-administration-progress.md#completed-remediation-verification); it was partitioned diagnostics plus successful focused fixes, not one clean full-suite rerun.
