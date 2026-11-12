# Desired features and implementation register

11 November F24/F51: [Business-day date badges](../delivery/lifecycle-business-day-colours-20261111.md) add separate proximity colours and visible labels, with governed holiday calendars or explicitly marked weekday estimates. Contractual dates, discovery/filter/count logic and financial authority are unchanged.


11 November F15/F24/F51: [Remaining lifecycle reader batching](../delivery/lifecycle-reader-batching-20261111.md) preserves complete results/proofs while reducing FX-forward, futures and option read amplification. Bond/coupon reads were already batched; full source/authority checks and native commands remain intact. Follow-up analysis records one option-date query within the 55-call request, about 20 ms of repeated local permission-context overhead, and still-pending context/evidence reuse; see the same delivery checkpoint.


11 November F15/F24/F51: [Structured lifecycle batch reads](../delivery/structured-lifecycle-batch-reads-20261111.md) removes per-contract query amplification while retaining complete permissions, source evidence and portfolio results. FCPGF:4458→89 queries,9.632→1.310-second median; distinct-contract query budgets and graph/chunk/privacy regressions are in place.

11 November F15/F24/F43/F51: [Structured informational notices](../delivery/structured-informational-notifications-20261111.md) adds independent manual/notification selection, source-linked observation/final-valuation/maturity dates and read-only conditions for direct notes and structured references of held swaps. All rows remain informational, including passed dates and unavailable sources. No outcome, payable amount or financial action is inferred.

11 November F24/F51: [Option deadline notifications](../delivery/option-lifecycle-notifications-20261111.md) adds independent manual/notification selection, sourced last trading/expiry/settlement notices and read-only contract/holding inspection. No exercise, assignment, lapse, cash/delivery or closing trade is inferred. Structured-product informational schedules are now delivered separately; outcomes and financial processing remain deferred.

11 November F24/F51: [Futures lifecycle notifications](../delivery/future-lifecycle-notifications-20261111.md) adds independent strategy manual/notification selection and read-only sourced last-trading, expiry, settlement and physical-delivery milestones. No closure, roll, cash or delivery is generated; first-notice dates and broker cutoffs remain unmodelled.

11 November F24/F38/F51: [Coupon notifications and read-only inspection](../delivery/coupon-notifications-20261111.md) joins current sourced coupon dates and recorded confirmations in Lifecycle. Review due never means unpaid; financial/cash/P&L treatment stays unassessed. Existing bond notification selection governs visibility; independent coupon controls and receipt reconciliation remain deferred.

11 November F24/F51: [Mixed bond/FX maturity worklist](../delivery/fx-maturity-worklist-20261111.md) adds deliverable-forward discovery, combined server-side filtering/counts, native FX side-panel actions and complete prepared standard/custom-field replay. No payment or operating assistance change is implied; other event detectors remain deferred.

5 November F24/F51: [Lifecycle worklist](../delivery/lifecycle-worklist-20261105.md) adds the menu-accessible bond-maturity detector, scoped chronological and instrument-name/identifier filters/counts,25/50/100 pagination, event inspection and context-preserving handoff to native processing. [Booking UI follow-up](../delivery/lifecycle-booking-ui-20261105.md) separates closing inputs, processing controls and history. It creates no financial effect. At that checkpoint FX discovery was deferred; the 11 November entries above supersede that limit. Other discovery, retained task acknowledgement and billing remain deferred.

5 November F51: implemented [lifecycle subscription ceilings, strategy/event selections and reviewed downgrades](../delivery/lifecycle-assistance-entitlements-20261105.md). Tiers0–3 are server-enforced in bounded bond/FX maturity; native review, user permissions and strategy scope remain independent. General notification discovery and billing remain deferred.

4 November F20/F24/F51: implemented [tenant reference data and strategy trade profiles](../delivery/tenant-reference-data-trade-profiles-20261104.md). Shared tenant sources and field meanings are separate from immutable profile rules and explicit strategy assignments. All supported booking/import/correction and bond/FX maturity consumers resolve the pinned profile; publication does not adopt a version. See delivery for verification, cutover and remaining limits.

4 November F20/F24/F51: [Allocation-preserving maturity](../delivery/lifecycle-allocation-preservation-20261104.md)
adds joint custom-field classification, validated fresh inputs and atomic classified
bond/FX closures. Capability statuses remain unchanged; general lifecycle notifications,
other product handlers and historical reconciliation remain separate.

