# Feature implementation and test map

5 November F24/F51: [worklist delivery](../delivery/lifecycle-worklist-20261105.md), [domain read model](../../lifecycle/worklist.py), [scoped repository](../../lifecycle/worklist_repository.py), [GET adapter](../../apps/reference_api/lifecycle_worklist_routes.py), [UI](../../apps/ops-console/src/features/lifecycle-worklist/), [DB regression](../../tests/test_lifecycle_worklist.py), [scoped API regression](../../tests/test_lifecycle_worklist_api.py) and [browser/filter/handoff checks](../../apps/ops-console/browser-tests/lifecycle-worklist.spec.ts). [Search and workspace UI follow-up](../delivery/lifecycle-booking-ui-20261105.md) covers server-side instrument filtering, responsive booking cards and refreshed mode/action decisions. Only bond maturity detection is delivered; native posting authority is unchanged.

5 November F51: [delivered scope and evidence](../delivery/lifecycle-assistance-entitlements-20261105.md), [typed schema](../../security_master_schema/lifecycle_entitlement_tables.py), [commercial ceiling](../../lifecycle/entitlements.py), [scoped decisions](../../lifecycle/assistance.py), [reviewed transitions](../../lifecycle/assistance_transitions.py), [HTTP adapter](../../apps/reference_api/lifecycle_assistance_routes.py), [UI controls](../../apps/ops-console/src/features/lifecycle-assistance/), [native enforcement tests](../../tests/test_lifecycle_subscription_enforcement.py), [scope/API tests](../../tests/test_lifecycle_assistance_api.py), [commit-race test](../../tests/test_lifecycle_subscription_races.py) and [browser acceptance](../../apps/ops-console/browser-tests/lifecycle-assistance.spec.ts). General notifications and billing are not delivered.

4 November F20/F24/F51: implemented [tenant reference data and strategy trade profiles](../delivery/tenant-reference-data-trade-profiles-20261104.md). Shared tenant sources and field meanings are separate from immutable profile rules and explicit strategy assignments. All supported booking/import/correction and bond/FX maturity consumers resolve the pinned profile; publication does not adopt a version. See delivery for verification, cutover and remaining limits.

3 November F37 [expanded measure delivery](../delivery/expanded-position-measures-20261103.md):
[original booking validation](../../valuation/measure_contracts.py),
[exact formulas](../../valuation/position_measures.py),
[governed selection/conversion](../../valuation/measure_inputs.py),
[assessed note-stock adapter](../../valuation/note_measure_balances.py),
[holdings unit recovery](../../positions/holdings_repository.py),
[report](../../apps/ops-console/src/components/position-measures-report.tsx),
[inspection](../../apps/ops-console/src/components/strategy-measure-details.tsx),
[native product regressions](../../tests/test_expanded_measure_inputs.py) and
[source-proof unit checks](../../tests/test_note_measure_balances.py).
Unmodelled risk exposure stays explicit; this adds no measure publication or NAV weights.

3 November: [Instrument consistency cleanup](../delivery/instrument-consistency-20261103.md)
removes seed-specific equity creation choices, adds scoped non-ledger source
reassessment and aligns CLEAN bond monetary previews with maintained accrued
stocks. Existing product support/status boundaries remain; source changes create
review work, not rewritten published numbers.

Current seams: [creation catalogue](../../security_master_schema/creation_options.py),
[authorized HTTP adapter](../../apps/reference_api/reference_creation_routes.py),
[creation tests](../../tests/test_reference_creation_options.py),
[source dependency tracker](../../valuation/source_dependencies.py),
[source-change regressions](../../tests/test_valuation_source_dependencies.py),
[maintained bond-stock adapter](../../valuation/bond_measure_balances.py) and
[bond measure regressions](../../tests/test_bond_measure_balances.py).

3 November F38/F39 trade annotations:
[ledger service](../../valuation/balance_trade_events.py),
[HTTP adapter](../../apps/reference_api/balance_history_routes.py),
[timeline](../../apps/ops-console/src/features/valuation/balance-trade-timeline.tsx),
[backend scope/recognition tests](../../tests/test_balance_trade_events.py),
[frontend grouping/contract tests](../../apps/ops-console/src/features/valuation/balance-trade-timeline.test.tsx)
and [delivery/limits](../delivery/balance-trade-markers-20261103.md).
Trade disclosure has its own action checks; it is not implied by valuation access.

F38 external-data follow-up: [3 November accrual refresh and deferred fund scope](../delivery/daily-accrual-csv-refresh-20261103.md)
uses the existing [isolated aggregator/poster](../../tooling/reconciliation_csv/reconciliation_accruals.py)
and [native daily writer](../../valuation/accruals.py), verified by
[posting/replay tests](../../tooling/reconciliation_csv/tests/test_reconciliation_accruals.py).
No application import interface changed; fund share-class accrual support remains
unimplemented pending semantic investigation.

3 November F38/F39 exploration:
[route](../../apps/ops-console/src/app/valuation/interest/explorer/page.tsx),
[filters/report](../../apps/ops-console/src/features/valuation/balance-explorer.tsx),
[scope-response checks](../../apps/ops-console/src/features/valuation/balance-explorer-model.ts),
[UI regression](../../apps/ops-console/src/features/valuation/balance-explorer.test.tsx),
[contract regression](../../apps/ops-console/src/features/valuation/balance-explorer-model.test.ts),
[reused API access test](../../tests/test_balance_series_api.py) and
[delivery/limits](../delivery/accrued-balance-explorer-20261103.md).

3 November F38/F39 current entry points:
[review service](../../valuation/interest_review.py),
[typed review schema](../../valuation/interest_review_tables.py),
[comparison model](../../valuation/interest_review_model.py),
[HTTP adapter](../../apps/reference_api/interest_review_routes.py),
[two-stage UI](../../apps/ops-console/src/features/valuation/interest-ops-review.tsx),
[API permissions](../../tests/test_interest_review_api.py),
[transactions/gaps/staleness](../../tests/test_interest_review_integration.py),
[loaded UI regression](../../apps/ops-console/src/features/valuation/interest-ops-review-loaded.test.tsx)
and [delivery/limits](../delivery/interest-daily-review-20261103.md).
The older workspace references below are historical foundations, not the current
main-page navigation.

1 November F38/F39 Ops maintenance:
[workspace](../../apps/ops-console/src/features/valuation/interest-register.tsx),
[source editors](../../apps/ops-console/src/features/valuation/interest-input-editor.tsx),
[exact payloads](../../apps/ops-console/src/features/valuation/interest-model.ts),
[independent scoped loading](../../apps/ops-console/src/features/valuation/use-interest-data.ts),
[retained transport](../../apps/ops-console/src/features/valuation/interest-api.ts),
[filtered history API](../../apps/reference_api/balance_history_routes.py),
[loading regressions](../../apps/ops-console/src/features/valuation/use-interest-data.test.ts),
[To-date overview/range separation](../../apps/ops-console/src/features/valuation/interest-register-snapshot.test.tsx),
[editor/pagination regressions](../../apps/ops-console/src/features/valuation/interest-input-editor.test.tsx),
[native maintenance loop](../../tests/test_balance_history_api.py) and
[delivery/limits](../delivery/interest-ops-workspace-20261101.md).

1 November F38/F39 chart:
[series GET](../../apps/reference_api/balance_history_routes.py),
[viewer/table](../../apps/ops-console/src/features/valuation/balance-history-chart.tsx),
[geometry](../../apps/ops-console/src/features/valuation/balance-chart-model.ts),
[API/scope regression](../../tests/test_balance_series_api.py),
[model tests](../../apps/ops-console/src/features/valuation/balance-chart-model.test.ts),
[rendering tests](../../apps/ops-console/src/features/valuation/balance-history-chart.test.tsx)
and [delivery](../delivery/accrued-balance-chart-20261101.md).

31 October F38/F39 maintained accrued balances:
[contracts](../../valuation/balance_history_contracts.py),
[schema](../../valuation/balance_history_tables.py),
[commands/reads](../../valuation/balance_history.py),
[local/FX adapters](../../valuation/accrued_balance_inputs.py),
[API](../../apps/reference_api/balance_history_routes.py),
[workbench](../../apps/ops-console/src/features/valuation/interest-register.tsx),
[migration 108](../../alembic/versions/20261031_108_maintained_accrued_balances.py),
[financial/history tests](../../tests/test_balance_history_integration.py),
[API scope tests](../../tests/test_balance_history_api.py) and
[frontend tests](../../apps/ops-console/src/features/valuation/interest-register.test.tsx).
See [delivery and limits](../delivery/maintained-accrued-balances-20261031.md).

31 October F32/F37 [NAV convention correction](../delivery/fund-nav-lag-20261031.md):
[optional configuration](../../tooling/reconciliation_csv/reconciliation_eligibility.py)
and [lightweight boundary tests](../../tooling/reconciliation_csv/tests/test_fund_nav_convention.py)
reuse existing NAV_DATE/FIXED_LAG selection. FCPGF policy v3 uses prior-session NAVs
and independent current-day FX; no calculator or production API behavior changed.


31 October F32/F37/F39 [delivery and limits](../delivery/incomplete-price-review-20261031.md):
[missing-input population proof](../../valuation/price_inputs.py),
[reviewed marks](../../valuation/mark_overrides.py),
[decision health](../../valuation/mark_health.py),
[migration 107](../../alembic/versions/20261031_107_reviewed_mark_overrides.py),
[HTTP](../../apps/reference_api/mark_override_routes.py),
[review UI](../../apps/ops-console/src/features/valuation/mark-override-review.tsx),
[partial staging tests](../../tests/test_partial_price_staging.py),
[manual-mark tests](../../tests/test_reviewed_mark_overrides.py),
[cash FX tests](../../tests/test_partial_cash_prices.py) and
[browser checks](../../apps/ops-console/browser-tests/missing-marks.spec.ts).
Missing required marks block normal/self publication; optional interest/cash
snapshots keep their separate nonblocking treatment. No source-value invention.


30 October F27/F48: [strict rights](../../market_data/rights.py),
[uniform display purpose](../../market_data/display_access.py),
[explicit seed governance](../../security_master_schema/synthetic_market_data.py),
[migration 106](../../alembic/versions/20261030_106_explicit_synthetic_rights.py),
[admission](../../apps/reference_api/workload_admission.py) and
[safe retry metadata](../../apps/ops-console/src/lib/server/workload-response.ts).
[Missing-profile checks](../../tests/test_missing_dataset_profiles.py),
[cross-worker/cancellation checks](../../tests/test_workload_concurrency.py),
[no-effect busy checks](../../tests/test_workload_api.py) and
[numerical acceptance](../../tests/test_valuation_acceptance.py) support
[delivery evidence and explicit remaining scope](../delivery/dataset-rights-and-workload-20261030.md).

