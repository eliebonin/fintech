"""The reusable cash command must run with the HTTP application unavailable."""
import ast
from pathlib import Path
from tests.test_market_data_boundaries import run_without_api

ROOT=Path(__file__).resolve().parents[1]


def test_trading_has_no_http_imports():
    folder=ROOT/'trading'
    assert (folder/'booking.py').exists(),'Trading command owner is missing'
    violations=[]
    for path in folder.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names=([node.module or ''] if isinstance(node,ast.ImportFrom) else
                [a.name for a in node.names] if isinstance(node,ast.Import) else [])
            violations.extend(f'{path.name}: {n}' for n in names if n=='apps' or n.startswith(('apps.','fastapi')))
    assert not violations,violations


def test_native_command_and_contracts_import_without_http():
    result=run_without_api('''
from trading.booking import book_cash_trade
from trading.booking_contracts import TradeBookingRequest, BookingResult
from trading.booking_store import booking_fingerprint
print('isolated')
''')
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='isolated'


def test_trading_does_not_construct_engines_or_commit_callers_transactions():
    for path in (ROOT/'trading').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if not isinstance(node,ast.Call):continue
            assert not (isinstance(node.func,ast.Name) and node.func.id in {'create_engine','get_engine'}),path.name
            assert not (isinstance(node.func,ast.Attribute) and node.func.attr in {'commit','rollback'}),path.name
