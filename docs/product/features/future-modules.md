# Broader product directions and deferred operations

**Status:** Maintained reference  
**Content type:** Capability/backlog reference  
**Owner:** Product/operations  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). These are discussed/documented directions, not newly approved implementation commitments. Module/operating-profile names in the database do not certify product delivery.

## F41 AMC management

- **Desired:** Manage an AMC vehicle and its strategy/operational configuration.
- **Status / backend / frontend:** FOUNDATION. AMC profile/module and strategy type exist; generic trading/reference/P&L foundations, no complete dedicated AMC management workflow.
- **Cuts/trade-offs:** Reuse platform building blocks rather than a premature separate engine.
- **Weaknesses:** Vehicle issuance, issuer/admin interfaces, fees and dedicated operational lifecycle missing.
- **Remaining:** Define the actual AMC workflow and authority/data/valuation requirements before implementation.
- **Evidence:** [Module/profiles](../../architecture/tenancy-and-entitlements/tenant-capabilities-and-operating-profiles.md), [module portfolio](../../../fintech-moduls/README.md), [strategy alpha](../../delivery/tenant-workspace-strategy-alpha.md).

## F42 Fund operations

- **Desired:** Tenant fund/share-class administration, provider IDs and operational feeds.
- **Status / backend / frontend:** FOUNDATION. Approved effective-dated `cfg` mapping profiles/object mappings and resolver implemented; no complete fund-operations ingestion/review/reconciliation UI.
- **Cuts/trade-offs:** Canonical provider/vehicle identity separate from tenant feed codes; report business date selects mapping.
- **Weaknesses:** End-to-end admin/custodian feed workflows and full NAV/accounting are not established.
- **Remaining:** Curated mapping administration, real feed adapters, source/row provenance and reconciled operations; do not confuse schema/resolver completion with module completion.
- **Evidence:** [Mappings](../../architecture/trading-and-operations/tenant-fund-operational-mappings.md), [operating model](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md).

## F43 Structured-product management

- **Desired:** Terms, schedules, event/payoff lifecycle and complete operational product management.
- **Status / backend / frontend:** PARTIAL. Bounded terms/components/barriers, onboarding and security booking exist; full product monitoring/valuation/lifecycle does not.
- **Cuts/trade-offs:** Preserve reference instruments even for OTC payoffs; no universal payoff engine inferred from template availability.
- **Weaknesses:** Complex payoff, reset/autocall/redemption execution and validated model inputs incomplete.
- **Remaining:** Independently scope event evaluation, payoff/valuation and operational management, building on F15/F18.
- **Evidence:** [Terms](../../../security-master-notes/27-structured-product-terms-and-coupon-memory.md), [current booking](../../delivery/structured-security-and-futures-booking-alpha.md), [lifecycle direction](../../../fintech-moduls/03-otc-and-structured-product-lifecycle.md).

## F44 Structured-product distribution

- **Desired:** Client/distribution linkage, suitability and chargeable distribution operations.
- **Status / backend / frontend:** NOT IMPLEMENTED. Profile/module metadata exists; no reviewed dedicated end-to-end workflow.
- **Cuts/trade-offs:** Product creation/booking is not distribution.
- **Weaknesses:** Client/suitability/approval/service-fee operational model and UI missing.
- **Remaining:** Define and implement jurisdiction/client-specific scope only when prioritized.
- **Evidence:** [Commercial module portfolio](../../../fintech-moduls/README.md), [capability catalogue](../../architecture/tenancy-and-entitlements/tenant-capabilities-and-operating-profiles.md).

## F45 UCITS-AIF and liquidity controls

- **Desired:** Governed fund-control policies, evidence, breach handling and liquidity monitoring.
- **Status / backend / frontend:** NOT IMPLEMENTED. Research and UCITS module label exist; no accepted monitored compliance engine/UI.
- **Cuts/trade-offs:** Research is not a compliance claim or complete requirements specification.
- **Weaknesses:** Validated exposure/look-through, jurisdiction-specific rules, control ownership and operational breach evidence missing.
- **Remaining:** Confirm regulated scope, source authoritative rules and implement/test controls plus review workflows when authorized.
- **Evidence:** [Research](../../../fintech-moduls/02-ucits-aif-controls-and-liquidity.md), [module index](../../product/fintech-modules/README.md).

