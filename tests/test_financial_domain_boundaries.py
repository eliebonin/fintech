"""The reviewed financial services must not depend on HTTP-owned adapters."""
import ast
from pathlib import Path
import pytest


@pytest.mark.parametrize('path',[
    'tenant_reference/catalogues.py','tenant_reference/sources.py',
    'positions/fx_forward.py',
    'positions/structured_note.py','security_master_schema/structured_note_valuation.py',
    'security_master_schema/cash_products.py',
    'security_master_schema/future_economics.py','security_master_schema/future_valuation.py','positions/future.py',
    'valuation/structured_note_inputs.py','valuation/structured_note_interest.py',
    'valuation/measure_inputs.py','valuation/measure_contracts.py','valuation/note_measure_balances.py',
    'valuation/source_dependencies.py','valuation/bond_measure_balances.py',
    'security_master_schema/creation_options.py',
    'market_data/bond_quotes.py','market_data/bond_quote_store.py',
    'valuation/bond_prices.py','valuation/bond_quote_review.py',
    'valuation/review_coverage.py','valuation/accrued_balance_presentation.py',
    'valuation/flows.py',
    'lifecycle/coupon_service.py','lifecycle/fx_service.py',
    'valuation/accruals.py','valuation/amendments.py','lifecycle/bond_service.py',
    'market_data/pricing_policies.py','market_data/pricing_policy_contracts.py',
    'apps/market_data_ingestor/yahoo_fx_valuation_setup.py',
    'security_master_schema/evidence.py',
    'security_master_schema/booking_conventions.py','security_master_schema/swap_terms.py',
])
def test_shared_financial_services_do_not_import_api_contracts_or_services(path):
    root=Path(__file__).resolve().parents[1]
    tree=ast.parse((root/path).read_text(encoding='utf-8'))
    violations=[]
    for node in ast.walk(tree):
        modules=[node.module or ''] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
        violations.extend(module for module in modules if module.startswith('apps.reference_api'))
    assert not violations, f'{path} depends on transport-owned code: {violations}'


@pytest.mark.parametrize('path', [
    'tenant_reference/catalogues.py','tenant_reference/sources.py',
    'positions/fx_forward.py','positions/repository.py',
    'market_data/bond_quote_store.py','market_data/price_basis_store.py',
    'market_data/storage.py','market_data/providers/yahoo/raw_prices.py',
    'security_master_schema/evidence.py',
])
def test_shared_evidence_does_not_depend_on_valuation(path):
    root=Path(__file__).resolve().parents[1]
    tree=ast.parse((root/path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        modules=([node.module or ''] if isinstance(node,ast.ImportFrom) else
                 [a.name for a in node.names] if isinstance(node,ast.Import) else [])
        assert not any(m=='valuation' or m.startswith('valuation.') for m in modules), path


def test_lifecycle_uses_shared_evidence_without_importing_the_pnl_kernel():
    root=Path(__file__).resolve().parents[1]
    for path in (root/'lifecycle').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.ImportFrom):
                assert node.module!='valuation.economics',str(path)