30 October F48: [runtime-role boundary](../../security_master_schema/database_security.py),
[local provisioner](../../scripts/configure_local_database.py),
[audit migration 105](../../alembic/versions/20261030_105_access_audit_immutability.py),
[safe security events](../../apps/reference_api/security_events.py),
[browser policy](../../apps/ops-console/src/lib/security-headers.ts) and
[cookie options](../../apps/ops-console/src/lib/server/session-cookie.ts).
[Role/booking regression](../../tests/test_runtime_database_role.py),
[audit regression](../../tests/test_access_audit_protection.py),
[configuration/log regressions](../../tests/test_security_controls.py) and
[browser acceptance](../../apps/ops-console/browser-tests/context-guard.spec.ts)
support the [bounded delivery claims](../delivery/security-controls-20261030.md).

30 October F03/F48: [local identity verifier](../../apps/reference_api/local_identity.py),
[boundary](../../apps/reference_api/access_boundary.py), [startup settings](../../apps/reference_api/config.py),
[BFF](../../apps/ops-console/src/lib/server/local-identity.ts) and
[session-only context](../../apps/ops-console/src/lib/tenant-session.ts).
[Offline regressions](../../tests/test_local_identity_safeguard.py) and
[real session tests](../../tests/test_local_identity_sessions.py) distinguish
local containment from deferred production login. [Evidence](../delivery/local-identity-safeguard-20261030.md).

30 October F48: [dependency audit workflow](../../.github/workflows/dependency-security.yml)
checks the complete pnpm/Python locks on PR/main/manual/weekly triggers. Targeted
upgrades, generated-contract parity and compatibility results are recorded in
[delivery evidence](../delivery/dependency-security-20261030.md); remote scheduled
execution and production certification are separate claims.

29 October F53: [preparation delivery](../delivery/regulatory-reporting-20261029.md)
adds the dedicated Regulatory Reporting module and bounded preparation/review/
export path. Regulatory submission/schema acceptance remains unimplemented;
the [working-reference review](../research/transaction-reporting-reference-20261029.md)
is design evidence, not proof of regulatory acceptance.

29 October F38/F39 [review/display follow-up](../delivery/valuation-review-signals-20261029.md):
[coverage classification](../../valuation/review_coverage.py),
[stock projection](../../valuation/accrued_balance_presentation.py),
[API decoration](../../apps/reference_api/valuation_presentation.py),
[compact disclosure](../../apps/ops-console/src/features/valuation/coverage-review.tsx),
[numerical/availability tests](../../tests/test_valuation_review_signals.py),
[native stock evidence](../../tests/test_accrued_balance_integration.py) and
[keyboard/mobile acceptance](../../apps/ops-console/browser-tests/valuation-review-signals.spec.ts).

28 October F17/F27/F37–F39 [bond quote normalization](../delivery/bond-dirty-to-clean-20261028.md):
[typed quote math](../../market_data/bond_quotes.py),
[source-paired writer](../../market_data/bond_quote_store.py),
[ingestion/corrections](../../market_data/storage.py),
[normalizer](../../valuation/bond_prices.py),
[publication check](../../valuation/bond_quote_review.py),
[migration 103](../../alembic/versions/20261028_103_bond_quote_accrual.py),
[inspector](../../apps/ops-console/src/features/valuation/bond-price-normalization.tsx),
[native P&L tests](../../tests/test_bond_dirty_market_integration.py),
[ingestion tests](../../tests/test_bond_quote_ingestion.py) and
[browser check](../../apps/ops-console/browser-tests/bond-dirty-price.spec.ts).

28 October F16/F37/F39 [linear futures extension](../delivery/linear-futures-extension-20261028.md):
[capability](../../security_master_schema/future_economics.py),
[booking/reference locks](../../apps/reference_api/product_booking.py),
[frozen facts](../../security_master_schema/future_valuation.py),
[variation/dimensions](../../valuation/futures_pnl.py),
[numerical and lock-order tests](../../tests/test_linear_future_economics.py),
[native booking](../../tests/test_linear_futures_api.py),
[governed financial integration](../../tests/test_linear_futures_pnl_integration.py),
[browser editor/inspection](../../apps/ops-console/browser-tests/linear-futures.spec.ts).
No delivery/accounting engine is implied. Crypto monetary-preview coverage is separately implemented in the 3 November measure extension above.

28 October F12/F36–F39 [ETP/spot-crypto P&L](../delivery/etp-spot-crypto-pnl-20261028.md):
[shared classification](../../security_master_schema/cash_products.py),
[native cash writer checks](../../trading/cash_reference.py),
[financial adapter](../../positions/repository.py),
[quantity-only adapter](../../positions/holdings_repository.py),
[numerical tests](../../tests/test_cash_product_pnl.py),
[native financial/review tests](../../tests/test_cash_product_pnl_integration.py)
and [browser inspection](../../apps/ops-console/browser-tests/cash-product-pnl.spec.ts).
These reuse security price/FX economics; no underlying payoff or token lifecycle
model or automatic provider rights is implied. Crypto monetary previews are separately implemented in the 3 November extension above.

28 October F15/F37/F38/F39 [supplied whole-note P&L](../delivery/structured-note-pnl-20261028.md):
[quotation/frozen evidence](../../security_master_schema/structured_note_valuation.py),
[historical binding](../../positions/structured_note.py),
[source quotation matching](../../valuation/structured_note_inputs.py),
[optional CLEAN stock FX](../../valuation/structured_note_interest.py),
[bounded migration 102](../../alembic/versions/20261028_102_structured_note_interest.py),
[pure tests](../../tests/test_structured_note_valuation.py),
[real-booking/publication tests](../../tests/test_structured_note_pnl_integration.py)
and [browser inspection](../../apps/ops-console/browser-tests/structured-note-pnl.spec.ts).
Lifecycle, generated detached note receivables and payoff pricing remain deferred.

27 October F16/F37/F39 [futures daily P&L](../delivery/futures-daily-pnl-20261027.md):
[frozen conventions](../../security_master_schema/future_valuation.py),
[historical binding](../../positions/future.py), [bridge](../../valuation/futures_pnl.py),
[real-booking/staging/publication tests](../../tests/test_futures_pnl_integration.py),
[inspector](../../apps/ops-console/src/features/valuation/futures-pnl-inspection.tsx)
and [browser check](../../apps/ops-console/browser-tests/futures-pnl.spec.ts).

27 October F36–F40 [cross-layer review](../delivery/quality-reviews/2026-10-27-valuation-state-review.md)
maps intent to current calculation, review UI, schema and focused evidence; it
does not expand product support or certify operating financial results.

27 October F38/F39 accrued stock:
[replay](../../valuation/accrued_balance.py), [sources](../../valuation/accrued_balance_inputs.py),
[storage](../../valuation/accrued_balance_storage.py), [source health](../../valuation/accrued_balance_health.py),
[migration 101](../../alembic/versions/20261027_101_accrued_balance_fx.py),
[integration regressions](../../tests/test_accrued_balance_integration.py),
[inspector](../../apps/ops-console/src/features/valuation/accrued-balance-inspection.tsx),
[browser acceptance](../../apps/ops-console/browser-tests/accrued-balance.spec.ts).
[Current rules](../architecture/market-data-and-valuation/accrued-balance-fx.md).

27 October F38 [full schedule delivery](../delivery/bond-cashflow-schedule-20261027.md):
[typed contracts](../../lifecycle/coupon_contracts.py), [schema](../../lifecycle/coupon_tables.py),
[service](../../lifecycle/coupon_service.py), [migration 100](../../alembic/versions/20261027_100_bond_cashflow_schedule.py),
[editor/table](../../apps/ops-console/src/components/bond-cashflow-schedule.tsx),
[contract checks](../../tests/test_bond_cashflow_contracts.py),
[service checks](../../tests/test_bond_cashflow_schedule.py),
[retained-receipt migration](../../tests/test_bond_cashflow_migration.py),
[browser acceptance](../../apps/ops-console/browser-tests/bond-cashflow-schedule.spec.ts).
Current [data/workflow reference](../architecture/trading-and-operations/bond-cashflow-schedules.md).

26 October F07/F19/F39 [shared instrument display](../delivery/shared-instrument-display-20261026.md):
[pure rules](../../security_master_schema/instrument_display.py),
[visible bulk resolver](../../apps/reference_api/instrument_display.py),
[shared React label](../../apps/ops-console/src/components/instrument-label.tsx),
[policy tests](../../tests/test_instrument_display.py),
[scope/batching/snapshot tests](../../tests/test_instrument_display_api.py),
[holdings identifier search](../../tests/test_strategy_holdings_api.py),
[render tests](../../apps/ops-console/src/components/instrument-label.test.tsx) and
[browser identities/keyboard/mobile](../../apps/ops-console/browser-tests/instrument-display.spec.ts).
Rules and remaining limits: [maintained policy](../architecture/security-master/instrument-display.md).