The more specific desired [strategy and pre-trade UCITS assessment](#f52-strategy-and-pre-trade-ucits-assessment) is recorded separately, without implying that the broader module is implemented.

## F46 Portfolio risk and diagnostics

- **Desired:** Exposure/risk and product-solution diagnostics based on reliable holdings/market inputs.
- **Status / backend / frontend:** NOT IMPLEMENTED. Commercial research and shared position/data foundations only; no validated risk analytics product.
- **Cuts/trade-offs:** Booking multipliers/position quantities are necessary, not sufficient, for risk or model correctness.
- **Weaknesses:** Validated risk methodologies, sensitivity/scenario inputs, limits and operational UI absent.
- **Remaining:** Scope risk measures and acceptance separately; do not describe P&L or a frozen factor as a risk engine.
- **Evidence:** [Product direction](../../../fintech-moduls/05-portfolio-risk-and-solution-diagnostics.md), [position foundation](../../delivery/position-reconstruction-foundation.md).

## F47 Settlement and accounting

- **Desired:** Later obligations, transfer confirmation, cash/security accounting and reconciliation.
- **Status / backend / frontend:** DEFERRED. User postponed this; snapshot/schema and bounded FX-delivery evidence exist, not a signed-off posting/reconciliation module.
- **Cuts/trade-offs:** Trade, amount due, income recognition and payment settlement are different facts. Maturity and payment alone do not generate an opposite trade.
- **Weaknesses:** Authoritative cash movement ownership, ledger accounting, netting/allocations and complete reconciliation missing.
- **Remaining:** Resume with scoped obligations/transfers and one authoritative posting path, avoiding duplicate cash/income recognition. Existing F24 is parked, not sign-off.
- **Evidence:** [Scope ruling](../../delivery/booking-signoff-and-lifecycle-execution.md), [FX evidence slice](../../delivery/fx-delivery-lifecycle-alpha.md), [market versus accounting boundary](../../delivery/economic-pnl-agreed-foundation-2026-10-09.md).

## F52 Strategy and pre-trade UCITS assessment

- **Desired:** Assess a given strategy against its applicable UCITS guidelines at any selected date/time, and assess the resulting strategy if a list of potential trades were booked.
- **Origin:** User-requested addition to the desired list on 12 October 2026. Requirements only; no specification or implementation requested yet.
- **Status / backend / frontend:** NOT IMPLEMENTED. No reviewed strategy-level UCITS assessment engine, as-of assessment screen or proposed-trade assessment workflow is implemented.

| Context | Desired assessment |
| --- | --- |
| Strategy at a selected time | Assess the strategy's actual state against the applicable UCITS guidelines at the chosen date/time, including historical assessment. |
| Pre-trade proposed list | Assess the hypothetical resulting strategy after applying the proposed list of trades together; show how guideline adherence would change relative to the actual strategy. |

- **Cuts/trade-offs:** Actual strategy state and hypothetical trade effects remain distinguishable. Assessment of proposed trades does not itself book them. No automatic booking block, approval or override policy is decided by this desired-list entry.
- **Weaknesses:** Applicable guideline/rule versions, reliable historical inputs and validated UCITS calculations are not yet established as an end-to-end workflow.
- **Remaining:** Guideline applicability, jurisdiction, time/evidence semantics, proposed-trade inputs and assessment presentation are intentionally left for later specification. Authoritative regulatory sources and calculation acceptance will be needed when that work is scoped.
- **Evidence / related capabilities:** User request recorded above; [broader UCITS/AIF controls](#f45-ucits-aif-and-liquidity-controls), [strategy ownership](access-and-strategies.md#f05-strategies), [position reconstruction](valuation-and-pnl.md#f36-position-reconstruction), and [risk diagnostics direction](#f46-portfolio-risk-and-diagnostics). Existing foundations do not establish UCITS compliance or delivery of this assessment.

## F53 Regulatory reporting across jurisdictions

- **Desired:** Support applicable regulatory reporting for the UK (including FCA reporting), EU jurisdictions and Switzerland, including daily reporting where applicable and comparable reporting workflows across those jurisdictions.
- **Origin:** User-requested addition to the desired list on 12 October 2026. Requirements only; no specification or implementation requested yet.
- **Status / backend / frontend:** NOT IMPLEMENTED. No reviewed regulatory report production/submission workflow or reporting administration workspace is implemented for this capability.
- **Cuts/trade-offs:** Reporting scope and frequency must follow the relevant regime and reporting entity. The user's daily FCA reporting example is a desired use case, not a claim that every UK/EU/Swiss entity has the same daily obligation or report format.
- **Weaknesses:** Applicable obligations, reporting entities, required data, formats, deadlines and submission channels have not yet been established for this desired capability.
- **Remaining:** Identify the specific reports and jurisdictions, authoritative requirements, frequencies and reporting scope during later specification; then scope preparation, review, submission and correction/status evidence. No report template, automatic submission or reporting schedule is specified yet.
- **Evidence / related capabilities:** User request recorded above; [fund operations](#f42-fund-operations), [UCITS/AIF controls](#f45-ucits-aif-and-liquidity-controls), and [strategy/pre-trade UCITS assessment](#f52-strategy-and-pre-trade-ucits-assessment). Regulatory reporting is a separate desired workflow; those foundations do not establish reporting delivery or regulatory acceptance.

## F54 AI-assisted termsheet parsing and instrument creation

Latest [reviewed data load](../../delivery/all-reviewed-autocalls-loaded-2026-10-14.md):
all four autocalls and their separate share layers, plus two direct Phoenix notes,
are in the app DB under recorded source/default assumptions. This explicit
operator load does not activate integrated AI ingestion or a provider.

[Reviewed Citi wrapper data load](../../delivery/citi-class-1562-seed-2026-10-14.md)
on 14 October installed the wrapper schema and loaded XS3446382098 plus its
Class 1562 share after user review. This does not implement/activate integrated
AI ingestion or a live provider in this checkout.

- **Desired:** Use AI to parse termsheets and extract the economic terms needed to create OTC instruments or structured products through the platform's instrument-creation workflow.
- **Origin:** Added to the desired list on 12 October 2026; user prioritized building the structured-product ingestion foundation on 13 October 2026, then testing real termsheets. The [written design](../../superpowers/specs/2026-10-13-structured-product-termsheet-ingestion.md) is approved, explicitly including underlyings, issuer/parties, dates, currency and amounts as well as schedules. The [execution plan](../../superpowers/plans/2026-10-13-structured-product-termsheet-ingestion.md) is proposed for review.
- **Status / backend / frontend:** NOT IMPLEMENTED. Existing proposal/approval and manual builder foundations were reviewed; no integrated intake, extraction, persisted ingestion draft or unattended submission workflow is delivered yet.
- **Cuts/trade-offs:** Two agreed modes: assisted ingestion populates editable frontend inputs and the same creation schedule; unattended ingestion submits a validated draft directly into the existing checking workflow without a user pressing Create. Approval remains separate. Missing/conflicting/unsupported terms block unattended submission. Source evidence and explicit schedule exceptions must be retained.
- **Weaknesses:** The reviewed creation path silently ignores unknown input fields/defaults missing coupon values, accepts headline/row coupon disagreement, generates payment lags without calendar holidays, and lacks explicit source-payload ownership checking. See [scoped findings](../../../FIX.md). Real-termsheet accuracy and live AI/provider/browser acceptance remain unverified.
- **Remaining:** Review the execution plan, implement the common builder, full-instrument extraction/evidence contract, intake/revision storage, reference resolution, readiness gates and both submission modes with synthetic fixtures. Then verify representative real termsheets independently. Initial ingestion targets existing autocall/Phoenix/Athena templates; broader OTC/template coverage and provider activation remain separate work.
- **Evidence / related capabilities:** User request recorded above; [instrument requests and approval](instrument-management.md#f09-requests-and-approval), [structured securities](product-booking.md#f15-structured-securities), [generic swaps](product-booking.md#f18-generic-swaps), and [structured-product management](#f43-structured-product-management). Existing creation paths do not establish an integrated AI termsheet workflow or trade-booking capability for every extracted product.

## F55 AI-assisted portfolio and investment-idea recommendations

- **Desired:** AI-assisted recommendations informed by the current portfolio and its applicable guidelines, or generated from textual investment hints and ideas.
- **Origin:** User-requested addition to the desired list on 12 October 2026. Requirements only; no specification or implementation requested yet.
- **Status / backend / frontend:** NOT IMPLEMENTED. No reviewed AI portfolio recommendation engine or text-to-investment-recommendation workflow is implemented.

| Starting context | Desired recommendation behavior |
| --- | --- |
| Current portfolio and guidelines | Use the portfolio's current holdings and applicable guidelines to inform recommendations. |
| Textual hints or ideas | Interpret user-supplied investment hints or ideas and generate relevant recommendations; portfolio and guideline context may also be supplied. |

- **Cuts/trade-offs:** Portfolio guidelines are broader than UCITS rules alone. Recommendations remain distinguishable from approved decisions or booked trades; automatic execution is not requested. Specific recommendation outputs and their validation workflow remain undecided.
- **Weaknesses:** Required portfolio/guideline inputs, model accuracy, explainability and recommendation evaluation have not yet been established for this desired capability.
- **Remaining:** Scope guideline interpretation, textual input, recommendation types, supporting rationale and evaluation during later specification. AI/model choice, user-review workflow and any link to hypothetical pre-trade assessment remain undecided.
- **Evidence / related capabilities:** User request recorded above; [strategy ownership](access-and-strategies.md#f05-strategies), [position reconstruction](valuation-and-pnl.md#f36-position-reconstruction), [portfolio risk and diagnostics](#f46-portfolio-risk-and-diagnostics), and [strategy/pre-trade UCITS assessment](#f52-strategy-and-pre-trade-ucits-assessment). These foundations do not establish an AI recommendation workflow.

## F56 Option and structured-product Greeks with cross-asset look-through risk

- **Desired:** Compute Greeks for options and structured products, and use those sensitivities for cross-asset risk and look-through analytics.
- **Origin:** User-requested addition to the desired list on 12 October 2026. Requirements only; no specification or implementation requested yet.
- **Status / backend / frontend:** NOT IMPLEMENTED. No reviewed end-to-end option/structured-product Greeks engine or cross-asset sensitivity/look-through analytics workspace is implemented.

| Capability | Desired outcome |
| --- | --- |
| Instrument Greeks | Compute supported sensitivities for options and structured products from their economic terms and required model/market inputs. |
| Cross-asset risk | Use instrument sensitivities and portfolio holdings to analyse risk across asset classes. |
| Look-through analytics | Look through options and structured products to their underlying risk exposures and sensitivities for portfolio analysis. |

- **Cuts/trade-offs:** Existing product terms, booking and position reconstruction are foundations; they do not establish derivative pricing, Greeks or a validated risk engine. Supported products, Greeks, models, units and aggregation conventions remain undecided.
- **Weaknesses:** Validated pricing/sensitivity models, required market inputs, underlying risk mappings and portfolio aggregation are not established as an end-to-end workflow.
- **Remaining:** Scope product/model coverage, sensitivities, cross-asset and look-through methodology, inputs and analytical presentation during later specification; define model validation and comparison evidence before claiming supported risk calculations.
- **Evidence / related capabilities:** User request recorded above; [listed options](product-booking.md#f14-listed-options), [structured securities](product-booking.md#f15-structured-securities), [structured-product management](#f43-structured-product-management), [position reconstruction](valuation-and-pnl.md#f36-position-reconstruction), and [portfolio risk and diagnostics](#f46-portfolio-risk-and-diagnostics). Recording this desire does not extend current derivative valuation support.

## Read-only contractual inspection — 14 October 2026

F15/F43 now expose approved structured-product Terms & Schedule and swap-reference look-through from instrument details. Note/share layers retain distinct dates; missing swap dates remain explicit. See [delivery and verification](../../delivery/instrument-terms-schedule-2026-10-14.md). Current lifecycle/valuation capability status is unchanged.
