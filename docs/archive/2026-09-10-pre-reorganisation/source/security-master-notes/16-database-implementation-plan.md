# Database implementation plan

## Purpose

This is the staged plan for evolving the current SQLAlchemy/PostgreSQL draft into the shared-master, tenant-overlay, client-ingestion, and Soft-NAV architecture. It is deliberately additive. No existing canonical identity, market-data observation, trade, or client history is destructively rewritten.

## Current SQLAlchemy draft coverage

The current draft now represents the foundational table layer for the first end-to-end workflow. It includes tenant scope, external-ID namespaces/mappings, raw source payloads, provider/product/dataset/licence records, entitlement records, source proposals and approvals, market-data resolution snapshots, position snapshots, and Soft-NAV audit/result tables.

All newly deployed database changes are versioned Alembic revisions. SQLAlchemy metadata remains the schema definition for the draft, but `metadata.create_all()` is not a deployment mechanism because it does not evolve an existing database. The local bootstrap command upgrades to the current Alembic revision; schema upgrade/downgrade is tested against a disposable PostgreSQL database.

It also includes the key reference/economic extensions: organisation identifiers, instrument party roles, areas/countries, the dedicated `cal` calendar domain, effective-dated listing quotation and contract-unit terms, common schedules, futures/options/FX-forward/swap/structured-product terms, barriers/actions, dated constituent snapshots, corporate actions/adjustment factors, and regulatory labels including UCITS-style assignments.

The index subtype follows the future-family pattern without a duplicate
`secm.index` identity table. `secm.index_family` groups conceptual lineages,
`secm.index_terms` stores one concrete `INDEX` node's terms, and
`secm.index_methodology_version` stores effective-dated methodology and
back-tested-history metadata. The reusable `secm.return_profile` catalogue
covers price, gross/net total, excess, and dividend-points semantics and can be
referenced by index terms or performance-based swap legs. Constituent snapshots
remain available but are not part of the initial operational ingestion flow.

The first UI onboarding slice follows the same boundary. `/instruments/indices/new`
creates a manual `CREATE_INDEX` proposal through the Next.js BFF; it never
materialises an approved node from the browser. The server-rendered page loads
active, tenant-visible family, currency, return-profile, and organisation
catalogues before rendering the form, so dropdowns do not depend on a browser
fetch completing. A family is selected by `index_family_id`; family creation is
a separate governed setup action rather than free text on a variant form. The
page keeps optional methodology fields sparse and displays the proposal
ID/status returned by the API. Approval remains an Operations workflow and is
the point at which the family, terms, methodology version, tenant scope, and
approval evidence are written atomically.

The generic fee boundary is also implemented in one dedicated `fee` schema:
`fee_type`, `fee_rule`, and `fee_rule_target`. Contractual fee rules are
versioned and effective-dated, while realised trade fees remain in
`trd.trade_fee` and can reference the rule used for calculation.

Cryptoassets use the same additive boundary. `secm.crypto_network` is the
governed network catalogue; `secm.crypto_asset_terms` versions the parent
asset's identity and issuer/protocol facts; and
`secm.crypto_asset_deployment` stores chain-specific contract addresses,
standards, symbols, decimals, and lifecycle. The currency row may point back
to the same reference node so BTC/USDC can be used as quote or settlement
currencies without duplicating their economic identity. The current mockup
fixture seeds BTC and USDC across Bitcoin, Ethereum, Solana, and Base examples;
venue pair listings use the generic listing workflow, while the dedicated
crypto parent workflow creates the economic node and currency role before
those listings are allowed. Crypto-specific UI onboarding is intentionally
manual-first and approval-gated; network deployment entry remains a separate
future screen.

Exchange-traded products use one new common `secm.etp_terms` table. Concrete
`ETF`, `ETC`, `ETN`, and `EXCHANGE_TRADED_VEHICLE` values live in the existing
`secm.instrument_type` catalogue, while `ETP` is an umbrella taxonomy value.
ETF fund/share-class terms and PCF constituent snapshots reuse their existing
tables; ETC and ETN do not get separate price or listing tables.

For ETP references, `secm.instrument_relationship` is the authoritative source
for multiple or effective-dated references. The nullable `reference_node_id` in
`secm.etp_terms` is only a primary-reference convenience field. A future
hardening revision should add a governed relationship-role catalogue and
validate roles such as `REFERENCE_INDEX`, `UNDERLYING`, and `COLLATERAL`.

