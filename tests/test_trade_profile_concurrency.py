"""Real locking: a reviewed allocation change must see an in-flight booking."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic,sleep
from uuid import uuid4
import pytest
from sqlalchemy import select,text
from tests.test_governed_trade_configuration import engine,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from trading.booking import book_cash_trade
from trading.booking_contracts import TradeBookingRequest
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,current_assignment
from trading.profiles.migration import initialize_strategy_profile
from apps.reference_api.trade_configuration import create_property
from tenant_reference.errors import ConfigurationConflict


def test_allocation_adoption_waits_for_booking_and_rechecks_its_new_source(engine):
    strategy=uuid4()
    with engine.begin() as c:
        parent=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==ids['strategy'])).mappings().one())
        c.execute(m.strategy.insert().values(**(parent|dict(strategy_id=strategy,strategy_code='CONCURRENT_'+strategy.hex))))
        initialize_strategy_profile(c,TENANT,ACTOR,strategy)
        revision=current_assignment(c,TENANT,strategy)['revision']
        field=create_property(c,TENANT,ACTOR,dict(code='CONCURRENT_'+uuid4().hex,label='New allocation',valueType='TEXT'))
        profile=create_profile(c,TENANT,ACTOR,'CONCURRENT_'+uuid4().hex,'Concurrent profile','Isolated test')
        version=publish_profile_version(c,TENANT,ACTOR,profile['profileId'],dict(label='Require allocation',reason='Explicit concurrent change',expectedVersion=0,fields=[dict(propertyCode=field['code'],propertyVersion=1,requirement='REQUIRED',lifecycleBehavior='ALLOCATION')]))
    booked=Event();release=Event();attempted=Event();pids={}
    def writer():
        with engine.begin() as c:
            pids['writer']=c.scalar(text('select pg_backend_pid()'))
            request=TradeBookingRequest(strategyId=strategy,listingId=ids['hsbc_xlon_listing_node'],side='BUY',quantity='1',executionPrice='1',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05')
            book_cash_trade(c,TENANT,ACTOR,request,str(uuid4()))
            booked.set()
            if not release.wait(5):raise RuntimeError('Owned concurrency release timed out')
    def adopter():
        with engine.begin() as c:
            pids['adopter']=c.scalar(text('select pg_backend_pid()'));attempted.set()
            assign_profile(c,TENANT,ACTOR,strategy,version['versionId'],revision,'Reviewed against initially empty population')
    with ThreadPoolExecutor(max_workers=2) as executor:
        first=executor.submit(writer)
        try:
            assert booked.wait(5)
            second=executor.submit(adopter);assert attempted.wait(5)
            blocked=False;deadline=monotonic()+2
            with engine.connect() as observer:
                while monotonic()<deadline:
                    blocked=pids['writer'] in observer.scalar(text('select pg_blocking_pids(:pid)'),dict(pid=pids['adopter']))
                    if blocked:break
                    sleep(.02)
            assert blocked,'The actual tenant configuration lock must serialize adoption behind booking'
        finally:release.set()
        first.result(timeout=5)
        with pytest.raises(ConfigurationConflict,match='required source classifications'):second.result(timeout=5)
    with engine.connect() as c:
        assert current_assignment(c,TENANT,strategy)['revision']==revision
        assert c.scalar(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==strategy)) is not None
