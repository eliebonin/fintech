# Module 5 — Portfolio risk and investment-solution diagnostics

## Commercial proposition

Externalise Fortem's investment-solution expertise as repeatable diagnostics for CIOs, portfolio-construction teams, wealth platforms, and distributors. Frame portfolios through the Fortem sleeves—Income, Beta, Diversifiers, and Protection—while retaining a transparent view of actual holdings, economic exposures, liquidity, derivatives, and scenarios.

This should initially be a managed analytics service with reproducible reports and APIs. It should not promise an automated investment recommendation or replace a manager's investment decision process.

## Client workflow

```text
tenant position snapshot
 + approved instrument/relationship data
 + market-data and valuation snapshot
 + portfolio policy and scenario definition
 -> exposure normalisation
 -> risk, liquidity, and scenario calculations
 -> explainable diagnostics and report/API output
 -> investment committee / adviser workflow
```

## Functional scope

* Exposure decomposition by asset class, issuer, geography, currency, rate, index, and Fortem sleeve.
* Look-through of funds, ETFs, baskets, derivatives, structured products, and composed options where authorised data exists.
* Net/gross, delta-adjusted, notional, and economic exposure views.
* Factor, scenario, drawdown, volatility, concentration, liquidity, and stress diagnostics.
* Hedge effectiveness and FX exposure monitoring.
* Portfolio comparison against mandate, benchmark, target allocation, or model portfolio.
* Client/distributor reports with a stated calculation and valuation snapshot.

## Core domain model

```text
portfolio_definition
  tenant_id, portfolio/mandate identity, base currency, policy version

position_snapshot
  tenant-owned holdings, source, as-of time, status

exposure_methodology
  version, definitions, approved parameters, scope

scenario_definition
  scenario name, shocks, correlations, liquidity assumptions, version

risk_run
  position_snapshot_id, valuation_snapshot_id, methodology_version,
  scenario_set_version, calculation_version, executed_at

risk_measure
  risk_run_id, measure code, scope node, value, currency/unit, explanation

portfolio_sleeve_assignment
  portfolio or position scope, INCOME/BETA/DIVERSIFIERS/PROTECTION,
  effective dates, methodology version
```

Do not store a sleeve assignment as an immutable truth of an instrument. The same instrument can serve a different purpose in different portfolios. Keep this tenant- and methodology-scoped.

## Reproducibility requirements

Every report and API result must reference:

```text
position snapshot
+ reference-data version / source state
+ market-data snapshot and valuation cut
+ exposure methodology version
+ scenario version
+ calculation code version
+ user/service actor and calculation timestamp
```

This is essential when comparing a new cloud/API result against Fortem's existing Python calculations. Golden-master tests should compare outputs at agreed tolerances for a fixed set of historic portfolios and snapshots before each release.

## APIs

```text
POST /v1/risk-runs
GET  /v1/risk-runs/{id}
GET  /v1/portfolios/{id}/exposures
POST /v1/portfolio-comparisons
GET  /v1/reports/{id}
```

The response contract must expose methodology and snapshot IDs. A chart without its assumptions is not an institutional output.

## MVP

Start with one Fortem-managed model portfolio or bespoke mandate. Produce a daily exposure and scenario pack using current Python calculations behind a stable API, reconcile it against existing Fortem outputs, and only then progressively externalise calculation components.

Defer automated optimisation, order generation, suitability advice, personal recommendations, and opaque AI-generated allocation changes.

## Commercial model

This module is a good entry point for CIO and distribution conversations, but should be sold as a managed, attributable insight service initially. It has stronger retention when bundled with Modules 1–2 because the underlying values, controls, liquidity classifications, and methodology are then demonstrably trustworthy.

## Market evidence and positioning

MSCI, Aladdin, and FactSet all offer institutional risk, attribution, scenario, and multi-asset analytics: [MSCI](https://www.msci.com/data-and-analytics/portfolio-management/barra-portfolio-manager), [Aladdin](https://www.blackrock.com/aladdin/platforms/products/aladdin-risk), and [FactSet](https://www.factset.com/solutions/portfolio-analytics). This validates demand while ruling out a credible “replace the whole risk stack” message. Fortem should lead with its Income/Beta/Diversifiers/Protection methodology, explainable outputs, and reconciliation to established Python analytics.

See [market evidence and go-to-market](06-market-evidence-and-go-to-market.md) for commercial hypotheses and the proof required before platform investment.
