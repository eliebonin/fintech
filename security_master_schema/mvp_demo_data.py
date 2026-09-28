"""Synthetic two-year market-data and portfolio fixture for the local MVP.

The fixture is deliberately deterministic and idempotent.  It provides enough
realistic provenance and cut-off variation to exercise the resolver and the
console without pretending that the values are production market data.
"""

from datetime import date, datetime, time, timedelta, timezone
import json
from random import Random
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, bindparam, select, update
from sqlalchemy.dialects.postgresql import insert

from . import models as m
from .demo_data import DEMO_IDS
from .seed_data import seed_defaults


MVP_NAMESPACE = UUID("4e0f7b3f-1e34-4b8c-98ad-5e6e27e23a12")
MVP_START_DATE = date(2024, 9, 2)
MVP_END_DATE = date(2026, 8, 28)
MVP_CLOSED_DATES = frozenset((date(2024, 12, 25), date(2025, 12, 25), date(2026, 1, 1)))


def _id(key: str) -> UUID:
    return uuid5(MVP_NAMESPACE, key)


def _insert_once(connection: Connection, table, values: dict) -> None:
    connection.execute(insert(table).values(values).on_conflict_do_nothing())


def _insert_many(connection: Connection, table, rows: list[dict], chunk_size: int = 400) -> None:
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        if chunk:
            connection.execute(insert(table).values(chunk).on_conflict_do_nothing())


def _business_dates(calendar_key: str) -> list[date]:
    """Return expected open dates for the synthetic calendar contract."""
    result: list[date] = []
    current = MVP_START_DATE
    while current <= MVP_END_DATE:
        if current.weekday() < 5 and (calendar_key == "mvp_fx_calendar" or current not in MVP_CLOSED_DATES):
            result.append(current)
        current += timedelta(days=1)
    return result


def _catalogue_id(connection: Connection, table, code_column, code: str):
    return connection.execute(select(table.primary_key.columns.values()[0]).where(code_column == code)).scalar_one()


def _local_close(day: date, timezone_name: str, hour: int = 16, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)


def _provider_id_for_dataset(dataset_key: str) -> UUID:
    return {
        "mvp_bloomberg_dataset": DEMO_IDS["mvp_bloomberg_provider"],
        "mvp_yahoo_dataset": DEMO_IDS["mvp_yahoo_provider"],
        "mvp_lseg_dataset": DEMO_IDS["mvp_lseg_provider"],
    }[dataset_key]


def _vintage_id(dataset_key: str, day: date) -> UUID:
    return _id(f"vintage:{dataset_key}:{day.isoformat()}")


