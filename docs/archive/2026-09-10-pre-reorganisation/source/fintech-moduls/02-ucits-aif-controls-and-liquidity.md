# Module 2 — UCITS/AIF controls and liquidity-risk workbench

## Commercial proposition

Offer a fund-control workbench that converts each fund's prospectus, mandate, risk policy, and approved legal interpretation into governed calculations, alerts, approvals, and evidence.

It is **decision support**, not a legal opinion or an assertion of automatic regulatory compliance. The manager, compliance function, depositary, and board retain responsibility for interpretation and action.

## Why it matters

UCITS managers must maintain risk-management processes that measure positions and their contribution to portfolio risk, including accurate and independent OTC-derivative valuation. [UCITS Article 51](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/ucits/article-51) ESMA expects liquidity stress testing to be embedded in governance and to lead to follow-up action. [ESMA LST guidelines](https://www.esma.europa.eu/document/guidelines-liquidity-stress-testing-in-ucits-and-aifs)

The module should initially target managers with open-ended UCITS/AIFs, derivatives exposure, evolving liquidity-management-tool frameworks, or a depositary/risk-committee demand for auditable evidence.

## Functional scope

### Investment and exposure controls

* Issuer, group, counterparty, deposit, and concentration limits.
* Eligible-asset and instrument classification controls.
* Fund-of-fund, index-replication, and issuer-group aggregation rules.
* Derivative look-through, commitment exposure, counterparty exposure, and collateral treatment.
* Borrowing, efficient-portfolio-management, and mandate-specific restrictions.

### Liquidity controls

* Asset liquidity classification and liquidation horizon.
* Investor-flow, redemption, and stressed-redemption scenarios.
* Market depth, concentration, haircut, bid-ask, and market-impact assumptions.
* Cash, financing, collateral, and settlement liquidity forecasts.
* Evidence supporting liquidity-management-tool consideration and escalation.

## Core domain model

```text
tenant_fund
  fund_id, tenant_id, legal fund/share-class relationships,
  base currency, dealing frequency, regulatory regime

control_policy
  policy_id, tenant_id, fund_id, policy_kind, version,
  approved_by, effective_from/to, source_document_reference

control_rule
  rule_id, policy_id, code, scope, expression_version,
  warning_threshold, hard_threshold, aggregation_method

control_input_snapshot
  snapshot_id, fund_id, valuation_snapshot_id,
  positions_source, holdings_as_of, market-data snapshot,
  legal/policy versions

control_run
  run_id, rule_id, input_snapshot_id, calculation_version,
  result_status, measured_value, threshold, executed_at

control_exception
  exception_id, control_run_id, severity, reason,
  owner, due_date, remediation_status

control_attestation
  attestation_id, exception_id, decision, rationale,
  approver, approved_at, evidence_reference

liquidity_scenario
  scenario_id, tenant_id, fund scope, version,
  redemption assumptions, market assumptions, status

liquidity_run
  liquidity_run_id, scenario_id, input_snapshot_id,
  calculation_version, outcome, executed_at
```

Rules are versioned documents plus executable expressions. Do not bury legal rationale in code. Each rule points to the source document, approved interpretation, owner, effective dates, and test cases.

## Calculation architecture

```text
tenant position snapshot
 + canonical instrument classification / relationships
 + market-data and valuation snapshot
 + fund policy version
 -> normalised exposure graph
 -> deterministic rule engine
 -> control results and explainable breaches
 -> workflow, attestation, export
```

The exposure graph is essential: a swap, option, ETF, fund share class, structured product, or composed option may require underlying, issuer, counterparty, collateral, and liquidity look-through. Missing look-through is itself a governed control result, not silently treated as zero exposure.

## APIs

```text
POST /v1/control-runs
GET  /v1/control-runs/{runId}
GET  /v1/control-exceptions?fundId=&status=
POST /v1/control-exceptions/{id}/attestations
POST /v1/liquidity-runs
GET  /v1/liquidity-runs/{id}/report
```

The API returns calculation versions, input snapshot IDs, rule IDs, thresholds, source references, and drill-down constituents. It must never return only a red/amber/green badge.

## MVP

Start with one UCITS fund family and a limited, approved rule catalogue:

1. issuer/group concentration;
2. cash/deposit/counterparty concentration;
3. derivative global-exposure inputs and missing-look-through exceptions;
4. liquidity profile and one stressed-redemption scenario;
5. exception workflow and risk-committee export.

Do not initially attempt every national UCITS interpretation, automated legal validation, all liquidity-management-tool mechanics, pre-trade blocking, or regulatory filing generation.

## Commercial model

Offer a managed implementation to translate the fund documents and existing calculations into testable controls, followed by recurring licensing and annual policy review. Sell the evidence, explainability, and operational workflow—not an unsupported claim that the software makes a fund compliant.

## Market evidence and positioning

The 2026 ESMA guidelines give current regulatory relevance to liquidity-management-tool selection and calibration: [ESMA LMT Guidelines](https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_open-ended_AIFs.pdf). FundApps already offers maintained daily UCITS/AIFMD monitoring, including exposure, diversification, and leverage controls: [FundApps](https://www.fundapps.co/ucits-aifmd-monitoring). Fortem should not compete by claiming a larger generic rules library; differentiate through fund-document interpretation, derivatives/structured-product look-through, liquidity evidence, and reconciliation to the client's trusted data.

See [market evidence and go-to-market](06-market-evidence-and-go-to-market.md) for commercial hypotheses and required customer validation.
