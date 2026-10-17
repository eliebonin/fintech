# Valuation methodology assurance — 14 October 2026

Status: implemented and focused-test verified. No schema migration or operating financial mutation is required. This is a supported-method assurance slice, not a complete NAV/product-pricing sign-off.

Local activation: restarted only the verified API with the same loopback launch settings; startup and `/health` succeeded. No operating calculation, trade, permission, publication or database migration was performed. API-contract freshness, whitespace and local link targets in 13 reconciled documents passed. New calculations use the updated explanations; existing published results remain unchanged.

[Plan](../superpowers/plans/2026-10-14-valuation-methodology-assurance.md) · [Methodology and source rationale](../architecture/market-data-and-valuation/valuation-methodology.md) · [Capability records](../product/features/valuation-and-pnl.md).

## Changes

- Added an explicit product/lifecycle matrix, exact local/reporting bridge, fund NAV availability semantics, bond daily-interest/stock distinction, forward maturity convention and cash-preview boundary, each linked to source/tests.
- Added 17 hand-calculated cases for holdings, shorts, new/additional trades, partial/full closures, execution-only round trips, currency attribution, new fund execution economics, bond earnings, forward maturity and fail-closed input/product cases.
- Fixed missing calculation-level daily-accrual explanation by supplying all retained line economic evidence, rather than flows alone.
- Staged position explanations now include the frozen value/execution bridge and clean-bond nominal convention. Selection rules retain source publication/receipt and staleness alongside requested/actual dates. Existing UI consumes readable explanations; no UI repricing or redesign was added.
- Corrected a stale legacy compatibility fixture: it now denies newly publishing an unverified legacy candidate, then models an already-published historical row and verifies replacement. Production safety checks remain intact.
- Reconciled root AGENTS/KNOWLEDGE/FIX and current feature navigation using md-document. Review focus is the valuation dependency path, not every repository file. Unrelated stable findings/manual notes remain.

No numerical formula, price selection authority, product readiness gate, cash movement, publication permission or historical stored financial record was changed. New explanations affect new result evidence/hashes; they are not retrospectively inserted into published records.

## Verification

Initial reproduction: two pure rule assertions failed for missing facts/rules; the bond integration failed for missing DAILY_EARNED_ACCRUAL while numerical interest remained correct. The matrix initially used a wrong forward-unit fixture; corrected to the real CURRENCY_AMOUNT contract without weakening product validation.

Final pure command:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/test_valuation_methodology_matrix.py tests/test_valuation_decisions.py tests/test_position_valuation.py tests/test_position_split_replay.py tests/test_fx_forward_pnl.py tests/test_valuation_product_inputs.py tests/test_valuation_resolver.py -q -p no:cacheprovider
```

64 passed. This includes 17 new matrix cases; existing-behaviour characterizations are not claimed as new RED/GREEN implementations.

Final disposable integration command:

```powershell
.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_bond_redemption_valuation.py tests/test_economic_pnl_acceptance.py tests/test_valuation_accruals.py tests/test_valuation_flows.py tests/test_valuation_follow_up.py tests/test_valuation_service.py tests/test_fx_forward_valuation.py tests/test_position_attribution_storage.py -q --tb=short -p no:cacheprovider
```

63 passed in 27.28 seconds; wrapper startup/migration/cleanup took additional time. Prior run: 62 passed and the stale legacy-publication test failed as expected under migration 92; corrected fixture rerun is green. The wrapper exited successfully and removed its owned test database. No full-project suite, new browser financial walkthrough, independent custodian comparison or load test was run. Previously completed FX browser acceptance remains separate dated evidence.

## Trade-offs / remaining work

Existing day-end execution FX and PRICE/FX/CROSS are explicit engine conventions, not universal accounting requirements. Forward rate-difference values remain undiscounted; options, futures, swaps and structured notes remain unsupported by the live pricer. Cash snapshots remain value-only previews. Assessed earnings depend on Ops eligibility/inputs. Broader corporate actions, source-change reassessment beyond the trade ledger, automatic amendment carry-forward, cash P&L/full NAV and measured scale remain open.

Research sources and limitations are recorded beside the matrix: opened SEC/IFRIC/FINRA guidance and current FSA IOSCO-update notice; inaccessible June 2026 IOSCO final text is not presented as reviewed. Self-review is by the author, honoring sequential/no-subagent preference, not an independent audit. Work stays in the user-selected dirty feature checkout, with unrelated changes preserved; no commit/push requested.
