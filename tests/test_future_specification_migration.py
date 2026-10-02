import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_family_specification_migration_is_additive_and_nullable(monkeypatch):
    path=Path(__file__).parents[1]/'alembic/versions/20261002_57_future_family_specification.py'
    spec=importlib.util.spec_from_file_location('family_spec_migration',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls=[]
    monkeypatch.setattr(module,'op',SimpleNamespace(add_column=lambda table,column,**kwargs:calls.append((table,column,kwargs))))
    module.upgrade()
    table,column,kwargs=calls[0]
    assert table=='future_family' and column.name=='specification_payload' and column.nullable
    assert kwargs['schema']=='secm' and module.down_revision=='20261001_56'
