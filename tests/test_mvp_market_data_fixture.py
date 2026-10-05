"""Coverage tests for the two-year mock market-data and portfolio fixture."""

import os

from sqlalchemy import create_engine, text

from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm",
)


def test_mvp_fixture_has_provider_universe_portfolios_and_trades() -> None:
    expected_ids = {
        "mvp_us_strategy",
        "mvp_uk_strategy",
        "mvp_us_equity_listing",
        "mvp_eu_equity_listing",
        "mvp_future_family",
        "mvp_future_instrument",
        "mvp_fx_forward_instrument",
        "mvp_bloomberg_provider",
        "mvp_yahoo_provider",
    }
    assert expected_ids.issubset(DEMO_IDS)

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        provider_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM md.data_provider
                WHERE provider_code IN ('BLOOMBERG_MOCK', 'YAHOO_FINANCE_MOCK', 'LSEG_MOCK')
                """
            )
        )
        strategy_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM trd.strategy
                WHERE strategy_code IN ('MVP_US_PORTFOLIO', 'MVP_UK_PORTFOLIO')
                """
            )
        )
        trade_counts = connection.execute(
            text(
                """
                SELECT s.strategy_code, count(t.trade_id) AS trade_count
                FROM trd.strategy s
                LEFT JOIN trd.trade t ON t.strategy_id = s.strategy_id
                WHERE s.strategy_code IN ('MVP_US_PORTFOLIO', 'MVP_UK_PORTFOLIO')
                GROUP BY s.strategy_code
                """
            )
        ).mappings().all()
        listing_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM secm.listing
                WHERE listing_node_id IN (:us_listing, :eu_listing)
                """
            ),
            {"us_listing": DEMO_IDS["mvp_us_equity_listing"], "eu_listing": DEMO_IDS["mvp_eu_equity_listing"]},
        )
        future_count = connection.scalar(
            text("SELECT count(*) FROM secm.future_terms WHERE future_family_id = :family_id"),
            {"family_id": DEMO_IDS["mvp_future_family"]},
        )
        fx_forward_count = connection.scalar(
            text("SELECT count(*) FROM secm.fx_forward_terms WHERE instrument_node_id = :instrument_id"),
            {"instrument_id": DEMO_IDS["mvp_fx_forward_instrument"]},
        )
        day_count_convention_count = connection.scalar(
            text("SELECT count(*) FROM secm.day_count_convention WHERE status = 'ACTIVE'")
        )

    assert provider_count == 3
    assert strategy_count == 2
    assert {row["strategy_code"] for row in trade_counts} == {"MVP_US_PORTFOLIO", "MVP_UK_PORTFOLIO"}
    assert all(row["trade_count"] >= 3 for row in trade_counts)
    assert listing_count == 2
    assert future_count >= 2
    assert fx_forward_count == 1
    assert day_count_convention_count >= 9


def test_mvp_fixture_has_generic_return_profiles_and_index_variants() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        profile_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM secm.return_profile
                WHERE profile_code IN (
                    'PRICE_RETURN', 'GROSS_TOTAL_RETURN', 'NET_TOTAL_RETURN',
                    'EXCESS_PRICE_RETURN', 'EXCESS_TOTAL_RETURN', 'DIVIDEND_POINTS'
                )
                """
            )
        )
        index_rows = connection.execute(
            text(
                """
                SELECT i.index_node_id, n.canonical_name, f.family_node_id, p.profile_code
                FROM secm.index_terms i
                JOIN secm.financial_reference_node n ON n.reference_node_id = i.index_node_id
                JOIN secm.index_family f ON f.index_family_id = i.index_family_id
                JOIN secm.return_profile p ON p.return_profile_id = i.return_profile_id
                WHERE f.family_node_id = :family_node_id
                  AND i.index_node_id IN (:price_node, :net_node)
                ORDER BY n.canonical_name
                """
            ),
            {
                "family_node_id": DEMO_IDS["mvp_index_family_node"],
                "price_node": DEMO_IDS["mvp_sp500_price_index_node"],
                "net_node": DEMO_IDS["mvp_sp500_net_index_node"],
            },
        ).mappings().all()
        methodology_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM secm.index_methodology_version
                WHERE index_node_id IN (:price_node, :net_node)
                """
            ),
            {"price_node": DEMO_IDS["mvp_sp500_price_index_node"], "net_node": DEMO_IDS["mvp_sp500_net_index_node"]},
        )

    assert profile_count == 6
    assert {row["index_node_id"]: row["profile_code"] for row in index_rows} == {
        DEMO_IDS["mvp_sp500_price_index_node"]: "PRICE_RETURN",
        DEMO_IDS["mvp_sp500_net_index_node"]: "NET_TOTAL_RETURN",
    }
    assert methodology_count == 2


def test_mvp_fixture_has_etf_etc_etn_terms_listings_and_constituents() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        terms = connection.execute(
            text(
                """
                SELECT etp_kind, legal_form, collateralisation_type
                FROM secm.etp_terms
                WHERE instrument_node_id IN (:etf, :etc, :etn)
                ORDER BY etp_kind
                """
            ),
            {"etf": DEMO_IDS["mvp_etf_node"], "etc": DEMO_IDS["mvp_etc_node"], "etn": DEMO_IDS["mvp_etn_node"]},
        ).mappings().all()
        listing_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM secm.listing
                WHERE listing_node_id IN (:etf_listing, :etc_listing, :etn_listing)
                """
            ),
            {"etf_listing": DEMO_IDS["mvp_etf_listing"], "etc_listing": DEMO_IDS["mvp_etc_listing"], "etn_listing": DEMO_IDS["mvp_etn_listing"]},
        )
        pcf_items = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM secm.reference_constituent_snapshot_item i
                JOIN secm.reference_constituent_snapshot s
                  ON s.reference_constituent_snapshot_id = i.reference_constituent_snapshot_id
                WHERE s.reference_constituent_snapshot_id = :snapshot_id
                """
            ),
            {"snapshot_id": DEMO_IDS["mvp_etf_snapshot"]},
        )

    assert [row["etp_kind"] for row in terms] == ["ETC", "ETF", "ETN"]
    assert listing_count == 3
    assert pcf_items == 2


def test_mvp_fixture_separates_cryptoasset_currency_roles_and_deployments() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT n.canonical_name, c.currency_code, t.asset_subtype, d.deployment_kind, net.network_code
                FROM secm.crypto_asset_terms t
                JOIN secm.financial_reference_node n ON n.reference_node_id = t.instrument_node_id
                JOIN secm.currency c ON c.reference_node_id = t.instrument_node_id
                JOIN secm.crypto_asset_deployment d ON d.instrument_node_id = t.instrument_node_id
                JOIN secm.crypto_network net ON net.crypto_network_id = d.crypto_network_id
                WHERE t.instrument_node_id IN (:btc, :usdc)
                ORDER BY n.canonical_name, net.network_code
                """
            ),
            {"btc": DEMO_IDS["mvp_btc_node"], "usdc": DEMO_IDS["mvp_usdc_node"]},
        ).mappings().all()

    assert {(row["currency_code"], row["asset_subtype"]) for row in rows} == {("BTC", "NATIVE"), ("USDC", "STABLECOIN")}
    assert {(row["currency_code"], row["network_code"]) for row in rows} == {
        ("BTC", "BITCOIN_MAINNET"),
        ("USDC", "ETHEREUM_MAINNET"),
        ("USDC", "SOLANA_MAINNET"),
    }

    with engine.connect() as connection:
        identifiers = connection.execute(
            text(
                """
                SELECT l.trading_symbol, s.scheme_code, i.identifier_value
                FROM secm.listing l
                JOIN secm.financial_reference_identifier i ON i.reference_node_id = l.listing_node_id
                JOIN secm.identifier_scheme s ON s.identifier_scheme_id = i.identifier_scheme_id
                WHERE l.listing_node_id IN (:btc_usd, :btc_usdc, :usdc_usd)
                ORDER BY l.trading_symbol, s.scheme_code
                """
            ),
            {
                "btc_usd": DEMO_IDS["mvp_btc_coinbase_usd_listing"],
                "btc_usdc": DEMO_IDS["mvp_btc_binance_usdc_listing"],
                "usdc_usd": DEMO_IDS["mvp_usdc_kraken_usd_listing"],
            },
        ).mappings().all()

    assert {row["scheme_code"] for row in identifiers} == {"FIX_SECURITY_ID", "TICKER", "VENUE_PRODUCT_ID"}
    assert {row["identifier_value"] for row in identifiers} >= {"BTC-USD", "BTCUSDC", "USDCUSD"}


