"""Deterministic synthetic operating scenarios for the Security Master draft."""

from datetime import date, datetime, timezone
import json
from uuid import UUID, NAMESPACE_URL, uuid5

from sqlalchemy import Connection, Engine, select, text, update
from sqlalchemy.dialects.postgresql import insert

from . import models as m
from .seed_data import seed_defaults


DEMO_IDS = {
    "fortem_entity": UUID("00000000-0000-7000-8000-000000000001"),
    "fortem_organisation": UUID("00000000-0000-7000-8000-000000000002"),
    "hsbc_entity": UUID("00000000-0000-7000-8000-000000000003"),
    "hsbc_organisation": UUID("00000000-0000-7000-8000-000000000004"),
    "lseg_entity": UUID("00000000-0000-7000-8000-000000000005"),
    "lseg_organisation": UUID("00000000-0000-7000-8000-000000000006"),
    "bank_a_entity": UUID("00000000-0000-7000-8000-000000000007"),
    "bank_a_organisation": UUID("00000000-0000-7000-8000-000000000008"),
    "custodian_b_entity": UUID("00000000-0000-7000-8000-000000000009"),
    "custodian_b_organisation": UUID("00000000-0000-7000-8000-000000000010"),
    "tenant": UUID("00000000-0000-7000-8000-000000000011"),
    "gbp_currency_node": UUID("00000000-0000-7000-8000-000000000012"),
    "gbp_currency": UUID("00000000-0000-7000-8000-000000000013"),
    "xlon_venue": UUID("00000000-0000-7000-8000-000000000014"),
    "hsbc_instrument_node": UUID("00000000-0000-7000-8000-000000000015"),
    "hsbc_xlon_listing_node": UUID("00000000-0000-7000-8000-000000000016"),
    "data_provider": UUID("00000000-0000-7000-8000-000000000017"),
    "provider_product": UUID("00000000-0000-7000-8000-000000000018"),
    "dataset": UUID("00000000-0000-7000-8000-000000000019"),
    "data_licence": UUID("00000000-0000-7000-8000-000000000020"),
    "source_system": UUID("00000000-0000-7000-8000-000000000021"),
    "source_payload": UUID("00000000-0000-7000-8000-000000000022"),
    "bank_a_namespace": UUID("00000000-0000-7000-8000-000000000023"),
    "custodian_b_namespace": UUID("00000000-0000-7000-8000-000000000024"),
    "fortem_legacy_namespace": UUID("00000000-0000-7000-8000-000000000025"),
    "bank_a_hsbc_mapping": UUID("00000000-0000-7000-8000-000000000026"),
    "custodian_b_hsbc_mapping": UUID("00000000-0000-7000-8000-000000000027"),
    "fortem_hsbc_mapping": UUID("00000000-0000-7000-8000-000000000028"),
    "valuation_cut": UUID("00000000-0000-7000-8000-000000000029"),
    "market_data_series": UUID("00000000-0000-7000-8000-000000000030"),
    "market_data_observation": UUID("00000000-0000-7000-8000-000000000031"),
    "strategy": UUID("00000000-0000-7000-8000-000000000032"),
    "position_snapshot": UUID("00000000-0000-7000-8000-000000000033"),
    "position_line": UUID("00000000-0000-7000-8000-000000000034"),
    "valuation_policy": UUID("00000000-0000-7000-8000-000000000035"),
    "valuation_policy_rule": UUID("00000000-0000-7000-8000-000000000036"),
    "resolution_snapshot": UUID("00000000-0000-7000-8000-000000000037"),
    "resolution_item": UUID("00000000-0000-7000-8000-000000000038"),
    "nav_calculation_run": UUID("00000000-0000-7000-8000-000000000039"),
    "nav_input_snapshot": UUID("00000000-0000-7000-8000-000000000040"),
    "nav_input_item": UUID("00000000-0000-7000-8000-000000000041"),
    "nav_valuation_line": UUID("00000000-0000-7000-8000-000000000042"),
    "nav_result": UUID("00000000-0000-7000-8000-000000000043"),
    "nav_reconciliation": UUID("00000000-0000-7000-8000-000000000044"),
    "gbp_currency_scope": UUID("00000000-0000-7000-8000-000000000045"),
    "hsbc_instrument_scope": UUID("00000000-0000-7000-8000-000000000046"),
    "hsbc_xlon_listing_scope": UUID("00000000-0000-7000-8000-000000000047"),
    "eur_currency_node": UUID("00000000-0000-7000-8000-000000000048"),
    "eur_currency": UUID("00000000-0000-7000-8000-000000000049"),
    "multi_asset_dataset": UUID("00000000-0000-7000-8000-000000000050"),
    "bond_instrument_node": UUID("00000000-0000-7000-8000-000000000051"),
    "bond_dates": UUID("00000000-0000-7000-8000-000000000052"),
    "bond_series": UUID("00000000-0000-7000-8000-000000000053"),
    "bond_observation": UUID("00000000-0000-7000-8000-000000000054"),
    "fx_forward_instrument_node": UUID("00000000-0000-7000-8000-000000000055"),
    "fx_forward_dates": UUID("00000000-0000-7000-8000-000000000056"),
    "fx_forward_series": UUID("00000000-0000-7000-8000-000000000057"),
    "fx_forward_observation": UUID("00000000-0000-7000-8000-000000000058"),
    "future_family_node": UUID("00000000-0000-7000-8000-000000000059"),
    "future_family": UUID("00000000-0000-7000-8000-000000000060"),
    "future_instrument_node": UUID("00000000-0000-7000-8000-000000000061"),
    "future_listing_node": UUID("00000000-0000-7000-8000-000000000062"),
    "future_dates": UUID("00000000-0000-7000-8000-000000000063"),
    "future_series": UUID("00000000-0000-7000-8000-000000000064"),
    "future_observation": UUID("00000000-0000-7000-8000-000000000065"),
    "autocall_instrument_node": UUID("00000000-0000-7000-8000-000000000066"),
    "autocall_terms": UUID("00000000-0000-7000-8000-000000000067"),
    "autocall_dates": UUID("00000000-0000-7000-8000-000000000068"),
    "autocall_schedule": UUID("00000000-0000-7000-8000-000000000069"),
    "autocall_schedule_event_1": UUID("00000000-0000-7000-8000-000000000070"),
    "autocall_schedule_event_2": UUID("00000000-0000-7000-8000-000000000071"),
    "autocall_condition_group": UUID("00000000-0000-7000-8000-000000000256"),
    "autocall_hsbc_barrier": UUID("00000000-0000-7000-8000-000000000257"),
    "autocall_eurostoxx_barrier": UUID("00000000-0000-7000-8000-000000000258"),
    "autocall_coupon_action": UUID("00000000-0000-7000-8000-000000000259"),
    "autocall_redemption_action": UUID("00000000-0000-7000-8000-000000000260"),
    "autocall_coupon_component_node": UUID("00000000-0000-7000-8000-000000000261"),
    "autocall_hsbc_composition": UUID("00000000-0000-7000-8000-000000000262"),
    "autocall_eurostoxx_composition": UUID("00000000-0000-7000-8000-000000000263"),
    "autocall_coupon_composition": UUID("00000000-0000-7000-8000-000000000264"),
    "autocall_coupon_programme": UUID("00000000-0000-7000-8000-000000000265"),
    "autocall_coupon_period_1": UUID("00000000-0000-7000-8000-000000000266"),
    "autocall_coupon_period_2": UUID("00000000-0000-7000-8000-000000000267"),
    "autocall_coupon_component_terms": UUID("00000000-0000-7000-8000-000000000268"),
    "demo_fund_node": UUID("00000000-0000-7000-8000-000000000075"),
    "demo_share_class_instrument_node": UUID("00000000-0000-7000-8000-000000000076"),
    "demo_fund_share_class_terms": UUID("00000000-0000-7000-8000-000000000077"),
    "demo_fund_nav_series": UUID("00000000-0000-7000-8000-000000000078"),
    "demo_fund_nav_observation": UUID("00000000-0000-7000-8000-000000000079"),
    "demo_fund_nav_policy_rule": UUID("00000000-0000-7000-8000-000000000080"),
    "demo_bond_terms": UUID("00000000-0000-7000-8000-000000000081"),
    "xlon_venue_mic": UUID("00000000-0000-7000-8000-000000000082"),
    "demo_user_account": UUID("00000000-0000-7000-8000-000000000083"),
    "pending_mapping_proposal": UUID("00000000-0000-7000-8000-000000000084"),
    "demo_tenant_membership": UUID("00000000-0000-7000-8000-000000000085"),
    "second_tenant": UUID("00000000-0000-7000-8000-000000000302"),
    "second_tenant_membership": UUID("00000000-0000-7000-8000-000000000303"),
    "platform_admin_user_account": UUID("00000000-0000-7000-8000-000000000304"),
    "platform_admin_authority": UUID("00000000-0000-7000-8000-000000000305"),
    "abc_daily_valuation_profile": UUID("00000000-0000-7000-8000-000000000269"),
    "abc_daily_accounting_profile": UUID("00000000-0000-7000-8000-000000000270"),
    "abc_share_class_valuation_mapping": UUID("00000000-0000-7000-8000-000000000271"),
    "abc_fund_accounting_mapping": UUID("00000000-0000-7000-8000-000000000272"),
    # Cutoff-aware market-data fixtures.
    "usd_currency_node": UUID("00000000-0000-7000-8000-000000000086"),
    "usd_currency": UUID("00000000-0000-7000-8000-000000000087"),
    "uk_fx_cut": UUID("00000000-0000-7000-8000-000000000088"),
    "us_fx_cut": UUID("00000000-0000-7000-8000-000000000089"),
    "gbpusd_fx_pair_node": UUID("00000000-0000-7000-8000-000000000090"),
    "uk_gbpusd_series": UUID("00000000-0000-7000-8000-000000000091"),
    "us_gbpusd_series": UUID("00000000-0000-7000-8000-000000000092"),
    "uk_fx_observation_before_cut": UUID("00000000-0000-7000-8000-000000000093"),
    "uk_fx_observation_after_cut": UUID("00000000-0000-7000-8000-000000000094"),
    "us_fx_observation_before_cut": UUID("00000000-0000-7000-8000-000000000095"),
    "us_fx_observation_after_cut": UUID("00000000-0000-7000-8000-000000000096"),
    "uk_fund_strategy": UUID("00000000-0000-7000-8000-000000000097"),
    "us_fund_strategy": UUID("00000000-0000-7000-8000-000000000098"),
    "uk_fund_policy": UUID("00000000-0000-7000-8000-000000000099"),
    "us_fund_policy": UUID("00000000-0000-7000-8000-000000000100"),
    "uk_fund_fx_policy_rule": UUID("00000000-0000-7000-8000-000000000101"),
    "us_fund_fx_policy_rule": UUID("00000000-0000-7000-8000-000000000102"),
    "listing_observation_20260826": UUID("00000000-0000-7000-8000-000000000103"),
    "listing_observation_20260827": UUID("00000000-0000-7000-8000-000000000104"),
    "bond_observation_20260826": UUID("00000000-0000-7000-8000-000000000105"),
    "bond_observation_20260827": UUID("00000000-0000-7000-8000-000000000106"),
    "bond_observation_20260828": UUID("00000000-0000-7000-8000-000000000107"),
    "uk_gbpusd_quote_dimension": UUID("00000000-0000-7000-8000-000000000108"),
    "uk_gbpusd_session_dimension": UUID("00000000-0000-7000-8000-000000000109"),
    "us_gbpusd_quote_dimension": UUID("00000000-0000-7000-8000-000000000110"),
    "us_gbpusd_session_dimension": UUID("00000000-0000-7000-8000-000000000111"),
    # Broad MVP market-data and portfolio universe. Generated observations use
    # stable UUID5 values derived from their series/date keys, so the manifest
    # can be reloaded without storing thousands of IDs here.
    "mvp_bloomberg_entity": UUID("00000000-0000-7000-8000-000000000112"),
    "mvp_bloomberg_organisation": UUID("00000000-0000-7000-8000-000000000113"),
    "mvp_bloomberg_provider": UUID("00000000-0000-7000-8000-000000000114"),
    "mvp_bloomberg_product": UUID("00000000-0000-7000-8000-000000000115"),
    "mvp_bloomberg_dataset": UUID("00000000-0000-7000-8000-000000000116"),
    "mvp_bloomberg_licence": UUID("00000000-0000-7000-8000-000000000117"),
    "mvp_yahoo_entity": UUID("00000000-0000-7000-8000-000000000118"),
    "mvp_yahoo_organisation": UUID("00000000-0000-7000-8000-000000000119"),
    "mvp_yahoo_provider": UUID("00000000-0000-7000-8000-000000000120"),
    "mvp_yahoo_product": UUID("00000000-0000-7000-8000-000000000121"),
    "mvp_yahoo_dataset": UUID("00000000-0000-7000-8000-000000000122"),
    "mvp_yahoo_licence": UUID("00000000-0000-7000-8000-000000000123"),
    "mvp_lseg_provider": UUID("00000000-0000-7000-8000-000000000124"),
    "mvp_lseg_product": UUID("00000000-0000-7000-8000-000000000125"),
    "mvp_lseg_dataset": UUID("00000000-0000-7000-8000-000000000126"),
    "mvp_lseg_licence": UUID("00000000-0000-7000-8000-000000000127"),
    "mvp_london_calendar": UUID("00000000-0000-7000-8000-000000000128"),
    "mvp_new_york_calendar": UUID("00000000-0000-7000-8000-000000000129"),
    "mvp_europe_calendar": UUID("00000000-0000-7000-8000-000000000130"),
    "mvp_fx_calendar": UUID("00000000-0000-7000-8000-000000000131"),
    "mvp_nyse_venue": UUID("00000000-0000-7000-8000-000000000132"),
    "mvp_xetr_venue": UUID("00000000-0000-7000-8000-000000000133"),
    "mvp_nyse_mic": UUID("00000000-0000-7000-8000-000000000134"),
    "mvp_xetr_mic": UUID("00000000-0000-7000-8000-000000000135"),
    "mvp_us_equity_node": UUID("00000000-0000-7000-8000-000000000136"),
    "mvp_us_equity_listing": UUID("00000000-0000-7000-8000-000000000137"),
    "mvp_eu_equity_node": UUID("00000000-0000-7000-8000-000000000138"),
    "mvp_eu_equity_listing": UUID("00000000-0000-7000-8000-000000000139"),
    "mvp_us_bond_node": UUID("00000000-0000-7000-8000-000000000140"),
    "mvp_us_bond_dates": UUID("00000000-0000-7000-8000-000000000141"),
    "mvp_us_bond_terms": UUID("00000000-0000-7000-8000-000000000142"),
    "mvp_eu_bond_node": UUID("00000000-0000-7000-8000-000000000143"),
    "mvp_eu_bond_dates": UUID("00000000-0000-7000-8000-000000000144"),
    "mvp_eu_bond_terms": UUID("00000000-0000-7000-8000-000000000145"),
    "mvp_future_family_node": UUID("00000000-0000-7000-8000-000000000146"),
    "mvp_future_family": UUID("00000000-0000-7000-8000-000000000147"),
    "mvp_future_dec_node": UUID("00000000-0000-7000-8000-000000000148"),
    "mvp_future_instrument": UUID("00000000-0000-7000-8000-000000000162"),
    "mvp_future_dec_listing": UUID("00000000-0000-7000-8000-000000000149"),
    "mvp_future_mar_node": UUID("00000000-0000-7000-8000-000000000150"),
    "mvp_future_mar_listing": UUID("00000000-0000-7000-8000-000000000151"),
    "mvp_fx_forward_instrument": UUID("00000000-0000-7000-8000-000000000152"),
    "mvp_fx_forward_dates": UUID("00000000-0000-7000-8000-000000000153"),
    "mvp_gbpusd_fx_pair_node": UUID("00000000-0000-7000-8000-000000000154"),
    "mvp_eurusd_fx_pair_node": UUID("00000000-0000-7000-8000-000000000155"),
    "mvp_gbpusd_uk_cut": UUID("00000000-0000-7000-8000-000000000156"),
    "mvp_gbpusd_us_cut": UUID("00000000-0000-7000-8000-000000000157"),
    "mvp_eurusd_uk_cut": UUID("00000000-0000-7000-8000-000000000158"),
    "mvp_eurusd_us_cut": UUID("00000000-0000-7000-8000-000000000159"),
    "mvp_us_strategy": UUID("00000000-0000-7000-8000-000000000160"),
    "mvp_uk_strategy": UUID("00000000-0000-7000-8000-000000000161"),
    "equity_automation_policy": UUID("00000000-0000-7000-8000-000000000163"),
    # Canonical venue catalogue used by the onboarding form.
    "xpar_venue": UUID("00000000-0000-7000-8000-000000000164"),
    "xpar_venue_mic": UUID("00000000-0000-7000-8000-000000000165"),
    "xnas_venue": UUID("00000000-0000-7000-8000-000000000170"),
    "xnas_venue_mic": UUID("00000000-0000-7000-8000-000000000171"),
    "kraken_venue": UUID("00000000-0000-7000-8000-000000000172"),
    "kraken_venue_code": UUID("00000000-0000-7000-8000-000000000173"),
    "mvp_index_family_node": UUID("00000000-0000-7000-8000-000000000174"),
    "mvp_index_family": UUID("00000000-0000-7000-8000-000000000175"),
    "mvp_sp500_price_index_node": UUID("00000000-0000-7000-8000-000000000176"),
    "mvp_sp500_net_index_node": UUID("00000000-0000-7000-8000-000000000177"),
    "mvp_sp500_price_methodology": UUID("00000000-0000-7000-8000-000000000178"),
    "mvp_sp500_net_methodology": UUID("00000000-0000-7000-8000-000000000179"),
    "mvp_etf_node": UUID("00000000-0000-7000-8000-000000000180"),
    "mvp_etf_listing": UUID("00000000-0000-7000-8000-000000000181"),
    "mvp_etf_terms": UUID("00000000-0000-7000-8000-000000000182"),
    "mvp_etf_fund_node": UUID("00000000-0000-7000-8000-000000000183"),
    "mvp_etf_share_class_terms": UUID("00000000-0000-7000-8000-000000000184"),
    "mvp_etf_snapshot": UUID("00000000-0000-7000-8000-000000000185"),
    "mvp_etc_node": UUID("00000000-0000-7000-8000-000000000186"),
    "mvp_etc_listing": UUID("00000000-0000-7000-8000-000000000187"),
    "mvp_etc_terms": UUID("00000000-0000-7000-8000-000000000188"),
    "mvp_etn_node": UUID("00000000-0000-7000-8000-000000000189"),
    "mvp_etn_listing": UUID("00000000-0000-7000-8000-000000000190"),
    "mvp_etn_terms": UUID("00000000-0000-7000-8000-000000000191"),
    "mvp_gold_commodity_node": UUID("00000000-0000-7000-8000-000000000192"),
    "sonia_rate_index_node": UUID("00000000-0000-7000-8000-000000000193"),
    "qis_index_node": UUID("00000000-0000-7000-8000-000000000194"),
    "bond_total_return_swap_node": UUID("00000000-0000-7000-8000-000000000195"),
    "bond_total_return_swap_dates": UUID("00000000-0000-7000-8000-000000000196"),
    "bond_total_return_schedule": UUID("00000000-0000-7000-8000-000000000197"),
    "bond_total_return_performance_leg": UUID("00000000-0000-7000-8000-000000000198"),
    "bond_total_return_funding_leg": UUID("00000000-0000-7000-8000-000000000199"),
    "qis_total_return_swap_node": UUID("00000000-0000-7000-8000-000000000200"),
    "qis_total_return_swap_dates": UUID("00000000-0000-7000-8000-000000000201"),
    "qis_total_return_schedule": UUID("00000000-0000-7000-8000-000000000202"),
    "qis_total_return_performance_leg": UUID("00000000-0000-7000-8000-000000000203"),
    "qis_total_return_funding_leg": UUID("00000000-0000-7000-8000-000000000204"),
    "autocall_total_return_swap_node": UUID("00000000-0000-7000-8000-000000000205"),
    "autocall_total_return_swap_dates": UUID("00000000-0000-7000-8000-000000000206"),
    "autocall_total_return_schedule": UUID("00000000-0000-7000-8000-000000000207"),
    "autocall_total_return_performance_leg": UUID("00000000-0000-7000-8000-000000000208"),
    "autocall_total_return_funding_leg": UUID("00000000-0000-7000-8000-000000000209"),
    "bond_total_return_reset_event": UUID("00000000-0000-7000-8000-000000000210"),
    "qis_total_return_reset_event": UUID("00000000-0000-7000-8000-000000000211"),
    "autocall_total_return_reset_event": UUID("00000000-0000-7000-8000-000000000212"),
    # Vanilla option fixtures: a listed physical equity call, a cash-settled
    # index-point put, and a Bermudan option whose dates live in a schedule.
    "vanilla_equity_option_node": UUID("00000000-0000-7000-8000-000000000213"),
    "vanilla_equity_option_listing": UUID("00000000-0000-7000-8000-000000000214"),
    "vanilla_equity_option_dates": UUID("00000000-0000-7000-8000-000000000215"),
    "vanilla_equity_option_contract_unit_terms": UUID("00000000-0000-7000-8000-000000000216"),
    "vanilla_index_option_node": UUID("00000000-0000-7000-8000-000000000217"),
    "vanilla_index_option_dates": UUID("00000000-0000-7000-8000-000000000218"),
    "vanilla_index_option_contract_unit_terms": UUID("00000000-0000-7000-8000-000000000219"),
    "vanilla_bermudan_option_node": UUID("00000000-0000-7000-8000-000000000220"),
    "vanilla_bermudan_option_dates": UUID("00000000-0000-7000-8000-000000000221"),
    "vanilla_bermudan_option_contract_unit_terms": UUID("00000000-0000-7000-8000-000000000222"),
    "vanilla_bermudan_option_schedule": UUID("00000000-0000-7000-8000-000000000223"),
    "vanilla_bermudan_option_schedule_event_1": UUID("00000000-0000-7000-8000-000000000224"),
    "vanilla_bermudan_option_schedule_event_2": UUID("00000000-0000-7000-8000-000000000225"),
    "vanilla_index_reference_node": UUID("00000000-0000-7000-8000-000000000226"),
    "vanilla_reset_option_node": UUID("00000000-0000-7000-8000-000000000227"),
    "vanilla_reset_option_terms": UUID("00000000-0000-7000-8000-000000000228"),
    "vanilla_reset_option_dates": UUID("00000000-0000-7000-8000-000000000229"),
    "vanilla_reset_option_contract_unit_terms": UUID("00000000-0000-7000-8000-000000000230"),
    "vanilla_reset_option_schedule": UUID("00000000-0000-7000-8000-000000000231"),
    "vanilla_reset_option_schedule_event_1": UUID("00000000-0000-7000-8000-000000000232"),
    "vanilla_reset_option_schedule_event_2": UUID("00000000-0000-7000-8000-000000000233"),
    "vanilla_reset_option_rule_1": UUID("00000000-0000-7000-8000-000000000234"),
    "vanilla_reset_option_rule_2": UUID("00000000-0000-7000-8000-000000000235"),
    "vanilla_reset_option_fixing_1": UUID("00000000-0000-7000-8000-000000000236"),
    "vanilla_reset_option_fixing_2": UUID("00000000-0000-7000-8000-000000000237"),
    # Cryptoasset identity/deployment fixtures.
    "mvp_btc_node": UUID("00000000-0000-7000-8000-000000000240"),
    "mvp_btc_currency": UUID("00000000-0000-7000-8000-000000000241"),
    "mvp_btc_terms": UUID("00000000-0000-7000-8000-000000000242"),
    "mvp_btc_bitcoin_deployment": UUID("00000000-0000-7000-8000-000000000243"),
    "mvp_usdc_node": UUID("00000000-0000-7000-8000-000000000244"),
    "mvp_usdc_currency": UUID("00000000-0000-7000-8000-000000000245"),
    "mvp_usdc_terms": UUID("00000000-0000-7000-8000-000000000246"),
    "mvp_usdc_ethereum_deployment": UUID("00000000-0000-7000-8000-000000000247"),
    "mvp_usdc_solana_deployment": UUID("00000000-0000-7000-8000-000000000248"),
    # Crypto venue markets and listing-level trading identifiers.
    "coinbase_venue": UUID("00000000-0000-7000-8000-000000000249"),
    "coinbase_venue_code": UUID("00000000-0000-7000-8000-000000000250"),
    "binance_venue": UUID("00000000-0000-7000-8000-000000000251"),
    "binance_venue_code": UUID("00000000-0000-7000-8000-000000000252"),
    "mvp_btc_coinbase_usd_listing": UUID("00000000-0000-7000-8000-000000000253"),
    "mvp_btc_binance_usdc_listing": UUID("00000000-0000-7000-8000-000000000254"),
    "mvp_usdc_kraken_usd_listing": UUID("00000000-0000-7000-8000-000000000255"),
    # Tenant operating profiles and separately governed module entitlements.
    "fund_manager_profile_assignment": UUID("00000000-0000-7000-8000-000000000273"),
    "trading_book_manager_profile_assignment": UUID("00000000-0000-7000-8000-000000000274"),
    "security_master_module_entitlement": UUID("00000000-0000-7000-8000-000000000275"),
    "trading_module_entitlement": UUID("00000000-0000-7000-8000-000000000276"),
    "valuation_module_entitlement": UUID("00000000-0000-7000-8000-000000000277"),
    "fund_management_module_entitlement": UUID("00000000-0000-7000-8000-000000000278"),
}