def _provider_rows() -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    providers = [
        {"data_provider_id": DEMO_IDS["mvp_bloomberg_provider"], "organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "provider_code": "BLOOMBERG_MOCK", "display_name": "Bloomberg (synthetic)", "status": "ACTIVE"},
        {"data_provider_id": DEMO_IDS["mvp_yahoo_provider"], "organisation_id": DEMO_IDS["mvp_yahoo_organisation"], "provider_code": "YAHOO_FINANCE_MOCK", "display_name": "Yahoo Finance (synthetic)", "status": "ACTIVE"},
        {"data_provider_id": DEMO_IDS["mvp_lseg_provider"], "organisation_id": DEMO_IDS["lseg_organisation"], "provider_code": "LSEG_MOCK", "display_name": "LSEG (synthetic)", "status": "ACTIVE"},
    ]
    products = [
        {"provider_product_id": DEMO_IDS["mvp_bloomberg_product"], "data_provider_id": DEMO_IDS["mvp_bloomberg_provider"], "product_code": "EOD_MARKET_DATA", "display_name": "Bloomberg EOD market data", "description": "Synthetic end-of-day and FX cut observations.", "status": "ACTIVE"},
        {"provider_product_id": DEMO_IDS["mvp_yahoo_product"], "data_provider_id": DEMO_IDS["mvp_yahoo_provider"], "product_code": "PUBLIC_EOD", "display_name": "Yahoo public EOD", "description": "Synthetic public-reference observations for the MVP.", "status": "ACTIVE"},
        {"provider_product_id": DEMO_IDS["mvp_lseg_product"], "data_provider_id": DEMO_IDS["mvp_lseg_provider"], "product_code": "REFERENCE_EOD", "display_name": "LSEG reference EOD", "description": "Synthetic reference and evaluated-price observations.", "status": "ACTIVE"},
    ]
    datasets = [
        {"dataset_id": DEMO_IDS["mvp_bloomberg_dataset"], "provider_product_id": DEMO_IDS["mvp_bloomberg_product"], "dataset_code": "BBG_MVP_MULTI_ASSET_EOD", "display_name": "Bloomberg multi-asset EOD (synthetic)", "data_domain": "MARKET_DATA", "coverage_description": "US and European securities plus cut-specific FX.", "delivery_channel": "API", "status": "ACTIVE", "valid_from": MVP_START_DATE},
        {"dataset_id": DEMO_IDS["mvp_yahoo_dataset"], "provider_product_id": DEMO_IDS["mvp_yahoo_product"], "dataset_code": "YAHOO_MVP_EQUITIES_EOD", "display_name": "Yahoo equities EOD (synthetic)", "data_domain": "MARKET_DATA", "coverage_description": "Synthetic listed-equity observations.", "delivery_channel": "API", "status": "ACTIVE", "valid_from": MVP_START_DATE},
        {"dataset_id": DEMO_IDS["mvp_lseg_dataset"], "provider_product_id": DEMO_IDS["mvp_lseg_product"], "dataset_code": "LSEG_MVP_REFERENCE_EOD", "display_name": "LSEG reference EOD (synthetic)", "data_domain": "MARKET_DATA", "coverage_description": "Synthetic futures, bonds, and FX observations.", "delivery_channel": "FILE", "status": "ACTIVE", "valid_from": MVP_START_DATE},
    ]
    licences = [
        {"data_licence_id": DEMO_IDS["mvp_bloomberg_licence"], "licensor_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "licensee_organisation_id": DEMO_IDS["fortem_organisation"], "licence_code": "MVP_BBG_INTERNAL", "display_name": "Bloomberg internal-use mock licence", "permitted_use_description": "Synthetic fixture only; internal valuation and test use.", "status": "ACTIVE", "valid_from": MVP_START_DATE},
        {"data_licence_id": DEMO_IDS["mvp_yahoo_licence"], "licensor_organisation_id": DEMO_IDS["mvp_yahoo_organisation"], "licensee_organisation_id": DEMO_IDS["fortem_organisation"], "licence_code": "MVP_YAHOO_INTERNAL", "display_name": "Yahoo internal-use mock licence", "permitted_use_description": "Synthetic fixture only; internal valuation and test use.", "status": "ACTIVE", "valid_from": MVP_START_DATE},
        {"data_licence_id": DEMO_IDS["mvp_lseg_licence"], "licensor_organisation_id": DEMO_IDS["lseg_organisation"], "licensee_organisation_id": DEMO_IDS["fortem_organisation"], "licence_code": "MVP_LSEG_INTERNAL", "display_name": "LSEG internal-use mock licence", "permitted_use_description": "Synthetic fixture only; internal valuation and test use.", "status": "ACTIVE", "valid_from": MVP_START_DATE},
    ]
    assignments = [
        {"dataset_licence_assignment_id": _id(f"assignment:{dataset['dataset_code']}"), "dataset_id": dataset["dataset_id"], "data_licence_id": licence["data_licence_id"], "licence_role": "INTERNAL_USE", "valid_from": MVP_START_DATE, "status": "ACTIVE"}
        for dataset, licence in zip(datasets, licences)
    ]
    entitlements = [
        {"tenant_dataset_entitlement_id": _id(f"entitlement:{dataset['dataset_code']}"), "tenant_id": DEMO_IDS["tenant"], "dataset_id": dataset["dataset_id"], "dataset_licence_assignment_id": assignment["dataset_licence_assignment_id"], "use_purpose": "VALUATION", "status": "ACTIVE", "valid_from": MVP_START_DATE}
        for dataset, assignment in zip(datasets, assignments)
    ]
    return providers, products, datasets, licences, assignments, entitlements


def _add_instruments(connection: Connection, node_instrument, node_listing, future_type, equity_type, bond_type, fx_forward_type) -> None:
    today = MVP_END_DATE
    day_count_convention_id = _catalogue_id(connection, m.day_count_convention, m.day_count_convention.c.code, "ACT_ACT_ICMA")
    rows = [
        ("mvp_us_equity_node", "MVP US Technology Equity", "MVP_US_TECH_EQUITY", equity_type, "EQUITY", DEMO_IDS["usd_currency"]),
        ("mvp_eu_equity_node", "MVP European Industrials Equity", "MVP_EU_INDUSTRIALS_EQUITY", equity_type, "EQUITY", DEMO_IDS["eur_currency"]),
        ("mvp_us_bond_node", "MVP US Corporate 4.00% 2030", "MVP_US_CORP_2030", bond_type, "FIXED_INCOME", DEMO_IDS["usd_currency"]),
        ("mvp_eu_bond_node", "MVP German Government 2.50% 2031", "MVP_DE_GOV_2031", bond_type, "FIXED_INCOME", DEMO_IDS["eur_currency"]),
        ("mvp_future_dec_node", "MVP Euro Stoxx Future Dec-2025", "MVP_ESTX_202512", future_type, "FUTURES", DEMO_IDS["eur_currency"]),
        ("mvp_future_mar_node", "MVP Euro Stoxx Future Mar-2026", "MVP_ESTX_202603", future_type, "FUTURES", DEMO_IDS["eur_currency"]),
        ("mvp_fx_forward_instrument", "MVP GBP/USD 3M Forward", "MVP_FXFWD_GBPUSD_202512", fx_forward_type, "FX", DEMO_IDS["usd_currency"]),
    ]
    for key, name, code, type_id, asset_class, currency_id in rows:
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS[key], "reference_node_type_id": node_instrument, "canonical_name": name, "internal_code": code, "status": "ACTIVE", "is_tradable": True})
        issuer = DEMO_IDS["hsbc_organisation"] if "bond" in key else None
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS[key], "instrument_type_id": type_id, "asset_class": asset_class, "issuer_organisation_id": issuer, "base_currency_id": currency_id, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})

    for node_key, date_key, maturity in (("mvp_us_bond_node", "mvp_us_bond_dates", date(2030, 9, 15)), ("mvp_eu_bond_node", "mvp_eu_bond_dates", date(2031, 7, 4))):
        _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS[date_key], "instrument_node_id": DEMO_IDS[node_key], "issue_date": MVP_START_DATE, "maturity_date": maturity, "final_settlement_date": maturity + timedelta(days=2)})
    _insert_once(connection, m.bond_terms, {"bond_terms_id": DEMO_IDS["mvp_us_bond_terms"], "instrument_node_id": DEMO_IDS["mvp_us_bond_node"], "issue_currency_id": DEMO_IDS["usd_currency"], "par_amount": 100, "coupon_type": "FIXED", "coupon_rate": 0.04, "coupon_frequency_per_year": 2, "day_count_convention_id": day_count_convention_id, "day_count_convention": "ACT_ACT_ICMA", "redemption_amount_per_par": 100, "quotation_basis": "PCT_OF_PAR", "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})
    _insert_once(connection, m.bond_terms, {"bond_terms_id": DEMO_IDS["mvp_eu_bond_terms"], "instrument_node_id": DEMO_IDS["mvp_eu_bond_node"], "issue_currency_id": DEMO_IDS["eur_currency"], "par_amount": 100, "coupon_type": "FIXED", "coupon_rate": 0.025, "coupon_frequency_per_year": 2, "day_count_convention_id": day_count_convention_id, "day_count_convention": "ACT_ACT_ICMA", "redemption_amount_per_par": 100, "quotation_basis": "PCT_OF_PAR", "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})
    _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["mvp_future_dec_dates"] if "mvp_future_dec_dates" in DEMO_IDS else _id("dates:future-dec"), "instrument_node_id": DEMO_IDS["mvp_future_dec_node"], "last_trading_date": date(2025, 12, 19), "expiry_date": date(2025, 12, 19), "final_settlement_date": date(2025, 12, 22)})
    _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["mvp_future_mar_dates"] if "mvp_future_mar_dates" in DEMO_IDS else _id("dates:future-mar"), "instrument_node_id": DEMO_IDS["mvp_future_mar_node"], "last_trading_date": date(2026, 3, 20), "expiry_date": date(2026, 3, 20), "final_settlement_date": date(2026, 3, 23)})
    _insert_once(connection, m.future_terms, {"instrument_node_id": DEMO_IDS["mvp_future_dec_node"], "future_family_id": DEMO_IDS["mvp_future_family"], "contract_month": date(2025, 12, 19), "last_trade_date": date(2025, 12, 19), "settlement_method": "CASH"})
    _insert_once(connection, m.future_terms, {"instrument_node_id": DEMO_IDS["mvp_future_mar_node"], "future_family_id": DEMO_IDS["mvp_future_family"], "contract_month": date(2026, 3, 20), "last_trade_date": date(2026, 3, 20), "settlement_method": "CASH"})
    _insert_once(connection, m.fx_forward_terms, {"instrument_node_id": DEMO_IDS["mvp_fx_forward_instrument"], "base_currency_id": DEMO_IDS["gbp_currency"], "quote_currency_id": DEMO_IDS["usd_currency"], "quote_convention": "USD_PER_GBP", "agreed_forward_rate": 1.2745, "settlement_type": "DELIVERABLE"})
    _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["mvp_fx_forward_dates"], "instrument_node_id": DEMO_IDS["mvp_fx_forward_instrument"], "effective_date": MVP_START_DATE, "maturity_date": date(2025, 12, 19), "settlement_date": date(2025, 12, 22), "final_settlement_date": date(2025, 12, 22)})

    listings = [
        ("mvp_us_equity_listing", "mvp_us_equity_node", DEMO_IDS["mvp_nyse_venue"], DEMO_IDS["usd_currency"], "MUST", 1, 1),
        ("mvp_eu_equity_listing", "mvp_eu_equity_node", DEMO_IDS["mvp_xetr_venue"], DEMO_IDS["eur_currency"], "MEUR", 1, 1),
        ("mvp_future_dec_listing", "mvp_future_dec_node", DEMO_IDS["mvp_xetr_venue"], DEMO_IDS["eur_currency"], "ESTXU5", 1, 10),
        ("mvp_future_mar_listing", "mvp_future_mar_node", DEMO_IDS["mvp_xetr_venue"], DEMO_IDS["eur_currency"], "ESTXH6", 1, 10),
    ]
    for listing_key, instrument_key, venue_id, currency_id, symbol, quote_factor, multiplier in listings:
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS[listing_key], "reference_node_type_id": node_listing, "canonical_name": f"{symbol} listed", "internal_code": f"{symbol}_MVP", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.listing, {"listing_node_id": DEMO_IDS[listing_key], "instrument_node_id": DEMO_IDS[instrument_key], "market_venue_id": venue_id, "trading_currency_id": currency_id, "trading_symbol": symbol, "quote_factor": quote_factor, "unit_multiplier": multiplier, "is_primary_listing": True, "effective_from": MVP_START_DATE, "status": "ACTIVE"})

    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_future_family_node"], "reference_node_type_id": _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FUTURE_FAMILY"), "canonical_name": "MVP Euro Stoxx futures family", "internal_code": "MVP_ESTX_FAMILY", "status": "ACTIVE", "is_tradable": False})
    _insert_once(connection, m.future_family, {"future_family_id": DEMO_IDS["mvp_future_family"], "family_node_id": DEMO_IDS["mvp_future_family_node"], "underlying_reference_node_id": DEMO_IDS["mvp_eu_equity_node"], "contract_currency_id": DEMO_IDS["eur_currency"], "expiry_cycle": "QUARTERLY", "status": "ACTIVE"})


