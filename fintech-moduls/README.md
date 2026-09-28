# Fortem fintech modules

> **Legacy product-module index.** Start from the maintained [fintech-modules index](../docs/product/fintech-modules/README.md) and [project documentation home](../docs/README.md). These detailed commercial and research notes remain available; their pre-reorganisation snapshot is in the [archive](../docs/archive/2026-09-10-pre-reorganisation/README.md).

This folder describes five client-facing software and managed-service modules that can be built incrementally on top of Fortem's canonical reference-data and market-data plane.

The purpose is not to replace an OMS, IBOR, fund administrator, accounting system, or risk engine in one project. Each module provides a narrow, commercially meaningful control or operational workflow, integrates with existing systems, and preserves enough provenance to reconcile outputs to the client's established process.

The commercial and regulatory claims in these module notes are intentionally
labelled as sourced evidence, planning assumptions, or open research. The
security-master evidence register records the same discipline for the shared
technical foundation: [external evidence and research register](../security-master-notes/24-external-evidence-and-research.md).

## Modules

1. [Portfolio valuation control and market-data provenance](01-valuation-control-and-provenance.md)
2. [UCITS/AIF controls and liquidity-risk workbench](02-ucits-aif-controls-and-liquidity.md)
3. [OTC and structured-product lifecycle hub](03-otc-and-structured-product-lifecycle.md)
4. [Instrument onboarding, identifier, and corporate-action control](04-instrument-onboarding-and-corporate-actions.md)
5. [Portfolio risk and investment-solution diagnostics](05-portfolio-risk-and-solution-diagnostics.md)
6. [Market evidence, competition, pricing confidence, and discovery plan](06-market-evidence-and-go-to-market.md)
7. [Competitor technical operating models](07-competitor-technical-operating-models.md)

## Shared product principles

* **Canonical identity is Fortem-generated.** Provider codes are effective-dated mappings, never primary identity.
* **Data rights are explicit.** Ingestion, retention, processing, and client display are separately governed by provider, dataset, licence, and tenant entitlement.
* **Shared facts; tenant-specific decisions.** Shared reference data and authorised normalised observations can be stored once. Positions, private instruments, aliases, valuation policies, overrides, and outputs remain tenant-scoped.
* **No silent mutation.** Source facts, canonical approvals, observations, overrides, and calculated outputs retain immutable lineage and versioning.
* **Every control result is reproducible.** A result stores its policy, input snapshot, code/version, calculation time, user/service actor, and source lineage.
* **Integrate before replacing.** Existing OMS, administrator, custodian, risk, accounting, and Python processes remain systems of record until reconciliation proves a controlled migration is safe.

## Recommended delivery sequence

Build the common reference-data and market-data control plane first, but market it through a useful workflow:

```text
Phase 1  Instrument onboarding + authorised EOD data + valuation exceptions
Phase 2  OTC / structured product lifecycle and valuation evidence
Phase 3  UCITS controls and liquidity scenarios
Phase 4  Portfolio diagnostics and client/distributor outputs
```

The likely first customer is a UK/EU manager with a £2bn–£20bn asset base, open-ended funds or mandates, derivatives/structured exposure, multiple data sources, and a concrete control or operational trigger. A targeted first-year engagement should normally aim for a six-figure annual contract plus scoped implementation, not a low-price generic pilot.

## Regulatory and market context

* ESMA has highlighted deficiencies in valuation policies, stressed-market valuation, valuation independence, and early detection of valuation errors: [ESMA valuation findings](https://www.esma.europa.eu/press-news/esma-news/esma-report-points-out-improvements-needed-supervision-asset-valuation).
* UCITS requires an effective risk-management process and accurate, independent OTC-derivative valuation: [UCITS Article 51](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/ucits/article-51).
* ESMA liquidity-stress-test guidance requires embedding liquidity testing into risk management, governance, reporting, and escalation: [ESMA LST guidelines](https://www.esma.europa.eu/document/guidelines-liquidity-stress-testing-in-ucits-and-aifs).
* ISDA FpML supports derivative communication and lifecycle processes, but remains an integration boundary rather than Fortem's internal data model: [ISDA FpML](https://www.isda.org/isda-solutions-infohub/fpml/).