26 October F39 [manual position check](../delivery/position-inspection-manual-check-20261026.md):
[frozen-input worksheet](../../apps/ops-console/src/features/valuation/position-calculation.tsx),
[inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[rendering edge cases](../../apps/ops-console/src/features/valuation/position-calculation.test.tsx)
and [browser proof/navigation/layout checks](../../apps/ops-console/browser-tests/pnl-ops.spec.ts).
No calculation/API change; technical evidence stays available under disclosure.
Its [bond-label follow-up](../delivery/position-inspection-manual-check-20261026.md#bond-business-identifiers)
uses [bulk current-ISIN projection](../../apps/reference_api/valuation_presentation.py)
and [disposable metadata/visibility regressions](../../tests/test_valuation_presentation_api.py).

26 October F39 instrument-type column/filter: [accessible type projection](../../apps/reference_api/valuation_presentation.py),
[full-result selection](../../apps/ops-console/src/features/valuation/ops-review-model.ts),
[table/filter](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[metadata/visibility tests](../../tests/test_valuation_presentation_api.py),
[selection tests](../../apps/ops-console/src/features/valuation/ops-review-model.test.ts),
[render tests](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx) and
[isolated browser journeys](../../apps/ops-console/browser-tests/pnl-ops.spec.ts).
See the [report follow-up](../delivery/valuation-report-tabs-20261026.md#instrument-type-column-and-filter-follow-up).

26 October F38 [zero-coupon applicability](../delivery/zero-coupon-accrual-applicability-20261026.md):
[original booked coupon terms](../../positions/repository.py),
[coverage and publication guard](../../valuation/accruals.py),
[calculation wiring](../../valuation/service.py),
[applied rule](../../valuation/decisions.py),
[offline edge cases](../../tests/test_zero_coupon_accruals.py) and
[calculation/staging/publication acceptance](../../tests/test_economic_pnl_acceptance.py).
No master-data guess, invented zero input or historical financial rewrite.

23 October F37/F38 [optional daily accruals](../delivery/optional-bond-accruals-20261023.md):
[coverage/consumer/publication guard](../../valuation/accruals.py),
[strict request](../../apps/reference_api/valuation_contracts.py),
[calculation](../../valuation/service.py),
[results disclosure](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[economic acceptance](../../tests/test_economic_pnl_acceptance.py),
[request/retry checks](../../tests/test_optional_accrual_contract.py).

The external CSV reconciliation exercise is not product capability delivery.
Its source-specific operators, adapters and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md); retained delivery
records describe that exercise, not a supported upload interface.

23 October F14/F37 [supplied option-premium P&L](../delivery/option-premium-pnl-20261023.md):
[frozen premium validation](../../security_master_schema/option_valuation.py),
[original fingerprint adapter](../../positions/option.py), [native writer](../../apps/reference_api/option_booking.py),
[input selection](../../valuation/service.py), [shared bridge](../../valuation/position_calculation.py)
and [applied rules](../../valuation/decisions.py). Verification:
[arithmetic](../../tests/test_option_valuation.py), [frozen evidence](../../tests/test_option_frozen_valuation.py),
[native booking/resolution/staging](../../tests/test_option_valuation_integration.py).
Existing Results/evidence UI presents staged lines; no option pricer, exercise,
expiry posting, new upload family or monetary-measure preview is added.

23 October: [AMC delivery/limits](../delivery/amc-onboarding-20261023.md),
[creation](../../apps/reference_api/amc_creation.py),
[booking](../../apps/reference_api/product_booking.py),
[UI](../../apps/ops-console/src/components/amc-creation-form.tsx),
[booking tests](../../tests/test_amc.py),
[quotation factors](../../security_master_schema/amc_quotation.py),
[measure/daily integration tests](../../tests/test_amc_measures.py). Native certificate onboarding is not full AMC
management; F41 remains incomplete.

October 16 query-efficiency follow-up for F02/F27/F32/F34/F36/F37/F48:
[delivery, source paths, measurements and limits](../delivery/quality-reviews/2026-10-16-query-efficiency.md).
Regression entry point: `tests/test_query_efficiency.py`; existing policy/coverage,
strategy-access, holdings, forward-maturity and history tests remain authoritative.
No capability-status upgrade or operating activation is implied.

**Status:** Maintained traceability reference  
**Last reviewed:** 2026-10-12  
**Code baseline reviewed:** main 76f6292

Use this map with the [desired-feature register](feature-register.md) and its [capability records](features/). Each row identifies a concrete backend implementation surface, frontend route/component, and focused regression-test file where one exists. For foundation-only, deferred or not-implemented capabilities, it points to the existing foundation and states where the desired workflow or its dedicated tests are absent.

Test links identify test files; they do not imply that tests were run in this review or cover every scenario. “No dedicated test located” means no matching focused file was found in the current source inventory. Component/API tests are not browser acceptance. This is a navigation aid, not a certification of correctness.

17 October F08/F09/F11: [shared/private instrument stewardship](features/instrument-management.md#proposed-direction-shared-and-tenant-private-stewardship)
is a recorded proposal, not a newly implemented or verified authority matrix.
Existing source/test mappings and capability classifications remain unchanged.

F05 contract-date follow-up: [frozen-date extraction](../../positions/holdings_repository.py)
and [as-of attention projection](../../apps/reference_api/strategy_workspace.py)
feed the existing workspace table; [quantity/date tests](../../tests/test_strategy_holdings.py),
[frozen-date HTTP regression](../../tests/test_strategy_holdings_api.py) and
[component rendering](../../apps/ops-console/src/components/strategy-workspace.test.tsx)
cover this read-only addition, not a lifecycle dashboard or automated booking.

## Platform and tenant workspace

15 October F38: [coupon delivery/limits](../delivery/bond-coupons-20261015.md), [service](../../lifecycle/coupon_service.py), [migration 94](../../alembic/versions/20261015_94_bond_coupons.py), [API](../../apps/reference_api/coupon_routes.py), [UI](../../apps/ops-console/src/components/bond-coupon-console.tsx), [domain tests](../../tests/test_bond_coupons.py), [API tests](../../tests/test_bond_coupons_api.py). Contract schedules and actual confirmations are separate from daily earnings; migration 94/API active, browser acceptance pending.

14 October F38 typed interest: [delivery](../delivery/typed-daily-interest-20261014.md), [migration 93](../../alembic/versions/20261014_93_typed_daily_interest.py), [schema](../../valuation/tables.py), [request contracts](../../apps/reference_api/valuation_input_contracts.py), [consumer/writer](../../valuation/accruals.py), [input form](../../apps/ops-console/src/features/valuation/input-register.tsx), [core tests](../../tests/test_typed_daily_interest.py), [populated migration tests](../../tests/test_typed_daily_interest_migration.py).

14 October F36–F39 methodology assurance: [reference matrix](../architecture/market-data-and-valuation/valuation-methodology.md), [17 numerical cases](../../tests/test_valuation_methodology_matrix.py), [applied decisions](../../valuation/decisions.py), [service evidence](../../valuation/service.py), [staged identity](../../valuation/position_storage.py), [rule tests](../../tests/test_valuation_decisions.py), [bond calculation/staging regression](../../tests/test_bond_redemption_valuation.py). [Verification and limits](../delivery/valuation-methodology-assurance-20261014.md).

14 October F36/F37/F39 follow-up: [delivery/limits](../delivery/trade-corrections-valuation-reassessment-20261014.md), [reconstruction](../../positions/reconstruction.py), [ledger impact checks](../../valuation/ledger_impacts.py), [recalculation service](../../valuation/reassessment.py), [scoped API](../../apps/reference_api/valuation_reassessment_routes.py), [operational panel](../../apps/ops-console/src/features/valuation/reassessment-panel.tsx), [impact tests](../../tests/test_valuation_ledger_impacts.py), [API tests](../../tests/test_valuation_reassessment_api.py). Migration `20261014_92` adds transactional ledger evidence and is locally applied; API restart/health and route registration verified.

F02/F05 access UX: [presentation labels](../../apps/ops-console/src/lib/access-presentation.ts),
[matrix](../../apps/ops-console/src/components/strategy-access-matrix.tsx),
[filter handler tests](../../apps/ops-console/src/components/strategy-access-filters.test.tsx),
[preview confirmation tests](../../apps/ops-console/src/components/strategy-access-preview.test.tsx).
See [research and workflow record](../delivery/access-management-ux.md).

F02/F05 strategy scopes: [predicate](../../security_master_schema/strategy_access.py),
[preview/matrix](../../security_master_schema/strategy_access_admin.py),
[creation](../../security_master_schema/strategy_creation_access.py),
[transport guard](../../apps/reference_api/strategy_boundary.py),
[migration 85](../../alembic/versions/20261013_85_strategy_access_scopes.py),
[scoped HTTP tests](../../tests/test_strategy_scopes_api.py),
[scope UI](../../apps/ops-console/src/components/strategy-access.test.tsx).
See [delivery evidence/limits](../delivery/strategy-access-scopes.md).

F02 authority separation: [permission resolver](../../security_master_schema/access_control.py),
[one-time bootstrap](../../security_master_schema/access_bootstrap.py),
[migration 84](../../alembic/versions/20261013_84_admin_operational_groups.py),
[HTTP/migration regression tests](../../tests/test_admin_authority_separation.py).
See [delivery and remaining controls](../delivery/admin-operational-authority-separation.md).

F02/F04 current-state access addition (2026-10-13):
[service](../../security_master_schema/access_explanations.py),
[page](../../apps/ops-console/src/app/tenant-profile/effective-access/page.tsx),
[pure tests](../../tests/test_access_explanations.py),
[HTTP isolation tests](../../tests/test_effective_access_api.py),
[UI checks](../../apps/ops-console/src/components/effective-access.test.tsx).
See [scope and remaining work](../delivery/effective-access-transparency.md).

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F01](features/access-and-strategies.md#f01-platform-tenant-administration) | [update_tenant](../../security_master_schema/access_management.py#L28), [set_module](../../security_master_schema/access_management.py#L67); [platform routes](../../apps/reference_api/access_routes.py#L29) | [Platform tenants page](../../apps/ops-console/src/app/platform/tenants/page.tsx) | [test_platform_tenant_update.py](../../tests/test_platform_tenant_update.py); [tenant editor rendering](../../apps/ops-console/src/components/platform-tenant-edit.test.tsx), [editor handlers](../../apps/ops-console/src/components/access-editor-interactions.test.tsx). |
| [F02](features/access-and-strategies.md#f02-users-groups-and-delegated-actions) | [save_group](../../security_master_schema/access_management.py#L106), [add_user](../../security_master_schema/access_management.py#L138), [set_user_groups](../../security_master_schema/access_management.py#L161), [set_user_status](../../security_master_schema/access_management.py#L175); [access API](../../apps/reference_api/access_routes.py#L46) | [Tenant access page](../../apps/ops-console/src/app/tenant-profile/access/page.tsx) | [test_access_management.py](../../tests/test_access_management.py), [test_access_api.py](../../tests/test_access_api.py); [access rendering](../../apps/ops-console/src/components/access-administration.test.tsx), [editor handlers](../../apps/ops-console/src/components/access-editor-interactions.test.tsx), [access UX](../../apps/ops-console/src/components/access-ux.test.tsx). |
| [F03](features/access-and-strategies.md#f03-context-switching) | [start, resolve, revoke, end](../../security_master_schema/access_sessions.py#L17); [local-session routes](../../apps/reference_api/access_routes.py#L97) | [Context selector](../../apps/ops-console/src/app/select-context/page.tsx) | [test_access_session.py](../../tests/test_access_session.py); [context rendering](../../apps/ops-console/src/components/access-administration.test.tsx), [selection/reset handlers](../../apps/ops-console/src/components/access-editor-interactions.test.tsx), [empty-state UX](../../apps/ops-console/src/components/access-ux.test.tsx). |
| [F04](features/access-and-strategies.md#f04-module-entitlements-and-profile) | [resolve_tenant_workspace](../../security_master_schema/tenant_workspace.py#L75); [effective_permissions](../../security_master_schema/access_control.py#L27), [effective_modules](../../security_master_schema/access_control.py#L35) | [Tenant profile](../../apps/ops-console/src/app/tenant-profile/page.tsx); [navigation](../../apps/ops-console/src/lib/navigation.ts) | [test_tenant_module_entitlements.py](../../tests/test_tenant_module_entitlements.py), [test_tenant_workspace.py](../../tests/test_tenant_workspace.py); [profile component](../../apps/ops-console/src/components/tenant-profile-overview.test.tsx). |
| [F05](features/access-and-strategies.md#f05-strategies) | [Strategy CRUD](../../apps/reference_api/repository.py), [workspace API and type/name ordering before pagination](../../apps/reference_api/strategy_workspace.py), [quantity projection](../../positions/holdings.py), [ledger adapter](../../positions/holdings_repository.py) | [Register/create](../../apps/ops-console/src/app/strategies/strategy-console.tsx), [strategy detail](../../apps/ops-console/src/app/strategies/[strategyId]/page.tsx), [compact grouped positions/calendars](../../apps/ops-console/src/components/strategy-workspace.tsx), [quantity chart](../../apps/ops-console/src/components/position-history-chart.tsx) | [Existing strategy API](../../tests/test_strategy_workspace_api.py), [holdings HTTP](../../tests/test_strategy_holdings_api.py), [quantity/group-order tests](../../tests/test_strategy_holdings.py), [workspace UI](../../apps/ops-console/src/components/strategy-workspace.test.tsx), [chart arithmetic](../../tests/test_position_chart.py), [chart UI](../../apps/ops-console/src/components/position-history-chart.test.tsx) |
| [F06](features/access-and-strategies.md#f06-production-identity-and-isolation) | [tenant/action resolution](../../security_master_schema/tenant_workspace.py#L42); [tenant routing](../../security_master_schema/tenant_routing.py#L20); [API boundary](../../apps/reference_api/access_boundary.py#L45) | No production identity or deployed tenant-isolation UI; local context selection is F03. | [test_tenant_routing.py](../../tests/test_tenant_routing.py), [test_access_control.py](../../tests/test_access_control.py); no production identity integration test because that integration is not implemented. |

## Reference data and instrument management

October 16 cross-cutting backend follow-up for F02/F04/F09/F15/F37/F39:
[delivery and verification](../delivery/quality-reviews/2026-10-16-backend-remediation.md),
[strict dependency checks](../../apps/reference_api/structured_product_dependencies.py),
[UTC clock](../../security_master_schema/governance_clock.py),
[transactional audit](../../security_master_schema/command_audit.py),
[scoped queue tests](../../tests/test_backend_queue_scopes.py),
[preview snapshot/current-rights tests](../../tests/test_measure_snapshot_boundary.py),
[typed paged options](../../apps/reference_api/valuation_choices.py),
[paged UI](../../apps/ops-console/src/features/valuation/paged-choice.tsx) and
[measured SQL regression](../../tests/test_resolution_read_performance.py).
The approved shared-model follow-up moves
[ConventionBase/FutureConvention](../../security_master_schema/booking_conventions.py)
and [GenericSwapTerms](../../security_master_schema/swap_terms.py) below HTTP;
[compatibility fingerprints](../../tests/test_shared_financial_contract_parity.py)
and [mandatory import guards](../../tests/test_financial_domain_boundaries.py)
protect the reviewed seams. Architecture extraction is incremental, not a
wholesale service decomposition.

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F07](features/instrument-management.md#f07-catalogue-and-details) | [search_instrument_catalogue](../../apps/reference_api/instrument_catalogue.py#L9); [search_instruments](../../apps/reference_api/repository.py#L951), [get_instrument](../../apps/reference_api/repository.py#L919) | [Instrument catalogue](../../apps/ops-console/src/app/instruments/page.tsx); [instrument detail](../../apps/ops-console/src/app/instruments/%5BinstrumentId%5D/page.tsx) | [test_instrument_catalogue_summary.py](../../tests/test_instrument_catalogue_summary.py), [test_catalogue_query_recovery.py](../../tests/test_catalogue_query_recovery.py), [catalogue route test](../../apps/ops-console/src/app/api/instruments/catalogue/route.test.ts) |
| [F08](features/instrument-management.md#f08-canonical-instruments-and-listings) | [canonical link validation](../../security_master_schema/canonical_links.py#L31); [equity/listing materialization](../../apps/reference_api/repository.py#L1508); [listing proposal](../../apps/reference_api/repository.py#L1949) | [Instrument create](../../apps/ops-console/src/app/instruments/create/page.tsx); [contextual listing create](../../apps/ops-console/src/app/instruments/listings/new/page.tsx) | [test_canonical_links.py](../../tests/test_canonical_links.py), [test_reference_versioning.py](../../tests/test_reference_versioning.py), [listing-context.test.ts](../../apps/ops-console/src/app/instruments/listing-context.test.ts) |
| [F09](features/instrument-management.md#f09-requests-and-approval) | [decide_reference_data_proposal](../../apps/reference_api/repository.py#L1368), [work_queue](../../apps/reference_api/repository.py#L4209); [approval reference checks](../../apps/reference_api/approval_reference_integrity.py#L54) | [Instrument requests](../../apps/ops-console/src/app/instruments/requests/page.tsx); [Operations queue](../../apps/ops-console/src/app/operations/page.tsx) | [test_reference_api_proposal_review.py](../../tests/test_reference_api_proposal_review.py), [test_reference_api_work_queue.py](../../tests/test_reference_api_work_queue.py), [requests page test](../../apps/ops-console/src/app/instruments/requests/page.test.ts) |
| [F10](features/instrument-management.md#f10-instrument-taxonomy) | [taxonomy read projection](../../apps/reference_api/repository.py#L462); shared schema in [models.py](../../security_master_schema/models.py) | No general tenant taxonomy-definition or assignment UI. | No dedicated tenant-taxonomy workflow test located; current evidence covers schema/read foundations only. |
| [F11](features/instrument-management.md#f11-instrument-amendments-and-lifecycle) | [select_current_version](../../security_master_schema/reference_versioning.py#L22); [approval checks](../../apps/reference_api/approval_reference_integrity.py#L54) | Creation, review and inspection pages exist; no universal safe amendment/promotion editor. | [test_reference_versioning.py](../../tests/test_reference_versioning.py), [test_cash_definition_history.py](../../tests/test_cash_definition_history.py); no universal amendment-UI test located. |

## Instrument-specific creation and booking

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F12](features/product-booking.md#f12-plain-listed-cash) | [Shared cash command](../../trading/booking.py), [commands/results](../../trading/booking_contracts.py), [persistence](../../trading/booking_store.py), [locked eligibility](../../trading/cash_reference.py); API retains the detail adapter. | [Trade ticket](../../apps/ops-console/src/app/trades/new/trade-ticket.tsx); [booking page](../../apps/ops-console/src/app/trades/new/page.tsx) | [Native/API/file/audit parity](../../tests/test_trading_cash_booking.py), [fixed schemas](../../tests/test_cash_booking_contract_parity.py), [boundaries](../../tests/test_trading_boundaries.py), [test_cash_booking_integrity.py](../../tests/test_cash_booking_integrity.py), [test_trade_booking_api.py](../../tests/test_trade_booking_api.py), [trade-ticket.test.tsx](../../apps/ops-console/src/app/trades/new/trade-ticket.test.tsx) |
| [F13](features/product-booking.md#f13-deliverable-fx-forwards) | [book_fx_forward_trade](../../apps/reference_api/fx_forward_booking.py#L133); [resolve_fx_forward_settlement](../../security_master_schema/fx_forward_booking.py#L48) | [FX forward ticket](../../apps/ops-console/src/app/trades/new/fx-forward-ticket.tsx) | [test_fx_forward_booking_api.py](../../tests/test_fx_forward_booking_api.py), [test_fx_forward_booking_rules.py](../../tests/test_fx_forward_booking_rules.py), [fx-forward-ticket.test.tsx](../../apps/ops-console/src/app/trades/new/fx-forward-ticket.test.tsx) |
| [F14](features/product-booking.md#f14-listed-options) | [load](../../apps/reference_api/option_booking.py#L91), [search](../../apps/reference_api/option_booking.py#L118), [book](../../apps/reference_api/option_booking.py#L128); [execution validation](../../security_master_schema/option_booking.py#L28) | [Option ticket](../../apps/ops-console/src/app/trades/new/option-ticket.tsx); [option creation form](../../apps/ops-console/src/app/instruments/options/new/form.tsx) | [test_option_booking_api.py](../../tests/test_option_booking_api.py), [test_option_booking_rules.py](../../tests/test_option_booking_rules.py), [option-ticket-state.test.tsx](../../apps/ops-console/src/app/trades/new/option-ticket-state.test.tsx) |
| [F15](features/product-booking.md#f15-structured-securities) | [structured-product draft validation](../../apps/reference_api/structured_product_contracts.py#L258); [structured-product materialization](../../apps/reference_api/repository.py#L3484) | [Autocall creation form](../../apps/ops-console/src/app/instruments/autocalls/new/form.tsx); [product ticket](../../apps/ops-console/src/app/trades/new/product-ticket.tsx) | [test_structured_product_api.py](../../tests/test_structured_product_api.py), [test_structured_product_draft.py](../../tests/test_structured_product_draft.py), [product-ticket-model.test.ts](../../apps/ops-console/src/app/trades/new/product-ticket-model.test.ts) [Seeded-note readiness](../delivery/termsheet-note-booking-readiness-2026-10-14.md): six PDF parent notes have approved unit/PCT_OF_PAR dirty OTC conventions; 15 focused tests and app readiness verified. [Terms & Schedule](../delivery/instrument-terms-schedule-2026-10-14.md): read-only approved structured schedules, distinct note/share dates and swap performance-reference look-through are available; lifecycle processing remains separate. |
| [F16](features/product-booking.md#f16-futures) | [materialize_future](../../apps/reference_api/product_booking.py#L188); [materialize_family](../../apps/reference_api/product_booking.py#L598); [book](../../apps/reference_api/product_booking.py#L487) | [Future family page](../../apps/ops-console/src/app/instruments/future-families/page.tsx); [future creation](../../apps/ops-console/src/app/instruments/futures/new/page.tsx); [trade ticket](../../apps/ops-console/src/app/trades/new/product-ticket.tsx) | [test_future_family_api.py](../../tests/test_future_family_api.py), [test_future_specification_rules.py](../../tests/test_future_specification_rules.py), [test_product_booking_api.py](../../tests/test_product_booking_api.py); no dedicated family/future creation page test located. |
| [F17](features/product-booking.md#f17-bonds) | [product booking](../../apps/reference_api/product_booking.py#L487); [bond_amounts](../../security_master_schema/product_booking.py#L65) | [Bond/product ticket](../../apps/ops-console/src/app/trades/new/product-ticket.tsx); [bond terms](../../apps/ops-console/src/app/instruments/bonds/new/page.tsx) | [test_bond_booking_api.py](../../tests/test_bond_booking_api.py), [test_bond_booking_rules.py](../../tests/test_bond_booking_rules.py), [bond-ticket.test.tsx](../../apps/ops-console/src/app/trades/new/bond-ticket.test.tsx) |
| [F18](features/product-booking.md#f18-generic-swaps) | [validate_swap_references / materialize_swap](../../apps/reference_api/swap_creation.py), [nominal/unit terms](../../apps/reference_api/swap_creation_contracts.py); [generic swap context](../../apps/reference_api/generic_swap_booking.py); [product booking](../../apps/reference_api/product_booking.py); [mock-unit seed](../../scripts/seed_mock_unit_swaps.py) | [Swap terms form](../../apps/ops-console/src/components/swap-creation-form.tsx); [unit-aware ticket](../../apps/ops-console/src/app/trades/new/product-ticket.tsx); [history](../../apps/ops-console/src/app/trades/page.tsx) | [test_swap_creation_api.py](../../tests/test_swap_creation_api.py), [test_generic_swap_booking_api.py](../../tests/test_generic_swap_booking_api.py), [unit rules](../../tests/test_unit_swap_booking.py), [mock marks](../../tests/test_mock_unit_swap_data.py), [swap-ticket.test.tsx](../../apps/ops-console/src/app/trades/new/swap-ticket.test.tsx) |

## Trade operations

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F19](features/trade-operations.md#f19-booking-console-and-readiness) | [authorize_booking](../../apps/reference_api/booking_controls.py#L27), [find_booking_replay](../../apps/reference_api/booking_controls.py#L49); [cash readiness](../../apps/reference_api/cash_booking_readiness.py#L63); [product_booking.load_context](../../apps/reference_api/product_booking.py#L285) | [Booking page](../../apps/ops-console/src/app/trades/new/page.tsx); [booking review](../../apps/ops-console/src/app/trades/new/booking-review.tsx) | [test_booking_controls.py](../../tests/test_booking_controls.py), [test_product_booking_readiness.py](../../tests/test_product_booking_readiness.py), [booking-review.test.tsx](../../apps/ops-console/src/app/trades/new/booking-review.test.tsx) |
| [F20](features/trade-operations.md#f20-governed-trade-properties) | [create_property](../../apps/reference_api/trade_configuration.py#L38), [retire_property](../../apps/reference_api/trade_configuration.py#L54), [replace_property](../../apps/reference_api/trade_configuration.py#L64); [validate_trade_annotations](../../apps/reference_api/trade_properties.py#L117) | [Trade configuration console](../../apps/ops-console/src/app/tenant-profile/trade-configuration/trade-configuration-console.tsx); [booking properties](../../apps/ops-console/src/app/trades/new/property-fields.tsx) | [test_trade_configuration.py](../../tests/test_trade_configuration.py), [test_trade_properties.py](../../tests/test_trade_properties.py), [trade-configuration-console.test.tsx](../../apps/ops-console/src/app/tenant-profile/trade-configuration/trade-configuration-console.test.tsx), [property-fields.test.tsx](../../apps/ops-console/src/app/trades/new/property-fields.test.tsx) |
| [F21](features/trade-operations.md#f21-history-and-detail) | [list_booked_trades](../../apps/reference_api/repository.py#L4667), [get_booked_trade_detail](../../apps/reference_api/repository.py#L4824); [trade API](../../apps/reference_api/main.py#L1053) | [Trade history](../../apps/ops-console/src/app/trades/page.tsx); [trade detail](../../apps/ops-console/src/app/trades/%5BtradeId%5D/page.tsx) | [test_trade_history_api.py](../../tests/test_trade_history_api.py), [test_trade_history.py](../../tests/test_trade_history.py), [trade-history-page.test.tsx](../../apps/ops-console/src/app/trades/trade-history-page.test.tsx) |
| [F22](features/trade-operations.md#f22-record-corrections) | [prepare_correction](../../apps/reference_api/trade_corrections.py#L65), [complete_correction](../../apps/reference_api/trade_corrections.py#L83), [cancel_booking](../../apps/reference_api/trade_corrections.py#L98); [lifecycle reconstruction](../../positions/reconstruction.py#L38) | [Correction controls](../../apps/ops-console/src/app/trades/record-correction-controls.tsx); [correction ticket](../../apps/ops-console/src/app/trades/new/page.tsx) | [test_trade_corrections.py](../../tests/test_trade_corrections.py), [test_cancelled_legacy_positions.py](../../tests/test_cancelled_legacy_positions.py), [record-correction-controls.test.tsx](../../apps/ops-console/src/app/trades/record-correction-controls.test.tsx) |
| [F23](features/trade-operations.md#f23-historical-and-recognition-dates) | [frozen_recognition](../../trading/recognition.py); [iter_ledger_facts](../../positions/repository.py#L14) | [Recognition-date fields](../../apps/ops-console/src/app/trades/new/valuation-recognition-fields.tsx); [trade ticket](../../apps/ops-console/src/app/trades/new/trade-ticket.tsx) | [test_position_recognition.py](../../tests/test_position_recognition.py), [test_historical_booking.py](../../tests/test_historical_booking.py), [native booking](../../tests/test_trading_cash_booking.py); no dedicated recognition-field component test located. |
| [F24](features/trade-operations.md#f24-contractual-lifecycle) | Plain bonds: [redemption service](../../lifecycle/bond_service.py), [API](../../apps/reference_api/bond_redemption_routes.py), [ledger adapter](../../positions/repository.py), [applied rules](../../valuation/decisions.py). Separate parked [FX prototype](../../apps/reference_api/fx_delivery.py). | [Bond maturity workspace](../../apps/ops-console/src/components/bond-redemption-console.tsx); no general lifecycle notification dashboard. | [Service](../../tests/test_bond_redemption_service.py), [API](../../tests/test_bond_redemption_api.py), [financial calculation/staging](../../tests/test_bond_redemption_valuation.py). Other product lifecycles not covered. |

## Booking and valuation follow-ups

F18/F37 rate-exchange swaps: [strict terms/frozen leg checks](../../security_master_schema/rate_swap_terms.py),
[native reference/completion helper](../../trading/rate_swaps.py),
[HTTP creation adapter](../../apps/reference_api/swap_creation.py),
[booking context](../../apps/reference_api/generic_swap_booking.py),
[whole-mark proof](../../security_master_schema/swap_valuation.py),
[native price/staging regressions](../../tests/test_rate_swap_booking.py),
[creation form](../../apps/ops-console/src/components/rate-swap-creation-form.tsx)
and [UI checks](../../apps/ops-console/src/components/rate-swap-creation-form.test.tsx).
See [scope, assumptions and delivery](../delivery/rate-exchange-swaps-20261030.md).

F12/F37 fund-unit movements: [native command](../../trading/position_movements.py),
[shared typed proof](../../security_master_schema/quantity_movements.py),
[daily bridge](../../valuation/position_calculation.py),
[financial regressions](../../tests/test_fund_unit_movements.py),
[authority/NAV/staging/cancellation](../../tests/test_fund_unit_movements_integration.py)
and [UI cancellation eligibility](../../apps/ops-console/src/lib/trade-correction-model.test.ts).
No new movement endpoint, ticket or template; unassessed reinvestment income
remains partial coverage. See [delivery](../delivery/fund-unit-movements-20261030.md).

F13/F37 rate-based FX-forward P&L: [frozen ledger adapter](../../positions/fx_forward.py),
[contract-rate selection](../../valuation/forward_inputs.py), [rate-difference/FX bridge](../../valuation/position_calculation.py),
[orchestration](../../valuation/service.py), [readable rules](../../valuation/decisions.py),
[pure financial tests](../../tests/test_fx_forward_pnl.py), [real booking/staging/amendment/publication acceptance](../../tests/test_fx_forward_valuation.py)
and [scope/value-basis documentation](../delivery/fx-forward-rate-pnl-20261014.md).
Discounted forward model MTM remains unsupported; other products have their own
coverage and limits in the valuation section below.

F24/F51 deliverable FX maturity follow-up: [product service and scoped ledger](../../lifecycle/fx_service.py),
[rate economics](../../lifecycle/fx_maturity.py), [shared product-parameterized routes](../../apps/reference_api/bond_redemption_routes.py),
[migration 91](../../alembic/versions/20261014_91_fx_maturity.py) and
[maturity workspace](../../apps/ops-console/src/app/trades/lifecycle/page.tsx).
Evidence: [service/market-selection tests](../../tests/test_fx_maturity_service.py),
[mock booking/API/scope journey](../../tests/test_fx_maturity_api.py) and
[delivery limits](../delivery/fx-forward-maturity-20261014.md).
This supersedes the bond-only F24/F51 implementation boundaries in earlier delivery
records. Maturity posting does not itself implement general FX-forward valuation
or currency delivery.

## Market data

F33 reference-calendar addition: [reviewed import](../../market_data/reference_calendar_import.py),
[local operator](../../scripts/import_reference_calendar.py),
[focused import tests](../../tests/test_reference_calendar_import.py),
[Paris source and activation record](../delivery/paris-reference-calendar-20261013.md),
[major-market registry](../../data/major-exchange-calendars-2026.json) and
[major-market activation/FX verification](../delivery/major-exchange-calendars-20261013.md).

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F25](features/market-data.md#f25-public-reference-universe) | [validate_manifest/seed](../../security_master_schema/index_universe_seed.py#L26); dated seed manifest in [index_universe_2026_10_06.json](../../security_master_schema/data/index_universe_2026_10_06.json) | Shared instruments appear in the [instrument catalogue](../../apps/ops-console/src/app/instruments/page.tsx); no universe-maintenance UI. | [test_index_universe_seed.py](../../tests/test_index_universe_seed.py), [test_index_trading_history.py](../../tests/test_index_trading_history.py); no ongoing membership-maintenance UI test. |
| [F26](features/market-data.md#f26-ingestion-boundary-and-operations) | [ingest_delivery](../../market_data/ingestion.py#L33); [job/attempt lifecycle](../../market_data/jobs.py#L10); operator CLIs in [apps/market_data_ingestor/yahoo.py](../../apps/market_data_ingestor/yahoo.py) | Stored-series workspace only; no acquisition/job-control UI. | [test_market_data_ingestion.py](../../tests/test_market_data_ingestion.py), [test_market_data_jobs.py](../../tests/test_market_data_jobs.py), [test_market_data_boundaries.py](../../tests/test_market_data_boundaries.py) |
| [F27](features/market-data.md#f27-licensing-and-scoped-rights) | [evaluate_rights/load_rights](../../market_data/rights.py#L16); [tenant series entitlement](../../market_data/entitlements.py#L10) | [Source catalogue](../../apps/ops-console/src/app/market-data/sources/page.tsx); [coverage](../../apps/ops-console/src/app/market-data/coverage/page.tsx); no complete licence administration UI. | [test_market_data_rights.py](../../tests/test_market_data_rights.py), [test_dataset_coverage.py](../../tests/test_dataset_coverage.py), [test_market_data_display_rights.py](../../tests/test_market_data_display_rights.py) |
| [F28](features/market-data.md#f28-provider-catalogue-and-priority) | [effective_priority/choose_row](../../market_data/source_priority.py#L21); [save_priority](../../apps/reference_api/market_data_sources.py#L86) | [Sources and priority page](../../apps/ops-console/src/app/market-data/sources/page.tsx) | [test_source_priority.py](../../tests/test_source_priority.py), [test_market_data_sources.py](../../tests/test_market_data_sources.py); no dedicated ranking-page test located. |
| [F29](features/market-data.md#f29-yahoo-historical-data) | [Yahoo fetch/parse](../../market_data/providers/yahoo/adapter.py#L30); [FX parser](../../market_data/providers/yahoo/fx_adapter.py#L21); [personal onboarding](../../market_data/providers/yahoo/onboarding.py#L23) | [Market-data explorer](../../apps/ops-console/src/app/market-data/explorer/page.tsx); no dedicated explorer chart test located. | [test_yahoo_market_data.py](../../tests/test_yahoo_market_data.py), [test_yahoo_fx.py](../../tests/test_yahoo_fx.py), [test_yahoo_market_data_onboarding.py](../../tests/test_yahoo_market_data_onboarding.py) |
| [F30](features/market-data.md#f30-price-basis-and-raw-reconstruction) | [normalize_dataset](../../market_data/providers/yahoo/raw_prices.py#L162); [normalise_as_traded](../../market_data/price_basis.py#L33) | [Explorer](../../apps/ops-console/src/app/market-data/explorer/page.tsx); basis/date interaction has no dedicated page test located. | [test_yahoo_raw_prices.py](../../tests/test_yahoo_raw_prices.py), [test_price_basis.py](../../tests/test_price_basis.py), [test_yahoo_adjustment_evidence.py](../../tests/test_yahoo_adjustment_evidence.py) |
| [F31](features/market-data.md#f31-corporate-actions) | [Yahoo event import](../../market_data/providers/yahoo/corporate_actions.py#L15); [reviewed ratio source/decision loading](../../market_data/split_replay.py), [position replay](../../positions/splits.py), [unrepresented-action/stale-mark guards](../../valuation/corporate_actions.py) | [Quantity adjustment inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx); decisions use an [operator command](../../scripts/review_share_ratio.py), not a general review UI. | [test_yahoo_corporate_actions.py](../../tests/test_yahoo_corporate_actions.py), [test_valuation_corporate_actions.py](../../tests/test_valuation_corporate_actions.py), [ratio arithmetic](../../tests/test_position_split_replay.py), [review/immutability/cutoffs/successors/storage](../../tests/test_split_replay_evidence.py) |
| [F32](features/market-data.md#f32-pricing-policies) | [Shared commands](../../market_data/pricing_policies.py), [command contracts](../../market_data/pricing_policy_contracts.py); [select_composite](../../market_data/policy_selection.py#L93); [policy compatibility](../../market_data/policy_compatibility.py#L68) | [Pricing policies](../../apps/ops-console/src/app/market-data/policies/page.tsx) | [Shared-command/API/authority parity](../../tests/test_pricing_policy_commands.py), [fixed schema/evidence vectors](../../tests/test_extraction_characterization.py), [test_flexible_pricing_policies.py](../../tests/test_flexible_pricing_policies.py), [test_composite_policy_resolution.py](../../tests/test_composite_policy_resolution.py), [test_pricing_policy_compatibility.py](../../tests/test_pricing_policy_compatibility.py); no dedicated page test located. |
| [F33](features/market-data.md#f33-calendars) | [publish_calendar/assign_calendar](../../apps/reference_api/calendar_service.py#L55); [calendar composition](../../market_data/calendar_composition.py#L9) | [Calendar page](../../apps/ops-console/src/app/market-data/calendars/page.tsx) | [test_tenant_calendars.py](../../tests/test_tenant_calendars.py), [test_calendar_composition.py](../../tests/test_calendar_composition.py); no dedicated calendar-page test located. |
| [F34](features/market-data.md#f34-inspection-and-validation) | [market_data_catalogue](../../apps/reference_api/market_data_workspace.py#L36); [audit_dataset](../../market_data/coverage.py#L41); [market-data resolver](../../security_master_schema/market_data_resolver.py) | [Workspace](../../apps/ops-console/src/app/market-data/page.tsx); [coverage](../../apps/ops-console/src/app/market-data/coverage/page.tsx); [explorer](../../apps/ops-console/src/app/market-data/explorer/page.tsx) | [test_market_data_workspace.py](../../tests/test_market_data_workspace.py), [test_market_data_coverage.py](../../tests/test_market_data_coverage.py), [market-data page test](../../apps/ops-console/src/app/market-data/page.test.tsx); no explorer chart/date-refresh test located. |
| [F35](features/market-data.md#f35-tenant-time-series-upload) | Generic provider ingestion exists in [ingest_delivery](../../market_data/ingestion.py#L33); tenant self-service upload endpoint/workflow: none. | No tenant upload page or API route. | No tenant-upload workflow test located; generic ingestion tests do not verify tenant intake. |

## Tenant data onboarding

| Feature | Backend evidence / remaining work | Frontend evidence / remaining work | Tests / evidence limits |
| --- | --- | --- | --- |
| [F59](features/tenant-data-imports.md#f59-governed-tenant-file-imports) | [Import routes](../../apps/reference_api/import_routes.py), [trade orchestration](../../apps/reference_api/import_service.py), [adapter](../../apps/reference_api/import_adapters/trades.py), [safe formats](../../data_imports/formats.py), [retained jobs/identities](../../data_imports/tables.py), migration 96. Existing cash-booking writer remains authoritative; other public processors absent. | [Imports page](../../apps/ops-console/src/app/imports/page.tsx), [guided console](../../apps/ops-console/src/features/imports/import-console.tsx), [row review](../../apps/ops-console/src/features/imports/import-review.tsx), [separate history](../../apps/ops-console/src/features/imports/import-history.tsx), [context-checked BFF](../../apps/ops-console/src/app/api/trade-imports/%5B...path%5D/route.ts). No reconciliation operator UI. | [Parser tests](../../tests/test_import_formats.py), [disposable booking tests](../../tests/test_import_trades.py), [browser recovery/mobile/read-only tests](../../apps/ops-console/browser-tests/imports.spec.ts), [transport tests](../../apps/ops-console/src/app/api/trade-imports/%5B...path%5D/route.test.ts). [Delivery evidence and limits](../delivery/trade-imports-20261018.md). |

External CSV helper evidence is kept in the [optional tooling README](../../tooling/reconciliation_csv/README.md),
not in this product implementation table.

## Valuation and P&L

23 October F18/F37 [supplied swap-mark P&L](../delivery/swap-supplied-mark-pnl-20261023.md):
[frozen generic evidence adapter](../../security_master_schema/swap_valuation.py),
[native BOOKED writer](../../apps/reference_api/product_booking.py),
[ledger reader](../../positions/repository.py), [input selection](../../valuation/service.py),
[shared bridge](../../valuation/position_calculation.py), [applied rules](../../valuation/decisions.py).
Focused evidence: [arithmetic](../../tests/test_swap_valuation.py),
[frozen compatibility](../../tests/test_swap_frozen_valuation.py),
[native resolver integration](../../tests/test_swap_valuation_integration.py).
Existing generic BOOKED payloads are read without rewriting them; options and
automatic funding/reset/maturity modelling remain outside this extension.

F37 monetary-measure preview: [exact kernel](../../valuation/position_measures.py),
[governed inputs](../../valuation/measure_inputs.py), [strategy API](../../apps/reference_api/strategy_workspace.py),
[Measures component](../../apps/ops-console/src/components/strategy-measures.tsx),
  [numerical](../../tests/test_position_measures.py), [database input](../../tests/test_measure_inputs.py),
  [pre-extension assurance and repaired regressions](../../tests/test_position_measures_assurance.py),
  [guarded mock setup](../../scripts/prepare_mock_swap_measures.py),
  [setup/policy validation](../../tests/test_prepare_mock_swap_measures.py)
and [component tests](../../apps/ops-console/src/components/strategy-measures.test.tsx).
See [scope, live-data gaps and evidence](../delivery/position-monetary-measures-20261015.md).

F37 report presentation: [grouped report](../../apps/ops-console/src/components/position-measures-report.tsx),
[readable input inspection](../../apps/ops-console/src/components/strategy-measure-details.tsx),
[full-width disclosure](../../apps/ops-console/src/components/measure-row-disclosure.tsx),
[display-only decimal formatting](../../apps/ops-console/src/lib/measure-display.ts),
[formatting regressions](../../apps/ops-console/src/lib/measure-display.test.ts),
[reason metadata](../../valuation/measure_inputs.py), [reason tests](../../tests/test_measure_presentation.py)
and the existing component suite. [UI delivery/research](../delivery/position-values-report-ui-20261015.md)
distinguishes deferred support from missing inputs without changing calculations.

F16/F37 futures monetary exposure: [linear kernel](../../valuation/position_measures.py),
[governed FUTURE adapter](../../valuation/measure_inputs.py), [price selection](../../valuation/service.py),
[arithmetic](../../tests/test_future_measures.py), [real booking/input tests](../../tests/test_future_measure_inputs.py).
This adds notional/exposure only; no clearing MTM, future P&L, margin or delivery.
See [futures scope and verification](../delivery/future-position-measures-20261015.md).

F13/F37 forward monetary obligations: [frozen adapter](../../valuation/forward_measures.py),
[exact leg arithmetic](../../valuation/position_measures.py), [base-flat safety before pagination](../../apps/reference_api/strategy_workspace.py),
[pure tests](../../tests/test_fx_forward_measures.py), [real booking/FX/lifecycle checks](../../tests/test_fx_forward_measure_inputs.py)
and the existing Measures component/tests above. [Delivery](../delivery/fx-forward-position-measures-20261015.md)
and [cross-measure review](../delivery/quality-reviews/2026-10-15-position-measures-review.md)
retain limits: no discounted MTM, cash movement or risk sensitivities.

F39 self-publication continuity: [policy/authority](../../valuation/self_publication.py),
[tenant settings](../../apps/ops-console/src/components/valuation-publication-settings.tsx),
[storage/security regressions](../../tests/test_self_publication_storage.py),
[API governance regressions](../../tests/test_self_publication_api.py),
[default-off activation and limits](../delivery/valuation-self-publication-20261014.md).

F39 rounding boundary: [implementation](../../valuation/rounding.py),
[regressions](../../tests/test_valuation_rounding.py),
[staging/amendment/publication evidence](../delivery/valuation-storage-rounding-20261013.md).

F39 UI follow-up: [position inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[tabbed console](../../apps/ops-console/src/components/valuation-console.tsx),
[tab interaction regressions](../../apps/ops-console/src/components/valuation-tabs.test.tsx),
[workspace tests](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx),
[delivery and security limits](../delivery/valuation-review-workspace-20261013.md).

October 14 F39 reporting: [SQL filter/count relation](../../valuation/history.py),
[Results/History UI](../../apps/ops-console/src/features/valuation/run-report.tsx),
[visible publication confirmation](../../apps/ops-console/src/features/valuation/publication-action.tsx),
[API/security tests](../../tests/test_valuation_history_api.py),
[report interaction tests](../../apps/ops-console/src/features/valuation/run-report.test.tsx),
[delivery/activation/limits](../delivery/valuation-results-history-report-20261014.md).

24 October F39 Ops review: [read-only metadata/component projections](../../apps/reference_api/valuation_presentation.py),
[full-result filters/order](../../apps/ops-console/src/features/valuation/ops-review-model.ts),
[summary](../../apps/ops-console/src/features/valuation/review-summary.tsx),
[technical IDs](../../apps/ops-console/src/features/valuation/technical-reference.tsx),
[frozen quantities](../../apps/ops-console/src/features/valuation/position-facts.tsx),
[isolated projection tests](../../tests/test_valuation_presentation_api.py),
[browser journey](../../apps/ops-console/browser-tests/pnl-ops.spec.ts),
[delivery and limits](../delivery/pnl-ops-review-20261024.md). This changes review
presentation, not financial formulas, frozen evidence or publication authority.

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F36](features/valuation-and-pnl.md#f36-position-reconstruction) | [iter_ledger_facts](../../positions/repository.py#L14); [reconstruct](../../positions/reconstruction.py#L68); [ratio replay](../../positions/splits.py), [reviewed source/decision loading](../../market_data/split_replay.py) | [Valuation page and position view](../../apps/ops-console/src/app/valuation/page.tsx); [quantity adjustment inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx) | [test_position_repository.py](../../tests/test_position_repository.py), [test_position_reconstruction.py](../../tests/test_position_reconstruction.py), [test_position_projection_scaling.py](../../tests/test_position_projection_scaling.py), [split arithmetic](../../tests/test_position_split_replay.py), [review/storage/scope safety](../../tests/test_split_replay_evidence.py) |
| [F37](features/valuation-and-pnl.md#f37-economic-valuation) | [calculate_position](../../valuation/service.py#L117); [prepare_product_inputs](../../valuation/product_inputs.py#L33); [attribute_projection](../../valuation/position_calculation.py#L62); [resolve_fx](../../valuation/fx.py#L34) | [Valuation page](../../apps/ops-console/src/app/valuation/page.tsx) | [test_position_valuation_acceptance.py](../../tests/test_position_valuation_acceptance.py), [test_valuation_fx.py](../../tests/test_valuation_fx.py), [test_economic_pnl_acceptance.py](../../tests/test_economic_pnl_acceptance.py); no financial/browser sign-off implied. |
| [F38](features/valuation-and-pnl.md#f38-accruals-and-economic-flows) | [load_accrual_inputs](../../valuation/accruals.py#L98), [attach_accruals](../../valuation/accruals.py#L148); [load_economic_flows](../../valuation/flows.py#L99), [attach_flows](../../valuation/flows.py#L131) | [Valuation inputs and components](../../apps/ops-console/src/app/valuation/page.tsx) | [test_valuation_accruals.py](../../tests/test_valuation_accruals.py), [test_valuation_flows.py](../../tests/test_valuation_flows.py); no automated coupon/dividend/reset reconciliation test exists. |
| [F39](features/valuation-and-pnl.md#f39-review-and-publication) | [stage](../../valuation/storage.py#L114), [publish](../../valuation/storage.py#L226); [assert_batch_independent](../../valuation/review_authority.py#L81); [valuation API](../../apps/reference_api/valuation_routes.py#L21) | [Valuation review page](../../apps/ops-console/src/app/valuation/page.tsx) | [test_valuation_storage.py](../../tests/test_valuation_storage.py), [test_valuation_amendments.py](../../tests/test_valuation_amendments.py), [valuation page test](../../apps/ops-console/src/app/valuation/page.test.tsx); financial/browser sign-off remains outstanding. |
| [F40](features/valuation-and-pnl.md#f40-full-nav-and-cash-balances) | [Cash register / exact-date preview](../../valuation/cash_snapshots.py), [cash APIs](../../apps/reference_api/cash_snapshot_routes.py), [migration 89](../../alembic/versions/20261014_89_cash_snapshot_revisions.py). Separate from live investment position P&L. | [Dated cash balance page](../../apps/ops-console/src/app/valuation/cash-balances/page.tsx), [manual entry / CSV / revisions / preview](../../apps/ops-console/src/features/valuation/cash-register.tsx). | [Cash API isolation/revision tests](../../tests/test_cash_snapshot_api.py), [precision/date contracts](../../tests/test_cash_snapshot_contracts.py), [CSV tests](../../apps/ops-console/src/features/valuation/cash-csv.test.ts), [register presentation](../../apps/ops-console/src/features/valuation/cash-register.test.tsx). Migration 89 activated; read-only navigation checked. No populated browser/full cash-P&L/full-NAV sign-off. |

## Broader modules and platform quality

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F41](features/future-modules.md#f41-amc-management) | AMC-specific operations workflow: none; shared [strategy creation](../../apps/reference_api/repository.py#L92) and module/action foundations only. | Strategy/profile surfaces exist; no AMC management workspace. | No AMC workflow test located; generic strategy/entitlement tests are not AMC product tests. |
| [F42](features/future-modules.md#f42-fund-operations) | [select_effective_operational_mapping](../../security_master_schema/tenancy.py#L91) and tenant mapping resolver foundations; no full operational feed pipeline. | No complete fund-operations ingestion/review/reconciliation workspace. | [test_tenant_operational_mapping_database.py](../../tests/test_tenant_operational_mapping_database.py), [test_tenant_operational_mapping_resolution.py](../../tests/test_tenant_operational_mapping_resolution.py); no end-to-end fund-operations UI test. |
| [F43](features/future-modules.md#f43-structured-product-management) | [structured-product draft validation](../../apps/reference_api/structured_product_contracts.py#L258); [reference materialization](../../apps/reference_api/repository.py#L3484); no general payoff/event engine. | [Structured-product creation](../../apps/ops-console/src/app/instruments/autocalls/new/page.tsx); booking uses [product ticket](../../apps/ops-console/src/app/trades/new/product-ticket.tsx); no lifecycle-management workspace. | [test_structured_product_api.py](../../tests/test_structured_product_api.py), [test_structured_product_condition_groups.py](../../tests/test_structured_product_condition_groups.py); no payoff/lifecycle workflow test. [Terms & Schedule](../delivery/instrument-terms-schedule-2026-10-14.md): read-only approved structured schedules, distinct note/share dates and swap performance-reference look-through are available; lifecycle processing remains separate. |
| [F44](features/future-modules.md#f44-structured-product-distribution) | No client/distribution/suitability workflow; module metadata only. | No distribution workspace. | No dedicated distribution workflow tests located. |
| [F45](features/future-modules.md#f45-ucits-aif-and-liquidity-controls) | No validated UCITS/AIF control engine; module metadata/research only. | No compliance monitoring or breach-management workspace. | No dedicated regulatory-control workflow tests located. |
| [F46](features/future-modules.md#f46-portfolio-risk-and-diagnostics) | No validated risk analytics engine; position/P&L foundations are not risk calculations. | No risk diagnostics workspace. | No dedicated risk-product tests located. |
| [F47](features/future-modules.md#f47-settlement-and-accounting) | No general settlement, accounting-posting or reconciliation engine; FX delivery prototype is [record_delivery](../../apps/reference_api/fx_delivery.py#L153). | FX delivery detail controls only; no general settlement/accounting workspace. | FX prototype: [test_fx_delivery_api.py](../../tests/test_fx_delivery_api.py); no general accounting or settlement workflow test exists. |
| [F48](features/platform-quality.md#f48-api-and-operational-hardening) | [required_action](../../apps/reference_api/access_boundary.py#L45), [install_access_boundary](../../apps/reference_api/access_boundary.py#L70); [ProblemDetails](../../apps/reference_api/problem_details.py#L32); [resource limits](../../apps/reference_api/resource_limits.py) | BFFs under [ops-console app API routes](../../apps/ops-console/src/app/api/) | [test_reference_api_boundary.py](../../tests/test_reference_api_boundary.py), [test_reference_api_problem_details.py](../../tests/test_reference_api_problem_details.py), [test_api_resource_bounds.py](../../tests/test_api_resource_bounds.py); no production deployment/SLO test. |
| [F49](features/platform-quality.md#f49-frontend-acceptance) | No single backend function proves UX acceptance; API evidence is linked per capability above. | Pages/components in F01–F39; [shared transport remediation](../delivery/quality-reviews/2026-10-16-frontend-remediation.md) and [October 17 visual consistency](../delivery/quality-reviews/2026-10-17-frontend-visual-consistency.md). Shared theme/native CSS, navigation and [contextual page guides](../delivery/page-contextual-help-20261017.md) preserve authority/evidence. Broader live visual/assistive sign-off remains open. | [Critical journeys](../../apps/ops-console/browser-tests/critical.spec.ts), [actual Next guard](../../apps/ops-console/browser-tests/context-guard.spec.ts), [style/navigation browser checks](../../apps/ops-console/browser-tests/style-consistency.spec.ts), [help disclosure browser check](../../apps/ops-console/browser-tests/page-help.spec.ts), [guide routing](../../apps/ops-console/src/lib/page-guides.test.ts), [CI](../../.github/workflows/quality.yml), plus component/BFF tests. 21 Chrome browser cases and 957 frontend regressions passed October 17; Linux CI execution not observed locally. |
| [F50](features/platform-quality.md#f50-automated-reference-onboarding) | Provider proposals and [Yahoo onboarding](../../market_data/providers/yahoo/onboarding.py#L23); no generic multi-provider onboarding control plane. | [Requests](../../apps/ops-console/src/app/instruments/requests/page.tsx) and [Operations review](../../apps/ops-console/src/app/operations/page.tsx) are manual review surfaces, not automated onboarding administration. | [test_reference_data_automation.py](../../tests/test_reference_data_automation.py), [test_yahoo_market_data_onboarding.py](../../tests/test_yahoo_market_data_onboarding.py); no generic multi-provider workflow test. |

## Additional capabilities and phased deliveries

26 October F49 [HTML/console integrity](../delivery/quality-reviews/2026-10-26-frontend-console-integrity.md):
[shared diagnostic guard](../../apps/ops-console/browser-tests/console-check.ts),
[native pattern regressions](../../apps/ops-console/browser-tests/console-integrity.spec.ts)
and supplied-interest evidence in [P&L acceptance](../../apps/ops-console/browser-tests/pnl-ops.spec.ts)
cover the reproduced markup and input-validation defects. No financial or
authorization semantics changed; wider live/assistive acceptance remains open.

F58's wider [design](../superpowers/specs/2026-10-16-tenant-organisations-design.md) remains phased.
The [17 October trading-only delivery](../delivery/tenant-organisations-20261017.md) implements the register and counterparty/broker controls; directory/non-trading workflows remain pending.

| ID | Backend implementation | Frontend route/component | Focused test evidence |
| --- | --- | --- | --- |
| [F58](features/organisation-management.md#f58-shared-directory-and-tenant-organisations) | [Service](../../apps/reference_api/tenant_organisations.py), [audited routes](../../apps/reference_api/organisation_routes.py), [migration 95](../../alembic/versions/20261017_95_tenant_organisation_profiles.py). Private metadata is separate; original `trade_selection_policy/member` remain authoritative. | [Page](../../apps/ops-console/src/app/tenant-profile/organisations/page.tsx), [feature](../../apps/ops-console/src/features/organisations/); tenant-profile link and old editor hand-off. | [Domain/API/booking/audit](../../tests/test_tenant_organisations.py), [UI protocols](../../apps/ops-console/src/features/organisations/organisations.test.tsx), [browser](../../apps/ops-console/browser-tests/organisations.spec.ts). Migration 95 locally applied with approval; live register load verified. No role-list activation or GLEIF import. |
| [F57](features/valuation-and-pnl.md#f57-valuation-purpose-and-descriptive-tags) | Existing scope/status and strategy/date publication boundary only; controlled purpose lanes and descriptive tags not implemented. | No run-purpose selector or tag catalogue implemented. | No purpose-lane/tag workflow tests; user deferred specification and implementation on 2026-10-14. |
| [F51](features/trade-operations.md#f51-tenant-lifecycle-handling-modes) | [Authority](../../security_master_schema/lifecycle_authority.py), [retained records](../../security_master_schema/lifecycle_tables.py), [plain-bond mode/posting service](../../lifecycle/bond_service.py), [migration 90](../../alembic/versions/20261014_90_bond_redemption.py). | [Group editor](../../apps/ops-console/src/components/tenant-access-console.tsx), [plain-bond workspace](../../apps/ops-console/src/components/bond-redemption-console.tsx), [allowlisted BFF](../../apps/ops-console/src/app/api/lifecycle/[...segments]/route.ts). | [Authority](../../tests/test_lifecycle_authority.py), [service](../../tests/test_bond_redemption_service.py), [UI initial state](../../apps/ops-console/src/components/bond-redemption-console.test.tsx), [BFF](../../apps/ops-console/src/app/api/lifecycle/[...segments]/route.test.ts). Plain-bond increment only; no operating financial browser posting. |
| [F52](features/future-modules.md#f52-strategy-and-pre-trade-ucits-assessment) | No reviewed strategy-level UCITS or hypothetical proposed-trade assessment engine implemented. | No as-of strategy UCITS assessment or proposed-trade-list assessment workflow implemented. | No dedicated assessment workflow tests; specification and implementation are intentionally postponed. |
| [F53](features/regulatory-reporting.md) | [contracts/checks](../../regulatory_reporting/assessment.py), [scoped service](../../regulatory_reporting/service.py), [execution facts](../../regulatory_reporting/source.py), [retained tables](../../regulatory_reporting/tables.py), [audited API](../../apps/reference_api/regulatory_routes.py), migration 104. Preparation only; no official serializer/transport. | [workspace](../../apps/ops-console/src/features/regulatory-reporting/workspace.tsx), [server gate](../../apps/ops-console/src/app/regulatory-reporting/page.tsx), [BFF](../../apps/ops-console/src/app/api/regulatory-reporting/[[...segments]]/route.ts); readable review, entities and export history. | [pure controls](../../tests/test_regulatory_assessment.py), [disposable API](../../tests/test_regulatory_reporting_api.py), [BFF controls](../../apps/ops-console/src/app/api/regulatory-reporting/[[...segments]]/route.test.ts), [browser](../../apps/ops-console/browser-tests/regulatory-reporting.spec.ts). No live regulatory acceptance. |
| [F54](features/future-modules.md#f54-ai-assisted-termsheet-parsing-and-instrument-creation) | No integrated ingestion delivered. Existing `validate_autocall_draft`, `submit_structured_product_proposal`, `decide_structured_product_proposal` and `find_proposal_replay` are reviewed foundations; [design](../superpowers/specs/2026-10-13-structured-product-termsheet-ingestion.md) approved and [execution plan](../superpowers/plans/2026-10-13-structured-product-termsheet-ingestion.md) proposed for review. | Existing `autocalls/new/form.tsx`, `schedule.ts`, `draft.ts` and `payload.ts` implement manual creation; assisted full-instrument hydration and unattended submission not implemented. | 26 focused draft/API-boundary tests passed 2026-10-13, plus offline contract probes; no integrated ingestion or real-termsheet acceptance tests yet. Foundation prioritized 2026-10-13. [All-four reviewed load](../delivery/all-reviewed-autocalls-loaded-2026-10-14.md): all four note/share bundles plus two Phoenix notes ACTIVE in app DB; 40 focused tests and replay/lookup verified. Explicit operator seed, not integrated AI ingestion. |
| [F55](features/future-modules.md#f55-ai-assisted-portfolio-and-investment-idea-recommendations) | No reviewed AI recommendation workflow using portfolio/guideline context or textual investment ideas implemented. | No portfolio-guideline recommendation or text-to-idea recommendation workspace implemented. | No dedicated AI recommendation workflow tests; specification and implementation are intentionally postponed. |
| [F56](features/future-modules.md#f56-option-and-structured-product-greeks-with-cross-asset-look-through-risk) | No reviewed option/structured-product Greeks engine or cross-asset sensitivity/look-through aggregation workflow implemented. | No Greeks, cross-asset risk or underlying look-through analytics workspace implemented. | No dedicated end-to-end Greeks/risk workflow tests; models, specification and implementation are intentionally postponed. |

## Maintenance rule

24 October F39 [source coverage](../delivery/pnl-source-coverage-20261024.md):
[response-only grouping](../../apps/reference_api/valuation_source_coverage.py),
[table](../../apps/ops-console/src/features/valuation/source-coverage.tsx),
[exact/coverage tests](../../tests/test_valuation_presentation.py) and
[synthetic Ops journey](../../apps/ops-console/browser-tests/pnl-ops.spec.ts).
That presentation-only delivery excluded cash FX. The later F39/F40
[cash-FX extension](../delivery/cash-fx-pnl-20261025.md) supersedes that boundary:
[formula](../../valuation/cash_fx.py), [scoped inputs](../../valuation/cash_fx_inputs.py),
[typed storage](../../valuation/cash_fx_storage.py), [source health](../../valuation/cash_fx_health.py),
[migration 99](../../alembic/versions/20261024_99_cash_fx_pnl.py),
[account report](../../apps/ops-console/src/features/valuation/cash-fx-report.tsx),
[storage checks](../../tests/test_cash_fx_storage.py),
[revision/publication checks](../../tests/test_cash_fx_governance.py) and
[browser acceptance](../../apps/ops-console/browser-tests/pnl-ops.spec.ts).
Daily cash FX is always assessed and staged/published separately from investment MARKET;
there is no opt-out flag. Missing entries remain visible and do not themselves
block publication; obsolete cashless retry identities cannot replay as current.
Coverage/hash/reassessment use only opening-through-closing snapshots; old history,
unused accounts and days with neither snapshot do not create expected balances.
Focused storage/governance regressions above pin disappearance and genuine
one-sided gaps. Full cash-stock/fund NAV and intraday movement attribution remain unavailable.
Display follow-up: [rounding boundary tests](../../apps/ops-console/src/features/valuation/presentation.test.ts)
and [unknown/absence rendering tests](../../apps/ops-console/src/features/valuation/source-coverage.test.tsx).

When implementation changes, update the affected capability record and this map in the same change. Keep implementation symbols, route/components and focused tests together. If no workflow, page or test exists, say so; do not use a schema, generic helper or unrelated test as evidence that the desired product workflow is delivered. Add and run tests according to the task's verification scope, then record actual execution separately from this static map.

26 October F39: [position inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx)
supports close/reopen with full-width table and keyboard focus restoration;
[responsive rules](../../apps/ops-console/src/app/valuation-workspace.css),
[component regression](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx)
and [three-viewport synthetic journey](../../apps/ops-console/browser-tests/pnl-ops.spec.ts)
cover the boundary. No financial calculation, authority or publication change.

26 October F39 [report tabs](../delivery/valuation-report-tabs-20261026.md):
[controlled tabs/panels](../../apps/ops-console/src/features/valuation/report-tabs.tsx),
[URL boundary](../../apps/ops-console/src/features/valuation/report-navigation.ts),
[selected log](../../apps/ops-console/src/features/valuation/run-evidence.tsx) and
[console integration](../../apps/ops-console/src/components/valuation-console.tsx).
[Navigation tests](../../apps/ops-console/src/features/valuation/report-navigation.test.ts),
[console transition/race checks](../../apps/ops-console/src/components/valuation-tabs.test.tsx)
and the synthetic browser journeys above cover task separation, retained state,
failed/no-result and denied disclosure. No new data/financial endpoints.
The [result workspace](../../apps/ops-console/src/features/valuation/result-workspace.tsx)
also offers 25/50/100/All position pagination after full-result filtering; its
component/browser regressions cover default size, boundaries, filters, retained
inspection and bounded fallback name lookups.


## F20/F24/F51 allocation-preserving maturity follow-up — 4 November 2026

[Delivery](../delivery/lifecycle-allocation-preservation-20261104.md) links the actual
scope and final activation evidence. [Policy](../../trading/allocation_policy.py),
[batched annotations](../../trading/annotation_snapshots.py), [projection](../../positions/allocations.py)
and [lifecycle validation](../../lifecycle/allocations.py) serve the existing bond/FX
writers. [Policy UI](../../apps/ops-console/src/components/lifecycle-allocation-policy.tsx)
and [entry fields](../../apps/ops-console/src/components/lifecycle-allocation-fields.tsx)
are integrated with trade configuration and maturity preview. Regression evidence:
[projection](../../tests/test_lifecycle_allocations.py), [store](../../tests/test_lifecycle_allocation_store.py),
[HTTP](../../tests/test_lifecycle_allocation_api.py), [contracts](../../tests/test_lifecycle_allocation_contracts.py).
This does not enable other product lifecycle handlers, accounting, or a notification dashboard.

11 November: [Lifecycle closing-entry drawer](../delivery/lifecycle-action-panel-20261110.md) embeds the existing governed maturity workflow in the worklist, preserving filters and guarded financial retries; full-workspace access remains available. Direct and independently approved booking passed real isolated BFF/API/PostgreSQL acceptance; current ledger checks use database recording time. Operating activation remains separate (local port54329 is blocked).