def _add_index_reference_data(connection: Connection) -> None:
    """Seed one index family with concrete price- and net-total-return variants."""
    index_node_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "INDEX")
    family_node_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "INDEX_FAMILY")
    price_profile = _catalogue_id(connection, m.return_profile, m.return_profile.c.profile_code, "PRICE_RETURN")
    net_profile = _catalogue_id(connection, m.return_profile, m.return_profile.c.profile_code, "NET_TOTAL_RETURN")

    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_index_family_node"], "reference_node_type_id": family_node_type, "canonical_name": "MVP S&P 500 index family", "internal_code": "MVP_SP500_FAMILY", "status": "ACTIVE", "is_tradable": False})
    _insert_once(connection, m.index_family, {"index_family_id": DEMO_IDS["mvp_index_family"], "family_node_id": DEMO_IDS["mvp_index_family_node"], "provider_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "status": "ACTIVE"})

    variants = (
        ("mvp_sp500_price_index_node", "MVP S&P 500 Price Return", "MVP_SP500_PR", price_profile, "S&P 500 Price Return"),
        ("mvp_sp500_net_index_node", "MVP S&P 500 Net Total Return", "MVP_SP500_NTR", net_profile, "S&P 500 Net Total Return"),
    )
    for node_key, name, code, profile_id, methodology_name in variants:
        node_id = DEMO_IDS[node_key]
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": node_id, "reference_node_type_id": index_node_type, "canonical_name": name, "internal_code": code, "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.index_terms, {"index_node_id": node_id, "index_family_id": DEMO_IDS["mvp_index_family"], "index_kind": "PUBLIC", "return_profile_id": profile_id, "base_currency_id": DEMO_IDS["usd_currency"], "administrator_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "calculation_agent_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "base_date": date(1957, 3, 4), "base_level": 10, "methodology_reference": methodology_name, "status": "ACTIVE"})
        _insert_once(connection, m.index_methodology_version, {"index_methodology_version_id": DEMO_IDS["mvp_sp500_price_methodology"] if "price" in node_key else DEMO_IDS["mvp_sp500_net_methodology"], "index_node_id": node_id, "sequence_no": 1, "effective_from": MVP_START_DATE, "weighting_method": "FLOAT_ADJUSTED_MARKET_CAP", "rebalance_frequency": "QUARTERLY", "calculation_frequency": "BUSINESS_DAILY", "dividend_treatment": methodology_name, "launch_date": date(1957, 3, 4), "is_backtested_history": False, "methodology_document_uri": "synthetic://mvp/sp500/methodology/v1", "status": "APPROVED"})


def _add_crypto_reference_data(connection: Connection, node_instrument, digital_asset_type) -> None:
    """Seed cryptoassets that are also represented as currency roles."""

    networks = {
        code: _catalogue_id(connection, m.crypto_network, m.crypto_network.c.network_code, code)
        for code in ("BITCOIN_MAINNET", "ETHEREUM_MAINNET", "SOLANA_MAINNET")
    }
    assets = (
        ("mvp_btc_node", "Bitcoin", "MVP_BTC", "BTC", "CRYPTOASSET", "NATIVE", "Bitcoin", "mvp_btc_currency", "BITCOIN_MAINNET", None, "NATIVE", None, 8, True, "mvp_btc_terms", "mvp_btc_bitcoin_deployment"),
        ("mvp_usdc_node", "USD Coin", "MVP_USDC", "USDC", "STABLECOIN", "STABLECOIN", "USDC", "mvp_usdc_currency", "ETHEREUM_MAINNET", "0x0000000000000000000000000000000000000abc", "TOKEN_CONTRACT", "ERC20", 6, True, "mvp_usdc_terms", "mvp_usdc_ethereum_deployment"),
    )
    for node_key, name, code, symbol, currency_kind, subtype, protocol, currency_key, network_code, address, deployment_kind, token_standard, decimals, canonical, terms_key, deployment_key in assets:
        node_id = DEMO_IDS[node_key]
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": node_id, "reference_node_type_id": node_instrument, "canonical_name": name, "internal_code": code, "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": node_id, "instrument_type_id": digital_asset_type, "asset_class": "DIGITAL_ASSET", "base_currency_id": None, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.instrument_definition_version, {"instrument_definition_version_id": _id(f"crypto:instrument-version:{node_key}"), "instrument_node_id": node_id, "sequence_no": 1, "instrument_type_id": digital_asset_type, "asset_class": "DIGITAL_ASSET", "effective_from": MVP_START_DATE, "is_current": True, "status": "APPROVED"})
        _insert_once(connection, m.crypto_asset_terms, {"crypto_asset_terms_id": DEMO_IDS[terms_key], "instrument_node_id": node_id, "asset_subtype": subtype, "native_symbol": symbol, "protocol_name": protocol, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1, "status": "ACTIVE"})
        _insert_once(connection, m.currency, {"currency_id": DEMO_IDS[currency_key], "reference_node_id": node_id, "currency_code": symbol, "display_name": name, "minor_unit": decimals, "currency_kind": currency_kind, "status": "ACTIVE"})
        _insert_once(connection, m.crypto_asset_deployment, {"crypto_asset_deployment_id": DEMO_IDS[deployment_key], "instrument_node_id": node_id, "crypto_network_id": networks[network_code], "deployment_kind": deployment_kind, "contract_address": address, "token_standard": token_standard, "on_chain_symbol": symbol, "decimals": decimals, "is_canonical": canonical, "effective_from": MVP_START_DATE, "is_current": True, "status": "ACTIVE"})

    _insert_once(connection, m.crypto_asset_deployment, {"crypto_asset_deployment_id": DEMO_IDS["mvp_usdc_solana_deployment"], "instrument_node_id": DEMO_IDS["mvp_usdc_node"], "crypto_network_id": networks["SOLANA_MAINNET"], "deployment_kind": "TOKEN_CONTRACT", "contract_address": "MVP_USDC_SOLANA_MINT", "token_standard": "SPL", "on_chain_symbol": "USDC", "decimals": 6, "is_canonical": False, "effective_from": MVP_START_DATE, "is_current": True, "status": "ACTIVE"})

    node_listing = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "LISTING")
    listing_rows = (
        ("mvp_btc_coinbase_usd_listing", "mvp_btc_node", DEMO_IDS["coinbase_venue"], DEMO_IDS["usd_currency"], "BTC-USD", "BTC-USD", "BTCUSD", True, 2, 0.01),
        ("mvp_btc_binance_usdc_listing", "mvp_btc_node", DEMO_IDS["binance_venue"], DEMO_IDS["mvp_usdc_currency"], "BTCUSDC", "BTCUSDC", "BTCUSDC", False, 2, 0.01),
        ("mvp_usdc_kraken_usd_listing", "mvp_usdc_node", DEMO_IDS["kraken_venue"], DEMO_IDS["usd_currency"], "USDC/USD", "USDCUSD", "USDCUSD", False, 6, 0.000001),
    )
    for listing_key, instrument_key, venue_id, quote_currency_id, symbol, venue_product_id, fix_security_id, is_primary, display_decimals, tick_size in listing_rows:
        listing_id = DEMO_IDS[listing_key]
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": listing_id, "reference_node_type_id": node_listing, "canonical_name": f"{symbol} venue market", "internal_code": f"{symbol.replace('-', '_').replace('/', '_')}_MVP", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.listing, {"listing_node_id": listing_id, "instrument_node_id": DEMO_IDS[instrument_key], "market_venue_id": venue_id, "trading_currency_id": quote_currency_id, "trading_symbol": symbol, "quote_factor": 1, "unit_multiplier": 1, "is_primary_listing": is_primary, "effective_from": MVP_START_DATE, "status": "ACTIVE"})
        _insert_once(connection, m.listing_definition_version, {"listing_definition_version_id": _id(f"crypto:listing-version:{listing_key}"), "listing_node_id": listing_id, "sequence_no": 1, "market_venue_id": venue_id, "trading_currency_id": quote_currency_id, "trading_symbol": symbol, "quote_factor": 1, "unit_multiplier": 1, "effective_from": MVP_START_DATE, "is_current": True, "status": "APPROVED"})
        _insert_once(connection, m.listing_quotation_terms, {"listing_quotation_terms_id": _id(f"crypto:quotation:{listing_key}"), "listing_node_id": listing_id, "quote_currency_id": quote_currency_id, "quote_unit_code": "CURRENCY_PER_UNIT", "quote_factor": 1, "display_decimals": display_decimals, "tick_size": tick_size, "valid_from": MVP_START_DATE, "sequence_no": 1})
        _insert_once(connection, m.financial_reference_identifier, {"financial_reference_identifier_id": _id(f"crypto:identifier:ticker:{listing_key}"), "reference_node_id": listing_id, "identifier_scheme_id": _catalogue_id(connection, m.identifier_scheme, m.identifier_scheme.c.scheme_code, "TICKER"), "identifier_value": symbol, "context_market_venue_id": venue_id, "valid_from": MVP_START_DATE, "is_primary": True})
        _insert_once(connection, m.financial_reference_identifier, {"financial_reference_identifier_id": _id(f"crypto:identifier:product:{listing_key}"), "reference_node_id": listing_id, "identifier_scheme_id": _catalogue_id(connection, m.identifier_scheme, m.identifier_scheme.c.scheme_code, "VENUE_PRODUCT_ID"), "identifier_value": venue_product_id, "context_market_venue_id": venue_id, "valid_from": MVP_START_DATE, "is_primary": True})
        _insert_once(connection, m.financial_reference_identifier, {"financial_reference_identifier_id": _id(f"crypto:identifier:fix:{listing_key}"), "reference_node_id": listing_id, "identifier_scheme_id": _catalogue_id(connection, m.identifier_scheme, m.identifier_scheme.c.scheme_code, "FIX_SECURITY_ID"), "identifier_value": fix_security_id, "context_market_venue_id": venue_id, "valid_from": MVP_START_DATE, "is_primary": True})


