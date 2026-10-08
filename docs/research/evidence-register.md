# Evidence register

Yahoo personal-project ingestion and layered-rights sources checked on 6 October 2026, including licensing limitations and project-specific decisions, are recorded in the [delivery report](../delivery/yahoo-market-data-alpha.md#best-practice-review-and-decisions).

**Status:** Draft  
**Content type:** Research  
**Owner:** Product and architecture team  
**Last reviewed:** 2026-10-07

Primary research records: [external evidence register](../../security-master-notes/24-external-evidence-and-research.md), [range accrual and supertracker research](../../security-master-notes/28-range-accrual-and-supertracker-research.md), [Phoenix research/UI scope](../superpowers/specs/2026-09-10-phoenix-research-and-ui-scope.md), [market evidence and go-to-market](../../fintech-moduls/06-market-evidence-and-go-to-market.md), and [competitor technical operating models](../../fintech-moduls/07-competitor-technical-operating-models.md).

External sources cited by these records must be rechecked when a decision depends on time-sensitive law, licensing, vendor policy, or market practice.

## Market data module boundary

Architecture sources reviewed on 7 October 2026 (Microsoft dependency direction/composition, Fowler's modular-monolith trade-offs and Import Linter contracts) are recorded with dates, applicability and implementation choices in [Market data ingestion boundary](../delivery/market-data-ingestion-boundary.md#best-practice-evidence-and-decisions). No distributed-service or new licensing requirement is inferred from this refactor.

## Tenant fund and strategy calendars (2026-10-07)

Primary-source findings from BlackRock's 2026 fund-specific non-business/non-dealing schedule and QuantLib's joint-calendar implementation are recorded, with links and applicability, in [Tenant fund and strategy calendars](../delivery/tenant-fund-and-strategy-calendars-alpha.md#source-backed-design). They informed separate fund schedules, explicit dated exceptions and ALL_OPEN / ANY_OPEN composition. A dealing holiday does not establish a NAV holiday. Immutable publication, recorded-time assignment selection and UNKNOWN coverage are platform design decisions, not asserted universal regulatory obligations. Reference-calendar feeds remain unpopulated or incomplete until separately sourced and reviewed.

Futures onboarding sources reviewed on 2026-10-02 (CME month codes and platform
symbol conventions, ICE Bitcoin size/quote/delivery distinctions and GOV.UK form
grouping) are recorded with applicability and project decisions in
[Futures creation and contract conventions alpha](../delivery/futures-creation-and-contract-conventions-alpha.md#best-practice-evidence-and-project-decisions).

## Structured product and futures booking proposal (2026-10-01)

The [reviewed booking plan](../superpowers/plans/2026-10-01-structured-product-and-futures-booking.md) records inspected code/schema gaps and primary-source research from ANNA DSB, SIX and CME. It separates ISIN from listing/execution route, funded structured securities from bilateral derivatives, unit/nominal quotation conventions, and futures contract value from purchase payments. Source dates and limits are explicit. Funded listed/OTC securities and cash-settled index futures are bounded project restrictions, not universal requirements. The [delivery report](../delivery/structured-security-and-futures-booking-alpha.md) records implementation and verification. CME's multiplier/tick example and margin guidance were reopened on 2026-10-01 during implementation review. Valuation, margin and lifecycle processing remain outside scope.

## Option booking and lifecycle boundary (2026-10-01)

The [agreed booking and lifecycle scope](../delivery/booking-and-lifecycle-scope.md#research-and-applicability) records inspected implementation, research links/applicability and the decision to extend booking without implementing settlement/positions/valuation first. It covers FIX PositionEffect, FINOS CDM events/transfers, BIS FX finality/netting, OCC/OIC contract and open/close conventions, and CME premium styles. Initial listed fixed-strike upfront-premium option support is a project boundary; OTC options and lifecycle processing remain deferred. This is not an option-delivery claim.

## FX-forward booking decision (2026-10-01)

The approved [FX-forward design](../superpowers/specs/2026-10-01-deliverable-fx-forward-booking-design.md) and [booking delivery](../delivery/fx-forward-booking-alpha.md) preserve the following researched evidence and scope:

- [OpenGamma FxSingle](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/fx/FxSingle.html): two currency payments can belong to one economic product; separate payment dates exist. A single agreed date is this alpha's restriction, not a universal rule.
- [OpenGamma FX measures](https://strata.opengamma.io/fx_single/): forward rate and present value are distinct measures. A rate-like provider observation must not silently become monetary MTM.
- [OpenGamma FxNdf](https://strata.opengamma.io/apidocs/com/opengamma/strata/product/fx/FxNdf.html): fixing-observation/payment economics differ; NDF booking is deferred.
- [OpenGamma DiscountFactors](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/DiscountFactors.html) and [collateral framework](https://quant.opengamma.io/Multi-Curve-Framework-with-Collateral-OpenGamma.pdf): currency/date curves and collateral assumptions matter. No universally correct OIS selection or guessed DF=1 is asserted.
- [CME FX MTM methodology (2012), pp. 3–4](https://www.cmegroup.com/rulebook/files/s_6105_otc_fx_pai_cash_mk_to_mkt_ser_020112_revised.pdf): historical rate-difference/notional/discount-factor methodology, not a claim about every current clearing arrangement.
- [ESMA EMIR REFIT guidance (2023), §3.18](https://www.esma.europa.eu/sites/default/files/2023-10/ESMA74-362-2281_Guidelines_EMIR_REFIT.pdf): applicable reporting uses signed monetary contract valuations. This does not prescribe internal database structure or apply universally to tenants/jurisdictions.

Implementation preserves raw/economic distinctions and explicitly rejects FX-containing strategies in the existing cash-only P&L engine. Provider semantics, discount curves, reconciliation and settlement accounting require separate design/approval.

Trade-history UI sources reviewed on 2026-09-30 (Cloudscape table/resource views,
Carbon data tables/pagination, and W3C accessible tables), their applicability,
and the resulting project decisions are recorded in
[Trade history alpha](../delivery/trade-history-alpha.md#best-practice-references-and-project-decisions).

Enriched-booking UX/security sources reviewed on 2026-09-30, with applicability
and project-specific decisions, are recorded in
[Enriched trade booking alpha](../delivery/enriched-trade-booking-alpha.md#research-and-boundaries).

Governed trade configuration sources reviewed on 2026-10-01 (Microsoft reusable
choices, Reltio canonical values and OWASP multi-tenant security), including their
applicability and project decisions, are recorded in
[Governed trade configuration alpha](../delivery/governed-trade-configuration-alpha.md#best-practice-evidence-and-project-decisions).

Trade-field administration UX sources reviewed on 2026-10-01 (IBM Carbon tables,
NN/G progressive disclosure, GOV.UK tabs/error summaries and W3C WAI-ARIA tabs),
including source dates, applicability and implementation choices, are recorded in
[Trade configuration UI refresh](../delivery/trade-configuration-ui-alpha.md#online-evidence-and-project-decisions).

Booking-property form sources reviewed on 2026-10-01 (W3C WAI grouping and
GOV.UK optional labels, hints and field errors), with applicability and the
project's grouping/search decisions, are recorded in
[Trade booking property section refresh](../delivery/trade-booking-properties-ui-alpha.md#best-practice-evidence).
