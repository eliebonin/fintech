# Market data sources and priorities

## Intent

Provide a discoverable frontend page to inspect providers, tenant-authorised dataset coverage and source priority by instrument type. The preceding scope foundation is implemented. The user authorised this feature and requested sequential work, documented changes and focused tests without further plan approval prompts.

## Design

- `/market-data/sources`, linked from navigation and Market data, contains Providers & scope and Source priorities sections.
- Catalogue only current entitled datasets and tenant-owned or shared provider identities; show product/dataset identity, coverage packages, timing, owner/market, intended use and non-display readiness. Never expose confidential agreement references or grant other rights.
- Priority configuration uses explicit ordered dataset IDs per instrument type for VALUATION. Platform defaults are editable only by PLATFORM_ADMIN; TENANT_ADMIN + MARKET_DATA may configure tenant overrides or restore inheritance. Readers cannot save.
- Save immutable versioned configurations with attribution, idempotency and optimistic concurrency. An override excludes datasets not listed; an empty override explicitly disables sources for that type. Platform defaults must contain only shared sources. Tenant-owned datasets are not silently included in global defaults.
- Suggest tenant-owned sources first in an unsaved new tenant configuration, but activation requires explicit save. Existing uploads do not automatically override marks; accepted observations and existing pricing/rights checks are still required.
- Explicit policy dataset rules remain authoritative within permitted configured sources. Flexible/strict pricing-policy modes and generic uploads remain separate work.
- For composite selection: filter price convention/basis/calendar eligibility first, select latest eligible pricing date as already defined by policy, then apply source priority before timestamp arbitration. A rejected or stale price is not rescued by changing its rank. For legacy date policies, rank candidates within each market date before existing date selection.
- Configurations known by the request information cutoff apply; freeze their IDs/order in selection evidence. Previously staged runs and immutable observations are not rewritten. No configuration retains legacy arbitration and is clearly labelled unconfigured in the UI.
- Scope restrictions and activity rights precede source priority. Provider rank never substitutes for licensing or makes incompatible prices eligible.

## Acceptance

Tenant-admin reordering changes new same-date price selection, even when a lower-priority source arrived later. Readers/other tenants cannot mutate configuration. Idempotent retry returns the same version; stale concurrent edits conflict. Explicit datasets cannot escape exclusions. Scoped forbidden series remain inaccessible. Navigation, empty/unavailable/loading states, save errors, keyboard up/down controls, exclusions and inheritance are clear and tested.

## Scope boundaries

No new commercial rights, licence purchasing, quarterly reviews, market-data upload workflow, pricing engine or flexible-policy redesign. The page visualises coverage but does not edit licensing grants. Preserve dirty checkout changes and use focused isolated tests.