3 November: [Instrument consistency cleanup](../delivery/instrument-consistency-20261103.md)
removes seed-specific equity creation choices, adds scoped non-ledger source
reassessment and aligns CLEAN bond monetary previews with maintained accrued
stocks. Existing product support/status boundaries remain; source changes create
review work, not rewritten published numbers.

3 November F38/F39: [balance-history trade markers](../delivery/balance-trade-markers-20261103.md)
add a default-on date-aligned Buy/Sell strip, same-day groups, exact booked
accrual/nominal details and trade links. Both valuation-read and trade-read scope
are enforced; annotation failures leave the balance report available. No financial
calculation or lifecycle change; F38 PARTIAL/F39 ALPHA remain.

F38 open investigation — **NOT IMPLEMENTED**: fund distribution/yield accruals.
The [3 November source review](../delivery/daily-accrual-csv-refresh-20261103.md#deferred-fund-distribution--yield-accruals)
retains three fund share classes' source amounts without posting them. Determine
NAV inclusion, recognition/currency and distribution/reset semantics before
extending daily-interest support. The accompanying bond import is data population,
not a new product CSV-upload capability.

3 November F38/F39: [independent accrued-balance explorer](../delivery/accrued-balance-explorer-20261103.md)
adds strategy/instrument/range selection, the full-series chart and exact
25/50/100/All datapoints. It reuses scoped read-only history and needs no daily
validation. This delivers the exploration follow-up below for existing bond
histories; F38 PARTIAL/F39 ALPHA remain.

3 November F38/F39: [two-stage daily interest review](../delivery/interest-daily-review-20261103.md)
replaces the three-tab main maintenance UI with strategy/day daily assessments,
then gated balance review. Whole-population bulk validation, sourced overrides,
weekend-normalized diagnostics and explicit **Reviewed with gaps** retain exact
financial evidence. Drafts do not mutate financial inputs; missing is never zero.
Exploration is deferred. F38 PARTIAL/F39 ALPHA remain.

1 November F38/F39: [Ops interest maintenance](../delivery/interest-ops-workspace-20261101.md)
separates daily interest, sourced closing inputs and derived balance history.
Contextual correction/withdrawal, applied filters, independent loading and explicit
rebuild retain exact revisions, authority and evidence. No automatic accrual,
coupon-reset, accounting or bulk-upload engine added; F38 PARTIAL/F39 ALPHA remain.
The accrued-balance overview shows only the selected To date; each row's chart
retains the complete From-to-To series and exact datapoint table.

1 November F38/F39: [accrued-balance chart and datapoints](../delivery/accrued-balance-chart-20261101.md)
provide a bond/date modal, full-series plotting, explicit missing/stale values and
25/50/100/All exact table pagination. Strategy/module visibility remains enforced;
an existing unrelated-bond selector defect was corrected. No calculation, source,
coupon-reset or accounting behavior changed; F38 PARTIAL/F39 ALPHA remain.

31 October F38/F39: [maintained accrued balances](../delivery/maintained-accrued-balances-20261031.md)
add daily-input → explicit local-stock update → valuation-FX workflow at
`/valuation/interest`. Sourced stock revisions, immutable history, verified
checkpoints and stale-source guards preserve evidence. Optional gaps remain
nonblocking. No automatic accrual model, scheduler, bulk workbook or accounting
flow; F38 PARTIAL/F39 ALPHA remain.

31 October F32/F37: [fund NAV-date correction](../delivery/fund-nav-lag-20261031.md)
sets FCPGF policy v3 to T−1/T−2 fund NAVs with T/T−1 FX, using a new published
weekday valuation calendar. Existing fixed-lag selection is reused; source dates,
other product rules, inactive trades and historical financial evidence are unchanged.


31 October F32/F37/F39: [incomplete-price review and reviewed manual marks](../delivery/incomplete-price-review-20261031.md)
adds explicit WARN/MANUAL_OVERRIDE partial staging, unavailable investment/cash FX
contributions, calculated subtotals and a required-mark publication guard.
Independent append-only mark review applies only after recalculation; source
rights, quote conventions and real-operator independence remain enforced.
F32/F39 ALPHA and F37 PARTIAL remain; this is not an official complete NAV.


30 October F18/F37: [two-floating-leg rate-exchange swaps](../delivery/rate-exchange-swaps-20261030.md)
support governed creation, booking, frozen evidence and separately staged supplied
marks. All four pending FCPGF source executions are posted; independent bank series
and RESET records are preserved. No generated funding/principal flows, general
term amendment. [3 November](../delivery/expanded-position-measures-20261103.md) adds rate-swap reference/whole-mark values; rate-risk sensitivities remain unavailable. F18 ALPHA and F37 PARTIAL remain.

30 October F27/F48: [explicit profiles and shared expensive-work admission](../delivery/dataset-rights-and-workload-20261030.md)
close the missing-profile bypass and add safe backpressure without financial
population caps. Migration 106/seed-origin activation preserve operating data.
Rights administration, production identity, durable worker processing and OS
job budgets remain incomplete; capability statuses remain PARTIAL.

30 October F48: [database/audit/browser security controls](../delivery/security-controls-20261030.md)
are implemented and locally activated with retained operating data. Profiles and
admission are covered by the follow-up above; production authentication remains open;
F48 is PARTIAL. [Operational setup](../platform/security-controls.md).

30 October F03/F48: [local identity containment](../delivery/local-identity-safeguard-20261030.md)
requires verified sessions and private operator bootstrap; demo/header-only
authentication and non-local startup are disabled. Local selector behaviour
remains. Production authentication is deferred; capability statuses are unchanged.

30 October F48: [dependency-security remediation](../delivery/dependency-security-20261030.md)
updates affected locked packages and adds complete recurring audits. Production
identity, audit protection and broader operational acceptance remain separate;
F48 remains PARTIAL. No financial/permission or database change.

29 October F12/F22/F23: [cash-booking domain extraction](../delivery/cash-booking-service-extraction-20261029.md)
shares original cash commands and validators between HTTP and file confirmation.
Statuses/product scope are unchanged. Other booking types, cancellation and
reference/proposal orchestration remain for later extraction.

29 October F53: [Regulatory Reporting preparation](features/regulatory-reporting.md)
is PARTIAL: dedicated module, legal-entity profiles, execution preparation,
reasoned review and immutable preparation exports. Full official field/schema
validation, submission/acknowledgements/corrections and other jurisdictions remain
unimplemented. [Delivery and verification](../delivery/regulatory-reporting-20261029.md).

29 October F38/F39: [compact review signals and accrued stocks](../delivery/valuation-review-signals-20261029.md)
add actual-window cash partial status, interest/stock FX and reconciliation notes,
full-result Attention navigation and local/reporting stock display. No new
publication gate or migration. Realistic mixed-portfolio acceptance awaits data.

28 October F17/F27/F37–F39: [DIRTY bond quotation normalization](../delivery/bond-dirty-to-clean-20261028.md)
uses typed observation-paired accrued per 100 to derive CLEAN, retaining separate
daily earnings/stock FX, original monetary values and current-input publication
checks. No automatic accrued generator or broader bond subtype is implied.

28 October F16/F37/F39: [Linear crypto futures](../delivery/linear-futures-extension-20261028.md)
extend native booking and daily variation to approved asset-unit CASH/PHYSICAL
contracts. Frozen economics and ordinary governed publication remain. Delivery,
margin accounting remains separate; current crypto monetary notional/exposure is covered by the 3 November measure extension.

28 October F12/F36–F39: [non-ETF ETP then spot-crypto P&L](../delivery/etp-spot-crypto-pnl-20261028.md)
preserves wrapper types, frozen factors and listing identity, normalizes historical
cash unit labels and supports explicit crypto cuts/continuous-day coverage.
Existing review/source controls remain; broader product subtypes remain separate.

28 October F15/F37/F38/F39: [Directly held structured-note P&L](../delivery/structured-note-pnl-20261028.md)
adds supplied whole-note marks, frozen quotation factors, optional CLEAN interest
and assessed stock FX, explicit note coupon income and ordinary review/publication.
Migration 102 is locally active; payoff pricing and lifecycle remain deferred.

27 October F16/F37/F39: [futures daily P&L](../delivery/futures-daily-pnl-20261027.md)
connects the bookable cash-settled index slice to reconstruction, governed marks,
multiplier-once variation, closing FX, staging/publication and readable inspection.
No physical/crypto booking, margin cash generation or assessed contract MTM.

27 October review: [valuation achieved versus intended](../delivery/quality-reviews/2026-10-27-valuation-state-review.md)
traces F36–F40 across UI, calculation and schema. Existing PARTIAL/ALPHA statuses
remain appropriate; warning consistency, wider source reassessment, dual-currency
stock presentation and independent end-to-end acceptance remain open.

27 October F38/F39: [accrued-balance FX](../delivery/accrued-balance-fx-20261027.md)
adds source-based stock reconstruction, typed retained balances, CARRY and unpaid
receivables after disposal. Missing optional stocks/FX produce partial coverage;
changed coupon/accrual sources require reassessment. F38 remains PARTIAL: no
automatic earned-interest generation, entitlement or complete accounting.

27 October F38: [full contractual bond schedules](../delivery/bond-cashflow-schedule-20261027.md)
add principal alongside coupons in one retained version. Explicit dates/formulas,
zero-bond principal-only schedules and coupon-only confirmations retain separate
economic boundaries. The subsequent stock-FX extension supplies bounded accrued-stock
derivation; automatic entitlement and DCF remain pending. F38 stays PARTIAL.

26 October F07/F19/F39: [shared instrument display](../delivery/shared-instrument-display-20261026.md)
replaces the bond-only label patch with a common name/identifier/context policy,
exact listing navigation and retained search aliases. ALPHA status remains;
missing business identifiers stay explicit and existing data is not renamed.

26 October F39: [readable position-inspection worksheet](../delivery/position-inspection-manual-check-20261026.md)
puts exact frozen quantities/prices/FX, period trades and the value bridge before
expandable technical proof. Presentation only; existing ALPHA status remains.
The same delivery's bond-label correction prefers current governed ISINs over
internal import codes; no stored reference or financial result is changed.

26 October F38: [zero-coupon accrual applicability](../delivery/zero-coupon-accrual-applicability-20261026.md)
removes missing-interest warnings/strict requirements only for confirmed frozen
ZERO terms. Supplied inputs, maturity checks and stale-publication protection
remain; unknown/mixed terms are not waived. No historical evidence rewrite.

23 October F37/F38: [optional assessed bond accruals](../delivery/optional-bond-accruals-20261023.md)
replace the blanket missing-interest blocker. Price/FX P&L includes supplied
interest and discloses omissions; explicit strict coverage remains available.
Missing is not zero; newly supplied interest requires recalculation before
publication. The UKTB blocker below describes the earlier pre-change run.

The external CSV reconciliation exercise is not product capability delivery.
Its source-specific operators, adapters and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md); retained delivery
records describe that exercise, not a supported upload interface.

