"""Contract tests for deterministic synthetic Security Master scenarios."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, text

from security_master_schema.demo_data import DEMO_IDS, load_demo_data


class DemoScenarioTests(unittest.TestCase):
    def test_demo_loader_seeds_taxonomy_catalogues_on_postgresql(self) -> None:
        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )

        load_demo_data(engine)

        with engine.connect() as connection:
            taxonomy_count = connection.scalar(text("SELECT count(*) FROM secm.taxonomy"))
        self.assertGreater(taxonomy_count, 0)

    def test_demo_loader_is_idempotent(self) -> None:
        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )

        load_demo_data(engine)
        load_demo_data(engine)

    def test_bootstrap_scripts_resolve_project_package_when_run_directly(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ | {
            "DATABASE_URL": "postgresql+psycopg://invalid:invalid@127.0.0.1:1/invalid?connect_timeout=1"
        }

        result = subprocess.run(
            [sys.executable, str(project_root / "scripts" / "create_schema.py")],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotIn("ModuleNotFoundError: No module named 'security_master_schema'", result.stderr)

    def test_hsbc_listing_scenario_has_stable_cross_system_identifiers(self) -> None:
        expected_ids = {
            "hsbc_instrument_node",
            "hsbc_xlon_listing_node",
            "bank_a_namespace",
            "custodian_b_namespace",
            "fortem_legacy_namespace",
            "bank_a_hsbc_mapping",
            "custodian_b_hsbc_mapping",
            "fortem_hsbc_mapping",
            "market_data_observation",
            "position_snapshot",
            "nav_calculation_run",
        }

        self.assertTrue(expected_ids.issubset(DEMO_IDS))
        self.assertEqual(len(DEMO_IDS), len(set(DEMO_IDS.values())))

    def test_additional_instrument_scenarios_cover_otc_fx_future_and_structured_product(self) -> None:
        expected_ids = {
            "eur_currency_node",
            "bond_instrument_node",
            "fx_forward_instrument_node",
            "future_family_node",
            "future_instrument_node",
            "autocall_instrument_node",
            "autocall_terms",
            "autocall_schedule",
            "autocall_condition_group",
            "autocall_hsbc_barrier",
            "autocall_eurostoxx_barrier",
            "autocall_coupon_action",
            "autocall_redemption_action",
            "autocall_coupon_programme",
            "autocall_coupon_period_1",
            "autocall_coupon_period_2",
            "autocall_coupon_component_terms",
        }

        self.assertTrue(expected_ids.issubset(DEMO_IDS))

        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            instrument_count = connection.scalar(text("SELECT count(*) FROM secm.instrument"))
            future_link_count = connection.scalar(text("SELECT count(*) FROM secm.future_terms"))
            fx_forward_count = connection.scalar(text("SELECT count(*) FROM secm.fx_forward_terms"))
            autocall_group_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.structured_product_condition_group "
                    "WHERE group_code = 'AUTOCALL_OBS_1_AT_100'"
                )
            )
            autocall_member_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.barrier_rule rule "
                    "JOIN secm.structured_product_condition_group condition_group "
                    "ON condition_group.condition_group_id = rule.condition_group_id "
                    "WHERE condition_group.group_code = 'AUTOCALL_OBS_1_AT_100'"
                )
            )
            autocall_action_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.condition_group_action action "
                    "JOIN secm.structured_product_condition_group condition_group "
                    "ON condition_group.condition_group_id = action.condition_group_id "
                    "WHERE condition_group.group_code = 'AUTOCALL_OBS_1_AT_100'"
                )
            )
            autocall_coupon_action_target = connection.execute(
                text(
                    "SELECT target_scope, target_composition_id, payout_multiplicity "
                    "FROM secm.condition_group_action action "
                    "JOIN secm.structured_product_condition_group condition_group "
                    "ON condition_group.condition_group_id = action.condition_group_id "
                    "WHERE condition_group.group_code = 'AUTOCALL_OBS_1_AT_100' "
                    "AND action.action_type = 'PAY_COMPONENT'"
                )
            ).mappings().one()
            autocall_component_terms_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.structured_product_component_terms "
                    "WHERE structured_product_component_terms_id = :component_terms_id"
                ),
                {"component_terms_id": str(DEMO_IDS["autocall_coupon_component_terms"])},
            )
            autocall_terms_link_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.instrument_composition "
                    "WHERE parent_instrument_node_id = :parent_id "
                    "AND structured_product_terms_id IN ("
                    "  SELECT structured_product_terms_id FROM secm.structured_product_terms "
                    "  WHERE instrument_node_id = :parent_id AND is_current = true"
                    ")"
                ),
                {"parent_id": str(DEMO_IDS["autocall_instrument_node"])},
            )

        self.assertGreaterEqual(instrument_count, 5)
        self.assertGreaterEqual(future_link_count, 1)
        self.assertGreaterEqual(fx_forward_count, 1)
        self.assertEqual(autocall_group_count, 1)
        self.assertEqual(autocall_member_count, 2)
        self.assertEqual(autocall_action_count, 2)
        self.assertEqual(autocall_coupon_action_target["target_scope"], "PARENT")
        self.assertIsNone(autocall_coupon_action_target["target_composition_id"])
        self.assertEqual(autocall_coupon_action_target["payout_multiplicity"], "ONCE_PER_PARENT")
        self.assertEqual(autocall_component_terms_count, 1)
        self.assertGreaterEqual(autocall_terms_link_count, 3)

    def test_swap_fixtures_cover_bond_qis_and_structured_product_total_return_swaps(self) -> None:
        expected_ids = {
            "sonia_rate_index_node",
            "qis_index_node",
            "bond_total_return_swap_node",
            "qis_total_return_swap_node",
            "autocall_total_return_swap_node",
            "bond_total_return_performance_leg",
            "bond_total_return_funding_leg",
            "qis_total_return_performance_leg",
            "qis_total_return_funding_leg",
            "autocall_total_return_performance_leg",
            "autocall_total_return_funding_leg",
        }
        self.assertTrue(expected_ids.issubset(DEMO_IDS))

        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT l.leg_role, l.pay_receive, l.reference_node_id, l.return_profile_id, l.currency_id "
                    "FROM secm.swap_leg l "
                    "WHERE l.swap_instrument_node_id = ANY(:swap_ids)"
                ),
                {
                    "swap_ids": [
                        DEMO_IDS["bond_total_return_swap_node"],
                        DEMO_IDS["qis_total_return_swap_node"],
                        DEMO_IDS["autocall_total_return_swap_node"],
                    ]
                },
            ).mappings().all()

        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(row["leg_role"] == "PERFORMANCE" for row in rows), 3)
        self.assertEqual(sum(row["leg_role"] == "FUNDING" for row in rows), 3)
        self.assertTrue(all(row["pay_receive"] in {"PAY", "RECEIVE"} for row in rows))
        self.assertTrue(all(row["reference_node_id"] is not None for row in rows))
        self.assertTrue(all(row["return_profile_id"] is not None for row in rows if row["leg_role"] == "PERFORMANCE"))
        self.assertTrue(all(row["currency_id"] is not None for row in rows if row["leg_role"] == "FUNDING"))

    def test_vanilla_option_fixtures_cover_underlying_strike_exercise_and_unit_terms(self) -> None:
        expected_ids = {
            "vanilla_equity_option_node",
            "vanilla_equity_option_listing",
            "vanilla_index_option_node",
            "vanilla_bermudan_option_node",
            "vanilla_bermudan_option_schedule",
            "vanilla_index_reference_node",
        }
        self.assertTrue(expected_ids.issubset(DEMO_IDS))

        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT o.instrument_node_id, o.option_type, o.exercise_style, "
                    "o.strike_basis, o.settlement_method, o.settlement_currency_id, "
                    "o.exercise_schedule_id, u.unit_multiplier "
                    "FROM secm.option_terms o "
                    "JOIN secm.instrument_contract_unit_terms u "
                    "  ON u.instrument_node_id = o.instrument_node_id "
                    "WHERE o.instrument_node_id = ANY(:option_ids) "
                    "ORDER BY o.instrument_node_id"
                ),
                {
                    "option_ids": [
                        DEMO_IDS["vanilla_equity_option_node"],
                        DEMO_IDS["vanilla_index_option_node"],
                        DEMO_IDS["vanilla_bermudan_option_node"],
                    ]
                },
            ).mappings().all()
            exercise_events = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.schedule_event "
                    "WHERE schedule_id = :schedule_id"
                ),
                {"schedule_id": DEMO_IDS["vanilla_bermudan_option_schedule"]},
            )

        self.assertEqual(len(rows), 3)
        self.assertEqual({row["option_type"] for row in rows}, {"CALL", "PUT"})
        self.assertEqual({row["exercise_style"] for row in rows}, {"EUROPEAN", "BERMUDAN"})
        self.assertIn("INDEX_POINTS", {row["strike_basis"] for row in rows})
        self.assertIn("CASH", {row["settlement_method"] for row in rows})
        bermudan = next(row for row in rows if row["exercise_style"] == "BERMUDAN")
        self.assertEqual(bermudan["exercise_schedule_id"], DEMO_IDS["vanilla_bermudan_option_schedule"])
        self.assertEqual(exercise_events, 2)

    def test_dynamic_strike_option_fixture_keeps_resets_and_fixings_separate(self) -> None:
        expected_ids = {
            "vanilla_reset_option_node",
            "vanilla_reset_option_terms",
            "vanilla_reset_option_schedule",
            "vanilla_reset_option_schedule_event_1",
            "vanilla_reset_option_schedule_event_2",
            "vanilla_reset_option_rule_1",
            "vanilla_reset_option_rule_2",
            "vanilla_reset_option_fixing_1",
            "vanilla_reset_option_fixing_2",
        }
        self.assertTrue(expected_ids.issubset(DEMO_IDS))

        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            terms = connection.execute(
                text(
                    "SELECT strike_mode, strike_value, strike_reset_schedule_id "
                    "FROM secm.option_terms WHERE option_terms_id = :terms_id"
                ),
                {"terms_id": DEMO_IDS["vanilla_reset_option_terms"]},
            ).mappings().one()
            rule_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.option_strike_reset_rule "
                    "WHERE option_terms_id = :terms_id"
                ),
                {"terms_id": DEMO_IDS["vanilla_reset_option_terms"]},
            )
            fixing_count = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.option_strike_fixing f "
                    "JOIN secm.option_strike_reset_rule r "
                    "  ON r.option_strike_reset_rule_id = f.option_strike_reset_rule_id "
                    "WHERE r.option_terms_id = :terms_id AND f.status = 'ACCEPTED'"
                ),
                {"terms_id": DEMO_IDS["vanilla_reset_option_terms"]},
            )

        self.assertEqual(terms["strike_mode"], "RESET")
        self.assertIsNone(terms["strike_value"])
        self.assertEqual(terms["strike_reset_schedule_id"], DEMO_IDS["vanilla_reset_option_schedule"])
        self.assertEqual(rule_count, 2)
        self.assertEqual(fixing_count, 2)

    def test_fund_share_class_fixture_has_t_plus_one_published_official_nav(self) -> None:
        expected_ids = {
            "demo_fund_node",
            "demo_share_class_instrument_node",
            "demo_fund_share_class_terms",
            "demo_fund_nav_series",
            "demo_fund_nav_observation",
        }
        self.assertTrue(expected_ids.issubset(DEMO_IDS))

        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT nav_publication_lag_business_days "
                    "FROM secm.fund_share_class_terms "
                    "WHERE fund_share_class_terms_id = :terms_id"
                ),
                {"terms_id": DEMO_IDS["demo_fund_share_class_terms"]},
            ).one()
        self.assertEqual(row.nav_publication_lag_business_days, 1)

    def test_bond_fixtures_resolve_legacy_day_count_text_to_governed_reference(self) -> None:
        engine = create_engine(
            os.environ.get(
                "DATABASE_URL",
                os.environ["DATABASE_URL"],
            )
        )
        load_demo_data(engine)
        with engine.connect() as connection:
            unresolved = connection.scalar(
                text(
                    "SELECT count(*) FROM secm.bond_terms "
                    "WHERE day_count_convention = 'ACT_ACT_ICMA' "
                    "AND day_count_convention_id IS NULL"
                )
            )
        self.assertEqual(unresolved, 0)
