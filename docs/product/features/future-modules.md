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
