# Decision log and open questions

## Decisions made

| Topic | Decision |
|---|---|
| Database | PostgreSQL. |
| Initial boundary | Canonical financial-instrument reference data. |
| Canonical ownership | Operations creates and governs records; external/internal sources enrich with lineage. |
| Identity | Hybrid `financial_reference_node` / `instrument` / `listing` model. |
| Price storage | One `security_price` table keyed by a single reference node. |
| OTC trades/prices | Use the economic instrument node unless a specific venue representation is genuinely relevant. |
| Listed trades/prices | Use the listing node for venue-specific execution/observations; retain economic identity for trades. |
| Futures | Future family plus one economic instrument per expiry and normally a listing per venue. |
| Swaps | General leg model as canonical model; simple `info_swaps` view for common two-leg representation. |
| Desk labels | ABC, XYZ, FOO live in an internal product taxonomy mapping. |
| IDs | UUIDv7 internal IDs, with normal audit timestamps retained. |
| Dates | One wide `instrument_dates` table for shared key dates, and separate tables for repeating schedules. |
| Structured products | Parent product plus actual payoff components, parent lifecycle barriers, component payoff barriers, and schedules. |
| Structured-product aggregation and KIP cardinality | Persist `underlying_scope` and explicit `underlying_aggregation`. The first slice supports `SINGLE`/`SINGLE` with `ALL`, and `WORST_OF`/`MIN` or `BEST_OF`/`MAX` with `NONE`: reduce once, then apply the shared predicate. KIP-enabled drafts contain one fresh PUT child per underlying. `condition_group_action.payout_multiplicity` records `ONCE_PER_PARENT` for aggregate best-/worst-of outcomes, `PER_COMPONENT` for a single/explicit component outcome, and reserves `PER_UNDERLYING` for a later governed `EACH_UNDERLYING` shape. Reject weighted baskets and ungoverned per-underlying outcomes. |
| Structured-product consolation | `AUTOCALL_CONSOLATION` is a parent `PAY_CONSOLATION` range action. The KIP barrier is the inclusive lower bound when KIP exists; otherwise require an explicit `consolationLowerBarrier`. The final payoff barrier is the exclusive upper bound, and no dummy KIP component is created. |
| Structured-product dates | Keep terms-effective, observation/fixing, and payment/settlement dates distinct. The UI schedule is a provisional weekend-only preview; approval owns governed calendar resolution and explicit date validation. |
| Structured-product strike anchoring | Generated child options store `PERCENT_OF_INITIAL` and FK to the accepted `structured_product_initial_fixing`; never infer a percentage strike from an unversioned spot value. Corporate-action strike changes append `secm.option_strike_adjustment`; deliverable-unit changes create a new `instrument_contract_unit_terms` version. |
| Composed OTC options | One parent composed-option instrument with signed `composition_value` multipliers; the kind column makes weights/quantities explicit when those shapes are later enabled. |
| Listed strategies | Trade packages and individual listed option legs; not necessarily parent master instruments. |
| Entity model | Top-level entity/group, child legal entities/branches, organisation identifiers, and instrument-party roles. |
| SP key terms | Governed term-definition catalogue and instrument-level term/metric values for extraction, description, and reporting. |
| SP term applicability | Lightweight structured-product-type to term-definition mapping; validate required terms at activation. |
| Indices | Model index identity separately from tradeable instruments; price, net-total-return, gross-total-return, and excess-return variants are distinct index nodes. |
| FX forwards | A booked forward is an economic instrument with fixed contractual terms; rolling pair-tenor quotes such as GBPEUR 1M are market-data series, not instruments. |
| Market-data catalogue | Use a common `market_data_series` catalogue and scalar observation model; introduce specialised physical tables only for data with different shape or scale (ticks, bars, curves/surfaces, marks). |
| Valuation cuts | Store named, timezone-aware valuation cuts. A timestamp says when data was observed; a cut says which business moment a selected value represents. |
| Calendar ownership | Keep calendars outside `secm` in a dedicated `cal` schema. `cal.market_calendar`, dated sessions, and holidays are shared by market data, NAV, trades, and schedules; `md.valuation_cut` references them. |
| Quote conversion | Keep quote factor (quotation convention) distinct from unit/contract multiplier (instrument economics). |
| Corporate actions, V1 | Store a versioned canonical event, flexible event dates, one-or-more economic effects, and series-specific adjustment factors. Defer custody-grade entitlement/election processing. |
| Adjusted history | Raw observations are immutable. Whether a historical vendor value is already adjusted is explicit observation metadata, not inferred from our ingestion timestamp. |
| Macro data | Use dedicated indicator/observation tables with economic reference periods and release vintages; do not store macro releases as ordinary prices. |
| Commodities | Use commodity reference nodes, existing futures/options/swaps, scalar series for spot, generic curves for forwards, and generic surfaces for volatility. |
| Cryptoassets | One canonical `DIGITAL_ASSET` node can carry both instrument and currency roles. Effective-dated `secm.crypto_asset_terms` describe the parent asset; `secm.crypto_asset_deployment` plus `secm.crypto_network` describe chain-specific native/token deployments. Wrapped/bridged assets with distinct risk are separate linked nodes. Venue markets are listings of a base asset against fiat, stablecoin, or another cryptoasset. |
| Crypto listing identifiers | Keep the primary venue symbol on `secm.listing.trading_symbol`. Store listing-level `TICKER`, `VENUE_PRODUCT_ID`, `FIX_SECURITY_ID`, and similar venue identifiers in `secm.financial_reference_identifier` with venue context. Provider, custodian, client, and broker aliases remain `ing.external_object_mapping`; the identifier actually used in an execution is retained as a trade external reference. |
| AMC/ETI | An AMC is an exchange-traded certificate linked to a managed reference portfolio, not a fund. Use a certificate wrapper plus dated reference-portfolio constituent snapshots. |
| Standards | Use standards as controlled identifiers, classifications, and integration vocabularies at system boundaries; retain the normalized PostgreSQL model as canonical internal storage. |
| Additional product roadmap | Add focused terms models for credit derivatives, financing, rates options, and convertible/warrant/right securities; do not force them into generic swaps, bonds, or options. |
| Geography and venues | Use a geographic-area hierarchy with country terms as a subtype; use a MIC-compatible market-venue model that also supports crypto venues without MICs. |
| Trade grain | One trade row is one booked economic event / actual execution. A multi-leg OTC product is represented by its parent instrument and one trade row. |
| Trade identity | Use UUIDv7 as immutable internal trade ID; preserve any external/source trade IDs as typed external references. |
| Trade subject and reference | A trade subjects an instrument, listing, or cash currency. Related cash events use a nullable originating `reference_instrument_node_id`, interpreted by `trade_type`. |
| Trade parties and actors | Use party roles for client/counterparty/broker/custodian etc.; store the economic trader as `person_id` and booking actor as `user_account_id`. |
| Cash balances | Cash is a strategy-owned position snapshot in a dedicated `cash_balance` table, not a trade. It contributes to position and FX P&L. |
| Client distribution | Record dealing capacity, execution channel/source/venue, client party role, and child fee records. Distribution fees are normally issuer-paid revenues to the firm's legal entity. |
| Fees and charges | Centralise contractual fee vocabulary, immutable effective-dated rules, and typed target assignments in one `fee` schema. Apply the same framework to AMCs, funds, share classes, strategies, mandates, and other fee-bearing objects; keep realised trade charges in `trd.trade_fee` with an optional rule link. |
| Node and instrument classification | Govern structural node types and economic instrument types in separate catalogues. A taxonomy/value hierarchy captures commercial archetypes and internal desk classifications. |
| Tenant model | Keep shared canonical data and tenant-scoped data logically separate. Tenant overlays reference immutable UUIDs and never overwrite canonical facts. |
| Client integration | Accept controlled APIs, uploads, SFTP batches, and authorised provider adapters; convert them through versioned mappings into strict canonical contracts. |
| External-ID mapping | Preserve immutable Fortem UUIDs as internal identity. Map bank, client, custodian, vendor and internal-system identifiers through effective-dated, namespace-aware external-object mappings. |
| Soft NAV | Provide it as a tenant-scoped operational calculation service. Each run retains an append-only resolved-input audit snapshot and is distinct from official administrator NAV. |
| Tenant routing | Select the tenant overlay database only from the trusted central registry; never accept a database endpoint from the client request. |
| Canonical definition history | Keep stable instrument/listing UUIDs and append approved effective-dated definition versions; protect versions from UPDATE/DELETE. |
| Cross-database links | Store central UUID plus local type/version/status validation evidence because PostgreSQL foreign keys do not cross databases. |
| Trade corrections | Keep the booked trade/event immutable; append lifecycle events with sequence, supersession and source idempotency keys. |
| Generic marks | Store tenant valuation conclusions separately from raw observations; require exactly one immutable resolver snapshot or approved override lineage. |
| Market-data vintages | Retain source publication and platform receipt timestamps; a historic information cut may use only vintages knowable by that cut. |
| Automated reference-data onboarding | Use versioned, source-bound automation policies and append-only proposal/approval evidence. High-confidence equity creates may be auto-approved and materialised atomically; conflicts remain pending/manual. Idempotency is source-scoped. |
| Equity onboarding scope | Start with common equity facts and multiple listings. Treat CFI as a classification code, not a unique identifier; defer its assignment model. Materialise tenant-private records first; promotion to shared canonical data is explicit. |
| Bond onboarding scope | Require the user to select only `FIXED`, `ZERO`, or `FLOATING` coupon structure. Allow sparse capture and provider enrichment; do not activate an incomplete bond. Keep bond economics in versioned `bond_terms`, repeating coupons in schedules, and venue representation in separate listings. |
| Day-count vocabulary | Keep a governed `secm.day_count_convention` catalogue with stable codes, descriptions, optional standards source, lifecycle status, and display order. Bond and future rate-bearing terms reference it through a nullable foreign key; `NULL` means unknown/not applicable and is never guessed. Calendar sessions remain in `cal`; calculation formulas remain in the valuation engine. |
| Index model and return semantics | Use `financial_reference_node` with `node_type = INDEX`, `secm.index_terms`, `secm.index_family`, and effective-dated `secm.index_methodology_version`; do not create a duplicate `secm.index` identity table. Keep a generic `secm.return_profile` catalogue for stable price/total/excess/dividend-points semantics. Index variants remain separate `INDEX` reference nodes grouped by family, with their own provider mappings and market-data series. Provider-specific tax, financing, fee, and calculation rules belong in methodology or contractual terms. Constituent ingestion and internal calculation remain deferred. |
| Index classification | Reuse `secm.taxonomy`, `secm.taxonomy_value`, and `secm.instrument_taxonomy_assignment` with separate canonical domains for asset class, geography, scope, size, strategy, benchmark role, and sector. Assign classifications to concrete index variants; retain provider taxonomies separately and keep return/profile/methodology data outside taxonomy. |
| Index onboarding UI | Use a manual-first `/instruments/indices/new` proposal page behind the Next.js BFF. Require canonical name, effective date, and index kind; make family, return profile, currency, organisations, and methodology facts optional for provider/steward enrichment. Approval, not browser submission, materialises the `INDEX` node and related terms/methodology rows. |
| Index-kind semantics | Govern `PUBLIC`, `QIS`, `PROPRIETARY`, and `CUSTOM_BASKET` in `secm.index_kind_catalogue`, including description, dissemination class, methodology ownership, and examples. Do not treat public dissemination and proprietary methodology as mutually exclusive; for example, S&P 500 can be public and provider-owned. The API validates active catalogue codes and the UI consumes the same DB-backed metadata. |
| Index family selection | Treat an index family as a reusable governed reference node. Index variants select an active visible family by `index_family_id`; the variant form does not create or identify a family by free-text name. Family creation is a separate Operations setup workflow. |
| Index family onboarding UI | Use `/instruments/index-families/new` for a manual `CREATE_INDEX_FAMILY` proposal. Capture canonical family name, optional unique internal code, and optional active provider organisation. Approval materialises a non-tradable `INDEX_FAMILY` node plus `secm.index_family` and tenant scope; pending family and index proposals share the reference-data work queue. |
| Exchange-traded products | Use one versioned `secm.etp_terms` table for common ETF/ETC/ETN/ETV/ETI wrapper terms. Add concrete ETF/ETC/ETN/ETV instrument types and an `EXCHANGE_TRADED_PRODUCT_CLASS` umbrella taxonomy; reuse fund/share-class terms, constituent snapshots, listings, relationships, identifiers, and market-data tables. Do not create separate ETP price or listing tables. |
| ETP relationship authority | Keep `secm.instrument_relationship` as the authoritative, effective-dated, multi-reference mapping for ETPs. Treat `secm.etp_terms.reference_node_id` as an optional primary-reference shortcut only. Govern relationship roles through a catalogue in a later hardening slice; do not let the shortcut replace or override relationship rows. |
| Vanilla options | Use governed CALL/PUT terms, EUROPEAN/AMERICAN/BERMUDAN exercise, explicit strike basis/currency, FpML-compatible settlement choices, exact underlying node, and common instrument dates. Keep contract entitlement in effective-dated `secm.instrument_contract_unit_terms`; keep premium amount/payment events trade-specific. Static option terms are versioned with a stable economic instrument UUID. |
| Option strike resets | Model `FIXED`, `FORWARD_START`, and `RESET` strikes with one stable option instrument, a versioned `option_terms` row, existing schedule/events, `option_strike_reset_rule`, and immutable `option_strike_fixing` records. Reset events are ordering facts, not new terms versions; corrections supersede fixings. |
| Option feature boundary | Do not encode digital, barrier, Asian, quanto, or other exotic payoff behaviour as additional `option_type` values. Add dedicated payoff/feature terms when those products are implemented. Forward-start/reset strike determination is now a dedicated terms/schedule feature, not an option-type value. |
| Option standards mapping | Treat FpML/ISDA/CME as evidence for the controlled concepts and adapter vocabulary, not as the internal PostgreSQL schema. Internal `BERMUDAN` maps to the standards' `Bermuda`; `CASH_OR_PHYSICAL` is retained alongside `CASH`, `PHYSICAL`, and `ELECTION`. |
| First composed-option UI templates | Implement `VANILLA_SPREAD_KIP`, `VANILLA_KIP`, and `DIGITAL_KIP` as governed structured-product archetypes on the existing parent/component graph. Use signed option composition rows, explicit `OPTION_PAYOFF` unconditional groups, and a separate `CAPITAL_PROTECTION` KIP barrier component. Default KIP monitoring is `CONTINUOUS`, with `FINAL_ONLY` available for European/maturity-only terms. |
| Composed-option research boundary | A call spread is represented as long/short vanilla legs; a digital is a cash-or-nothing component, not a new vanilla option type; and a knock-in option is activated by a specified barrier event. These semantics are supported by CME, Investor.gov, and ISDA documentation; pricing and path evaluation remain deferred. |