The tables create the contractual and audit boundaries. They do not by themselves implement the resolver, parsing/mapping engine, RLS policies, calculation engine, or database migrations.

### Implemented FX-forward onboarding slice

The first FX-forward vertical slice reuses `secm.instrument`,
`secm.instrument_dates`, and `secm.fx_forward_terms`. A manual proposal is
validated against active currency catalogue rows, routed through the generic
reference-data approval workflow, and materialised atomically as one
tenant-private economic instrument. The UI is available at
`/instruments/fx-forwards/new`; venue listings remain intentionally absent.
Rolling pair-tenor curves, confirmation-level calendars, monetary MTM marks,
and governed quote-convention catalogues are deferred as documented in
`docs/architecture/fx-forward-onboarding-2026-09-08.md`.

The automated onboarding slice adds a versioned `secm.reference_data_automation_policy`
catalogue and extends proposal/approval rows with source, idempotency, matching,
confidence, policy, decision-method, and evidence fields. The initial service
contract is equity CREATE; it materialises a tenant-private node/instrument/
listing aggregate only after a manual or governed automated approval.

## Slice 0: external-ID mapping foundation

This slice is first because every external position, cash balance, trade, administrator NAV, reference-data feed, and client report needs to identify the same Fortem object despite different upstream codes.

```text
HSBC shares on XLON
  Fortem listing UUID: 019...XYZ
  Bank A code: ABC
  Custodian B code: FOO
  Client C code: HSBC-LONDON
  -> all map to the same LISTING UUID
```

### Add tables

```text
ing.integration_source_system
  integration_source_system_id UUIDv7 PK
  owning_organisation_id FK secm.organisation
  tenant_id nullable FK ten.tenant             -- null for a shared provider
  system_code, display_name, source_kind
  environment                                  -- PROD / UAT / TEST
  status, created_at

ing.external_id_namespace
  external_id_namespace_id UUIDv7 PK
  integration_source_system_id FK
  namespace_code                              -- e.g. CUSTODIAN_B_ASSET_PROD
  external_object_type                        -- optional limiting type
  description, status, valid_from, valid_to

ing.external_object_mapping
  external_object_mapping_id UUIDv7 PK
  external_id_namespace_id FK
  external_object_type                        -- LISTING / REFERENCE_NODE / STRATEGY / TRADE / ORGANISATION / PERSON
  external_id_value
  target_object_type                          -- controlled counterpart
  target_object_id UUIDv7                     -- Fortem internal UUID
  context_market_venue_id nullable FK secm.market_venue
  mapping_role                                -- PRIMARY / ALIAS / LEGACY / SOURCE_REFERENCE
  mapping_method                              -- MANUAL / PROVIDER_MATCH / CLIENT_CONFIRMED / RULE
  status                                      -- PROPOSED / VERIFIED / REJECTED / RETIRED
  confidence nullable, verified_by nullable, verified_at nullable
  valid_from, valid_to, recorded_at
  source_payload_id nullable FK ing.source_payload (added in Slice 2)
  supersedes_mapping_id nullable self-FK
```

`external_object_mapping` is a controlled polymorphic mapping because integration identity crosses instruments, listings, organisations, strategies and trades. The mapping service validates `target_object_type` and target UUID against the relevant table; a PostgreSQL trigger supplies database-level enforcement once the supported target types are fixed.

### Rules and indexes

* A formal identifier (`ISIN`, `FIGI`, `CUSIP`, `SEDOL`, ticker) stays in `secm.financial_reference_identifier`; provider/client/custodian codes belong in the mapping layer.
* A bank code that means “HSBC on XLON” targets `LISTING`, not the generic HSBC economic instrument.
* A source code with only security-level meaning targets `REFERENCE_NODE`; the resolver must not invent a listing.
* Resolve using namespace + external object type + external ID + optional venue/context + as-of date.
* Require a unique current mapping for `(namespace, external object type, external ID, context)`. Add a PostgreSQL effective-date overlap exclusion constraint before allowing historic mappings.
* Index both lookup directions: external lookup for intake, and `(target_object_type, target_object_id)` for outbound/reporting aliases.
* An ambiguous, unverified, expired, or missing mapping produces a durable exception; it never falls back to a display-name or ticker guess.

