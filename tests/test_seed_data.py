"""Contract tests for the baseline governed-reference seed data."""

import unittest

from security_master_schema import seed_data
from security_master_schema.seed_data import (
    IDENTIFIER_SCHEME_SEEDS,
    INDEX_KIND_CATALOGUE_SEEDS,
    CRYPTO_NETWORK_SEEDS,
    INSTRUMENT_TYPE_SEEDS,
    REFERENCE_NODE_TYPE_SEEDS,
    TAXONOMY_SEEDS,
    TAXONOMY_VALUE_SEEDS,
)


class SeedDataTests(unittest.TestCase):
    def test_reference_node_type_seed_includes_currency_and_listing_semantics(self) -> None:
        seeded_types = {row["type_code"]: row for row in REFERENCE_NODE_TYPE_SEEDS}

        self.assertFalse(seeded_types["CURRENCY"]["default_is_tradable"])
        self.assertEqual("VENUE_REPRESENTATION", seeded_types["LISTING"]["node_class"])
        self.assertTrue(seeded_types["LISTING"]["default_is_tradable"])

    def test_identifier_scheme_seed_includes_the_core_listed_security_identifiers(self) -> None:
        seeded_schemes = {row["scheme_code"] for row in IDENTIFIER_SCHEME_SEEDS}

        self.assertTrue({"ISIN", "FIGI", "CUSIP", "SEDOL", "TICKER"}.issubset(seeded_schemes))

    def test_instrument_type_seed_covers_the_discussed_product_set(self) -> None:
        seeded_types = {row["type_code"] for row in INSTRUMENT_TYPE_SEEDS}

        self.assertTrue(
            {
                "EQUITY",
                "BOND",
                "ETF",
                "FUND_SHARE_CLASS",
                "FX_FORWARD",
                "SWAP",
                "OPTION",
                "STRUCTURED_PRODUCT",
                "COMPOSED_OPTION",
                "FUTURE",
                "ACTIVELY_MANAGED_CERTIFICATE",
                "ETC",
                "ETN",
                "EXCHANGE_TRADED_VEHICLE",
            }.issubset(seeded_types)
        )

    def test_exchange_traded_product_taxonomy_is_an_umbrella_not_a_new_economic_type(self) -> None:
        taxonomy_codes = {row["taxonomy_code"] for row in TAXONOMY_SEEDS}
        etp_values = {
            row["value_code"]
            for row in TAXONOMY_VALUE_SEEDS
            if row["taxonomy_code"] == "EXCHANGE_TRADED_PRODUCT_CLASS"
        }
        self.assertIn("EXCHANGE_TRADED_PRODUCT_CLASS", taxonomy_codes)
        self.assertTrue({"ETF", "ETC", "ETN", "ETV", "ETI"}.issubset(etp_values))
        self.assertNotIn("ETP", {row["type_code"] for row in INSTRUMENT_TYPE_SEEDS})

    def test_taxonomy_seed_includes_structured_product_and_index_domains(self) -> None:
        taxonomy_codes = {row["taxonomy_code"] for row in TAXONOMY_SEEDS}
        structured_values = {
            row["value_code"]
            for row in TAXONOMY_VALUE_SEEDS
            if row["taxonomy_code"] == "STRUCTURED_PRODUCT_ARCHETYPE"
        }
        self.assertIn("STRUCTURED_PRODUCT_ARCHETYPE", taxonomy_codes)
        self.assertTrue(
            {
                "INDEX_ASSET_CLASS",
                "INDEX_GEOGRAPHY",
                "INDEX_SCOPE",
                "INDEX_SIZE",
                "INDEX_STRATEGY",
                "INDEX_BENCHMARK_ROLE",
                "INDEX_SECTOR",
            }.issubset(taxonomy_codes)
        )
        self.assertNotIn("INTERNAL_SWAP_STRATEGY", taxonomy_codes)
        self.assertTrue(
            {"AUTOCALL", "AUTOCALL_CONSOLATION", "PHOENIX", "ATHENA", "SUPERTRACKER", "RANGE_ACCRUAL", "VANILLA_SPREAD_KIP", "VANILLA_KIP", "DIGITAL_KIP"}.issubset(
                structured_values
            )
        )
        consolation = next(
            row for row in TAXONOMY_VALUE_SEEDS if row["taxonomy_code"] == "STRUCTURED_PRODUCT_ARCHETYPE" and row["value_code"] == "AUTOCALL_CONSOLATION"
        )
        self.assertEqual(consolation["parent_value_code"], "AUTOCALL")
        self.assertTrue({"ABC", "XYZ", "FOO"}.isdisjoint({row["value_code"] for row in TAXONOMY_VALUE_SEEDS}))

    def test_index_taxonomy_seed_has_hierarchical_and_strategy_values(self) -> None:
        index_values = {
            row["value_code"]
            for row in TAXONOMY_VALUE_SEEDS
            if row["taxonomy_code"].startswith("INDEX_")
        }
        self.assertTrue({"EQUITY", "FIXED_INCOME", "COMMODITY", "CURRENCY"}.issubset(index_values))
        self.assertTrue({"MARKET_CAP_WEIGHTED", "FACTOR", "QIS"}.issubset(index_values))
        sector_root = next(
            row for row in TAXONOMY_VALUE_SEEDS
            if row["taxonomy_code"] == "INDEX_SECTOR" and row["value_code"] == "BROAD_SECTOR"
        )
        sector_child = next(
            row for row in TAXONOMY_VALUE_SEEDS
            if row["taxonomy_code"] == "INDEX_SECTOR" and row["value_code"] == "TECHNOLOGY"
        )
        self.assertIsNone(sector_root["parent_value_code"])
        self.assertEqual("BROAD_SECTOR", sector_child["parent_value_code"])

    def test_return_profile_seed_covers_the_governed_generic_profiles(self) -> None:
        seeded_profiles = {row["profile_code"] for row in seed_data.RETURN_PROFILE_SEEDS}
        self.assertTrue(
            {
                "PRICE_RETURN",
                "GROSS_TOTAL_RETURN",
                "NET_TOTAL_RETURN",
                "EXCESS_PRICE_RETURN",
                "EXCESS_TOTAL_RETURN",
                "DIVIDEND_POINTS",
            }.issubset(seeded_profiles)
        )

    def test_index_kind_seed_explains_dissemination_and_ownership_separately(self) -> None:
        seeded = {row["index_kind_code"]: row for row in INDEX_KIND_CATALOGUE_SEEDS}
        self.assertTrue({"PUBLIC", "QIS", "PROPRIETARY", "CUSTOM_BASKET"}.issubset(seeded))
        self.assertEqual("PUBLIC", seeded["PUBLIC"]["dissemination_class"])
        self.assertEqual("PROVIDER_OWNED", seeded["PUBLIC"]["methodology_ownership"])
        self.assertIn("publicly", seeded["PUBLIC"]["description"].lower())
        self.assertIn("S&P 500", seeded["PUBLIC"]["example_text"])

    def test_crypto_network_seed_covers_native_and_multi_chain_examples(self) -> None:
        seeded = {row["network_code"]: row for row in CRYPTO_NETWORK_SEEDS}
        self.assertTrue({"BITCOIN_MAINNET", "ETHEREUM_MAINNET", "SOLANA_MAINNET", "BASE_MAINNET"}.issubset(seeded))
        self.assertEqual("BITCOIN", seeded["BITCOIN_MAINNET"]["network_family"])
        self.assertEqual("1", seeded["ETHEREUM_MAINNET"]["chain_identifier"])

    def test_listing_identifier_seed_covers_operational_venue_codes(self) -> None:
        seeded = {row["scheme_code"]: row for row in seed_data.IDENTIFIER_SCHEME_SEEDS}
        self.assertEqual("LISTING", seeded["VENUE_PRODUCT_ID"]["scope"])
        self.assertEqual("LISTING", seeded["FIX_SECURITY_ID"]["scope"])