## Important technical notes

* UUIDs are identifiers, not authorization capabilities. UUIDv7 can expose approximate creation ordering; access control must be authorization-based.
* Do not encode business meaning or type prefixes into UUIDs. Human-friendly internal codes may exist separately.
* Operations and market-data consumers must not silently mix venue close, vendor composite, internal mark values, or different valuation cuts.
* A listing relationship is a direct foreign key; economic underlyings and components are generic typed relationships.

## Open questions

1. How should source priority, steward approval, and typed canonical/tenant overrides be governed? Observation source-vintage identity and approved instrument/listing version history are now defined in V1; the approval workflow is not.
2. What legal-entity, issuer, fund, AMC, currency, index, rate-index, curve, and FX-pair reference submodels are required?
3. What market-data source hierarchy and quality-control rules will select marks for each portfolio and use case?
4. What exact lifecycle rules govern trade amendment, cancellation, correction, novation, and replacement? The append-only event envelope is implemented; business transition validation and accounting effects remain open.
5. What schedule/cashflow abstraction best serves bonds, swap legs, and structured-product cashflows? Option exercise and strike-reset schedules now use `secm.schedule` and `secm.schedule_event`; broader cashflow conventions remain open.
6. What exact asset-specific terms and controlled vocabularies are required for the first delivery slice?
7. What effective-dating, audit, correction, approval, and entitlement controls are required? The six foundation controls are now schema primitives; RLS, provisioning, and operational approval gates remain.
8. Which fields are legitimately tenant-overridable, and which require a private instrument rather than an overlay?
9. What dataset rights, redistribution terms, and client entitlements govern every market-data series and observation?
10. What first canonical input contracts and maintained source adapters will be commercially supported?
11. Which object types need database-enforced specialised external-mapping tables versus the controlled generic mapping service?
12. What exact precedence and stacking rules apply when a fund-level fee and a share-class-level fee coexist? The V1 model stores `application_mode` and `priority`; the resolver policy is still required.
13. Which performance-fee and tiered-fee methods should be implemented first, including high-water marks, hurdles, crystallisation, breakpoints, waivers, and equalisation?
14. Should NAV accruals and non-trade charges eventually be represented by a central `fee_event` table, or remain in NAV/accounting-specific output tables?
15. Which source adapters and confidence/matching policies should be approved for production, and who owns their policy versions?
16. When should a tenant-private equity be promoted to shared canonical identity, and what evidence is required to merge duplicate private records?
17. What classification-assignment model should carry CFI and other non-unique regulatory codes?

## Recommended next discussion

Do not rush the schedule model. The next high-value design discussion is the source-provenance and golden-record model: immutable source facts, effective dating, operations approval, and canonical value selection.
