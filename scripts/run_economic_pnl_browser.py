"""Owned synthetic browser acceptance server on 8008; never operating data.

Run with the repository Python runtime; stop with Ctrl-C to drop its owned DB.
The UI must use port 3008, REFERENCE_API_URL=http://127.0.0.1:8008 and its own
NEXT_DIST_DIR=.next-economic-pnl. Seed helpers are test fixtures, not application
imports or a production initialization path.
"""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    name='fortem_isolated_tests_browser_'+uuid4().hex
    url=make_url('postgresql+psycopg://fortem:fortem_local_only@localhost:54329/postgres')
    admin=create_engine(url,isolation_level='AUTOCOMMIT')
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    engine=None
    try:
        os.environ['DATABASE_URL']=url.set(database=name).render_as_string(hide_password=False)
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,check=True)
        from apps.reference_api.db import get_engine
        from apps.reference_api.main import create_app
        from security_master_schema.demo_data import load_demo_data,DEMO_IDS as ids
        from security_master_schema import models as m
        from tests.test_valuation_service import valued
        from tests.test_economic_pnl_acceptance import add_bond
        from valuation.service import calculate
        from valuation.accruals import record_accrual,accrual_amounts
        from valuation.flows import book_flow
        from valuation import storage
        from valuation.amendments import request_component_change
        engine=get_engine();load_demo_data(engine)
        fixture=valued.__wrapped__();c,r,trade=next(fixture)
        try:
            c.execute(m.tenant.update().where(m.tenant.c.tenant_id==ids['tenant']).values(display_name='SYNTHETIC Economic P&L Acceptance'))
            add_bond(c,r,trade)
            inputs=dict(openingBalance=Decimal('990'),dailyEarned=Decimal('10'),closingBalance=Decimal('0'),balanceMovements=Decimal('-1000'),openingFx=Decimal(1),closingFx=Decimal(1))
            for day in (date(2026,9,30),date(2026,10,1)):
                payload=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=day,inputType='DAILY_INTEREST',
                    currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],eligibleNominal=Decimal('100000'),sourceReference='SYNTHETIC',
                    eligibilityConvention='OPS_ASSESSED_NOMINAL',inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[],supersedesInputId=None)
                record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
            book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=ids['hsbc_instrument_node'],currencyId=ids['gbp_currency'],
                amount=Decimal('100'),component='DIVIDEND',recognitionRole='INCOME',economicDate=date(2026,10,1),paymentDate=None,sourceReference='SYNTHETIC DIVIDEND'),str(uuid4()))
            c.commit()
            actor=ids['platform_admin_user_account']
            run=storage.begin_attempt(engine,r,actor,str(uuid4()))
            batch=storage.stage(c,run,actor,calculate(c,r))
            item=storage.batch_view(c,r.tenant_id,batch)['items'][0]
            request=request_component_change(c,r.tenant_id,batch,item['attribution_id'],actor,
                dict(component='ADJUSTMENT',amount=Decimal('-10'),reason='Synthetic browser request',sourceReference='SYNTHETIC NOTICE'),str(uuid4()))
            c.commit()
            print(f'SYNTHETIC ONLY: database={name}, strategy={r.strategy_id}, attempt={run}, batch={batch}, request={request}',flush=True)
        finally: fixture.close()
        import uvicorn
        uvicorn.run(create_app(engine=engine),host='127.0.0.1',port=8008)
    finally:
        if engine: engine.dispose()
        assert name.startswith('fortem_isolated_tests_browser_') and len(name.rsplit('_',1)[1])==32
        with admin.connect() as c: c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


if __name__=='__main__': main()
