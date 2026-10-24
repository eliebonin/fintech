"""External dataset preparation must be removable from the clean application."""
import ast
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=('apps/reference_api','apps/market_data_ingestor','security_master_schema',
    'market_data','positions','valuation','lifecycle','data_imports','tests')


def test_product_and_its_tests_do_not_import_external_csv_tooling():
    violations=[]
    for folder in PRODUCT:
        for path in (ROOT/folder).rglob('*.py'):
            if path==Path(__file__):continue
            # These are source-adapter tests, not general product acceptance.
            if path.parent==ROOT/'tests' and path.name.startswith('test_reconciliation_'):
                violations.append(str(path.relative_to(ROOT)))
            if folder in ('data_imports','market_data') and path.stem.startswith('reconciliation'):
                violations.append(str(path.relative_to(ROOT)))
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                targets=([node.module or ''] if isinstance(node,ast.ImportFrom) else
                    [a.name for a in node.names] if isinstance(node,ast.Import) else [])
                for target in targets:
                    if target.startswith(('tooling','data_imports.reconciliation','market_data.reconciliation',
                        'scripts.seed_reconciliation','scripts.prepare_reconciliation','tests.test_reconciliation_')):
                        violations.append(f'{path.relative_to(ROOT)} -> {target}')
    assert not violations,'\n'.join(violations)


def test_application_schema_and_supported_imports_load_with_tooling_unavailable():
    result=subprocess.run([sys.executable,'-B','-c','''
import importlib.abc,sys
class NoTooling(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(('tooling','data_imports.reconciliation','market_data.reconciliation')):
            raise ImportError('One-off tooling is absent: '+fullname)
sys.meta_path.insert(0,NoTooling())
from apps.reference_api.main import create_app
from data_imports.formats import parse_file
from valuation.service import calculate_position
from market_data.ingestion import ingest_delivery
paths=create_app().openapi()['paths']
assert '/v1/trades/imports' in paths
assert '/v1/valuation/attempts' in paths
assert not any('reconciliation' in path for path in paths)
'''],cwd=ROOT,capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('name',['seed_reconciliation_bundle','prepare_reconciliation_valuation'])
def test_isolated_operator_help_needs_no_csv_database_or_network(name):
    result=subprocess.run([sys.executable,'-B',str(ROOT/'tooling'/'reconciliation_csv'/f'{name}.py'),'--help'],
        cwd=ROOT.parent,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert '--apply' in result.stdout
