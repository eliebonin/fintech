"""Revision 54 reconciles only exact compatible manually provisioned fields."""
import importlib.util
from pathlib import Path
import pytest
import sqlalchemy as sa

def migration():
    spec=importlib.util.spec_from_file_location('bond_revision_54',Path(__file__).resolve().parents[1]/'alembic/versions/20261001_54_bond_floating_coupon_fields.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run(monkeypatch,columns):
    from types import SimpleNamespace
    module=migration();added=[];altered=[]
    monkeypatch.setattr(module,'context',SimpleNamespace(is_offline_mode=lambda:False))
    monkeypatch.setattr(module.sa,'inspect',lambda bind:SimpleNamespace(get_columns=lambda *args,**kwargs:columns))
    monkeypatch.setattr(module,'op',SimpleNamespace(get_bind=lambda:None,add_column=lambda table,column,**kwargs:added.append(column.name),alter_column=lambda table,name,**kwargs:altered.append(name)))
    module.upgrade()
    return added,altered

def column(name,type):return dict(name=name,type=type,nullable=True,default=None)

def test_fresh_schema_adds_fields(monkeypatch):
    assert run(monkeypatch,[])[0]==['floating_reference_index','floating_spread']

def test_existing_compatible_fields_are_preserved(monkeypatch):
    added,altered=run(monkeypatch,[column('floating_reference_index',sa.String(150)),column('floating_spread',sa.Numeric(20,12))])
    assert added==[]
    assert altered==['floating_reference_index','floating_spread']

@pytest.mark.parametrize('bad',[column('floating_reference_index',sa.String(100)),column('floating_spread',sa.Numeric(20,8)),dict(column('floating_spread',sa.Numeric(20,12)),nullable=False),dict(column('floating_spread',sa.Numeric(20,12)),default='0')])
def test_incompatible_schema_is_not_silently_accepted(monkeypatch,bad):
    with pytest.raises(RuntimeError,match='manual reconciliation'):run(monkeypatch,[bad])