def _insert_once(connection: Connection, table, values: dict) -> None:
    """Insert a fixed synthetic row once, preserving previously loaded demo data."""

    connection.execute(insert(table).values(values).on_conflict_do_nothing())


def _catalogue_id(connection: Connection, table, code_column, code: str):
    return connection.execute(select(table.primary_key.columns.values()[0]).where(code_column == code)).scalar_one()


def create_schema(engine: Engine) -> None:
    """Create required PostgreSQL schemas and the full SQLAlchemy draft without migrations."""

    with engine.begin() as connection:
        for schema_name in ("secm", "trd", "md", "ten", "ing", "nav", "cal", "cfg"):
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        m.metadata.create_all(connection)
        seed_defaults(connection)


def load_demo_data(engine: Engine) -> None:
    """Load an idempotent synthetic HSBC XLON-to-Soft-NAV scenario."""

    today = date(2026, 8, 28)
    now = datetime(2026, 8, 28, 16, 30, tzinfo=timezone.utc)

    with engine.begin() as connection:
        seed_defaults(connection)
        node_instrument = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "INSTRUMENT")
        node_listing = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "LISTING")
        node_currency = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "CURRENCY")
        node_fund = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FUND")
        node_index = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "INDEX")
        node_rate_index = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "RATE_INDEX")
        equity_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "EQUITY")
        day_count_convention_id = _catalogue_id(connection, m.day_count_convention, m.day_count_convention.c.code, "ACT_ACT_ICMA")
        fund_manager_profile_id = _catalogue_id(connection, m.operating_profile, m.operating_profile.c.profile_code, "FUND_MANAGER")
        trading_book_manager_profile_id = _catalogue_id(connection, m.operating_profile, m.operating_profile.c.profile_code, "TRADING_BOOK_MANAGER")
        module_ids = {
            code: _catalogue_id(connection, m.platform_module, m.platform_module.c.module_code, code)
            for code in ("SECURITY_MASTER", "TRADING", "VALUATION", "FUND_MANAGEMENT")
        }

        for entity_id, code, name in (
            (DEMO_IDS["fortem_entity"], "FORTEM_DEMO", "Fortem Demo Group"),
            (DEMO_IDS["hsbc_entity"], "HSBC_DEMO", "HSBC Demo Group"),
            (DEMO_IDS["lseg_entity"], "LSEG_DEMO", "LSEG Demo Group"),
            (DEMO_IDS["bank_a_entity"], "BANK_A_DEMO", "Bank A Demo Group"),
            (DEMO_IDS["custodian_b_entity"], "CUSTODIAN_B_DEMO", "Custodian B Demo Group"),
        ):
            _insert_once(connection, m.entity, {"entity_id": entity_id, "entity_code": code, "display_name": name, "legal_name": name, "status": "ACTIVE"})

        for organisation_id, entity_id, kind, name in (
            (DEMO_IDS["fortem_organisation"], DEMO_IDS["fortem_entity"], "LEGAL_ENTITY", "Fortem Demo Management Ltd"),
            (DEMO_IDS["hsbc_organisation"], DEMO_IDS["hsbc_entity"], "LEGAL_ENTITY", "HSBC Demo plc"),
            (DEMO_IDS["lseg_organisation"], DEMO_IDS["lseg_entity"], "VENDOR", "LSEG Demo Data Ltd"),
            (DEMO_IDS["bank_a_organisation"], DEMO_IDS["bank_a_entity"], "CUSTODIAN", "Bank A Demo plc"),
            (DEMO_IDS["custodian_b_organisation"], DEMO_IDS["custodian_b_entity"], "CUSTODIAN", "Custodian B Demo Ltd"),
        ):
            _insert_once(connection, m.organisation, {"organisation_id": organisation_id, "entity_id": entity_id, "organisation_type": kind, "display_name": name, "legal_name": name, "status": "ACTIVE"})

        _insert_once(connection, m.tenant, {"tenant_id": DEMO_IDS["tenant"], "owning_organisation_id": DEMO_IDS["fortem_organisation"], "tenant_code": "FORTEM_DEMO_TENANT", "display_name": "Fortem Demo Tenant", "status": "ACTIVE"})
        _insert_once(connection, m.tenant, {"tenant_id": DEMO_IDS["second_tenant"], "owning_organisation_id": DEMO_IDS["fortem_organisation"], "tenant_code": "FORTEM_SECOND_TENANT", "display_name": "Fortem Second Tenant", "status": "ACTIVE"})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["gbp_currency_node"], "reference_node_type_id": node_currency, "canonical_name": "Pound sterling", "internal_code": "GBP_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.currency, {"currency_id": DEMO_IDS["gbp_currency"], "reference_node_id": DEMO_IDS["gbp_currency_node"], "currency_code": "GBP", "display_name": "Pound sterling", "numeric_code": "826", "minor_unit": 2, "currency_kind": "FIAT", "status": "ACTIVE"})
        _insert_once(connection, m.market_venue, {"market_venue_id": DEMO_IDS["xlon_venue"], "operating_organisation_id": DEMO_IDS["fortem_organisation"], "venue_type": "EXCHANGE", "display_name": "London Stock Exchange (synthetic)", "country_code": "GBR", "city": "London", "timezone_name": "Europe/London", "status": "ACTIVE"})
        _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": DEMO_IDS["xlon_venue_mic"], "market_venue_id": DEMO_IDS["xlon_venue"], "identifier_scheme": "ISO_10383_MIC", "identifier_value": "XLON", "is_primary": True})
        connection.execute(
            update(m.market_venue)
            .where(m.market_venue.c.market_venue_id == DEMO_IDS["xlon_venue"])
            .where(m.market_venue.c.display_name == "London Stock Exchange (synthetic)")
            .values(display_name="London Stock Exchange")
        )
        for venue_id, name, venue_type, country, city, timezone_name, identifier_id, identifier_scheme, identifier_value in (
            (DEMO_IDS["xpar_venue"], "Euronext Paris", "EXCHANGE", "FRA", "Paris", "Europe/Paris", DEMO_IDS["xpar_venue_mic"], "ISO_10383_MIC", "XPAR"),
            (DEMO_IDS["mvp_nyse_venue"], "New York Stock Exchange", "EXCHANGE", "USA", "New York", "America/New_York", DEMO_IDS["mvp_nyse_mic"], "ISO_10383_MIC", "XNYS"),
            (DEMO_IDS["mvp_xetr_venue"], "Xetra", "EXCHANGE", "DEU", "Frankfurt", "Europe/Berlin", DEMO_IDS["mvp_xetr_mic"], "ISO_10383_MIC", "XETR"),
            (DEMO_IDS["xnas_venue"], "Nasdaq", "EXCHANGE", "USA", "New York", "America/New_York", DEMO_IDS["xnas_venue_mic"], "ISO_10383_MIC", "XNAS"),
            (DEMO_IDS["kraken_venue"], "Kraken", "CEX", "USA", "San Francisco", "America/Los_Angeles", DEMO_IDS["kraken_venue_code"], "CRYPTO_EXCHANGE_CODE", "KRAKEN"),
        ):
            _insert_once(connection, m.market_venue, {"market_venue_id": venue_id, "venue_type": venue_type, "display_name": name, "country_code": country, "city": city, "timezone_name": timezone_name, "status": "ACTIVE"})
            _insert_once(connection, m.market_venue_identifier, {"market_venue_identifier_id": identifier_id, "market_venue_id": venue_id, "identifier_scheme": identifier_scheme, "identifier_value": identifier_value, "is_primary": True})
            connection.execute(
                update(m.market_venue)
                .where(m.market_venue.c.market_venue_id == venue_id)
                .where(m.market_venue.c.display_name.like("% (synthetic)"))
                .values(display_name=name, country_code=country, city=city, timezone_name=timezone_name)
            )
        _insert_once(connection, m.user_account, {"user_account_id": DEMO_IDS["demo_user_account"], "account_type": "HUMAN", "status": "ACTIVE"})
        _insert_once(connection, m.user_account, {"user_account_id": DEMO_IDS["platform_admin_user_account"], "account_type": "HUMAN", "status": "ACTIVE"})
        _insert_once(connection, m.tenant_user_account, {"tenant_user_account_id": DEMO_IDS["demo_tenant_membership"], "tenant_id": DEMO_IDS["tenant"], "user_account_id": DEMO_IDS["demo_user_account"], "membership_role": "TENANT_ADMIN", "status": "ACTIVE", "valid_from": date(2026, 1, 1)})
        connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_user_account_id == DEMO_IDS["demo_tenant_membership"]).values(membership_role="TENANT_ADMIN"))
        _insert_once(connection, m.tenant_user_account, {"tenant_user_account_id": DEMO_IDS["second_tenant_membership"], "tenant_id": DEMO_IDS["second_tenant"], "user_account_id": DEMO_IDS["demo_user_account"], "membership_role": "OPERATIONS", "status": "ACTIVE", "valid_from": date(2026, 1, 1)})
        _insert_once(connection, m.platform_user_account, {"platform_user_account_id": DEMO_IDS["platform_admin_authority"], "user_account_id": DEMO_IDS["platform_admin_user_account"], "platform_role": "PLATFORM_ADMIN", "status": "ACTIVE", "valid_from": date(2026, 1, 1)})
        for assignment_id, profile_id in (
            (DEMO_IDS["fund_manager_profile_assignment"], fund_manager_profile_id),
            (DEMO_IDS["trading_book_manager_profile_assignment"], trading_book_manager_profile_id),
        ):
            _insert_once(connection, m.tenant_operating_profile_assignment, {"tenant_operating_profile_assignment_id": assignment_id, "tenant_id": DEMO_IDS["tenant"], "operating_profile_id": profile_id, "assignment_source": "ONBOARDING", "status": "ACTIVE", "approved_by_user_account_id": DEMO_IDS["demo_user_account"], "approved_at_utc": now, "valid_from": today, "recorded_at_utc": now})
        for entitlement_id, module_code in (
            (DEMO_IDS["security_master_module_entitlement"], "SECURITY_MASTER"),
            (DEMO_IDS["trading_module_entitlement"], "TRADING"),
            (DEMO_IDS["valuation_module_entitlement"], "VALUATION"),
            (DEMO_IDS["fund_management_module_entitlement"], "FUND_MANAGEMENT"),
        ):
            _insert_once(connection, m.tenant_module_entitlement, {"tenant_module_entitlement_id": entitlement_id, "tenant_id": DEMO_IDS["tenant"], "platform_module_id": module_ids[module_code], "entitlement_state": "GRANTED", "entitlement_source": "MIGRATION", "approved_by_user_account_id": DEMO_IDS["demo_user_account"], "approved_at_utc": now, "valid_from": today, "recorded_at_utc": now})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["hsbc_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "HSBC Demo ordinary shares", "internal_code": "HSBC_DEMO_ORD", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["hsbc_instrument_node"], "instrument_type_id": equity_type, "asset_class": "EQUITY", "issuer_organisation_id": DEMO_IDS["hsbc_organisation"], "base_currency_id": DEMO_IDS["gbp_currency"], "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "reference_node_type_id": node_listing, "canonical_name": "HSBC Demo on XLON", "internal_code": "HSBC_XLON_DEMO", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.listing, {"listing_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "instrument_node_id": DEMO_IDS["hsbc_instrument_node"], "market_venue_id": DEMO_IDS["xlon_venue"], "trading_currency_id": DEMO_IDS["gbp_currency"], "trading_symbol": "HSD", "quote_factor": 100, "unit_multiplier": 1, "is_primary_listing": True, "status": "ACTIVE"})
        for scope_id, node_id in (
            (DEMO_IDS["gbp_currency_scope"], DEMO_IDS["gbp_currency_node"]),
            (DEMO_IDS["hsbc_instrument_scope"], DEMO_IDS["hsbc_instrument_node"]),
            (DEMO_IDS["hsbc_xlon_listing_scope"], DEMO_IDS["hsbc_xlon_listing_node"]),
        ):
            _insert_once(connection, m.reference_node_scope, {"reference_node_scope_id": scope_id, "reference_node_id": node_id, "scope_type": "SHARED_CANONICAL", "status": "ACTIVE"})

        _insert_once(connection, m.data_provider, {"data_provider_id": DEMO_IDS["data_provider"], "organisation_id": DEMO_IDS["lseg_organisation"], "provider_code": "LSEG_DEMO", "display_name": "LSEG Demo", "status": "ACTIVE"})
        _insert_once(connection, m.provider_product, {"provider_product_id": DEMO_IDS["provider_product"], "data_provider_id": DEMO_IDS["data_provider"], "product_code": "EOD_PRICES", "display_name": "Demo EOD prices", "status": "ACTIVE"})
        _insert_once(connection, m.dataset, {"dataset_id": DEMO_IDS["dataset"], "provider_product_id": DEMO_IDS["provider_product"], "dataset_code": "UK_EQUITIES_EOD", "display_name": "UK equities EOD (synthetic)", "data_domain": "MARKET_DATA", "coverage_description": "Synthetic London-listed equity EOD prices for tests.", "delivery_channel": "FILE", "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.data_licence, {"data_licence_id": DEMO_IDS["data_licence"], "licensor_organisation_id": DEMO_IDS["lseg_organisation"], "licensee_organisation_id": DEMO_IDS["fortem_organisation"], "licence_code": "FORTEM_DEMO_EOD_INTERNAL", "display_name": "Synthetic internal EOD licence", "permitted_use_description": "Synthetic testing only; internal valuation and risk.", "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.dataset_licence_assignment, {"dataset_id": DEMO_IDS["dataset"], "data_licence_id": DEMO_IDS["data_licence"], "licence_role": "ACQUISITION", "valid_from": today, "status": "ACTIVE"})
        _insert_once(connection, m.tenant_dataset_entitlement, {"tenant_id": DEMO_IDS["tenant"], "dataset_id": DEMO_IDS["dataset"], "use_purpose": "VALUATION", "status": "ACTIVE", "valid_from": today})

        _insert_once(connection, m.integration_source_system, {"integration_source_system_id": DEMO_IDS["source_system"], "owning_organisation_id": DEMO_IDS["bank_a_organisation"], "tenant_id": DEMO_IDS["tenant"], "system_code": "BANK_A_STATIC_PROD", "display_name": "Bank A static data production", "source_kind": "BANK", "environment": "PROD", "status": "ACTIVE"})
        _insert_once(connection, m.reference_data_automation_policy, {"reference_data_automation_policy_id": DEMO_IDS["equity_automation_policy"], "policy_code": "BANK_A_EQUITY_CREATE", "display_name": "Bank A equity create policy", "source_system_id": DEMO_IDS["source_system"], "target_object_type": "EQUITY", "operation_type": "CREATE", "min_confidence": 0.95, "required_identifier_schemes": ["ISIN", "FIGI"], "criteria_json": {"requireIssuer": True, "requirePrimaryListing": True}, "auto_approve": True, "tenant_id": DEMO_IDS["tenant"], "valid_from": date(2024, 1, 1), "version_no": 1, "status": "ACTIVE", "approved_by_user_account_id": DEMO_IDS["demo_user_account"], "approved_at_utc": now})
        _insert_once(connection, m.source_payload, {"source_payload_id": DEMO_IDS["source_payload"], "integration_source_system_id": DEMO_IDS["source_system"], "tenant_id": DEMO_IDS["tenant"], "payload_format": "CSV", "external_message_reference": "demo-eod-20260828", "payload_locator": "synthetic://demo/eod-20260828.csv", "payload_sha256": "0" * 64, "source_published_at_utc": now, "received_at_utc": now, "processing_status": "MAPPED"})
        for namespace_id, code in ((DEMO_IDS["bank_a_namespace"], "BANK_A_STATIC_PROD"), (DEMO_IDS["custodian_b_namespace"], "CUSTODIAN_B_ASSET_PROD"), (DEMO_IDS["fortem_legacy_namespace"], "FORTEM_LEGACY")):
            _insert_once(connection, m.external_id_namespace, {"external_id_namespace_id": namespace_id, "integration_source_system_id": DEMO_IDS["source_system"], "namespace_code": code, "external_object_type": "LISTING", "status": "ACTIVE", "valid_from": today})
        for mapping_id, namespace_id, external_id in ((DEMO_IDS["bank_a_hsbc_mapping"], DEMO_IDS["bank_a_namespace"], "ABC"), (DEMO_IDS["custodian_b_hsbc_mapping"], DEMO_IDS["custodian_b_namespace"], "FOO"), (DEMO_IDS["fortem_hsbc_mapping"], DEMO_IDS["fortem_legacy_namespace"], "XYZ")):
            _insert_once(connection, m.external_object_mapping, {"external_object_mapping_id": mapping_id, "external_id_namespace_id": namespace_id, "external_object_type": "LISTING", "external_id_value": external_id, "tenant_id": DEMO_IDS["tenant"], "target_object_type": "LISTING", "target_object_id": DEMO_IDS["hsbc_xlon_listing_node"], "context_market_venue_id": DEMO_IDS["xlon_venue"], "mapping_role": "PRIMARY", "mapping_method": "MANUAL", "status": "VERIFIED", "valid_from": today, "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.reference_data_proposal, {"reference_data_proposal_id": DEMO_IDS["pending_mapping_proposal"], "reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "tenant_id": DEMO_IDS["tenant"], "proposal_type": "IDENTIFIER_MAPPING", "proposed_payload": json.dumps({"namespace": "CUSTODIAN_B_ASSET_PROD", "externalObjectType": "LISTING", "externalId": "PENDING-HSBC-XLON", "targetObjectType": "LISTING", "targetObjectId": str(DEMO_IDS["hsbc_xlon_listing_node"]), "contextMarketVenueId": str(DEMO_IDS["xlon_venue"]), "validFrom": today.isoformat(), "reason": "Synthetic pending mapping for operations queue"}, sort_keys=True), "source_payload_id": DEMO_IDS["source_payload"], "status": "PENDING", "proposed_at_utc": now})

        _insert_once(connection, m.valuation_cut, {"valuation_cut_id": DEMO_IDS["valuation_cut"], "cut_code": "LONDON_CLOSE_DEMO", "display_name": "London close (synthetic)", "timezone_name": "Europe/London", "local_time": "16:30:00", "status": "ACTIVE"})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["market_data_series"], "reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "currency_id": DEMO_IDS["gbp_currency"], "default_dataset_id": DEMO_IDS["dataset"], "valuation_cut_id": DEMO_IDS["valuation_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": True})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["market_data_observation"], "market_data_series_id": DEMO_IDS["market_data_series"], "dataset_id": DEMO_IDS["dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": today, "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": now, "received_at_utc": now, "value": 1023.0, "value_basis": "RAW", "source_timestamp_utc": now, "source_observation_key": "LSEG_DEMO:HSBC_XLON:2026-08-28:CLOSE", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["listing_observation_20260826"], "market_data_series_id": DEMO_IDS["market_data_series"], "dataset_id": DEMO_IDS["dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": date(2026, 8, 26), "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": datetime(2026, 8, 26, 15, 30, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 26, 15, 31, tzinfo=timezone.utc), "value": 1002.5, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 26, 15, 30, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:HSBC_XLON:2026-08-26:CLOSE", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["listing_observation_20260827"], "market_data_series_id": DEMO_IDS["market_data_series"], "dataset_id": DEMO_IDS["dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": date(2026, 8, 27), "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": datetime(2026, 8, 27, 15, 30, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 27, 15, 31, tzinfo=timezone.utc), "value": 1015.0, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 27, 15, 30, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:HSBC_XLON:2026-08-27:CLOSE", "quality_status": "ACCEPTED"})

        fund_share_class_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "FUND_SHARE_CLASS")
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["demo_fund_node"], "reference_node_type_id": node_fund, "canonical_name": "Fortem Demo Income Fund", "internal_code": "FUND_DEMO_INCOME", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.fund, {"fund_reference_node_id": DEMO_IDS["demo_fund_node"], "fund_kind": "STANDALONE", "fund_manager_organisation_id": DEMO_IDS["fortem_organisation"], "domicile_country_code": "GBR", "legal_form": "OEIC", "status": "ACTIVE"})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["demo_share_class_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "Fortem Demo Income Fund I Acc GBP", "internal_code": "FUND_DEMO_I_ACC_GBP", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["demo_share_class_instrument_node"], "instrument_type_id": fund_share_class_type, "asset_class": "FUND", "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.fund_share_class_terms, {"fund_share_class_terms_id": DEMO_IDS["demo_fund_share_class_terms"], "instrument_node_id": DEMO_IDS["demo_share_class_instrument_node"], "fund_reference_node_id": DEMO_IDS["demo_fund_node"], "share_class_code": "I_ACC_GBP", "share_currency_id": DEMO_IDS["gbp_currency"], "income_treatment": "ACCUMULATION", "dealing_frequency": "DAILY", "nav_frequency": "DAILY", "nav_publication_lag_business_days": 1, "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.external_data_mapping_profile, {"external_data_mapping_profile_id": DEMO_IDS["abc_daily_valuation_profile"], "tenant_id": DEMO_IDS["tenant"], "provider_organisation_id": DEMO_IDS["bank_a_organisation"], "integration_source_system_id": DEMO_IDS["source_system"], "profile_code": "ABC_DAILY_VALUATION", "display_name": "ABC daily fund valuation", "operational_context": "VALUATION", "allowed_source_scope": "BOTH", "normalization_mode": "TRIM_UPPER", "parser_contract_version": "v1", "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.external_data_mapping_profile, {"external_data_mapping_profile_id": DEMO_IDS["abc_daily_accounting_profile"], "tenant_id": DEMO_IDS["tenant"], "provider_organisation_id": DEMO_IDS["bank_a_organisation"], "integration_source_system_id": DEMO_IDS["source_system"], "profile_code": "ABC_DAILY_ACCOUNTING", "display_name": "ABC daily fund accounting", "operational_context": "ACCOUNTING", "allowed_source_scope": "FUND", "normalization_mode": "TRIM_UPPER", "parser_contract_version": "v1", "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.external_data_object_mapping, {"external_data_object_mapping_id": DEMO_IDS["abc_share_class_valuation_mapping"], "external_data_mapping_profile_id": DEMO_IDS["abc_daily_valuation_profile"], "source_object_scope": "FUND_SHARE_CLASS", "target_object_type": "FUND_SHARE_CLASS", "target_object_id": DEMO_IDS["demo_share_class_instrument_node"], "external_id_raw": " NAV-I-GBP ", "external_id_normalized": "NAV-I-GBP", "mapping_role": "PRIMARY", "mapping_method": "MANUAL", "status": "APPROVED", "approved_by_user_account_id": DEMO_IDS["demo_user_account"], "approved_at_utc": now, "valid_from": today, "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.external_data_object_mapping, {"external_data_object_mapping_id": DEMO_IDS["abc_fund_accounting_mapping"], "external_data_mapping_profile_id": DEMO_IDS["abc_daily_accounting_profile"], "source_object_scope": "FUND", "target_object_type": "FUND", "target_object_id": DEMO_IDS["demo_fund_node"], "external_id_raw": " ACCT-1042 ", "external_id_normalized": "ACCT-1042", "mapping_role": "PRIMARY", "mapping_method": "MANUAL", "status": "APPROVED", "approved_by_user_account_id": DEMO_IDS["demo_user_account"], "approved_at_utc": now, "valid_from": today, "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["demo_fund_nav_series"], "reference_node_id": DEMO_IDS["demo_share_class_instrument_node"], "series_type": "OFFICIAL_NAV", "value_type": "PRICE", "currency_id": DEMO_IDS["gbp_currency"], "default_dataset_id": DEMO_IDS["dataset"], "valuation_cut_id": DEMO_IDS["valuation_cut"], "source_system_id": "FORTEM_FUND_ADMIN_DEMO", "status": "ACTIVE", "is_official": True})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["demo_fund_nav_observation"], "market_data_series_id": DEMO_IDS["demo_fund_nav_series"], "dataset_id": DEMO_IDS["dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": date(2026, 8, 27), "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": datetime(2026, 8, 27, 16, 30, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc), "value": 101.25, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 28, 8, 45, tzinfo=timezone.utc), "quality_status": "ACCEPTED"})

        _insert_once(connection, m.strategy, {"strategy_id": DEMO_IDS["strategy"], "tenant_id": DEMO_IDS["tenant"], "strategy_code": "DEMO_INCOME", "display_name": "Demo Income Strategy", "strategy_type": "FUND", "base_currency_id": DEMO_IDS["gbp_currency"], "legal_owner_organisation_id": DEMO_IDS["fortem_organisation"], "status": "ACTIVE"})
        connection.execute(
            m.strategy.update()
            .where(m.strategy.c.strategy_id == DEMO_IDS["strategy"])
            .values(tenant_id=DEMO_IDS["tenant"])
        )
        _insert_once(connection, m.position_snapshot, {"position_snapshot_id": DEMO_IDS["position_snapshot"], "tenant_id": DEMO_IDS["tenant"], "strategy_id": DEMO_IDS["strategy"], "as_of_date": today, "as_of_datetime_utc": now, "source_payload_id": DEMO_IDS["source_payload"], "content_hash": "1" * 64, "status": "ACTIVE", "received_at_utc": now})
        _insert_once(connection, m.position_snapshot_line, {"position_snapshot_line_id": DEMO_IDS["position_line"], "position_snapshot_id": DEMO_IDS["position_snapshot"], "reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "external_object_mapping_id": DEMO_IDS["custodian_b_hsbc_mapping"], "quantity": 1000, "quantity_unit": "SHARES", "source_price": 1023.0, "source_market_value": 10230.0, "currency_id": DEMO_IDS["gbp_currency"], "source_line_reference": "demo-line-1"})
        _insert_once(connection, m.valuation_policy, {"valuation_policy_id": DEMO_IDS["valuation_policy"], "tenant_id": DEMO_IDS["tenant"], "policy_code": "DEMO_EOD", "display_name": "Demo EOD valuation", "valuation_cut_id": DEMO_IDS["valuation_cut"], "version_no": 1, "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.valuation_policy_rule, {"valuation_policy_rule_id": DEMO_IDS["valuation_policy_rule"], "valuation_policy_id": DEMO_IDS["valuation_policy"], "rule_sequence": 1, "subject_type": "LISTING", "subject_reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "market_data_series_id": DEMO_IDS["market_data_series"], "series_type": "OFFICIAL_CLOSE", "selection_method": "OFFICIAL", "pricing_date_rule": "SAME_DAY", "lag_business_days": 0, "max_staleness_business_days": 0, "missing_data_action": "FAIL", "dataset_id": DEMO_IDS["dataset"], "status": "ACTIVE"})
        _insert_once(connection, m.valuation_policy_rule, {"valuation_policy_rule_id": DEMO_IDS["demo_fund_nav_policy_rule"], "valuation_policy_id": DEMO_IDS["valuation_policy"], "rule_sequence": 2, "subject_type": "INSTRUMENT", "subject_reference_node_id": DEMO_IDS["demo_share_class_instrument_node"], "market_data_series_id": DEMO_IDS["demo_fund_nav_series"], "series_type": "OFFICIAL_NAV", "selection_method": "OFFICIAL", "pricing_date_rule": "FIXED_LAG", "lag_business_days": 1, "max_staleness_business_days": 0, "missing_data_action": "FAIL", "dataset_id": DEMO_IDS["dataset"], "status": "ACTIVE"})
        _insert_once(connection, m.market_data_resolution_snapshot, {"market_data_resolution_snapshot_id": DEMO_IDS["resolution_snapshot"], "tenant_id": DEMO_IDS["tenant"], "valuation_policy_id": DEMO_IDS["valuation_policy"], "valuation_date": today, "valuation_cut_id": DEMO_IDS["valuation_cut"], "market_data_as_of_utc": now, "resolver_version": "demo-v1", "status": "COMPLETED", "created_at_utc": now})
        _insert_once(connection, m.market_data_resolution_snapshot_item, {"market_data_resolution_snapshot_item_id": DEMO_IDS["resolution_item"], "market_data_resolution_snapshot_id": DEMO_IDS["resolution_snapshot"], "subject_reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "market_data_series_id": DEMO_IDS["market_data_series"], "market_data_observation_id": DEMO_IDS["market_data_observation"], "dataset_id": DEMO_IDS["dataset"], "selected_value": 1023.0, "currency_id": DEMO_IDS["gbp_currency"], "pricing_date_requested": today, "pricing_date_used": today, "staleness_business_days": 0, "staleness_status": "CURRENT", "selection_reason": "ENTITLED_PROVIDER", "entitlement_decision": "ALLOWED", "policy_rule_id": DEMO_IDS["valuation_policy_rule"]})
        _insert_once(connection, m.nav_calculation_run, {"nav_calculation_run_id": DEMO_IDS["nav_calculation_run"], "tenant_id": DEMO_IDS["tenant"], "strategy_id": DEMO_IDS["strategy"], "position_snapshot_id": DEMO_IDS["position_snapshot"], "valuation_date": today, "valuation_cut_id": DEMO_IDS["valuation_cut"], "valuation_policy_id": DEMO_IDS["valuation_policy"], "market_data_resolution_snapshot_id": DEMO_IDS["resolution_snapshot"], "calculation_version": "demo-v1", "status": "APPROVED", "created_at_utc": now})
        _insert_once(connection, m.nav_input_snapshot, {"nav_input_snapshot_id": DEMO_IDS["nav_input_snapshot"], "nav_calculation_run_id": DEMO_IDS["nav_calculation_run"], "resolved_at_utc": now, "input_hash": "2" * 64, "status": "FROZEN"})
        _insert_once(connection, m.nav_input_snapshot_item, {"nav_input_snapshot_item_id": DEMO_IDS["nav_input_item"], "nav_input_snapshot_id": DEMO_IDS["nav_input_snapshot"], "subject_reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "market_data_series_id": DEMO_IDS["market_data_series"], "market_data_observation_id": DEMO_IDS["market_data_observation"], "market_data_resolution_snapshot_item_id": DEMO_IDS["resolution_item"], "policy_rule_id": DEMO_IDS["valuation_policy_rule"], "dataset_id": DEMO_IDS["dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "selected_value": 1023.0, "currency_id": DEMO_IDS["gbp_currency"], "pricing_date_requested": today, "pricing_date_used": today, "staleness_business_days": 0, "staleness_status": "CURRENT", "selection_reason": "OFFICIAL_CLOSE", "entitlement_decision": "ALLOWED"})
        _insert_once(connection, m.nav_valuation_line, {"nav_valuation_line_id": DEMO_IDS["nav_valuation_line"], "nav_calculation_run_id": DEMO_IDS["nav_calculation_run"], "reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "price_input_snapshot_item_id": DEMO_IDS["nav_input_item"], "quantity": 1000, "local_value": 10230.0, "local_currency_id": DEMO_IDS["gbp_currency"], "fx_rate": 1, "fx_input_snapshot_item_id": DEMO_IDS["nav_input_item"], "reporting_value": 10230.0, "exception_status": "NONE"})
        _insert_once(connection, m.nav_result, {"nav_result_id": DEMO_IDS["nav_result"], "nav_calculation_run_id": DEMO_IDS["nav_calculation_run"], "reporting_currency_id": DEMO_IDS["gbp_currency"], "gross_assets": 10230.0, "liabilities": 0, "net_asset_value": 10230.0, "units_in_issue": 1000, "nav_per_unit": 10.23, "status": "APPROVED"})
        _insert_once(connection, m.nav_reconciliation, {"nav_reconciliation_id": DEMO_IDS["nav_reconciliation"], "nav_calculation_run_id": DEMO_IDS["nav_calculation_run"], "reference_nav_value": 10230.0, "reference_currency_id": DEMO_IDS["gbp_currency"], "reference_source_payload_id": DEMO_IDS["source_payload"], "difference_amount": 0, "tolerance_amount": 1, "status": "MATCHED"})

        # Additional synthetic reference-data scenarios: OTC bond, FX forward,
        # expiry-level future, and a dated autocall structured product.
        bond_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "BOND")
        fx_forward_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "FX_FORWARD")
        future_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "FUTURE")
        option_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "OPTION")
        swap_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "SWAP")
        future_family_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FUTURE_FAMILY")
        structured_product_type = _catalogue_id(connection, m.instrument_type, m.instrument_type.c.type_code, "STRUCTURED_PRODUCT")
        gross_total_return_profile = _catalogue_id(connection, m.return_profile, m.return_profile.c.profile_code, "GROSS_TOTAL_RETURN")
        net_total_return_profile = _catalogue_id(connection, m.return_profile, m.return_profile.c.profile_code, "NET_TOTAL_RETURN")

        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["eur_currency_node"], "reference_node_type_id": node_currency, "canonical_name": "Euro", "internal_code": "EUR_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.currency, {"currency_id": DEMO_IDS["eur_currency"], "reference_node_id": DEMO_IDS["eur_currency_node"], "currency_code": "EUR", "display_name": "Euro", "numeric_code": "978", "minor_unit": 2, "currency_kind": "FIAT", "status": "ACTIVE"})
        _insert_once(connection, m.reference_node_scope, {"reference_node_scope_id": UUID("00000000-0000-7000-8000-000000000075"), "reference_node_id": DEMO_IDS["eur_currency_node"], "scope_type": "SHARED_CANONICAL", "status": "ACTIVE"})
        _insert_once(connection, m.dataset, {"dataset_id": DEMO_IDS["multi_asset_dataset"], "provider_product_id": DEMO_IDS["provider_product"], "dataset_code": "MULTI_ASSET_DEMO", "display_name": "Multi-asset reference data (synthetic)", "data_domain": "MARKET_DATA", "coverage_description": "Synthetic OTC, FX, futures, and structured-product marks for tests.", "delivery_channel": "API", "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.tenant_dataset_entitlement, {"tenant_id": DEMO_IDS["tenant"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "use_purpose": "VALUATION", "status": "ACTIVE", "valid_from": today})

        # Cutoff-aware fund contexts use the same canonical GBP/USD pair but
        # separate cut-specific series.  On 28 August 2026, 16:00 London is
        # 15:00 UTC (BST) and 16:00 New York is 20:00 UTC (EDT).
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["usd_currency_node"], "reference_node_type_id": node_currency, "canonical_name": "US dollar", "internal_code": "USD_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.currency, {"currency_id": DEMO_IDS["usd_currency"], "reference_node_id": DEMO_IDS["usd_currency_node"], "currency_code": "USD", "display_name": "US dollar", "numeric_code": "840", "minor_unit": 2, "currency_kind": "FIAT", "status": "ACTIVE"})
        fx_pair_type = _catalogue_id(connection, m.reference_node_type, m.reference_node_type.c.type_code, "FX_PAIR")
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "reference_node_type_id": fx_pair_type, "canonical_name": "GBP/USD spot reference", "internal_code": "FXPAIR_GBPUSD_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.reference_node_scope, {"reference_node_scope_id": UUID("00000000-0000-0000-0000-000000000086"), "reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "scope_type": "SHARED_CANONICAL", "status": "ACTIVE"})
        _insert_once(connection, m.valuation_cut, {"valuation_cut_id": DEMO_IDS["uk_fx_cut"], "cut_code": "UK_FUND_FX_1600_DEMO", "display_name": "UK fund FX cut at 16:00 London (synthetic)", "timezone_name": "Europe/London", "local_time": "16:00:00", "status": "ACTIVE"})
        _insert_once(connection, m.valuation_cut, {"valuation_cut_id": DEMO_IDS["us_fx_cut"], "cut_code": "US_FUND_FX_1600_DEMO", "display_name": "US fund FX cut at 16:00 New York (synthetic)", "timezone_name": "America/New_York", "local_time": "16:00:00", "status": "ACTIVE"})

        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["bond_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "Fortem Demo 3.25% 2031 Note", "internal_code": "BOND_DEMO_2031", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["bond_instrument_node"], "instrument_type_id": bond_type, "asset_class": "FIXED_INCOME", "issuer_organisation_id": DEMO_IDS["hsbc_organisation"], "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["bond_dates"], "instrument_node_id": DEMO_IDS["bond_instrument_node"], "issue_date": date(2026, 1, 15), "maturity_date": date(2031, 1, 15), "final_settlement_date": date(2031, 1, 17)})
        _insert_once(connection, m.bond_terms, {"bond_terms_id": DEMO_IDS["demo_bond_terms"], "instrument_node_id": DEMO_IDS["bond_instrument_node"], "issue_currency_id": DEMO_IDS["gbp_currency"], "par_amount": 100, "coupon_type": "FIXED", "coupon_rate": 0.0325, "coupon_frequency_per_year": 2, "day_count_convention_id": day_count_convention_id, "day_count_convention": "ACT_ACT_ICMA", "redemption_amount_per_par": 100, "quotation_basis": "PCT_OF_PAR", "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["bond_series"], "reference_node_id": DEMO_IDS["bond_instrument_node"], "series_type": "EVALUATED_PRICE", "value_type": "PRICE", "currency_id": DEMO_IDS["gbp_currency"], "default_dataset_id": DEMO_IDS["multi_asset_dataset"], "valuation_cut_id": DEMO_IDS["valuation_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": False})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["bond_observation"], "market_data_series_id": DEMO_IDS["bond_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "market_date": today, "observed_at_utc": now, "received_at_utc": now, "value": 98.425, "value_basis": "RAW", "source_timestamp_utc": now, "quality_status": "ACCEPTED"})
        connection.execute(
            m.market_data_observation.update()
            .where(m.market_data_observation.c.market_data_observation_id == DEMO_IDS["bond_observation"])
            .values(
                source_payload_id=DEMO_IDS["source_payload"],
                market_date=today,
                valuation_cut_id=DEMO_IDS["valuation_cut"],
                source_observation_key="LSEG_DEMO:BOND_DEMO_2031:2026-08-28:EVALUATED",
            )
        )
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["bond_observation_20260826"], "market_data_series_id": DEMO_IDS["bond_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": date(2026, 8, 26), "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": datetime(2026, 8, 26, 16, 30, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 26, 16, 31, tzinfo=timezone.utc), "value": 98.115, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 26, 16, 30, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:BOND_DEMO_2031:2026-08-26:EVALUATED", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["bond_observation_20260827"], "market_data_series_id": DEMO_IDS["bond_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "source_payload_id": DEMO_IDS["source_payload"], "market_date": date(2026, 8, 27), "valuation_cut_id": DEMO_IDS["valuation_cut"], "observed_at_utc": datetime(2026, 8, 27, 16, 30, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 27, 16, 31, tzinfo=timezone.utc), "value": 98.260, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 27, 16, 30, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:BOND_DEMO_2031:2026-08-27:EVALUATED", "quality_status": "ACCEPTED"})

        # The GBP/USD pair has a separate scalar series for each fund cut.
        # The two observations on each series deliberately straddle its UTC
        # cut so historic-information replay can prove the later print is
        # excluded until it was received.
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["uk_gbpusd_series"], "reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "series_type": "FX_SPOT", "value_type": "RATE", "currency_id": DEMO_IDS["usd_currency"], "default_dataset_id": DEMO_IDS["multi_asset_dataset"], "valuation_cut_id": DEMO_IDS["uk_fx_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": True})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["us_gbpusd_series"], "reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "series_type": "FX_SPOT", "value_type": "RATE", "currency_id": DEMO_IDS["usd_currency"], "default_dataset_id": DEMO_IDS["multi_asset_dataset"], "valuation_cut_id": DEMO_IDS["us_fx_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": True})
        for series_id, quote_dimension_id, session_dimension_id, session in (
            (DEMO_IDS["uk_gbpusd_series"], DEMO_IDS["uk_gbpusd_quote_dimension"], DEMO_IDS["uk_gbpusd_session_dimension"], "UK_FUND_FX_1600"),
            (DEMO_IDS["us_gbpusd_series"], DEMO_IDS["us_gbpusd_quote_dimension"], DEMO_IDS["us_gbpusd_session_dimension"], "US_FUND_FX_1600"),
        ):
            _insert_once(connection, m.market_data_series_dimension, {"market_data_series_dimension_id": quote_dimension_id, "market_data_series_id": series_id, "dimension_code": "QUOTE_CONVENTION", "dimension_value": "USD_PER_GBP"})
            _insert_once(connection, m.market_data_series_dimension, {"market_data_series_dimension_id": session_dimension_id, "market_data_series_id": series_id, "dimension_code": "SESSION", "dimension_value": session})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["uk_fx_observation_before_cut"], "market_data_series_id": DEMO_IDS["uk_gbpusd_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "market_date": today, "valuation_cut_id": DEMO_IDS["uk_fx_cut"], "observed_at_utc": datetime(2026, 8, 28, 14, 59, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 28, 14, 59, 30, tzinfo=timezone.utc), "value": 1.3560, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 28, 14, 59, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:GBPUSD:UK_FUND_FX_1600:2026-08-28:BEFORE", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["uk_fx_observation_after_cut"], "market_data_series_id": DEMO_IDS["uk_gbpusd_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "market_date": today, "valuation_cut_id": DEMO_IDS["uk_fx_cut"], "observed_at_utc": datetime(2026, 8, 28, 15, 5, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 28, 15, 5, 30, tzinfo=timezone.utc), "value": 1.3570, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 28, 15, 5, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:GBPUSD:UK_FUND_FX_1600:2026-08-28:AFTER", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["us_fx_observation_before_cut"], "market_data_series_id": DEMO_IDS["us_gbpusd_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "market_date": today, "valuation_cut_id": DEMO_IDS["us_fx_cut"], "observed_at_utc": datetime(2026, 8, 28, 19, 59, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 28, 19, 59, 30, tzinfo=timezone.utc), "value": 1.3588, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 28, 19, 59, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:GBPUSD:US_FUND_FX_1600:2026-08-28:BEFORE", "quality_status": "ACCEPTED"})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["us_fx_observation_after_cut"], "market_data_series_id": DEMO_IDS["us_gbpusd_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "market_date": today, "valuation_cut_id": DEMO_IDS["us_fx_cut"], "observed_at_utc": datetime(2026, 8, 28, 20, 5, tzinfo=timezone.utc), "received_at_utc": datetime(2026, 8, 28, 20, 5, 30, tzinfo=timezone.utc), "value": 1.3601, "value_basis": "RAW", "source_timestamp_utc": datetime(2026, 8, 28, 20, 5, tzinfo=timezone.utc), "source_observation_key": "LSEG_DEMO:GBPUSD:US_FUND_FX_1600:2026-08-28:AFTER", "quality_status": "ACCEPTED"})

        _insert_once(connection, m.strategy, {"strategy_id": DEMO_IDS["uk_fund_strategy"], "tenant_id": DEMO_IDS["tenant"], "strategy_code": "UK_FUND_CUTOFF_DEMO", "display_name": "UK fund cutoff demo", "strategy_type": "FUND", "base_currency_id": DEMO_IDS["gbp_currency"], "legal_owner_organisation_id": DEMO_IDS["fortem_organisation"], "status": "ACTIVE"})
        _insert_once(connection, m.strategy, {"strategy_id": DEMO_IDS["us_fund_strategy"], "tenant_id": DEMO_IDS["tenant"], "strategy_code": "US_FUND_CUTOFF_DEMO", "display_name": "US fund cutoff demo", "strategy_type": "FUND", "base_currency_id": DEMO_IDS["usd_currency"], "legal_owner_organisation_id": DEMO_IDS["fortem_organisation"], "status": "ACTIVE"})
        _insert_once(connection, m.valuation_policy, {"valuation_policy_id": DEMO_IDS["uk_fund_policy"], "tenant_id": DEMO_IDS["tenant"], "policy_code": "UK_FUND_CUTOFF_DEMO", "display_name": "UK fund valuation with London FX cut", "valuation_cut_id": DEMO_IDS["uk_fx_cut"], "version_no": 1, "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.valuation_policy, {"valuation_policy_id": DEMO_IDS["us_fund_policy"], "tenant_id": DEMO_IDS["tenant"], "policy_code": "US_FUND_CUTOFF_DEMO", "display_name": "US fund valuation with New York FX cut", "valuation_cut_id": DEMO_IDS["us_fx_cut"], "version_no": 1, "status": "ACTIVE", "valid_from": today})
        _insert_once(connection, m.valuation_policy_rule, {"valuation_policy_rule_id": DEMO_IDS["uk_fund_fx_policy_rule"], "valuation_policy_id": DEMO_IDS["uk_fund_policy"], "rule_sequence": 1, "subject_type": "FX_PAIR", "subject_reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "market_data_series_id": DEMO_IDS["uk_gbpusd_series"], "series_type": "FX_SPOT", "selection_method": "OFFICIAL", "pricing_date_rule": "SAME_DAY", "lag_business_days": 0, "max_staleness_business_days": 0, "missing_data_action": "FAIL", "dataset_id": DEMO_IDS["multi_asset_dataset"], "status": "ACTIVE"})
        _insert_once(connection, m.valuation_policy_rule, {"valuation_policy_rule_id": DEMO_IDS["us_fund_fx_policy_rule"], "valuation_policy_id": DEMO_IDS["us_fund_policy"], "rule_sequence": 1, "subject_type": "FX_PAIR", "subject_reference_node_id": DEMO_IDS["gbpusd_fx_pair_node"], "market_data_series_id": DEMO_IDS["us_gbpusd_series"], "series_type": "FX_SPOT", "selection_method": "OFFICIAL", "pricing_date_rule": "SAME_DAY", "lag_business_days": 0, "max_staleness_business_days": 0, "missing_data_action": "FAIL", "dataset_id": DEMO_IDS["multi_asset_dataset"], "status": "ACTIVE"})

        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["fx_forward_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "GBP/EUR deliverable forward 2026-09-28", "internal_code": "FXFWD_GBPEUR_20260928", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["fx_forward_instrument_node"], "instrument_type_id": fx_forward_type, "asset_class": "FX", "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["fx_forward_dates"], "instrument_node_id": DEMO_IDS["fx_forward_instrument_node"], "effective_date": today, "maturity_date": date(2026, 9, 28), "settlement_date": date(2026, 9, 30), "final_settlement_date": date(2026, 9, 30)})
        _insert_once(connection, m.fx_forward_terms, {"instrument_node_id": DEMO_IDS["fx_forward_instrument_node"], "base_currency_id": DEMO_IDS["gbp_currency"], "quote_currency_id": DEMO_IDS["eur_currency"], "quote_convention": "EUR_PER_GBP", "agreed_forward_rate": 1.1584, "settlement_type": "DELIVERABLE"})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["fx_forward_series"], "reference_node_id": DEMO_IDS["fx_forward_instrument_node"], "series_type": "MARK", "value_type": "RATE", "currency_id": DEMO_IDS["eur_currency"], "default_dataset_id": DEMO_IDS["multi_asset_dataset"], "valuation_cut_id": DEMO_IDS["valuation_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": False})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["fx_forward_observation"], "market_data_series_id": DEMO_IDS["fx_forward_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "market_date": today, "observed_at_utc": now, "received_at_utc": now, "value": 1.1612, "value_basis": "RAW", "source_timestamp_utc": now, "quality_status": "ACCEPTED"})

        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["future_family_node"], "reference_node_type_id": future_family_type, "canonical_name": "Demo Euro Stoxx future family", "internal_code": "FUT_FAMILY_ESTX_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.future_family, {"future_family_id": DEMO_IDS["future_family"], "family_node_id": DEMO_IDS["future_family_node"], "underlying_reference_node_id": DEMO_IDS["hsbc_instrument_node"], "contract_currency_id": DEMO_IDS["eur_currency"], "expiry_cycle": "QUARTERLY", "status": "ACTIVE"})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["future_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "Demo Euro Stoxx future Dec-2026", "internal_code": "FUT_ESTX_202612", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["future_instrument_node"], "instrument_type_id": future_type, "asset_class": "FUTURES", "base_currency_id": DEMO_IDS["eur_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.future_terms, {"instrument_node_id": DEMO_IDS["future_instrument_node"], "future_family_id": DEMO_IDS["future_family"], "contract_month": date(2026, 12, 18), "last_trade_date": date(2026, 12, 18), "settlement_method": "CASH"})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["future_listing_node"], "reference_node_type_id": node_listing, "canonical_name": "Demo Euro Stoxx future on XEUR", "internal_code": "FUT_ESTX_202612_XEUR", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.listing, {"listing_node_id": DEMO_IDS["future_listing_node"], "instrument_node_id": DEMO_IDS["future_instrument_node"], "market_venue_id": DEMO_IDS["xlon_venue"], "trading_currency_id": DEMO_IDS["eur_currency"], "trading_symbol": "ESTX6", "quote_factor": 1, "unit_multiplier": 10, "is_primary_listing": True, "status": "ACTIVE"})
        _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["future_dates"], "instrument_node_id": DEMO_IDS["future_instrument_node"], "last_trading_date": date(2026, 12, 18), "expiry_date": date(2026, 12, 18), "final_settlement_date": date(2026, 12, 21)})
        _insert_once(connection, m.market_data_series, {"market_data_series_id": DEMO_IDS["future_series"], "reference_node_id": DEMO_IDS["future_listing_node"], "series_type": "OFFICIAL_CLOSE", "value_type": "PRICE", "currency_id": DEMO_IDS["eur_currency"], "default_dataset_id": DEMO_IDS["multi_asset_dataset"], "valuation_cut_id": DEMO_IDS["valuation_cut"], "source_system_id": "LSEG_DEMO", "status": "ACTIVE", "is_official": True})
        _insert_once(connection, m.market_data_observation, {"market_data_observation_id": DEMO_IDS["future_observation"], "market_data_series_id": DEMO_IDS["future_series"], "dataset_id": DEMO_IDS["multi_asset_dataset"], "acquisition_licence_id": DEMO_IDS["data_licence"], "market_date": today, "observed_at_utc": now, "received_at_utc": now, "value": 4875.5, "value_basis": "RAW", "source_timestamp_utc": now, "quality_status": "ACCEPTED"})

        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["autocall_coupon_component_node"], "reference_node_type_id": node_instrument, "canonical_name": "Demo autocall coupon component", "internal_code": "SP_AUTOCALL_COUPON_COMPONENT", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["autocall_coupon_component_node"], "instrument_type_id": option_type, "asset_class": "EQUITY_DERIVATIVE", "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["autocall_instrument_node"], "reference_node_type_id": node_instrument, "canonical_name": "Demo HSBC and Euro Stoxx quarterly autocall", "internal_code": "SP_AUTOCALL_HSBC_ESTX_DEMO", "status": "ACTIVE", "is_tradable": True})
        _insert_once(connection, m.instrument, {"instrument_node_id": DEMO_IDS["autocall_instrument_node"], "instrument_type_id": structured_product_type, "asset_class": "STRUCTURED_PRODUCT", "issuer_organisation_id": DEMO_IDS["hsbc_organisation"], "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
        existing_autocall_terms_id = connection.execute(
            select(m.structured_product_terms.c.structured_product_terms_id)
            .where(m.structured_product_terms.c.instrument_node_id == DEMO_IDS["autocall_instrument_node"])
            .where(m.structured_product_terms.c.version_no == 1)
        ).scalar_one_or_none()
        autocall_terms_id = existing_autocall_terms_id or DEMO_IDS["autocall_terms"]
        _insert_once(connection, m.structured_product_terms, {"structured_product_terms_id": autocall_terms_id, "instrument_node_id": DEMO_IDS["autocall_instrument_node"], "version_no": 1, "effective_from": today, "is_current": True, "issue_currency_id": DEMO_IDS["gbp_currency"], "notional_amount": 1000000, "redemption_currency_id": DEMO_IDS["gbp_currency"], "default_underlying_scope": "WORST_OF", "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        connection.execute(
            update(m.structured_product_terms)
            .where(m.structured_product_terms.c.structured_product_terms_id == autocall_terms_id)
            .values(default_underlying_scope="WORST_OF", status="VALIDATED", source_payload_id=DEMO_IDS["source_payload"], is_current=True)
        )
        _insert_once(connection, m.instrument_dates, {"instrument_dates_id": DEMO_IDS["autocall_dates"], "instrument_node_id": DEMO_IDS["autocall_instrument_node"], "effective_date": today, "maturity_date": date(2029, 8, 28), "expiry_date": date(2029, 8, 28), "final_valuation_date": date(2029, 8, 24), "final_settlement_date": date(2029, 8, 31)})
        _insert_once(connection, m.schedule, {"schedule_id": DEMO_IDS["autocall_schedule"], "owner_reference_node_id": DEMO_IDS["autocall_instrument_node"], "schedule_type": "AUTOCALL_OBSERVATION", "status": "ACTIVE"})
        _insert_once(connection, m.schedule_event, {"schedule_event_id": DEMO_IDS["autocall_schedule_event_1"], "schedule_id": DEMO_IDS["autocall_schedule"], "event_sequence": 1, "event_type": "OBSERVATION", "event_date": date(2026, 11, 28), "payment_date": date(2026, 12, 4), "status": "SCHEDULED"})
        _insert_once(connection, m.schedule_event, {"schedule_event_id": DEMO_IDS["autocall_schedule_event_2"], "schedule_id": DEMO_IDS["autocall_schedule"], "event_sequence": 2, "event_type": "OBSERVATION", "event_date": date(2027, 2, 26), "payment_date": date(2027, 3, 5), "status": "SCHEDULED"})
        _insert_once(connection, m.instrument_composition, {"instrument_composition_id": DEMO_IDS["autocall_hsbc_composition"], "parent_instrument_node_id": DEMO_IDS["autocall_instrument_node"], "component_reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"], "composition_role": "UNDERLYING", "composition_value": 1, "composition_value_kind": "SIGNED_MULTIPLIER", "component_sequence": 1, "structured_product_terms_id": autocall_terms_id, "composition_date": today, "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.instrument_composition, {"instrument_composition_id": DEMO_IDS["autocall_eurostoxx_composition"], "parent_instrument_node_id": DEMO_IDS["autocall_instrument_node"], "component_reference_node_id": DEMO_IDS["future_listing_node"], "composition_role": "UNDERLYING", "composition_value": 1, "composition_value_kind": "SIGNED_MULTIPLIER", "component_sequence": 2, "structured_product_terms_id": autocall_terms_id, "composition_date": today, "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.instrument_composition, {"instrument_composition_id": DEMO_IDS["autocall_coupon_composition"], "parent_instrument_node_id": DEMO_IDS["autocall_instrument_node"], "component_reference_node_id": DEMO_IDS["autocall_coupon_component_node"], "composition_role": "PAYOFF_COMPONENT", "composition_value": 1, "composition_value_kind": "SIGNED_MULTIPLIER", "component_sequence": 3, "structured_product_terms_id": autocall_terms_id, "composition_date": today, "source_payload_id": DEMO_IDS["source_payload"]})
        legacy_autocall_composition_exists = connection.execute(
            select(m.instrument_composition.c.instrument_composition_id)
            .where(m.instrument_composition.c.instrument_composition_id == UUID("00000000-0000-7000-8000-000000000074"))
        ).scalar_one_or_none() is not None
        composition_sequence_offset = 1 if legacy_autocall_composition_exists else 0
        for composition_id, component_node_id, role, sequence in (
            (DEMO_IDS["autocall_hsbc_composition"], DEMO_IDS["hsbc_xlon_listing_node"], "UNDERLYING", 1),
            (DEMO_IDS["autocall_eurostoxx_composition"], DEMO_IDS["future_listing_node"], "UNDERLYING", 2),
            (DEMO_IDS["autocall_coupon_composition"], DEMO_IDS["autocall_coupon_component_node"], "PAYOFF_COMPONENT", 3),
        ):
            connection.execute(
                update(m.instrument_composition)
                .where(m.instrument_composition.c.instrument_composition_id == composition_id)
                .values(
                    parent_instrument_node_id=DEMO_IDS["autocall_instrument_node"],
                    component_reference_node_id=component_node_id,
                    composition_role=role,
                    composition_value=1,
                    composition_value_kind="SIGNED_MULTIPLIER",
                    component_sequence=sequence + composition_sequence_offset,
                    structured_product_terms_id=autocall_terms_id,
                    composition_date=today,
                    source_payload_id=DEMO_IDS["source_payload"],
                )
            )
        _insert_once(connection, m.structured_product_condition_group, {"condition_group_id": DEMO_IDS["autocall_condition_group"], "structured_product_terms_id": autocall_terms_id, "group_code": "AUTOCALL_OBS_1_AT_100", "observation_style": "DISCRETE", "schedule_event_id": DEMO_IDS["autocall_schedule_event_1"], "logical_operator": "NONE", "underlying_aggregation": "MIN", "underlying_scope": "WORST_OF", "evaluation_sequence": 1, "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        connection.execute(
            update(m.structured_product_condition_group)
            .where(m.structured_product_condition_group.c.condition_group_id == DEMO_IDS["autocall_condition_group"])
            .values(structured_product_terms_id=autocall_terms_id, logical_operator="NONE", underlying_scope="WORST_OF", underlying_aggregation="MIN", status="VALIDATED", source_payload_id=DEMO_IDS["source_payload"])
        )
        for barrier_id, underlying_id, sequence in ((DEMO_IDS["autocall_hsbc_barrier"], DEMO_IDS["hsbc_xlon_listing_node"], 1), (DEMO_IDS["autocall_eurostoxx_barrier"], DEMO_IDS["future_listing_node"], 2)):
            _insert_once(connection, m.barrier_rule, {"barrier_rule_id": barrier_id, "condition_group_id": DEMO_IDS["autocall_condition_group"], "owner_reference_node_id": DEMO_IDS["autocall_instrument_node"], "underlying_reference_node_id": underlying_id, "condition_sequence": sequence, "comparison_operator": "GE", "level_reference_type": "PCT_OF_INITIAL", "lower_level_value": 100, "underlying_measure": "OFFICIAL_CLOSE", "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
            connection.execute(update(m.barrier_rule).where(m.barrier_rule.c.barrier_rule_id == barrier_id).values(owner_reference_node_id=DEMO_IDS["autocall_instrument_node"], source_payload_id=DEMO_IDS["source_payload"], status="VALIDATED"))
        _insert_once(connection, m.condition_group_action, {"condition_group_action_id": DEMO_IDS["autocall_coupon_action"], "condition_group_id": DEMO_IDS["autocall_condition_group"], "action_type": "PAY_COMPONENT", "target_scope": "PARENT", "target_reference_node_id": DEMO_IDS["autocall_instrument_node"], "target_composition_id": None, "payment_rate": 5, "payment_currency_id": DEMO_IDS["gbp_currency"], "payment_basis": "PCT_OF_NOTIONAL", "payment_timing": "ON_AUTOCALL", "payment_schedule_id": DEMO_IDS["autocall_schedule"], "payout_multiplicity": "ONCE_PER_PARENT", "execution_sequence": 10, "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        connection.execute(update(m.condition_group_action).where(m.condition_group_action.c.condition_group_action_id == DEMO_IDS["autocall_coupon_action"]).values(target_scope="PARENT", target_reference_node_id=DEMO_IDS["autocall_instrument_node"], target_composition_id=None, payment_rate=5, payment_currency_id=DEMO_IDS["gbp_currency"], payment_basis="PCT_OF_NOTIONAL", payment_timing="ON_AUTOCALL", payment_schedule_id=DEMO_IDS["autocall_schedule"], payout_multiplicity="ONCE_PER_PARENT", status="VALIDATED", source_payload_id=DEMO_IDS["source_payload"]))
        _insert_once(connection, m.condition_group_action, {"condition_group_action_id": DEMO_IDS["autocall_redemption_action"], "condition_group_id": DEMO_IDS["autocall_condition_group"], "action_type": "REDEEM_PARENT", "target_scope": "PARENT", "target_reference_node_id": DEMO_IDS["autocall_instrument_node"], "payment_timing": "ON_AUTOCALL", "payment_schedule_id": DEMO_IDS["autocall_schedule"], "payout_multiplicity": "ONCE_PER_PARENT", "execution_sequence": 20, "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        connection.execute(update(m.condition_group_action).where(m.condition_group_action.c.condition_group_action_id == DEMO_IDS["autocall_redemption_action"]).values(payment_timing="ON_AUTOCALL", payment_schedule_id=DEMO_IDS["autocall_schedule"], payout_multiplicity="ONCE_PER_PARENT", status="VALIDATED", source_payload_id=DEMO_IDS["source_payload"]))
        _insert_once(connection, m.structured_product_coupon_programme, {"coupon_programme_id": DEMO_IDS["autocall_coupon_programme"], "structured_product_terms_id": autocall_terms_id, "programme_code": "MAIN_COUPON", "payment_mode": "ON_AUTOCALL", "memory_mode": "CONDITIONAL_CATCH_UP", "coupon_currency_id": DEMO_IDS["gbp_currency"], "default_coupon_rate": 5, "schedule_id": DEMO_IDS["autocall_schedule"], "eligibility_condition_group_id": DEMO_IDS["autocall_condition_group"], "final_payment_treatment": "FORFEIT", "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        connection.execute(update(m.structured_product_coupon_programme).where(m.structured_product_coupon_programme.c.coupon_programme_id == DEMO_IDS["autocall_coupon_programme"]).values(structured_product_terms_id=autocall_terms_id, schedule_id=DEMO_IDS["autocall_schedule"], eligibility_condition_group_id=DEMO_IDS["autocall_condition_group"], default_coupon_rate=5, status="VALIDATED", source_payload_id=DEMO_IDS["source_payload"]))
        for period_id, event_id, payment_date, sequence in ((DEMO_IDS["autocall_coupon_period_1"], DEMO_IDS["autocall_schedule_event_1"], date(2026, 12, 4), 1), (DEMO_IDS["autocall_coupon_period_2"], DEMO_IDS["autocall_schedule_event_2"], date(2027, 3, 5), 2)):
            _insert_once(connection, m.structured_product_coupon_period, {"coupon_period_id": period_id, "coupon_programme_id": DEMO_IDS["autocall_coupon_programme"], "period_sequence": sequence, "observation_event_id": event_id, "payment_date": payment_date, "eligibility_condition_group_id": DEMO_IDS["autocall_condition_group"], "coupon_rate": 5, "memory_eligible": True, "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})
        _insert_once(connection, m.structured_product_component_terms, {"structured_product_component_terms_id": DEMO_IDS["autocall_coupon_component_terms"], "instrument_composition_id": DEMO_IDS["autocall_coupon_composition"], "component_kind": "DIGITAL", "payoff_style": "RATE_OF_NOTIONAL", "payout_rate": 5, "payout_currency_id": DEMO_IDS["gbp_currency"], "payout_basis": "PCT_OF_NOTIONAL", "payment_timing": "ON_AUTOCALL", "schedule_id": DEMO_IDS["autocall_schedule"], "status": "VALIDATED", "source_payload_id": DEMO_IDS["source_payload"]})

        # Vanilla option fixtures deliberately cover the standards dimensions
        # without introducing digital/barrier payoff logic: a listed physical
        # equity call, a cash-settled index-point put, and a Bermudan option
        # whose permitted exercise dates are a reusable schedule.
        _insert_once(
            connection,
            m.financial_reference_node,
            {
                "reference_node_id": DEMO_IDS["vanilla_index_reference_node"],
                "reference_node_type_id": node_index,
                "canonical_name": "Demo FTSE 100 price index underlying",
                "internal_code": "INDEX_FTSE100_PRICE_DEMO",
                "status": "ACTIVE",
                "is_tradable": False,
            },
        )
        _insert_once(
            connection,
            m.financial_reference_node,
            {
                "reference_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "reference_node_type_id": node_instrument,
                "canonical_name": "Demo HSBC September 2027 8.50 call",
                "internal_code": "OPT_HSBC_CALL_850_202709",
                "status": "ACTIVE",
                "is_tradable": True,
            },
        )
        _insert_once(
            connection,
            m.instrument,
            {
                "instrument_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "instrument_type_id": option_type,
                "asset_class": "DERIVATIVE",
                "issuer_organisation_id": DEMO_IDS["hsbc_organisation"],
                "base_currency_id": DEMO_IDS["gbp_currency"],
                "effective_from": today,
                "is_current": True,
                "sequence_no": 1,
            },
        )
        _insert_once(
            connection,
            m.instrument_dates,
            {
                "instrument_dates_id": DEMO_IDS["vanilla_equity_option_dates"],
                "instrument_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "effective_date": today,
                "expiry_date": date(2027, 9, 17),
                "maturity_date": date(2027, 9, 17),
                "final_settlement_date": date(2027, 9, 20),
            },
        )
        _insert_once(
            connection,
            m.option_terms,
            {
                "instrument_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "underlying_reference_node_id": DEMO_IDS["hsbc_xlon_listing_node"],
                "option_type": "CALL",
                "exercise_style": "EUROPEAN",
                "strike_value": 8.50,
                "strike_basis": "ABSOLUTE",
                "strike_currency_id": DEMO_IDS["gbp_currency"],
                "premium_currency_id": DEMO_IDS["gbp_currency"],
                "settlement_method": "PHYSICAL",
            },
        )
        _insert_once(
            connection,
            m.instrument_contract_unit_terms,
            {
                "instrument_contract_unit_terms_id": DEMO_IDS["vanilla_equity_option_contract_unit_terms"],
                "instrument_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "unit_multiplier": 100,
                "unit_of_measure": "SHARES_PER_CONTRACT",
                "valid_from": today,
                "sequence_no": 1,
            },
        )
        _insert_once(
            connection,
            m.financial_reference_node,
            {
                "reference_node_id": DEMO_IDS["vanilla_equity_option_listing"],
                "reference_node_type_id": node_listing,
                "canonical_name": "Demo HSBC September 2027 8.50 call on XLON",
                "internal_code": "OPT_HSBC_CALL_850_202709_XLON",
                "status": "ACTIVE",
                "is_tradable": True,
            },
        )
        _insert_once(
            connection,
            m.listing,
            {
                "listing_node_id": DEMO_IDS["vanilla_equity_option_listing"],
                "instrument_node_id": DEMO_IDS["vanilla_equity_option_node"],
                "market_venue_id": DEMO_IDS["xlon_venue"],
                "trading_currency_id": DEMO_IDS["gbp_currency"],
                "trading_symbol": "HSDC8.50",
                "quote_factor": 1,
                "unit_multiplier": 1,
                "is_primary_listing": True,
                "status": "ACTIVE",
            },
        )

        for option_node_id, canonical_name, internal_code, dates_id, asset_class, base_currency_id in (
            (
                DEMO_IDS["vanilla_index_option_node"],
                "Demo FTSE 100 December 2027 7,500 put",
                "OPT_FTSE100_PUT_7500_202712",
                DEMO_IDS["vanilla_index_option_dates"],
                "DERIVATIVE",
                DEMO_IDS["usd_currency"],
            ),
            (
                DEMO_IDS["vanilla_bermudan_option_node"],
                "Demo FTSE 100 June 2028 Bermudan put",
                "OPT_FTSE100_BERMUDAN_PUT_202806",
                DEMO_IDS["vanilla_bermudan_option_dates"],
                "DERIVATIVE",
                DEMO_IDS["gbp_currency"],
            ),
        ):
            _insert_once(
                connection,
                m.financial_reference_node,
                {
                    "reference_node_id": option_node_id,
                    "reference_node_type_id": node_instrument,
                    "canonical_name": canonical_name,
                    "internal_code": internal_code,
                    "status": "ACTIVE",
                    "is_tradable": True,
                },
            )
            _insert_once(
                connection,
                m.instrument,
                {
                    "instrument_node_id": option_node_id,
                    "instrument_type_id": option_type,
                    "asset_class": asset_class,
                    "base_currency_id": base_currency_id,
                    "effective_from": today,
                    "is_current": True,
                    "sequence_no": 1,
                },
            )

        _insert_once(
            connection,
            m.instrument_dates,
            {
                "instrument_dates_id": DEMO_IDS["vanilla_index_option_dates"],
                "instrument_node_id": DEMO_IDS["vanilla_index_option_node"],
                "effective_date": today,
                "expiry_date": date(2027, 12, 17),
                "maturity_date": date(2027, 12, 17),
                "final_settlement_date": date(2027, 12, 20),
            },
        )
        _insert_once(
            connection,
            m.option_terms,
            {
                "instrument_node_id": DEMO_IDS["vanilla_index_option_node"],
                "underlying_reference_node_id": DEMO_IDS["vanilla_index_reference_node"],
                "option_type": "PUT",
                "exercise_style": "EUROPEAN",
                "strike_value": 7500,
                "strike_basis": "INDEX_POINTS",
                "premium_currency_id": DEMO_IDS["usd_currency"],
                "settlement_method": "CASH",
                "settlement_currency_id": DEMO_IDS["usd_currency"],
            },
        )
        _insert_once(
            connection,
            m.instrument_contract_unit_terms,
            {
                "instrument_contract_unit_terms_id": DEMO_IDS["vanilla_index_option_contract_unit_terms"],
                "instrument_node_id": DEMO_IDS["vanilla_index_option_node"],
                "unit_multiplier": 50,
                "unit_of_measure": "CURRENCY_PER_INDEX_POINT",
                "valid_from": today,
                "sequence_no": 1,
            },
        )

        _insert_once(
            connection,
            m.instrument_dates,
            {
                "instrument_dates_id": DEMO_IDS["vanilla_bermudan_option_dates"],
                "instrument_node_id": DEMO_IDS["vanilla_bermudan_option_node"],
                "effective_date": today,
                "expiry_date": date(2028, 6, 30),
                "maturity_date": date(2028, 6, 30),
                "final_settlement_date": date(2028, 7, 3),
            },
        )
        _insert_once(
            connection,
            m.schedule,
            {
                "schedule_id": DEMO_IDS["vanilla_bermudan_option_schedule"],
                "owner_reference_node_id": DEMO_IDS["vanilla_bermudan_option_node"],
                "schedule_type": "EXERCISE",
                "status": "ACTIVE",
            },
        )
        _insert_once(
            connection,
            m.schedule_event,
            {
                "schedule_event_id": DEMO_IDS["vanilla_bermudan_option_schedule_event_1"],
                "schedule_id": DEMO_IDS["vanilla_bermudan_option_schedule"],
                "event_sequence": 1,
                "event_type": "EXERCISE",
                "event_date": date(2027, 12, 15),
                "status": "SCHEDULED",
            },
        )
        _insert_once(
            connection,
            m.schedule_event,
            {
                "schedule_event_id": DEMO_IDS["vanilla_bermudan_option_schedule_event_2"],
                "schedule_id": DEMO_IDS["vanilla_bermudan_option_schedule"],
                "event_sequence": 2,
                "event_type": "EXERCISE",
                "event_date": date(2028, 3, 15),
                "status": "SCHEDULED",
            },
        )
        _insert_once(
            connection,
            m.option_terms,
            {
                "instrument_node_id": DEMO_IDS["vanilla_bermudan_option_node"],
                "underlying_reference_node_id": DEMO_IDS["vanilla_index_reference_node"],
                "option_type": "PUT",
                "exercise_style": "BERMUDAN",
                "strike_value": 7500,
                "strike_basis": "INDEX_POINTS",
                "premium_currency_id": DEMO_IDS["gbp_currency"],
                "settlement_method": "ELECTION",
                "settlement_currency_id": DEMO_IDS["gbp_currency"],
                "exercise_schedule_id": DEMO_IDS["vanilla_bermudan_option_schedule"],
            },
        )
        _insert_once(
            connection,
            m.instrument_contract_unit_terms,
            {
                "instrument_contract_unit_terms_id": DEMO_IDS["vanilla_bermudan_option_contract_unit_terms"],
                "instrument_node_id": DEMO_IDS["vanilla_bermudan_option_node"],
                "unit_multiplier": 50,
                "unit_of_measure": "CURRENCY_PER_INDEX_POINT",
                "valid_from": today,
                "sequence_no": 1,
            },
        )

        # A reset-strike option keeps one economic instrument and one static
        # terms version.  The scheduled rules and resolved fixings are stored
        # separately so a later strike does not overwrite the contract terms.
        _insert_once(
            connection,
            m.financial_reference_node,
            {
                "reference_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "reference_node_type_id": node_instrument,
                "canonical_name": "Demo FTSE 100 quarterly reset call",
                "internal_code": "OPT_FTSE100_RESET_CALL_2028",
                "status": "ACTIVE",
                "is_tradable": True,
            },
        )
        _insert_once(
            connection,
            m.instrument,
            {
                "instrument_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "instrument_type_id": option_type,
                "asset_class": "DERIVATIVE",
                "base_currency_id": DEMO_IDS["gbp_currency"],
                "effective_from": today,
                "is_current": True,
                "sequence_no": 1,
            },
        )
        _insert_once(
            connection,
            m.instrument_dates,
            {
                "instrument_dates_id": DEMO_IDS["vanilla_reset_option_dates"],
                "instrument_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "effective_date": today,
                "expiry_date": date(2028, 7, 21),
                "maturity_date": date(2028, 7, 21),
                "final_settlement_date": date(2028, 7, 24),
            },
        )
        _insert_once(
            connection,
            m.schedule,
            {
                "schedule_id": DEMO_IDS["vanilla_reset_option_schedule"],
                "owner_reference_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "schedule_type": "STRIKE_RESET",
                "status": "ACTIVE",
            },
        )
        for event_id, sequence, event_date in (
            (DEMO_IDS["vanilla_reset_option_schedule_event_1"], 1, date(2027, 1, 21)),
            (DEMO_IDS["vanilla_reset_option_schedule_event_2"], 2, date(2027, 4, 21)),
        ):
            _insert_once(
                connection,
                m.schedule_event,
                {
                    "schedule_event_id": event_id,
                    "schedule_id": DEMO_IDS["vanilla_reset_option_schedule"],
                    "event_sequence": sequence,
                    "event_type": "RESET",
                    "event_date": event_date,
                    "status": "SCHEDULED",
                },
            )
        _insert_once(
            connection,
            m.option_terms,
            {
                "option_terms_id": DEMO_IDS["vanilla_reset_option_terms"],
                "instrument_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "version_no": 1,
                "effective_from": today,
                "is_current": True,
                "status": "ACTIVE",
                "underlying_reference_node_id": DEMO_IDS["vanilla_index_reference_node"],
                "option_type": "CALL",
                "exercise_style": "EUROPEAN",
                "strike_value": None,
                "strike_mode": "RESET",
                "strike_reset_schedule_id": DEMO_IDS["vanilla_reset_option_schedule"],
                "strike_basis": "INDEX_POINTS",
                "premium_currency_id": DEMO_IDS["gbp_currency"],
                "settlement_method": "CASH",
                "settlement_currency_id": DEMO_IDS["gbp_currency"],
            },
        )
        _insert_once(
            connection,
            m.instrument_contract_unit_terms,
            {
                "instrument_contract_unit_terms_id": DEMO_IDS["vanilla_reset_option_contract_unit_terms"],
                "instrument_node_id": DEMO_IDS["vanilla_reset_option_node"],
                "unit_multiplier": 10,
                "unit_of_measure": "CURRENCY_PER_INDEX_POINT",
                "valid_from": today,
                "sequence_no": 1,
            },
        )
        for rule_id, event_id, method in (
            (DEMO_IDS["vanilla_reset_option_rule_1"], DEMO_IDS["vanilla_reset_option_schedule_event_1"], "SPOT_AT_RESET"),
            (DEMO_IDS["vanilla_reset_option_rule_2"], DEMO_IDS["vanilla_reset_option_schedule_event_2"], "PREVIOUS_FIXING"),
        ):
            _insert_once(
                connection,
                m.option_strike_reset_rule,
                {
                    "option_strike_reset_rule_id": rule_id,
                    "option_terms_id": DEMO_IDS["vanilla_reset_option_terms"],
                    "schedule_event_id": event_id,
                    "determination_method": method,
                    "reference_node_id": DEMO_IDS["vanilla_index_reference_node"],
                    "strike_basis": "INDEX_POINTS",
                },
            )
        for fixing_id, rule_id, fixing_date, value in (
            (DEMO_IDS["vanilla_reset_option_fixing_1"], DEMO_IDS["vanilla_reset_option_rule_1"], date(2027, 1, 21), 7600),
            (DEMO_IDS["vanilla_reset_option_fixing_2"], DEMO_IDS["vanilla_reset_option_rule_2"], date(2027, 4, 21), 7800),
        ):
            _insert_once(
                connection,
                m.option_strike_fixing,
                {
                    "option_strike_fixing_id": fixing_id,
                    "option_strike_reset_rule_id": rule_id,
                    "fixing_date": fixing_date,
                    "fixing_observed_at_utc": datetime.combine(fixing_date, datetime.min.time(), tzinfo=timezone.utc),
                    "resolved_strike_value": value,
                    "status": "ACCEPTED",
                    "recorded_at_utc": now,
                },
            )

        # Three total-return swap examples deliberately share the same two-leg
        # contract shape while varying only the performance reference.
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["sonia_rate_index_node"], "reference_node_type_id": node_rate_index, "canonical_name": "SONIA overnight rate", "internal_code": "RATE_SONIA_DEMO", "status": "ACTIVE", "is_tradable": False})
        _insert_once(connection, m.financial_reference_node, {"reference_node_id": DEMO_IDS["qis_index_node"], "reference_node_type_id": node_index, "canonical_name": "Demo diversified QIS excess-return index", "internal_code": "QIS_DEMO_ER", "status": "ACTIVE", "is_tradable": False})

        for swap_node_id, canonical_name, internal_code, dates_id, schedule_id, maturity_date, reset_event_id, reset_date in (
            (DEMO_IDS["bond_total_return_swap_node"], "Demo UK gilt total-return swap", "SWAP_BOND_TRS_DEMO", DEMO_IDS["bond_total_return_swap_dates"], DEMO_IDS["bond_total_return_schedule"], date(2027, 8, 28), DEMO_IDS["bond_total_return_reset_event"], date(2026, 9, 28)),
            (DEMO_IDS["qis_total_return_swap_node"], "Demo QIS index total-return swap", "SWAP_QIS_TRS_DEMO", DEMO_IDS["qis_total_return_swap_dates"], DEMO_IDS["qis_total_return_schedule"], date(2027, 8, 28), DEMO_IDS["qis_total_return_reset_event"], date(2026, 10, 28)),
            (DEMO_IDS["autocall_total_return_swap_node"], "Demo autocall total-return swap", "SWAP_AUTOCALL_TRS_DEMO", DEMO_IDS["autocall_total_return_swap_dates"], DEMO_IDS["autocall_total_return_schedule"], date(2029, 8, 28), DEMO_IDS["autocall_total_return_reset_event"], date(2026, 11, 28)),
        ):
            _insert_once(connection, m.financial_reference_node, {"reference_node_id": swap_node_id, "reference_node_type_id": node_instrument, "canonical_name": canonical_name, "internal_code": internal_code, "status": "ACTIVE", "is_tradable": True})
            _insert_once(connection, m.instrument, {"instrument_node_id": swap_node_id, "instrument_type_id": swap_type, "asset_class": "DERIVATIVE", "base_currency_id": DEMO_IDS["gbp_currency"], "effective_from": today, "is_current": True, "sequence_no": 1})
            _insert_once(connection, m.instrument_dates, {"instrument_dates_id": dates_id, "instrument_node_id": swap_node_id, "effective_date": today, "maturity_date": maturity_date, "final_settlement_date": maturity_date})
            _insert_once(connection, m.swap_terms, {"instrument_node_id": swap_node_id, "swap_type": "TOTAL_RETURN"})
            _insert_once(connection, m.schedule, {"schedule_id": schedule_id, "owner_reference_node_id": swap_node_id, "schedule_type": "RESET_PAYMENT", "status": "ACTIVE"})
            _insert_once(connection, m.schedule_event, {"schedule_event_id": reset_event_id, "schedule_id": schedule_id, "event_sequence": 1, "event_type": "RESET", "event_date": reset_date, "payment_date": reset_date, "status": "SCHEDULED"})

        for swap_node_id, performance_leg_id, funding_leg_id, performance_reference_id, return_profile_id, spread, schedule_id in (
            (DEMO_IDS["bond_total_return_swap_node"], DEMO_IDS["bond_total_return_performance_leg"], DEMO_IDS["bond_total_return_funding_leg"], DEMO_IDS["bond_instrument_node"], gross_total_return_profile, 0.0150, DEMO_IDS["bond_total_return_schedule"]),
            (DEMO_IDS["qis_total_return_swap_node"], DEMO_IDS["qis_total_return_performance_leg"], DEMO_IDS["qis_total_return_funding_leg"], DEMO_IDS["qis_index_node"], net_total_return_profile, 0.0125, DEMO_IDS["qis_total_return_schedule"]),
            (DEMO_IDS["autocall_total_return_swap_node"], DEMO_IDS["autocall_total_return_performance_leg"], DEMO_IDS["autocall_total_return_funding_leg"], DEMO_IDS["autocall_instrument_node"], gross_total_return_profile, 0.0100, DEMO_IDS["autocall_total_return_schedule"]),
        ):
            _insert_once(connection, m.swap_leg, {"swap_leg_id": performance_leg_id, "swap_instrument_node_id": swap_node_id, "leg_number": 1, "leg_role": "PERFORMANCE", "pay_receive": "RECEIVE", "reference_node_id": performance_reference_id, "return_profile_id": return_profile_id})
            _insert_once(connection, m.swap_leg, {"swap_leg_id": funding_leg_id, "swap_instrument_node_id": swap_node_id, "leg_number": 2, "leg_role": "FUNDING", "pay_receive": "PAY", "reference_node_id": DEMO_IDS["sonia_rate_index_node"], "currency_id": DEMO_IDS["gbp_currency"], "spread": spread, "schedule_id": schedule_id})

        # The larger MVP fixture is kept in its own module so the original
        # focused scenarios remain readable while the loader stays one command.
        from .mvp_demo_data import load_mvp_demo_data

        load_mvp_demo_data(connection)
        _ensure_demo_definition_versions(connection)


def _ensure_demo_definition_versions(connection: Connection) -> None:
    """Give loader-owned synthetic projections immutable approved definitions.

    Never approve arbitrary application records or replace existing versions.
    Historical migrations cannot bootstrap records inserted after migration.
    """
    demo_ids = tuple(DEMO_IDS.values())
    for table, version, key, version_key, fields in (
        (m.instrument, m.instrument_definition_version, "instrument_node_id", "instrument_definition_version_id",
         ("instrument_type_id", "asset_class", "issuer_organisation_id", "base_currency_id", "effective_from", "effective_to")),
        (m.listing, m.listing_definition_version, "listing_node_id", "listing_definition_version_id",
         ("market_venue_id", "trading_currency_id", "trading_symbol", "quote_factor", "unit_multiplier", "effective_from", "effective_to")),
    ):
        rows = connection.execute(select(table).where(table.c[key].in_(demo_ids))).mappings().all()
        for row in rows:
            if connection.scalar(select(version.c[version_key]).where(version.c[key] == row[key]).limit(1)):
                continue
            values = {field: row[field] for field in fields}
            # Original synthetic projections predate effective-dated definitions.
            # Their documented scenario date supplies only this loader-owned fixture.
            values["effective_from"] = values["effective_from"] or date(2026, 8, 28)
            values.update({key: row[key], version_key: uuid5(NAMESPACE_URL, f"fortem-demo:{version.name}:{row[key]}"),
                           "sequence_no": 1, "is_current": True, "status": "APPROVED",
                           "approved_by_user_account_id": DEMO_IDS["demo_user_account"],
                           "approved_at_utc": datetime.now(timezone.utc)})
            connection.execute(version.insert().values(**values))
