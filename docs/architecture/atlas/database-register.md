# Exact architecture register

Snapshot: 29 October 2026, before the same-day API service extraction. Table/column
metadata and static imports only; no business rows. The extraction changed no
schema; code counts/import edges below remain a historical baseline. Read the
[current atlas ownership notes](README.md) before interpreting these counts.

## Database schema references

Each count is the number of foreign-key **constraints** from the source schema to the target schema. Composite keys count once. Same-schema relationships are retained in the table register below. These are not processing-flow arrows.

| Dependent schema | Referenced schema | Constraints |
| --- | --- | ---: |
| `cal` | `secm` | 2 |
| `cal` | `ten` | 2 |
| `cfg` | `ing` | 2 |
| `cfg` | `md` | 1 |
| `cfg` | `secm` | 2 |
| `cfg` | `ten` | 1 |
| `fee` | `ing` | 1 |
| `fee` | `secm` | 6 |
| `fee` | `ten` | 1 |
| `fee` | `trd` | 1 |
| `ing` | `secm` | 3 |
| `ing` | `ten` | 3 |
| `md` | `cal` | 2 |
| `md` | `ing` | 6 |
| `md` | `secm` | 13 |
| `md` | `ten` | 9 |
| `md` | `trd` | 1 |
| `nav` | `ing` | 1 |
| `nav` | `md` | 9 |
| `nav` | `secm` | 27 |
| `nav` | `ten` | 12 |
| `nav` | `trd` | 20 |
| `reg` | `secm` | 5 |
| `reg` | `ten` | 5 |
| `reg` | `trd` | 3 |
| `secm` | `cal` | 3 |
| `secm` | `ing` | 30 |
| `secm` | `md` | 7 |
| `secm` | `ten` | 4 |
| `ten` | `cal` | 1 |
| `ten` | `md` | 7 |
| `ten` | `secm` | 16 |
| `ten` | `trd` | 2 |
| `trd` | `fee` | 1 |
| `trd` | `ing` | 2 |
| `trd` | `md` | 1 |
| `trd` | `secm` | 55 |
| `trd` | `ten` | 22 |

## Complete table register

All 204 application tables after runtime metadata registration. Names match the inspected database; the `public.alembic_version` bookkeeping table is excluded. Reference lists identify table targets, not complete column-level join conditions; those are retained in the JSON inventory.

### cal

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `cal.calendar_assignment` | 13 | `calendar_assignment_id` | `cal.market_calendar`, `secm.user_account`, `ten.tenant` |
| `cal.market_calendar` | 17 | `market_calendar_id` | `secm.user_account`, `ten.tenant` |
| `cal.market_calendar_holiday` | 7 | `market_calendar_holiday_id` | `cal.market_calendar` |
| `cal.market_calendar_session` | 8 | `market_calendar_session_id` | `cal.market_calendar` |

### cfg

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `cfg.external_data_mapping_profile` | 16 | `external_data_mapping_profile_id` | `ing.integration_source_system`, `md.dataset`, `secm.organisation`, `ten.tenant` |
| `cfg.external_data_object_mapping` | 18 | `external_data_object_mapping_id` | `cfg.external_data_mapping_profile`, `cfg.external_data_object_mapping`, `ing.source_payload`, `secm.user_account` |

### fee

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `fee.fee_rule` | 27 | `fee_rule_id` | `fee.fee_rule`, `fee.fee_type`, `ing.source_payload`, `secm.currency`, `secm.day_count_convention`, `secm.user_account`, `ten.tenant` |
| `fee.fee_rule_target` | 12 | `fee_rule_target_id` | `fee.fee_rule`, `secm.financial_reference_node`, `secm.organisation`, `trd.strategy` |
| `fee.fee_type` | 6 | `fee_type_id` | None |

### ing

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `ing.external_id_namespace` | 8 | `external_id_namespace_id` | `ing.integration_source_system` |
| `ing.external_object_mapping` | 19 | `external_object_mapping_id` | `ing.external_id_namespace`, `ing.external_object_mapping`, `ing.source_payload`, `secm.market_venue`, `secm.user_account`, `ten.tenant` |
| `ing.integration_source_system` | 9 | `integration_source_system_id` | `secm.organisation`, `ten.tenant` |
| `ing.source_payload` | 10 | `source_payload_id` | `ing.integration_source_system`, `ten.tenant` |