### Modify current model material

* Retain `secm.financial_reference_identifier`; do not merge it with the new mapping table.
* Retain `trd.trade_external_reference` temporarily. Migrate it later to an external-object mapping/reference pattern only after trade lifecycle behaviour and external-reference cardinality are tested.
* Replace no existing UUIDs and do not make bank/client/custodian IDs primary keys.

### Acceptance proof

1. Resolve `BANK_A_STATIC_PROD / LISTING / ABC` to the Fortem HSBC XLON listing UUID.
2. Resolve `CUSTODIAN_B_ASSET_PROD / LISTING / FOO` to that same UUID.
3. Resolve a client portfolio code to its strategy UUID.
4. Reject the same external ID in an unknown namespace and a listing mapping with an incompatible venue context.
5. Preserve a retired code and resolve the correct historical target for a requested as-of date.

## Slice 1: tenancy and visibility

Add `ten.tenant`, `ten.reference_node_scope`, `ten.tenant_reference_override`, and typed tenant alias/classification/valuation-override tables. Link each tenant to its subscribing `secm.organisation` and apply row-level/API entitlement checks through the scope table. Keep the existing shared `secm.financial_reference_node` UUID as the cross-domain target; do not duplicate canonical identity per tenant.

## Slice 2: source provenance and canonical approval

Add `ing.source_payload`, `ing.ingestion_job`, `ing.mapping_spec_version`, `ing.validation_issue`, `secm.reference_data_proposal`, and `secm.reference_data_approval`. Progressively replace free-text `source_system_id` fields with foreign keys while retaining legacy text during migration. Source payloads hold hash/locator and processing lineage, not a second operational copy of normalized data.

## Slice 3: entitled market-data resolution

Add provider, provider-product, dataset, licence and tenant-entitlement tables in `md`/`ten`; versioned tenant valuation policies; resolver results; and immutable resolution snapshots.

```text
secm.organisation
  -> md.data_provider
    -> md.provider_product
      -> md.dataset
        -> md.market_data_series
          -> md.market_data_observation

md.data_licence
  -> md.dataset_licence_assignment
  -> ten.tenant_dataset_entitlement
```

`dataset` is the governed content universe and entitlement scope, such as `BLOOMBERG_COMMODITY_INDICES_EOD` or `FACTSET_US_EQUITIES_EOD`, rather than merely a delivery file or the provider's entire product. `provider_product` is the commercial product family; file/API/streaming delivery details remain separate.

Extend every `md.market_data_observation` with mandatory `dataset_id`, nullable `acquisition_licence_id`, and source-payload link, in addition to observed, published and received times, value basis, and revision/supersession. `acquisition_licence_id` records the right under which Fortem received the exact observation where known. This is immutable provenance.

Do not put a tenant's entitlement ID directly on an observation: access is many-to-many and depends on tenant, intended use and effective date. `ten.tenant_dataset_entitlement` evaluates `tenant + dataset + use purpose + as-of date` at read/resolution time. A completed resolver or NAV snapshot records the resulting entitlement/policy decision as audit evidence.

The resolver selects a value under tenant entitlement and named valuation cut; it never implements a generic “latest price” query.

This slice now also includes `md.market_data_vintage` and observation vintage
lineage. The resolver's information-cut predicate is: receipt no later than
the cut, and source publication no later than the cut when available. This
separates a source's current restated history from a historically reproducible
information set.

Implementation choice: the first database-backed resolver has a deliberately
small, fixed rule hierarchy and returns an explicit missing/stale/needs-override
result instead of guessing a fallback. Snapshot persistence is append-only:
subsequent reruns create another snapshot and reference their exact policy and
input observation IDs.

Schema evolution is migration-only. Demo and seed loaders may insert governed
reference rows after `alembic upgrade head`, but they must not call SQLAlchemy
`create_all`: otherwise a new model table could exist locally without a
reviewable, deployable migration.

Calendar ownership is implemented in Alembic revision `20260901_13`: the
legacy `secm.market_calendar` table is moved to `cal.market_calendar`, with
`cal.market_calendar_session` and `cal.market_calendar_holiday` added for
dated session and closure data. Existing venue, schedule, and valuation-policy
foreign keys are retargeted to `cal`. The migration preserves existing calendar
definitions and is reversible.

