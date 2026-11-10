from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.profile_fixtures import assign
from trading.profiles.management import preview_assignments,adopt_assignments
from trading.profiles.configuration import current_assignment
from tenant_reference.errors import ConfigurationConflict


def rows(preview):return [dict(strategyId=r['strategyId'],expectedRevision=r['assignmentRevision'],inputHash=r['inputHash']) for r in preview['items']]


def test_batch_is_explicit_atomic_and_retry_safe(connection,monkeypatch):
    c=connection
    version,_=assign(c,TENANT,ACTOR,ids['strategy'])
    strategies=[ids['strategy'],ids['uk_fund_strategy']]
    preview=preview_assignments(c,TENANT,ACTOR,strategies,version['versionId'])
    assert len(preview['items'])==2 and preview['allowed']
    before=c.scalar(select(func.count()).select_from(m.strategy_trade_profile_assignment))
    import trading.profiles.configuration as commands
    original=commands._append_assignment;calls=0
    def failure(*args,**kwargs):
        nonlocal calls
        calls+=1
        result=original(*args,**kwargs)
        if calls==2:raise RuntimeError('Synthetic second assignment audit failure')
        return result
    monkeypatch.setattr(commands,'_append_assignment',failure)
    with pytest.raises(RuntimeError,match='second assignment'):
        adopt_assignments(c,TENANT,ACTOR,version['versionId'],rows(preview),'Synthetic reviewed selection')
    assert c.scalar(select(func.count()).select_from(m.strategy_trade_profile_assignment))==before
    monkeypatch.setattr(commands,'_append_assignment',original)
    result=adopt_assignments(c,TENANT,ACTOR,version['versionId'],rows(preview),'Synthetic reviewed selection')
    count=c.scalar(select(func.count()).select_from(m.strategy_trade_profile_assignment))
    assert len(result['items'])==2
    adopt_assignments(c,TENANT,ACTOR,version['versionId'],rows(preview),'Synthetic reviewed selection')
    assert c.scalar(select(func.count()).select_from(m.strategy_trade_profile_assignment))==count


def test_changed_member_blocks_whole_batch_without_partial_assignments(connection):
    c=connection
    version,_=assign(c,TENANT,ACTOR,ids['strategy'])
    strategies=[ids['strategy'],ids['uk_fund_strategy']]
    preview=preview_assignments(c,TENANT,ACTOR,strategies,version['versionId'])
    assign(c,TENANT,ACTOR,ids['uk_fund_strategy'])
    before=current_assignment(c,TENANT,ids['strategy'])['revision']
    with pytest.raises(ConfigurationConflict,match='changed'):
        adopt_assignments(c,TENANT,ACTOR,version['versionId'],rows(preview),'Stale selected population')
    assert current_assignment(c,TENANT,ids['strategy'])['revision']==before


def test_foreign_strategy_in_selection_denies_whole_review(connection):
    version,_=assign(connection,TENANT,ACTOR,ids['strategy'])
    with pytest.raises(PermissionError):preview_assignments(connection,TENANT,ACTOR,[ids['strategy'],uuid4()],version['versionId'])
