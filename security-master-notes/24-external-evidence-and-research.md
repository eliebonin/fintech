# External evidence and research register

## Purpose

This note records which parts of the architecture are supported by external
primary sources and which parts are deliberate internal design choices. A
source link is evidence for a principle or market convention; it is not an
instruction to copy the source's data model into PostgreSQL.

The register prevents a common failure mode in architecture work: presenting a
useful Fortem design decision as if it were a universally mandated industry
standard. Where research has not yet been completed, the topic is explicitly
marked **research gap**.

**Research pass date:** 2026-09-10 (expanded from the 2026-09-07 pass). Links and regulatory interpretations must
be revalidated when a standard, provider contract, licence, or regulation
changes.

## Evidence status

| Status | Meaning |
|---|---|
| **Sourced** | A primary or authoritative source was reviewed and the linked point is recorded below. |
| **Design choice** | Our internal operating decision; it may be informed by practice but is not claimed to be a standard. |
| **Research gap** | Important topic identified in the notebook, but no precise primary source was captured in this research pass. |

## Indexes and benchmark governance — sourced

The index model is supported by two complementary observations:

* S&P describes indexes as rule-based measures that may use securities,
  derivatives, or other instruments, and distinguishes broad, sector, factor,
  fixed-income, commodity, and strategy families. See [What is an Index?](https://www.spglobal.com/spdji/en/research-insights/index-literacy/what-is-an-index/)
  and the [S&P index finder](https://www.spglobal.com/spdji/en/index-finder/).
* S&P publishes separate identifiers and levels for variants such as S&P 500
  price return, total return, and net total return. Its return-type material
  also distinguishes price, total, excess, and dividend-points concepts. See
  [S&P 500](https://www.spglobal.com/spdji/en/indices/equity/sp-500/),
  [return types](https://www.spglobal.com/spdji/en/education/article/an-overview-of-return-types-for-insurance-indices/),
  and [dividend-points FAQ](https://www.spglobal.com/spdji/en/education/article/faq-sp-500-dividend-points-index/).
* IOSCO's [Principles for Financial Benchmarks](https://www.iosco.org/library/pubdocs/pdf/ioscopd409.pdf)
  emphasise administrator governance, benchmark quality, methodology quality,
  accountability, and oversight. They do not prescribe one universal relational
  schema.

**Adopted design:** represent an index as a governed reference node; group
variants under `secm.index_family`; store variant semantics in the generic
`secm.return_profile`; version methodology separately in
`secm.index_methodology_version`. Constituent snapshots and calculation engines
remain optional later capabilities.

**Deferred:** a full benchmark-administrator control framework, methodology
approval workflow, constituent ingestion, and independent index calculation.

## Commodity, currency, and real-time index conventions — sourced

ICE's public index catalogues demonstrate that index products span fixed income,
equity, commodity, currency, volatility, intraday, and custom families. ICE
also publishes currency index products with named publication conventions,
including an official New York-time close. See [ICE Data Indices](https://developer.ice.com/fixed-income-data-services/catalog/ice-data-indices)
and [ICE Currency Indices](https://www.ice.com/fixed-income-data-services/index-solutions/currency-indices).
S&P's commodity education notes that futures-based indexes need explicit roll
and weighting methodology; see [There's an Index for That](https://www.spglobal.com/spdji/en/research-insights/index-literacy/there-s-an-index-for-that/).

**Adopted design:** the observable stream is a `market_data_series` with an
explicit measure, tenor, cut, provider/dataset, and provenance. An FX forward
contract is an instrument; a rolling `GBPEUR 1M` quote is a series. Commodity
and currency indexes are reference objects, not an excuse to create a second
generic price table.

## Exchange-traded products — sourced distinction, internal model

The FCA groups exchange-traded products into ETFs, ETCs, and ETNs, while noting
that complex products may add leverage, inverse exposure, or daily resets. See
[FCA complex ETP review](https://www.fca.org.uk/publications/good-and-poor-practice/complex-exchange-traded-products).
The SEC describes ETNs as unsecured debt obligations whose return is linked to
an index or benchmark; see the [ETN Investor Bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-50).
ESMA's ETF guidance distinguishes a UCITS ETF by continuous trading and
market-maker support, so a listed fund is not automatically a UCITS ETF; see
[ESMA ETF Guidelines](https://www.esma.europa.eu/document/guidelines-etfs-and-other-ucits-issues-0).
Euronext's reference-data offering operationally groups ETF, ETC, ETV, and ETN
products, which supports a shared listing/data workflow but not identical
economic terms; see [Euronext master files](https://www.euronext.com/en/products-services/master-file-products).

**Adopted design:** one common versioned `secm.etp_terms` table, concrete
instrument types for ETF/ETC/ETN/ETV, and `ETP` as an umbrella taxonomy/UI
category. Reuse listings, relationships, parties, identifiers, market-data,
fund/share-class, and constituent-snapshot tables. Do not infer fund NAV,
collateral, or issuer-credit semantics from the fact that a product trades on
an exchange.

**Relationship governance deferred:** the generic relationship table is
authoritative for multiple/effective-dated references; the ETP terms reference
field is only a primary-reference shortcut. A governed role catalogue and
cardinality/role validation are intentionally deferred to a later hardening
slice.

## Cryptoasset identity and venue pairs — sourced distinction, internal model

The venue APIs consistently treat a market as an ordered base/quote pair, not
as an undifferentiated ticker. Coinbase exposes `base_currency_id` and
`quote_currency_id` alongside product status and trading increments; see the
[Coinbase product schema](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-single-product).
Binance defines the base asset as the asset being bought or sold and the quote
asset as the asset used to price it; see its [Spot glossary](https://developers.binance.com/en/docs/products/spot/faqs/spot_glossary).
Kraken's pre-trade endpoint likewise requires base and quote assets as
separate fields; see [Get tradable asset pairs](https://docs.kraken.com/api/docs/rest-api/get-pre-trade).

Chain standards provide a separate identity dimension. Ethereum's [ERC-20
standard](https://ethereum.org/developers/docs/standards/tokens/erc-20/)
defines token behaviour on a network, while Circle publishes distinct USDC
contract addresses for each supported chain in its [USDC contract address
catalogue](https://developers.circle.com/stablecoins/usdc-contract-addresses).
Those sources support storing the parent asset once and recording chain,
contract address, token standard, and decimals separately. They do not imply
that a venue symbol or contract address should become our primary identity.

**Adopted design:** use one stable `DIGITAL_ASSET` reference node that may also
carry a currency role; version its parent facts in `secm.crypto_asset_terms`;
store chain-specific deployments in `secm.crypto_asset_deployment` linked to
the governed `secm.crypto_network` catalogue; and model each venue's native
ordered pair as a normal listing. Wrapped/bridged assets with materially
different issuer, redemption, or bridge risk are separate linked nodes.

**Deferred:** wallet addresses, custody balances, transfers, on-chain proof,
DEX pool reserves, and venue-specific symbol alias governance. Those belong to
custody/ledger or market-data ingestion slices, not the canonical asset terms.

## Vanilla options — sourced contract dimensions

The first vanilla-option slice was checked against primary standards and
exchange specifications on 2026-09-06 and the dynamic-strike extension was
reviewed on 2026-09-07:

* [FpML equity-option product architecture](https://www.fpml.org/spec/fpml-5-1-6-rec-1/html/reporting/fpml-5-1-intro-8.html)
  describes vanilla put/call options, American/European/Bermuda exercise,
  single or basket underlyings, monetary strike currency, and cash or physical
  delivery. It also shows that FpML later extends the architecture for
  barriers, digitals, baskets, and other exotic features.
* [FpML exercise/valuation/settlement schema](https://www.fpml.org/spec/fpml-5-11-7-rec-1/html/transparency/schemaDocumentation/schemas/fpml-eqd-5-11_xsd/complexTypes/EquityExerciseValuationSettlement.html)
  enumerates Cash, Physical, Election, and CashOrPhysical settlement and
  carries settlement currency and exercise style as separate concepts.
* [ISDA 2000 Definitions](https://www.isda.org/book/2000-isda-definitions-pdf)
  provide the contractual definitions boundary for privately negotiated
  derivatives. The [ISDA definitions text](https://www.isda.org/a/smMDE/Blackline-2000-v-2006-ISDA-Definitions.pdf)
  distinguishes European, Bermuda, and American exercise periods.
* [CME strike-price guidance](https://www.cmegroup.com/education/courses/introduction-to-options/what-is-exercise-price-strike.hideHeader.hideFooter.hideSubnav.hideAddThisExt.educationIframe.html)
  confirms that strike is a contract specification and that strike intervals
  vary by product and expiry.
* [FpML EquityStrike](https://www.fpml.org/spec/fpml-5-8-6-tr-1/html/recordkeeping/schemaDocumentation/schemas/fpml-eq-shared-5-8_xsd/complexTypes/EquityStrike.html)
  and [strikeDeterminationDate](https://www.fpml.org/spec/fpml-5-10-5-rec-1/html/confirmation/schemaDocumentation/schemas/fpml-eq-shared-5-10_xsd/complexTypes/EquityStrike/strikeDeterminationDate.html)
  separate strike price/percentage from a date on which a forward-starting
  strike is determined.
* The [ISDA glossary](https://www.isda.org/?p=6823) describes a cliquet as
  consecutive forward-starting options with strikes determined from prior
  settlement levels, supporting a schedule/rule/fixing model.
* [CME E-mini S&P European-option specifications](https://www.cmegroup.com/education/articles-and-reports/e-mini-sp-500-quarterly-pm-options-european-style-faq.html)
  shows the practical need to identify the specific underlying future,
  multiplier, expiry time, exercise style, and settlement result.

**Adopted design:** normalize static economic dimensions in versioned
`secm.option_terms`; keep exact expiry/maturity dates in
`secm.instrument_dates`, Bermudan exercise and strike-reset dates in
`secm.schedule`/`secm.schedule_event`, and contract entitlement in
effective-dated `secm.instrument_contract_unit_terms`. Store reset methodology
in `secm.option_strike_reset_rule` and actual market-derived values in
immutable `secm.option_strike_fixing` rows. Keep premium amounts and payment
events with the trade/cashflow layer. The internal `BERMUDAN` code maps to the
standards' `Bermuda` label.

**Deferred:** premium cashflow modelling, adjusted-option deliverable baskets
after corporate actions, formula reset evaluation, and quanto/asian payoff
features. Digital and barrier components are now represented for the first
structured-product templates through
`secm.structured_product_component_terms`, condition groups, and barrier rules;
their pricing, path evaluation, and full lifecycle outcome processing remain
deferred. This keeps digital/barrier semantics out of the vanilla option type
list while still making the contractual graph explicit.

## Corporate actions and adjusted history — design choice / research gap

The notebook's corporate-action model is an internal design choice: immutable
raw observations, versioned actions and effects, explicit adjustment basis, and
source-vintage-aware replay. It was intentionally designed to handle the
difference between (a) today's vendor-restated history and (b) the information
that was knowable at a historic cut.

This research pass did not capture a single authoritative source precise enough
to define all event codes, ex/record/payable-date semantics, option
deliverables, tax treatment, or vendor adjustment conventions. Treat [ISO
20022 securities-event messages](https://www.iso20022.org/market-infrastructure-messages)
and the relevant venue/custodian event specifications as the next primary
research inputs before production custody processing.

**Adopted design:** do not infer adjustment status from our receipt timestamp;
retain raw, adjusted/restated, derived, vintage, and method metadata. Custody
entitlements, elections, tax, manufactured dividends, and full adjusted-option
deliverables remain out of the first release.

## Market-data provenance, vintages, and valuation cuts — design choice

The separation between `market_date`, `observed_at`, source publication time,
platform receipt time, valuation cut, and source vintage is a reproducibility
requirement in our architecture. The research performed here did not establish
a single industry-wide rule for how every vendor publishes corrections or
historic vintages.

**Adopted design:** observations are immutable; corrections are new vintages or
observations; a resolver receives an explicit tenant, entitlement, valuation
date, cut, and historic information cutoff; a NAV run freezes the selected
inputs and lineage. The resolver must never call an unqualified “latest price”.

**Research gap:** document provider-specific correction, restatement, finality,
publication-time, and redistribution semantics for each licensed dataset.

## Identifiers, integration formats, and external mappings — sourced in part

The notebook uses ISO identifiers and boundary formats as integration
vocabularies, while retaining a normalized internal schema. The exact current
specifications should be confirmed against the relevant standards bodies before
each adapter is certified:

| Topic | Architectural use | Evidence status |
|---|---|---|
| ISIN / ISO 6166 | Security identifier assignment, never internal identity | Design choice; standard text/licence review pending |
| FIGI and provider IDs | Effective-dated external mappings to immutable UUIDs | Design choice; provider terms govern use |
| LEI / GLEIF | Legal-organisation identification | Design choice; authoritative registry should be integrated where required |
| MIC / ISO 10383 | Venue and listing context | Design choice; venue lifecycle needs source governance |
| FpML / ISDA | OTC confirmation and terms coverage at the boundary | Design choice; adapter certification pending |
| FIX | Execution and market-data transport | Design choice; message-version scope pending |
| ISO 20022 `seev` | Corporate-action and settlement boundary | Research gap for the first production adapter |
| SDMX | Official macroeconomic-statistics boundary | Research gap for the first production adapter |

The integration pattern is: retain the original payload and checksum, map via a
versioned adapter, validate and reconcile, then materialise canonical records.
An external code such as a bank's `ABC`, a custodian's `FOO`, and our `XYZ` is
stored in namespace-aware `external_object_mapping`; it is not a competing
primary key.

## UCITS, Soft NAV, fees, and tenant isolation — design choice / research gap

The service boundary for tenant overlays, Soft NAV, effective-dated fees, and
per-client entitlements is primarily a product and control decision. It is not
presented as a claim that one particular database topology is mandated by UCITS
or by a fund-accounting standard.

**Adopted design:** one shared canonical database plus one logically isolated
tenant overlay database per client; trusted tenant routing; immutable snapshots
for Soft NAV inputs/results; dataset/licence entitlement checks; and append-only
fee rules and trade/correction evidence.

**Research gap:** obtain legal/compliance review for the intended service scope,
especially UCITS valuation/NAV responsibilities, record-retention obligations,
outsourcing, data residency, market-data redistribution, and client-specific
override authority. The platform remains an indicative operational service, not
an administrator's official NAV by default.

## Commercial platform patterns — vendor self-description

These sources are useful evidence that institutional buyers accept managed,
integration-led workflows, but they are not neutral benchmarks and do not prove
that a design is legally or technically correct:

* [FundApps data specification and upload documentation](https://techdocs.fundapps.co/docs/data-specification)
  shows controlled position ingestion and asynchronous processing patterns.
* [NeoXam DataHub](https://www.neoxam.com/datahub/) describes configurable
  mapping, golden-copy/survivorship, data-quality, exception, entitlement, and
  multi-channel integration capabilities.
* [OpenGamma API documentation](https://docs.opengamma.com/) illustrates
  entitlement-aware calculation discovery, asynchronous calculation resources,
  named valuation inputs, and structured errors.
* [Aladdin APIs and Data Cloud](https://www.blackrock.com/aladdin/platforms/products/apis)
  demonstrates an API/bulk-file/integration boundary around a large managed
  operating platform.
* [MSCI portfolio analytics](https://www.msci.com/data-and-analytics/portfolio-management/barra-portfolio-manager)
  and [FactSet portfolio analytics](https://www.factset.com/solutions/portfolio-analytics)
  show that portfolio risk and scenario analytics are established products;
  Fortem should therefore differentiate on explainability, structured/OTC
  coverage, and reconciliation rather than promise a universal replacement.

**Adopted product implication:** sell narrow, auditable workflows on top of the
shared master (valuation control, onboarding/corporate actions, OTC lifecycle,
UCITS controls, and portfolio diagnostics) and integrate with incumbent systems.
Do not infer competitor internals from marketing pages.

## Cross-layer control research — sourced 2026-09-10

The global DB/API/frontend review added the following primary-source checks.
They support control patterns rather than prescribing our schema:

* [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
  confirms that RLS can restrict reads and writes and becomes default-deny when
  no applicable policy exists, while table owners and `BYPASSRLS` roles normally
  bypass it. Tenant isolation therefore needs both session context and a
  constrained runtime role.
* [PostgreSQL declarative partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
  supports range/list/hash partitioning and pruning for large time-series data;
  the review consequently recommends measurement before partitioning the MVP.
* [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) defines
  `application/problem+json` for machine-readable HTTP errors, and
  [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) defines conditional
  requests such as `If-Match`/ETag for safe updates.
* The [OpenAPI specification](https://spec.openapis.org/oas/) supports a
  versioned contract as the source for generated clients and contract tests.
* [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
  and its [BOLA guidance](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
  make clear that UUIDs do not provide authorization; every ID-taking endpoint
  needs object/function-level checks and bounded resource use.
* [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0-18.html)
  provides the authentication/claims boundary for mapping an Auth0 subject to
  our internal account and tenant membership.
* [Next.js hydration guidance](https://nextjs.org/docs/messages/react-hydration-error)
  identifies browser-only APIs, time-dependent rendering, invalid nesting, and
  CSS-in-JS setup as common mismatch sources. The frontend should render a
  deterministic initial tree and isolate client-only state.
* [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
  supports server components as the default data-fetching boundary with small
  client islands for interaction.
* [WCAG 2.2](https://www.w3.org/TR/WCAG22/) requires keyboard/focus, name/role/
  value, and error/status behaviour to be tested, not inferred from visual QA.
* [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
  provides the trace/metric/log correlation model recommended for following a
  browser request through BFF, API, database, resolver, and NAV run.

These findings are now reflected in
[`docs/architecture/global-db-api-frontend-review-2026-09-10.md`](../docs/architecture/global-db-api-frontend-review-2026-09-10.md).

## Source-use policy

1. Prefer primary standards bodies, administrators, exchanges, index providers,
   regulators, and official vendor documentation.
2. Record the source URL, access/review date, and the narrow proposition it
   supports; do not copy proprietary schemas or long text into this notebook.
3. Separate a market convention from a mandated requirement and from our own
   implementation choice.
4. Re-review sources when a data licence, standard version, regulation, or
   provider contract changes.
5. Do not make scraping or systematic manual transcription a production source
   of record; obtain permission/licensing for intended internal or client-facing
   use.

## Research backlog

* Corporate-action event-code and adjusted-derivative conventions by venue.
* Provider-specific market-data correction and vintage semantics.
* FpML/FIX/ISO 20022 adapter scope and conformance tests.
* UCITS valuation, outsourcing, audit trail, and retention requirements for the
  planned Soft-NAV service.
* Dataset licence terms, redistribution rights, and tenant entitlement models.
* Benchmark-administrator governance if proprietary/QIS indexes become a
  regulated or client-facing benchmark product.