30 October F12/F37: [typed fund-unit movements](../delivery/fund-unit-movements-20261030.md)
record transfers and reinvestment credits through an internal native command.
Daily NAV/FX excludes moved principal from market gains; unconfirmed distribution
income remains nonblocking partial coverage. No movement ticket/template or
automatic income is provided. ALPHA/PARTIAL classifications remain unchanged.

23 October F08/F09/F37: [native AMC onboarding, quotation and monetary measures](../delivery/amc-onboarding-20261023.md).
Certificate identity remains distinct while common booking/price/FX machinery is
reused. Unit and percentage quotations are supported with explicit dimensions;
full AMC management F41, look-through and dedicated amendment UI remain deferred.

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
| F08 | [Canonical instruments and contextual listings](features/instrument-management.md#f08-canonical-instruments-and-listings) | ALPHA | Product/date/convention eligibility remains explicit. [Shared/private stewardship direction](features/instrument-management.md#proposed-direction-shared-and-tenant-private-stewardship) recorded 17 October; platform-managed shared publication and type-independent tenant-private creation remain to be specified/verified consistently. |
| F09 | [Creation requests, approval and Operations queue](features/instrument-management.md#f09-requests-and-approval) | ALPHA | Not universal reference stewardship or contractual lifecycle. |
| F10 | [Custom instrument taxonomy](features/instrument-management.md#f10-instrument-taxonomy) | FOUNDATION | Reference classification model; general tenant taxonomy UI absent. |
| F11 | [Safe instrument amendments/version lifecycle](features/instrument-management.md#f11-instrument-amendments-and-lifecycle) | PARTIAL | Historical definitions exist; complete amendment/promotion UX does not. |

## Instrument-specific creation and booking

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F12 | [Plain listed cash booking](features/product-booking.md#f12-plain-listed-cash) | ALPHA | Explicit cash listing boundary, governed ETP terms and native wrapper/token/fund UNITS. [Typed fund movements](../delivery/fund-unit-movements-20261030.md) are native internal commands; ordinary purchases stay positive-price, with no movement ticket/template or generated income. [ETP/spot P&L](../delivery/etp-spot-crypto-pnl-20261028.md) is distinct from booking readiness. |
| F13 | [Deliverable FX forwards](features/product-booking.md#f13-deliverable-fx-forwards) | ALPHA | Booking, maturity closure and bounded rate-based P&L; no NDF, discounted model MTM or signed-off delivery. |
| F14 | [Listed options](features/product-booking.md#f14-listed-options) | ALPHA | OPEN/CLOSE is intent, not inventory validation or exercise. [Supplied-premium P&L](../delivery/option-premium-pnl-20261023.md) applies the frozen multiplier once; no model pricing, Greeks or automatic expiry. |
| F15 | [Listed/OTC structured securities](features/product-booking.md#f15-structured-securities) | ALPHA | [Supplied whole-note P&L](../delivery/structured-note-pnl-20261028.md) uses matching CLEAN/DIRTY/NONE quotations, frozen factors and recorded income; payoff pricing and lifecycle automation remain deferred. [Seeded-note readiness](../delivery/termsheet-note-booking-readiness-2026-10-14.md): six PDF parent notes have approved unit/PCT_OF_PAR dirty OTC conventions; 15 focused tests and app readiness verified. [Terms & Schedule](../delivery/instrument-terms-schedule-2026-10-14.md): read-only approved structured schedules, distinct note/share dates and swap performance-reference look-through are available; lifecycle processing remains separate. |
| F16 | [Future family → contract → listing → booking](features/product-booking.md#f16-futures) | ALPHA | Index and approved linear crypto futures have native booking and daily supplied-price P&L; crypto supports CASH/PHYSICAL terms. Monetary notional/exposure preview stays index-only. No assessed contract MTM, delivery/assignment automation, inverse/perpetual adapter or margin accounting. |
| F17 | [Bond CLEAN/DIRTY booking](features/product-booking.md#f17-bonds) | ALPHA | Assessed execution accrual; [DIRTY market normalization](../delivery/bond-dirty-to-clean-20261028.md) uses separate exact quote evidence. Ops-triggered plain redemption is supported; no automatic accrued/coupon engine. |
| F18 | [Generic swap creation and booking](features/product-booking.md#f18-generic-swaps) | ALPHA | Performance and [two-floating-leg rate exchanges](../delivery/rate-exchange-swaps-20261030.md), with separate component identities/prices, typed leg currencies/notionals and guarded first-time reference completion. Nominal/unit whole-swap quotes and supplied-mark P&L retain factors once. No general payoff/funding model, generated payments or general term-amendment workflow. |

## Trade operations

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F19 | [Dedicated enriched booking and readiness](features/trade-operations.md#f19-booking-console-and-readiness) | ALPHA | Advisory readiness; writer remains authoritative. |
| F20 | [Tenant-governed properties and catalogues](features/trade-operations.md#f20-governed-trade-properties) | ALPHA | Shared sources, immutable field meanings and strategy-pinned profiles; 1,000 active definitions per tenant, manual curation and explicit adoption. |
| F21 | [Trade history and frozen detail](features/trade-operations.md#f21-history-and-detail) | ALPHA | Not a complete settlement/accounting or export workspace. |
| F22 | [Cancel/replace erroneous bookings](features/trade-operations.md#f22-record-corrections) | ALPHA | Record correction is not a market unwind; P&L replay is bounded. |
| F23 | [Historical booking and valuation recognition date](features/trade-operations.md#f23-historical-and-recognition-dates) | ALPHA | Explicit date override; information cutoff still matters. |
| F24 | [Contractual delivery, expiry, reset and redemption](features/trade-operations.md#f24-contractual-lifecycle) | PARTIAL | Plain-bond redemption and deliverable FX maturity closure feed bounded P&L; cash/delivery separate, bond/FX maturity workflows, read-only coupons and independent futures/option deadline notices available; other event discovery deferred. |
| F51 | [Tenant lifecycle handling modes](features/trade-operations.md#f51-tenant-lifecycle-handling-modes) | ALPHA | Typed0–3 subscription ceiling, scoped strategy/event choice, reviewed downgrades and bond/FX prepare/confirm/approve/book/cancel; Bond/FX maturity, read-only coupon, futures and option notices delivered; futures/option selection supports0/1 only, and coupon visibility shares the bond setting. Other discovery, persisted task assignment and billing deferred. |

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

## Tenant data onboarding and file imports

External reconciliation scripts are separate from F59. See the
[isolated tooling scope](../../tooling/reconciliation_csv/README.md).
No new supported dataset family is implied.

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F59 | [Governed tenant file imports](features/tenant-data-imports.md#f59-governed-tenant-file-imports) | PARTIAL | NEW listed equity/ETF/fund imports: tenant-aware Excel/CSV, optional/custom fields, backend validation, atomic confirmation and durable replay/row receipts at `/imports`. One strategy and 500 rows/512 KiB per file; no partial booking. Other products/datasets, bulk corrections, queued processing and retention cleanup remain absent. [Delivery and acceptance limits](../delivery/trade-imports-20261018.md). |

## Valuation and P&L

| ID | Desired feature / detailed Markdown record | Status | Main remaining boundary |
| --- | --- | --- | --- |
| F36 | [Relevant positions from immutable trade history](features/valuation-and-pnl.md#f36-position-reconstruction) | ALPHA | No total 1,000-trade cap; reviewed basic share-ratio replay. Complex entitlements/transformations and historical scaling remain bounded. |
| F37 | [Market P&L and position monetary measures](features/valuation-and-pnl.md#f37-economic-valuation) | PARTIAL | [Whole-swap marks](../delivery/swap-supplied-mark-pnl-20261023.md) and [listed-option premiums](../delivery/option-premium-pnl-20261023.md) use frozen factors once; [linear index/crypto futures P&L](../delivery/linear-futures-extension-20261028.md) uses daily price variation and closing FX with cash/physical crypto terms; [fully funded note P&L](../delivery/structured-note-pnl-20261028.md) uses supplied whole-note marks and optional assessed CLEAN interest/stocks. [Non-ETF ETPs and spot digital assets](../delivery/etp-spot-crypto-pnl-20261028.md) now use type-preserving cash economics, quote-currency FX and explicit crypto-day calendars. [Expanded position measures](../delivery/expanded-position-measures-20261103.md) report native/fund values for spot crypto, linear index/crypto futures, option strike notional/premium values, funded notes and whole-mark performance/rate swaps. Unmodelled option/note/rate exposure and forward/futures clearing MTM remain unavailable. Exact inspection retained. No weights, measure publication, modelled resets, automatic option expiry or generic derivative pricer. |
| F38 | [Daily bond/note accrual and economic income/cost flows](features/valuation-and-pnl.md#f38-accruals-and-economic-flows) | PARTIAL | Assessed daily inputs, independent bond-stock revisions and explicit maintained-history updates at `/valuation/interest`; source-verified balance FX, coupon receipts and income stay separate. CLEAN-note adapters remain; DIRTY notes do not add embedded interest twice. Optional gaps remain nonblocking. No accrual model, scheduler, bulk stock upload or detached note receivables. |
| F39 | [Stage → amendment → governed publication](features/valuation-and-pnl.md#f39-review-and-publication) | ALPHA | [Four report views](../delivery/valuation-report-tabs-20261026.md), business labels, instrument-type column/full-result filter, exact source coverage, 25/50/100/All position pagination, closable inspector/full-width table, separate typed cash lines and contextual publication confirmation. Shared totals/blockers and governed publication stay visible; URL navigation and drafts retained. Relevant source changes block stale publication. Independent/default-off scoped self-publication unchanged. No completeness assurance, full NAV or broad independent financial sign-off. |
| F40 | [Full strategy/fund NAV and cash balance valuation](features/valuation-and-pnl.md#f40-full-nav-and-cash-balances) | PARTIAL | Dated balance register/translated preview plus [standard daily cash FX P&L](../delivery/cash-fx-pnl-20261025.md) staged/published per account/currency. No exclusion switch; actual valuation-window gaps are visible/non-blocking, never zero. Old/disappeared scopes do not create continuing upload warnings. Supplied nonzero foreign cash requires eligible FX; relevant source changes still block stale publication. No intraday movement P&L, full cash-stock publication or fund NAV. |

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
| F53 | [Regulatory Reporting](features/regulatory-reporting.md) | PARTIAL | UK transaction preparation/review and retained preparation exports; official mapping/acceptance, submission lifecycle and other regimes remain. |
| F54 | [AI-assisted termsheet parsing and instrument creation](features/future-modules.md#f54-ai-assisted-termsheet-parsing-and-instrument-creation) | NOT IMPLEMENTED | Full-instrument assisted editing and unattended submission into checking prioritized 2026-10-13; design approved, execution plan proposed for review, real-termsheet acceptance unverified. [All-four reviewed load](../delivery/all-reviewed-autocalls-loaded-2026-10-14.md): all four note/share bundles plus two Phoenix notes ACTIVE in app DB; 40 focused tests and replay/lookup verified. Explicit operator seed, not integrated AI ingestion. |
| F55 | [AI-assisted portfolio and investment-idea recommendations](features/future-modules.md#f55-ai-assisted-portfolio-and-investment-idea-recommendations) | NOT IMPLEMENTED | Desired recommendations from current portfolio/guidelines or textual hints/ideas; specification postponed. |
| F56 | [Option and structured-product Greeks with cross-asset look-through risk](features/future-modules.md#f56-option-and-structured-product-greeks-with-cross-asset-look-through-risk) | NOT IMPLEMENTED | Desired Greeks feeding cross-asset risk and underlying look-through analytics; models, coverage and specification postponed. |
| F46 | [Portfolio risk and solution diagnostics](features/future-modules.md#f46-portfolio-risk-and-diagnostics) | NOT IMPLEMENTED | Commercial research, not a validated analytics engine. |
| F47 | [Settlement and accounting](features/future-modules.md#f47-settlement-and-accounting) | DEFERRED | Explicitly postponed; no posting engine or reconciliation module. |
| F48 | [API quality and production operations](features/platform-quality.md#f48-api-and-operational-hardening) | PARTIAL | Alpha controls/tests; scalable production operations still pending. |
| F49 | [Frontend usability/accessibility acceptance](features/platform-quality.md#f49-frontend-acceptance) | PARTIAL | Shared styles and contextual workflow guides; [26 October HTML/console review](../delivery/quality-reviews/2026-10-26-frontend-console-integrity.md) repairs disclosure nesting and native patterns and adds a browser diagnostics guard. Broader live visual/assistive sign-off remains open. |
| F50 | [Automated reference/provider onboarding](features/platform-quality.md#f50-automated-reference-onboarding) | FOUNDATION | Proposals/mappings exist; complete multi-provider onboarding absent. |

## Adding a desired feature

1. Append the next unused `Fnn` ID; never recycle or renumber IDs.
2. Add a capability section to the relevant `features/*.md` record (or a new focused file).
3. State desired outcome and origin: user agreement, documented direction, or proposed idea. A proposal is not approved implementation scope.
4. Record status, backend and frontend separately, evidence links, deliberate cuts/trade-offs, weaknesses, and concrete remaining work. Use “not verified” where evidence is absent.
5. Add the summary row here, with an actual Markdown link to the detailed record and its principal boundary. Review both after implementation; retain dated evidence rather than rewriting history.

## Review and evidence boundary

See the [documentation reconciliation report](../delivery/quality-reviews/2026-10-12-documentation-reconciliation.md) for inspected scope, discovered drift, research and verification. No application tests, database writes, deployment, commit or GitHub push are implied by a documentation update. Prior merge verification is retained in the [merge record](../delivery/tenant-access-administration-progress.md#completed-remediation-verification); it was partitioned diagnostics plus successful focused fixes, not one clean full-suite rerun.

11 November: [Lifecycle closing-entry drawer](../delivery/lifecycle-action-panel-20261110.md) embeds the existing governed maturity workflow in the worklist, preserving filters and guarded financial retries; full-workspace access remains available. Direct and independently approved booking passed real isolated BFF/API/PostgreSQL acceptance; current ledger checks use database recording time. The normal app was subsequently [recovered on port15432](../delivery/local-postgres-port-recovery-20261111.md) with existing data; operating financial acceptance remains separate.
