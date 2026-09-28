"""Baseline governed reference data and idempotent PostgreSQL seed helpers."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Connection, select, update
from sqlalchemy.dialects.postgresql import insert

from .models import (
    bond_terms,
    crypto_network,
    day_count_convention,
    fee_rule,
    identifier_scheme,
    index_kind_catalogue,
    instrument_type,
    operating_profile,
    operating_profile_module_recommendation,
    platform_module,
    reference_node_type,
    return_profile,
    series_measure_definition,
    taxonomy,
    taxonomy_value,
)


DAY_COUNT_CONVENTION_SEEDS: Sequence[dict[str, Any]] = (
    {
        "code": "ACT_360",
        "display_name": "Actual/360",
        "description": "Actual elapsed days divided by 360; common for money-market and floating-rate instruments.",
        "standard_source": "MARKET_PRACTICE",
        "status": "ACTIVE",
        "sort_order": 10,
    },
    {
        "code": "ACT_365F",
        "display_name": "Actual/365 Fixed",
        "description": "Actual elapsed days divided by a fixed denominator of 365.",
        "standard_source": "MARKET_PRACTICE",
        "status": "ACTIVE",
        "sort_order": 20,
    },
    {
        "code": "ACT_ACT_ISDA",
        "display_name": "Actual/Actual ISDA",
        "description": "Actual days apportioned using the ISDA actual/actual convention across calendar years.",
        "standard_source": "ISDA",
        "status": "ACTIVE",
        "sort_order": 30,
    },
    {
        "code": "ACT_ACT_ICMA",
        "display_name": "Actual/Actual ICMA",
        "description": "Actual days compared with the regular coupon period under the ICMA bond convention.",
        "standard_source": "ICMA",
        "status": "ACTIVE",
        "sort_order": 40,
    },
    {
        "code": "ACT_ACT_AFB",
        "display_name": "Actual/Actual AFB",
        "description": "Actual/actual convention following the Association Française de Banques methodology.",
        "standard_source": "AFB",
        "status": "ACTIVE",
        "sort_order": 50,
    },
    {
        "code": "30_360_US",
        "display_name": "30/360 US",
        "description": "Thirty/360 US municipal or bond basis with US date-adjustment rules.",
        "standard_source": "MARKET_PRACTICE",
        "status": "ACTIVE",
        "sort_order": 60,
    },
    {
        "code": "30E_360",
        "display_name": "30E/360",
        "description": "European thirty/360 basis, treating month ends according to the standard European rule.",
        "standard_source": "MARKET_PRACTICE",
        "status": "ACTIVE",
        "sort_order": 70,
    },
    {
        "code": "30E_360_ISDA",
        "display_name": "30E/360 ISDA",
        "description": "Thirty/360 European basis with ISDA end-of-month adjustments.",
        "standard_source": "ISDA",
        "status": "ACTIVE",
        "sort_order": 80,
    },
    {
        "code": "BUS_252",
        "display_name": "Business/252",
        "description": "Business days divided by 252 using the applicable business calendar.",
        "standard_source": "MARKET_PRACTICE",
        "status": "ACTIVE",
        "sort_order": 90,
    },
)


RETURN_PROFILE_SEEDS: Sequence[dict[str, Any]] = (
    {
        "profile_code": "PRICE_RETURN",
        "display_name": "Price return",
        "description": "Performance based on price movements only; distributed income is not reinvested.",
        "base_return_basis": "PRICE",
        "income_treatment": "NONE",
        "tax_treatment": "NONE",
        "financing_treatment": "NONE",
        "requires_financing_reference": False,
        "status": "ACTIVE",
        "sort_order": 10,
    },
    {
        "profile_code": "GROSS_TOTAL_RETURN",
        "display_name": "Gross total return",
        "description": "Price performance plus distributed income notionally reinvested before withholding tax.",
        "base_return_basis": "TOTAL",
        "income_treatment": "REINVESTED_GROSS",
        "tax_treatment": "GROSS",
        "financing_treatment": "NONE",
        "requires_financing_reference": False,
        "status": "ACTIVE",
        "sort_order": 20,
    },
    {
        "profile_code": "NET_TOTAL_RETURN",
        "display_name": "Net total return",
        "description": "Price performance plus distributed income notionally reinvested after the methodology's withholding-tax assumption.",
        "base_return_basis": "TOTAL",
        "income_treatment": "REINVESTED_NET",
        "tax_treatment": "NET_WITHHOLDING",
        "financing_treatment": "NONE",
        "requires_financing_reference": False,
        "status": "ACTIVE",
        "sort_order": 30,
    },
    {
        "profile_code": "EXCESS_PRICE_RETURN",
        "display_name": "Excess price return",
        "description": "Price return adjusted by subtracting an applicable financing or reference-rate return according to methodology.",
        "base_return_basis": "PRICE",
        "income_treatment": "NONE",
        "tax_treatment": "NONE",
        "financing_treatment": "SUBTRACT_REFERENCE_RATE",
        "requires_financing_reference": True,
        "status": "ACTIVE",
        "sort_order": 40,
    },
    {
        "profile_code": "EXCESS_TOTAL_RETURN",
        "display_name": "Excess total return",
        "description": "Total return adjusted by subtracting an applicable financing or reference-rate return according to methodology.",
        "base_return_basis": "TOTAL",
        "income_treatment": "REINVESTED_GROSS",
        "tax_treatment": "METHODOLOGY_DEFINED",
        "financing_treatment": "SUBTRACT_REFERENCE_RATE",
        "requires_financing_reference": True,
        "status": "ACTIVE",
        "sort_order": 50,
    },
    {
        "profile_code": "DIVIDEND_POINTS",
        "display_name": "Dividend points",
        "description": "Index points attributable to constituent dividends, tracked separately from price appreciation and total return.",
        "base_return_basis": "INCOME_ONLY",
        "income_treatment": "POINTS_ONLY",
        "tax_treatment": "METHODOLOGY_DEFINED",
        "financing_treatment": "NONE",
        "requires_financing_reference": False,
        "status": "ACTIVE",
        "sort_order": 60,
    },
)


INDEX_KIND_CATALOGUE_SEEDS: Sequence[dict[str, Any]] = (
    {
        "index_kind_code": "PUBLIC",
        "display_name": "Public benchmark",
        "description": "Publicly disseminated or observable benchmark. Public access does not mean the methodology is open; the provider may still own and restrict the methodology.",
        "dissemination_class": "PUBLIC",
        "methodology_ownership": "PROVIDER_OWNED",
        "example_text": "S&P 500: publicly quoted benchmark with provider-owned methodology.",
        "status": "ACTIVE",
        "sort_order": 10,
    },
    {
        "index_kind_code": "QIS",
        "display_name": "QIS / quantitative strategy",
        "description": "Rules-based quantitative investment strategy expressed as an index. It is commonly provider- or client-designed and may be public, restricted, or private.",
        "dissemination_class": "RESTRICTED",
        "methodology_ownership": "MIXED",
        "example_text": "A bank QIS index with a documented ruleset and controlled distribution.",
        "status": "ACTIVE",
        "sort_order": 20,
    },
    {
        "index_kind_code": "PROPRIETARY",
        "display_name": "Proprietary methodology",
        "description": "Index whose methodology, calculation rules, or constituent process is owned or controlled by a provider or client. It may still have a public price or identifier.",
        "dissemination_class": "RESTRICTED",
        "methodology_ownership": "PROVIDER_OWNED",
        "example_text": "A provider-owned thematic or systematic index distributed to selected users.",
        "status": "ACTIVE",
        "sort_order": 30,
    },
    {
        "index_kind_code": "CUSTOM_BASKET",
        "display_name": "Custom basket",
        "description": "Bespoke index or basket maintained for a client, product, or internal use. Its constituent snapshots and rules are governed separately from this category code.",
        "dissemination_class": "PRIVATE",
        "methodology_ownership": "CLIENT_OWNED",
        "example_text": "A manually maintained client basket whose constituents are snapshotted over time.",
        "status": "ACTIVE",
        "sort_order": 40,
    },
)


CRYPTO_NETWORK_SEEDS: Sequence[dict[str, Any]] = (
    {
        "network_code": "BITCOIN_MAINNET",
        "display_name": "Bitcoin mainnet",
        "network_family": "BITCOIN",
        "chain_identifier": "bitcoin-mainnet",
        "native_currency_code": "BTC",
        "status": "ACTIVE",
        "sort_order": 10,
    },
    {
        "network_code": "ETHEREUM_MAINNET",
        "display_name": "Ethereum mainnet",
        "network_family": "EVM",
        "chain_identifier": "1",
        "native_currency_code": "ETH",
        "status": "ACTIVE",
        "sort_order": 20,
    },
    {
        "network_code": "SOLANA_MAINNET",
        "display_name": "Solana mainnet",
        "network_family": "SOLANA",
        "chain_identifier": "mainnet-beta",
        "native_currency_code": "SOL",
        "status": "ACTIVE",
        "sort_order": 30,
    },
    {
        "network_code": "BASE_MAINNET",
        "display_name": "Base mainnet",
        "network_family": "EVM",
        "chain_identifier": "8453",
        "native_currency_code": "ETH",
        "status": "ACTIVE",
        "sort_order": 40,
    },
)


REFERENCE_NODE_TYPE_SEEDS: Sequence[dict[str, Any]] = (
    {
        "type_code": "INSTRUMENT",
        "display_name": "Economic instrument",
        "description": "A contractual or economic financial instrument, including OTC contracts and issued securities.",
        "node_class": "ECONOMIC",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 10,
    },
    {
        "type_code": "LISTING",
        "display_name": "Venue listing",
        "description": "A venue-specific tradable representation of an economic instrument.",
        "node_class": "VENUE_REPRESENTATION",
        "default_is_tradable": True,
        "status": "ACTIVE",
        "sort_order": 20,
    },
    {
        "type_code": "INDEX",
        "display_name": "Index",
        "description": "A calculated financial index, normally non-tradeable in its own right.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 30,
    },
    {
        "type_code": "INDEX_FAMILY",
        "display_name": "Index family",
        "description": "A non-tradeable conceptual grouping for related index variants such as price, total-return, or hedged variants.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 35,
    },
    {
        "type_code": "CURRENCY",
        "display_name": "Currency",
        "description": "A fiat, cryptoasset, stablecoin, or accounting currency role; individual currencies are not traded in isolation.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 40,
    },
    {
        "type_code": "FX_PAIR",
        "display_name": "FX pair",
        "description": "A pair of currencies used as a spot or market-data reference; contracts on it are separate instruments.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 50,
    },
    {
        "type_code": "COMMODITY",
        "display_name": "Commodity",
        "description": "A precisely defined physical commodity underlying or reference object.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 60,
    },
    {
        "type_code": "RATE_INDEX",
        "display_name": "Rate index",
        "description": "A benchmark interest-rate or fixing reference such as SONIA, SOFR, or EURIBOR.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 70,
    },
    {
        "type_code": "REFERENCE_PORTFOLIO",
        "display_name": "Reference portfolio",
        "description": "A non-tradeable managed or calculated portfolio used as a benchmark, AMC reference portfolio, or strategy reference.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 80,
    },
    {
        "type_code": "FUTURE_FAMILY",
        "display_name": "Future family",
        "description": "A non-tradeable future-contract specification grouping separately tradeable expiry instruments.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 90,
    },
    {
        "type_code": "FUND",
        "display_name": "Fund or sub-fund",
        "description": "A non-tradeable collective investment vehicle or compartment; its share classes are separate economic instruments.",
        "node_class": "REFERENCE",
        "default_is_tradable": False,
        "status": "ACTIVE",
        "sort_order": 100,
    },
)


IDENTIFIER_SCHEME_SEEDS: Sequence[dict[str, Any]] = (
    {"scheme_code": "ISIN", "display_name": "International Securities Identification Number", "scope": "INSTRUMENT", "is_external_standard": True},
    {"scheme_code": "FIGI", "display_name": "Financial Instrument Global Identifier", "scope": "MIXED", "is_external_standard": True},
    {"scheme_code": "CUSIP", "display_name": "Committee on Uniform Securities Identification Procedures", "scope": "INSTRUMENT", "is_external_standard": True},
    {"scheme_code": "SEDOL", "display_name": "Stock Exchange Daily Official List", "scope": "INSTRUMENT", "is_external_standard": True},
    {"scheme_code": "TICKER", "display_name": "Venue ticker symbol", "scope": "LISTING", "is_external_standard": False},
    {"scheme_code": "VENUE_PRODUCT_ID", "display_name": "Venue product or market identifier", "scope": "LISTING", "is_external_standard": False},
    {"scheme_code": "FIX_SECURITY_ID", "display_name": "FIX security identifier used for execution or allocation", "scope": "LISTING", "is_external_standard": False},
    {"scheme_code": "RIC", "display_name": "Refinitiv Instrument Code", "scope": "MIXED", "is_external_standard": False},
    {"scheme_code": "BLOOMBERG_TICKER", "display_name": "Bloomberg ticker", "scope": "MIXED", "is_external_standard": False},
)


INSTRUMENT_TYPE_SEEDS: Sequence[dict[str, Any]] = (
    {"type_code": "EQUITY", "display_name": "Equity", "description": "Issued ordinary, preferred, or other equity security.", "default_asset_class": "EQUITY", "status": "ACTIVE", "sort_order": 10},
    {"type_code": "BOND", "display_name": "Bond", "description": "Fixed-income debt security, including sovereign and corporate bonds.", "default_asset_class": "FIXED_INCOME", "status": "ACTIVE", "sort_order": 20},
    {"type_code": "CONVERTIBLE_BOND", "display_name": "Convertible bond", "description": "Bond with contractual conversion or exchange rights.", "default_asset_class": "FIXED_INCOME", "status": "ACTIVE", "sort_order": 30},
    {"type_code": "ETF", "display_name": "Exchange-traded fund", "description": "Exchange-traded fund share or unit.", "default_asset_class": "FUND", "status": "ACTIVE", "sort_order": 40},
    {"type_code": "ETC", "display_name": "Exchange-traded commodity", "description": "Exchange-traded commodity-linked security or certificate.", "default_asset_class": "COMMODITY", "status": "ACTIVE", "sort_order": 41},
    {"type_code": "ETN", "display_name": "Exchange-traded note", "description": "Exchange-traded unsecured or secured note linked to a reference index or asset.", "default_asset_class": "STRUCTURED_PRODUCT", "status": "ACTIVE", "sort_order": 42},
    {"type_code": "EXCHANGE_TRADED_VEHICLE", "display_name": "Exchange-traded vehicle", "description": "Exchange-traded investment vehicle whose legal form is not classified as an ETF, ETC, or ETN.", "default_asset_class": "STRUCTURED_PRODUCT", "status": "ACTIVE", "sort_order": 43},
    {"type_code": "FUND", "display_name": "Fund", "description": "Collective investment vehicle or fund umbrella.", "default_asset_class": "FUND", "status": "ACTIVE", "sort_order": 50},
    {"type_code": "FUND_SHARE_CLASS", "display_name": "Fund share class", "description": "Tradeable or subscribable share class of a fund.", "default_asset_class": "FUND", "status": "ACTIVE", "sort_order": 60},
    {"type_code": "FX_FORWARD", "display_name": "FX forward", "description": "OTC foreign-exchange forward with fixed contractual currencies, rate, and maturity.", "default_asset_class": "FX", "status": "ACTIVE", "sort_order": 70},
    {"type_code": "FORWARD", "display_name": "Forward", "description": "OTC forward contract other than a dedicated FX forward.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 80},
    {"type_code": "FUTURE", "display_name": "Future", "description": "Standardised listed or cleared futures contract for one expiry.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 90},
    {"type_code": "OPTION", "display_name": "Option", "description": "Vanilla or barrier option instrument.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 100},
    {"type_code": "COMPOSED_OPTION", "display_name": "Composed option", "description": "One OTC legal/economic option package composed of payoff components.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 110},
    {"type_code": "SWAP", "display_name": "Swap", "description": "Bilateral swap represented by its contractual legs and terms.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 120},
    {"type_code": "SWAPTION", "display_name": "Swaption", "description": "Option to enter an underlying swap.", "default_asset_class": "DERIVATIVE", "status": "ACTIVE", "sort_order": 130},
    {"type_code": "FRA", "display_name": "Forward rate agreement", "description": "Forward rate agreement instrument.", "default_asset_class": "RATES", "status": "ACTIVE", "sort_order": 140},
    {"type_code": "CAP", "display_name": "Interest-rate cap", "description": "Interest-rate option cap.", "default_asset_class": "RATES", "status": "ACTIVE", "sort_order": 150},
    {"type_code": "FLOOR", "display_name": "Interest-rate floor", "description": "Interest-rate option floor.", "default_asset_class": "RATES", "status": "ACTIVE", "sort_order": 160},
    {"type_code": "CREDIT_DEFAULT_SWAP", "display_name": "Credit default swap", "description": "Single-name or reference-obligation credit default swap.", "default_asset_class": "CREDIT", "status": "ACTIVE", "sort_order": 170},
    {"type_code": "CREDIT_INDEX", "display_name": "Credit index product", "description": "Tradeable credit-index product or contract.", "default_asset_class": "CREDIT", "status": "ACTIVE", "sort_order": 180},
    {"type_code": "CREDIT_TRANCHE", "display_name": "Credit tranche", "description": "Tradeable tranche on a credit index or basket.", "default_asset_class": "CREDIT", "status": "ACTIVE", "sort_order": 190},
    {"type_code": "STRUCTURED_PRODUCT", "display_name": "Structured product", "description": "Issued or OTC structured payoff product with composition, barriers, and schedules.", "default_asset_class": "STRUCTURED_PRODUCT", "status": "ACTIVE", "sort_order": 200},
    {"type_code": "ACTIVELY_MANAGED_CERTIFICATE", "display_name": "Actively managed certificate", "description": "Securitised actively managed certificate linked to a dated reference portfolio.", "default_asset_class": "STRUCTURED_PRODUCT", "status": "ACTIVE", "sort_order": 210},
    {"type_code": "EXCHANGE_TRADED_CERTIFICATE", "display_name": "Exchange-traded certificate", "description": "Exchange-traded certificate or ETI wrapper.", "default_asset_class": "STRUCTURED_PRODUCT", "status": "ACTIVE", "sort_order": 220},
    {"type_code": "WARRANT", "display_name": "Warrant", "description": "Issued warrant security with option-like economics.", "default_asset_class": "EQUITY", "status": "ACTIVE", "sort_order": 230},
    {"type_code": "RIGHT", "display_name": "Right", "description": "Temporary tradeable right generated by a corporate action or issuance.", "default_asset_class": "EQUITY", "status": "ACTIVE", "sort_order": 240},
    {"type_code": "REPO", "display_name": "Repurchase agreement", "description": "Securities financing repurchase agreement.", "default_asset_class": "FINANCING", "status": "ACTIVE", "sort_order": 250},
    {"type_code": "SECURITIES_LENDING", "display_name": "Securities lending", "description": "Securities lending or borrowing transaction.", "default_asset_class": "FINANCING", "status": "ACTIVE", "sort_order": 260},
    {"type_code": "DIGITAL_ASSET", "display_name": "Digital asset", "description": "Cryptoasset economic instrument role, potentially also represented as a currency.", "default_asset_class": "DIGITAL_ASSET", "status": "ACTIVE", "sort_order": 270},
)


TAXONOMY_SEEDS: Sequence[dict[str, Any]] = (
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "display_name": "Structured product archetype", "description": "Internal commercial taxonomy for structured-product payoff archetypes.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "display_name": "Index asset class", "description": "Canonical asset-class classification for an index and its underlying exposure.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "display_name": "Index geography", "description": "Geographic market scope represented by an index.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_SCOPE", "display_name": "Index scope", "description": "Breadth or coverage scope of an index universe.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_SIZE", "display_name": "Index size segment", "description": "Capitalisation or issuer-size segment represented by an index.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_STRATEGY", "display_name": "Index strategy", "description": "Construction or investment strategy used by an index.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "display_name": "Index benchmark role", "description": "Operational role of an index as benchmark, investable reference, or custom strategy.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "INDEX_SECTOR", "display_name": "Index sector", "description": "Sector exposure represented by an index where a sector classification applies.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "display_name": "Exchange-traded product class", "description": "Umbrella classification grouping ETF, ETC, ETN, ETV, and ETI instruments for reporting and UI filtering.", "applies_to": "INSTRUMENT", "status": "ACTIVE"},
)


TAXONOMY_VALUE_SEEDS: Sequence[dict[str, Any]] = (
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "AUTOCALL", "parent_value_code": None, "display_name": "Autocall", "description": "Structured product with an early redemption mechanism.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "STANDARD_AUTOCALL", "parent_value_code": "AUTOCALL", "display_name": "Standard autocall", "description": "Autocall with the standard coupon and early-redemption mechanics.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "AUTOCALL_CONSOLATION", "parent_value_code": "AUTOCALL", "display_name": "Autocall consolation", "description": "Autocall with a contractual consolation payoff.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "PHOENIX", "parent_value_code": "AUTOCALL", "display_name": "Phoenix", "description": "Autocall archetype with conditional coupon observations, potentially including memory.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "ATHENA", "parent_value_code": "AUTOCALL", "display_name": "Athena", "description": "Autocall archetype with contingent coupon and maturity payoff mechanics.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "VANILLA_SPREAD_KIP", "parent_value_code": None, "display_name": "Vanilla spread with KIP", "description": "Composed option template with two signed vanilla option legs and a separate maturity knock-in put component.", "status": "ACTIVE", "sort_order": 55},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "VANILLA_KIP", "parent_value_code": None, "display_name": "Vanilla with KIP", "description": "Composed option template with one vanilla option payoff and a separate maturity knock-in put component.", "status": "ACTIVE", "sort_order": 56},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "DIGITAL_KIP", "parent_value_code": None, "display_name": "Digital with KIP", "description": "Composed option template with one digital payout and a separate maturity knock-in put component.", "status": "ACTIVE", "sort_order": 57},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "TRACKER", "parent_value_code": None, "display_name": "Tracker", "description": "Structured product with participation in underlying performance.", "status": "ACTIVE", "sort_order": 60},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "SUPERTRACKER", "parent_value_code": "TRACKER", "display_name": "Supertracker", "description": "Leveraged tracker with participation and potential cap mechanics.", "status": "ACTIVE", "sort_order": 70},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "RANGE_ACCRUAL", "parent_value_code": None, "display_name": "Range accrual", "description": "Structured product whose accrual depends on observations remaining in a range.", "status": "ACTIVE", "sort_order": 80},
    {"taxonomy_code": "STRUCTURED_PRODUCT_ARCHETYPE", "value_code": "CAPITAL_PROTECTED", "parent_value_code": None, "display_name": "Capital protected", "description": "Structured product with a stated capital-protection mechanism.", "status": "ACTIVE", "sort_order": 90},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "EQUITY", "parent_value_code": None, "display_name": "Equity", "description": "Index primarily representing equity securities or equity performance.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "FIXED_INCOME", "parent_value_code": None, "display_name": "Fixed income", "description": "Index primarily representing bonds or other fixed-income instruments.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "COMMODITY", "parent_value_code": None, "display_name": "Commodity", "description": "Index primarily representing commodities or commodity futures.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "CURRENCY", "parent_value_code": None, "display_name": "Currency", "description": "Index measuring a currency or currency basket.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "VOLATILITY", "parent_value_code": None, "display_name": "Volatility", "description": "Index measuring implied or realised volatility.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "MULTI_ASSET", "parent_value_code": None, "display_name": "Multi-asset", "description": "Index combining more than one asset class.", "status": "ACTIVE", "sort_order": 60},
    {"taxonomy_code": "INDEX_ASSET_CLASS", "value_code": "DIGITAL_ASSET", "parent_value_code": None, "display_name": "Digital asset", "description": "Index representing one or more cryptoassets or digital assets.", "status": "ACTIVE", "sort_order": 70},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "value_code": "GLOBAL", "parent_value_code": None, "display_name": "Global", "description": "Broad global market scope.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "value_code": "UNITED_STATES", "parent_value_code": None, "display_name": "United States", "description": "United States market scope.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "value_code": "EUROPE", "parent_value_code": None, "display_name": "Europe", "description": "European market scope.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "value_code": "UNITED_KINGDOM", "parent_value_code": "EUROPE", "display_name": "United Kingdom", "description": "United Kingdom market scope.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_GEOGRAPHY", "value_code": "EMERGING_MARKETS", "parent_value_code": None, "display_name": "Emerging markets", "description": "Emerging-market scope.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "INDEX_SCOPE", "value_code": "BROAD_MARKET", "parent_value_code": None, "display_name": "Broad market", "description": "Broad universe intended to represent a market or asset class.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_SCOPE", "value_code": "SECTOR", "parent_value_code": None, "display_name": "Sector", "description": "Universe restricted to an economic or industry sector.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_SCOPE", "value_code": "SINGLE_ASSET", "parent_value_code": None, "display_name": "Single asset", "description": "Index focused on one asset or reference instrument.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_SCOPE", "value_code": "THEMATIC", "parent_value_code": None, "display_name": "Thematic", "description": "Universe selected around a theme or structural trend.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_SCOPE", "value_code": "CUSTOM_BASKET", "parent_value_code": None, "display_name": "Custom basket", "description": "Defined basket or bespoke index universe.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "INDEX_SIZE", "value_code": "LARGE_CAP", "parent_value_code": None, "display_name": "Large cap", "description": "Large-capitalisation issuer segment.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_SIZE", "value_code": "MID_CAP", "parent_value_code": None, "display_name": "Mid cap", "description": "Mid-capitalisation issuer segment.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_SIZE", "value_code": "SMALL_CAP", "parent_value_code": None, "display_name": "Small cap", "description": "Small-capitalisation issuer segment.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_SIZE", "value_code": "ALL_CAP", "parent_value_code": None, "display_name": "All cap", "description": "Mixed or all-capitalisation universe.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "MARKET_CAP_WEIGHTED", "parent_value_code": None, "display_name": "Market-cap weighted", "description": "Constituents weighted by market capitalisation or a related float-adjusted measure.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "EQUAL_WEIGHTED", "parent_value_code": None, "display_name": "Equal weighted", "description": "Constituents receive equal or near-equal target weights.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "FACTOR", "parent_value_code": None, "display_name": "Factor", "description": "Index targeting one or more systematic factors.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "DIVIDEND", "parent_value_code": None, "display_name": "Dividend", "description": "Index constructed around dividend characteristics.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "ESG", "parent_value_code": None, "display_name": "ESG", "description": "Index incorporating environmental, social, or governance criteria.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "VOLATILITY_CONTROL", "parent_value_code": None, "display_name": "Volatility control", "description": "Index targeting or controlling realised portfolio volatility.", "status": "ACTIVE", "sort_order": 60},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "INVERSE", "parent_value_code": None, "display_name": "Inverse", "description": "Index designed to provide inverse exposure to a reference return.", "status": "ACTIVE", "sort_order": 70},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "LEVERAGED", "parent_value_code": None, "display_name": "Leveraged", "description": "Index designed to provide leveraged exposure to a reference return.", "status": "ACTIVE", "sort_order": 80},
    {"taxonomy_code": "INDEX_STRATEGY", "value_code": "QIS", "parent_value_code": None, "display_name": "Quantitative investment strategy", "description": "Rules-based proprietary or quantitative investment strategy index.", "status": "ACTIVE", "sort_order": 90},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "value_code": "BENCHMARK", "parent_value_code": None, "display_name": "Benchmark", "description": "Index used as a performance or market benchmark.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "value_code": "INVESTABLE", "parent_value_code": None, "display_name": "Investable", "description": "Index designed to support investable products or replication.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "value_code": "REFERENCE", "parent_value_code": None, "display_name": "Reference", "description": "Reference index used for analytics, contracts, or product terms.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "value_code": "CUSTOM", "parent_value_code": None, "display_name": "Custom", "description": "Client-specific or bespoke index definition.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_BENCHMARK_ROLE", "value_code": "PROPRIETARY", "parent_value_code": None, "display_name": "Proprietary", "description": "Index administered or defined as a proprietary strategy.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "INDEX_SECTOR", "value_code": "BROAD_SECTOR", "parent_value_code": None, "display_name": "Broad sector", "description": "Sector-level classification without a narrower industry value.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "INDEX_SECTOR", "value_code": "ENERGY", "parent_value_code": "BROAD_SECTOR", "display_name": "Energy", "description": "Energy sector exposure.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "INDEX_SECTOR", "value_code": "FINANCIALS", "parent_value_code": "BROAD_SECTOR", "display_name": "Financials", "description": "Financials sector exposure.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "INDEX_SECTOR", "value_code": "TECHNOLOGY", "parent_value_code": "BROAD_SECTOR", "display_name": "Technology", "description": "Technology sector exposure.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "INDEX_SECTOR", "value_code": "HEALTHCARE", "parent_value_code": "BROAD_SECTOR", "display_name": "Healthcare", "description": "Healthcare sector exposure.", "status": "ACTIVE", "sort_order": 50},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "value_code": "ETF", "parent_value_code": None, "display_name": "Exchange-traded fund", "description": "Fund or fund share class traded on a venue.", "status": "ACTIVE", "sort_order": 10},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "value_code": "ETC", "parent_value_code": None, "display_name": "Exchange-traded commodity", "description": "Commodity-linked exchange-traded security or certificate.", "status": "ACTIVE", "sort_order": 20},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "value_code": "ETN", "parent_value_code": None, "display_name": "Exchange-traded note", "description": "Debt note linked to a reference index or asset.", "status": "ACTIVE", "sort_order": 30},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "value_code": "ETV", "parent_value_code": None, "display_name": "Exchange-traded vehicle", "description": "Other exchange-traded investment vehicle.", "status": "ACTIVE", "sort_order": 40},
    {"taxonomy_code": "EXCHANGE_TRADED_PRODUCT_CLASS", "value_code": "ETI", "parent_value_code": None, "display_name": "Exchange-traded instrument", "description": "Broader exchange-traded certificate or instrument category.", "status": "ACTIVE", "sort_order": 50},
)

SERIES_MEASURE_DEFINITION_SEEDS: Sequence[dict[str, Any]] = (
    {"measure_code": "PRICE", "display_name": "Price", "description": "Tradable or evaluated unit price; period performance is normally expressed as a relative return.", "unit_type": "CURRENCY_PRICE", "default_change_method": "RELATIVE_RETURN", "change_display_unit": "PERCENT", "display_decimal_places": 4, "change_decimal_places": 4, "status": "ACTIVE", "sort_order": 10},
    {"measure_code": "FX_RATE", "display_name": "FX rate", "description": "Quote-currency amount per base-currency unit under the series quote convention; movement is normally expressed as a relative return.", "unit_type": "CURRENCY_PRICE", "default_change_method": "RELATIVE_RETURN", "change_display_unit": "PERCENT", "display_decimal_places": 6, "change_decimal_places": 4, "status": "ACTIVE", "sort_order": 20},
    {"measure_code": "INDEX_LEVEL", "display_name": "Index level", "description": "Published price, total-return, or excess-return index level; movement is normally expressed as a relative return.", "unit_type": "INDEX_POINTS", "default_change_method": "RELATIVE_RETURN", "change_display_unit": "PERCENT", "display_decimal_places": 4, "change_decimal_places": 4, "status": "ACTIVE", "sort_order": 30},
    {"measure_code": "NAV", "display_name": "Net asset value", "description": "Fund or share-class net asset value per unit; movement is normally expressed as a relative return.", "unit_type": "CURRENCY_PRICE", "default_change_method": "RELATIVE_RETURN", "change_display_unit": "PERCENT", "display_decimal_places": 6, "change_decimal_places": 4, "status": "ACTIVE", "sort_order": 40},
    {"measure_code": "IMPLIED_VOLATILITY", "display_name": "Implied volatility", "description": "Implied-volatility quote stored as percent, where 19.00 represents 19 percent; movement is normally an absolute volatility-point change.", "unit_type": "PERCENT", "default_change_method": "ABSOLUTE_CHANGE", "change_display_unit": "VOLATILITY_POINTS", "display_decimal_places": 4, "change_decimal_places": 4, "status": "ACTIVE", "sort_order": 50},
    {"measure_code": "YIELD", "display_name": "Yield", "description": "Yield quote stored as percent; movement is normally expressed in basis points.", "unit_type": "PERCENT", "default_change_method": "BASIS_POINT_CHANGE", "change_display_unit": "BASIS_POINTS", "display_decimal_places": 6, "change_decimal_places": 2, "status": "ACTIVE", "sort_order": 60},
    {"measure_code": "RATE", "display_name": "Rate", "description": "Interest or zero rate stored as percent; movement is normally expressed in basis points unless the series is an FX rate.", "unit_type": "PERCENT", "default_change_method": "BASIS_POINT_CHANGE", "change_display_unit": "BASIS_POINTS", "display_decimal_places": 6, "change_decimal_places": 2, "status": "ACTIVE", "sort_order": 70},
    {"measure_code": "CREDIT_SPREAD", "display_name": "Credit spread", "description": "Credit, option-adjusted, or similar spread quoted in basis points; movement is normally expressed in basis points.", "unit_type": "BASIS_POINTS", "default_change_method": "BASIS_POINT_CHANGE", "change_display_unit": "BASIS_POINTS", "display_decimal_places": 2, "change_decimal_places": 2, "status": "ACTIVE", "sort_order": 80},
    {"measure_code": "VOLUME", "display_name": "Volume", "description": "Trading volume or turnover quantity; movement is normally expressed as an absolute unit change.", "unit_type": "QUANTITY", "default_change_method": "ABSOLUTE_CHANGE", "change_display_unit": "UNITS", "display_decimal_places": 0, "change_decimal_places": 0, "status": "ACTIVE", "sort_order": 90},
    {"measure_code": "OPEN_INTEREST", "display_name": "Open interest", "description": "Open derivative contract count; movement is normally expressed as an absolute unit change.", "unit_type": "QUANTITY", "default_change_method": "ABSOLUTE_CHANGE", "change_display_unit": "UNITS", "display_decimal_places": 0, "change_decimal_places": 0, "status": "ACTIVE", "sort_order": 100},
    {"measure_code": "MONETARY_VALUE", "display_name": "Monetary value", "description": "Trade-specific or position-specific monetary value or MTM; movement is normally expressed as a monetary amount, not a percentage return.", "unit_type": "CURRENCY_AMOUNT", "default_change_method": "MONETARY_CHANGE", "change_display_unit": "CURRENCY_AMOUNT", "display_decimal_places": 2, "change_decimal_places": 2, "status": "ACTIVE", "sort_order": 110},
)


OPERATING_PROFILE_SEEDS: Sequence[dict[str, Any]] = (
    {"profile_code": "FUND_MANAGER", "display_name": "Fund manager", "description": "Manages pooled funds, their share classes, fund operations and fund controls.", "status": "ACTIVE", "sort_order": 10},
    {"profile_code": "TRADING_BOOK_MANAGER", "display_name": "Trading-book manager", "description": "Operates discretionary or client trading books and their trade lifecycle.", "status": "ACTIVE", "sort_order": 20},
    {"profile_code": "AMC_MANAGER", "display_name": "AMC manager", "description": "Manages an actively managed certificate and its associated strategy portfolio.", "status": "ACTIVE", "sort_order": 30},
    {"profile_code": "STRUCTURED_PRODUCT_DISTRIBUTOR", "display_name": "Structured-product distributor", "description": "Distributes structured products and administers related suitability and operational data.", "status": "ACTIVE", "sort_order": 40},
)


PLATFORM_MODULE_SEEDS: Sequence[dict[str, Any]] = (
    {"module_code": "SECURITY_MASTER", "display_name": "Security master", "description": "Governed canonical reference data, instruments, listings and identifiers.", "module_category": "REFERENCE_DATA", "status": "ACTIVE", "sort_order": 10},
    {"module_code": "MARKET_DATA", "display_name": "Market data", "description": "Series, observations, provenance and licensed dataset entitlement.", "module_category": "DATA", "status": "ACTIVE", "sort_order": 20},
    {"module_code": "TRADING", "display_name": "Trading", "description": "Booked economic events, parties, corrections and trade operations.", "module_category": "OPERATIONS", "status": "ACTIVE", "sort_order": 30},
    {"module_code": "VALUATION", "display_name": "Valuation", "description": "Valuation policy, frozen inputs, NAV calculations and reproducibility evidence.", "module_category": "VALUATION", "status": "ACTIVE", "sort_order": 40},
    {"module_code": "FUND_MANAGEMENT", "display_name": "Fund management", "description": "Fund vehicles, share classes and manager-specific configuration.", "module_category": "FUND", "status": "ACTIVE", "sort_order": 50},
    {"module_code": "FUND_OPERATIONS", "display_name": "Fund operations", "description": "Fund operational mappings, administrator feeds and NAV workflows.", "module_category": "FUND", "status": "ACTIVE", "sort_order": 60},
    {"module_code": "UCITS_CONTROLS", "display_name": "UCITS controls", "description": "UCITS control policies, evidence and breach workflow.", "module_category": "FUND", "status": "ACTIVE", "sort_order": 70},
    {"module_code": "AMC_MANAGEMENT", "display_name": "AMC management", "description": "Actively managed certificate strategy and operational configuration.", "module_category": "STRUCTURED_PRODUCTS", "status": "ACTIVE", "sort_order": 80},
    {"module_code": "STRUCTURED_PRODUCTS", "display_name": "Structured products", "description": "Structured-product terms, components, barriers and schedules.", "module_category": "STRUCTURED_PRODUCTS", "status": "ACTIVE", "sort_order": 90},
    {"module_code": "STRUCTURED_PRODUCT_DISTRIBUTION", "display_name": "Structured-product distribution", "description": "Distribution workflow, client linkage and chargeable service operations.", "module_category": "STRUCTURED_PRODUCTS", "status": "ACTIVE", "sort_order": 100},
)


OPERATING_PROFILE_MODULE_RECOMMENDATIONS: Sequence[tuple[str, str, str, str]] = (
    ("FUND_MANAGER", "SECURITY_MASTER", "CORE", "Fund master data is a prerequisite for fund operations."),
    ("FUND_MANAGER", "MARKET_DATA", "CORE", "Fund valuation needs governed market data."),
    ("FUND_MANAGER", "TRADING", "STANDARD", "Fund managers commonly need economic trade booking."),
    ("FUND_MANAGER", "VALUATION", "CORE", "Fund workflows need reproducible valuation runs."),
    ("FUND_MANAGER", "FUND_MANAGEMENT", "CORE", "Fund vehicle and share-class configuration is required."),
    ("FUND_MANAGER", "FUND_OPERATIONS", "CORE", "Administrator and custodian operating mappings are required."),
    ("FUND_MANAGER", "UCITS_CONTROLS", "OPTIONAL", "Applicable where the tenant operates UCITS products."),
    ("TRADING_BOOK_MANAGER", "SECURITY_MASTER", "CORE", "Trading requires governed economic instruments and listings."),
    ("TRADING_BOOK_MANAGER", "MARKET_DATA", "CORE", "Trading and valuation require observable market data."),
    ("TRADING_BOOK_MANAGER", "TRADING", "CORE", "Trade booking is the principal workflow."),
    ("TRADING_BOOK_MANAGER", "VALUATION", "STANDARD", "Valuation is commonly needed for position monitoring."),
    ("AMC_MANAGER", "SECURITY_MASTER", "CORE", "AMC references and underlying instruments require canonical identity."),
    ("AMC_MANAGER", "MARKET_DATA", "CORE", "AMC valuation needs governed market data."),
    ("AMC_MANAGER", "TRADING", "CORE", "AMC portfolio activity is recorded as trade events."),
    ("AMC_MANAGER", "VALUATION", "CORE", "AMC workflows need reproducible valuation runs."),
    ("AMC_MANAGER", "AMC_MANAGEMENT", "CORE", "AMC-specific configuration is required."),
    ("AMC_MANAGER", "STRUCTURED_PRODUCTS", "STANDARD", "AMCs can use structured-product modelling where relevant."),
    ("STRUCTURED_PRODUCT_DISTRIBUTOR", "SECURITY_MASTER", "CORE", "Distribution needs a governed product identity."),
    ("STRUCTURED_PRODUCT_DISTRIBUTOR", "MARKET_DATA", "STANDARD", "Distribution workflows may need product market data."),
    ("STRUCTURED_PRODUCT_DISTRIBUTOR", "STRUCTURED_PRODUCTS", "CORE", "Product economics and schedules need structured-product models."),
    ("STRUCTURED_PRODUCT_DISTRIBUTOR", "STRUCTURED_PRODUCT_DISTRIBUTION", "CORE", "Distribution workflow is the primary capability."),
)


def seed_defaults(connection: Connection) -> None:
    """Insert baseline governed catalogues without overwriting existing local decisions."""

    connection.execute(
        insert(day_count_convention)
        .values(list(DAY_COUNT_CONVENTION_SEEDS))
        .on_conflict_do_nothing(index_elements=[day_count_convention.c.code])
    )
    # Backfill the additive FK for legacy/demo rows without changing their
    # retained source text.  Unknown provider text remains unresolved.
    connection.execute(
        update(bond_terms)
        .where(bond_terms.c.day_count_convention_id.is_(None))
        .where(bond_terms.c.day_count_convention.is_not(None))
        .values(
            day_count_convention_id=(
                select(day_count_convention.c.day_count_convention_id)
                .where(day_count_convention.c.code == bond_terms.c.day_count_convention)
                .where(day_count_convention.c.status == "ACTIVE")
                .scalar_subquery()
            )
        )
    )
    connection.execute(
        update(fee_rule)
        .where(fee_rule.c.day_count_convention_id.is_(None))
        .where(fee_rule.c.day_count_convention.is_not(None))
        .values(
            day_count_convention_id=(
                select(day_count_convention.c.day_count_convention_id)
                .where(day_count_convention.c.code == fee_rule.c.day_count_convention)
                .where(day_count_convention.c.status == "ACTIVE")
                .scalar_subquery()
            )
        )
    )
    connection.execute(
        insert(reference_node_type)
        .values(list(REFERENCE_NODE_TYPE_SEEDS))
        .on_conflict_do_nothing(index_elements=[reference_node_type.c.type_code])
    )
    connection.execute(
        insert(series_measure_definition)
        .values(list(SERIES_MEASURE_DEFINITION_SEEDS))
        .on_conflict_do_nothing(index_elements=[series_measure_definition.c.measure_code])
    )
    connection.execute(
        insert(operating_profile)
        .values(list(OPERATING_PROFILE_SEEDS))
        .on_conflict_do_nothing(index_elements=[operating_profile.c.profile_code])
    )
    connection.execute(
        insert(platform_module)
        .values(list(PLATFORM_MODULE_SEEDS))
        .on_conflict_do_nothing(index_elements=[platform_module.c.module_code])
    )
    profile_id_by_code = dict(
        connection.execute(select(operating_profile.c.profile_code, operating_profile.c.operating_profile_id)).tuples().all()
    )
    module_id_by_code = dict(
        connection.execute(select(platform_module.c.module_code, platform_module.c.platform_module_id)).tuples().all()
    )
    recommendation_payloads = [
        {
            "operating_profile_id": profile_id_by_code[profile_code],
            "platform_module_id": module_id_by_code[module_code],
            "recommendation_strength": strength,
            "rationale": rationale,
            "status": "ACTIVE",
        }
        for profile_code, module_code, strength, rationale in OPERATING_PROFILE_MODULE_RECOMMENDATIONS
    ]
    connection.execute(
        insert(operating_profile_module_recommendation)
        .values(recommendation_payloads)
        .on_conflict_do_nothing(
            index_elements=[
                operating_profile_module_recommendation.c.operating_profile_id,
                operating_profile_module_recommendation.c.platform_module_id,
            ]
        )
    )
    connection.execute(
        insert(return_profile)
        .values(list(RETURN_PROFILE_SEEDS))
        .on_conflict_do_nothing(index_elements=[return_profile.c.profile_code])
    )
    connection.execute(
        insert(index_kind_catalogue)
        .values(list(INDEX_KIND_CATALOGUE_SEEDS))
        .on_conflict_do_nothing(index_elements=[index_kind_catalogue.c.index_kind_code])
    )
    connection.execute(
        insert(crypto_network)
        .values(list(CRYPTO_NETWORK_SEEDS))
        .on_conflict_do_nothing(index_elements=[crypto_network.c.network_code])
    )
    connection.execute(
        insert(identifier_scheme)
        .values(list(IDENTIFIER_SCHEME_SEEDS))
        .on_conflict_do_nothing(index_elements=[identifier_scheme.c.scheme_code])
    )
    connection.execute(
        insert(instrument_type)
        .values(list(INSTRUMENT_TYPE_SEEDS))
        .on_conflict_do_nothing(index_elements=[instrument_type.c.type_code])
    )
    connection.execute(
        insert(taxonomy)
        .values(list(TAXONOMY_SEEDS))
        .on_conflict_do_nothing(index_elements=[taxonomy.c.taxonomy_code])
    )

    taxonomy_id_by_code = dict(
        connection.execute(select(taxonomy.c.taxonomy_code, taxonomy.c.taxonomy_id)).tuples().all()
    )
    root_values = [row for row in TAXONOMY_VALUE_SEEDS if row["parent_value_code"] is None]
    child_values = [row for row in TAXONOMY_VALUE_SEEDS if row["parent_value_code"] is not None]

    for seed_rows, needs_parent in ((root_values, False), (child_values, True)):
        value_id_by_business_key = {
            (row.taxonomy_id, row.value_code): row.taxonomy_value_id
            for row in connection.execute(
                select(taxonomy_value.c.taxonomy_id, taxonomy_value.c.value_code, taxonomy_value.c.taxonomy_value_id)
            ).mappings()
        }
        payloads = []
        for row in seed_rows:
            payload = {key: value for key, value in row.items() if key not in {"taxonomy_code", "parent_value_code"}}
            payload["taxonomy_id"] = taxonomy_id_by_code[row["taxonomy_code"]]
            if needs_parent:
                payload["parent_taxonomy_value_id"] = value_id_by_business_key[(payload["taxonomy_id"], row["parent_value_code"])]
            payloads.append(payload)
        connection.execute(
            insert(taxonomy_value)
            .values(payloads)
            .on_conflict_do_nothing(index_elements=[taxonomy_value.c.taxonomy_id, taxonomy_value.c.value_code])
        )
