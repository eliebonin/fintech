"""Local bootstrap configuration preserves other settings and never prints keys."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]


def operator():
    spec=importlib.util.spec_from_file_location('configure_local_access',ROOT/'scripts/configure_local_access.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_private_setup_is_idempotent_and_preserves_unrelated_configuration(tmp_path,capsys):
    ui=tmp_path/'apps/ops-console/.env.local'
    ui.parent.mkdir(parents=True)
    original='REFERENCE_API_URL=http://127.0.0.1:8001\n# Keep this comment\n'
    ui.write_text(original)
    module=operator()
    module.configure(tmp_path)
    first=ui.read_text()
    assert first.startswith(original)
    root=(tmp_path/'.env.local-access').read_text()
    from dotenv import dotenv_values
    key=dotenv_values(tmp_path/'.env.local-access')['LOCAL_ACCESS_OPERATOR_KEY']
    assert len(key)>=32 and key==dotenv_values(ui)['LOCAL_ACCESS_OPERATOR_KEY']
    assert dotenv_values(ui)['APP_ENV']=='local'
    module.configure(tmp_path)
    assert ui.read_text()==first
    assert (tmp_path/'.env.local-access').read_text()==root
    assert key not in capsys.readouterr().out


def test_mismatched_existing_keys_are_not_silently_replaced(tmp_path):
    ui=tmp_path/'apps/ops-console/.env.local'
    ui.parent.mkdir(parents=True)
    ui.write_text('LOCAL_ACCESS_OPERATOR_KEY='+'a'*48+'\n')
    config=tmp_path/'.env.local-access'
    config.write_text('LOCAL_ACCESS_OPERATOR_KEY='+'b'*48+'\n')
    original=(ui.read_bytes(),config.read_bytes())
    with pytest.raises(ValueError,match='match'):
        operator().configure(tmp_path)
    assert (ui.read_bytes(),config.read_bytes())==original
