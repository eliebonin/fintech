"""The reviewed financial services must not depend on HTTP-owned adapters."""
import ast
from pathlib import Path
import pytest


@pytest.mark.parametrize('path',[
    'positions/fx_forward.py',
    'valuation/measure_inputs.py',
    'valuation/flows.py',
    'lifecycle/coupon_service.py','lifecycle/fx_service.py',
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