## Slice 4: client snapshots and Soft NAV

The draft now includes `trd.position_snapshot` and `trd.position_snapshot_line`, linked to source payloads and external-ID mappings, plus the `nav` calculation run, input snapshot/items, valuation lines, result and reconciliation tables. Each NAV run references one immutable position snapshot and one immutable market-data resolution snapshot. Cash uses the existing `trd.cash_balance` snapshot model.

Deferred: ingestion-job orchestration, administrator-NAV dedicated intake type, NAV adjustments, and calculation/reconciliation services.

The generic `nav.valuation_mark` table is now available for tenant-scoped
marks. It requires one and only one lineage route (resolution snapshot or
approved override) and freezes valuation cut, information cutoff, method, and
calculation version. The dedicated override evidence table remains deferred.

## Slice 5: economic terms and lifecycle breadth

The draft now includes focused futures/options/FX-forward/swap/structured-product terms, schedules/barriers, corporate-action events/effects/factors, organisation identifiers/party roles, geographic records, the `cal.market_calendar`/session/holiday tables, regulatory labels, dated constituent snapshots, and effective-dated quotation/contract-unit tables. Calendar ownership is deliberately outside `secm`; `md.valuation_cut` and other consumers reference the shared `cal` records.

The vanilla-option slice is now explicit in migrations `20260906_23` and
`20260907_24`: governed CALL/PUT, EUROPEAN/AMERICAN/BERMUDAN exercise, strike
basis and currencies, FpML-compatible settlement methods, optional Bermudan
exercise schedule, and effective-dated contract-unit terms. Migration
`20260907_24` adds versioned static option terms plus schedule-driven
`option_strike_reset_rule` and immutable `option_strike_fixing` tables for
FORWARD_START and RESET strikes. It intentionally leaves premium amounts and
payment events at trade/cashflow level, rejects formula resets until a governed
formula contract exists, and defers digital/barrier and other exotic payoff
features to dedicated models. The first structured-product composed-option UI
slice now supplies that dedicated component/condition model for
`VANILLA_SPREAD_KIP`, `VANILLA_KIP`, and `DIGITAL_KIP`; it does not expand the
vanilla option type vocabulary. Reset events are not new terms versions; a legal
amendment or correction creates a new option-terms version linked through
`supersedes_option_terms_id`.

Implemented: focused `fund`, `fund_share_class_terms`, and `bond_terms` tables.
Funds/sub-funds are reference objects, share classes are economic instruments,
and both share-class and bond terms use effective-dated version rows. Deferred:
credit/repo/rate-option specialised terms; coupon-program and structured-product
key-term registry; detailed schedule conventions; corporate-action custody
elections; and a tested migration that retires legacy quote/multiplier/date
columns. `instrument_composition` remains backward-compatible until its use is
restricted to contractual payoff components in that migration.

The bond onboarding MVP now requires only the canonical name and a coupon
structure (`FIXED`, `ZERO`, or `FLOATING`). Issue/maturity dates, identifiers,
issuer, currency, coupon rate, frequency, day count, and floating reference
index are optional submission facts. A sparse proposal remains `PENDING` with
`PENDING_ENRICHMENT` until provider evidence or Operations supplies enough
terms for approval; approval then materialises the economic instrument and its
versioned `bond_terms` row. The terms model includes optional floating
reference-index and spread fields; the live demo database was extended
non-destructively with those nullable columns. Venue listings remain a separate
workflow.

Alembic revisions `20260903_18` and `20260903_19` add the governed day-count
vocabulary and its fee-rule reference. Day-count conventions are now a governed
`secm.day_count_convention` catalogue,
seeded with common ISDA, ICMA, AFB, actual/360, actual/365, thirty/360, and
business/252 codes. `secm.bond_terms.day_count_convention_id` is nullable and
canonical for new records; the existing text field remains as legacy/provider
source text during the additive transition. The reference API exposes active
conventions for onboarding dropdowns, with an explicit `— Not specified —`
option. The catalogue stores vocabulary and descriptions only; accrual formulas
remain in the calculation service, and calendars remain in `cal`.

## Slice 6: generic fees and charges