def _add_etp_reference_data(connection: Connection, node_instrument, node_listing, etf_type, etc_type, etn_type) -> None:
    """Seed an ETF, ETC, and ETN using the shared instrument/listing model."""
    fund_node_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FUND")
    commodity_node_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "COMMODITY")
    etp_taxonomy_id = _catalogue_id(connection, m.taxonomy, m.taxonomy.c.taxonomy_code, "EXCHANGE_TRADED_PRODUCT_CLASS")

    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_etf_fund_node"], "reference_node_type_id": fund_node_type, "canonical_name": "MVP S&P 500 UCITS ETF fund", "internal_code": "MVP_SP500_ETF_FUND", "status": "ACTIVE", "is_tradable": False})
    _insert_once(connection, m.fund, {"fund_reference_node_id": DEMO_IDS["mvp_etf_fund_node"], "fund_kind": "ETF_ISSUER", "fund_manager_organisation_id": DEMO_IDS["hsbc_organisation"], "domicile_country_code": "IRL", "legal_form": "UCITS", "status": "ACTIVE"})
    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_gold_commodity_node"], "reference_node_type_id": commodity_node_type, "canonical_name": "MVP Gold commodity", "internal_code": "MVP_GOLD_COMMODITY", "status": "ACTIVE", "is_tradable": False})

    products = (
        ("mvp_etf_node", "MVP S&P 500 UCITS ETF", "MVP_SP500_ETF", etf_type, "FUND", DEMO_IDS["usd_currency"], "ETF", "UCITS_FUND", "PHYSICAL", "NOT_APPLICABLE", "OPEN_ENDED", "DISTRIBUTING", DEMO_IDS["mvp_sp500_price_index_node"]),
        ("mvp_etc_node", "MVP Gold ETC", "MVP_GOLD_ETC", etc_type, "COMMODITY", DEMO_IDS["usd_currency"], "ETC", "CERTIFICATE", "PHYSICAL", "SECURED", "OPEN_ENDED", "NONE", DEMO_IDS["mvp_gold_commodity_node"]),
        ("mvp_etn_node", "MVP S&P 500 Linked ETN", "MVP_SP500_ETN", etn_type, "STRUCTURED_PRODUCT", DEMO_IDS["usd_currency"], "ETN", "DEBT_NOTE", "NOT_APPLICABLE", "UNSECURED", "FIXED_MATURITY", "NONE", DEMO_IDS["mvp_sp500_price_index_node"]),
    )
    for key, name, code, type_id, asset_class, currency_id, etp_kind, legal_form, replication, collateral, redemption, distribution, reference_node_id in products:
        node_id = DEMO_IDS[key]
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": node_id, "reference_node_type_id": node_instrument, "canonical_name": name, "internal_code": code, "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": node_id, "instrument_type_id": type_id, "asset_class": asset_class, "issuer_organisation_id": DEMO_IDS["hsbc_organisation"], "base_currency_id": currency_id, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.etp_terms, {"etp_terms_id": DEMO_IDS[f"mvp_{etp_kind.lower()}_terms"], "instrument_node_id": node_id, "etp_kind": etp_kind, "legal_form": legal_form, "replication_method": replication, "collateralisation_type": collateral, "redemption_model": redemption, "distribution_policy": distribution, "reference_node_id": reference_node_id, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1, "status": "ACTIVE"})
        value_id = connection.execute(select(m.taxonomy_value.c.taxonomy_value_id).where(m.taxonomy_value.c.taxonomy_id == etp_taxonomy_id, m.taxonomy_value.c.value_code == etp_kind)).scalar_one()
        _insert_once(connection, m.instrument_taxonomy_assignment, {"instrument_taxonomy_assignment_id": _id(f"taxonomy:etp:{etp_kind}"), "instrument_node_id": node_id, "taxonomy_value_id": value_id, "effective_from": MVP_START_DATE, "is_primary": True, "source_system_id": "MVP_MANUAL"})
        _insert_once(connection, m.instrument_relationship, {"instrument_relationship_id": _id(f"relationship:etp:{etp_kind}:reference"), "from_reference_node_id": node_id, "to_reference_node_id": reference_node_id, "relationship_type": "REFERENCE_INDEX" if etp_kind == "ETN" else "UNDERLYING", "effective_from": MVP_START_DATE, "source_system_id": "MVP_MANUAL"})

    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_etf_listing"], "reference_node_type_id": node_listing, "canonical_name": "MVP_SP500_ETF listed", "internal_code": "MVP_SP500_ETF_XNYS", "status": "ACTIVE", "is_tradable": True})
    _insert_once(connection, m.listing, {"listing_node_id": DEMO_IDS["mvp_etf_listing"], "instrument_node_id": DEMO_IDS["mvp_etf_node"], "market_venue_id": DEMO_IDS["mvp_nyse_venue"], "trading_currency_id": DEMO_IDS["usd_currency"], "trading_symbol": "SP5E", "quote_factor": 1, "unit_multiplier": 1, "is_primary_listing": True, "effective_from": MVP_START_DATE, "status": "ACTIVE"})
    for kind in ("etc", "etn"):
        listing_key = f"mvp_{kind}_listing"
        node_key = f"mvp_{kind}_node"
        symbol = "GLDE" if kind == "etc" else "SP5N"
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS[listing_key], "reference_node_type_id": node_listing, "canonical_name": f"{symbol} listed", "internal_code": f"{symbol}_XNYS", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.listing, {"listing_node_id": DEMO_IDS[listing_key], "instrument_node_id": DEMO_IDS[node_key], "market_venue_id": DEMO_IDS["mvp_nyse_venue"], "trading_currency_id": DEMO_IDS["usd_currency"], "trading_symbol": symbol, "quote_factor": 1, "unit_multiplier": 1, "is_primary_listing": True, "effective_from": MVP_START_DATE, "status": "ACTIVE"})

    _insert_once(connection, m.fund_share_class_terms, {"fund_share_class_terms_id": DEMO_IDS["mvp_etf_share_class_terms"], "instrument_node_id": DEMO_IDS["mvp_etf_node"], "fund_reference_node_id": DEMO_IDS["mvp_etf_fund_node"], "share_class_code": "MVP_SP500_ACC_USD", "share_currency_id": DEMO_IDS["usd_currency"], "income_treatment": "DISTRIBUTION", "dealing_frequency": "DAILY", "nav_frequency": "DAILY", "nav_publication_lag_business_days": 0, "effective_from": MVP_START_DATE, "is_current": True, "sequence_no": 1})
    _insert_once(connection, m.reference_constituent_snapshot, {"reference_constituent_snapshot_id": DEMO_IDS["mvp_etf_snapshot"], "owner_reference_node_id": DEMO_IDS["mvp_etf_node"], "snapshot_date": MVP_END_DATE, "snapshot_kind": "ETF_PCF", "status": "ACTIVE"})
    for sequence_no, constituent_node_id, weight in ((1, DEMO_IDS["mvp_us_equity_node"], 0.60), (2, DEMO_IDS["mvp_eu_equity_node"], 0.40)):
        _insert_once(connection, m.reference_constituent_snapshot_item, {"reference_constituent_snapshot_item_id": _id(f"etf:pcf:{sequence_no}"), "reference_constituent_snapshot_id": DEMO_IDS["mvp_etf_snapshot"], "constituent_reference_node_id": constituent_node_id, "weight": weight, "sequence_no": sequence_no})


