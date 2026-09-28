# Module 1 — Portfolio valuation control and market-data provenance

## Commercial proposition

Provide a governed independent control layer answering: **what value was used, why was it selected, who approved any exception, and can the result be reproduced?**

This module is not a replacement for a fund administrator's NAV, a market-data vendor, or a pricing library. It reconciles and controls the inputs and decisions around those processes.

Primary buyers are the COO, CFO, Head of Fund Operations, Head of Risk, and valuation committee. Typical triggers are multiple price sources, OTC instruments, fund-admin price challenges, stale-data incidents, audit findings, or a need to evidence valuation decisions under stressed conditions.

## Client workflow

```text
authorised data source
  -> immutable normalised observation
  -> series-selection policy for a valuation context
  -> selected observation or attributable override
  -> valuation snapshot and exception result
  -> valuation committee / operations review
  -> export to administrator, IBOR, risk, or reporting process
```

The client sees a valuation exception queue rather than a generic price screen. Each exception explains the prior value, candidate values, tolerance, reason, affected portfolios, action, approver, and downstream status.

## Core domain model

### Shared data plane (`secm`, `md`)

```text
provider
  provider_id, name, status

provider_dataset
  provider_dataset_id, provider_id, dataset_code, data_class,
  permitted_internal_use, permitted_client_display

data_licence
  data_licence_id, provider_dataset_id, legal_entity_id,
  effective_from/to, retention_terms, redistribution_terms

provider_instrument_mapping
  provider_id, provider_key, reference_node_id,
  mapping_status, effective_from/to, confidence, source_lineage

market_data_series
  series_id, reference_node_id, observation_definition,
  provider_dataset_id, valuation_cut_id, currency_id, status

market_data_observation
  observation_id, series_id, market_date, observed_at_utc,
  published_at_utc, received_at_utc, source_vintage,
  correction_sequence, finality, value, value_basis, raw_payload_id
```

### Tenant control plane

```text
tenant
tenant_data_entitlement
  tenant_id, provider_dataset_id, permitted_use, effective_from/to

valuation_context
  valuation_context_id, tenant_id, policy_version_id,
  base_currency_id, valuation_cut_id, purpose

series_selection_policy
  policy_version_id, reference-node/type scope, observation definition,
  source priority, accepted quality/finality, fallback behaviour

valuation_override
  override_id, tenant_id, scope, value, reason_code,
  requested_by, approved_by, approval_status, effective period

market_data_snapshot
  snapshot_id, tenant_id, valuation_context_id, as_of_cut,
  created_at, policy_version, source-vintage boundary, status

effective_value_selection
  snapshot_id, target_node_id, selected_series_id,
  selected_observation_id, selected_override_id,
  selection_rank, exception_code, explanation
```

`effective_value_selection` is append-only. It records a decision; it never changes the raw observation.

## Resolver rules

There is no generic `latest_price(instrument)` endpoint. The caller must supply a valuation context and valuation cut.

For each required observable, the resolver follows a deterministic ordered policy:

```text
approved tenant override
-> tenant-entitled provider observation
-> platform-entitled provider observation allowed for this tenant
-> approved public observation
-> explicit missing-data exception
```

The resolver must reject a candidate if it is outside the permitted source-vintage boundary, has unacceptable quality/finality, is stale under the policy, has no licence/entitlement, or belongs to a different valuation cut.

## APIs

```text
POST /v1/valuation-snapshots
GET  /v1/valuation-snapshots/{snapshotId}
GET  /v1/effective-values?nodeId=&valuationContextId=&asOf=
POST /v1/valuation-overrides
POST /v1/valuation-overrides/{id}/approve
GET  /v1/valuation-exceptions
```

Responses include canonical IDs, selected source, timestamps, policy version, entitlement basis, and a machine-readable reason code. Pydantic/OpenAPI contracts are versioned independently of implementation tables.

## Integration and controls

* Ingest vendor, administrator, custodian, and internal data through adapters that preserve original payload references.
* Reconcile output against administrator/NAV packs before allowing automation.
* Separate requestor, approver, and deployment/service identities.
* Enforce tenant and provider-dataset entitlement before returning values.
* Apply audit logging to all policy, override, and approval changes.
* Do not expose or redistribute vendor data through an API unless the licence explicitly permits it.

## MVP

Support listed instruments and funds/share classes at one named EOD cut. Ingest two authorised price sources, select a single official close/evaluated price under one policy, raise exceptions, allow two-person approval for overrides, and produce a downloadable provenance report.

Exclude intraday pricing, model valuation, portfolio P&L, and automated NAV calculation from the initial release.

## Success measures

* Percentage of EOD marks with complete source and policy lineage.
* Price-exception rate, age, resolution time, and override frequency.
* Reconciliation rate against the administrator's accepted marks.
* Ability to replay a historical valuation snapshot without using later information.

## Risks

Licensing and entitlement are not implementation details. Data must not be ingested, stored, transformed, displayed, or redistributed beyond the contractual rights for the dataset and client. Also, a selected price is not automatically a fair-value conclusion; the valuation policy and accountable committee remain responsible.

## Market evidence and positioning

ESMA's valuation review supports the control need by identifying weaknesses in valuation policies, stressed-market valuation, independence, and error detection: [ESMA](https://www.esma.europa.eu/press-news/esma-news/esma-report-points-out-improvements-needed-supervision-asset-valuation). Rimes demonstrates that broad governed price/security/entity data management is an established enterprise market: [Rimes](https://www.rimes.com/). Fortem should therefore position this module as the independent **selection, exception, and evidence layer** across incumbent sources and administrators, not as a substitute for global data coverage.

See [market evidence and go-to-market](06-market-evidence-and-go-to-market.md) for the pricing-confidence assessment and discovery gates.
