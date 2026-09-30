"""Structural contract tests for the first security-master schema draft."""

import unittest

from security_master_schema.models import metadata


class SchemaMetadataTests(unittest.TestCase):
    def test_valuation_date_selection_and_snapshot_evidence_are_modelled(self) -> None:
        self.assertTrue(
            {
                "market_date",
                "valuation_cut_id",
            }.issubset(metadata.tables["md.market_data_observation"].c.keys())
        )
        self.assertTrue(
            {
                "subject_reference_node_id",
                "market_data_series_id",
                "pricing_date_rule",
                "lag_business_days",
                "market_calendar_id",
                "max_staleness_business_days",
                "missing_data_action",
            }.issubset(metadata.tables["ten.valuation_policy_rule"].c.keys())
        )
        self.assertTrue(
            {
                "pricing_date_requested",
                "pricing_date_used",
                "staleness_business_days",
                "staleness_status",
            }.issubset(metadata.tables["md.market_data_resolution_snapshot_item"].c.keys())
        )
        self.assertTrue(
            {
                "market_data_resolution_snapshot_item_id",
                "policy_rule_id",
                "pricing_date_requested",
                "pricing_date_used",
                "staleness_business_days",
                "staleness_status",
            }.issubset(metadata.tables["nav.nav_input_snapshot_item"].c.keys())
        )

    def test_core_tables_are_in_their_domain_schemas(self) -> None:
        expected_tables = {
            "secm.financial_reference_node",
            "secm.reference_node_type",
            "secm.instrument",
            "secm.instrument_type",
            "secm.taxonomy",
            "secm.taxonomy_value",
            "secm.instrument_taxonomy_assignment",
            "secm.listing",
            "secm.organisation",
            "secm.currency",
            "trd.trade",
            "trd.trade_booking_idempotency",
            "trd.cash_balance",
            "trd.trade_fee",
            "fee.fee_type",
            "fee.fee_rule",
            "fee.fee_rule_target",
            "md.market_data_series",
            "md.market_data_observation",
            "cal.market_calendar",
            "cal.market_calendar_session",
            "cal.market_calendar_holiday",
            "secm.return_profile",
            "secm.index_kind_catalogue",
            "secm.crypto_network",
            "secm.crypto_asset_terms",
            "secm.crypto_asset_deployment",
            "secm.index_family",
            "secm.index_terms",
            "secm.index_methodology_version",
            "secm.etp_terms",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))

    def test_return_profiles_and_index_terms_are_linked_to_canonical_nodes(self) -> None:
        return_profile = metadata.tables["secm.return_profile"]
        index_family = metadata.tables["secm.index_family"]
        index_terms = metadata.tables["secm.index_terms"]
        methodology = metadata.tables["secm.index_methodology_version"]

        self.assertIn("profile_code", return_profile.c)
        self.assertIn("return_profile_id", index_terms.c)
        self.assertIn("index_family_id", index_terms.c)
        self.assertIn(
            "secm.return_profile.return_profile_id",
            {foreign_key.target_fullname for foreign_key in index_terms.c.return_profile_id.foreign_keys},
        )
        self.assertIn(
            "secm.financial_reference_node.reference_node_id",
            {foreign_key.target_fullname for foreign_key in index_family.c.family_node_id.foreign_keys},
        )
        self.assertIn(
            "secm.financial_reference_node.reference_node_id",
            {foreign_key.target_fullname for foreign_key in index_terms.c.index_node_id.foreign_keys},
        )
        self.assertIn(
            "secm.index_terms.index_node_id",
            {foreign_key.target_fullname for foreign_key in methodology.c.index_node_id.foreign_keys},
        )
        self.assertIn("requires_financing_reference", return_profile.c)
        self.assertIn(
            "secm.return_profile.return_profile_id",
            {foreign_key.target_fullname for foreign_key in metadata.tables["secm.swap_leg"].c.return_profile_id.foreign_keys},
        )
        self.assertTrue(
            any(constraint.name == "ck_index_methodology_version_valid_period" for constraint in methodology.constraints)
        )

    def test_index_kind_catalogue_carries_governed_semantics(self) -> None:
        catalogue = metadata.tables["secm.index_kind_catalogue"]
        self.assertTrue(
            {
                "index_kind_code",
                "display_name",
                "description",
                "dissemination_class",
                "methodology_ownership",
                "example_text",
                "status",
                "sort_order",
            }.issubset(catalogue.c.keys())
        )
        self.assertIn(
            "secm.index_kind_catalogue.index_kind_code",
            {foreign_key.target_fullname for foreign_key in metadata.tables["secm.index_terms"].c.index_kind.foreign_keys},
        )

    def test_crypto_terms_separate_asset_identity_from_chain_deployments(self) -> None:
        network = metadata.tables["secm.crypto_network"]
        terms = metadata.tables["secm.crypto_asset_terms"]
        deployment = metadata.tables["secm.crypto_asset_deployment"]
        self.assertTrue({"network_code", "network_family", "chain_identifier", "native_currency_code"}.issubset(network.c.keys()))
        self.assertTrue({"instrument_node_id", "asset_subtype", "native_symbol", "protocol_name", "issuer_organisation_id", "sequence_no", "is_current"}.issubset(terms.c.keys()))
        self.assertTrue({"instrument_node_id", "crypto_network_id", "deployment_kind", "contract_address", "token_standard", "decimals", "is_canonical"}.issubset(deployment.c.keys()))
        self.assertIn("secm.crypto_network.crypto_network_id", {foreign_key.target_fullname for foreign_key in deployment.c.crypto_network_id.foreign_keys})
        self.assertTrue(any(constraint.name == "ck_crypto_asset_deployment_address" for constraint in deployment.constraints))

    def test_etp_terms_cover_common_exchange_traded_product_economics(self) -> None:
        etp_terms = metadata.tables["secm.etp_terms"]

        self.assertTrue(
            {
                "instrument_node_id",
                "etp_kind",
                "legal_form",
                "replication_method",
                "collateralisation_type",
                "redemption_model",
                "distribution_policy",
                "reference_node_id",
                "effective_from",
                "sequence_no",
            }.issubset(etp_terms.c.keys())
        )
        self.assertIn(
            "secm.instrument.instrument_node_id",
            {foreign_key.target_fullname for foreign_key in etp_terms.c.instrument_node_id.foreign_keys},
        )
        self.assertIn(
            "secm.financial_reference_node.reference_node_id",
            {foreign_key.target_fullname for foreign_key in etp_terms.c.reference_node_id.foreign_keys},
        )
        self.assertTrue(
            any(constraint.name == "ck_etp_terms_valid_period" for constraint in etp_terms.constraints)
        )

    def test_every_schema_column_has_documentation(self) -> None:
        undocumented = [
            f"{table.fullname}.{column.name}"
            for table in metadata.tables.values()
            for column in table.columns
            if not column.comment
        ]

        self.assertEqual([], undocumented)

    def test_trade_and_market_data_reference_the_canonical_security_master(self) -> None:
        trade = metadata.tables["trd.trade"]
        series = metadata.tables["md.market_data_series"]

        self.assertIn(
            "secm.financial_reference_node.reference_node_id",
            {foreign_key.target_fullname for foreign_key in trade.c.trade_subject_reference_node_id.foreign_keys},
        )
        self.assertIn(
            "secm.financial_reference_node.reference_node_id",
            {foreign_key.target_fullname for foreign_key in series.c.reference_node_id.foreign_keys},
        )

    def test_market_data_series_describes_expected_coverage_and_calendar(self) -> None:
        series = metadata.tables["md.market_data_series"]

        self.assertTrue(
            {
                "expected_frequency_code",
                "expected_market_calendar_id",
                "coverage_start_date",
                "coverage_end_date",
            }.issubset(series.c.keys())
        )
        self.assertIn(
            "cal.market_calendar.market_calendar_id",
            {foreign_key.target_fullname for foreign_key in series.c.expected_market_calendar_id.foreign_keys},
        )

    def test_reference_nodes_use_the_governed_node_type_catalogue(self) -> None:
        reference_node = metadata.tables["secm.financial_reference_node"]

        self.assertIn(
            "secm.reference_node_type.reference_node_type_id",
            {foreign_key.target_fullname for foreign_key in reference_node.c.reference_node_type_id.foreign_keys},
        )

    def test_instruments_use_the_governed_instrument_type_catalogue(self) -> None:
        instrument = metadata.tables["secm.instrument"]

        self.assertIn(
            "secm.instrument_type.instrument_type_id",
            {foreign_key.target_fullname for foreign_key in instrument.c.instrument_type_id.foreign_keys},
        )

    def test_instrument_taxonomy_assignments_use_governed_taxonomy_values(self) -> None:
        assignment = metadata.tables["secm.instrument_taxonomy_assignment"]

        self.assertIn(
            "secm.taxonomy_value.taxonomy_value_id",
            {foreign_key.target_fullname for foreign_key in assignment.c.taxonomy_value_id.foreign_keys},
        )

    def test_tenant_scope_and_external_id_mapping_tables_are_available(self) -> None:
        expected_tables = {
            "ten.tenant",
            "ten.reference_node_scope",
            "ing.integration_source_system",
            "ing.external_id_namespace",
            "ing.external_object_mapping",
            "ing.source_payload",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))

        namespace = metadata.tables["ing.external_id_namespace"]
        mapping = metadata.tables["ing.external_object_mapping"]

        self.assertIn(
            "ing.integration_source_system.integration_source_system_id",
            {foreign_key.target_fullname for foreign_key in namespace.c.integration_source_system_id.foreign_keys},
        )
        self.assertIn("external_object_type", mapping.c)
        self.assertIn("target_object_type", mapping.c)
        self.assertIn("target_object_id", mapping.c)
        self.assertIn("valid_from", mapping.c)
        self.assertIn("valid_to", mapping.c)

    def test_tenant_operational_mapping_tables_are_available(self) -> None:
        profile = metadata.tables["cfg.external_data_mapping_profile"]
        mapping = metadata.tables["cfg.external_data_object_mapping"]

        self.assertIn("tenant_id", profile.c)
        self.assertIn("integration_source_system_id", profile.c)
        self.assertIn("normalization_mode", profile.c)
        self.assertIn("source_object_scope", mapping.c)
        self.assertIn("external_id_raw", mapping.c)
        self.assertIn("external_id_normalized", mapping.c)

    def test_tenant_capability_and_operating_profile_tables_are_available(self) -> None:
        expected_tables = {
            "ten.operating_profile",
            "ten.tenant_operating_profile_assignment",
            "ten.platform_module",
            "ten.operating_profile_module_recommendation",
            "ten.tenant_module_entitlement",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))
        assignment = metadata.tables["ten.tenant_operating_profile_assignment"]
        entitlement = metadata.tables["ten.tenant_module_entitlement"]
        self.assertIn("assignment_source", assignment.c)
        self.assertIn("entitlement_state", entitlement.c)
        self.assertIn("entitlement_source", entitlement.c)

    def test_market_data_observations_capture_dataset_and_licence_provenance(self) -> None:
        expected_tables = {
            "md.data_provider",
            "md.provider_product",
            "md.dataset",
            "md.data_licence",
            "md.dataset_licence_assignment",
            "ten.tenant_dataset_entitlement",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))

        observation = metadata.tables["md.market_data_observation"]
        self.assertFalse(observation.c.dataset_id.nullable)
        self.assertTrue(observation.c.acquisition_licence_id.nullable)
        self.assertIn(
            "md.dataset.dataset_id",
            {foreign_key.target_fullname for foreign_key in observation.c.dataset_id.foreign_keys},
        )
        self.assertIn(
            "md.data_licence.data_licence_id",
            {foreign_key.target_fullname for foreign_key in observation.c.acquisition_licence_id.foreign_keys},
        )

    def test_external_mapping_and_dataset_observation_lookup_indexes_exist(self) -> None:
        index_names = {
            index.name
            for table in metadata.tables.values()
            for index in table.indexes
        }

        self.assertTrue(
            {
                "ix_external_object_mapping_lookup",
                "ix_external_object_mapping_target",
                "ix_market_data_observation_dataset_observed",
            }.issubset(index_names)
        )

    def test_reference_lifecycle_and_terms_tables_cover_the_documented_core(self) -> None:
        expected_tables = {
            "secm.organisation_identifier",
            "secm.instrument_party_role",
            "secm.geographic_area",
            "secm.country_terms",
            "secm.geographic_area_membership",
            "secm.listing_quotation_terms",
            "secm.instrument_contract_unit_terms",
            "secm.schedule",
            "secm.schedule_event",
            "secm.future_family",
            "secm.future_terms",
            "secm.option_terms",
            "secm.option_strike_reset_rule",
            "secm.option_strike_fixing",
            "secm.option_strike_adjustment",
            "secm.fx_forward_terms",
            "secm.swap_terms",
            "secm.swap_leg",
            "secm.structured_product_terms",
            "secm.structured_product_condition_group",
            "secm.structured_product_range_accrual_terms",
            "secm.structured_product_supertracker_terms",
            "secm.barrier_rule",
            "secm.condition_group_action",
            "secm.reference_constituent_snapshot",
            "secm.reference_constituent_snapshot_item",
            "secm.corporate_action",
            "secm.corporate_action_date",
            "secm.corporate_action_effect",
            "secm.market_data_adjustment_factor",
            "secm.regulatory_label",
            "secm.reference_node_regulatory_label_assignment",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))

        venue = metadata.tables["secm.market_venue"]
        schedule = metadata.tables["secm.schedule"]
        policy_rule = metadata.tables["ten.valuation_policy_rule"]
        calendar_target = "cal.market_calendar.market_calendar_id"
        self.assertIn(calendar_target, {fk.target_fullname for fk in venue.c.market_calendar_id.foreign_keys})
        self.assertIn(calendar_target, {fk.target_fullname for fk in schedule.c.calendar_id.foreign_keys})
        self.assertIn(calendar_target, {fk.target_fullname for fk in policy_rule.c.market_calendar_id.foreign_keys})

    def test_calendar_tables_capture_sessions_and_holidays(self) -> None:
        calendar = metadata.tables["cal.market_calendar"]
        session = metadata.tables["cal.market_calendar_session"]
        holiday = metadata.tables["cal.market_calendar_holiday"]
        valuation_cut = metadata.tables["md.valuation_cut"]

        self.assertIn("timezone_name", calendar.c)
        self.assertIn("session_date", session.c)
        self.assertIn("session_status", session.c)
        self.assertIn("holiday_date", holiday.c)
        self.assertIn("holiday_name", holiday.c)
        self.assertIn("market_calendar_id", valuation_cut.c)
        self.assertIn(
            "cal.market_calendar.market_calendar_id",
            {fk.target_fullname for fk in valuation_cut.c.market_calendar_id.foreign_keys},
        )
        self.assertIn(
            "cal.market_calendar.market_calendar_id",
            {fk.target_fullname for fk in session.c.market_calendar_id.foreign_keys},
        )
        self.assertIn(
            "cal.market_calendar.market_calendar_id",
            {fk.target_fullname for fk in holiday.c.market_calendar_id.foreign_keys},
        )

        future_terms = metadata.tables["secm.future_terms"]
        swap_leg = metadata.tables["secm.swap_leg"]
        constituent_item = metadata.tables["secm.reference_constituent_snapshot_item"]

        self.assertIn(
            "secm.future_family.future_family_id",
            {foreign_key.target_fullname for foreign_key in future_terms.c.future_family_id.foreign_keys},
        )
        self.assertIn(
            "secm.swap_terms.instrument_node_id",
            {foreign_key.target_fullname for foreign_key in swap_leg.c.swap_instrument_node_id.foreign_keys},
        )
        self.assertIn(
            "secm.reference_constituent_snapshot.reference_constituent_snapshot_id",
            {foreign_key.target_fullname for foreign_key in constituent_item.c.reference_constituent_snapshot_id.foreign_keys},
        )

    def test_valuation_and_soft_nav_tables_retain_reproducible_input_lineage(self) -> None:
        expected_tables = {
            "ten.valuation_policy",
            "ten.valuation_policy_rule",
            "md.market_data_resolution_snapshot",
            "md.market_data_resolution_snapshot_item",
            "nav.nav_calculation_run",
            "nav.nav_input_snapshot",
            "nav.nav_input_snapshot_item",
            "nav.nav_valuation_line",
            "nav.nav_result",
            "nav.nav_reconciliation",
        }

        self.assertTrue(expected_tables.issubset(metadata.tables))

        nav_item = metadata.tables["nav.nav_input_snapshot_item"]
        self.assertIn(
            "md.market_data_observation.market_data_observation_id",
            {foreign_key.target_fullname for foreign_key in nav_item.c.market_data_observation_id.foreign_keys},
        )
        self.assertIn(
            "md.dataset.dataset_id",
            {foreign_key.target_fullname for foreign_key in nav_item.c.dataset_id.foreign_keys},
        )

    def test_legacy_venue_and_date_models_have_precise_additive_replacements(self) -> None:
        venue = metadata.tables["secm.market_venue"]
        dates = metadata.tables["secm.instrument_dates"]

        self.assertIn("operating_market_venue_id", venue.c)
        self.assertIn("primary_geographic_area_id", venue.c)
        self.assertIn("market_calendar_id", venue.c)
        self.assertIn("timezone_name", venue.c)
        self.assertIn("first_trading_date", dates.c)
        self.assertIn("last_trading_date", dates.c)
        self.assertIn("final_valuation_date", dates.c)
        self.assertIn("final_settlement_date", dates.c)

    def test_soft_nav_run_can_reference_an_immutable_position_snapshot(self) -> None:
        self.assertIn("trd.position_snapshot", metadata.tables)
        self.assertIn("trd.position_snapshot_line", metadata.tables)

        nav_run = metadata.tables["nav.nav_calculation_run"]
        self.assertIn(
            "trd.position_snapshot.position_snapshot_id",
            {foreign_key.target_fullname for foreign_key in nav_run.c.position_snapshot_id.foreign_keys},
        )

    def test_fund_share_classes_and_bonds_have_versioned_economic_terms(self) -> None:
        self.assertTrue(
            {
                "secm.fund",
                "secm.fund_share_class_terms",
                "secm.bond_terms",
            }.issubset(metadata.tables)
        )
        share_class_terms = metadata.tables["secm.fund_share_class_terms"]
        bond_terms = metadata.tables["secm.bond_terms"]
        self.assertIn("nav_publication_lag_business_days", share_class_terms.c)
        self.assertIn("sequence_no", share_class_terms.c)
        self.assertIn("quotation_basis", bond_terms.c)
        self.assertIn("coupon_type", bond_terms.c)

    def test_day_count_conventions_are_governed_secm_reference_data(self) -> None:
        self.assertIn("secm.day_count_convention", metadata.tables)
        convention = metadata.tables["secm.day_count_convention"]
        self.assertTrue(
            {
                "day_count_convention_id",
                "code",
                "display_name",
                "description",
                "status",
            }.issubset(convention.c.keys())
        )

        bond_terms = metadata.tables["secm.bond_terms"]
        self.assertIn("day_count_convention_id", bond_terms.c)
        self.assertTrue(bond_terms.c.day_count_convention_id.nullable)
        self.assertIn(
            "secm.day_count_convention.day_count_convention_id",
            {foreign_key.target_fullname for foreign_key in bond_terms.c.day_count_convention_id.foreign_keys},
        )

        fee_rule = metadata.tables["fee.fee_rule"]
        self.assertIn("day_count_convention_id", fee_rule.c)
        self.assertIn(
            "secm.day_count_convention.day_count_convention_id",
            {foreign_key.target_fullname for foreign_key in fee_rule.c.day_count_convention_id.foreign_keys},
        )

    def test_market_data_series_have_governed_measurement_semantics(self) -> None:
        self.assertIn("md.series_measure_definition", metadata.tables)
        definition = metadata.tables["md.series_measure_definition"]
        self.assertTrue(
            {
                "series_measure_definition_id",
                "measure_code",
                "unit_type",
                "default_change_method",
                "change_display_unit",
            }.issubset(definition.c.keys())
        )
        series = metadata.tables["md.market_data_series"]
        self.assertIn("measure_definition_id", series.c)
        self.assertTrue(series.c.measure_definition_id.nullable)
        self.assertIn(
            "md.series_measure_definition.series_measure_definition_id",
            {foreign_key.target_fullname for foreign_key in series.c.measure_definition_id.foreign_keys},
        )
