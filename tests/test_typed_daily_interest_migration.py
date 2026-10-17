"""Exact legacy backfill and atomic rejection, only in owned temporary DBs."""
import json,os,subprocess,sys
from pathlib import Path
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url


@pytest.mark.parametrize('amount,valid',[('1.234567890123',True),('1.0000000000001',False)])
def test_backfill_preserves_evidence_and_never_silently_rounds(amount,valid):
    base=make_url(os.environ['DATABASE_URL'])
    assert base.database.startswith('platform_isolated_tests_')
    name='platform_interest_migration_'+uuid4().hex
    admin=create_engine(base.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    url=base.set(database=name);engine=create_engine(url)
    env=dict(os.environ,DATABASE_URL=url.render_as_string(hide_password=False))
    root=Path(__file__).resolve().parents[1]
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','20261014_92'],cwd=root,env=env,check=True,capture_output=True)
        from security_master_schema.demo_data import load_demo_data,DEMO_IDS as ids
        load_demo_data(engine)
        payload=json.dumps(dict(currencyId=str(ids['gbp_currency']),inputs=dict(dailyEarned=amount),amounts=dict(dailyLocal=amount)))
        with engine.begin() as c:
            identity=c.scalar(text('''INSERT INTO nav.daily_accrual_input(tenant_id,strategy_id,recorded_by,instrument_id,
                value_date,input_type,revision,submission_key,input_hash,request_hash,payload)
                VALUES(:tenant,:strategy,:actor,:bond,'2026-10-01','DAILY_INTEREST',1,'legacy','retained-hash','retained-request',CAST(:payload AS jsonb)) RETURNING input_id'''),
                dict(tenant=ids['tenant'],strategy=ids['strategy'],actor=ids['demo_user_account'],bond=ids['bond_instrument_node'],payload=payload))
        result=subprocess.run([sys.executable,'-m','alembic','upgrade','20261014_93'],cwd=root,env=env,capture_output=True,text=True)
        with engine.connect() as c:
            if valid:
                assert result.returncode==0,result.stderr
                row=c.execute(text('SELECT daily_earned_interest,currency_id,payload,input_hash FROM nav.daily_accrual_input WHERE input_id=:id'),dict(id=identity)).mappings().one()
                assert row['daily_earned_interest']==Decimal(amount)
                assert row['currency_id']==ids['gbp_currency'] and row['payload']==json.loads(payload)
                assert row['input_hash']=='retained-hash'
                with pytest.raises(Exception,match='immutable'):
                    with c.begin_nested(): c.execute(text('UPDATE nav.daily_accrual_input SET daily_earned_interest=1 WHERE input_id=:id'),dict(id=identity))
            else:
                assert result.returncode!=0 and 'cannot be backfilled exactly' in result.stderr
                assert c.scalar(text('SELECT version_num FROM alembic_version'))=='20261014_92'
                assert c.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='nav' AND table_name='daily_accrual_input' AND column_name='daily_earned_interest'"))==0
            assert c.scalar(text("SELECT tgenabled FROM pg_trigger WHERE tgname='daily_accrual_immutable'"))=='O'
    finally:
        engine.dispose()
        assert name.startswith('platform_interest_migration_') and len(name.rsplit('_',1)[1])==32
        with admin.connect() as c: c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