def _series_specs() -> list[dict]:
    return [
        {"key": "us_equity", "node": "mvp_us_equity_listing", "source": "YAHOO_FINANCE_MOCK", "dataset": "mvp_yahoo_dataset", "licence": "mvp_yahoo_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 120.0, "vol": 0.018, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "eu_equity", "node": "mvp_eu_equity_listing", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "eur_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 85.0, "vol": 0.016, "tz": "Europe/Berlin", "calendar": "mvp_europe_calendar"},
        {"key": "etf_sp500", "node": "mvp_etf_listing", "source": "YAHOO_FINANCE_MOCK", "dataset": "mvp_yahoo_dataset", "licence": "mvp_yahoo_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 102.0, "vol": 0.010, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "etc_gold", "node": "mvp_etc_listing", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 188.0, "vol": 0.012, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "etn_sp500", "node": "mvp_etn_listing", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 99.0, "vol": 0.011, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "hsbc_equity", "node": "hsbc_xlon_listing_node", "source": "LSEG_MOCK", "dataset": "mvp_lseg_dataset", "licence": "mvp_lseg_licence", "currency": "gbp_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 7.0, "vol": 0.014, "tz": "Europe/London", "calendar": "mvp_london_calendar"},
        {"key": "us_bond", "node": "mvp_us_bond_node", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "EVALUATED_PRICE", "value_type": "PRICE", "base": 99.2, "vol": 0.002, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "eu_bond", "node": "mvp_eu_bond_node", "source": "LSEG_MOCK", "dataset": "mvp_lseg_dataset", "licence": "mvp_lseg_licence", "currency": "eur_currency", "series_type": "EVALUATED_PRICE", "value_type": "PRICE", "base": 98.1, "vol": 0.002, "tz": "Europe/Berlin", "calendar": "mvp_europe_calendar"},
        {"key": "sp500_price", "node": "mvp_sp500_price_index_node", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "INDEX_LEVEL", "base": 5000.0, "vol": 0.010, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "sp500_net", "node": "mvp_sp500_net_index_node", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "INDEX_LEVEL", "base": 7200.0, "vol": 0.010, "tz": "America/New_York", "calendar": "mvp_new_york_calendar"},
        {"key": "future_dec", "node": "mvp_future_dec_listing", "source": "LSEG_MOCK", "dataset": "mvp_lseg_dataset", "licence": "mvp_lseg_licence", "currency": "eur_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 4800.0, "vol": 0.006, "tz": "Europe/Berlin", "calendar": "mvp_europe_calendar"},
        {"key": "future_mar", "node": "mvp_future_mar_listing", "source": "LSEG_MOCK", "dataset": "mvp_lseg_dataset", "licence": "mvp_lseg_licence", "currency": "eur_currency", "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "base": 4825.0, "vol": 0.006, "tz": "Europe/Berlin", "calendar": "mvp_europe_calendar"},
        {"key": "fx_gbpusd_uk", "node": "mvp_gbpusd_fx_pair_node", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "FX_SPOT", "value_type": "RATE", "base": 1.27, "vol": 0.003, "tz": "Europe/London", "calendar": "mvp_fx_calendar", "cut": "mvp_gbpusd_uk_cut", "cut_code": "UK_FUND_FX_1600_MVP"},
        {"key": "fx_gbpusd_us", "node": "mvp_gbpusd_fx_pair_node", "source": "YAHOO_FINANCE_MOCK", "dataset": "mvp_yahoo_dataset", "licence": "mvp_yahoo_licence", "currency": "usd_currency", "series_type": "FX_SPOT", "value_type": "RATE", "base": 1.27, "vol": 0.003, "tz": "America/New_York", "calendar": "mvp_fx_calendar", "cut": "mvp_gbpusd_us_cut", "cut_code": "US_FUND_FX_1600_MVP"},
        {"key": "fx_eurusd_uk", "node": "mvp_eurusd_fx_pair_node", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "FX_SPOT", "value_type": "RATE", "base": 1.09, "vol": 0.0025, "tz": "Europe/London", "calendar": "mvp_fx_calendar", "cut": "mvp_eurusd_uk_cut", "cut_code": "EUR_FUND_FX_1600_MVP"},
        {"key": "fx_eurusd_us", "node": "mvp_eurusd_fx_pair_node", "source": "LSEG_MOCK", "dataset": "mvp_lseg_dataset", "licence": "mvp_lseg_licence", "currency": "usd_currency", "series_type": "FX_SPOT", "value_type": "RATE", "base": 1.09, "vol": 0.0025, "tz": "America/New_York", "calendar": "mvp_fx_calendar", "cut": "mvp_eurusd_us_cut", "cut_code": "EUR_FUND_US_1600_MVP"},
        {"key": "fx_forward_mark", "node": "mvp_fx_forward_instrument", "source": "BLOOMBERG_MOCK", "dataset": "mvp_bloomberg_dataset", "licence": "mvp_bloomberg_licence", "currency": "usd_currency", "series_type": "MARK", "value_type": "RATE", "base": 1.2745, "vol": 0.0025, "tz": "America/New_York", "calendar": "mvp_fx_calendar"},
    ]


def _add_series_and_observations(connection: Connection, specs: list[dict], cuts: dict[str, UUID]) -> None:
    for spec in specs:
        dataset_id = DEMO_IDS[spec["dataset"]]
        licence_id = DEMO_IDS[spec["licence"]]
        cut_id = cuts.get(spec.get("cut"))
        series_id = _id(f"series:{spec['key']}")
        series_contract = {
            "market_data_series_id": series_id,
            "reference_node_id": DEMO_IDS[spec["node"]],
            "series_type": spec["series_type"],
            "value_type": spec["value_type"],
            "currency_id": DEMO_IDS[spec["currency"]],
            "default_dataset_id": dataset_id,
            "valuation_cut_id": cut_id,
            "source_system_id": spec["source"],
            "expected_frequency_code": "BUSINESS_DAILY",
            "expected_market_calendar_id": DEMO_IDS[spec["calendar"]],
            "coverage_start_date": MVP_START_DATE,
            "coverage_end_date": MVP_END_DATE,
            "status": "ACTIVE",
            "is_official": True,
        }
        _insert_once(connection, m.market_data_series, series_contract)
        # Re-running the fixture upgrades a previously inserted series to the
        # current coverage contract without changing its identity.
        connection.execute(
            update(m.market_data_series)
            .where(m.market_data_series.c.market_data_series_id == series_id)
            .values(**{key: value for key, value in series_contract.items() if key != "market_data_series_id"})
        )
        _insert_once(connection, m.market_data_series_dimension, {"market_data_series_dimension_id": _id(f"dimension:{spec['key']}:source"), "market_data_series_id": series_id, "dimension_code": "SOURCE", "dimension_value": spec["source"]})
        if spec.get("cut_code"):
            _insert_once(connection, m.market_data_series_dimension, {"market_data_series_dimension_id": _id(f"dimension:{spec['key']}:cut"), "market_data_series_id": series_id, "dimension_code": "VALUATION_CUT", "dimension_value": spec["cut_code"]})
        dates = _business_dates(spec["calendar"])
        rng = Random(f"mvp:{spec['key']}")
        value = spec["base"]
        observations = []
        for day in dates:
            value = max(0.0001, value * (1.0 + rng.gauss(0.00008, spec["vol"])))
            observed = _local_close(day, spec["tz"], 16, 0) if spec.get("cut") else _local_close(day, spec["tz"], 16, 30)
            observations.append({"market_data_observation_id": _id(f"observation:{spec['key']}:{day.isoformat()}"), "market_data_series_id": series_id, "dataset_id": dataset_id, "acquisition_licence_id": licence_id, "market_data_vintage_id": _vintage_id(spec["dataset"], day), "market_date": day, "valuation_cut_id": cut_id, "observed_at_utc": observed, "received_at_utc": observed + timedelta(minutes=2), "value": round(value, 8), "value_basis": "RAW", "source_timestamp_utc": observed, "source_published_at_utc": observed + timedelta(minutes=1), "source_observation_key": f"{spec['source']}:{spec['key']}:{day.isoformat()}", "quality_status": "ACCEPTED"})
        _insert_many(connection, m.market_data_observation, observations)
        # The first MVP fixture pre-dated vintage lineage. Preserve its values
        # but attach the deterministic delivery batch when the fixture is run
        # again, so old and new rows have identical audit evidence.
        connection.execute(
            update(m.market_data_observation)
            .where(m.market_data_observation.c.market_data_observation_id == bindparam("row_id"))
            .values(market_data_vintage_id=bindparam("vintage_id")),
            [
                {"row_id": item["market_data_observation_id"], "vintage_id": item["market_data_vintage_id"]}
                for item in observations
            ],
        )


def _add_market_data_vintages(connection: Connection, specs: list[dict]) -> None:
    """Create immutable provider batches that explain each synthetic observation."""
    rows: dict[tuple[str, date], dict] = {}
    for spec in specs:
        for day in _business_dates(spec["calendar"]):
            key = (spec["dataset"], day)
            published_at = _local_close(day, spec["tz"], 18, 0)
            rows.setdefault(key, {
                "market_data_vintage_id": _vintage_id(spec["dataset"], day),
                "dataset_id": DEMO_IDS[spec["dataset"]],
                "data_provider_id": _provider_id_for_dataset(spec["dataset"]),
                "source_vintage_key": f"MVP_EOD:{spec['dataset']}:{day.isoformat()}",
                "source_published_at_utc": published_at,
                "received_at_utc": published_at + timedelta(minutes=2),
                "value_basis": "RAW",
                "vintage_status": "CURRENT",
            })
    _insert_many(connection, m.market_data_vintage, list(rows.values()))


def _extend_legacy_demo_histories(connection: Connection) -> None:
    """Backfill the original sparse demo series so every catalogue card is explorable.

    The first Security Master fixture predates the two-year MVP data set and
    intentionally contains only a few observations for resolver examples. It
    remains useful for those tests, so preserve those rows and fill only the
    missing business dates with deterministic synthetic observations.
    """
    legacy_specs = [
        ("legacy_hsbc_close", DEMO_IDS["market_data_series"], DEMO_IDS["dataset"], DEMO_IDS["valuation_cut"], 1023.0, 0.014, "Europe/London", 16, 30, "mvp_london_calendar"),
        ("legacy_bond", DEMO_IDS["bond_series"], DEMO_IDS["multi_asset_dataset"], DEMO_IDS["valuation_cut"], 98.4, 0.002, "Europe/London", 16, 30, "mvp_london_calendar"),
        ("legacy_gbpusd_uk", DEMO_IDS["uk_gbpusd_series"], DEMO_IDS["multi_asset_dataset"], DEMO_IDS["uk_fx_cut"], 1.356, 0.003, "Europe/London", 16, 0, "mvp_fx_calendar"),
        ("legacy_gbpusd_us", DEMO_IDS["us_gbpusd_series"], DEMO_IDS["multi_asset_dataset"], DEMO_IDS["us_fx_cut"], 1.359, 0.003, "America/New_York", 16, 0, "mvp_fx_calendar"),
        ("legacy_fund_nav", DEMO_IDS["demo_fund_nav_series"], DEMO_IDS["dataset"], DEMO_IDS["valuation_cut"], 101.25, 0.001, "Europe/London", 16, 30, "mvp_london_calendar"),
        ("legacy_fx_forward", DEMO_IDS["fx_forward_series"], DEMO_IDS["multi_asset_dataset"], DEMO_IDS["valuation_cut"], 1.1612, 0.0025, "Europe/London", 16, 30, "mvp_fx_calendar"),
        ("legacy_future", DEMO_IDS["future_series"], DEMO_IDS["multi_asset_dataset"], DEMO_IDS["valuation_cut"], 4875.5, 0.006, "Europe/Berlin", 16, 30, "mvp_europe_calendar"),
    ]
    for key, series_id, dataset_id, cut_id, base, volatility, timezone_name, hour, minute, calendar_key in legacy_specs:
        vintage_id = _id(f"vintage:legacy:{dataset_id}")
        _insert_once(connection, m.market_data_vintage, {
            "market_data_vintage_id": vintage_id,
            "dataset_id": dataset_id,
            "data_provider_id": DEMO_IDS["data_provider"],
            "source_vintage_key": f"MVP_LEGACY_FIXTURE:{dataset_id}",
            "source_published_at_utc": datetime.combine(MVP_END_DATE, time(18, 0), tzinfo=timezone.utc),
            "received_at_utc": datetime.combine(MVP_END_DATE, time(18, 2), tzinfo=timezone.utc),
            "value_basis": "RAW",
            "vintage_status": "CURRENT",
        })
        connection.execute(
            update(m.market_data_series)
            .where(m.market_data_series.c.market_data_series_id == series_id)
            .values(
                expected_frequency_code="BUSINESS_DAILY",
                expected_market_calendar_id=DEMO_IDS[calendar_key],
                coverage_start_date=MVP_START_DATE,
                coverage_end_date=MVP_END_DATE,
            )
        )
        connection.execute(
            update(m.market_data_observation)
            .where(m.market_data_observation.c.market_data_series_id == series_id)
            .where(m.market_data_observation.c.source_observation_key.like(f"MVP_LEGACY:{key}:%"))
            .values(
                dataset_id=dataset_id,
                acquisition_licence_id=DEMO_IDS["data_licence"],
                source_payload_id=DEMO_IDS["source_payload"],
                valuation_cut_id=cut_id,
                market_data_vintage_id=vintage_id,
            )
        )
        connection.execute(
            update(m.market_data_observation)
            .where(m.market_data_observation.c.market_data_series_id == series_id)
            .where(m.market_data_observation.c.market_date.is_(None))
            .values(market_date=MVP_END_DATE, market_data_vintage_id=vintage_id)
        )
        existing_dates = set(connection.execute(select(m.market_data_observation.c.market_date).where(m.market_data_observation.c.market_data_series_id == series_id)).scalars())
        rng = Random(f"mvp:{key}")
        value = base
        rows = []
        for day in _business_dates(calendar_key):
            value = max(0.0001, value * (1.0 + rng.gauss(0.00008, volatility)))
            if day in existing_dates:
                continue
            observed = _local_close(day, timezone_name, hour, minute)
            rows.append({
                "market_data_observation_id": _id(f"observation:{key}:{day.isoformat()}"),
                "market_data_series_id": series_id,
                "dataset_id": dataset_id,
                "acquisition_licence_id": DEMO_IDS["data_licence"],
                "source_payload_id": DEMO_IDS["source_payload"],
                "market_data_vintage_id": vintage_id,
                "market_date": day,
                "valuation_cut_id": cut_id,
                "observed_at_utc": observed,
                "received_at_utc": observed + timedelta(minutes=2),
                "value": round(value, 8),
                "value_basis": "RAW",
                "source_timestamp_utc": observed,
                "source_published_at_utc": observed + timedelta(minutes=1),
                "source_observation_key": f"MVP_LEGACY:{key}:{day.isoformat()}",
                "quality_status": "ACCEPTED",
            })
        _insert_many(connection, m.market_data_observation, rows)


def _link_series_measure_definitions(connection: Connection) -> None:
    """Attach the governed semantic meaning to synthetic and legacy series."""

    definition_ids = dict(
        connection.execute(
            select(
                m.series_measure_definition.c.measure_code,
                m.series_measure_definition.c.series_measure_definition_id,
            )
        ).tuples().all()
    )
    for series_id, series_type, value_type in connection.execute(
        select(
            m.market_data_series.c.market_data_series_id,
            m.market_data_series.c.series_type,
            m.market_data_series.c.value_type,
        ).where(m.market_data_series.c.measure_definition_id.is_(None))
    ).tuples():
        measure_code = (
            "FX_RATE"
            if value_type == "RATE" and series_type == "FX_SPOT"
            else "NAV"
            if value_type == "PRICE" and series_type == "OFFICIAL_NAV"
            else "CREDIT_SPREAD"
            if value_type == "SPREAD"
            else value_type
        )
        if measure_code in definition_ids:
            connection.execute(
                update(m.market_data_series)
                .where(m.market_data_series.c.market_data_series_id == series_id)
                .values(measure_definition_id=definition_ids[measure_code])
            )


def _add_trade_detail_rows(connection: Connection, trade_rows: list[tuple]) -> None:
    """Seed normalized counterparties, traders, references, fees and events."""
    internal_person_id = _id("person:mvp:operations-booker")
    trader_ids = {
        "MVP_US_PORTFOLIO": _id("person:mvp:us-trader"),
        "MVP_UK_PORTFOLIO": _id("person:mvp:uk-trader"),
    }
    _insert_once(connection, m.person, {"person_id": internal_person_id, "display_name": "MVP Operations Booker", "given_name": "MVP", "family_name": "Operations Booker", "status": "ACTIVE"})
    for person_id, display_name, given_name, family_name in (
        (trader_ids["MVP_US_PORTFOLIO"], "MVP US Trader", "US", "Trader"),
        (trader_ids["MVP_UK_PORTFOLIO"], "MVP UK Trader", "UK", "Trader"),
    ):
        _insert_once(connection, m.person, {"person_id": person_id, "display_name": display_name, "given_name": given_name, "family_name": family_name, "status": "ACTIVE"})
    connection.execute(update(m.user_account).where(m.user_account.c.user_account_id == DEMO_IDS["demo_user_account"]).values(person_id=internal_person_id))

    for key, strategy_id, subject_id, quantity, price, currency_id, quantity_unit in trade_rows:
        trade_id = _id(f"trade:{key}")
        strategy_code = "MVP_US_PORTFOLIO" if strategy_id == DEMO_IDS["mvp_us_strategy"] else "MVP_UK_PORTFOLIO"
        trader_id = trader_ids[strategy_code]
        # Keep the primary trader field convenient for list/read paths; all
        # other counterparties remain in the normalized party-role table.
        connection.execute(update(m.trade).where(m.trade.c.trade_id == trade_id).values(trader_person_id=trader_id))
        role_rows = []
        for role, organisation_id in (
            ("CLIENT", DEMO_IDS["hsbc_organisation"]),
            ("COUNTERPARTY", DEMO_IDS["bank_a_organisation"]),
            ("CUSTODIAN", DEMO_IDS["custodian_b_organisation"]),
            ("EXECUTING_BROKER", DEMO_IDS["bank_a_organisation"]),
        ):
            role_id = _id(f"trade:{key}:party:{role}")
            role_rows.append((role, role_id))
            _insert_once(connection, m.trade_party_role, {"trade_party_role_id": role_id, "trade_id": trade_id, "organisation_id": organisation_id, "role": role})
        _insert_once(connection, m.trade_external_reference, {"trade_external_reference_id": _id(f"trade:{key}:external:agent"), "trade_id": trade_id, "source_system_id": "MVP_BOOKING", "trade_party_role_id": dict(role_rows)["COUNTERPARTY"], "reference_type": "SOURCE_TRADE_ID", "reference_value": f"MVP-{strategy_code[-2:]}-{key.upper()}-001", "source_received_at_utc": datetime(2024, 9, 3, 10, 2, tzinfo=timezone.utc)})
        fee_currency = currency_id
        fee_amount = round(abs(float(quantity) * float(price)) * 0.0005, 8)
        _insert_once(connection, m.trade_fee, {"trade_fee_id": _id(f"trade:{key}:fee:distribution"), "trade_id": trade_id, "fee_type": "DISTRIBUTION", "fee_payer_organisation_id": DEMO_IDS["hsbc_organisation"], "fee_recipient_organisation_id": DEMO_IDS["fortem_organisation"], "fee_amount": fee_amount, "fee_currency_id": fee_currency, "fee_rate": 0.05, "fee_rate_unit": "BPS", "fee_basis": "GROSS_CONSIDERATION", "accrual_date": date(2024, 9, 3), "settlement_date": date(2024, 9, 5), "status": "EXPECTED", "external_reference": f"MVP-FEE-{key.upper()}"})
        _insert_once(connection, m.trade_lifecycle_event, {"trade_lifecycle_event_id": _id(f"trade:{key}:event:booked"), "trade_id": trade_id, "sequence_no": 1, "event_type": "BOOKED", "event_datetime_utc": datetime(2024, 9, 3, 10, 0, tzinfo=timezone.utc), "source_system_id": "MVP_BOOKING", "source_event_id": f"MVP-BOOKED-{key}", "event_payload": json.dumps({"fixture": True, "tradeKey": key}, sort_keys=True), "recorded_by_user_account_id": DEMO_IDS["demo_user_account"]})


def load_mvp_demo_data(connection: Connection) -> None:
    """Load the broad synthetic market-data and portfolio scenario."""
    # Keep this fixture self-contained when called directly, not only through
    # the larger load_demo_data orchestration path.
    seed_defaults(connection)
    providers, products, datasets, licences, assignments, entitlements = _provider_rows()
    for entity_id, code, name in ((DEMO_IDS["mvp_bloomberg_entity"], "BLOOMBERG_MVP", "Bloomberg MVP Data Group"), (DEMO_IDS["mvp_yahoo_entity"], "YAHOO_MVP", "Yahoo MVP Data Group")):
        _insert_once(connection, m.entity, {"entity_id": entity_id, "entity_code": code, "display_name": name, "legal_name": name, "status": "ACTIVE"})
    for org_id, entity_id, name in ((DEMO_IDS["mvp_bloomberg_organisation"], DEMO_IDS["mvp_bloomberg_entity"], "Bloomberg MVP Data Ltd"), (DEMO_IDS["mvp_yahoo_organisation"], DEMO_IDS["mvp_yahoo_entity"], "Yahoo MVP Data Ltd")):
        _insert_once(connection, m.organisation, {"organisation_id": org_id, "entity_id": entity_id, "organisation_type": "VENDOR", "display_name": name, "legal_name": name, "status": "ACTIVE"})
    for table, rows in ((m.data_provider, providers), (m.provider_product, products), (m.dataset, datasets), (m.data_licence, licences), (m.dataset_licence_assignment, assignments), (m.tenant_dataset_entitlement, entitlements)):
        _insert_many(connection, table, rows)

    calendars = [
        ("mvp_london_calendar", "MVP_LONDON_TRADING", "London trading calendar (synthetic)", "Europe/London", "TRADING"),
        ("mvp_new_york_calendar", "MVP_NEW_YORK_TRADING", "New York trading calendar (synthetic)", "America/New_York", "TRADING"),
        ("mvp_europe_calendar", "MVP_EUROPE_TRADING", "European trading calendar (synthetic)", "Europe/Berlin", "TRADING"),
        ("mvp_fx_calendar", "MVP_FX_24X5", "FX weekday calendar (synthetic)", "UTC", "TRADING"),
    ]
    for key, code, name, tz_name, kind in calendars:
        _insert_once(connection, m.market_calendar, {"market_calendar_id": DEMO_IDS[key], "calendar_code": code, "display_name": name, "timezone_name": tz_name, "calendar_kind": kind, "status": "ACTIVE"})
    for day, name in ((date(2024, 12, 25), "Christmas Day"), (date(2025, 12, 25), "Christmas Day"), (date(2026, 1, 1), "New Year's Day")):
        for key in ("mvp_london_calendar", "mvp_new_york_calendar", "mvp_europe_calendar"):
            _insert_once(connection, m.market_calendar_holiday, {"market_calendar_holiday_id": _id(f"holiday:{key}:{day}"), "market_calendar_id": DEMO_IDS[key], "holiday_date": day, "holiday_name": name, "holiday_kind": "FULL_CLOSE", "source_reference": "MVP_SYNTHETIC"})

    cuts = {
        "mvp_gbpusd_uk_cut": DEMO_IDS["mvp_gbpusd_uk_cut"],
        "mvp_gbpusd_us_cut": DEMO_IDS["mvp_gbpusd_us_cut"],
        "mvp_eurusd_uk_cut": DEMO_IDS["mvp_eurusd_uk_cut"],
        "mvp_eurusd_us_cut": DEMO_IDS["mvp_eurusd_us_cut"],
    }
    cut_rows = [
        ("mvp_gbpusd_uk_cut", "UK_FUND_FX_1600_MVP", "UK fund FX cut at 16:00 London (synthetic)", "Europe/London", DEMO_IDS["mvp_fx_calendar"]),
        ("mvp_gbpusd_us_cut", "US_FUND_FX_1600_MVP", "US fund FX cut at 16:00 New York (synthetic)", "America/New_York", DEMO_IDS["mvp_fx_calendar"]),
        ("mvp_eurusd_uk_cut", "EUR_FUND_FX_1600_MVP", "EUR fund FX cut at 16:00 London (synthetic)", "Europe/London", DEMO_IDS["mvp_fx_calendar"]),
        ("mvp_eurusd_us_cut", "EUR_FUND_US_1600_MVP", "EUR fund FX cut at 16:00 New York (synthetic)", "America/New_York", DEMO_IDS["mvp_fx_calendar"]),
    ]
    for key, code, name, tz_name, calendar_id in cut_rows:
        _insert_once(connection, m.valuation_cut, {"valuation_cut_id": DEMO_IDS[key], "cut_code": code, "display_name": name, "timezone_name": tz_name, "local_time": "16:00:00", "market_calendar_id": calendar_id, "status": "ACTIVE"})

    node_instrument = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "INSTRUMENT")
    node_listing = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "LISTING")
    future_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "FUTURE")
    equity_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "EQUITY")
    bond_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "BOND")
    fx_forward_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "FX_FORWARD")
    digital_asset_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "DIGITAL_ASSET")
    etf_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "ETF")
    etc_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "ETC")
    etn_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "ETN")
    _insert_once(connection, m.market_venue, {"market_venue_id": DEMO_IDS["mvp_nyse_venue"], "operating_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "venue_type": "EXCHANGE", "display_name": "NYSE (synthetic)", "country_code": "USA", "city": "New York", "timezone_name": "America/New_York", "market_calendar_id": DEMO_IDS["mvp_new_york_calendar"], "status": "ACTIVE"})
    _insert_once(connection, m.market_venue, {"market_venue_id": DEMO_IDS["mvp_xetr_venue"], "operating_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "venue_type": "EXCHANGE", "display_name": "Xetra (synthetic)", "country_code": "DEU", "city": "Frankfurt", "timezone_name": "Europe/Berlin", "market_calendar_id": DEMO_IDS["mvp_europe_calendar"], "status": "ACTIVE"})
    _insert_once(connection, m.market_venue, {"market_venue_id": DEMO_IDS["coinbase_venue"], "operating_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "venue_type": "CEX", "display_name": "Coinbase (synthetic)", "country_code": "USA", "city": "San Francisco", "timezone_name": "America/Los_Angeles", "status": "ACTIVE"})
    _insert_once(connection, m.market_venue, {"market_venue_id": DEMO_IDS["binance_venue"], "operating_organisation_id": DEMO_IDS["mvp_bloomberg_organisation"], "venue_type": "CEX", "display_name": "Binance (synthetic)", "country_code": None, "city": None, "timezone_name": "UTC", "status": "ACTIVE"})
    _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": DEMO_IDS["mvp_nyse_mic"], "market_venue_id": DEMO_IDS["mvp_nyse_venue"], "identifier_scheme": "ISO_10383_MIC", "identifier_value": "XNYS", "is_primary": True})
    _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": DEMO_IDS["mvp_xetr_mic"], "market_venue_id": DEMO_IDS["mvp_xetr_venue"], "identifier_scheme": "ISO_10383_MIC", "identifier_value": "XETR", "is_primary": True})
    _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": DEMO_IDS["coinbase_venue_code"], "market_venue_id": DEMO_IDS["coinbase_venue"], "identifier_scheme": "CRYPTO_EXCHANGE_CODE", "identifier_value": "COINBASE", "is_primary": True})
    _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": DEMO_IDS["binance_venue_code"], "market_venue_id": DEMO_IDS["binance_venue"], "identifier_scheme": "CRYPTO_EXCHANGE_CODE", "identifier_value": "BINANCE", "is_primary": True})

    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_gbpusd_fx_pair_node"], "reference_node_type_id": _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FX_PAIR"), "canonical_name": "GBP/USD spot pair", "internal_code": "MVP_GBPUSD", "status": "ACTIVE", "is_tradable": False})
    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_eurusd_fx_pair_node"], "reference_node_type_id": _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FX_PAIR"), "canonical_name": "EUR/USD spot pair", "internal_code": "MVP_EURUSD", "status": "ACTIVE", "is_tradable": False})
    # The family points at the economic equity node, so create that node before
    # the family row; the complete instrument definition follows immediately.
    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_eu_equity_node"], "reference_node_type_id": node_instrument, "canonical_name": "MVP European Industrials Equity", "internal_code": "MVP_EU_INDUSTRIALS_EQUITY", "status": "ACTIVE", "is_tradable": True})
    _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["mvp_future_family_node"], "reference_node_type_id": _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FUTURE_FAMILY"), "canonical_name": "MVP Euro Stoxx futures family", "internal_code": "MVP_ESTX_FAMILY", "status": "ACTIVE", "is_tradable": False})
    _insert_once(connection, m.future_family, {"future_family_id": DEMO_IDS["mvp_future_family"], "family_node_id": DEMO_IDS["mvp_future_family_node"], "underlying_reference_node_id": DEMO_IDS["mvp_eu_equity_node"], "contract_currency_id": DEMO_IDS["eur_currency"], "expiry_cycle": "QUARTERLY", "status": "ACTIVE"})
    _add_instruments(connection, node_instrument, node_listing, future_type, equity_type, bond_type, fx_forward_type)
    _add_index_reference_data(connection)
    _add_crypto_reference_data(connection, node_instrument, digital_asset_type)
    _add_etp_reference_data(connection, node_instrument, node_listing, etf_type, etc_type, etn_type)

    for strategy_id, code, name, currency_id in ((DEMO_IDS["mvp_us_strategy"], "MVP_US_PORTFOLIO", "US portfolio (synthetic)", DEMO_IDS["usd_currency"]), (DEMO_IDS["mvp_uk_strategy"], "MVP_UK_PORTFOLIO", "UK portfolio (synthetic)", DEMO_IDS["gbp_currency"])):
        _insert_once(connection, m.strategy, {"strategy_id": strategy_id, "tenant_id": DEMO_IDS["tenant"], "strategy_code": code, "display_name": name, "strategy_type": "FUND", "base_currency_id": currency_id, "legal_owner_organisation_id": DEMO_IDS["fortem_organisation"], "status": "ACTIVE"})

    trade_rows = [
        ("us_equity", DEMO_IDS["mvp_us_strategy"], DEMO_IDS["mvp_us_equity_listing"], 100, 120.0, DEMO_IDS["usd_currency"], "SHARES"),
        ("eu_equity", DEMO_IDS["mvp_us_strategy"], DEMO_IDS["mvp_eu_equity_listing"], 200, 85.0, DEMO_IDS["eur_currency"], "SHARES"),
        ("us_bond", DEMO_IDS["mvp_us_strategy"], DEMO_IDS["mvp_us_bond_node"], 50000, 99.2, DEMO_IDS["usd_currency"], "NOMINAL"),
        ("hsbc_equity", DEMO_IDS["mvp_uk_strategy"], DEMO_IDS["hsbc_xlon_listing_node"], 1000, 700.0, DEMO_IDS["gbp_currency"], "SHARES"),
        ("us_equity_uk", DEMO_IDS["mvp_uk_strategy"], DEMO_IDS["mvp_us_equity_listing"], 80, 120.0, DEMO_IDS["usd_currency"], "SHARES"),
        ("eu_bond_uk", DEMO_IDS["mvp_uk_strategy"], DEMO_IDS["mvp_eu_bond_node"], 40000, 98.4, DEMO_IDS["eur_currency"], "NOMINAL"),
    ]
    for key, strategy_id, subject_id, quantity, price, currency_id, quantity_unit in trade_rows:
        trade_id = _id(f"trade:{key}")
        _insert_once(connection, m.trade, {"trade_id": trade_id, "trade_subject_reference_node_id": subject_id, "strategy_id": strategy_id, "trade_type": "INVESTMENT", "trade_purpose": "INVESTMENT", "market_activity": "SECONDARY", "execution_price": price, "price_basis": "PCT_OF_PAR" if quantity_unit == "NOMINAL" else "UNIT_PRICE", "price_currency_id": currency_id, "quantity": quantity, "quantity_unit": quantity_unit, "trade_datetime_utc": datetime(2024, 9, 3, 10, 0, tzinfo=timezone.utc), "settlement_date": date(2024, 9, 5), "booked_by_user_account_id": DEMO_IDS["demo_user_account"], "execution_channel": "MANUAL_UI", "source_system_id": "MVP_BOOKING", "lifecycle_status": "BOOKED", "created_by_user_account_id": DEMO_IDS["demo_user_account"]})
    _add_trade_detail_rows(connection, trade_rows)

    series_specs = _series_specs()
    _add_market_data_vintages(connection, series_specs)
    _add_series_and_observations(connection, series_specs, cuts)
    _extend_legacy_demo_histories(connection)
    _link_series_measure_definitions(connection)