Migration `20260902_16` adds a single shared `fee` schema rather than separate
tables for AMCs, funds, share classes, or strategies:

```text
fee.fee_type
  governed fee classification catalogue

fee.fee_rule
  immutable, versioned calculation terms with explicit units, basis,
  frequencies, validity, provenance, and optional model parameters

fee.fee_rule_target
  typed assignment to exactly one reference node or strategy, with payer,
  recipient, application mode, priority, and optional assignment validity
```

`trd.trade_fee` gains an optional `fee_rule_id` foreign key. It remains the
realised trade-level fact and is not replaced by the contractual rule table.
There is deliberately no central NAV `fee_event` table in this slice. A
future implementation may add one after the accounting/accrual boundary and
performance-fee engine are agreed.

## Delivery order

```text
external-ID mapping
  -> tenant scope
  -> source payload / approval workflow
  -> entitled EOD resolver
  -> position and cash snapshots
  -> generic fee rules and assignments
  -> Soft NAV and reconciliation
  -> broader economic terms and lifecycle coverage
```

The first deployable client workflow is not “upload a CSV.” It is: upload a position/cash snapshot, resolve every external code deterministically, surface mapping exceptions, select entitled EOD inputs at a named cut, and retain a reproducible Soft-NAV snapshot.

## Deferred implementation choices

The first SQLAlchemy increment adds the core tables and provenance foreign keys, but intentionally defers three enforcement mechanisms until the API and migration boundary are implemented:

1. **Polymorphic mapping target enforcement.** `ing.external_object_mapping` supports multiple UUID-backed target types. The mapping service validates the type/UUID pair initially; introduce a PostgreSQL trigger after the supported target set and migration path are fixed. Do not pretend a generic SQL foreign key can enforce several target tables.
2. **Tenant data isolation mechanism.** `ten.reference_node_scope` is the foundation for scope. Define and test PostgreSQL RLS policies together with authenticated API database roles; do not enable partial RLS policies before all tenant-scoped child access paths are covered.
3. **Fine-grained licence clauses.** `md.data_licence.permitted_use_description` and the dataset/tenant assignment tables provide the V1 governed boundary. Add normalized restrictions for geography, user population, redistribution channel, retention, and derived-data rules only when actual contracts require machine enforcement beyond `use_purpose`.
4. **Business calculation logic.** The schema freezes input/output evidence but intentionally does not implement pricing, accrual, corporate-action position transformations, NAV calculation, or reconciliation tolerance logic. Those services require golden-master comparison with Fortem's established Python capability.

5. **Calendar population and resolution.** The `cal` tables are the governed
storage boundary, but production holiday/session ingestion and local-time to
UTC cutoff resolution remain a service concern. The first resolver may use
these tables through one application boundary; a PostgreSQL function is only
needed if multiple independent callers require the same resolution primitive.

6. **Canonical version backfill and cutover.** Version tables are additive in
   this implementation. A controlled backfill from existing mutable
   `instrument`/`listing` rows, dual-read reconciliation, and eventual write
   cutover must be implemented before treating the old definition columns as
   non-authoritative.
7. **Override evidence model.** `nav.valuation_mark.approved_override_id`
   currently preserves the UUID boundary without inventing a universal
   override schema. Define typed override categories, approval roles, and
   tenant visibility before adding its foreign key.
8. **Tenant database provisioning.** The registry/routing table records the
   approved destination and schema revision; automated database creation,
   secret rotation, health checks, migration orchestration, and failover are
   control-plane work still required before onboarding a production tenant.
9. **Fee calculation breadth.** The generic fee schema stores governed rules
   and assignments, but does not implement fee calculation. Performance fees,
   tiers, high-water marks, hurdles, equalisation, waivers, and NAV accrual
   posting require versioned calculation services and explicit approval rules.

The existing `source_system_id` text fields, `source_payload_reference`, and listing quote/multiplier fields remain backward-compatible draft fields. They are migrated only through a tested data migration, not dropped in this implementation slice.

Corporate-action V1 derivation is now implemented as a read-only service over
the existing versioned events and adjustment factors. It selects actions by the
requested historic information cut and returns factor/event lineage, preserving
raw observations and submitted position snapshots. Persisted adjusted-history
materialisation and custody processing remain deferred.
