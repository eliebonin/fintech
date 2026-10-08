"""Enforce ingestion isolation so adding a provider cannot pull in the web API."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run_without_api(code):
    return subprocess.run([sys.executable, '-c', '''
import importlib.abc
import sys
class Unavailable(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('apps.reference_api', 'fastapi')):
            raise ImportError('API unavailable: ' + fullname)
sys.meta_path.insert(0, Unavailable())
''' + code], cwd=ROOT, capture_output=True, text=True, timeout=30)


def test_core_imports_without_api_or_provider_adapters():
    result = run_without_api('''
class NoAcquisition(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('market_data.providers', 'httpx')):
            raise ImportError('Acquisition unavailable: ' + fullname)
sys.meta_path.insert(0, NoAcquisition())
from market_data.ingestion import ingest_delivery
from market_data.rights import evaluate_rights
from datetime import date
assert not evaluate_rights(None, [], [], 'DISPLAY', date(2026, 10, 7), 'PERSONAL').allowed
print('isolated')
''')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'isolated'


@pytest.mark.parametrize('entry', ['module', 'legacy_script'])
def test_cli_help_runs_without_reference_api(entry):
    invocation = ("runpy.run_module('apps.market_data_ingestor.yahoo', run_name='__main__')"
                  if entry == 'module' else
                  "runpy.run_path('scripts/ingest_yahoo_market_data.py', run_name='__main__')")
    result = run_without_api("import runpy\nsys.argv = ['ingestor', '--help']\n" + invocation)
    assert result.returncode == 0, result.stderr
    assert '--initialize-only' in result.stdout
    assert '--acknowledge-personal-access' in result.stdout


def imports(path):
    parts = path.relative_to(ROOT).with_suffix('').parts
    package = '.'.join(parts[:-1])
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = importlib.util.resolve_name('.' * node.level + (node.module or ''), package) if node.level else node.module
            yield module
            yield from (module + '.' + alias.name for alias in node.names)


def test_dependency_contracts():
    assert (ROOT / 'market_data').is_dir(), 'The ingestion subsystem needs an explicit package boundary'
    violations = []
    for folder in ('market_data', 'apps/reference_api', 'security_master_schema'):
        for path in (ROOT / folder).rglob('*.py'):
            relative = path.relative_to(ROOT).as_posix()
            forbidden = []
            if folder == 'market_data':
                forbidden += ['apps', 'fastapi']
                if '/providers/' not in relative:
                    forbidden += ['market_data.providers', 'httpx']
            else:
                forbidden += ['market_data.ingestion', 'market_data.storage', 'market_data.providers', 'apps.market_data_ingestor']
            if relative == 'market_data/contracts.py':
                forbidden += ['sqlalchemy', 'security_master_schema', 'market_data.storage', 'market_data.rights']
            for target in imports(path):
                if any(target == prefix or target.startswith(prefix + '.') for prefix in forbidden):
                    violations.append(f'{relative} -> {target}')
    assert not violations, '\n'.join(violations)