def test_mvp_fixture_has_two_year_daily_series_with_provenance() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        daily_series = connection.execute(
            text(
                """
                SELECT s.market_data_series_id, count(DISTINCT o.market_date) AS market_dates,
                       count(DISTINCT o.dataset_id) AS datasets,
                       count(DISTINCT o.acquisition_licence_id) AS licences
                FROM md.market_data_series s
                JOIN md.market_data_observation o
                  ON o.market_data_series_id = s.market_data_series_id
                WHERE s.source_system_id IN ('BLOOMBERG_MOCK', 'YAHOO_FINANCE_MOCK', 'LSEG_MOCK')
                GROUP BY s.market_data_series_id
                HAVING count(DISTINCT o.market_date) >= 500
                """
            )
        ).mappings().all()
        fx_cut_series = connection.execute(
            text(
                """
                SELECT vc.cut_code, count(DISTINCT o.market_date) AS market_dates
                FROM md.market_data_series s
                JOIN md.valuation_cut vc ON vc.valuation_cut_id = s.valuation_cut_id
                JOIN md.market_data_observation o ON o.market_data_series_id = s.market_data_series_id
                WHERE vc.cut_code IN ('UK_FUND_FX_1600_MVP', 'US_FUND_FX_1600_MVP')
                GROUP BY vc.cut_code
                """
            )
        ).mappings().all()

    assert len(daily_series) >= 6
    assert all(row["datasets"] >= 1 and row["licences"] >= 1 for row in daily_series)
    assert {row["cut_code"] for row in fx_cut_series} == {"UK_FUND_FX_1600_MVP", "US_FUND_FX_1600_MVP"}
    assert all(row["market_dates"] >= 500 for row in fx_cut_series)


def test_legacy_demo_bond_history_is_dense_enough_for_ui_drilldown() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT count(DISTINCT market_date) AS market_dates
                FROM md.market_data_observation
                WHERE market_data_series_id = :bond_series
                """
            ),
            {"bond_series": DEMO_IDS["bond_series"]},
        ).mappings().one()

    assert row["market_dates"] >= 500
