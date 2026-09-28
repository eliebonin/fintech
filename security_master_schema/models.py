"""First-draft PostgreSQL SQLAlchemy Core model for the security master."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Time,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


metadata = MetaData()

UUID_V7 = UUID(as_uuid=True)
UTC_NOW = text("CURRENT_TIMESTAMP")
UUID_V7_DEFAULT = text("uuidv7()")


# secm: canonical security-master, party, and reference-data domain.
reference_node_type = Table(
    "reference_node_type",
    metadata,
    Column("reference_node_type_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed reference-node type definition."),
    Column("type_code", String(40), nullable=False, unique=True, comment="Unique controlled type code such as INSTRUMENT, LISTING, INDEX, CURRENCY, COMMODITY, or RATE_INDEX."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the reference-node type."),
    Column("description", Text, nullable=True, comment="Business definition and intended use of the reference-node type."),
    Column("node_class", String(40), nullable=False, comment="Broad node classification such as ECONOMIC, VENUE_REPRESENTATION, or REFERENCE."),
    Column("default_is_tradable", Boolean, nullable=False, server_default=text("false"), comment="Default tradability proposed for newly created nodes of this type; each node retains its actual value."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed type definition."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for operational lists of node types."),
    schema="secm",
)

financial_reference_node = Table(
    "financial_reference_node",
    metadata,
    Column("reference_node_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the universal financial reference node."),
    Column("reference_node_type_id", UUID_V7, ForeignKey("secm.reference_node_type.reference_node_type_id"), nullable=False, comment="Governed classification defining the kind of financial reference node."),
    Column("canonical_name", String(500), nullable=False, comment="Canonical human-readable name of the reference object."),
    Column("internal_code", String(100), nullable=True, unique=True, comment="Optional stable internal business code; it is not an external identifier."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as DRAFT, ACTIVE, INACTIVE, MATURED, or RETIRED."),
    Column("is_tradable", Boolean, nullable=False, server_default=text("false"), comment="Whether this node is directly tradeable or bookable in the operating model."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this canonical node was created."),
    Column("updated_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp of the latest stored update to this node."),
    schema="secm",
)

entity = Table(
    "entity",
    metadata,
    Column("entity_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the top-level group or entity record."),
    Column("entity_code", String(100), nullable=False, unique=True, comment="Convenient unique internal code for the entity or corporate group."),
    Column("display_name", String(250), nullable=False, comment="Short display name used in operations and user interfaces."),
    Column("legal_name", String(500), nullable=True, comment="Full legal or registered name when known at group level."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, INACTIVE, PROSPECT, or BLOCKED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the entity record was created."),
    schema="secm",
)

organisation = Table(
    "organisation",
    metadata,
    Column("organisation_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a legal entity, branch, or operational organisation."),
    Column("entity_id", UUID_V7, ForeignKey("secm.entity.entity_id"), nullable=False, comment="Top-level entity or corporate group to which this organisation belongs."),
    Column("organisation_type", String(50), nullable=False, comment="Organisation kind such as LEGAL_ENTITY, BRANCH, FUND_MANAGER, ISSUER, CUSTODIAN, or VENDOR."),
    Column("display_name", String(250), nullable=False, comment="Short operational name for this organisation."),
    Column("legal_name", String(500), nullable=True, comment="Full registered legal name of this organisation."),
    Column("incorporation_country_code", String(3), nullable=True, comment="ISO 3166-1 alpha-3 country code of incorporation when applicable."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of this organisation record."),
    Column("effective_from", Date, nullable=True, comment="First business date on which this organisation record is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this organisation record is effective."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the organisation record was created."),
    schema="secm",
)

person = Table(
    "person",
    metadata,
    Column("person_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an individual human being."),
    Column("display_name", String(250), nullable=False, comment="Operational display name of the person."),
    Column("given_name", String(150), nullable=True, comment="Given or first name of the person when retained."),
    Column("family_name", String(150), nullable=True, comment="Family or last name of the person when retained."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, INACTIVE, or BLOCKED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the person record was created."),
    schema="secm",
)

user_account = Table(
    "user_account",
    metadata,
    Column("user_account_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an application user or service account."),
    Column("person_id", UUID_V7, ForeignKey("secm.person.person_id"), nullable=True, comment="Human person owning this account; null for a non-human service account."),
    Column("account_type", String(30), nullable=False, comment="Account kind such as HUMAN, SERVICE, or INTEGRATION."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the account."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the account was created."),
    schema="secm",
)

auth_identity = Table(
    "auth_identity",
    metadata,
    Column("auth_identity_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an external authentication identity mapping."),
    Column("user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Application account authenticated by this identity."),
    Column("provider", String(100), nullable=False, comment="Authentication provider name, for example AUTH0."),
    Column("issuer", String(500), nullable=False, comment="OIDC issuer URL or equivalent authentication namespace."),
    Column("subject", String(500), nullable=False, comment="Provider subject identifier, for example the Auth0 sub claim."),
    Column("valid_from", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp from which the authentication mapping is valid."),
    Column("valid_to", DateTime(timezone=True), nullable=True, comment="UTC timestamp after which the authentication mapping is no longer valid."),
    UniqueConstraint("provider", "issuer", "subject", name="uq_auth_identity_provider_issuer_subject"),
    schema="secm",
)

person_organisation_affiliation = Table(
    "person_organisation_affiliation",
    metadata,
    Column("person_organisation_affiliation_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a person's affiliation with an organisation."),
    Column("person_id", UUID_V7, ForeignKey("secm.person.person_id"), nullable=False, comment="Person participating in the affiliation."),
    Column("organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Organisation to which the person is affiliated."),
    Column("relationship_side", String(20), nullable=False, comment="Whether the affiliation is INTERNAL or EXTERNAL to the firm's operating perimeter."),
    Column("affiliation_type", String(50), nullable=False, comment="Affiliation kind such as EMPLOYEE, CONTRACTOR, CLIENT_CONTACT, or COUNTERPARTY_TRADER."),
    Column("effective_from", Date, nullable=False, comment="First business date on which this affiliation is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this affiliation is effective."),
    schema="secm",
)

market_venue = Table(
    "market_venue",
    metadata,
    Column("market_venue_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a regulated market, MTF, exchange, CEX, DEX, or venue segment."),
    Column("operating_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation operating the venue when known."),
    Column("operating_market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=True, comment="Parent operating venue for a market segment, MTF compartment, or venue subdivision."),
    Column("venue_type", String(40), nullable=False, comment="Venue kind such as EXCHANGE, MTF, OTF, CEX, DEX, OTC_VENUE, or INTERNAL."),
    Column("display_name", String(500), nullable=False, comment="Canonical display name of the market venue."),
    Column("country_code", String(3), nullable=True, comment="ISO 3166-1 alpha-3 country code of the venue location when applicable."),
    Column("primary_geographic_area_id", UUID_V7, ForeignKey("secm.geographic_area.geographic_area_id"), nullable=True, comment="Primary geographic area of operation; null when a decentralised venue has no meaningful jurisdictional location."),
    Column("city", String(150), nullable=True, comment="City in which the venue is principally located when relevant."),
    Column("timezone_name", String(100), nullable=True, comment="IANA timezone used for venue session interpretation; null only when genuinely inapplicable."),
    Column("market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=True, comment="Trading calendar governing sessions, holidays, and market-date derivation for the venue."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, INACTIVE, or EXPIRED."),
    schema="secm",
)

market_venue_identifier = Table(
    "market_venue_identifier",
    metadata,
    Column("market_venue_identifier_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a venue identifier record."),
    Column("market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=False, comment="Venue identified by this external or standards-based code."),
    Column("identifier_scheme", String(50), nullable=False, comment="Identifier scheme such as ISO_10383_MIC, LEI, EXCHANGE_CODE, or CRYPTO_EXCHANGE_CODE."),
    Column("identifier_value", String(250), nullable=False, comment="Value assigned by the identifier scheme."),
    Column("is_primary", Boolean, nullable=False, server_default=text("false"), comment="Whether this is the preferred identifier for its scheme and venue."),
    UniqueConstraint("identifier_scheme", "identifier_value", name="uq_market_venue_identifier_scheme_value"),
    schema="secm",
)

currency = Table(
    "currency",
    metadata,
    Column("currency_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a monetary currency or cryptoasset currency role."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, unique=True, comment="Optional canonical node, enabling a cryptoasset to carry both instrument and currency roles."),
    Column("currency_code", String(20), nullable=False, unique=True, comment="Canonical currency code such as ISO 4217 GBP or an approved digital-asset code."),
    Column("display_name", String(250), nullable=False, comment="Human-readable currency name."),
    Column("numeric_code", String(10), nullable=True, comment="ISO 4217 numeric code when one exists."),
    Column("minor_unit", Integer, nullable=True, comment="Number of decimal places conventionally used for the currency."),
    Column("currency_kind", String(30), nullable=False, comment="Currency classification such as FIAT, CRYPTOASSET, STABLECOIN, or ACCOUNTING_UNIT."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the currency definition."),
    schema="secm",
)

crypto_network = Table(
    "crypto_network",
    metadata,
    Column("crypto_network_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed blockchain or distributed-ledger network."),
    Column("network_code", String(80), nullable=False, unique=True, comment="Stable network code such as BITCOIN_MAINNET, ETHEREUM_MAINNET, SOLANA_MAINNET, or BASE_MAINNET."),
    Column("display_name", String(200), nullable=False, comment="Human-readable blockchain or distributed-ledger network name."),
    Column("network_family", String(40), nullable=False, comment="Network family such as BITCOIN, EVM, SOLANA, STELLAR, or OTHER."),
    Column("chain_identifier", String(150), nullable=True, comment="Network-specific chain identifier, retained as text because different ecosystems use different identifier formats."),
    Column("native_currency_code", String(40), nullable=True, comment="Native asset code when the network has one, such as BTC or ETH; this is descriptive and does not replace the currency foreign key."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, INACTIVE, DEPRECATED, or TESTNET."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for network selection lists."),
    schema="secm",
)

identifier_scheme = Table(
    "identifier_scheme",
    metadata,
    Column("identifier_scheme_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an instrument identifier scheme definition."),
    Column("scheme_code", String(50), nullable=False, unique=True, comment="Short controlled code such as ISIN, FIGI, CUSIP, SEDOL, TICKER, or RIC."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the identifier scheme."),
    Column("scope", String(40), nullable=False, comment="Normal scope of the scheme such as INSTRUMENT, LISTING, ORGANISATION, or MIXED."),
    Column("is_external_standard", Boolean, nullable=False, server_default=text("true"), comment="Whether the scheme is externally governed rather than internally defined."),
    schema="secm",
)

financial_reference_identifier = Table(
    "financial_reference_identifier",
    metadata,
    Column("financial_reference_identifier_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a reference-node identifier assignment."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Canonical reference node carrying the identifier."),
    Column("identifier_scheme_id", UUID_V7, ForeignKey("secm.identifier_scheme.identifier_scheme_id"), nullable=False, comment="Scheme governing the identifier value."),
    Column("identifier_value", String(500), nullable=False, comment="Identifier value exactly as assigned by the governing scheme."),
    Column("context_market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=True, comment="Venue context required by identifiers such as exchange tickers."),
    Column("valid_from", Date, nullable=True, comment="First business date on which this identifier assignment is valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this identifier assignment is valid."),
    Column("is_primary", Boolean, nullable=False, server_default=text("false"), comment="Whether this is the preferred identifier for the node and scheme context."),
    UniqueConstraint("identifier_scheme_id", "identifier_value", "context_market_venue_id", name="uq_reference_identifier_scheme_value_context"),
    schema="secm",
)

instrument_type = Table(
    "instrument_type",
    metadata,
    Column("instrument_type_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed economic instrument type."),
    Column("type_code", String(60), nullable=False, unique=True, comment="Unique controlled product type code such as EQUITY, BOND, SWAP, OPTION, or STRUCTURED_PRODUCT."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the economic instrument type."),
    Column("description", Text, nullable=True, comment="Business definition and modelling boundary of the instrument type."),
    Column("default_asset_class", String(40), nullable=False, comment="Default high-level asset class suggested for instruments of this type."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed instrument type."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for operational lists of instrument types."),
    schema="secm",
)

day_count_convention = Table(
    "day_count_convention",
    metadata,
    Column("day_count_convention_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed day-count convention."),
    Column("code", String(60), nullable=False, unique=True, comment="Stable controlled code such as ACT_360, ACT_ACT_ICMA, or 30E_360."),
    Column("display_name", String(150), nullable=False, comment="Human-readable name shown to Operations and API consumers."),
    Column("description", Text, nullable=False, comment="Plain-language description of the accrual convention and its intended scope."),
    Column("standard_source", String(100), nullable=True, comment="Optional standards or market-practice source, such as ISDA or ICMA."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the convention, normally ACTIVE or RETIRED."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for dropdowns and operational catalogues."),
    schema="secm",
)

taxonomy = Table(
    "taxonomy",
    metadata,
    Column("taxonomy_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed internal classification domain."),
    Column("taxonomy_code", String(100), nullable=False, unique=True, comment="Unique code for the taxonomy domain, such as STRUCTURED_PRODUCT_ARCHETYPE or INTERNAL_SWAP_STRATEGY."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the taxonomy domain."),
    Column("description", Text, nullable=True, comment="Business purpose and governance boundary of the taxonomy domain."),
    Column("applies_to", String(40), nullable=False, server_default=text("'INSTRUMENT'"), comment="Reference-object kind to which values in this taxonomy may be assigned."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the taxonomy domain."),
    schema="secm",
)

taxonomy_value = Table(
    "taxonomy_value",
    metadata,
    Column("taxonomy_value_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed taxonomy value."),
    Column("taxonomy_id", UUID_V7, ForeignKey("secm.taxonomy.taxonomy_id"), nullable=False, comment="Taxonomy domain that governs this value."),
    Column("parent_taxonomy_value_id", UUID_V7, ForeignKey("secm.taxonomy_value.taxonomy_value_id"), nullable=True, comment="Optional parent value used to represent a hierarchy within the same taxonomy."),
    Column("value_code", String(100), nullable=False, comment="Unique controlled code of the value within its taxonomy domain."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the taxonomy value."),
    Column("description", Text, nullable=True, comment="Business definition of the taxonomy value."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the taxonomy value."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value within its taxonomy domain and hierarchy."),
    UniqueConstraint("taxonomy_id", "value_code", name="uq_taxonomy_value_code"),
    schema="secm",
)

instrument = Table(
    "instrument",
    metadata,
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), primary_key=True, comment="Reference node representing the economic instrument or contractual object."),
    Column("instrument_type_id", UUID_V7, ForeignKey("secm.instrument_type.instrument_type_id"), nullable=False, comment="Governed economic product type of the instrument."),
    Column("asset_class", String(40), nullable=False, comment="High-level asset class used for reporting and policy selection."),
    Column("issuer_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation issuing the instrument when an issuer relationship applies."),
    Column("base_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Primary contractual or denomination currency of the instrument; it is never a strategy reporting currency."),
    Column("effective_from", Date, nullable=True, comment="First business date on which the instrument exists or is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which the instrument is effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current version of the instrument definition."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing version sequence for the instrument definition."),
    schema="secm",
)

crypto_asset_terms = Table(
    "crypto_asset_terms",
    metadata,
    Column("crypto_asset_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated version of cryptoasset terms."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic DIGITAL_ASSET instrument governed by these cryptoasset terms."),
    Column("asset_subtype", String(40), nullable=False, comment="Cryptoasset subtype such as NATIVE, TOKEN, STABLECOIN, WRAPPED, BRIDGED, or OTHER."),
    Column("native_symbol", String(50), nullable=False, comment="Canonical or native symbol of the cryptoasset, distinct from venue-specific trading symbols."),
    Column("protocol_name", String(150), nullable=True, comment="Protocol, issuer programme, or token system name when applicable."),
    Column("issuer_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Issuer or controlling organisation when the cryptoasset has one; null for genuinely decentralised native assets."),
    Column("effective_from", Date, nullable=False, comment="First date for which this version of cryptoasset terms is effective."),
    Column("effective_to", Date, nullable=True, comment="Last date for which this version of cryptoasset terms is effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current approved cryptoasset terms version."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing terms version sequence for the cryptoasset instrument."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source payload evidencing this cryptoasset terms version when available."),
    UniqueConstraint("instrument_node_id", "sequence_no", name="uq_crypto_asset_terms_version"),
    CheckConstraint("asset_subtype IN ('NATIVE', 'TOKEN', 'STABLECOIN', 'WRAPPED', 'BRIDGED', 'OTHER')", name="ck_crypto_asset_terms_subtype"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_crypto_asset_terms_valid_period"),
    schema="secm",
)

crypto_asset_deployment = Table(
    "crypto_asset_deployment",
    metadata,
    Column("crypto_asset_deployment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one chain-specific cryptoasset deployment."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic cryptoasset instrument deployed on the network."),
    Column("crypto_network_id", UUID_V7, ForeignKey("secm.crypto_network.crypto_network_id"), nullable=False, comment="Blockchain or distributed-ledger network hosting the deployment."),
    Column("deployment_kind", String(30), nullable=False, comment="Deployment kind such as NATIVE, TOKEN_CONTRACT, WRAPPED, or BRIDGED."),
    Column("contract_address", String(500), nullable=True, comment="Chain-specific token or contract address; null for a native asset without a contract."),
    Column("token_standard", String(80), nullable=True, comment="Token standard or ledger asset type such as ERC20, SPL, CW20, or native ledger asset."),
    Column("on_chain_symbol", String(80), nullable=True, comment="Symbol exposed by the chain deployment, which may differ from the canonical asset symbol."),
    Column("decimals", Integer, nullable=True, comment="Smallest-unit decimal precision exposed by the chain deployment."),
    Column("is_canonical", Boolean, nullable=False, server_default=text("false"), comment="Whether this is the issuer or protocol's canonical deployment for the asset."),
    Column("effective_from", Date, nullable=False, comment="First date for which this deployment is valid."),
    Column("effective_to", Date, nullable=True, comment="Last date for which this deployment is valid."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this deployment is currently operationally valid."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, PAUSED, DEPRECATED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source payload evidencing the chain deployment when available."),
    UniqueConstraint("instrument_node_id", "crypto_network_id", "contract_address", name="uq_crypto_asset_deployment_network_address"),
    CheckConstraint("deployment_kind IN ('NATIVE', 'TOKEN_CONTRACT', 'WRAPPED', 'BRIDGED')", name="ck_crypto_asset_deployment_kind"),
    CheckConstraint("(deployment_kind = 'NATIVE' AND contract_address IS NULL) OR (deployment_kind <> 'NATIVE' AND contract_address IS NOT NULL)", name="ck_crypto_asset_deployment_address"),
    CheckConstraint("decimals IS NULL OR (decimals >= 0 AND decimals <= 36)", name="ck_crypto_asset_deployment_decimals"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_crypto_asset_deployment_valid_period"),
    schema="secm",
)

instrument_definition_version = Table(
    "instrument_definition_version",
    metadata,
    Column("instrument_definition_version_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one approved effective-dated canonical instrument definition version."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Stable economic instrument identity whose canonical definition is versioned."),
    Column("sequence_no", Integer, nullable=False, comment="Monotonically increasing definition version sequence for the instrument identity."),
    Column("instrument_type_id", UUID_V7, ForeignKey("secm.instrument_type.instrument_type_id"), nullable=False, comment="Governed economic type in force for this instrument definition version."),
    Column("asset_class", String(40), nullable=False, comment="High-level asset class in force for this definition version."),
    Column("issuer_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Issuer organisation in force for this definition version when applicable."),
    Column("base_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Base or denomination currency in force for this definition version."),
    Column("effective_from", Date, nullable=False, comment="First business date on which this canonical definition version applies."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this canonical definition version applies."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current approved operational definition version for the instrument identity."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Version approval status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source evidence supporting this canonical definition version."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Steward account approving this definition version."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this definition version was approved."),
    UniqueConstraint("instrument_node_id", "sequence_no", name="uq_instrument_definition_version_sequence"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_instrument_definition_version_valid_period"),
    schema="secm",
)

listing_definition_version = Table(
    "listing_definition_version",
    metadata,
    Column("listing_definition_version_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one approved effective-dated canonical listing definition version."),
    Column("listing_node_id", UUID_V7, ForeignKey("secm.listing.listing_node_id"), nullable=False, comment="Stable venue-listing identity whose canonical definition is versioned."),
    Column("sequence_no", Integer, nullable=False, comment="Monotonically increasing definition version sequence for the listing identity."),
    Column("market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=False, comment="Venue in force for this listing definition version."),
    Column("trading_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Trading currency in force for this listing definition version."),
    Column("trading_symbol", String(100), nullable=True, comment="Venue symbol in force for this listing definition version."),
    Column("quote_factor", Numeric(20, 8), nullable=False, server_default=text("1"), comment="Quotation convention factor in force for this listing definition version."),
    Column("unit_multiplier", Numeric(20, 8), nullable=False, server_default=text("1"), comment="Economic units represented by one traded unit in this listing definition version."),
    Column("effective_from", Date, nullable=False, comment="First business date on which this canonical listing definition version applies."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this canonical listing definition version applies."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current approved operational definition version for the listing identity."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Version approval status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source evidence supporting this canonical listing definition version."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Steward account approving this listing definition version."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this listing definition version was approved."),
    UniqueConstraint("listing_node_id", "sequence_no", name="uq_listing_definition_version_sequence"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_listing_definition_version_valid_period"),
    schema="secm",
)

instrument_taxonomy_assignment = Table(
    "instrument_taxonomy_assignment",
    metadata,
    Column("instrument_taxonomy_assignment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an instrument's taxonomy classification assignment."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument classified by the taxonomy value."),
    Column("taxonomy_value_id", UUID_V7, ForeignKey("secm.taxonomy_value.taxonomy_value_id"), nullable=False, comment="Governed taxonomy value assigned to the instrument."),
    Column("effective_from", Date, nullable=False, comment="First business date on which the taxonomy assignment is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which the taxonomy assignment is effective."),
    Column("is_primary", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the primary classification within its taxonomy domain for the effective period."),
    Column("source_system_id", String(100), nullable=True, comment="Source system or operational process that assigned the taxonomy value."),
    schema="secm",
)

listing = Table(
    "listing",
    metadata,
    Column("listing_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), primary_key=True, comment="Reference node representing the venue-specific tradable listing."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument represented by this listing."),
    Column("market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=False, comment="Market venue or segment on which this listing trades."),
    Column("trading_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which the listing is quoted and traded."),
    Column("trading_symbol", String(100), nullable=True, comment="Venue trading symbol or ticker for the listing."),
    Column("quote_factor", Numeric(20, 8), nullable=False, server_default=text("1"), comment="Quotation convention factor, for example 100 for a GBX quotation relative to GBP."),
    Column("unit_multiplier", Numeric(20, 8), nullable=False, server_default=text("1"), comment="Economic units represented by one traded unit or contract."),
    Column("is_primary_listing", Boolean, nullable=False, server_default=text("false"), comment="Whether this is the designated primary listing for the economic instrument."),
    Column("effective_from", Date, nullable=True, comment="First business date on which the listing is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which the listing is effective."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as ACTIVE, SUSPENDED, DELISTED, or EXPIRED."),
    schema="secm",
)

instrument_dates = Table(
    "instrument_dates",
    metadata,
    Column("instrument_dates_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the common-date record of an instrument."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, unique=True, comment="Economic instrument to which the common dates apply."),
    Column("effective_date", Date, nullable=True, comment="Date on which the instrument becomes economically effective."),
    Column("trading_date", Date, nullable=True, comment="Legacy ambiguous trading-date field retained for compatibility; use first_trading_date or last_trading_date for new records."),
    Column("first_trading_date", Date, nullable=True, comment="First date on which the instrument or listing is contractually intended to trade."),
    Column("last_trading_date", Date, nullable=True, comment="Last date on which the instrument is contractually permitted to trade."),
    Column("issue_date", Date, nullable=True, comment="Date on which the instrument was issued."),
    Column("strike_date", Date, nullable=True, comment="Date on which strike terms are set or fixed."),
    Column("settlement_date", Date, nullable=True, comment="Legacy generic settlement-date field retained for compatibility; use final_settlement_date for final instrument settlement."),
    Column("maturity_date", Date, nullable=True, comment="Date on which the instrument matures."),
    Column("expiry_date", Date, nullable=True, comment="Date on which rights under the instrument expire."),
    Column("cash_settlement_date", Date, nullable=True, comment="Date on which cash settlement is contractually due."),
    Column("final_valuation_date", Date, nullable=True, comment="Final contractual valuation or fixing date used to determine redemption or settlement."),
    Column("final_settlement_date", Date, nullable=True, comment="Final contractual settlement date of the economic instrument."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the common-date record was created."),
    schema="secm",
)

fund = Table(
    "fund",
    metadata,
    Column("fund_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), primary_key=True, comment="Canonical non-tradeable fund, umbrella, or sub-fund reference node; fund share classes remain separate economic instruments."),
    Column("fund_kind", String(40), nullable=False, comment="Fund structural kind such as UMBRELLA, SUB_FUND, STANDALONE, ETF_ISSUER, or PARTNERSHIP."),
    Column("parent_fund_reference_node_id", UUID_V7, ForeignKey("secm.fund.fund_reference_node_id"), nullable=True, comment="Optional umbrella or parent fund reference node for a sub-fund; null for a standalone fund or top-level umbrella."),
    Column("fund_manager_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation appointed as fund manager or AIFM/management company where applicable."),
    Column("domicile_country_code", String(3), nullable=True, comment="ISO 3166-1 alpha-3 domicile country code of the fund vehicle or sub-fund."),
    Column("legal_form", String(100), nullable=True, comment="Legal form such as OEIC, SICAV, ICAV, UNIT_TRUST, LIMITED_PARTNERSHIP, or CONTRACTUAL_FUND."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as DRAFT, ACTIVE, CLOSED, LIQUIDATING, or TERMINATED."),
    schema="secm",
)

fund_share_class_terms = Table(
    "fund_share_class_terms",
    metadata,
    Column("fund_share_class_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated version of fund share-class terms."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument node representing the subscribable or tradeable fund share class."),
    Column("fund_reference_node_id", UUID_V7, ForeignKey("secm.fund.fund_reference_node_id"), nullable=False, comment="Fund or sub-fund to which the share class belongs."),
    Column("share_class_code", String(100), nullable=False, comment="Manager or administrator share-class code, such as I_ACC_GBP or A_DIST_EUR."),
    Column("share_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which the share class NAV, dealing and nominal share value are denominated."),
    Column("income_treatment", String(30), nullable=False, comment="Income treatment such as ACCUMULATION, DISTRIBUTION, INCOME, or UNKNOWN."),
    Column("dealing_frequency", String(30), nullable=True, comment="Normal subscription and redemption dealing frequency such as DAILY, WEEKLY, MONTHLY, or CLOSED_ENDED."),
    Column("nav_frequency", String(30), nullable=True, comment="Official NAV calculation frequency such as DAILY, WEEKLY, MONTHLY, or AD_HOC."),
    Column("nav_publication_lag_business_days", Integer, nullable=False, server_default=text("0"), comment="Expected business-day publication lag of the official NAV after its market date; a valuation policy still decides whether and how to use it."),
    Column("effective_from", Date, nullable=False, comment="First business date for which this version of share-class terms is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date for which this version of share-class terms is effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current operationally approved share-class terms version."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing version sequence for the same share-class instrument."),
    UniqueConstraint("instrument_node_id", "sequence_no", name="uq_fund_share_class_terms_version"),
    schema="secm",
)

etp_terms = Table(
    "etp_terms",
    metadata,
    Column("etp_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated version of exchange-traded-product terms."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument node representing the ETF, ETC, ETN, ETV, or other exchange-traded product."),
    Column("etp_kind", String(30), nullable=False, comment="Concrete exchange-traded-product kind such as ETF, ETC, ETN, ETV, or ETI."),
    Column("legal_form", String(50), nullable=False, comment="Legal wrapper such as UCITS_FUND, DEBT_NOTE, CERTIFICATE, or OTHER."),
    Column("replication_method", String(30), nullable=False, server_default=text("'NOT_APPLICABLE'"), comment="How the product obtains exposure, such as PHYSICAL, SYNTHETIC, HYBRID, or NOT_APPLICABLE."),
    Column("collateralisation_type", String(30), nullable=False, server_default=text("'NOT_APPLICABLE'"), comment="Collateral or credit basis such as UNSECURED, SECURED, PHYSICAL, CASH, or NOT_APPLICABLE."),
    Column("redemption_model", String(40), nullable=False, comment="Redemption lifecycle such as OPEN_ENDED, FIXED_MATURITY, or ISSUER_REDEEMABLE."),
    Column("distribution_policy", String(30), nullable=True, comment="Income policy such as ACCUMULATING, DISTRIBUTING, NONE, or UNKNOWN."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Primary reference index, commodity, basket, asset, or other reference node when one is defined."),
    Column("effective_from", Date, nullable=False, comment="First business date for which this version of exchange-traded-product terms is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date for which this version of exchange-traded-product terms is effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current operationally approved ETP terms version."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing terms version sequence for the same exchange-traded-product instrument."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source payload evidencing this exchange-traded-product terms version when available."),
    UniqueConstraint("instrument_node_id", "sequence_no", name="uq_etp_terms_version"),
    CheckConstraint("etp_kind IN ('ETF', 'ETC', 'ETN', 'ETV', 'ETI')", name="ck_etp_terms_kind"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_etp_terms_valid_period"),
    schema="secm",
)

bond_terms = Table(
    "bond_terms",
    metadata,
    Column("bond_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated version of bond contractual terms."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic bond instrument governed by these terms."),
    Column("issue_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Contractual denomination and principal currency of the bond."),
    Column("par_amount", Numeric(30, 12), nullable=True, comment="Contractual denomination or par amount represented by one bond unit when applicable."),
    Column("coupon_type", String(40), nullable=False, comment="Coupon style such as FIXED, FLOATING, ZERO, INFLATION_LINKED, STEP_UP, PIK, or OTHER."),
    Column("coupon_rate", Numeric(20, 12), nullable=True, comment="Contractual annual coupon rate in decimal form when fixed or the current quoted reference rate when relevant; null for non-rate coupon forms."),
    Column("coupon_frequency_per_year", Integer, nullable=True, comment="Number of regular coupon payment periods per year; null for zero-coupon or irregular schedules."),
    Column("day_count_convention_id", UUID_V7, ForeignKey("secm.day_count_convention.day_count_convention_id"), nullable=True, comment="Governed day-count convention used for coupon accrual; null means not yet sourced or applicable."),
    Column("day_count_convention", String(40), nullable=True, comment="Legacy provider/source text for the day-count convention; the governed day_count_convention_id is canonical for new records."),
    Column("floating_reference_index", String(150), nullable=True, comment="Reference rate index for a floating-rate bond coupon, such as SONIA, SOFR, or EURIBOR; nullable until sourced."),
    Column("floating_spread", Numeric(20, 12), nullable=True, comment="Spread added to or subtracted from the floating reference index, in the agreed rate representation."),
    Column("redemption_amount_per_par", Numeric(30, 12), nullable=True, comment="Contractual final redemption amount per unit of par, normally 100 when quoted as percentage of par."),
    Column("quotation_basis", String(40), nullable=False, server_default=text("'PCT_OF_PAR'"), comment="Price quotation basis such as PCT_OF_PAR, CURRENCY_PER_UNIT, or YIELD; distinct from listing quote factor."),
    Column("effective_from", Date, nullable=False, comment="First business date for which this version of bond terms is effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date for which this version of bond terms is effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current operationally approved bond-terms version."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing version sequence for the same bond instrument."),
    UniqueConstraint("instrument_node_id", "sequence_no", name="uq_bond_terms_version"),
    schema="secm",
)

instrument_relationship = Table(
    "instrument_relationship",
    metadata,
    Column("instrument_relationship_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a typed relationship between two reference nodes."),
    Column("from_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Reference node from which the relationship originates."),
    Column("to_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Reference node to which the relationship points."),
    Column("relationship_type", String(60), nullable=False, comment="Controlled relationship type such as UNDERLYING, GUARANTOR, REFERENCE_INDEX, or CONSTITUENT."),
    Column("effective_from", Date, nullable=True, comment="First business date on which the relationship is valid."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which the relationship is valid."),
    Column("source_system_id", String(100), nullable=True, comment="Source system or feed from which the relationship was obtained."),
    UniqueConstraint("from_reference_node_id", "to_reference_node_id", "relationship_type", "effective_from", name="uq_instrument_relationship_business_key"),
    schema="secm",
)

instrument_composition = Table(
    "instrument_composition",
    metadata,
    Column("instrument_composition_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a dated parent-component composition entry."),
    Column("parent_instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic parent instrument containing the component."),
    Column("component_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Economic or reference component included in the parent composition."),
    Column("composition_role", String(60), nullable=False, comment="Business role of the component such as PAYOFF_COMPONENT, UNDERLYING, BENCHMARK, or PORTFOLIO_CONSTITUENT."),
    Column("composition_value", Numeric(30, 12), nullable=False, server_default=text("1"), comment="Signed value applied to the component; interpretation is governed by composition_value_kind."),
    Column("composition_value_kind", String(30), nullable=False, server_default=text("'SIGNED_MULTIPLIER'"), comment="Interpretation of composition_value: SIGNED_MULTIPLIER, PERCENT_WEIGHT, QUANTITY, or NOTIONAL_AMOUNT."),
    Column("component_sequence", Integer, nullable=False, server_default=text("1"), comment="Deterministic component occurrence order within the parent, terms version, and composition date."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=True, comment="Structured-product terms version governing this row; null for baskets, portfolios, and other non-contractual compositions."),
    Column("composition_date", Date, nullable=False, comment="Effective composition date, supporting dated baskets and reference portfolios."),
    Column("effective_to", Date, nullable=True, comment="Last business date for which this composition entry is applicable."),
    Column("source_system_id", String(100), nullable=True, comment="Source system, vendor, or operational process that supplied the composition."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this composition entry when available."),
    UniqueConstraint("parent_instrument_node_id", "structured_product_terms_id", "composition_date", "component_sequence", name="uq_instrument_composition_component_sequence"),
    CheckConstraint("composition_value_kind IN ('SIGNED_MULTIPLIER', 'PERCENT_WEIGHT', 'QUANTITY', 'NOTIONAL_AMOUNT')", name="ck_instrument_composition_value_kind"),
    CheckConstraint("component_sequence > 0", name="ck_instrument_composition_component_sequence"),
    CheckConstraint("effective_to IS NULL OR effective_to >= composition_date", name="ck_instrument_composition_valid_period"),
    schema="secm",
)


# trd: booked events, client distribution, fee, and cash-position domain.
strategy = Table(
    "strategy",
    metadata,
    Column("strategy_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a portfolio, fund, client book, or generic reporting ledger."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant permitted to own and operate the strategy; nullable only for legacy or platform records that tenant-facing services must reject until explicitly scoped."),
    Column("strategy_code", String(100), nullable=False, unique=True, comment="Unique convenient code used to identify the strategy operationally."),
    Column("display_name", String(250), nullable=False, comment="Human-readable strategy name."),
    Column("strategy_type", String(50), nullable=False, comment="Strategy kind such as FUND, CLIENT_BOOK, HOUSE_BOOK, MODEL_PORTFOLIO, or OTHER_LEDGER."),
    Column("base_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Base currency used for strategy reporting and P&L."),
    Column("legal_owner_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation legally owning or operating the strategy when applicable."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the strategy."),
    schema="trd",
)

cash_account = Table(
    "cash_account",
    metadata,
    Column("cash_account_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a cash, custody, margin, or settlement account."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=False, comment="Strategy to which this cash account belongs."),
    Column("account_holder_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation legally owning the cash account."),
    Column("custodian_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Custodian, bank, or counterparty maintaining the account."),
    Column("external_account_reference", String(250), nullable=True, comment="External account number or reference, protected and masked in application views as required."),
    Column("account_type", String(40), nullable=False, comment="Cash account kind such as CUSTODY, MARGIN, SETTLEMENT, or INTERNAL_LEDGER."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the cash account."),
    schema="trd",
)

trade = Table(
    "trade",
    metadata,
    Column("trade_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 internal identifier for a booked economic event."),
    Column("trade_subject_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, or cash currency that is directly booked by this trade."),
    Column("reference_instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=True, comment="Originating instrument for related cash events such as dividends, coupons, or resets."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=False, comment="Primary strategy, portfolio, or ledger receiving the trade."),
    Column("trade_type", String(50), nullable=False, comment="Economic event type such as INVESTMENT, SUBSCRIPTION, REDEMPTION, DIVIDEND, COUPON, RESET, or CASH_FLOW."),
    Column("trade_purpose", String(50), nullable=True, comment="Business intent such as INVESTMENT, HEDGING, REBALANCING, CLIENT_INSTRUCTION, or TRANSFER."),
    Column("market_activity", String(30), nullable=True, comment="Market context such as PRIMARY or SECONDARY when applicable."),
    Column("execution_price", Numeric(30, 12), nullable=True, comment="Booked execution price or contractual rate in the declared price basis."),
    Column("locked_ytm", Numeric(20, 12), nullable=True, comment="Yield-to-maturity locked at booking when supplied by the legacy trade workflow; scale is governed by the declared trade convention."),
    Column("price_basis", String(40), nullable=True, comment="Price convention such as UNIT_PRICE, PCT_OF_PAR, CLEAN, DIRTY, RATE, or CASH_AMOUNT."),
    Column("price_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which execution price or rate is expressed when relevant."),
    Column("quantity", Numeric(30, 12), nullable=False, comment="Signed booked quantity, nominal, units, or cash amount according to quantity unit."),
    Column("quantity_unit", String(40), nullable=False, comment="Unit of quantity such as UNITS, NOMINAL, SHARES, CONTRACTS, or CURRENCY_AMOUNT."),
    Column("trade_datetime_utc", DateTime(timezone=True), nullable=False, comment="UTC timestamp at which the economic execution or event occurred."),
    Column("instruction_date", Date, nullable=True, comment="Business date on which the trade instruction was received or issued."),
    Column("settlement_date", Date, nullable=True, comment="Contractual or expected settlement date of the trade."),
    Column("trader_person_id", UUID_V7, ForeignKey("secm.person.person_id"), nullable=True, comment="Human who made the commercial trading decision, whether internal or external."),
    Column("booked_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated internal user or service account that recorded the trade."),
    Column("execution_channel", String(40), nullable=False, comment="Execution or booking channel such as FIX, MANUAL_UI, API, FILE_IMPORT, EMAIL, or PHONE."),
    Column("source_system_id", String(100), nullable=True, comment="External source system, feed, or integration from which the trade was received."),
    Column("source_received_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the source trade message or file was received."),
    Column("execution_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=True, comment="Venue or market segment on which the execution occurred when known."),
    Column("dealing_capacity", String(30), nullable=True, comment="Firm capacity such as PRINCIPAL, AGENT, DISTRIBUTOR, or INTRODUCER."),
    Column("lifecycle_status", String(30), nullable=False, server_default=text("'BOOKED'"), comment="Lifecycle status such as BOOKED, CANCELLED, SUPERSEDED, or VOID."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the trade record was created."),
    Column("created_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated internal account that created the trade record."),
    Column("comment", Text, nullable=True, comment="Free-text operational comment attached to the trade."),
    CheckConstraint("quantity <> 0", name="ck_trade_quantity_non_zero"),
    schema="trd",
)

trade_lifecycle_event = Table(
    "trade_lifecycle_event",
    metadata,
    Column("trade_lifecycle_event_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one append-only lifecycle event on a booked trade."),
    Column("trade_id", UUID_V7, ForeignKey("trd.trade.trade_id"), nullable=False, comment="Booked trade whose lifecycle this event changes or records."),
    Column("sequence_no", Integer, nullable=False, comment="Strictly increasing sequence within the trade lifecycle event chain."),
    Column("event_type", String(30), nullable=False, comment="Lifecycle event such as BOOKED, AMENDED, CANCELLED, SUPERSEDED, NOVATED, or CORRECTED."),
    Column("event_datetime_utc", DateTime(timezone=True), nullable=False, comment="UTC time at which the lifecycle event became effective economically or operationally."),
    Column("source_system_id", String(100), nullable=True, comment="Source system or integration that supplied the lifecycle event."),
    Column("source_event_id", String(500), nullable=True, comment="Source event or message identifier used for idempotent processing."),
    Column("payload_hash", String(64), nullable=True, comment="Hash of the immutable source event payload or normalized correction details."),
    Column("supersedes_event_id", UUID_V7, ForeignKey("trd.trade_lifecycle_event.trade_lifecycle_event_id"), nullable=True, comment="Prior lifecycle event superseded by this correction or replacement."),
    Column("event_payload", Text, nullable=True, comment="Serialized normalized correction details; the original trade and source payload remain separately retained."),
    Column("recorded_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated internal account or service that recorded this lifecycle event."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem recorded the lifecycle event."),
    UniqueConstraint("trade_id", "sequence_no", name="uq_trade_lifecycle_event_sequence"),
    UniqueConstraint("source_system_id", "source_event_id", name="uq_trade_lifecycle_event_source_id"),
    schema="trd",
)

trade_party_role = Table(
    "trade_party_role",
    metadata,
    Column("trade_party_role_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a party's role on a trade."),
    Column("trade_id", UUID_V7, ForeignKey("trd.trade.trade_id"), nullable=False, comment="Trade to which the party role applies."),
    Column("organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation participating in the trade role when the party is a legal organisation."),
    Column("person_id", UUID_V7, ForeignKey("secm.person.person_id"), nullable=True, comment="Person participating in the trade role when the party is an individual."),
    Column("role", String(50), nullable=False, comment="Party role such as CLIENT, COUNTERPARTY, EXECUTING_BROKER, CUSTODIAN, DISTRIBUTOR, or ADVISER."),
    CheckConstraint("(organisation_id IS NOT NULL) <> (person_id IS NOT NULL)", name="ck_trade_party_role_exactly_one_party"),
    schema="trd",
)

trade_external_reference = Table(
    "trade_external_reference",
    metadata,
    Column("trade_external_reference_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an external trade reference assignment."),
    Column("trade_id", UUID_V7, ForeignKey("trd.trade.trade_id"), nullable=False, comment="Trade carrying the external reference."),
    Column("source_system_id", String(100), nullable=True, comment="Source system or external party namespace governing the reference."),
    Column("trade_party_role_id", UUID_V7, ForeignKey("trd.trade_party_role.trade_party_role_id"), nullable=True, comment="Relevant party role, for example the agent supplying a subscription reference."),
    Column("reference_type", String(50), nullable=False, comment="Reference type such as SOURCE_TRADE_ID, EXECUTION_LISTING_IDENTIFIER, AGENT_SUBRED_REFERENCE, or BASKET_REFERENCE."),
    Column("reference_value", String(500), nullable=False, comment="External reference value retained exactly as supplied."),
    Column("source_received_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this external reference was received."),
    schema="trd",
)

trade_fee = Table(
    "trade_fee",
    metadata,
    Column("trade_fee_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a fee, charge, tax, or revenue item attached to a trade."),
    Column("trade_id", UUID_V7, ForeignKey("trd.trade.trade_id"), nullable=False, comment="Trade to which this fee item belongs."),
    Column("fee_rule_id", UUID_V7, ForeignKey("fee.fee_rule.fee_rule_id"), nullable=True, comment="Optional contractual fee rule used to calculate this realised trade fee."),
    Column("fee_type", String(50), nullable=False, comment="Fee classification such as DISTRIBUTION, TRAILER, BROKERAGE, EXCHANGE, CUSTODY, TAX, or OTHER."),
    Column("fee_payer_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation contractually responsible for paying the fee; normally the issuer for distribution revenue."),
    Column("fee_recipient_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation entitled to receive the fee; normally the firm's legal entity for distribution revenue."),
    Column("fee_amount", Numeric(30, 12), nullable=False, comment="Monetary fee amount retained for reconciliation regardless of whether a rate also applies."),
    Column("fee_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which the fee amount is due or settled."),
    Column("fee_rate", Numeric(20, 10), nullable=True, comment="Contractual or calculated fee rate when the fee is rate-based."),
    Column("fee_rate_unit", String(10), nullable=True, comment="Unit of fee rate such as BPS or PCT."),
    Column("fee_basis", String(50), nullable=False, comment="Basis used to calculate the fee, such as GROSS_CONSIDERATION, NOTIONAL, NAV, or FIXED."),
    Column("accrual_date", Date, nullable=True, comment="Business date on which the fee is earned or accrued."),
    Column("settlement_date", Date, nullable=True, comment="Business date on which the fee is expected to settle."),
    Column("status", String(30), nullable=False, server_default=text("'EXPECTED'"), comment="Fee lifecycle status such as EXPECTED, CONFIRMED, PAID, WAIVED, or CANCELLED."),
    Column("external_reference", String(500), nullable=True, comment="External fee invoice, statement, or settlement reference."),
    schema="trd",
)


# fee: shared contractual fee vocabulary and effective-dated rule assignments.
# Realised trade fees remain in trd.trade_fee because they are trade facts.
fee_type = Table(
    "fee_type",
    metadata,
    Column("fee_type_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed fee classification."),
    Column("fee_type_code", String(50), nullable=False, unique=True, comment="Unique fee classification code such as MANAGEMENT, PERFORMANCE, ADMINISTRATION, DISTRIBUTION, BROKERAGE, or TAX."),
    Column("display_name", String(250), nullable=False, comment="Human-readable fee classification name."),
    Column("description", Text, nullable=True, comment="Business definition and inclusion guidance for this fee classification."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed fee classification."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for fee-type lists."),
    schema="fee",
)


fee_rule = Table(
    "fee_rule",
    metadata,
    Column("fee_rule_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one version of a contractual or operational fee rule."),
    Column("fee_type_id", UUID_V7, ForeignKey("fee.fee_type.fee_type_id"), nullable=False, comment="Governed classification of the fee calculated by this rule."),
    Column("rule_code", String(100), nullable=False, comment="Stable business code for the fee rule across its immutable versions."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of this fee rule version."),
    Column("calculation_method", String(30), nullable=False, comment="Calculation model such as RATE, FIXED, TIERED, PERFORMANCE, WAIVER, or REIMBURSEMENT."),
    Column("calculation_basis", String(50), nullable=False, comment="Base to which the rule applies, such as NAV, AUM, NOTIONAL, PERFORMANCE, TRANSACTION_VALUE, or FIXED."),
    Column("rate_value", Numeric(30, 12), nullable=True, comment="Rate or amount parameter; when rate_unit is PCT, a stored value of 12 means 12 percent."),
    Column("rate_unit", String(20), nullable=True, comment="Unit of rate_value such as PCT, BPS, AMOUNT, or MULTIPLIER."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of a fixed fee, cap, floor, or other monetary parameter when applicable."),
    Column("accrual_frequency", String(40), nullable=True, comment="Frequency at which the fee is accrued, such as DAILY, MONTHLY, QUARTERLY, or ANNUAL."),
    Column("payment_frequency", String(40), nullable=True, comment="Frequency at which the accrued fee is paid or transferred."),
    Column("day_count_convention_id", UUID_V7, ForeignKey("secm.day_count_convention.day_count_convention_id"), nullable=True, comment="Governed day-count convention used for prorating a time-based fee; null means not applicable or not yet sourced."),
    Column("day_count_convention", String(30), nullable=True, comment="Legacy provider/source text for the fee day-count convention; the governed day_count_convention_id is canonical for new rules."),
    Column("minimum_amount", Numeric(30, 12), nullable=True, comment="Optional minimum monetary amount for the fee calculation."),
    Column("maximum_amount", Numeric(30, 12), nullable=True, comment="Optional maximum monetary amount or cap for the fee calculation."),
    Column("parameters_json", JSONB, nullable=True, comment="Versioned model-specific parameters, such as performance-fee hurdle or high-water-mark configuration; core identity and amount fields remain typed columns."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning a private fee rule; null identifies a shared canonical rule."),
    Column("valid_from", Date, nullable=False, comment="First business date on which this fee rule version is valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this fee rule version is valid."),
    Column("version_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing version number for the rule code."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Convenience indicator for the current rule projection; date validity and status remain authoritative."),
    Column("supersedes_fee_rule_id", UUID_V7, ForeignKey("fee.fee_rule.fee_rule_id"), nullable=True, comment="Prior fee rule version superseded by this immutable version."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload from which the rule terms were obtained or validated."),
    Column("source_reference", String(500), nullable=True, comment="Human-readable prospectus, agreement, schedule, or other source reference for the rule."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Internal account that approved the rule for operational use."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the rule version was approved."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the immutable fee rule version was created."),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_fee_rule_valid_period"),
    CheckConstraint("version_no > 0", name="ck_fee_rule_positive_version"),
    UniqueConstraint("rule_code", "version_no", name="uq_fee_rule_code_version"),
    schema="fee",
)


fee_rule_target = Table(
    "fee_rule_target",
    metadata,
    Column("fee_rule_target_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for assigning a fee rule to one fee-bearing object."),
    Column("fee_rule_id", UUID_V7, ForeignKey("fee.fee_rule.fee_rule_id"), nullable=False, comment="Fee rule version assigned by this row."),
    Column("target_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Canonical or private reference node targeted by the rule, such as a fund, share class, AMC, bond, or structured product."),
    Column("target_strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=True, comment="Portfolio, mandate, managed reference portfolio, or other strategy targeted by the rule."),
    Column("application_mode", String(20), nullable=False, server_default=text("'ADDITIVE'"), comment="How the target rule combines with broader rules: ADDITIVE, REPLACE, DEFAULT, or WAIVE."),
    Column("priority", Integer, nullable=False, server_default=text("1"), comment="Deterministic evaluation priority when multiple applicable rules share a fee type."),
    Column("payer_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation contractually responsible for paying the fee when specified."),
    Column("recipient_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation entitled to receive the fee when specified."),
    Column("effective_from", Date, nullable=True, comment="Optional first business date on which this assignment is effective; it cannot extend the fee rule validity."),
    Column("effective_to", Date, nullable=True, comment="Optional last business date on which this assignment is effective."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Assignment lifecycle status such as ACTIVE, RETIRED, or REJECTED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this fee-rule assignment was created."),
    CheckConstraint("(target_reference_node_id IS NOT NULL) <> (target_strategy_id IS NOT NULL)", name="ck_fee_rule_target_exactly_one_target"),
    CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_fee_rule_target_valid_period"),
    CheckConstraint("priority > 0", name="ck_fee_rule_target_positive_priority"),
    schema="fee",
)

cash_balance = Table(
    "cash_balance",
    metadata,
    Column("cash_balance_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a cash-position snapshot."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=False, comment="Strategy, portfolio, or ledger owning the cash position."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which the cash balance is denominated."),
    Column("cash_account_id", UUID_V7, ForeignKey("trd.cash_account.cash_account_id"), nullable=True, comment="Specific custody, margin, settlement, or internal account holding the balance."),
    Column("balance_as_of_date", Date, nullable=False, comment="Business date for which the balance is declared."),
    Column("balance_as_of_datetime_utc", DateTime(timezone=True), nullable=False, comment="UTC cut-off timestamp at which the balance applies."),
    Column("balance_type", String(30), nullable=False, comment="Cash balance classification such as SETTLED, AVAILABLE, LEDGER, or MARGIN."),
    Column("amount", Numeric(30, 12), nullable=False, comment="Full signed currency balance at the stated as-of time, not a cash movement."),
    Column("source_system_id", String(100), nullable=True, comment="Custodian, administrator, accounting, or internal source supplying the balance."),
    Column("source_reference", String(500), nullable=True, comment="External statement, file, or message reference for the balance snapshot."),
    Column("received_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the balance snapshot was received or recorded."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Snapshot status such as ACTIVE, SUPERSEDED, or REJECTED."),
    Column("created_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated internal user or service account that created the snapshot record."),
    schema="trd",
)


# ten and ing: tenant scope plus controlled integration-boundary lineage.
tenant = Table(
    "tenant",
    metadata,
    Column("tenant_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a subscribing client, Fortem business context, or isolated tenant workspace."),
    Column("owning_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Organisation legally or commercially responsible for the tenant context."),
    Column("tenant_code", String(100), nullable=False, unique=True, comment="Stable unique internal code used to identify the tenant in operations and integrations."),
    Column("display_name", String(250), nullable=False, comment="Human-readable tenant name used in operations and client-facing administration."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Tenant lifecycle status such as ACTIVE, SUSPENDED, or RETIRED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the tenant was created."),
    schema="ten",
)

operating_profile = Table(
    "operating_profile",
    metadata,
    Column("operating_profile_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed composable tenant operating-profile definition."),
    Column("profile_code", String(100), nullable=False, unique=True, comment="Stable unique operating-profile code such as FUND_MANAGER, AMC_MANAGER, or STRUCTURED_PRODUCT_DISTRIBUTOR."),
    Column("display_name", String(250), nullable=False, comment="Human-readable operating-profile name used in onboarding, administration, and reporting."),
    Column("description", Text, nullable=True, comment="Business definition of the operating profile and the tenant activities it commonly represents."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed operating profile, such as ACTIVE, RETIRED, or SUPERSEDED."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering for operational-profile catalogues and onboarding templates."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this governed operating-profile definition was created."),
    schema="ten",
)

platform_module = Table(
    "platform_module",
    metadata,
    Column("platform_module_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed platform product capability."),
    Column("module_code", String(100), nullable=False, unique=True, comment="Stable unique capability code such as TRADING, FUND_MANAGEMENT, UCITS_CONTROLS, or STRUCTURED_PRODUCTS."),
    Column("display_name", String(250), nullable=False, comment="Human-readable platform-module name used in administration and product packaging."),
    Column("description", Text, nullable=True, comment="Business definition of the capability granted when this platform module is entitled to a tenant."),
    Column("module_category", String(40), nullable=False, comment="Broad module category such as CORE_REFERENCE, MARKET_DATA, TRADING, VALUATION, FUND, AMC, STRUCTURED_PRODUCT, or DISTRIBUTION."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed platform module, such as ACTIVE, RETIRED, or SUPERSEDED."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering for module catalogues and tenant administration."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this governed platform-module definition was created."),
    schema="ten",
)

tenant_operating_profile_assignment = Table(
    "tenant_operating_profile_assignment",
    metadata,
    Column("tenant_operating_profile_assignment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated tenant operating-profile assignment."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant classified by this operating-profile assignment."),
    Column("operating_profile_id", UUID_V7, ForeignKey("ten.operating_profile.operating_profile_id"), nullable=False, comment="Governed operating profile assigned to the tenant."),
    Column("assignment_source", String(30), nullable=False, comment="How the profile assignment was established, such as ONBOARDING, CONTRACT, MANUAL, or MIGRATION."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the assignment, such as PROPOSED, ACTIVE, REJECTED, RETIRED, or SUPERSEDED."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Authenticated account that approved the operating-profile assignment for tenant use."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the tenant operating-profile assignment was approved."),
    Column("valid_from", Date, nullable=False, comment="First business date on which this profile assignment is effective for the tenant."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this profile assignment is effective; null means open-ended."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this assignment version was recorded."),
    Column("supersedes_assignment_id", UUID_V7, ForeignKey("ten.tenant_operating_profile_assignment.tenant_operating_profile_assignment_id"), nullable=True, comment="Prior assignment version superseded by this row when profile classification is corrected or renewed."),
    UniqueConstraint("tenant_id", "operating_profile_id", "valid_from", name="uq_tenant_operating_profile_assignment_business_key"),
    CheckConstraint("assignment_source IN ('ONBOARDING', 'CONTRACT', 'MANUAL', 'MIGRATION')", name="ck_tenant_profile_assignment_source"),
    CheckConstraint("status IN ('PROPOSED', 'ACTIVE', 'REJECTED', 'RETIRED', 'SUPERSEDED')", name="ck_tenant_profile_assignment_status"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_profile_assignment_valid_period"),
    schema="ten",
)

operating_profile_module_recommendation = Table(
    "operating_profile_module_recommendation",
    metadata,
    Column("operating_profile_module_recommendation_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one profile-to-module onboarding recommendation."),
    Column("operating_profile_id", UUID_V7, ForeignKey("ten.operating_profile.operating_profile_id"), nullable=False, comment="Operating profile for which this module is recommended during tenant onboarding."),
    Column("platform_module_id", UUID_V7, ForeignKey("ten.platform_module.platform_module_id"), nullable=False, comment="Platform module recommended for the associated operating profile."),
    Column("recommendation_strength", String(30), nullable=False, server_default=text("'STANDARD'"), comment="Onboarding recommendation strength: CORE, STANDARD, OPTIONAL, or NOT_APPLICABLE; it never grants access."),
    Column("rationale", Text, nullable=True, comment="Business rationale explaining why the module is recommended for the operating profile."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of this profile-to-module onboarding recommendation."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the onboarding recommendation was created."),
    UniqueConstraint("operating_profile_id", "platform_module_id", name="uq_operating_profile_module_recommendation"),
    CheckConstraint("recommendation_strength IN ('CORE', 'STANDARD', 'OPTIONAL', 'NOT_APPLICABLE')", name="ck_profile_module_recommendation_strength"),
    schema="ten",
)

tenant_module_entitlement = Table(
    "tenant_module_entitlement",
    metadata,
    Column("tenant_module_entitlement_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated tenant platform-module entitlement version."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant receiving, suspending, or revoking access to the platform module."),
    Column("platform_module_id", UUID_V7, ForeignKey("ten.platform_module.platform_module_id"), nullable=False, comment="Governed platform module to which this entitlement lifecycle record applies."),
    Column("entitlement_state", String(30), nullable=False, comment="Entitlement state: GRANTED permits capability resolution; SUSPENDED and REVOKED do not."),
    Column("entitlement_source", String(30), nullable=False, comment="Source of the entitlement decision, such as CONTRACT, TRIAL, MANUAL, or MIGRATION."),
    Column("external_contract_reference", String(250), nullable=True, comment="Optional commercial contract, order, or subscription reference evidencing the module entitlement decision."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Authenticated account that approved the entitlement lifecycle decision."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the module entitlement lifecycle decision was approved."),
    Column("valid_from", Date, nullable=False, comment="First business date on which this entitlement state applies to the tenant."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this entitlement state applies; null means open-ended."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this entitlement version was recorded."),
    Column("supersedes_entitlement_id", UUID_V7, ForeignKey("ten.tenant_module_entitlement.tenant_module_entitlement_id"), nullable=True, comment="Prior module-entitlement version superseded by this lifecycle record."),
    UniqueConstraint("tenant_id", "platform_module_id", "valid_from", name="uq_tenant_module_entitlement_business_key"),
    CheckConstraint("entitlement_state IN ('GRANTED', 'SUSPENDED', 'REVOKED')", name="ck_tenant_module_entitlement_state"),
    CheckConstraint("entitlement_source IN ('CONTRACT', 'TRIAL', 'MANUAL', 'MIGRATION')", name="ck_tenant_module_entitlement_source"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_module_entitlement_valid_period"),
    schema="ten",
)

Index("ix_tenant_operating_profile_assignment_lookup", tenant_operating_profile_assignment.c.tenant_id, tenant_operating_profile_assignment.c.operating_profile_id, tenant_operating_profile_assignment.c.status, tenant_operating_profile_assignment.c.valid_from, tenant_operating_profile_assignment.c.valid_to)
Index("ix_tenant_module_entitlement_resolve", tenant_module_entitlement.c.tenant_id, tenant_module_entitlement.c.platform_module_id, tenant_module_entitlement.c.entitlement_state, tenant_module_entitlement.c.valid_from, tenant_module_entitlement.c.valid_to)

tenant_database_registry = Table(
    "tenant_database_registry",
    metadata,
    Column("tenant_database_registry_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one tenant overlay database route."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, unique=True, comment="Tenant whose confidential operational overlay is routed to the registered database."),
    Column("database_name", String(250), nullable=False, unique=True, comment="Trusted logical PostgreSQL database name for the tenant overlay; never accepted directly from a client request."),
    Column("cluster_id", String(250), nullable=False, comment="Trusted PostgreSQL cluster or infrastructure identifier hosting the overlay database."),
    Column("environment", String(30), nullable=False, server_default=text("'PROD'"), comment="Deployment environment of the registered tenant database such as PROD, UAT, TEST, or SANDBOX."),
    Column("schema_version", Integer, nullable=False, comment="Last successfully applied overlay schema revision recorded by the control plane."),
    Column("connection_secret_reference", String(500), nullable=False, comment="Reference to a secret-manager entry; credentials are never stored in this table."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Route lifecycle status such as PROVISIONING, ACTIVE, SUSPENDED, RETIRED, or FAILED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the route was registered."),
    Column("updated_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp of the latest route or schema-version update."),
    schema="ten",
)

tenant_user_account = Table(
    "tenant_user_account",
    metadata,
    Column("tenant_user_account_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one user's membership in a tenant."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant whose data and operations the user may access."),
    Column("user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Application user account granted access to the tenant."),
    Column("membership_role", String(40), nullable=False, comment="Tenant role such as ADMIN, OPERATIONS, VALUATION, or READ_ONLY."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Membership lifecycle status such as ACTIVE, SUSPENDED, or REVOKED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the membership is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the membership is effective."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the membership was created."),
    UniqueConstraint("tenant_id", "user_account_id", "valid_from", name="uq_tenant_user_account_membership"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_user_account_valid_period"),
    schema="ten",
)

canonical_reference_link = Table(
    "canonical_reference_link",
    metadata,
    Column("canonical_reference_link_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for tenant-local evidence linking an object to central canonical identity."),
    Column("local_object_type", String(50), nullable=False, comment="Tenant-database object kind carrying the central reference, such as TRADE_SUBJECT, POSITION_LINE, or OVERRIDE."),
    Column("local_object_id", UUID_V7, nullable=False, comment="UUID of the object in the tenant overlay database; no cross-database foreign key is possible."),
    Column("canonical_reference_node_id", UUID_V7, nullable=False, comment="Immutable central financial-reference UUID validated through the canonical API."),
    Column("canonical_object_type", String(50), nullable=False, comment="Central object kind validated for the link, such as INSTRUMENT, LISTING, REFERENCE_NODE, or CURRENCY."),
    Column("canonical_version", Integer, nullable=False, comment="Canonical definition version observed and validated when this link evidence was recorded."),
    Column("canonical_status", String(30), nullable=False, comment="Central lifecycle status observed during validation, such as ACTIVE or MATURED."),
    Column("validated_as_of_date", Date, nullable=False, comment="Business date on which the canonical API validation was effective."),
    Column("validated_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the central UUID was validated."),
    Column("validation_result", String(30), nullable=False, server_default=text("'VALID'"), comment="Validation result such as VALID, STALE, REJECTED, or NOT_FOUND."),
    Column("central_api_version", String(100), nullable=False, comment="Version of the central canonical API contract that supplied the validation response."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of this tenant-local link evidence."),
    UniqueConstraint("local_object_type", "local_object_id", name="uq_canonical_reference_link_local_object"),
    schema="ten",
)

reference_node_scope = Table(
    "reference_node_scope",
    metadata,
    Column("reference_node_scope_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a reference-node visibility and ownership assignment."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, unique=True, comment="Canonical or private reference node whose visibility is governed by this scope record."),
    Column("scope_type", String(30), nullable=False, comment="Visibility scope such as SHARED_CANONICAL, TENANT_PRIVATE, or RESTRICTED_SHARED."),
    Column("owner_tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning a private or restricted node; null for universally shared canonical nodes."),
    Column("promoted_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Canonical node created when a tenant-private node is deliberately promoted after validation."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Scope lifecycle status such as ACTIVE, PROMOTED, RESTRICTED, or RETIRED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the scope assignment was recorded."),
    schema="ten",
)

integration_source_system = Table(
    "integration_source_system",
    metadata,
    Column("integration_source_system_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an external or internal system participating in an integration."),
    Column("owning_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation operating or owning the source system, provider feed, bank platform, or client application."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant scope when the source system is client-specific; null for shared provider or Fortem systems."),
    Column("system_code", String(100), nullable=False, unique=True, comment="Stable unique code for the source system, for example CUSTODIAN_B_ASSET_PROD or LSEG_DSS_PROD."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the source system or integration endpoint."),
    Column("source_kind", String(40), nullable=False, comment="Source category such as BANK, CUSTODIAN, CLIENT_PMS, ADMINISTRATOR, VENDOR, EXCHANGE, or INTERNAL."),
    Column("environment", String(20), nullable=False, server_default=text("'PROD'"), comment="System environment such as PROD, UAT, TEST, or SANDBOX."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the source system integration."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the source system record was created."),
    schema="ing",
)

external_id_namespace = Table(
    "external_id_namespace",
    metadata,
    Column("external_id_namespace_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a source-specific external identifier namespace."),
    Column("integration_source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=False, comment="Source system that governs the identifier namespace."),
    Column("namespace_code", String(150), nullable=False, unique=True, comment="Stable unique namespace code, for example BANK_A_STATIC_PROD or CUSTODIAN_B_ASSET_PROD."),
    Column("external_object_type", String(50), nullable=True, comment="Optional object-type restriction such as LISTING, REFERENCE_NODE, STRATEGY, TRADE, ORGANISATION, or PERSON."),
    Column("description", Text, nullable=True, comment="Business explanation of the source identifier domain and its intended use."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the namespace."),
    Column("valid_from", Date, nullable=False, comment="First business date on which identifiers in this namespace are valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which identifiers in this namespace are valid."),
    schema="ing",
)

source_payload = Table(
    "source_payload",
    metadata,
    Column("source_payload_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one retained inbound source payload or message."),
    Column("integration_source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=False, comment="Source system that submitted or supplied the payload."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning the submission when the payload contains tenant-scoped data."),
    Column("payload_format", String(40), nullable=False, comment="Payload format such as JSON, CSV, XML, FPML, FIX, ISO20022, XLSX, or PDF."),
    Column("external_message_reference", String(500), nullable=True, comment="Upstream message, file, batch, or delivery reference supplied by the source."),
    Column("payload_locator", String(1000), nullable=False, comment="Immutable object-store locator or secure external location of the retained raw payload."),
    Column("payload_sha256", String(64), nullable=False, comment="SHA-256 checksum used to establish payload identity and idempotency."),
    Column("source_published_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the source published the payload when supplied."),
    Column("received_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem received the payload."),
    Column("processing_status", String(30), nullable=False, server_default=text("'RECEIVED'"), comment="Payload processing status such as RECEIVED, VALIDATED, MAPPED, REJECTED, or SUPERSEDED."),
    schema="ing",
)

external_object_mapping = Table(
    "external_object_mapping",
    metadata,
    Column("external_object_mapping_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a time-bound mapping from an external source code to a Fortem UUID."),
    Column("external_id_namespace_id", UUID_V7, ForeignKey("ing.external_id_namespace.external_id_namespace_id"), nullable=False, comment="Namespace in which the external object identifier is meaningful."),
    Column("external_object_type", String(50), nullable=False, comment="Controlled type of the external object such as LISTING, REFERENCE_NODE, STRATEGY, TRADE, ORGANISATION, or PERSON."),
    Column("external_id_value", String(500), nullable=False, comment="External object identifier exactly as supplied by the governing source namespace."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning this mapping when it is a tenant-local alias; null means the mapping is shared canonical data."),
    Column("target_object_type", String(50), nullable=False, comment="Controlled Fortem target type corresponding to target_object_id; enforced by mapping-service validation and later database trigger."),
    Column("target_object_id", UUID_V7, nullable=False, comment="Fortem immutable UUID resolved from the external identifier; polymorphic target validation is intentionally deferred to controlled service and trigger logic."),
    Column("context_market_venue_id", UUID_V7, ForeignKey("secm.market_venue.market_venue_id"), nullable=True, comment="Venue context required when an external identifier refers to a specific listing or market representation."),
    Column("mapping_role", String(30), nullable=False, server_default=text("'PRIMARY'"), comment="Mapping role such as PRIMARY, TRADING_ROUTE, ALIAS, LEGACY, or SOURCE_REFERENCE."),
    Column("mapping_method", String(30), nullable=False, comment="How the mapping was established, for example MANUAL, PROVIDER_MATCH, CLIENT_CONFIRMED, or RULE."),
    Column("status", String(30), nullable=False, server_default=text("'PROPOSED'"), comment="Mapping verification status such as PROPOSED, VERIFIED, REJECTED, RETIRED, or SUPERSEDED."),
    Column("confidence", Numeric(5, 4), nullable=True, comment="Optional confidence score from zero to one for an automated or provider-supplied mapping."),
    Column("verified_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Internal authenticated user or service account that verified the mapping."),
    Column("verified_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the mapping was verified."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the external-to-Fortem mapping is valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the external-to-Fortem mapping is valid."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this mapping version was recorded by Fortem."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload that evidenced or proposed the mapping when applicable."),
    Column("supersedes_mapping_id", UUID_V7, ForeignKey("ing.external_object_mapping.external_object_mapping_id"), nullable=True, comment="Prior mapping version superseded by this mapping when a source code is reassigned or corrected."),
    UniqueConstraint("external_id_namespace_id", "external_object_type", "external_id_value", "context_market_venue_id", "tenant_id", "valid_from", name="uq_external_object_mapping_business_key"),
    schema="ing",
)


# cfg: tenant-owned operational configuration for administrator, agent, and custodian feeds.
external_data_mapping_profile = Table(
    "external_data_mapping_profile",
    metadata,
    Column("external_data_mapping_profile_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one tenant-owned external operational-data mapping profile."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant that owns the operational feed configuration and its mappings."),
    Column("provider_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Canonical organisation acting as administrator, agent, custodian, bank, or other operational-data provider."),
    Column("integration_source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=False, comment="Integration source system or endpoint from which this profile's files or messages are received."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=True, comment="Optional governed dataset representing the provider feed when it is catalogued as a dataset; null for operational feeds without a dataset contract."),
    Column("profile_code", String(100), nullable=False, comment="Stable tenant-local code for the feed interpretation, such as ABC_DAILY_VALUATION or ABC_DAILY_ACCOUNTING."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the tenant operational-data mapping profile."),
    Column("operational_context", String(40), nullable=False, comment="Governed purpose of the external identifiers, initially VALUATION or ACCOUNTING."),
    Column("allowed_source_scope", String(40), nullable=False, comment="Source-record scope accepted by the profile: FUND, FUND_SHARE_CLASS, or BOTH."),
    Column("normalization_mode", String(40), nullable=False, server_default=text("'EXACT'"), comment="Profile-controlled external-ID lookup normalisation: EXACT preserves value; TRIM_UPPER trims outer whitespace and uppercases it."),
    Column("parser_contract_version", String(100), nullable=True, comment="Version of the file, message, or parser contract interpreted by this profile."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the profile: DRAFT, ACTIVE, SUSPENDED, RETIRED, or SUPERSEDED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which this profile may resolve operational source identifiers."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this profile may resolve operational source identifiers; null means open-ended."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this tenant operational-data mapping profile was created."),
    Column("retired_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the profile was retired when no longer available for new processing."),
    UniqueConstraint("tenant_id", "profile_code", "valid_from", name="uq_cfg_external_data_mapping_profile_business_key"),
    CheckConstraint("operational_context IN ('VALUATION', 'ACCOUNTING')", name="ck_cfg_mapping_profile_context"),
    CheckConstraint("allowed_source_scope IN ('FUND', 'FUND_SHARE_CLASS', 'BOTH')", name="ck_cfg_mapping_profile_scope"),
    CheckConstraint("normalization_mode IN ('EXACT', 'TRIM_UPPER')", name="ck_cfg_mapping_profile_normalization"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_cfg_mapping_profile_valid_period"),
    schema="cfg",
)

external_data_object_mapping = Table(
    "external_data_object_mapping",
    metadata,
    Column("external_data_object_mapping_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated tenant operational identifier mapping."),
    Column("external_data_mapping_profile_id", UUID_V7, ForeignKey("cfg.external_data_mapping_profile.external_data_mapping_profile_id"), nullable=False, comment="Tenant operational-data mapping profile that defines how this external identifier is interpreted."),
    Column("source_object_scope", String(40), nullable=False, comment="Scope represented by the external source record: FUND or FUND_SHARE_CLASS."),
    Column("target_object_type", String(40), nullable=False, comment="Canonical target type corresponding to target_object_id; must match source_object_scope in V1."),
    Column("target_object_id", UUID_V7, nullable=False, comment="Immutable UUID of the resolved canonical fund or fund share-class instrument; validated by a PostgreSQL trigger."),
    Column("external_id_raw", String(500), nullable=False, comment="External identifier exactly as received in the provider file, message, or report; immutable evidence and never normalised in place."),
    Column("external_id_normalized", String(500), nullable=False, comment="Profile-normalised lookup form of external_id_raw used for deterministic matching while raw evidence remains preserved."),
    Column("mapping_role", String(30), nullable=False, server_default=text("'PRIMARY'"), comment="Business role of the identifier mapping, initially PRIMARY, ALIAS, LEGACY, or SOURCE_REFERENCE."),
    Column("mapping_method", String(30), nullable=False, comment="How the mapping was established, such as MANUAL, CLIENT_CONFIRMED, PROVIDER_MATCH, or RULE."),
    Column("status", String(30), nullable=False, server_default=text("'PROPOSED'"), comment="Lifecycle and approval status: PROPOSED, APPROVED, REJECTED, RETIRED, or SUPERSEDED; only APPROVED mappings resolve production input."),
    Column("confidence", Numeric(5, 4), nullable=True, comment="Optional confidence score from zero to one for a proposed or automatically matched mapping."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Authenticated internal user or service account that approved this mapping for operational resolution."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this mapping became approved for operational resolution."),
    Column("valid_from", Date, nullable=False, comment="First report business date for which this identifier mapping is valid."),
    Column("valid_to", Date, nullable=True, comment="Last report business date for which this identifier mapping is valid; null means open-ended."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this mapping version was recorded in tenant configuration."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Inbound source payload that evidenced or proposed the mapping when applicable."),
    Column("supersedes_mapping_id", UUID_V7, ForeignKey("cfg.external_data_object_mapping.external_data_object_mapping_id"), nullable=True, comment="Prior tenant operational mapping superseded by this version when an identifier is reassigned or corrected."),
    CheckConstraint("source_object_scope IN ('FUND', 'FUND_SHARE_CLASS')", name="ck_cfg_external_data_mapping_scope"),
    CheckConstraint("target_object_type = source_object_scope", name="ck_cfg_external_data_mapping_target_scope"),
    CheckConstraint("mapping_role IN ('PRIMARY', 'ALIAS', 'LEGACY', 'SOURCE_REFERENCE')", name="ck_cfg_external_data_mapping_role"),
    CheckConstraint("status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'RETIRED', 'SUPERSEDED')", name="ck_cfg_external_data_mapping_status"),
    CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_cfg_external_data_mapping_confidence"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_cfg_external_data_mapping_valid_period"),
    schema="cfg",
)

Index("ix_cfg_external_data_mapping_profile_lookup", external_data_mapping_profile.c.tenant_id, external_data_mapping_profile.c.provider_organisation_id, external_data_mapping_profile.c.operational_context, external_data_mapping_profile.c.valid_from, external_data_mapping_profile.c.valid_to)
Index("ix_cfg_external_data_object_mapping_resolve", external_data_object_mapping.c.external_data_mapping_profile_id, external_data_object_mapping.c.source_object_scope, external_data_object_mapping.c.external_id_normalized, external_data_object_mapping.c.valid_from, external_data_object_mapping.c.valid_to)
Index("ix_cfg_external_data_object_mapping_target", external_data_object_mapping.c.target_object_type, external_data_object_mapping.c.target_object_id)


# md: market-data catalogue, valuation-cut, and observation domain.
data_provider = Table(
    "data_provider",
    metadata,
    Column("data_provider_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed provider delivery identity."),
    Column("organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Organisation commercially or operationally providing the data service."),
    Column("provider_code", String(100), nullable=False, unique=True, comment="Stable unique code for the provider delivery identity, such as BLOOMBERG, LSEG_DSS, FACTSET, or INTERNAL_FORTEM."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the provider delivery identity."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the data provider record."),
    schema="md",
)

provider_product = Table(
    "provider_product",
    metadata,
    Column("provider_product_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a provider commercial product family."),
    Column("data_provider_id", UUID_V7, ForeignKey("md.data_provider.data_provider_id"), nullable=False, comment="Provider offering the commercial product family."),
    Column("product_code", String(150), nullable=False, comment="Provider-controlled or Fortem-governed code for the product family, such as DATA_LICENSE or DATASCOPE_SELECT."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the provider product family."),
    Column("description", Text, nullable=True, comment="Commercial and operational description of the provider product family."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the provider product family."),
    UniqueConstraint("data_provider_id", "product_code", name="uq_provider_product_code"),
    schema="md",
)

dataset = Table(
    "dataset",
    metadata,
    Column("dataset_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed provider content universe and entitlement scope."),
    Column("provider_product_id", UUID_V7, ForeignKey("md.provider_product.provider_product_id"), nullable=False, comment="Provider product family through which the dataset is commercially supplied."),
    Column("dataset_code", String(150), nullable=False, comment="Stable code for the data universe, such as BLOOMBERG_COMMODITY_INDICES_EOD or FACTSET_US_EQUITIES_EOD."),
    Column("display_name", String(250), nullable=False, comment="Human-readable dataset name."),
    Column("data_domain", String(50), nullable=False, comment="Data domain such as MARKET_DATA, REFERENCE_DATA, CORPORATE_ACTIONS, FUND_DATA, ESG, or MACRO."),
    Column("coverage_description", Text, nullable=True, comment="Description of asset-class, geography, measure, frequency, methodology, and other content boundaries."),
    Column("delivery_channel", String(30), nullable=True, comment="Operational delivery mechanism such as API, FILE, SFTP, STREAM, MANUAL, or MULTI_CHANNEL."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the dataset."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the dataset definition is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the dataset definition is effective."),
    UniqueConstraint("provider_product_id", "dataset_code", name="uq_dataset_provider_product_code"),
    schema="md",
)

data_licence = Table(
    "data_licence",
    metadata,
    Column("data_licence_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a versioned contractual data-use right or licence."),
    Column("licensor_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Organisation granting or controlling the contractual data-use right."),
    Column("licensee_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Fortem or client organisation holding the contractual data-use right."),
    Column("licence_code", String(150), nullable=False, unique=True, comment="Stable internal code for the specific licence or contractual right."),
    Column("display_name", String(250), nullable=False, comment="Human-readable licence name."),
    Column("licence_reference", String(500), nullable=True, comment="External agreement, order-form, or contractual reference where retention is permitted."),
    Column("permitted_use_description", Text, nullable=False, comment="Human-readable contractual description of permitted valuation, risk, reporting, redistribution, or other uses."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Licence lifecycle status such as ACTIVE, EXPIRED, SUSPENDED, or TERMINATED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the licence right is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the licence right is effective."),
    schema="md",
)

dataset_licence_assignment = Table(
    "dataset_licence_assignment",
    metadata,
    Column("dataset_licence_assignment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an effective-dated licence assignment to a dataset."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=False, comment="Dataset governed by the assigned licence."),
    Column("data_licence_id", UUID_V7, ForeignKey("md.data_licence.data_licence_id"), nullable=False, comment="Contractual data-use right assigned to the dataset."),
    Column("licence_role", String(30), nullable=False, comment="Role of the licence for the dataset, such as ACQUISITION, INTERNAL_USE, CLIENT_USE, or REDISTRIBUTION."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the licence applies to the dataset."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the licence applies to the dataset."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the dataset licence assignment."),
    UniqueConstraint("dataset_id", "data_licence_id", "licence_role", "valid_from", name="uq_dataset_licence_assignment_business_key"),
    schema="md",
)

tenant_dataset_entitlement = Table(
    "tenant_dataset_entitlement",
    metadata,
    Column("tenant_dataset_entitlement_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a tenant's effective-dated permission to use a dataset."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant receiving the governed data-use entitlement."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=False, comment="Dataset to which the entitlement applies."),
    Column("dataset_licence_assignment_id", UUID_V7, ForeignKey("md.dataset_licence_assignment.dataset_licence_assignment_id"), nullable=True, comment="Specific dataset licence assignment evidencing the entitlement when one is known and applicable."),
    Column("use_purpose", String(40), nullable=False, comment="Permitted intended use such as VALUATION, RISK, INTERNAL_REPORTING, CLIENT_REPORTING, or REDISTRIBUTION."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Entitlement status such as ACTIVE, SUSPENDED, EXPIRED, or REVOKED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the tenant may use the dataset for the stated purpose."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the tenant may use the dataset for the stated purpose."),
    UniqueConstraint("tenant_id", "dataset_id", "use_purpose", "valid_from", name="uq_tenant_dataset_entitlement_business_key"),
    schema="ten",
)

valuation_cut = Table(
    "valuation_cut",
    metadata,
    Column("valuation_cut_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a named business valuation cut."),
    Column("cut_code", String(100), nullable=False, unique=True, comment="Unique code such as LONDON_CLOSE, NEW_YORK_CLOSE, or FUND_NAV_CUT."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the valuation cut."),
    Column("timezone_name", String(100), nullable=False, comment="IANA timezone name used to interpret the valuation cut."),
    Column("local_time", String(20), nullable=False, comment="Local wall-clock time at which the valuation cut occurs, expressed as HH:MM:SS."),
    Column("market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=True, comment="Optional calendar governing valid session dates and roll behaviour for this valuation cut."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the valuation cut definition."),
    schema="md",
)

series_measure_definition = Table(
    "series_measure_definition",
    metadata,
    Column("series_measure_definition_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed definition of the economic meaning of a market-data series observation."),
    Column("measure_code", String(50), nullable=False, unique=True, comment="Stable unique semantic code such as PRICE, FX_RATE, IMPLIED_VOLATILITY, YIELD, RATE, CREDIT_SPREAD, or VOLUME."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the market-data measurement definition."),
    Column("description", Text, nullable=True, comment="Business definition of the observed value and its intended analytical interpretation."),
    Column("unit_type", String(40), nullable=False, comment="Governed unit category such as CURRENCY_PRICE, PERCENT, BASIS_POINTS, INDEX_POINTS, QUANTITY, or CURRENCY_AMOUNT."),
    Column("default_change_method", String(40), nullable=False, comment="Default period-on-period analytical convention: RELATIVE_RETURN, ABSOLUTE_CHANGE, BASIS_POINT_CHANGE, or MONETARY_CHANGE; policies may explicitly override it."),
    Column("change_display_unit", String(40), nullable=False, comment="Display unit for the default change, such as PERCENT, VOLATILITY_POINTS, BASIS_POINTS, PIPS, UNITS, or CURRENCY_AMOUNT."),
    Column("display_decimal_places", Integer, nullable=False, server_default=text("4"), comment="Default number of decimal places when presenting a raw observation; this does not limit stored precision."),
    Column("change_decimal_places", Integer, nullable=False, server_default=text("4"), comment="Default number of decimal places when presenting a period-on-period change; this does not limit calculated precision."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed definition, such as ACTIVE, RETIRED, or SUPERSEDED."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering for governed measurement-definition catalogues."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the governed measurement definition was created."),
    CheckConstraint("unit_type IN ('CURRENCY_PRICE', 'PERCENT', 'BASIS_POINTS', 'INDEX_POINTS', 'QUANTITY', 'CURRENCY_AMOUNT')", name="ck_series_measure_definition_unit_type"),
    CheckConstraint("default_change_method IN ('RELATIVE_RETURN', 'ABSOLUTE_CHANGE', 'BASIS_POINT_CHANGE', 'MONETARY_CHANGE')", name="ck_series_measure_definition_change_method"),
    CheckConstraint("display_decimal_places >= 0 AND change_decimal_places >= 0", name="ck_series_measure_definition_nonnegative_precision"),
    schema="md",
)

market_data_series = Table(
    "market_data_series",
    metadata,
    Column("market_data_series_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a precisely defined market-data series."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Canonical node observed, priced, valued, or otherwise measured by this series."),
    Column("series_type", String(50), nullable=False, comment="Series kind such as OFFICIAL_CLOSE, BID, ASK, LAST, EVALUATED_PRICE, FX_SPOT, INDEX_LEVEL, or MARK."),
    Column("value_type", String(40), nullable=False, comment="Value shape such as PRICE, RATE, YIELD, SPREAD, INDEX_LEVEL, VOLUME, or QUANTITY."),
    Column("measure_definition_id", UUID_V7, ForeignKey("md.series_measure_definition.series_measure_definition_id"), nullable=True, comment="Governed semantic definition of what one observation measures and how a normal period-on-period movement is expressed; nullable only during legacy-series backfill."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which the series values are expressed when applicable."),
    Column("default_dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=True, comment="Default source dataset for catalogue discovery; each observation still records its actual dataset provenance."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=True, comment="Named business cut represented by the series when it is cut-specific."),
    Column("expected_frequency_code", String(30), nullable=False, server_default=text("'EVENT_DRIVEN'"), comment="Expected cadence such as BUSINESS_DAILY, CALENDAR_DAILY, INTRADAY, MONTHLY, QUARTERLY, or EVENT_DRIVEN; used for coverage and date validation."),
    Column("expected_market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=True, comment="Calendar expected to govern valid market dates for this series; nullable only when no calendar is meaningful or a resolver derives one from the listing venue."),
    Column("coverage_start_date", Date, nullable=True, comment="First market date the source declares this series to cover; does not imply every expected session has been received."),
    Column("coverage_end_date", Date, nullable=True, comment="Last market date the source declares this series to cover; null while the series remains open-ended."),
    Column("source_system_id", String(100), nullable=False, comment="Legacy vendor, venue, calculation-agent, or internal-system code supplying the series; migrate to provider/dataset and source-payload lineage."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the market-data series."),
    Column("is_official", Boolean, nullable=False, server_default=text("false"), comment="Whether the series is designated as an official source for its stated observation type."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the series definition was created."),
    CheckConstraint("coverage_end_date IS NULL OR coverage_start_date IS NULL OR coverage_end_date >= coverage_start_date", name="ck_market_data_series_coverage_range"),
    schema="md",
)

market_data_vintage = Table(
    "market_data_vintage",
    metadata,
    Column("market_data_vintage_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one provider source vintage or extract version."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=False, comment="Governed dataset from which this source vintage was delivered."),
    Column("data_provider_id", UUID_V7, ForeignKey("md.data_provider.data_provider_id"), nullable=False, comment="Provider responsible for publishing this source vintage."),
    Column("source_vintage_key", String(250), nullable=True, comment="Provider revision, file, batch, run, or other stable source-vintage identifier when supplied."),
    Column("source_published_at_utc", DateTime(timezone=True), nullable=True, comment="UTC time at which the provider published this vintage; null only when the provider supplies no publication timestamp."),
    Column("received_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC time at which Fortem received or accepted this source vintage."),
    Column("value_basis", String(40), nullable=False, server_default=text("'RAW'"), comment="Lineage basis of values in this vintage such as RAW, VENDOR_ADJUSTED, or RESTATED."),
    Column("vintage_status", String(30), nullable=False, server_default=text("'CURRENT'"), comment="Lifecycle state such as CURRENT, CORRECTED, RESTATED, SUPERSEDED, or REJECTED."),
    Column("content_hash", String(128), nullable=True, comment="Hash of the retained source extract or normalized vintage content for duplicate and integrity detection."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained raw payload evidencing this source vintage when available."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC time at which the source vintage record was created."),
    UniqueConstraint("dataset_id", "source_vintage_key", name="uq_market_data_vintage_dataset_key"),
    schema="md",
)

market_data_observation = Table(
    "market_data_observation",
    metadata,
    Column("market_data_observation_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one scalar market-data observation."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=False, comment="Series to which this observation belongs."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=False, comment="Actual governed dataset from which this observation was sourced; mandatory immutable provenance even when the series has a default dataset."),
    Column("market_data_vintage_id", UUID_V7, ForeignKey("md.market_data_vintage.market_data_vintage_id"), nullable=True, comment="Provider source vintage containing this observation; nullable only for legacy rows pending lineage backfill."),
    Column("acquisition_licence_id", UUID_V7, ForeignKey("md.data_licence.data_licence_id"), nullable=True, comment="Specific licence or right under which Fortem acquired or retained this observation when known; tenant access is evaluated separately."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained raw payload or message containing the observation when source-level evidence is available."),
    Column("market_date", Date, nullable=True, comment="Business date for which the value is economically applicable; separate from source, observation, and receipt timestamps and mandatory for newly onboarded end-of-day or fund-NAV observations."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=True, comment="Named valuation cut represented by this particular observation when more precise than the series-level cut."),
    Column("observed_at_utc", DateTime(timezone=True), nullable=False, comment="UTC timestamp at which the value was observed or is economically applicable."),
    Column("received_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the system received or stored the observation."),
    Column("value", Numeric(30, 12), nullable=False, comment="Observed scalar value in the convention defined by the market-data series."),
    Column("value_basis", String(40), nullable=False, server_default=text("'RAW'"), comment="Value lineage such as RAW, SPLIT_ADJUSTED, VENDOR_ADJUSTED, or DERIVED."),
    Column("source_timestamp_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp carried by the upstream source for this observation."),
    Column("source_published_at_utc", DateTime(timezone=True), nullable=True, comment="UTC publication timestamp carried by the source for this observation or its vintage."),
    Column("source_sequence", String(100), nullable=True, comment="Upstream sequence, revision, or message identifier used for ordering and correction lineage."),
    Column("source_observation_key", String(250), nullable=True, comment="Stable source-provided observation key used to make replayed ingestion idempotent within a series and dataset."),
    Column("quality_status", String(30), nullable=False, server_default=text("'ACCEPTED'"), comment="Data-quality status such as ACCEPTED, SUSPECT, REJECTED, or SUPERSEDED."),
    Column("supersedes_observation_id", UUID_V7, ForeignKey("md.market_data_observation.market_data_observation_id"), nullable=True, comment="Prior observation superseded or corrected by this observation when applicable."),
    Column("source_payload_reference", String(500), nullable=True, comment="Pointer or opaque reference to retained source payload and lineage evidence."),
    schema="md",
)

market_data_series_dimension = Table(
    "market_data_series_dimension",
    metadata,
    Column("market_data_series_dimension_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one descriptive dimension of a market-data series."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=False, comment="Market-data series whose precise observable definition is being described."),
    Column("dimension_code", String(50), nullable=False, comment="Controlled dimension name such as TENOR, STRIKE, DELTA, QUOTE_SIDE, FIXING, SESSION, or SETTLEMENT."),
    Column("dimension_value", String(250), nullable=False, comment="Dimension value in canonical text form, for example 1M, ATM, BID, or LONDON_CLOSE."),
    Column("numeric_value", Numeric(30, 12), nullable=True, comment="Optional numeric representation of the dimension value when calculations need it."),
    Column("unit_code", String(30), nullable=True, comment="Optional unit for numeric_value, such as MONTHS, PERCENT, POINTS, or BASIS_POINTS."),
    UniqueConstraint("market_data_series_id", "dimension_code", "dimension_value", name="uq_market_data_series_dimension"),
    schema="md",
)


Index("ix_listing_instrument_venue", listing.c.instrument_node_id, listing.c.market_venue_id)
Index("ix_trade_strategy_datetime", trade.c.strategy_id, trade.c.trade_datetime_utc)
Index("ix_cash_balance_strategy_as_of", cash_balance.c.strategy_id, cash_balance.c.balance_as_of_datetime_utc)
Index("ix_external_object_mapping_lookup", external_object_mapping.c.external_id_namespace_id, external_object_mapping.c.external_object_type, external_object_mapping.c.external_id_value, external_object_mapping.c.valid_from, external_object_mapping.c.valid_to)
Index("ix_external_object_mapping_target", external_object_mapping.c.target_object_type, external_object_mapping.c.target_object_id)
Index("ix_market_data_observation_series_observed", market_data_observation.c.market_data_series_id, market_data_observation.c.observed_at_utc)
Index("ix_market_data_observation_dataset_observed", market_data_observation.c.dataset_id, market_data_observation.c.observed_at_utc)
Index("ix_market_data_series_calendar_frequency", market_data_series.c.expected_market_calendar_id, market_data_series.c.expected_frequency_code)
Index("ix_market_data_series_measure_definition", market_data_series.c.measure_definition_id)
Index("ix_tenant_user_account_lookup", tenant_user_account.c.tenant_id, tenant_user_account.c.user_account_id, tenant_user_account.c.status, tenant_user_account.c.valid_from, tenant_user_account.c.valid_to)
Index("ix_market_data_series_dimension_lookup", market_data_series_dimension.c.dimension_code, market_data_series_dimension.c.dimension_value, market_data_series_dimension.c.market_data_series_id)
Index("uq_market_data_observation_source_key", market_data_observation.c.market_data_series_id, market_data_observation.c.dataset_id, text("COALESCE(market_data_vintage_id, '00000000-0000-0000-0000-000000000000'::uuid)"), market_data_observation.c.source_observation_key, unique=True, postgresql_where=text("source_observation_key IS NOT NULL"))
Index("uq_trade_external_reference_source_value", trade_external_reference.c.source_system_id, trade_external_reference.c.reference_type, trade_external_reference.c.reference_value, unique=True, postgresql_where=text("source_system_id IS NOT NULL"))
Index("uq_cash_balance_snapshot_source", cash_balance.c.strategy_id, text("COALESCE(cash_account_id, '00000000-0000-0000-0000-000000000000'::uuid)"), cash_balance.c.currency_id, cash_balance.c.balance_as_of_datetime_utc, cash_balance.c.balance_type, text("COALESCE(source_system_id, '')"), unique=True)


# Second-draft reference lifecycle, economic terms, valuation, and Soft-NAV models.
organisation_identifier = Table(
    "organisation_identifier", metadata,
    Column("organisation_identifier_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an effective-dated organisation identifier assignment."),
    Column("organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Legal entity or branch carrying the identifier."),
    Column("identifier_scheme", String(50), nullable=False, comment="Identifier scheme such as LEI, BIC, REGISTRATION_NUMBER, TAX_ID, or VENDOR_ID."),
    Column("identifier_value", String(500), nullable=False, comment="Identifier value exactly as assigned by the governing scheme or provider."),
    Column("issuer_name", String(250), nullable=True, comment="Issuer or authority governing the identifier when relevant."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the identifier assignment is valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the identifier assignment is valid."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained payload evidencing the identifier assignment when available."),
    UniqueConstraint("organisation_id", "identifier_scheme", "identifier_value", "valid_from", name="uq_organisation_identifier_business_key"), schema="secm",
)

instrument_party_role = Table(
    "instrument_party_role", metadata,
    Column("instrument_party_role_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an organisation's effective-dated role on an instrument."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument to which the organisation is related."),
    Column("organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=False, comment="Organisation performing the stated instrument role."),
    Column("role", String(50), nullable=False, comment="Role such as ISSUER, GUARANTOR, CALCULATION_AGENT, PAYING_AGENT, ARRANGER, or HEDGING_ENTITY."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the party role is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the party role is effective."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained payload evidencing the party role when available."),
    UniqueConstraint("instrument_node_id", "organisation_id", "role", "valid_from", name="uq_instrument_party_role_business_key"), schema="secm",
)

geographic_area = Table(
    "geographic_area", metadata,
    Column("geographic_area_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a geographic, jurisdictional, or reporting area."),
    Column("area_code", String(50), nullable=False, unique=True, comment="Stable unique code for the area such as WORLD, EUROPE, EU, DE, or WESTERN_EUROPE."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the area."),
    Column("official_name", String(500), nullable=True, comment="Official legal or geographic name where applicable."),
    Column("area_type", String(40), nullable=False, comment="Area kind such as WORLD, CONTINENT, SUBREGION, COUNTRY_TERRITORY, SUPRANATIONAL, or INTERNAL_REGION."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the area definition."),
    Column("valid_from", Date, nullable=True, comment="First business date on which the area definition is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the area definition is effective."), schema="secm",
)

country_terms = Table(
    "country_terms", metadata,
    Column("geographic_area_id", UUID_V7, ForeignKey("secm.geographic_area.geographic_area_id"), primary_key=True, comment="Country or territory geographic area to which ISO country terms apply."),
    Column("iso3166_1_a2", String(2), nullable=False, unique=True, comment="ISO 3166-1 alpha-2 country code."),
    Column("iso3166_1_a3", String(3), nullable=False, unique=True, comment="ISO 3166-1 alpha-3 country code."),
    Column("iso3166_1_numeric", String(3), nullable=False, unique=True, comment="ISO 3166-1 numeric country code preserved as text for leading zeroes."), schema="secm",
)

geographic_area_membership = Table(
    "geographic_area_membership", metadata,
    Column("geographic_area_membership_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an effective-dated membership between two geographic areas."),
    Column("child_area_id", UUID_V7, ForeignKey("secm.geographic_area.geographic_area_id"), nullable=False, comment="More specific geographic area belonging to the parent."),
    Column("parent_area_id", UUID_V7, ForeignKey("secm.geographic_area.geographic_area_id"), nullable=False, comment="Broader geographic, political, or internal reporting area."),
    Column("relationship_type", String(40), nullable=False, comment="Membership kind such as GEOGRAPHIC_PART_OF, POLITICAL_MEMBER_OF, or INTERNAL_CLASSIFICATION."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the membership is valid."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the membership is valid."),
    UniqueConstraint("child_area_id", "parent_area_id", "relationship_type", "valid_from", name="uq_geographic_area_membership_business_key"), schema="secm",
)

market_calendar = Table(
    "market_calendar", metadata,
    Column("market_calendar_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed market or settlement calendar definition."),
    Column("calendar_code", String(100), nullable=False, unique=True, comment="Stable unique calendar code such as XLON_TRADING, TARGET2, NYSE, or CRYPTO_24X7."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the calendar."),
    Column("timezone_name", String(100), nullable=False, comment="IANA timezone used by the calendar."),
    Column("calendar_kind", String(40), nullable=False, comment="Calendar use such as TRADING, SETTLEMENT, FIXING, HOLIDAY, or CONTINUOUS_24X7."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the calendar definition."), schema="cal",
)

market_calendar_session = Table(
    "market_calendar_session",
    metadata,
    Column("market_calendar_session_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one calendar date's session definition."),
    Column("market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=False, comment="Calendar to which this dated session belongs."),
    Column("session_date", Date, nullable=False, comment="Local calendar date represented by this session definition."),
    Column("session_status", String(30), nullable=False, comment="Session state such as OPEN, CLOSED, or HALF_DAY."),
    Column("open_local_time", Time, nullable=True, comment="Local wall-clock opening time for an open or half-day session."),
    Column("close_local_time", Time, nullable=True, comment="Local wall-clock closing time for an open or half-day session."),
    Column("source_reference", String(250), nullable=True, comment="Source or publication reference supporting this session definition."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this session definition was created."),
    UniqueConstraint("market_calendar_id", "session_date", name="uq_market_calendar_session_date"),
    CheckConstraint(
        "(session_status = 'CLOSED' AND open_local_time IS NULL AND close_local_time IS NULL) OR "
        "(session_status IN ('OPEN', 'HALF_DAY') AND open_local_time IS NOT NULL AND close_local_time IS NOT NULL)",
        name="ck_market_calendar_session_times",
    ),
    schema="cal",
)

market_calendar_holiday = Table(
    "market_calendar_holiday",
    metadata,
    Column("market_calendar_holiday_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one calendar holiday or closure reason."),
    Column("market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=False, comment="Calendar to which this holiday entry belongs."),
    Column("holiday_date", Date, nullable=False, comment="Local calendar date on which the holiday or closure applies."),
    Column("holiday_name", String(250), nullable=False, comment="Human-readable holiday or closure name."),
    Column("holiday_kind", String(40), nullable=False, server_default=text("'FULL_CLOSE'"), comment="Closure kind such as FULL_CLOSE, BANK_HOLIDAY, or MARKET_HOLIDAY."),
    Column("source_reference", String(250), nullable=True, comment="Source or publication reference supporting this holiday entry."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which this holiday definition was created."),
    UniqueConstraint("market_calendar_id", "holiday_date", name="uq_market_calendar_holiday_date"),
    schema="cal",
)

listing_quotation_terms = Table(
    "listing_quotation_terms", metadata,
    Column("listing_quotation_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an effective-dated listing quotation convention."),
    Column("listing_node_id", UUID_V7, ForeignKey("secm.listing.listing_node_id"), nullable=False, comment="Venue-specific listing governed by the quotation convention."),
    Column("quote_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency in which displayed listing quotes are expressed."),
    Column("quote_unit_code", String(40), nullable=False, comment="Quotation unit such as GBX, PCT_OF_PAR, INDEX_POINT, or CURRENCY_PER_UNIT."),
    Column("quote_factor", Numeric(20, 8), nullable=False, server_default=text("1"), comment="Divisor converting the displayed quote into the economic price unit."),
    Column("display_decimals", Integer, nullable=True, comment="Number of decimals normally displayed for the quote."),
    Column("tick_size", Numeric(20, 8), nullable=True, comment="Minimum permitted price increment under the quotation convention."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the quotation terms apply."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the quotation terms apply."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing sequence for corrected quotation-term versions."), schema="secm",
)

instrument_contract_unit_terms = Table(
    "instrument_contract_unit_terms", metadata,
    Column("instrument_contract_unit_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for effective-dated instrument contract-unit economics."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument governed by the contract unit terms."),
    Column("unit_multiplier", Numeric(30, 12), nullable=False, server_default=text("1"), comment="Economic units represented by one traded or held instrument unit or contract."),
    Column("unit_of_measure", String(40), nullable=False, comment="Economic unit such as SHARE, CONTRACT, NOTIONAL, INDEX_POINT, BARREL, or MWH."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the contract unit terms apply."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the contract unit terms apply."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing sequence for corrected contract-unit versions."), schema="secm",
)

schedule = Table(
    "schedule", metadata,
    Column("schedule_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a reusable contractual, observation, payment, or fixing schedule."),
    Column("owner_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, component, or reference node owning the schedule."),
    Column("schedule_type", String(50), nullable=False, comment="Schedule purpose such as COUPON, RESET, FIXING, AUTOCALL_OBSERVATION, FINAL_VALUATION, or PAYMENT."),
    Column("calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=True, comment="Calendar used to interpret scheduled events when applicable."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the schedule."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained payload evidencing the schedule when available."), schema="secm",
)

schedule_event = Table(
    "schedule_event", metadata,
    Column("schedule_event_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one dated event in a schedule."),
    Column("schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=False, comment="Schedule to which the dated event belongs."),
    Column("event_sequence", Integer, nullable=False, comment="Deterministic sequence of the event within its schedule."),
    Column("event_type", String(40), nullable=False, comment="Event purpose such as OBSERVATION, FIXING, PAYMENT, RESET, or EXERCISE."),
    Column("event_date", Date, nullable=False, comment="Business date of the scheduled event."),
    Column("payment_date", Date, nullable=True, comment="Payment date associated with the scheduled event when distinct."),
    Column("status", String(30), nullable=False, server_default=text("'SCHEDULED'"), comment="Lifecycle status such as SCHEDULED, CONFIRMED, CANCELLED, or SUPERSEDED."),
    UniqueConstraint("schedule_id", "event_sequence", name="uq_schedule_event_sequence"), schema="secm",
)

future_family = Table(
    "future_family", metadata,
    Column("future_family_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a non-tradeable reusable futures contract specification."),
    Column("family_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, unique=True, comment="Non-tradeable FUTURE_FAMILY reference node representing the product specification."),
    Column("underlying_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Underlying index, commodity, rate, security, or reference object for the futures family."),
    Column("contract_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Standard contract currency for futures in the family."),
    Column("expiry_cycle", String(100), nullable=True, comment="Standard expiry cycle or month-code rule for the family."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the non-tradeable futures family."), schema="secm",
)

return_profile = Table(
    "return_profile", metadata,
    Column("return_profile_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed generic performance-return profile."),
    Column("profile_code", String(60), nullable=False, unique=True, comment="Stable controlled code such as PRICE_RETURN, NET_TOTAL_RETURN, or EXCESS_TOTAL_RETURN."),
    Column("display_name", String(150), nullable=False, comment="Human-readable name of the generic return profile."),
    Column("description", Text, nullable=False, comment="Plain-language definition of how performance or income is represented."),
    Column("base_return_basis", String(30), nullable=False, comment="Underlying basis of the profile, such as PRICE, TOTAL, or INCOME_ONLY."),
    Column("income_treatment", String(50), nullable=False, comment="Treatment of distributed income, such as NONE, REINVESTED_GROSS, REINVESTED_NET, or POINTS_ONLY."),
    Column("tax_treatment", String(50), nullable=True, comment="Tax convention applied to income when relevant, such as NONE, GROSS, or NET_WITHHOLDING."),
    Column("financing_treatment", String(50), nullable=False, server_default=text("'NONE'"), comment="Treatment of financing or reference-rate adjustments, such as NONE or SUBTRACT_REFERENCE_RATE."),
    Column("requires_financing_reference", Boolean, nullable=False, server_default=text("false"), comment="Whether a consumer must provide a financing-rate reference for this profile."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed return profile."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for operational profile lists."),
    schema="secm",
)

index_kind_catalogue = Table(
    "index_kind_catalogue", metadata,
    Column("index_kind_catalogue_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one governed index-kind catalogue entry."),
    Column("index_kind_code", String(40), nullable=False, unique=True, comment="Stable controlled code used by index terms, proposals, and integrations, such as PUBLIC or PROPRIETARY."),
    Column("display_name", String(150), nullable=False, comment="Human-readable label shown to Operations users."),
    Column("description", Text, nullable=False, comment="Governed plain-language meaning of the index kind."),
    Column("dissemination_class", String(30), nullable=False, comment="Whether the index is publicly disseminated, restricted, private, or bespoke; this describes access rather than methodology ownership."),
    Column("methodology_ownership", String(40), nullable=False, comment="Ownership or control of the methodology, such as PROVIDER_OWNED, CLIENT_OWNED, OPEN_OR_PUBLIC, or MIXED."),
    Column("example_text", String(500), nullable=True, comment="Short representative example that helps Operations choose the correct semantic category."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the governed index-kind catalogue entry."),
    Column("sort_order", Integer, nullable=False, server_default=text("0"), comment="Display ordering value for index-kind selection lists."),
    schema="secm",
)

index_family = Table(
    "index_family", metadata,
    Column("index_family_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a conceptual index family or lineage."),
    Column("family_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, unique=True, comment="Non-tradeable INDEX_FAMILY reference node representing the conceptual grouping."),
    Column("provider_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation administering or publishing the index family when known."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the index family."),
    schema="secm",
)

index_terms = Table(
    "index_terms", metadata,
    Column("index_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), primary_key=True, comment="Concrete INDEX reference node representing one return or currency variant."),
    Column("index_family_id", UUID_V7, ForeignKey("secm.index_family.index_family_id"), nullable=True, comment="Conceptual index family to which this concrete index variant belongs."),
    Column("index_kind", String(40), ForeignKey("secm.index_kind_catalogue.index_kind_code"), nullable=False, comment="Governed index-kind code describing dissemination and methodology ownership semantics."),
    Column("return_profile_id", UUID_V7, ForeignKey("secm.return_profile.return_profile_id"), nullable=True, comment="Generic return profile governing the variant; nullable while an unapproved source definition remains incomplete."),
    Column("base_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which the index level is calculated or published."),
    Column("administrator_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation responsible for administering the index methodology when known."),
    Column("calculation_agent_organisation_id", UUID_V7, ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Organisation responsible for calculating or disseminating the index level when distinct from the administrator."),
    Column("base_date", Date, nullable=True, comment="Base date from which the index level history is defined."),
    Column("base_level", Numeric(30, 12), nullable=True, comment="Starting index level on the base date."),
    Column("methodology_reference", String(500), nullable=True, comment="Reference to the governing methodology document or source identifier."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the concrete index variant."),
    schema="secm",
)

index_methodology_version = Table(
    "index_methodology_version", metadata,
    Column("index_methodology_version_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one effective-dated index methodology version."),
    Column("index_node_id", UUID_V7, ForeignKey("secm.index_terms.index_node_id"), nullable=False, comment="Concrete index variant governed by this methodology version."),
    Column("sequence_no", Integer, nullable=False, comment="Monotonically increasing methodology version sequence for the index variant."),
    Column("effective_from", Date, nullable=False, comment="First business date on which this methodology version applies."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this methodology version applies."),
    Column("weighting_method", String(100), nullable=True, comment="Weighting method such as MARKET_CAP, EQUAL_WEIGHT, PRICE_WEIGHTED, or RULE_BASED."),
    Column("rebalance_frequency", String(100), nullable=True, comment="Scheduled rebalancing frequency or rule."),
    Column("calculation_frequency", String(100), nullable=True, comment="Frequency at which the index level is calculated or disseminated."),
    Column("dividend_treatment", String(100), nullable=True, comment="Methodology-specific dividend, distribution, or income treatment."),
    Column("financing_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Reference rate or curve used by an excess-return methodology when applicable."),
    Column("launch_date", Date, nullable=True, comment="Provider launch date of the methodology or index variant."),
    Column("is_backtested_history", Boolean, nullable=False, server_default=text("false"), comment="Whether the methodology version describes pre-launch hypothetical or back-tested history."),
    Column("methodology_document_uri", String(1000), nullable=True, comment="URI or stable locator for the methodology document when available."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Approval lifecycle status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source payload evidencing this methodology version when available."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="User account approving this methodology version."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this methodology version was approved."),
    UniqueConstraint("index_node_id", "sequence_no", name="uq_index_methodology_version_sequence"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_index_methodology_version_valid_period"),
    schema="secm",
)

future_terms = Table(
    "future_terms", metadata,
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), primary_key=True, comment="Individual expiry-level future economic instrument."),
    Column("future_family_id", UUID_V7, ForeignKey("secm.future_family.future_family_id"), nullable=False, comment="Non-tradeable future family governing standard contract economics."),
    Column("contract_month", Date, nullable=False, comment="Contract month or delivery-month anchor for the individual future."),
    Column("last_trade_date", Date, nullable=True, comment="Last date on which the individual contract may be traded."),
    Column("settlement_method", String(30), nullable=False, comment="Settlement method such as CASH, PHYSICAL, or EFP."),
    Column("delivery_start_date", Date, nullable=True, comment="Start of physical delivery period when applicable."),
    Column("delivery_end_date", Date, nullable=True, comment="End of physical delivery period when applicable."), schema="secm",
)

option_terms = Table(
    "option_terms", metadata,
    Column("option_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one version of an economic option's static contract terms."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic option instrument governed by these terms; the instrument identity remains stable across terms versions."),
    Column("version_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing version number for corrected or amended static option terms."),
    Column("effective_from", Date, nullable=False, server_default=text("CURRENT_DATE"), comment="First business date on which this static option-terms version is contractually effective."),
    Column("effective_to", Date, nullable=True, comment="Last business date on which this static option-terms version is contractually effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Operational pointer indicating the currently approved option-terms version for this instrument; as-of queries still use dates and status."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle state of this option-terms version such as DRAFT, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("supersedes_option_terms_id", UUID_V7, ForeignKey("secm.option_terms.option_terms_id"), nullable=True, comment="Prior option-terms version superseded by this version when a correction or legal amendment is recorded."),
    Column("underlying_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Exact underlying instrument, listing, index, future, currency pair, or reference object."),
    Column("option_type", String(10), nullable=False, comment="Vanilla option direction. The first slice permits CALL or PUT only; digital and barrier effects are separate features."),
    Column("exercise_style", String(20), nullable=False, comment="Exercise style: EUROPEAN, AMERICAN, or BERMUDAN (the internal spelling of FpML Bermuda)."),
    Column("strike_value", Numeric(30, 12), nullable=True, comment="Contractual strike value. Nullable during source staging or when a reset schedule determines the future strike."),
    Column("strike_mode", String(30), nullable=False, server_default=text("'FIXED'"), comment="How the contractual strike is supplied: FIXED, FORWARD_START, or RESET."),
    Column("strike_reset_schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Schedule containing contractual strike-determination events for FORWARD_START or RESET options."),
    Column("strike_reference_initial_fixing_id", UUID_V7, ForeignKey("secm.structured_product_initial_fixing.structured_product_initial_fixing_id"), nullable=True, comment="Immutable structured-product initial fixing that anchors a percentage strike; keeps a child option traceable to its parent terms version."),
    Column("strike_basis", String(30), nullable=False, server_default=text("'ABSOLUTE'"), comment="Meaning of strike_value: ABSOLUTE monetary price, INDEX_POINTS, FX_RATE, PERCENT_OF_SPOT, or PERCENT_OF_INITIAL."),
    Column("strike_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of an ABSOLUTE or FX_RATE strike; not required for an index-point or percentage strike."),
    Column("premium_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Convention or quoting currency for option premium. The amount and payment event remain trade-specific."),
    Column("settlement_method", String(30), nullable=False, comment="Settlement method aligned with FpML: CASH, PHYSICAL, ELECTION, or CASH_OR_PHYSICAL."),
    Column("settlement_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of a cash settlement payoff; required for CASH and CASH_OR_PHYSICAL during canonical validation."),
    Column("exercise_schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Dated permitted exercise schedule for a BERMUDAN option; European and American options use common instrument dates unless a schedule is needed for extra rules."),
    UniqueConstraint("instrument_node_id", "version_no", name="uq_option_terms_version"),
    CheckConstraint("version_no > 0", name="ck_option_terms_version_positive"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_option_terms_valid_period"),
    CheckConstraint("option_type IN ('CALL', 'PUT')", name="ck_option_terms_type"),
    CheckConstraint("exercise_style IN ('EUROPEAN', 'AMERICAN', 'BERMUDAN')", name="ck_option_terms_exercise_style"),
    CheckConstraint("settlement_method IN ('CASH', 'PHYSICAL', 'ELECTION', 'CASH_OR_PHYSICAL')", name="ck_option_terms_settlement_method"),
    CheckConstraint("strike_mode IN ('FIXED', 'FORWARD_START', 'RESET')", name="ck_option_terms_strike_mode"),
    CheckConstraint("(strike_mode = 'FIXED' AND strike_value IS NOT NULL) OR (strike_mode <> 'FIXED' AND strike_reset_schedule_id IS NOT NULL)", name="ck_option_terms_dynamic_schedule"),
    CheckConstraint("strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL')", name="ck_option_terms_strike_basis"),
    CheckConstraint("strike_reference_initial_fixing_id IS NULL OR strike_basis = 'PERCENT_OF_INITIAL'", name="ck_option_terms_initial_fixing_basis"),
    CheckConstraint("strike_value IS NULL OR strike_basis IN ('INDEX_POINTS', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL') OR strike_currency_id IS NOT NULL", name="ck_option_terms_strike_currency"),
    CheckConstraint("settlement_method NOT IN ('CASH', 'CASH_OR_PHYSICAL') OR settlement_currency_id IS NOT NULL", name="ck_option_terms_cash_currency"),
    CheckConstraint("exercise_style <> 'BERMUDAN' OR exercise_schedule_id IS NOT NULL", name="ck_option_terms_bermudan_schedule"),
    schema="secm",
)

option_strike_reset_rule = Table(
    "option_strike_reset_rule", metadata,
    Column("option_strike_reset_rule_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one scheduled strike-determination rule."),
    Column("option_terms_id", UUID_V7, ForeignKey("secm.option_terms.option_terms_id"), nullable=False, comment="Option-terms version whose contractual reset process contains this rule."),
    Column("schedule_event_id", UUID_V7, ForeignKey("secm.schedule_event.schedule_event_id"), nullable=False, comment="Scheduled event at which the rule determines or resets the option strike."),
    Column("determination_method", String(30), nullable=False, comment="Strike determination method: FIXED, SPOT_AT_RESET, FORWARD_AT_RESET, PREVIOUS_FIXING, or FORMULA."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Underlying or reference node used by the determination method when the reset is not a standalone fixed value."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=True, comment="Market-data series used to resolve a market-derived strike when applicable."),
    Column("strike_basis", String(30), nullable=False, server_default=text("'ABSOLUTE'"), comment="Meaning of the fixed or resolved strike value: ABSOLUTE, INDEX_POINTS, FX_RATE, PERCENT_OF_SPOT, or PERCENT_OF_INITIAL."),
    Column("fixed_strike_value", Numeric(30, 12), nullable=True, comment="Pre-specified strike for a FIXED reset rule; null when the value is determined from a fixing or formula."),
    Column("strike_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of a monetary fixed or resolved strike when required by the strike basis."),
    Column("floor_value", Numeric(30, 12), nullable=True, comment="Optional minimum strike allowed after this reset rule is applied."),
    Column("cap_value", Numeric(30, 12), nullable=True, comment="Optional maximum strike allowed after this reset rule is applied."),
    UniqueConstraint("option_terms_id", "schedule_event_id", name="uq_option_strike_reset_rule_event"),
    CheckConstraint("determination_method IN ('FIXED', 'SPOT_AT_RESET', 'FORWARD_AT_RESET', 'PREVIOUS_FIXING', 'FORMULA')", name="ck_option_strike_reset_method"),
    CheckConstraint("strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL')", name="ck_option_strike_reset_basis"),
    CheckConstraint("determination_method <> 'FIXED' OR fixed_strike_value IS NOT NULL", name="ck_option_strike_reset_fixed_value"),
    CheckConstraint("floor_value IS NULL OR cap_value IS NULL OR cap_value >= floor_value", name="ck_option_strike_reset_bounds"),
    schema="secm",
)

option_strike_fixing = Table(
    "option_strike_fixing", metadata,
    Column("option_strike_fixing_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one resolved strike fixing."),
    Column("option_strike_reset_rule_id", UUID_V7, ForeignKey("secm.option_strike_reset_rule.option_strike_reset_rule_id"), nullable=False, comment="Reset rule whose scheduled strike value was resolved."),
    Column("fixing_date", Date, nullable=False, comment="Business date on which the contractual strike was determined."),
    Column("fixing_observed_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the source observation used for the fixing was observed."),
    Column("resolved_strike_value", Numeric(30, 12), nullable=False, comment="Strike value resolved for the scheduled event, expressed using the reset rule's strike basis."),
    Column("market_data_observation_id", UUID_V7, ForeignKey("md.market_data_observation.market_data_observation_id"), nullable=True, comment="Source market-data observation used to resolve this strike when applicable."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=True, comment="Resolution snapshot proving the entitled market-data inputs used for this fixing."),
    Column("status", String(30), nullable=False, server_default=text("'ACCEPTED'"), comment="Fixing lifecycle state: ACCEPTED, SUPERSEDED, or REJECTED."),
    Column("supersedes_fixing_id", UUID_V7, ForeignKey("secm.option_strike_fixing.option_strike_fixing_id"), nullable=True, comment="Prior fixing superseded by this corrected fixing, without mutating the original fact."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem recorded the fixing."),
    CheckConstraint("resolved_strike_value > 0", name="ck_option_strike_fixing_positive"),
    CheckConstraint("status IN ('ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_option_strike_fixing_status"),
    schema="secm",
)

fx_forward_terms = Table(
    "fx_forward_terms", metadata,
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), primary_key=True, comment="Economic FX-forward instrument governed by these contractual terms."),
    Column("base_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Base currency delivered, received, or quoted first under the stated convention."),
    Column("quote_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Quote currency delivered, received, or quoted second under the stated convention."),
    Column("quote_convention", String(40), nullable=False, comment="Immutable convention such as QUOTE_PER_BASE used to interpret the agreed forward rate."),
    Column("agreed_forward_rate", Numeric(30, 12), nullable=False, comment="Contractual agreed forward exchange rate in the declared quote convention."),
    Column("settlement_type", String(30), nullable=False, comment="Settlement type such as DELIVERABLE, NDF, or CASH."),
    Column("fixing_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which an NDF or cash settlement amount is calculated when applicable."), schema="secm",
)

swap_terms = Table(
    "swap_terms", metadata,
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), primary_key=True, comment="Economic swap contract governed by its leg terms."),
    Column("swap_type", String(50), nullable=False, comment="Swap category such as TOTAL_RETURN, INTEREST_RATE, CROSS_CURRENCY, INFLATION, CREDIT, or COMMODITY."),
    CheckConstraint("swap_type IN ('TOTAL_RETURN', 'INTEREST_RATE', 'CROSS_CURRENCY', 'INFLATION', 'CREDIT', 'COMMODITY')", name="ck_swap_terms_type"),
    schema="secm",
)

swap_leg = Table(
    "swap_leg", metadata,
    Column("swap_leg_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one contractual leg of a swap."),
    Column("swap_instrument_node_id", UUID_V7, ForeignKey("secm.swap_terms.instrument_node_id"), nullable=False, comment="Swap contract owning the leg."),
    Column("leg_number", Integer, nullable=False, comment="Deterministic ordinal of the leg within its swap."),
    Column("leg_role", String(40), nullable=False, comment="Economic role such as PERFORMANCE, FUNDING, COUPON, PROTECTION, or FEE."),
    Column("pay_receive", String(10), nullable=False, comment="Direction of the leg from the swap holder perspective: PAY or RECEIVE."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Exact reference instrument, listing, index, rate, or basket measured by the leg."),
    Column("return_profile_id", UUID_V7, ForeignKey("secm.return_profile.return_profile_id"), nullable=True, comment="Generic performance-return profile contractually applied by the leg when its reference is performance-based."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Leg payment or notional currency when applicable."),
    Column("spread", Numeric(20, 8), nullable=True, comment="Contractual spread over the leg's reference rate or performance where applicable, stored as a decimal rate: 0.015 means 1.50% or 150 bps."),
    Column("schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Reset, fixing, observation, or payment schedule used by the leg."),
    UniqueConstraint("swap_instrument_node_id", "leg_number", name="uq_swap_leg_number"),
    CheckConstraint("leg_number > 0", name="ck_swap_leg_number"),
    CheckConstraint("leg_role IN ('PERFORMANCE', 'FUNDING', 'COUPON', 'PROTECTION', 'FEE')", name="ck_swap_leg_role"),
    CheckConstraint("pay_receive IN ('PAY', 'RECEIVE')", name="ck_swap_leg_pay_receive"),
    CheckConstraint("(leg_role <> 'PERFORMANCE' OR (reference_node_id IS NOT NULL AND return_profile_id IS NOT NULL)) AND (leg_role <> 'FUNDING' OR (reference_node_id IS NOT NULL AND currency_id IS NOT NULL))", name="ck_swap_leg_role_requirements"),
    schema="secm",
)

structured_product_terms = Table(
    "structured_product_terms", metadata,
    Column("structured_product_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one version of the contractual structured-product terms graph."),
    Column("instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Stable parent structured-product economic instrument whose terms are versioned."),
    Column("version_no", Integer, nullable=False, server_default=text("1"), comment="Positive monotonic version number for the parent structured-product terms."),
    Column("effective_from", Date, nullable=False, comment="First date on which this structured-product terms version is contractually effective."),
    Column("effective_to", Date, nullable=True, comment="Last date on which this structured-product terms version is contractually effective."),
    Column("is_current", Boolean, nullable=False, server_default=text("true"), comment="Whether this is the current operational terms version for the parent instrument."),
    Column("supersedes_structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=True, comment="Prior terms version replaced by this amendment, when the contract graph was superseded."),
    Column("first_autocall_observation_date", Date, nullable=True, comment="Earliest scheduled date on which an early parent autocall/redemption test is permitted; earlier coupon observations may still occur."),
    Column("issue_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency of the structured-product issuance and principal terms."),
    Column("notional_amount", Numeric(30, 12), nullable=True, comment="Contractual issue notional or denomination when applicable."),
    Column("redemption_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which redemption is contractually paid when distinct from issue currency."),
    Column("default_underlying_scope", String(30), nullable=False, server_default=text("'SINGLE'"), comment="Default underlying aggregation for product conditions: SINGLE, BEST_OF, WORST_OF, BASKET, or EACH_UNDERLYING."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Terms completion status such as DRAFT, VALIDATED, ACTIVE, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this complete terms version when available."),
    UniqueConstraint("instrument_node_id", "version_no", name="uq_structured_product_terms_version"),
    CheckConstraint("version_no > 0", name="ck_structured_product_terms_version_no"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_structured_product_terms_valid_period"),
    CheckConstraint("default_underlying_scope IN ('SINGLE', 'BEST_OF', 'WORST_OF', 'BASKET', 'EACH_UNDERLYING')", name="ck_structured_product_terms_underlying_scope"),
    schema="secm",
)

structured_product_initial_fixing = Table(
    "structured_product_initial_fixing",
    metadata,
    Column("structured_product_initial_fixing_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one recorded initial fixing used by a structured-product terms version."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False, comment="Structured-product terms version for which the initial fixing is contractually relevant."),
    Column("underlying_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Exact underlying reference node whose initial level was fixed."),
    Column("fixing_date", Date, nullable=False, comment="Business date on which the initial underlying fixing applies."),
    Column("fixing_value", Numeric(30, 12), nullable=False, comment="Initial underlying value used as the contractual reference level."),
    Column("fixing_basis", String(40), nullable=False, comment="Unit and meaning of fixing_value: LEVEL, INDEX_POINTS, FX_RATE, or PERCENT_OF_INITIAL."),
    Column("fixing_source", String(30), nullable=False, comment="Provenance class of the fixing: MANUAL, MARKET_DATA, PROVIDER, or DERIVED."),
    Column("market_data_observation_id", UUID_V7, ForeignKey("md.market_data_observation.market_data_observation_id"), nullable=True, comment="Immutable market-data observation supporting the fixing when the source is market data."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=True, comment="Resolution snapshot proving the entitled market-data inputs used for the fixing."),
    Column("source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=True, comment="Source system that supplied or recorded the fixing when an external system is involved."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained raw payload evidencing the fixing when available."),
    Column("status", String(30), nullable=False, server_default=text("'ACCEPTED'"), comment="Fixing lifecycle state: ACCEPTED, SUPERSEDED, or REJECTED."),
    Column("supersedes_fixing_id", UUID_V7, ForeignKey("secm.structured_product_initial_fixing.structured_product_initial_fixing_id"), nullable=True, comment="Prior fixing superseded by this corrected value without mutating the original record."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem recorded this fixing record."),
    UniqueConstraint("structured_product_terms_id", "underlying_reference_node_id", "fixing_date", "fixing_source", name="uq_structured_product_initial_fixing_record"),
    CheckConstraint("fixing_value > 0", name="ck_structured_product_initial_fixing_positive"),
    CheckConstraint("fixing_basis IN ('LEVEL', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_INITIAL')", name="ck_structured_product_initial_fixing_basis"),
    CheckConstraint("fixing_source IN ('MANUAL', 'MARKET_DATA', 'PROVIDER', 'DERIVED')", name="ck_structured_product_initial_fixing_source"),
    CheckConstraint("status IN ('ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_structured_product_initial_fixing_status"),
    schema="secm",
)

structured_product_condition_group = Table(
    "structured_product_condition_group",
    metadata,
    Column("condition_group_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one Boolean structured-product condition evaluated as a unit."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False, comment="Structured-product terms version owning this Boolean condition group."),
    Column("group_code", String(100), nullable=False, comment="Stable product-local business code for the contractual condition group."),
    Column("observation_style", String(30), nullable=False, comment="Observation convention: DISCRETE, CONTINUOUS, or FINAL_ONLY."),
    Column("schedule_event_id", UUID_V7, ForeignKey("secm.schedule_event.schedule_event_id"), nullable=True, comment="Exact scheduled observation event; required for DISCRETE and FINAL_ONLY groups and absent for CONTINUOUS groups."),
    Column("logical_operator", String(20), nullable=False, comment="How independent Boolean members combine: ALL, ANY, or NONE; NONE denotes an unconditional gate or one aggregate underlying predicate evaluated after MIN/MAX reduction."),
    Column("underlying_aggregation", String(20), nullable=False, server_default=text("'SINGLE'"), comment="How multiple underlying measurements reduce before the predicate: SINGLE, MIN for worst-of, MAX for best-of, or NONE for an unconditional gate."),
    Column("underlying_scope", String(30), nullable=False, server_default=text("'SINGLE'"), comment="How the group evaluates its underlying members: SINGLE, BEST_OF, WORST_OF, BASKET, or EACH_UNDERLYING."),
    Column("evaluation_sequence", Integer, nullable=False, server_default=text("1"), comment="Deterministic group evaluation order for the parent and observation context; lower values are evaluated first."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this contractual condition group."),
    UniqueConstraint("structured_product_terms_id", "group_code", name="uq_sp_condition_group_code"),
    UniqueConstraint("structured_product_terms_id", "schedule_event_id", "evaluation_sequence", name="uq_sp_condition_group_event_sequence"),
    CheckConstraint("observation_style IN ('DISCRETE', 'CONTINUOUS', 'FINAL_ONLY')", name="ck_sp_condition_group_observation_style"),
    CheckConstraint("logical_operator IN ('ALL', 'ANY', 'NONE')", name="ck_sp_condition_group_operator"),
    CheckConstraint("underlying_aggregation IN ('SINGLE', 'MIN', 'MAX', 'NONE')", name="ck_sp_condition_group_underlying_aggregation"),
    CheckConstraint("underlying_scope IN ('SINGLE', 'BEST_OF', 'WORST_OF', 'BASKET', 'EACH_UNDERLYING')", name="ck_sp_condition_group_underlying_scope"),
    CheckConstraint("(observation_style IN ('DISCRETE', 'FINAL_ONLY') AND schedule_event_id IS NOT NULL) OR (observation_style = 'CONTINUOUS' AND schedule_event_id IS NULL)", name="ck_sp_condition_group_observation"),
    CheckConstraint("evaluation_sequence > 0", name="ck_sp_condition_group_evaluation_sequence"),
    schema="secm",
)

structured_product_coupon_programme = Table(
    "structured_product_coupon_programme", metadata,
    Column("coupon_programme_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one coupon programme within a terms version."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False, comment="Structured-product terms version owning this coupon programme."),
    Column("programme_code", String(100), nullable=False, comment="Stable terms-local code identifying a coupon programme such as MAIN_COUPON or MEMORY_COUPON."),
    Column("payment_mode", String(30), nullable=False, comment="Coupon payment timing mode: PERIODIC, ON_AUTOCALL, or ON_MATURITY."),
    Column("memory_mode", String(40), nullable=False, comment="Coupon memory behaviour: NONE, CONDITIONAL_CATCH_UP, or ACCUMULATE_TO_REDEMPTION."),
    Column("coupon_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency in which coupon amounts are paid; null when inherited from the parent terms."),
    Column("default_coupon_rate", Numeric(30, 12), nullable=True, comment="Default coupon rate per period, expressed in percentage points so 5 means 5%."),
    Column("default_coupon_amount", Numeric(30, 12), nullable=True, comment="Default absolute coupon amount per applicable unit or notional, in coupon_currency_id."),
    Column("schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Default observation/payment schedule for the programme; periods may override it through their events."),
    Column("eligibility_condition_group_id", UUID_V7, ForeignKey("secm.structured_product_condition_group.condition_group_id"), nullable=True, comment="Optional default condition group governing coupon eligibility when a period does not override it."),
    Column("final_payment_treatment", String(40), nullable=True, comment="Treatment of accrued coupon at final redemption, such as PAY_SEPARATELY, INCLUDE_IN_REDEMPTION, or FORFEIT; NULL when coupon memory is NONE."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing the coupon programme when available."),
    UniqueConstraint("structured_product_terms_id", "programme_code", name="uq_sp_coupon_programme_code"),
    CheckConstraint("payment_mode IN ('PERIODIC', 'ON_AUTOCALL', 'ON_MATURITY')", name="ck_sp_coupon_programme_payment_mode"),
    CheckConstraint("memory_mode IN ('NONE', 'CONDITIONAL_CATCH_UP', 'ACCUMULATE_TO_REDEMPTION')", name="ck_sp_coupon_programme_memory_mode"),
    CheckConstraint("final_payment_treatment IS NULL OR final_payment_treatment IN ('PAY_SEPARATELY', 'INCLUDE_IN_REDEMPTION', 'FORFEIT')", name="ck_sp_coupon_programme_final_payment_treatment"),
    CheckConstraint("default_coupon_rate IS NULL OR default_coupon_rate >= 0", name="ck_sp_coupon_programme_rate"),
    CheckConstraint("default_coupon_amount IS NULL OR default_coupon_amount >= 0", name="ck_sp_coupon_programme_amount"),
    schema="secm",
)

structured_product_coupon_period = Table(
    "structured_product_coupon_period", metadata,
    Column("coupon_period_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one dated coupon period."),
    Column("coupon_programme_id", UUID_V7, ForeignKey("secm.structured_product_coupon_programme.coupon_programme_id"), nullable=False, comment="Coupon programme owning this period."),
    Column("period_sequence", Integer, nullable=False, comment="Positive chronological sequence of the period within its coupon programme."),
    Column("observation_event_id", UUID_V7, ForeignKey("secm.schedule_event.schedule_event_id"), nullable=False, comment="Scheduled event at which this period's coupon eligibility is observed."),
    Column("payment_date", Date, nullable=True, comment="Contractual coupon payment date when distinct from the observation event payment date."),
    Column("eligibility_condition_group_id", UUID_V7, ForeignKey("secm.structured_product_condition_group.condition_group_id"), nullable=True, comment="Optional condition group that must be satisfied for this period's coupon to be payable."),
    Column("coupon_rate", Numeric(30, 12), nullable=True, comment="Period-specific coupon rate in percentage points so 5 means 5%; overrides the programme default when supplied."),
    Column("coupon_amount", Numeric(30, 12), nullable=True, comment="Period-specific absolute coupon amount; overrides the programme default when supplied."),
    Column("memory_eligible", Boolean, nullable=False, server_default=text("true"), comment="Whether a missed eligible coupon can participate in the programme's memory behaviour."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this coupon period when available."),
    UniqueConstraint("coupon_programme_id", "period_sequence", name="uq_sp_coupon_period_sequence"),
    CheckConstraint("period_sequence > 0", name="ck_sp_coupon_period_sequence"),
    CheckConstraint("coupon_rate IS NULL OR coupon_rate >= 0", name="ck_sp_coupon_period_rate"),
    CheckConstraint("coupon_amount IS NULL OR coupon_amount >= 0", name="ck_sp_coupon_period_amount"),
    schema="secm",
)

structured_product_range_accrual_terms = Table(
    "structured_product_range_accrual_terms", metadata,
    Column("range_accrual_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the range-accrual-specific terms attached to one structured-product terms version."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False, comment="Structured-product terms version owning this range-accrual convention."),
    Column("observation_frequency", String(20), nullable=False, comment="Contractual range observation cadence: DAILY, WEEKLY, or MONTHLY."),
    Column("accrual_basis", String(30), nullable=False, comment="Denominator used for the accrual fraction: OBSERVATION_COUNT or CALENDAR_DAYS."),
    Column("non_business_day_rule", String(40), nullable=False, comment="Treatment of non-business dates in the observation series: BUSINESS_DAYS_ONLY, CARRY_FORWARD_PREVIOUS, or CALENDAR_DAYS."),
    Column("lower_level", Numeric(30, 12), nullable=False, comment="Inclusive lower range boundary in percentage points of the contractual initial fixing; 70 means 70% of initial."),
    Column("upper_level", Numeric(30, 12), nullable=False, comment="Inclusive upper range boundary in percentage points of the contractual initial fixing; 130 means 130% of initial."),
    Column("coupon_rate_per_annum", Numeric(30, 12), nullable=False, comment="Annualised contractual coupon rate in percentage points; the lifecycle service multiplies it by the accrued observation fraction."),
    Column("observation_schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Coupon-period observation anchor schedule used by the onboarding slice; a lifecycle service may later materialise a separate detailed fixing schedule."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing the range-accrual convention when available."),
    UniqueConstraint("structured_product_terms_id", name="uq_sp_range_accrual_terms_version"),
    CheckConstraint("observation_frequency IN ('DAILY', 'WEEKLY', 'MONTHLY')", name="ck_sp_range_accrual_observation_frequency"),
    CheckConstraint("accrual_basis IN ('OBSERVATION_COUNT', 'CALENDAR_DAYS')", name="ck_sp_range_accrual_basis"),
    CheckConstraint("non_business_day_rule IN ('BUSINESS_DAYS_ONLY', 'CARRY_FORWARD_PREVIOUS', 'CALENDAR_DAYS')", name="ck_sp_range_accrual_non_business_day_rule"),
    CheckConstraint("lower_level >= 0 AND upper_level > lower_level", name="ck_sp_range_accrual_range_bounds"),
    CheckConstraint("coupon_rate_per_annum >= 0", name="ck_sp_range_accrual_coupon_rate"),
    schema="secm",
)

structured_product_supertracker_terms = Table(
    "structured_product_supertracker_terms", metadata,
    Column("supertracker_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the supertracker-specific terms attached to one structured-product terms version."),
    Column("structured_product_terms_id", UUID_V7, ForeignKey("secm.structured_product_terms.structured_product_terms_id"), nullable=False, comment="Structured-product terms version owning this supertracker payoff convention."),
    Column("participation_rate", Numeric(30, 12), nullable=False, comment="Positive upside participation multiplier stored as a decimal; 1.35 means 135% leveraged exposure."),
    Column("cap_enabled", Boolean, nullable=False, server_default=text("false"), comment="Whether the leveraged upside is capped by a short call component."),
    Column("cap_return", Numeric(30, 12), nullable=True, comment="Maximum underlying return in percentage points before the upside cap call flattens the payoff; 25 means a 25% underlying return cap."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing the supertracker convention when available."),
    UniqueConstraint("structured_product_terms_id", name="uq_sp_supertracker_terms_version"),
    CheckConstraint("participation_rate > 0", name="ck_sp_supertracker_participation_rate"),
    CheckConstraint("(cap_enabled = false AND cap_return IS NULL) OR (cap_enabled = true AND cap_return > 0)", name="ck_sp_supertracker_cap_terms"),
    schema="secm",
)

structured_product_component_terms = Table(
    "structured_product_component_terms", metadata,
    Column("structured_product_component_terms_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for payoff terms attached to one structured-product composition occurrence."),
    Column("instrument_composition_id", UUID_V7, ForeignKey("secm.instrument_composition.instrument_composition_id"), nullable=False, comment="Exact parent-component composition occurrence to which these payoff terms apply."),
    Column("component_kind", String(40), nullable=False, comment="Component role such as DIGITAL, VANILLA_OPTION, BARRIER, COUPON, PRINCIPAL_REDEMPTION, CAP, FLOOR, or CASHFLOW."),
    Column("payoff_style", String(40), nullable=False, comment="Payoff representation: FIXED_AMOUNT, RATE_OF_NOTIONAL, OPTION_PAYOFF, UNDERLYING_RETURN, or PRINCIPAL_REDEMPTION."),
    Column("payout_amount", Numeric(30, 12), nullable=True, comment="Absolute payout amount when the component pays a fixed cash amount."),
    Column("payout_rate", Numeric(30, 12), nullable=True, comment="Payout rate in percentage points when the component pays a percentage; 5 means 5%."),
    Column("payout_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the component payout when it is a monetary amount."),
    Column("payout_basis", String(40), nullable=True, comment="Basis for payout_amount or payout_rate: PER_UNIT, PCT_OF_NOTIONAL, PCT_OF_PAR, or ABSOLUTE."),
    Column("payment_timing", String(30), nullable=True, comment="When the component pays: ON_OBSERVATION, ON_TRIGGER, ON_AUTOCALL, or ON_MATURITY."),
    Column("schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Optional schedule governing this component's payment or observation timing."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing these component payoff terms when available."),
    UniqueConstraint("instrument_composition_id", name="uq_sp_component_terms_composition"),
    CheckConstraint("component_kind IN ('DIGITAL', 'VANILLA_OPTION', 'BARRIER', 'COUPON', 'PRINCIPAL_REDEMPTION', 'CAP', 'FLOOR', 'CASHFLOW', 'OTHER')", name="ck_sp_component_terms_kind"),
    CheckConstraint("payoff_style IN ('FIXED_AMOUNT', 'RATE_OF_NOTIONAL', 'OPTION_PAYOFF', 'UNDERLYING_RETURN', 'PRINCIPAL_REDEMPTION')", name="ck_sp_component_terms_payoff_style"),
    CheckConstraint("payout_amount IS NULL OR payout_amount >= 0", name="ck_sp_component_terms_payout_amount"),
    CheckConstraint("payout_rate IS NULL OR payout_rate >= 0", name="ck_sp_component_terms_payout_rate"),
    CheckConstraint("(payout_amount IS NULL OR payout_rate IS NULL) OR (payout_amount >= 0 AND payout_rate >= 0)", name="ck_sp_component_terms_payout_values"),
    CheckConstraint("payout_basis IS NULL OR payout_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'ABSOLUTE')", name="ck_sp_component_terms_payout_basis"),
    CheckConstraint("payment_timing IS NULL OR payment_timing IN ('ON_OBSERVATION', 'ON_TRIGGER', 'ON_AUTOCALL', 'ON_MATURITY')", name="ck_sp_component_terms_payment_timing"),
    schema="secm",
)

barrier_rule = Table(
    "barrier_rule", metadata,
    Column("barrier_rule_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one atomic, underlying-specific contractual predicate."),
    Column("condition_group_id", UUID_V7, ForeignKey("secm.structured_product_condition_group.condition_group_id"), nullable=False, comment="Boolean condition group that aggregates this atomic predicate."),
    Column("owner_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Component or instrument that supplies the contractual context for this atomic predicate."),
    Column("underlying_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Specific underlying reference node tested by this atomic predicate."),
    Column("condition_sequence", Integer, nullable=False, comment="Deterministic member sequence within the owning condition group."),
    Column("comparison_operator", String(20), nullable=False, comment="Comparison operator: GE, GT, LE, LT, BETWEEN, or OUTSIDE."),
    Column("level_reference_type", String(40), nullable=False, comment="Level basis such as PCT_OF_INITIAL, PCT_OF_STRIKE, ABSOLUTE_LEVEL, or PCT_OF_PAR."),
    Column("lower_level_value", Numeric(30, 12), nullable=True, comment="Required threshold, or lower bound for BETWEEN and OUTSIDE, expressed using level_reference_type."),
    Column("upper_level_value", Numeric(30, 12), nullable=True, comment="Upper bound for BETWEEN and OUTSIDE, expressed using level_reference_type."),
    Column("lower_bound_inclusive", Boolean, nullable=False, server_default=text("true"), comment="Whether a lower range bound is inclusive; scalar GE/LE and GT/LT operators remain authoritative for single-bound predicates."),
    Column("upper_bound_inclusive", Boolean, nullable=False, server_default=text("true"), comment="Whether an upper range bound is inclusive; a consolation range uses false to exclude the final payoff barrier."),
    Column("underlying_measure", String(40), nullable=False, comment="Measured metric such as OFFICIAL_CLOSE, FINAL_PERFORMANCE, INTRADAY_LOW, or AVERAGE_PERFORMANCE."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this atomic predicate."),
    UniqueConstraint("condition_group_id", "condition_sequence", name="uq_barrier_rule_group_sequence"),
    CheckConstraint("condition_sequence > 0", name="ck_barrier_rule_sequence"),
    CheckConstraint("comparison_operator IN ('GE', 'GT', 'LE', 'LT', 'BETWEEN', 'OUTSIDE')", name="ck_barrier_rule_comparison"),
    CheckConstraint("(comparison_operator IN ('GE', 'GT', 'LE', 'LT') AND lower_level_value IS NOT NULL AND upper_level_value IS NULL) OR (comparison_operator IN ('BETWEEN', 'OUTSIDE') AND lower_level_value IS NOT NULL AND upper_level_value IS NOT NULL AND upper_level_value >= lower_level_value)", name="ck_barrier_rule_levels"),
    CheckConstraint("(comparison_operator IN ('BETWEEN', 'OUTSIDE')) OR ((comparison_operator IN ('GE', 'LE') AND lower_bound_inclusive = true) OR (comparison_operator IN ('GT', 'LT') AND lower_bound_inclusive = false))", name="ck_barrier_rule_bound_inclusivity"),
    schema="secm",
)

condition_group_action = Table(
    "condition_group_action", metadata,
    Column("condition_group_action_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one ordered consequence of a satisfied condition group."),
    Column("condition_group_id", UUID_V7, ForeignKey("secm.structured_product_condition_group.condition_group_id"), nullable=False, comment="Satisfied Boolean condition group that causes this action."),
    Column("action_type", String(50), nullable=False, comment="Consequence: PAY_COMPONENT, PAY_CONSOLATION, REDEEM_PARENT, TERMINATE_PARENT, CANCEL_FUTURE_COMPONENTS, or ACTIVATE_CAPITAL_PROTECTION."),
    Column("target_scope", String(20), nullable=False, comment="Contractual target scope: COMPONENT or PARENT."),
    Column("target_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Specific component or parent reference node affected by this action; aggregate parent actions resolve selected child outcomes through their condition group."),
    Column("target_composition_id", UUID_V7, ForeignKey("secm.instrument_composition.instrument_composition_id"), nullable=True, comment="Exact component composition occurrence affected by a COMPONENT action; null for PARENT actions, including aggregate best-/worst-of KIP and coupon actions."),
    Column("payment_amount", Numeric(30, 12), nullable=True, comment="Absolute amount paid by this action when the action itself carries a fixed payout."),
    Column("payment_rate", Numeric(30, 12), nullable=True, comment="Percentage-point rate paid by this action when the payout is rate-based; 5 means 5%."),
    Column("payment_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the action payout when it is monetary."),
    Column("payment_basis", String(40), nullable=True, comment="Basis for a payment amount or rate: PER_UNIT, PCT_OF_NOTIONAL, PCT_OF_PAR, PCT_OF_MAX_PAYOFF, or ABSOLUTE."),
    Column("payment_timing", String(30), nullable=True, comment="Payment timing for the action: ON_OBSERVATION, ON_TRIGGER, ON_AUTOCALL, or ON_MATURITY."),
    Column("payment_schedule_id", UUID_V7, ForeignKey("secm.schedule.schedule_id"), nullable=True, comment="Optional schedule governing when an action payout is settled."),
    Column("payment_date", Date, nullable=True, comment="Action-specific settlement/payment date overriding the schedule event default when an outcome row is manually adjusted."),
    Column("payout_multiplicity", String(30), nullable=False, server_default=text("'PER_COMPONENT'"), comment="How many payouts the action may create: ONCE_PER_PARENT for one aggregate parent outcome, PER_UNDERLYING for one outcome per underlying, or PER_COMPONENT for each explicit composition action."),
    Column("execution_sequence", Integer, nullable=False, server_default=text("1"), comment="Deterministic sequence in which satisfied-group actions execute; lower values execute first."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this group action."),
    UniqueConstraint("condition_group_id", "execution_sequence", name="uq_condition_group_action_sequence"),
    CheckConstraint("action_type IN ('PAY_COMPONENT', 'PAY_CONSOLATION', 'REDEEM_PARENT', 'TERMINATE_PARENT', 'CANCEL_FUTURE_COMPONENTS', 'ACTIVATE_CAPITAL_PROTECTION')", name="ck_condition_group_action_type"),
    CheckConstraint("target_scope IN ('COMPONENT', 'PARENT')", name="ck_condition_group_action_target_scope"),
    CheckConstraint("(target_scope = 'COMPONENT' AND target_composition_id IS NOT NULL) OR (target_scope = 'PARENT' AND target_composition_id IS NULL)", name="ck_condition_group_action_target_composition"),
    CheckConstraint("payment_amount IS NULL OR payment_amount >= 0", name="ck_condition_group_action_payment_amount"),
    CheckConstraint("payment_rate IS NULL OR payment_rate >= 0", name="ck_condition_group_action_payment_rate"),
    CheckConstraint("(payment_amount IS NULL OR payment_rate IS NULL) OR (payment_amount >= 0 AND payment_rate >= 0)", name="ck_condition_group_action_payment_values"),
    CheckConstraint("payment_basis IS NULL OR payment_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'PCT_OF_MAX_PAYOFF', 'ABSOLUTE')", name="ck_condition_group_action_payment_basis"),
    CheckConstraint("payment_timing IS NULL OR payment_timing IN ('ON_OBSERVATION', 'ON_TRIGGER', 'ON_AUTOCALL', 'ON_MATURITY')", name="ck_condition_group_action_payment_timing"),
    CheckConstraint("payout_multiplicity IN ('ONCE_PER_PARENT', 'PER_UNDERLYING', 'PER_COMPONENT')", name="ck_condition_group_action_payout_multiplicity"),
    CheckConstraint("execution_sequence > 0", name="ck_condition_group_action_execution_sequence"),
    schema="secm",
)

reference_constituent_snapshot = Table(
    "reference_constituent_snapshot", metadata,
    Column("reference_constituent_snapshot_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a dated constituent snapshot of a reference portfolio, basket, ETF, AMC, or index."),
    Column("owner_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Reference portfolio, ETF, index, AMC, or other object whose constituents are captured."),
    Column("snapshot_date", Date, nullable=False, comment="Business date for which the constituent snapshot is effective."),
    Column("snapshot_kind", String(40), nullable=False, comment="Constituent purpose such as ETF_PCF, REFERENCE_PORTFOLIO, CUSTOM_BASKET, QIS_INDEX, or CREDIT_INDEX."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload providing the constituent snapshot."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Snapshot lifecycle status such as ACTIVE, SUPERSEDED, or REJECTED."),
    UniqueConstraint("owner_reference_node_id", "snapshot_date", "snapshot_kind", name="uq_reference_constituent_snapshot_business_key"), schema="secm",
)

reference_constituent_snapshot_item = Table(
    "reference_constituent_snapshot_item", metadata,
    Column("reference_constituent_snapshot_item_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one constituent in a dated reference snapshot."),
    Column("reference_constituent_snapshot_id", UUID_V7, ForeignKey("secm.reference_constituent_snapshot.reference_constituent_snapshot_id"), nullable=False, comment="Dated constituent snapshot containing the item."),
    Column("constituent_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, cash currency, or reference node included as a constituent."),
    Column("weight", Numeric(30, 12), nullable=True, comment="Portfolio or index weight when supplied by the source."),
    Column("quantity", Numeric(30, 12), nullable=True, comment="Constituent quantity when supplied by the source."),
    Column("cash_component", Numeric(30, 12), nullable=True, comment="Cash component attributable to this item when applicable."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the quantity or cash component when applicable."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Stable display and source ordering for the constituent item."),
    UniqueConstraint("reference_constituent_snapshot_id", "constituent_reference_node_id", "sequence_no", name="uq_reference_constituent_snapshot_item_business_key"), schema="secm",
)

corporate_action = Table(
    "corporate_action", metadata,
    Column("corporate_action_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a versioned canonical corporate-action event."),
    Column("affected_instrument_node_id", UUID_V7, ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Economic instrument affected by the corporate action."),
    Column("event_type", String(50), nullable=False, comment="Controlled event type such as CASH_DIVIDEND, STOCK_SPLIT, BONUS_ISSUE, SPIN_OFF, MERGER, or SECURITY_REPLACEMENT."),
    Column("status", String(30), nullable=False, comment="Event lifecycle status such as ANNOUNCED, CONFIRMED, CANCELLED, or COMPLETED."),
    Column("external_event_reference", String(500), nullable=True, comment="Provider, exchange, custodian, or issuer event reference."),
    Column("sequence_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing event version sequence for announcement changes or corrections."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing this corporate-action version."),
    Column("announced_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the event was announced when known."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem recorded this event version."), schema="secm",
)

corporate_action_date = Table(
    "corporate_action_date", metadata,
    Column("corporate_action_date_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one business date or timestamp on a corporate action."),
    Column("corporate_action_id", UUID_V7, ForeignKey("secm.corporate_action.corporate_action_id"), nullable=False, comment="Corporate action to which the date belongs."),
    Column("date_role", String(40), nullable=False, comment="Date purpose such as EX, RECORD, PAYABLE, EFFECTIVE, or ELECTION_DEADLINE."),
    Column("date_value", Date, nullable=True, comment="Business date for the stated event role when a date is sufficient."),
    Column("timestamp_value_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp for the stated event role when time precision is required."),
    Column("timezone_name", String(100), nullable=True, comment="IANA timezone supplied by the source when interpreting a local timestamp."), schema="secm",
)

corporate_action_effect = Table(
    "corporate_action_effect", metadata,
    Column("corporate_action_effect_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one economic effect of a corporate action."),
    Column("corporate_action_id", UUID_V7, ForeignKey("secm.corporate_action.corporate_action_id"), nullable=False, comment="Corporate action producing the economic effect."),
    Column("effect_type", String(40), nullable=False, comment="Effect kind such as CASH, SECURITY, QUANTITY_CHANGE, or REPLACEMENT."),
    Column("target_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Security or reference object delivered or replacing the affected instrument when applicable."),
    Column("ratio", Numeric(30, 12), nullable=True, comment="Quantity or exchange ratio for the effect when applicable."),
    Column("cash_amount", Numeric(30, 12), nullable=True, comment="Cash amount per entitled unit when applicable."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the cash amount when applicable."),
    Column("rounding_rule", String(100), nullable=True, comment="Source or contractual rounding rule for the economic effect."), schema="secm",
)

market_data_adjustment_factor = Table(
    "market_data_adjustment_factor", metadata,
    Column("market_data_adjustment_factor_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a corporate-action factor linking raw and derived market-data histories."),
    Column("corporate_action_id", UUID_V7, ForeignKey("secm.corporate_action.corporate_action_id"), nullable=False, comment="Corporate action requiring the history adjustment factor."),
    Column("raw_market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=False, comment="Raw source market-data series to which the adjustment applies."),
    Column("derived_market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=False, comment="Derived adjusted or return series produced using the factor."),
    Column("adjustment_basis", String(40), nullable=False, comment="Adjustment basis such as SPLIT_ADJUSTED, PRICE_RETURN, GROSS_TOTAL_RETURN, or NET_TOTAL_RETURN."),
    Column("effective_date", Date, nullable=False, comment="Business date from which the adjustment factor applies."),
    Column("factor", Numeric(30, 12), nullable=False, comment="Multiplicative adjustment factor in the declared calculation methodology."),
    Column("calculation_method", String(100), nullable=False, comment="Versioned method or provider methodology used to calculate the factor."), schema="secm",
)

option_strike_adjustment = Table(
    "option_strike_adjustment", metadata,
    Column("option_strike_adjustment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one attributable contractual option-strike adjustment."),
    Column("option_terms_id", UUID_V7, ForeignKey("secm.option_terms.option_terms_id"), nullable=False, comment="Option-terms version whose contractual strike was adjusted."),
    Column("corporate_action_id", UUID_V7, ForeignKey("secm.corporate_action.corporate_action_id"), nullable=False, comment="Confirmed corporate action causing the contractual strike or deliverable adjustment."),
    Column("effective_date", Date, nullable=False, comment="Business date on which the adjustment takes effect under the corporate action."),
    Column("adjustment_kind", String(40), nullable=False, comment="Adjustment reason such as STOCK_SPLIT, REVERSE_SPLIT, BONUS_ISSUE, SPECIAL_DIVIDEND, or OTHER."),
    Column("pre_adjustment_strike_value", Numeric(30, 12), nullable=False, comment="Strike value immediately before this adjustment, expressed in the option terms strike basis."),
    Column("post_adjustment_strike_value", Numeric(30, 12), nullable=False, comment="Strike value after applying the contractual corporate-action factor."),
    Column("strike_factor", Numeric(30, 12), nullable=False, comment="Positive multiplicative factor applied to the pre-adjustment strike; for example 0.5 for a two-for-one split."),
    Column("post_adjustment_fixing_value", Numeric(30, 12), nullable=True, comment="Adjusted reference fixing when the product's fixing basis also changes under the action."),
    Column("revision_no", Integer, nullable=False, server_default=text("1"), comment="Positive correction revision for the same option terms, corporate action, and effective date; incremented when a later record supersedes an earlier one."),
    Column("status", String(30), nullable=False, server_default=text("'PROPOSED'"), comment="Lifecycle state: PROPOSED, ACCEPTED, SUPERSEDED, or REJECTED."),
    Column("supersedes_adjustment_id", UUID_V7, ForeignKey("secm.option_strike_adjustment.option_strike_adjustment_id"), nullable=True, comment="Prior adjustment superseded by this corrected factor or result without mutating the original record."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained source payload evidencing the adjustment calculation or issuer notice."),
    Column("recorded_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem recorded this adjustment record."),
    UniqueConstraint("option_terms_id", "corporate_action_id", "effective_date", "revision_no", name="uq_option_strike_adjustment_revision"),
    CheckConstraint("adjustment_kind IN ('STOCK_SPLIT', 'REVERSE_SPLIT', 'BONUS_ISSUE', 'SPECIAL_DIVIDEND', 'OTHER')", name="ck_option_strike_adjustment_kind"),
    CheckConstraint("pre_adjustment_strike_value > 0 AND post_adjustment_strike_value > 0", name="ck_option_strike_adjustment_values"),
    CheckConstraint("strike_factor > 0", name="ck_option_strike_adjustment_factor"),
    CheckConstraint("post_adjustment_fixing_value IS NULL OR post_adjustment_fixing_value > 0", name="ck_option_strike_adjustment_fixing"),
    CheckConstraint("revision_no > 0", name="ck_option_strike_adjustment_revision"),
    CheckConstraint("status IN ('PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_option_strike_adjustment_status"),
    schema="secm",
)

regulatory_label = Table(
    "regulatory_label", metadata,
    Column("regulatory_label_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a governed regulatory or eligibility label definition."),
    Column("label_scheme", String(50), nullable=False, comment="Label scheme such as UCITS_ELIGIBILITY, PRIIPS, SFDR, or INTERNAL_REGULATORY."),
    Column("label_code", String(100), nullable=False, comment="Controlled label code within its scheme."),
    Column("display_name", String(250), nullable=False, comment="Human-readable regulatory label name."),
    Column("description", Text, nullable=True, comment="Definition, scope, and application guidance for the label."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status of the label definition."),
    UniqueConstraint("label_scheme", "label_code", name="uq_regulatory_label_code"), schema="secm",
)

reference_node_regulatory_label_assignment = Table(
    "reference_node_regulatory_label_assignment", metadata,
    Column("reference_node_regulatory_label_assignment_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for an effective-dated regulatory label assignment."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, fund, share class, or other reference node receiving the label."),
    Column("regulatory_label_id", UUID_V7, ForeignKey("secm.regulatory_label.regulatory_label_id"), nullable=False, comment="Governed regulatory or eligibility label assigned to the reference node."),
    Column("assessment_status", String(30), nullable=False, comment="Assessment state such as ASSERTED, VERIFIED, NOT_APPLICABLE, or REJECTED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the label assignment is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the label assignment is effective."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained evidence or assessment payload supporting the assignment."), schema="secm",
)

# Automation policies govern when an inbound source may be trusted to approve
# a canonical reference-data proposal without a human click.
reference_data_automation_policy = Table(
    "reference_data_automation_policy", metadata,
    Column("reference_data_automation_policy_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one version of a policy governing automated reference-data proposals."),
    Column("policy_code", String(100), nullable=False, comment="Stable business code for the automation policy across immutable versions."),
    Column("display_name", String(250), nullable=False, comment="Human-readable name of the automation policy version."),
    Column("source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=False, comment="Source system whose proposals may be evaluated by this policy."),
    Column("target_object_type", String(50), nullable=False, comment="Reference-data object type governed by the policy, such as EQUITY, LISTING, or IDENTIFIER_MAPPING."),
    Column("operation_type", String(30), nullable=False, comment="Permitted operation governed by the policy, such as CREATE, AMEND, or MAP."),
    Column("min_confidence", Numeric(5, 4), nullable=True, comment="Minimum normalized confidence score required for automatic approval, between zero and one."),
    Column("required_identifier_schemes", JSONB, nullable=True, comment="JSON array of identifier schemes that must be present before this policy can approve automatically."),
    Column("criteria_json", JSONB, nullable=True, comment="Versioned source-specific validation criteria evaluated by the automation service."),
    Column("auto_approve", Boolean, nullable=False, server_default=text("false"), comment="Whether a proposal satisfying this policy may receive an automated approval decision."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning a private policy; null identifies a shared canonical policy."),
    Column("valid_from", Date, nullable=False, comment="First business date on which this policy version is effective."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which this policy version is effective."),
    Column("version_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing immutable version number for the policy code."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Lifecycle status such as DRAFT, ACTIVE, RETIRED, or SUPERSEDED."),
    Column("approved_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Steward account approving this policy version for operational use."),
    Column("approved_at_utc", DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the automation policy version was approved."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the automation policy version was created."),
    UniqueConstraint("policy_code", "version_no", "tenant_id", name="uq_reference_data_automation_policy_version"),
    CheckConstraint("min_confidence IS NULL OR (min_confidence >= 0 AND min_confidence <= 1)", name="ck_reference_data_automation_policy_confidence"),
    CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_reference_data_automation_policy_valid_period"),
    CheckConstraint("version_no > 0", name="ck_reference_data_automation_policy_positive_version"),
    schema="secm",
)

reference_data_proposal = Table(
    "reference_data_proposal", metadata,
    Column("reference_data_proposal_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a proposed canonical reference-data creation or amendment."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Existing reference node to amend; null when the proposal creates a new canonical node."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant originating a private promotion or tenant-scoped proposal when applicable."),
    Column("proposal_type", String(40), nullable=False, comment="Proposal type such as CREATE, CREATE_BOND, CREATE_LISTING, AMEND, PROMOTE_PRIVATE, RETIRE, or IDENTIFIER_MAPPING."),
    Column("proposed_payload", Text, nullable=False, comment="Versioned serialized proposed facts or patch retained for review; canonical relational fields remain the approved operational truth."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Raw source payload that proposed or evidenced the change."),
    Column("source_system_id", UUID_V7, ForeignKey("ing.integration_source_system.integration_source_system_id"), nullable=True, comment="Source system that submitted the proposal, retained explicitly for automation policy evaluation."),
    Column("submission_mode", String(20), nullable=False, server_default=text("'MANUAL'"), comment="How the proposal entered the workflow: MANUAL or AUTOMATED."),
    Column("automation_policy_id", UUID_V7, ForeignKey("secm.reference_data_automation_policy.reference_data_automation_policy_id"), nullable=True, comment="Automation policy evaluated for this proposal when submission_mode is AUTOMATED."),
    Column("idempotency_key", String(500), nullable=True, comment="Source-scoped idempotency key ensuring retries do not create duplicate proposals or instruments."),
    Column("match_status", String(30), nullable=False, server_default=text("'NEW'"), comment="Result of duplicate and identity matching: NEW, EXACT_MATCH, POSSIBLE_MATCH, or CONFLICT."),
    Column("confidence_score", Numeric(5, 4), nullable=True, comment="Normalized confidence score assigned by matching or source validation, between zero and one."),
    Column("payload_schema_version", String(40), nullable=False, server_default=text("'1'"), comment="Version of the structured proposal payload contract used by the producer."),
    Column("status", String(30), nullable=False, server_default=text("'PENDING'"), comment="Workflow status such as PENDING, VALIDATED, APPROVED, REJECTED, or SUPERSEDED."),
    Column("proposed_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the proposal was recorded."),
    UniqueConstraint("source_system_id", "idempotency_key", "tenant_id", name="uq_reference_data_proposal_idempotency"),
    CheckConstraint("submission_mode IN ('MANUAL', 'AUTOMATED')", name="ck_reference_data_proposal_submission_mode"),
    CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)", name="ck_reference_data_proposal_confidence"),
    schema="secm",
)

reference_data_approval = Table(
    "reference_data_approval", metadata,
    Column("reference_data_approval_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a steward decision on a reference-data proposal."),
    Column("reference_data_proposal_id", UUID_V7, ForeignKey("secm.reference_data_proposal.reference_data_proposal_id"), nullable=False, comment="Reference-data proposal receiving the decision."),
    Column("decision", String(30), nullable=False, comment="Steward decision such as APPROVED, REJECTED, RETURNED, or SUPERSEDED."),
    Column("decided_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Internal authenticated steward or service account recording the decision."),
    Column("decision_method", String(20), nullable=False, server_default=text("'MANUAL'"), comment="How the decision was made: MANUAL by a steward or AUTOMATED under a governed policy."),
    Column("automation_policy_id", UUID_V7, ForeignKey("secm.reference_data_automation_policy.reference_data_automation_policy_id"), nullable=True, comment="Automation policy responsible for an automated decision, when decision_method is AUTOMATED."),
    Column("decision_evidence_json", JSONB, nullable=True, comment="Structured matching, validation, and policy evidence retained with the decision."),
    Column("decided_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the decision was recorded."),
    Column("reason", Text, nullable=True, comment="Decision rationale, validation evidence, or remediation request."),
    CheckConstraint("decision_method IN ('MANUAL', 'AUTOMATED')", name="ck_reference_data_approval_decision_method"),
    schema="secm",
)

valuation_policy = Table(
    "valuation_policy", metadata,
    Column("valuation_policy_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a tenant-scoped versioned valuation selection policy."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant owning the valuation policy."),
    Column("policy_code", String(100), nullable=False, comment="Tenant-unique code identifying the valuation policy."),
    Column("display_name", String(250), nullable=False, comment="Human-readable valuation policy name."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=False, comment="Named business cut used by the policy unless overridden by a rule."),
    Column("version_no", Integer, nullable=False, server_default=text("1"), comment="Monotonically increasing immutable policy version."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Policy lifecycle status such as DRAFT, ACTIVE, RETIRED, or SUPERSEDED."),
    Column("valid_from", Date, nullable=False, comment="First business date on which the policy version may be used."),
    Column("valid_to", Date, nullable=True, comment="Last business date on which the policy version may be used."),
    UniqueConstraint("tenant_id", "policy_code", "version_no", name="uq_valuation_policy_version"), schema="ten",
)

valuation_policy_rule = Table(
    "valuation_policy_rule", metadata,
    Column("valuation_policy_rule_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one ordered market-data selection rule in a valuation policy."),
    Column("valuation_policy_id", UUID_V7, ForeignKey("ten.valuation_policy.valuation_policy_id"), nullable=False, comment="Tenant valuation policy version owning the rule."),
    Column("rule_sequence", Integer, nullable=False, comment="Deterministic priority order of the selection rule within its policy."),
    Column("subject_type", String(50), nullable=True, comment="Optional target type filter such as LISTING, INSTRUMENT, INDEX, FX_PAIR, or COMMODITY."),
    Column("instrument_type_id", UUID_V7, ForeignKey("secm.instrument_type.instrument_type_id"), nullable=True, comment="Optional governed economic instrument-type filter for the rule."),
    Column("subject_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Optional exact instrument, listing, index, FX pair, or other canonical node to which this rule applies ahead of broader type rules."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=True, comment="Optional exact market-data series to which this rule applies ahead of broader subject or type rules."),
    Column("series_type", String(50), nullable=False, comment="Required market-data series type such as OFFICIAL_CLOSE, EVALUATED_PRICE, BID, ASK, or FX_SPOT."),
    Column("selection_method", String(40), nullable=False, comment="Selection method such as LAST_BEFORE_CUT, OFFICIAL, MID, APPROVED, or FALLBACK."),
    Column("pricing_date_rule", String(40), nullable=False, server_default=text("'SAME_DAY'"), comment="Controlled pricing-date selection such as SAME_DAY, PRIOR_AVAILABLE, or FIXED_LAG."),
    Column("lag_business_days", Integer, nullable=False, server_default=text("0"), comment="Non-negative business-day lag subtracted from the valuation date when pricing_date_rule is FIXED_LAG."),
    Column("market_calendar_id", UUID_V7, ForeignKey("cal.market_calendar.market_calendar_id"), nullable=True, comment="Optional governed calendar for business-day lag and staleness calculations; null only while the platform default calendar policy applies."),
    Column("max_staleness_business_days", Integer, nullable=True, comment="Maximum permitted business-day difference between requested and selected market date; null only when policy explicitly permits no fixed limit."),
    Column("missing_data_action", String(40), nullable=False, server_default=text("'FAIL'"), comment="Required policy outcome when no eligible or sufficiently current value exists, such as FAIL, WARN, or MANUAL_OVERRIDE."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=True, comment="Optional preferred or required dataset for the selection rule."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Rule lifecycle status."),
    UniqueConstraint("valuation_policy_id", "rule_sequence", name="uq_valuation_policy_rule_sequence"), schema="ten",
)

market_data_resolution_snapshot = Table(
    "market_data_resolution_snapshot", metadata,
    Column("market_data_resolution_snapshot_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for a resolved set of entitled market-data inputs."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant for whose entitlement and policy context values were resolved."),
    Column("valuation_policy_id", UUID_V7, ForeignKey("ten.valuation_policy.valuation_policy_id"), nullable=False, comment="Exact tenant valuation-policy version applied to select inputs."),
    Column("valuation_date", Date, nullable=False, comment="Business valuation date for the resolution snapshot."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=False, comment="Named valuation cut at which data eligibility was evaluated."),
    Column("market_data_as_of_utc", DateTime(timezone=True), nullable=False, comment="UTC information cut-off; observations received later are ineligible for this snapshot."),
    Column("use_purpose", String(50), nullable=False, server_default=text("'UNKNOWN'"), comment="Entitled use purpose evaluated when this immutable snapshot was created."),
    Column("resolver_version", String(100), nullable=False, comment="Version of the resolver logic used to make selections."),
    Column("status", String(30), nullable=False, server_default=text("'COMPLETED'"), comment="Snapshot status such as COMPLETED, PARTIAL, FAILED, or SUPERSEDED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which resolution completed."), schema="md",
)

market_data_resolution_snapshot_item = Table(
    "market_data_resolution_snapshot_item", metadata,
    Column("market_data_resolution_snapshot_item_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one selected value or explicit resolution exception."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=False, comment="Resolution snapshot containing the selection result."),
    Column("subject_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, index, FX pair, curve point, or other subject resolved."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=True, comment="Series selected by the resolver; null only for an explicit missing-data result."),
    Column("market_data_observation_id", UUID_V7, ForeignKey("md.market_data_observation.market_data_observation_id"), nullable=True, comment="Raw observation selected by the resolver; null for a policy override or missing-data result."),
    Column("market_data_vintage_id", UUID_V7, ForeignKey("md.market_data_vintage.market_data_vintage_id"), nullable=True, comment="Immutable source vintage selected at the historic information cut."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=True, comment="Dataset of the selected observation or override when applicable."),
    Column("acquisition_licence_id", UUID_V7, ForeignKey("md.data_licence.data_licence_id"), nullable=True, comment="Licence under which Fortem acquired the frozen observation when known."),
    Column("source_published_at_utc", DateTime(timezone=True), nullable=True, comment="Provider publication timestamp frozen from the selected observation or vintage."),
    Column("received_at_utc", DateTime(timezone=True), nullable=True, comment="Platform receipt timestamp frozen from the selected observation or vintage."),
    Column("selected_value", Numeric(30, 12), nullable=True, comment="Resolved scalar value; null only when the item records an explicit unresolved exception."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the selected value when applicable."),
    Column("pricing_date_requested", Date, nullable=True, comment="Business date requested after applying the frozen valuation policy's pricing-date rule and business-day lag."),
    Column("pricing_date_used", Date, nullable=True, comment="Actual market date of the selected observation; null for unresolved or non-market-data inputs."),
    Column("staleness_business_days", Integer, nullable=True, comment="Business-day difference between requested and used market date under the frozen rule calendar."),
    Column("staleness_status", String(40), nullable=True, comment="Recorded freshness outcome such as CURRENT, WITHIN_TOLERANCE, STALE, MISSING, or NOT_APPLICABLE."),
    Column("selection_reason", String(50), nullable=False, comment="Reason such as TENANT_OVERRIDE, ENTITLED_PROVIDER, PLATFORM_DATA, PUBLIC_FALLBACK, or MISSING_DATA."),
    Column("entitlement_decision", String(30), nullable=False, comment="Entitlement outcome such as ALLOWED, DENIED, NOT_REQUIRED, or NOT_AVAILABLE."),
    Column("policy_rule_id", UUID_V7, ForeignKey("ten.valuation_policy_rule.valuation_policy_rule_id"), nullable=True, comment="Policy rule that selected or rejected the candidate value."),
    Column("exception_code", String(100), nullable=True, comment="Structured exception code when a value could not be resolved."), schema="md",
)

market_data_resolution_idempotency = Table(
    "market_data_resolution_idempotency", metadata,
    Column("market_data_resolution_idempotency_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one idempotent snapshot-create request."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant scope of the idempotency key."),
    Column("endpoint", String(200), nullable=False, comment="Literal API endpoint whose create request is deduplicated."),
    Column("idempotency_key", String(255), nullable=False, comment="Caller-supplied opaque idempotency key retained only for replay lookup."),
    Column("request_fingerprint", String(64), nullable=False, comment="SHA-256 fingerprint of the canonical validated request payload."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=False, comment="Frozen snapshot created by the idempotent request."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the key was first recorded."),
    Column("expires_at_utc", DateTime(timezone=True), nullable=False, comment="UTC expiry timestamp after which the key may be retired."),
    UniqueConstraint("tenant_id", "endpoint", "idempotency_key", name="uq_market_data_resolution_idempotency_scope"),
    schema="md",
)

Index("ix_market_data_resolution_idempotency_snapshot", market_data_resolution_idempotency.c.market_data_resolution_snapshot_id)

nav_calculation_run = Table(
    "nav_calculation_run", metadata,
    Column("nav_calculation_run_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one tenant Soft-NAV calculation run."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant for which the Soft-NAV calculation is performed."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=False, comment="Fund, share-class, mandate, or ledger strategy valued by the run."),
    Column("position_snapshot_id", UUID_V7, ForeignKey("trd.position_snapshot.position_snapshot_id"), nullable=False, comment="Immutable position snapshot used by the Soft-NAV calculation rather than a later reconstructed holding set."),
    Column("valuation_date", Date, nullable=False, comment="Business date for which the Soft NAV is calculated."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=False, comment="Named business valuation cut for the run."),
    Column("valuation_policy_id", UUID_V7, ForeignKey("ten.valuation_policy.valuation_policy_id"), nullable=False, comment="Exact tenant valuation-policy version applied to the run."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=False, comment="Immutable resolved market-data input set used by the Soft NAV."),
    Column("calculation_version", String(100), nullable=False, comment="Version of the Fortem calculation implementation used by the run."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Run review status such as DRAFT, REVIEWED, APPROVED, REJECTED, or SUPERSEDED."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the calculation run was created."), schema="nav",
)

nav_input_snapshot = Table(
    "nav_input_snapshot", metadata,
    Column("nav_input_snapshot_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the append-only audit header of a Soft-NAV input set."),
    Column("nav_calculation_run_id", UUID_V7, ForeignKey("nav.nav_calculation_run.nav_calculation_run_id"), nullable=False, unique=True, comment="Soft-NAV calculation run whose inputs are frozen by this snapshot."),
    Column("resolved_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which all input selections were frozen."),
    Column("input_hash", String(64), nullable=False, comment="SHA-256 or equivalent deterministic hash of the ordered input set for audit and reproducibility."),
    Column("status", String(30), nullable=False, server_default=text("'FROZEN'"), comment="Snapshot status such as FROZEN, PARTIAL, or SUPERSEDED."), schema="nav",
)

nav_input_snapshot_item = Table(
    "nav_input_snapshot_item", metadata,
    Column("nav_input_snapshot_item_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one selected market-data, override, cash, or calculation input used by Soft NAV."),
    Column("nav_input_snapshot_id", UUID_V7, ForeignKey("nav.nav_input_snapshot.nav_input_snapshot_id"), nullable=False, comment="Frozen Soft-NAV input snapshot containing the item."),
    Column("subject_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Reference object whose value or input was used."),
    Column("market_data_series_id", UUID_V7, ForeignKey("md.market_data_series.market_data_series_id"), nullable=True, comment="Selected market-data series when the input is externally or internally observed."),
    Column("market_data_observation_id", UUID_V7, ForeignKey("md.market_data_observation.market_data_observation_id"), nullable=True, comment="Selected immutable observation when the input comes from market data."),
    Column("market_data_resolution_snapshot_item_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot_item.market_data_resolution_snapshot_item_id"), nullable=True, comment="Resolved market-data snapshot item supplying this frozen input when the Soft-NAV input came from the shared resolver."),
    Column("policy_rule_id", UUID_V7, ForeignKey("ten.valuation_policy_rule.valuation_policy_rule_id"), nullable=True, comment="Exact frozen valuation-policy rule responsible for selecting, rejecting, or requiring override of the input."),
    Column("dataset_id", UUID_V7, ForeignKey("md.dataset.dataset_id"), nullable=True, comment="Dataset provenance for the selected market-data input."),
    Column("acquisition_licence_id", UUID_V7, ForeignKey("md.data_licence.data_licence_id"), nullable=True, comment="Licence under which Fortem acquired the selected market-data input when known."),
    Column("selected_value", Numeric(30, 12), nullable=False, comment="Exact scalar value frozen for use by the Soft-NAV calculation."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of the selected input value when applicable."),
    Column("pricing_date_requested", Date, nullable=True, comment="Business date requested by the policy for this input, retained even when it differs from the NAV valuation date."),
    Column("pricing_date_used", Date, nullable=True, comment="Actual market date of the frozen selected observation, retained for reproducibility and freshness review."),
    Column("staleness_business_days", Integer, nullable=True, comment="Business-day staleness of the selected observation relative to the requested pricing date."),
    Column("staleness_status", String(40), nullable=True, comment="Frozen freshness state such as CURRENT, WITHIN_TOLERANCE, STALE, MISSING, or NOT_APPLICABLE."),
    Column("selection_reason", String(50), nullable=False, comment="Reason such as OFFICIAL_CLOSE, EVALUATED_PRICE, MODEL_OVERRIDE, FX_SPOT, or CASH_BALANCE."),
    Column("entitlement_decision", String(30), nullable=False, comment="Recorded access decision such as ALLOWED, INTERNAL_ONLY, OVERRIDE, or NOT_REQUIRED."), schema="nav",
)

nav_valuation_line = Table(
    "nav_valuation_line", metadata,
    Column("nav_valuation_line_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one position or cash valuation line in a Soft-NAV run."),
    Column("nav_calculation_run_id", UUID_V7, ForeignKey("nav.nav_calculation_run.nav_calculation_run_id"), nullable=False, comment="Soft-NAV calculation run producing the valuation line."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=True, comment="Instrument, listing, or cash currency valued by the line when applicable."),
    Column("price_input_snapshot_item_id", UUID_V7, ForeignKey("nav.nav_input_snapshot_item.nav_input_snapshot_item_id"), nullable=True, comment="Frozen NAV input item supplying the instrument or cash price used by this line."),
    Column("quantity", Numeric(30, 12), nullable=True, comment="Position quantity or cash amount used by the line."),
    Column("local_value", Numeric(30, 12), nullable=False, comment="Calculated value in local currency before reporting-currency conversion."),
    Column("local_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency of the local valuation amount."),
    Column("fx_rate", Numeric(30, 12), nullable=True, comment="FX conversion rate applied to derive reporting-currency value when required."),
    Column("fx_input_snapshot_item_id", UUID_V7, ForeignKey("nav.nav_input_snapshot_item.nav_input_snapshot_item_id"), nullable=True, comment="Frozen NAV input item supplying the FX rate used by this line."),
    Column("reporting_value", Numeric(30, 12), nullable=False, comment="Calculated value in the Soft-NAV reporting currency."),
    Column("exception_status", String(30), nullable=False, server_default=text("'NONE'"), comment="Valuation exception state such as NONE, STALE_DATA, MISSING_DATA, or MANUAL_OVERRIDE."), schema="nav",
)

nav_result = Table(
    "nav_result", metadata,
    Column("nav_result_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for the aggregate result of a Soft-NAV run."),
    Column("nav_calculation_run_id", UUID_V7, ForeignKey("nav.nav_calculation_run.nav_calculation_run_id"), nullable=False, unique=True, comment="Soft-NAV calculation run producing the aggregate result."),
    Column("reporting_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Base currency in which the Soft-NAV result is reported."),
    Column("gross_assets", Numeric(30, 12), nullable=False, comment="Aggregate gross assets in reporting currency."),
    Column("liabilities", Numeric(30, 12), nullable=False, comment="Aggregate liabilities in reporting currency."),
    Column("net_asset_value", Numeric(30, 12), nullable=False, comment="Calculated Soft NAV in reporting currency."),
    Column("units_in_issue", Numeric(30, 12), nullable=True, comment="Fund or share-class units in issue used to derive NAV per unit when applicable."),
    Column("nav_per_unit", Numeric(30, 12), nullable=True, comment="Calculated Soft NAV per unit when units in issue are available."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Aggregate result review status such as DRAFT, REVIEWED, APPROVED, REJECTED, or SUPERSEDED."), schema="nav",
)

nav_reconciliation = Table(
    "nav_reconciliation", metadata,
    Column("nav_reconciliation_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for comparison of a Soft-NAV result with an administrator or other reference NAV."),
    Column("nav_calculation_run_id", UUID_V7, ForeignKey("nav.nav_calculation_run.nav_calculation_run_id"), nullable=False, comment="Soft-NAV run being reconciled."),
    Column("reference_nav_value", Numeric(30, 12), nullable=False, comment="Administrator, accounting, or other reference NAV against which the run is compared."),
    Column("reference_currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency of the reference NAV."),
    Column("reference_source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Administrator or other retained source payload supplying the reference NAV."),
    Column("difference_amount", Numeric(30, 12), nullable=False, comment="Soft-NAV minus reference-NAV difference in the stated reference currency or reconciled reporting currency."),
    Column("tolerance_amount", Numeric(30, 12), nullable=True, comment="Approved monetary tolerance used to evaluate the reconciliation."),
    Column("status", String(30), nullable=False, comment="Reconciliation status such as MATCHED, WITHIN_TOLERANCE, BREAK, INVESTIGATING, or APPROVED."),
    Column("comment", Text, nullable=True, comment="Explanation, break analysis, or approval notes for the reconciliation."), schema="nav",
)

valuation_mark = Table(
    "valuation_mark",
    metadata,
    Column("valuation_mark_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one tenant-scoped valuation conclusion."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant owning the valuation mark and its confidential methodology/context."),
    Column("subject_reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, fund, position subject or other reference node being marked."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=True, comment="Optional strategy or portfolio context for the mark."),
    Column("position_snapshot_line_id", UUID_V7, ForeignKey("trd.position_snapshot_line.position_snapshot_line_id"), nullable=True, comment="Optional frozen position line to which the mark applies."),
    Column("trade_id", UUID_V7, ForeignKey("trd.trade.trade_id"), nullable=True, comment="Optional booked trade to which the mark applies."),
    Column("valuation_date", Date, nullable=False, comment="Business valuation date of the mark."),
    Column("valuation_cut_id", UUID_V7, ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=False, comment="Named valuation cut used for the mark."),
    Column("market_data_as_of_utc", DateTime(timezone=True), nullable=False, comment="Historic information cut after which observations were ineligible for this mark."),
    Column("mark_type", String(50), nullable=False, comment="Mark classification such as FAIR_VALUE, MODEL_PRICE, ADMINISTRATOR_MARK, CLEAN_PRICE, DIRTY_PRICE, or YIELD."),
    Column("valuation_method", String(100), nullable=False, comment="Controlled or versioned method used to reach the mark."),
    Column("value", Numeric(30, 12), nullable=False, comment="Valuation result in the stated currency and price/value convention."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency of the valuation result."),
    Column("market_data_resolution_snapshot_id", UUID_V7, ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=True, comment="Immutable selected market-data input set supporting the mark when source data was used."),
    Column("approved_override_id", UUID_V7, nullable=True, comment="Tenant-approved override evidence identifier when the mark is not based on a market-data snapshot."),
    Column("calculation_version", String(100), nullable=False, comment="Version of the valuation implementation or model used to calculate the mark."),
    Column("status", String(30), nullable=False, server_default=text("'DRAFT'"), comment="Review lifecycle such as DRAFT, REVIEWED, APPROVED, REJECTED, or SUPERSEDED."),
    Column("created_by_user_account_id", UUID_V7, ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated account or service that created the mark."),
    Column("created_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which the mark was created."),
    schema="nav",
)

position_snapshot = Table(
    "position_snapshot", metadata,
    Column("position_snapshot_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one full tenant strategy position snapshot."),
    Column("tenant_id", UUID_V7, ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant owning the submitted or calculated position snapshot."),
    Column("strategy_id", UUID_V7, ForeignKey("trd.strategy.strategy_id"), nullable=False, comment="Fund, share class, mandate, or ledger strategy represented by the snapshot."),
    Column("as_of_date", Date, nullable=False, comment="Business date for which positions are asserted."),
    Column("as_of_datetime_utc", DateTime(timezone=True), nullable=False, comment="UTC cut-off timestamp at which the full position set applies."),
    Column("source_payload_id", UUID_V7, ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained client, custodian, administrator, or internal payload supplying the positions."),
    Column("content_hash", String(64), nullable=False, comment="Deterministic hash of the ordered position lines for idempotency and audit."),
    Column("status", String(30), nullable=False, server_default=text("'ACTIVE'"), comment="Snapshot status such as ACTIVE, SUPERSEDED, REJECTED, or PARTIAL."),
    Column("received_at_utc", DateTime(timezone=True), nullable=False, server_default=UTC_NOW, comment="UTC timestamp at which Fortem received or created the snapshot."),
    UniqueConstraint("tenant_id", "strategy_id", "as_of_datetime_utc", "content_hash", name="uq_position_snapshot_idempotency"), schema="trd",
)

position_snapshot_line = Table(
    "position_snapshot_line", metadata,
    Column("position_snapshot_line_id", UUID_V7, primary_key=True, server_default=UUID_V7_DEFAULT, comment="Immutable UUIDv7 identifier for one holding line in a full position snapshot."),
    Column("position_snapshot_id", UUID_V7, ForeignKey("trd.position_snapshot.position_snapshot_id"), nullable=False, comment="Full position snapshot containing the holding line."),
    Column("reference_node_id", UUID_V7, ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Resolved Fortem instrument, listing, cash currency, or other reference node held by the strategy."),
    Column("external_object_mapping_id", UUID_V7, ForeignKey("ing.external_object_mapping.external_object_mapping_id"), nullable=True, comment="External-ID mapping used to resolve the inbound holding identifier when applicable."),
    Column("quantity", Numeric(30, 12), nullable=False, comment="Signed quantity held in the stated quantity unit."),
    Column("quantity_unit", String(40), nullable=False, comment="Quantity unit such as SHARE, CONTRACT, NOMINAL, UNIT, or CURRENCY_AMOUNT."),
    Column("source_price", Numeric(30, 12), nullable=True, comment="Price supplied by the source snapshot for reconciliation only; it does not replace selected valuation inputs."),
    Column("source_market_value", Numeric(30, 12), nullable=True, comment="Market value supplied by the source snapshot for reconciliation only."),
    Column("currency_id", UUID_V7, ForeignKey("secm.currency.currency_id"), nullable=True, comment="Currency of supplied source price or market value when applicable."),
    Column("source_line_reference", String(500), nullable=True, comment="Source row, position, or holding reference used for reconciliation and exception investigation."), schema="trd",
)

Index("ix_external_mapping_current_lookup", external_object_mapping.c.external_id_namespace_id, external_object_mapping.c.external_id_value, external_object_mapping.c.valid_to)
Index("ix_constituent_snapshot_owner_date", reference_constituent_snapshot.c.owner_reference_node_id, reference_constituent_snapshot.c.snapshot_date)
Index("uq_structured_product_initial_fixing_current", structured_product_initial_fixing.c.structured_product_terms_id, structured_product_initial_fixing.c.underlying_reference_node_id, structured_product_initial_fixing.c.fixing_date, unique=True, postgresql_where=text("status = 'ACCEPTED'"))
Index("ix_option_strike_adjustment_terms_effective", option_strike_adjustment.c.option_terms_id, option_strike_adjustment.c.effective_date, option_strike_adjustment.c.recorded_at_utc)
Index("ix_corporate_action_instrument", corporate_action.c.affected_instrument_node_id, corporate_action.c.recorded_at_utc)
Index("ix_resolution_snapshot_tenant_date", market_data_resolution_snapshot.c.tenant_id, market_data_resolution_snapshot.c.valuation_date)
Index("ix_nav_run_tenant_strategy_date", nav_calculation_run.c.tenant_id, nav_calculation_run.c.strategy_id, nav_calculation_run.c.valuation_date)
Index("ix_position_snapshot_strategy_as_of", position_snapshot.c.strategy_id, position_snapshot.c.as_of_datetime_utc)
Index("ix_fee_rule_type_validity", fee_rule.c.fee_type_id, fee_rule.c.valid_from, fee_rule.c.valid_to)
Index("ix_fee_rule_target_reference_node", fee_rule_target.c.target_reference_node_id, fee_rule_target.c.effective_from, fee_rule_target.c.effective_to)
Index("ix_fee_rule_target_strategy", fee_rule_target.c.target_strategy_id, fee_rule_target.c.effective_from, fee_rule_target.c.effective_to)
Index(
    "ix_reference_data_automation_policy_source_target",
    reference_data_automation_policy.c.source_system_id,
    reference_data_automation_policy.c.target_object_type,
    reference_data_automation_policy.c.operation_type,
    reference_data_automation_policy.c.valid_from,
    reference_data_automation_policy.c.valid_to,
)
Index("ix_index_terms_family", index_terms.c.index_family_id)
Index("ix_index_methodology_index_effective", index_methodology_version.c.index_node_id, index_methodology_version.c.effective_from, index_methodology_version.c.effective_to)
Index("uq_option_terms_current", option_terms.c.instrument_node_id, unique=True, postgresql_where=text("is_current"))
Index("ix_option_terms_effective", option_terms.c.instrument_node_id, option_terms.c.effective_from, option_terms.c.effective_to)
Index("ix_option_strike_reset_rule_event", option_strike_reset_rule.c.schedule_event_id, option_strike_reset_rule.c.option_terms_id)
Index("uq_option_strike_fixing_current", option_strike_fixing.c.option_strike_reset_rule_id, option_strike_fixing.c.fixing_date, unique=True, postgresql_where=text("status = 'ACCEPTED'"))
Index("ix_option_strike_fixing_rule_date", option_strike_fixing.c.option_strike_reset_rule_id, option_strike_fixing.c.fixing_date, option_strike_fixing.c.recorded_at_utc)
Index(
    "ix_reference_data_proposal_idempotency",
    reference_data_proposal.c.source_system_id,
    reference_data_proposal.c.idempotency_key,
    reference_data_proposal.c.tenant_id,
)