### md

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `md.bond_quote_accrual` | 6 | `observation_id` | `md.market_data_observation` |
| `md.data_licence` | 10 | `data_licence_id` | `secm.organisation` |
| `md.data_provider` | 6 | `data_provider_id` | `secm.organisation`, `ten.tenant` |
| `md.dataset` | 10 | `dataset_id` | `md.provider_product` |
| `md.dataset_access_profile` | 8 | `dataset_id` | `ing.external_id_namespace`, `md.dataset`, `secm.organisation`, `ten.tenant` |
| `md.dataset_coverage_package` | 11 | `coverage_package_id` | `md.data_provider`, `md.dataset`, `secm.market_venue` |
| `md.dataset_licence_assignment` | 7 | `dataset_licence_assignment_id` | `md.data_licence`, `md.dataset` |
| `md.dataset_right_requirement` | 5 | `requirement_id` | `md.dataset`, `md.dataset_licence_assignment` |
| `md.licence_activity_grant` | 9 | `grant_id` | `md.dataset_licence_assignment` |
| `md.market_data_ingestion_attempt` | 9 | `attempt_id` | `md.market_data_ingestion_job`, `md.market_data_ingestion_run` |
| `md.market_data_ingestion_job` | 11 | `job_id` | `ing.external_id_namespace`, `md.dataset`, `secm.user_account`, `ten.tenant` |
| `md.market_data_ingestion_run` | 9 | `run_id` | `ing.source_payload`, `md.dataset` |
| `md.market_data_mapping_history_review` | 10 | `review_id` | `ing.external_object_mapping`, `md.market_data_mapping_history_review`, `secm.user_account`, `ten.tenant` |
| `md.market_data_observation` | 19 | `market_data_observation_id` | `ing.source_payload`, `md.data_licence`, `md.dataset`, `md.market_data_observation`, `md.market_data_series`, `md.market_data_vintage`, `md.valuation_cut` |
| `md.market_data_price_basis_proof` | 5 | `proof_id` | `md.market_data_observation` |
| `md.market_data_resolution_idempotency` | 8 | `market_data_resolution_idempotency_id` | `md.market_data_resolution_snapshot`, `ten.tenant` |
| `md.market_data_resolution_snapshot` | 12 | `market_data_resolution_snapshot_id` | `md.valuation_cut`, `ten.tenant`, `ten.valuation_policy`, `trd.strategy` |
| `md.market_data_resolution_snapshot_item` | 23 | `market_data_resolution_snapshot_item_id` | `md.data_licence`, `md.dataset`, `md.market_data_observation`, `md.market_data_resolution_snapshot`, `md.market_data_series`, `md.market_data_vintage`, `secm.currency`, `secm.financial_reference_node`, `ten.valuation_policy_rule` |
| `md.market_data_series` | 17 | `market_data_series_id` | `cal.market_calendar`, `md.dataset`, `md.series_measure_definition`, `md.valuation_cut`, `secm.currency`, `secm.financial_reference_node` |
| `md.market_data_series_coverage` | 3 | `dataset_id`, `market_data_series_id` | `md.dataset`, `md.dataset_coverage_package`, `md.market_data_series` |
| `md.market_data_series_dimension` | 6 | `market_data_series_dimension_id` | `md.market_data_series` |
| `md.market_data_vintage` | 11 | `market_data_vintage_id` | `ing.source_payload`, `md.data_provider`, `md.dataset` |
| `md.provider_product` | 6 | `provider_product_id` | `md.data_provider` |
| `md.series_measure_definition` | 12 | `series_measure_definition_id` | None |
| `md.source_priority_entry` | 3 | `source_priority_version_id`, `dataset_id` | `md.dataset`, `md.source_priority_version` |
| `md.source_priority_version` | 10 | `source_priority_version_id` | `secm.instrument_type`, `secm.user_account`, `ten.tenant` |
| `md.valuation_cut` | 7 | `valuation_cut_id` | `cal.market_calendar` |

