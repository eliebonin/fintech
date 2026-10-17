"""Queue metadata and counts use the same action-bound scope as valuation reads."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_access_management import connection
from security_master_schema import access_management as am, models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.repository import work_queue


@pytest.mark.parametrize('mode,actions,selection,expected',[
    ('SELECTED',['VALUATION_READ'],['strategy'],1),
    ('SELECTED',['VALUATION_READ'],[],0),
    ('ALL',['VALUATION_READ'],[],2),
    ('ALL',['REFERENCE_READ'],[],0),
])
def test_nav_rows_and_total_are_filtered_before_pagination(connection,mode,actions,selection,expected):
    tenant,admin=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='Queue reader')
    group=am.save_group(connection,tenant,admin,code='QUEUE_'+uuid4().hex,name='Queue scope',
        actions=actions,scope_mode=mode,strategy_ids=[ids[key] for key in selection])
    am.set_user_groups(connection,tenant,admin,user,[group])
    original=dict(connection.execute(select(m.nav_calculation_run).where(
        m.nav_calculation_run.c.nav_calculation_run_id==ids['nav_calculation_run'])).mappings().one())
    snapshots=dict(connection.execute(select(m.position_snapshot).where(
        m.position_snapshot.c.position_snapshot_id==ids['position_snapshot'])).mappings().one())
    navs={}
    for strategy in [ids['strategy'],ids['uk_fund_strategy']]:
        snapshot=uuid4(); run=uuid4();navs[strategy]=run
        connection.execute(m.position_snapshot.insert().values(**(snapshots|dict(position_snapshot_id=snapshot,
            strategy_id=strategy,content_hash=uuid4().hex*2))))
        connection.execute(m.nav_calculation_run.insert().values(**(original|dict(nav_calculation_run_id=run,
            position_snapshot_id=snapshot,strategy_id=strategy,status='DRAFT'))))
    connection.info['request_actor']=user
    try:
        page=work_queue(connection,tenant,'test','queue-test',limit=1,offset=0,permission_codes=actions)
        assert page.counts['NAV_REVIEW']==expected
        navitems=[item for item in page.items if item.category=='NAV_REVIEW']
        if expected==1:
            assert [item.reference_id for item in navitems]==[navs[ids['strategy']]]
        elif expected==0:
            assert navitems==[]
        if expected==2:
            second=work_queue(connection,tenant,'test','queue-test',limit=1,offset=1,permission_codes=actions)
            assert second.counts['NAV_REVIEW']==2
            assert len(second.items)==1
            assert second.items[0].item_id!=page.items[0].item_id
    finally:
        connection.info.pop('request_actor',None)