### nav

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `nav.accrued_interest_balance` | 21 | `balance_id` | `nav.valuation_attempt`, `secm.currency`, `secm.instrument`, `trd.strategy` |
| `nav.daily_accrual_input` | 16 | `input_id` | `nav.daily_accrual_input`, `secm.currency`, `secm.instrument`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `nav.nav_calculation_run` | 11 | `nav_calculation_run_id` | `md.market_data_resolution_snapshot`, `md.valuation_cut`, `ten.tenant`, `ten.valuation_policy`, `trd.position_snapshot`, `trd.strategy` |
| `nav.nav_input_snapshot` | 5 | `nav_input_snapshot_id` | `nav.nav_calculation_run` |
| `nav.nav_input_snapshot_item` | 17 | `nav_input_snapshot_item_id` | `md.data_licence`, `md.dataset`, `md.market_data_observation`, `md.market_data_resolution_snapshot_item`, `md.market_data_series`, `nav.nav_input_snapshot`, `secm.currency`, `secm.financial_reference_node`, `ten.valuation_policy_rule` |
| `nav.nav_reconciliation` | 9 | `nav_reconciliation_id` | `ing.source_payload`, `nav.nav_calculation_run`, `secm.currency` |
| `nav.nav_result` | 9 | `nav_result_id` | `nav.nav_calculation_run`, `secm.currency` |
| `nav.nav_valuation_line` | 11 | `nav_valuation_line_id` | `nav.nav_calculation_run`, `nav.nav_input_snapshot_item`, `secm.currency`, `secm.financial_reference_node` |
| `nav.pnl_amendment_request` | 19 | `request_id` | `nav.pnl_attribution`, `nav.pnl_review_batch`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `nav.pnl_attribution` | 21 | `attribution_id` | `nav.pnl_attribution`, `nav.valuation_attempt`, `secm.currency`, `secm.financial_reference_node`, `ten.tenant`, `trd.cash_account`, `trd.strategy`, `trd.trade` |
| `nav.pnl_attribution_lineage` | 5 | `lineage_id` | `nav.pnl_attribution`, `trd.trade`, `trd.trade_lifecycle_event` |
| `nav.pnl_review_batch` | 12 | `batch_id` | `nav.valuation_attempt`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `nav.pnl_review_event` | 6 | `review_event_id` | `nav.pnl_review_batch`, `secm.user_account` |
| `nav.pnl_review_item` | 8 | `item_id` | `nav.pnl_attribution`, `nav.pnl_review_batch`, `secm.currency`, `trd.cash_account`, `trd.trade` |
| `nav.strategy_ledger_change` | 10 | `change_id` | `secm.user_account`, `ten.tenant`, `trd.strategy`, `trd.trade` |
| `nav.strategy_ledger_revision` | 3 | `tenant_id`, `strategy_id` | `trd.strategy` |
| `nav.valuation_attempt` | 12 | `attempt_id` | `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `nav.valuation_mark` | 19 | `valuation_mark_id` | `md.market_data_resolution_snapshot`, `md.valuation_cut`, `secm.currency`, `secm.financial_reference_node`, `secm.user_account`, `ten.tenant`, `trd.position_snapshot_line`, `trd.strategy`, `trd.trade` |
| `nav.valuation_publication_policy` | 7 | `tenant_id`, `revision` | `secm.user_account`, `ten.tenant` |
| `nav.valuation_reassessment_request` | 7 | `request_id` | `secm.user_account`, `ten.tenant` |
| `nav.valuation_run_event` | 6 | `event_id` | `nav.valuation_attempt` |

### reg

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `reg.candidate_revision` | 6 | `candidate_id`, `revision` | `reg.transaction_candidate`, `secm.user_account`, `ten.tenant` |
| `reg.preparation_export` | 11 | `export_id` | `reg.reporting_profile`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `reg.profile_revision` | 6 | `profile_id`, `revision` | `reg.reporting_profile`, `secm.user_account`, `ten.tenant` |
| `reg.reporting_profile` | 10 | `profile_id` | `secm.user_account`, `ten.tenant` |
| `reg.transaction_candidate` | 15 | `candidate_id` | `reg.reporting_profile`, `secm.user_account`, `ten.tenant`, `trd.strategy`, `trd.trade` |

### secm

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `secm.amc_terms` | 16 | `amc_terms_id` | `secm.financial_reference_node`, `secm.instrument`, `secm.organisation` |
| `secm.auth_identity` | 7 | `auth_identity_id` | `secm.user_account` |
| `secm.barrier_rule` | 14 | `barrier_rule_id` | `ing.source_payload`, `secm.financial_reference_node`, `secm.structured_product_condition_group` |
| `secm.bond_cashflow` | 12 | `cashflow_id` | `secm.bond_cashflow_schedule` |
| `secm.bond_cashflow_schedule` | 18 | `schedule_id` | `cal.market_calendar`, `secm.bond_cashflow_schedule`, `secm.bond_terms`, `secm.currency`, `secm.day_count_convention`, `secm.instrument`, `secm.user_account`, `ten.tenant` |
| `secm.bond_terms` | 17 | `bond_terms_id` | `secm.currency`, `secm.day_count_convention`, `secm.instrument` |
| `secm.condition_group_action` | 17 | `condition_group_action_id` | `ing.source_payload`, `secm.currency`, `secm.financial_reference_node`, `secm.instrument_composition`, `secm.schedule`, `secm.structured_product_condition_group` |
| `secm.corporate_action` | 9 | `corporate_action_id` | `ing.source_payload`, `secm.instrument` |
| `secm.corporate_action_date` | 6 | `corporate_action_date_id` | `secm.corporate_action` |
| `secm.corporate_action_effect` | 8 | `corporate_action_effect_id` | `secm.corporate_action`, `secm.currency`, `secm.financial_reference_node` |
| `secm.corporate_action_replay_decision` | 6 | `replay_decision_id` | `secm.corporate_action`, `secm.user_account` |
| `secm.country_terms` | 4 | `geographic_area_id` | `secm.geographic_area` |
| `secm.crypto_asset_deployment` | 14 | `crypto_asset_deployment_id` | `ing.source_payload`, `secm.crypto_network`, `secm.instrument` |
| `secm.crypto_asset_terms` | 12 | `crypto_asset_terms_id` | `ing.source_payload`, `secm.instrument`, `secm.organisation` |
| `secm.crypto_network` | 8 | `crypto_network_id` | None |
| `secm.currency` | 8 | `currency_id` | `secm.financial_reference_node` |
| `secm.day_count_convention` | 7 | `day_count_convention_id` | None |
| `secm.entity` | 6 | `entity_id` | None |
| `secm.etp_terms` | 15 | `etp_terms_id` | `ing.source_payload`, `secm.financial_reference_node`, `secm.instrument` |
| `secm.financial_reference_identifier` | 8 | `financial_reference_identifier_id` | `secm.financial_reference_node`, `secm.identifier_scheme`, `secm.market_venue` |
| `secm.financial_reference_node` | 8 | `reference_node_id` | `secm.reference_node_type` |
| `secm.fund` | 7 | `fund_reference_node_id` | `secm.financial_reference_node`, `secm.fund`, `secm.organisation` |
| `secm.fund_share_class_terms` | 13 | `fund_share_class_terms_id` | `secm.currency`, `secm.fund`, `secm.instrument` |
| `secm.future_family` | 7 | `future_family_id` | `secm.currency`, `secm.financial_reference_node` |
| `secm.future_terms` | 7 | `instrument_node_id` | `secm.future_family`, `secm.instrument` |
| `secm.fx_forward_terms` | 7 | `instrument_node_id` | `secm.currency`, `secm.instrument` |
| `secm.geographic_area` | 8 | `geographic_area_id` | None |
| `secm.geographic_area_membership` | 6 | `geographic_area_membership_id` | `secm.geographic_area` |
| `secm.identifier_scheme` | 5 | `identifier_scheme_id` | None |
| `secm.index_family` | 4 | `index_family_id` | `secm.financial_reference_node`, `secm.organisation` |
| `secm.index_kind_catalogue` | 9 | `index_kind_catalogue_id` | None |
| `secm.index_methodology_version` | 17 | `index_methodology_version_id` | `ing.source_payload`, `secm.financial_reference_node`, `secm.index_terms`, `secm.user_account` |
| `secm.index_terms` | 11 | `index_node_id` | `secm.currency`, `secm.financial_reference_node`, `secm.index_family`, `secm.index_kind_catalogue`, `secm.organisation`, `secm.return_profile` |
| `secm.instrument` | 9 | `instrument_node_id` | `secm.currency`, `secm.financial_reference_node`, `secm.instrument_type`, `secm.organisation` |
| `secm.instrument_booking_convention` | 8 | `instrument_booking_convention_id` | `secm.instrument`, `secm.user_account` |
| `secm.instrument_composition` | 12 | `instrument_composition_id` | `ing.source_payload`, `secm.financial_reference_node`, `secm.instrument`, `secm.structured_product_terms` |
| `secm.instrument_contract_unit_terms` | 7 | `instrument_contract_unit_terms_id` | `secm.instrument` |
| `secm.instrument_dates` | 15 | `instrument_dates_id` | `secm.instrument` |
| `secm.instrument_definition_version` | 14 | `instrument_definition_version_id` | `ing.source_payload`, `secm.currency`, `secm.instrument`, `secm.instrument_type`, `secm.organisation`, `secm.user_account` |
| `secm.instrument_party_role` | 7 | `instrument_party_role_id` | `ing.source_payload`, `secm.instrument`, `secm.organisation` |
| `secm.instrument_relationship` | 7 | `instrument_relationship_id` | `secm.financial_reference_node` |
| `secm.instrument_taxonomy_assignment` | 7 | `instrument_taxonomy_assignment_id` | `secm.instrument`, `secm.taxonomy_value` |
| `secm.instrument_type` | 7 | `instrument_type_id` | None |
| `secm.listing` | 11 | `listing_node_id` | `secm.currency`, `secm.financial_reference_node`, `secm.instrument`, `secm.market_venue` |
| `secm.listing_definition_version` | 15 | `listing_definition_version_id` | `ing.source_payload`, `secm.currency`, `secm.listing`, `secm.market_venue`, `secm.user_account` |
| `secm.listing_quotation_terms` | 10 | `listing_quotation_terms_id` | `secm.currency`, `secm.listing` |
| `secm.market_data_adjustment_factor` | 8 | `market_data_adjustment_factor_id` | `md.market_data_series`, `secm.corporate_action` |
| `secm.market_venue` | 11 | `market_venue_id` | `cal.market_calendar`, `secm.geographic_area`, `secm.market_venue`, `secm.organisation` |
| `secm.market_venue_identifier` | 5 | `market_venue_identifier_id` | `secm.market_venue` |
| `secm.option_strike_adjustment` | 14 | `option_strike_adjustment_id` | `ing.source_payload`, `secm.corporate_action`, `secm.option_strike_adjustment`, `secm.option_terms` |
| `secm.option_strike_fixing` | 10 | `option_strike_fixing_id` | `md.market_data_observation`, `md.market_data_resolution_snapshot`, `secm.option_strike_fixing`, `secm.option_strike_reset_rule` |
| `secm.option_strike_reset_rule` | 11 | `option_strike_reset_rule_id` | `md.market_data_series`, `secm.currency`, `secm.financial_reference_node`, `secm.option_terms`, `secm.schedule_event` |
| `secm.option_terms` | 24 | `option_terms_id` | `secm.currency`, `secm.financial_reference_node`, `secm.instrument`, `secm.option_terms`, `secm.schedule`, `secm.structured_product_initial_fixing` |
| `secm.organisation` | 10 | `organisation_id` | `secm.entity` |
| `secm.organisation_identifier` | 8 | `organisation_identifier_id` | `ing.source_payload`, `secm.organisation` |
| `secm.person` | 6 | `person_id` | None |
| `secm.person_organisation_affiliation` | 7 | `person_organisation_affiliation_id` | `secm.organisation`, `secm.person` |
| `secm.preference_share_redemption_period` | 8 | `preference_share_redemption_period_id` | `secm.preference_share_terms` |
| `secm.preference_share_terminal_branch` | 9 | `preference_share_terminal_branch_id` | `secm.preference_share_terms` |
| `secm.preference_share_terms` | 9 | `preference_share_terms_id` | `ing.source_payload`, `secm.instrument`, `secm.organisation`, `secm.structured_product_terms`, `ten.tenant` |
| `secm.reference_constituent_snapshot` | 6 | `reference_constituent_snapshot_id` | `ing.source_payload`, `secm.financial_reference_node` |
| `secm.reference_constituent_snapshot_item` | 8 | `reference_constituent_snapshot_item_id` | `secm.currency`, `secm.financial_reference_node`, `secm.reference_constituent_snapshot` |
| `secm.reference_data_approval` | 9 | `reference_data_approval_id` | `secm.reference_data_automation_policy`, `secm.reference_data_proposal`, `secm.user_account` |
| `secm.reference_data_automation_policy` | 18 | `reference_data_automation_policy_id` | `ing.integration_source_system`, `secm.user_account`, `ten.tenant` |
| `secm.reference_data_proposal` | 15 | `reference_data_proposal_id` | `ing.integration_source_system`, `ing.source_payload`, `secm.financial_reference_node`, `secm.reference_data_automation_policy`, `ten.tenant` |
| `secm.reference_node_regulatory_label_assignment` | 7 | `reference_node_regulatory_label_assignment_id` | `ing.source_payload`, `secm.financial_reference_node`, `secm.regulatory_label` |
| `secm.reference_node_type` | 8 | `reference_node_type_id` | None |
| `secm.regulatory_label` | 6 | `regulatory_label_id` | None |
| `secm.return_profile` | 11 | `return_profile_id` | None |
| `secm.schedule` | 6 | `schedule_id` | `cal.market_calendar`, `ing.source_payload`, `secm.financial_reference_node` |
| `secm.schedule_event` | 7 | `schedule_event_id` | `secm.schedule` |
| `secm.structured_product_component_terms` | 12 | `structured_product_component_terms_id` | `ing.source_payload`, `secm.currency`, `secm.instrument_composition`, `secm.schedule` |
| `secm.structured_product_condition_group` | 11 | `condition_group_id` | `ing.source_payload`, `secm.schedule_event`, `secm.structured_product_terms` |
| `secm.structured_product_coupon_period` | 11 | `coupon_period_id` | `ing.source_payload`, `secm.schedule_event`, `secm.structured_product_condition_group`, `secm.structured_product_coupon_programme` |
| `secm.structured_product_coupon_programme` | 13 | `coupon_programme_id` | `ing.source_payload`, `secm.currency`, `secm.schedule`, `secm.structured_product_condition_group`, `secm.structured_product_terms` |
| `secm.structured_product_initial_fixing` | 14 | `structured_product_initial_fixing_id` | `ing.integration_source_system`, `ing.source_payload`, `md.market_data_observation`, `md.market_data_resolution_snapshot`, `secm.financial_reference_node`, `secm.structured_product_initial_fixing`, `secm.structured_product_terms` |
| `secm.structured_product_range_accrual_terms` | 11 | `range_accrual_terms_id` | `ing.source_payload`, `secm.schedule`, `secm.structured_product_terms` |
| `secm.structured_product_supertracker_terms` | 7 | `supertracker_terms_id` | `ing.source_payload`, `secm.structured_product_terms` |
| `secm.structured_product_terms` | 14 | `structured_product_terms_id` | `ing.source_payload`, `secm.currency`, `secm.instrument`, `secm.structured_product_terms` |
| `secm.structured_product_wrapper_terms` | 8 | `wrapper_terms_id` | `ing.source_payload`, `secm.instrument`, `secm.structured_product_terms` |
| `secm.swap_definition_version` | 3 | `instrument_definition_version_id` | `secm.instrument_definition_version` |
| `secm.swap_leg` | 10 | `swap_leg_id` | `secm.currency`, `secm.financial_reference_node`, `secm.return_profile`, `secm.schedule`, `secm.swap_terms` |
| `secm.swap_terms` | 2 | `instrument_node_id` | `secm.instrument` |
| `secm.taxonomy` | 6 | `taxonomy_id` | None |
| `secm.taxonomy_value` | 8 | `taxonomy_value_id` | `secm.taxonomy`, `secm.taxonomy_value` |
| `secm.user_account` | 5 | `user_account_id` | `secm.person` |

### ten

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `ten.access_audit_event` | 7 | `event_id` | `secm.user_account`, `ten.tenant` |
| `ten.access_group` | 9 | `group_id` | `ten.tenant` |
| `ten.access_group_grant` | 3 | `tenant_id`, `group_id`, `action_code` | `ten.access_group` |
| `ten.access_group_member` | 3 | `tenant_id`, `group_id`, `user_account_id` | `secm.user_account`, `ten.access_group` |
| `ten.access_group_strategy` | 3 | `tenant_id`, `group_id`, `strategy_id` | `ten.access_group`, `trd.strategy` |
| `ten.canonical_reference_link` | 12 | `canonical_reference_link_id` | None |
| `ten.local_access_session` | 8 | `session_id` | `secm.user_account`, `ten.tenant` |
| `ten.operating_profile` | 7 | `operating_profile_id` | None |
| `ten.operating_profile_module_recommendation` | 7 | `operating_profile_module_recommendation_id` | `ten.operating_profile`, `ten.platform_module` |
| `ten.platform_module` | 8 | `platform_module_id` | None |
| `ten.platform_user_account` | 7 | `platform_user_account_id` | `secm.user_account` |
| `ten.reference_node_scope` | 7 | `reference_node_scope_id` | `secm.financial_reference_node`, `ten.tenant` |
| `ten.tenant` | 9 | `tenant_id` | `secm.organisation` |
| `ten.tenant_database_registry` | 10 | `tenant_database_registry_id` | `ten.tenant` |
| `ten.tenant_dataset_coverage` | 3 | `tenant_dataset_entitlement_id`, `coverage_package_id` | `md.dataset_coverage_package`, `ten.tenant_dataset_entitlement` |
| `ten.tenant_dataset_entitlement` | 9 | `tenant_dataset_entitlement_id` | `md.dataset`, `md.dataset_licence_assignment`, `ten.tenant` |
| `ten.tenant_module_entitlement` | 12 | `tenant_module_entitlement_id` | `secm.user_account`, `ten.platform_module`, `ten.tenant`, `ten.tenant_module_entitlement` |
| `ten.tenant_operating_profile_assignment` | 11 | `tenant_operating_profile_assignment_id` | `secm.user_account`, `ten.operating_profile`, `ten.tenant`, `ten.tenant_operating_profile_assignment` |
| `ten.tenant_user_account` | 8 | `tenant_user_account_id` | `secm.user_account`, `ten.tenant` |
| `ten.valuation_policy` | 15 | `valuation_policy_id` | `md.valuation_cut`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `ten.valuation_policy_rule` | 26 | `valuation_policy_rule_id` | `cal.market_calendar`, `md.dataset`, `md.market_data_series`, `md.valuation_cut`, `secm.financial_reference_node`, `secm.instrument_type`, `secm.market_venue`, `ten.valuation_policy` |

### trd

| Table | Columns | Primary key | Referenced tables |
| --- | ---: | --- | --- |
| `trd.bond_coupon_payment` | 19 | `payment_id` | `secm.bond_cashflow`, `secm.currency`, `secm.user_account`, `ten.tenant`, `trd.bond_coupon_payment`, `trd.cash_account`, `trd.strategy` |
| `trd.bond_redemption_policy` | 8 | `tenant_id`, `strategy_id`, `revision` | `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `trd.bond_redemption_posting` | 11 | `posting_id` | `secm.user_account`, `ten.tenant`, `trd.bond_redemption_proposal`, `trd.strategy` |
| `trd.bond_redemption_proposal` | 11 | `proposal_id` | `secm.instrument`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `trd.cash_account` | 8 | `cash_account_id` | `secm.organisation`, `trd.strategy` |
| `trd.cash_balance` | 19 | `cash_balance_id` | `secm.currency`, `secm.user_account`, `trd.cash_account`, `trd.cash_balance`, `trd.strategy` |
| `trd.file_import_job` | 13 | `job_id` | `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `trd.file_import_trade_identity` | 7 | `tenant_id`, `strategy_id`, `source`, `source_trade_id` | `ten.tenant`, `trd.file_import_job`, `trd.strategy`, `trd.trade` |
| `trd.fx_maturity_policy` | 10 | `tenant_id`, `strategy_id`, `revision` | `md.valuation_cut`, `secm.user_account`, `ten.tenant`, `ten.valuation_policy`, `trd.strategy` |
| `trd.fx_maturity_posting` | 11 | `posting_id` | `secm.user_account`, `ten.tenant`, `trd.fx_maturity_proposal`, `trd.strategy` |
| `trd.fx_maturity_proposal` | 11 | `proposal_id` | `secm.instrument`, `secm.user_account`, `ten.tenant`, `trd.strategy` |
| `trd.position_snapshot` | 9 | `position_snapshot_id` | `ing.source_payload`, `ten.tenant`, `trd.strategy` |
| `trd.position_snapshot_line` | 10 | `position_snapshot_line_id` | `ing.external_object_mapping`, `secm.currency`, `secm.financial_reference_node`, `trd.position_snapshot` |
| `trd.reference_catalogue` | 10 | `catalogue_id` | `secm.user_account`, `ten.tenant` |
| `trd.reference_catalogue_record` | 12 | `record_version_id` | `secm.user_account`, `trd.reference_catalogue` |
| `trd.strategy` | 13 | `strategy_id` | `secm.currency`, `secm.organisation`, `secm.user_account`, `ten.tenant` |
| `trd.tenant_organisation_profile` | 8 | `tenant_id`, `organisation_id` | `secm.organisation`, `secm.user_account`, `ten.tenant` |
| `trd.trade` | 31 | `trade_id` | `secm.currency`, `secm.financial_reference_node`, `secm.instrument`, `secm.market_venue`, `secm.person`, `secm.user_account`, `trd.strategy` |
| `trd.trade_booking_idempotency` | 7 | `trade_booking_idempotency_id` | `ten.tenant`, `trd.trade` |
| `trd.trade_configuration_event` | 8 | `event_id` | `secm.user_account`, `ten.tenant` |
| `trd.trade_external_reference` | 7 | `trade_external_reference_id` | `trd.trade`, `trd.trade_party_role` |
| `trd.trade_fee` | 15 | `trade_fee_id` | `fee.fee_rule`, `secm.currency`, `secm.organisation`, `trd.trade` |
| `trd.trade_lifecycle_event` | 12 | `trade_lifecycle_event_id` | `secm.user_account`, `trd.trade`, `trd.trade_lifecycle_event` |
| `trd.trade_party_role` | 5 | `trade_party_role_id` | `secm.organisation`, `secm.person`, `trd.trade` |
| `trd.trade_property_definition` | 16 | `definition_id` | `secm.user_account`, `ten.tenant`, `trd.reference_catalogue` |
| `trd.trade_property_reference` | 4 | `trade_id`, `definition_id` | `ten.tenant`, `trd.reference_catalogue_record`, `trd.trade`, `trd.trade_property_definition` |
| `trd.trade_property_value` | 4 | `trade_id`, `definition_id` | `ten.tenant`, `trd.trade`, `trd.trade_property_definition` |
| `trd.trade_selection_member` | 5 | `member_id` | `secm.organisation`, `secm.person`, `trd.trade_selection_policy` |
| `trd.trade_selection_policy` | 5 | `tenant_id`, `role` | `secm.user_account`, `ten.tenant` |
| `trd.trade_tag` | 9 | `tag_id` | `secm.user_account`, `ten.tenant` |
| `trd.trade_tag_assignment` | 3 | `trade_id`, `tag_id` | `ten.tenant`, `trd.trade`, `trd.trade_tag` |

## Static Python dependencies

Counts are distinct source files in one package family importing the target family. Includes conditional/deferred imports. Schema-registration imports are identified separately. Auxiliary scripts/tooling are not normal request-path dependencies.

| Importing package family | Imported family | Kind | Source files | Examples |
| --- | --- | --- | ---: | --- |
| API | File intake | static_import | 2 | [apps/reference_api/import_routes.py](../../../apps/reference_api/import_routes.py), [apps/reference_api/import_service.py](../../../apps/reference_api/import_service.py) |
| API | Foundation | static_import | 57 | [apps/reference_api/access_boundary.py](../../../apps/reference_api/access_boundary.py), [apps/reference_api/access_routes.py](../../../apps/reference_api/access_routes.py) |
| API | Lifecycle | static_import | 3 | [apps/reference_api/bond_redemption_routes.py](../../../apps/reference_api/bond_redemption_routes.py), [apps/reference_api/coupon_routes.py](../../../apps/reference_api/coupon_routes.py) |
| API | Market data | static_import | 10 | [apps/reference_api/calendar_service.py](../../../apps/reference_api/calendar_service.py), [apps/reference_api/main.py](../../../apps/reference_api/main.py) |
| API | Positions | static_import | 1 | [apps/reference_api/strategy_workspace.py](../../../apps/reference_api/strategy_workspace.py) |
| API | Reporting | static_import | 1 | [apps/reference_api/regulatory_routes.py](../../../apps/reference_api/regulatory_routes.py) |
| API | Valuation | static_import | 13 | [apps/reference_api/access_boundary.py](../../../apps/reference_api/access_boundary.py), [apps/reference_api/access_routes.py](../../../apps/reference_api/access_routes.py) |
| File intake | Foundation | static_import | 1 | [data_imports/tables.py](../../../data_imports/tables.py) |
| Foundation | Lifecycle | metadata_registration | 1 | [security_master_schema/models.py](../../../security_master_schema/models.py) |
| Foundation | Market data | static_import | 1 | [security_master_schema/market_data_resolver.py](../../../security_master_schema/market_data_resolver.py) |
| Foundation | Reporting | metadata_registration | 1 | [security_master_schema/models.py](../../../security_master_schema/models.py) |
| Foundation | Valuation | metadata_registration | 1 | [security_master_schema/models.py](../../../security_master_schema/models.py) |
| Ingestor | API | static_import | 1 | [apps/market_data_ingestor/yahoo_fx_valuation_setup.py](../../../apps/market_data_ingestor/yahoo_fx_valuation_setup.py) |
| Ingestor | Foundation | static_import | 7 | [apps/market_data_ingestor/index_trading_history.py](../../../apps/market_data_ingestor/index_trading_history.py), [apps/market_data_ingestor/yahoo.py](../../../apps/market_data_ingestor/yahoo.py) |
| Ingestor | Market data | static_import | 7 | [apps/market_data_ingestor/index_trading_history.py](../../../apps/market_data_ingestor/index_trading_history.py), [apps/market_data_ingestor/yahoo.py](../../../apps/market_data_ingestor/yahoo.py) |
| Lifecycle | API | static_import | 1 | [lifecycle/bond_service.py](../../../lifecycle/bond_service.py) |
| Lifecycle | Foundation | static_import | 3 | [lifecycle/bond_service.py](../../../lifecycle/bond_service.py), [lifecycle/coupon_service.py](../../../lifecycle/coupon_service.py) |
| Lifecycle | Market data | static_import | 1 | [lifecycle/coupon_service.py](../../../lifecycle/coupon_service.py) |
| Lifecycle | Positions | static_import | 1 | [lifecycle/bond_service.py](../../../lifecycle/bond_service.py) |
| Lifecycle | Valuation | static_import | 5 | [lifecycle/bond_redemption.py](../../../lifecycle/bond_redemption.py), [lifecycle/bond_service.py](../../../lifecycle/bond_service.py) |
| Market data | Foundation | static_import | 23 | [market_data/bond_quote_store.py](../../../market_data/bond_quote_store.py), [market_data/calendar_decisions.py](../../../market_data/calendar_decisions.py) |
| Market data | Positions | static_import | 1 | [market_data/split_replay.py](../../../market_data/split_replay.py) |
| Market data | Valuation | static_import | 4 | [market_data/bond_quote_store.py](../../../market_data/bond_quote_store.py), [market_data/price_basis_store.py](../../../market_data/price_basis_store.py) |
| Operators | API | static_import | 15 | [scripts/export_openapi_contract.py](../../../scripts/export_openapi_contract.py), [scripts/prepare_fx_signoff_fixture.py](../../../scripts/prepare_fx_signoff_fixture.py) |
| Operators | Foundation | static_import | 18 | [scripts/import_reference_calendar.py](../../../scripts/import_reference_calendar.py), [scripts/load_demo_scenarios.py](../../../scripts/load_demo_scenarios.py) |
| Operators | Ingestor | static_import | 9 | [scripts/enable_yahoo_personal_valuation.py](../../../scripts/enable_yahoo_personal_valuation.py), [scripts/import_reference_calendar.py](../../../scripts/import_reference_calendar.py) |
| Operators | Market data | static_import | 9 | [scripts/enable_yahoo_personal_valuation.py](../../../scripts/enable_yahoo_personal_valuation.py), [scripts/import_reference_calendar.py](../../../scripts/import_reference_calendar.py) |
| Operators | Valuation | static_import | 4 | [scripts/prepare_mock_swap_measures.py](../../../scripts/prepare_mock_swap_measures.py), [scripts/prepare_yahoo_fx_valuation.py](../../../scripts/prepare_yahoo_fx_valuation.py) |
| Optional tooling | API | static_import | 9 | [tooling/reconciliation_csv/reconciliation_bond_postings.py](../../../tooling/reconciliation_csv/reconciliation_bond_postings.py), [tooling/reconciliation_csv/reconciliation_bonds.py](../../../tooling/reconciliation_csv/reconciliation_bonds.py) |
| Optional tooling | Foundation | static_import | 14 | [tooling/reconciliation_csv/prepare_reconciliation_valuation.py](../../../tooling/reconciliation_csv/prepare_reconciliation_valuation.py), [tooling/reconciliation_csv/reconciliation_accruals.py](../../../tooling/reconciliation_csv/reconciliation_accruals.py) |
| Optional tooling | Market data | static_import | 3 | [tooling/reconciliation_csv/reconciliation_eligibility.py](../../../tooling/reconciliation_csv/reconciliation_eligibility.py), [tooling/reconciliation_csv/reconciliation_fx.py](../../../tooling/reconciliation_csv/reconciliation_fx.py) |
| Optional tooling | Positions | static_import | 1 | [tooling/reconciliation_csv/reconciliation_eligibility.py](../../../tooling/reconciliation_csv/reconciliation_eligibility.py) |
| Optional tooling | Valuation | static_import | 3 | [tooling/reconciliation_csv/reconciliation_accruals.py](../../../tooling/reconciliation_csv/reconciliation_accruals.py), [tooling/reconciliation_csv/reconciliation_cash.py](../../../tooling/reconciliation_csv/reconciliation_cash.py) |
| Positions | Foundation | static_import | 8 | [positions/contracts.py](../../../positions/contracts.py), [positions/future.py](../../../positions/future.py) |
| Positions | Valuation | static_import | 2 | [positions/fx_forward.py](../../../positions/fx_forward.py), [positions/repository.py](../../../positions/repository.py) |
| Reporting | Foundation | static_import | 2 | [regulatory_reporting/service.py](../../../regulatory_reporting/service.py), [regulatory_reporting/source.py](../../../regulatory_reporting/source.py) |
| Valuation | API | static_import | 2 | [valuation/accruals.py](../../../valuation/accruals.py), [valuation/amendments.py](../../../valuation/amendments.py) |
| Valuation | Foundation | static_import | 27 | [valuation/accruals.py](../../../valuation/accruals.py), [valuation/accrued_balance_inputs.py](../../../valuation/accrued_balance_inputs.py) |
| Valuation | Lifecycle | static_import | 2 | [valuation/accrued_balance_health.py](../../../valuation/accrued_balance_health.py), [valuation/accrued_balance_inputs.py](../../../valuation/accrued_balance_inputs.py) |
| Valuation | Market data | static_import | 9 | [valuation/bond_prices.py](../../../valuation/bond_prices.py), [valuation/cash_snapshots.py](../../../valuation/cash_snapshots.py) |
| Valuation | Positions | static_import | 10 | [valuation/accruals.py](../../../valuation/accruals.py), [valuation/accrued_balance_inputs.py](../../../valuation/accrued_balance_inputs.py) |

## Source size by package family

Physical lines include comments/blank lines. The shared TypeScript package total includes generated API types, and is not comparable to hand-maintained code volume.

| Group | Files | Physical lines |
| --- | ---: | ---: |
| API | 80 | 16,983 |
| Console | 353 | 18,247 |
| File intake | 3 | 176 |
| Foundation | 57 | 9,803 |
| Ingestor | 9 | 935 |
| Lifecycle | 8 | 737 |
| Market data | 36 | 3,178 |
| Operators | 30 | 2,019 |
| Optional tooling | 18 | 2,364 |
| Positions | 13 | 1,006 |
| Reporting | 6 | 464 |
| Shared TS packages | 4 | 30,805 |
| Valuation | 45 | 4,654 |

## Catalogue verification

- Deployed revision: `20261029_104`.
- Application table sets: identical after late registration of the two file-intake tables.
- FK source/target multiplicities: identical.
- Column-count differences: 0.
- Non-internal triggers: 81.
- Application views/materialized views: 0.
- Tables with enabled PostgreSQL row-level security: 0.

These checks do not compare every column type, check expression, default, index definition, trigger body or actual access predicate. Those need their own schema/security review.
