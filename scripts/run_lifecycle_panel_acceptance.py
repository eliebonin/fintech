"""Real browser/BFF/API/DB acceptance using an owned disposable database only.

Requires TEST_DATABASE_ADMIN_URL to a local test PostgreSQL instance. Never reads
or changes operating database credentials; runtime/API uses a separate non-owner.
"""
from pathlib import Path
import json,os,secrets,shutil,subprocess,sys,time
from uuid import uuid4,UUID
from datetime import date
from sqlalchemy import create_engine,select,text,func
from sqlalchemy.engine import make_url
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def wait_for(url,process,timeout=75):
    import httpx
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Acceptance server exited; inspect its private task log')
        try:
            if httpx.get(url,timeout=3).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise RuntimeError('Acceptance server did not become ready; inspect its private task log')

def main():
    raw=os.environ.get('TEST_DATABASE_ADMIN_URL')
    if not raw:raise RuntimeError('Explicit TEST_DATABASE_ADMIN_URL is required')
    url=make_url(raw)
    if url.host not in {'127.0.0.1','localhost','::1'}:raise ValueError('Acceptance requires a local test database')
    api_port=int(os.environ.get('LIFECYCLE_E2E_API_PORT','8011'));ui_port=int(os.environ.get('LIFECYCLE_E2E_UI_PORT','3011'))
    name='platform_isolated_tests_browser_'+uuid4().hex;role='panel_e2e_'+uuid4().hex[:16]
    evidence=ROOT/'.superpowers/sdd/2026-11-11-lifecycle-panel';evidence.mkdir(parents=True,exist_ok=True)
    admin=create_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT',hide_parameters=True)
    processes=[];logs=[];engine=None;created=False;role_created=False
    try:
        with admin.connect() as c:c.exec_driver_sql(f'CREATE DATABASE "{name}"')
        created=True;os.environ['DATABASE_URL']=url.set(database=name).render_as_string(hide_password=False)
        os.environ['APP_ENV']='test';os.environ['LOCAL_ACCESS_OPERATOR_KEY']=secrets.token_urlsafe(48)
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,check=True)
        from apps.reference_api.db import get_engine
        from security_master_schema import models as m,access_management as am,access_sessions
        from security_master_schema.demo_data import load_demo_data,DEMO_IDS as ids
        from security_master_schema.database_security import grant_runtime_access,assert_runtime_role
        from trading.profiles.migration import backfill_profiles
        from tests.test_valuation_service import valued
        from tests.test_bond_redemption_service import setup as setup_bond
        from lifecycle import bond_service
        from scripts.local_database_config import private_write
        engine=get_engine();load_demo_data(engine)
        with engine.begin() as c:backfill_profiles(c,ids['demo_user_account'])
        strategies={};groups=[]
        for mode in ['DIRECT','REVIEW']:
            fixture=valued.__wrapped__();c,r,trade=next(fixture)
            try:
                _,_,group=setup_bond(c,r,trade);groups.append(group)
                c.execute(m.strategy.update().where(m.strategy.c.strategy_id==r.strategy_id).values(display_name='SYNTHETIC Lifecycle '+mode))
                if mode=='DIRECT':bond_service.configure(c,r.tenant_id,ids['demo_user_account'],ids['platform_admin_user_account'],r.strategy_id,'DIRECT',0,'Owned browser acceptance')
                strategies[mode]=str(r.strategy_id)
                # The reusable fixture adds a synthetic valuation rule at90.
                # Give the first committed fixture its own slot before reusing it.
                if mode=='DIRECT':c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,m.valuation_policy_rule.c.rule_sequence==90).values(rule_sequence=91))
                c.commit()
            finally:fixture.close()
        with engine.begin() as c:
            c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==ids['bond_instrument_node']).values(canonical_name='SYNTHETIC Maturity Acceptance Bond'))
            reviewer=am.add_user(c,ids['tenant'],ids['demo_user_account'],name='SYNTHETIC Independent Reviewer')
            am.set_user_groups(c,ids['tenant'],ids['demo_user_account'],reviewer,groups)
            operator=am.add_user(c,ids['tenant'],ids['demo_user_account'],name='SYNTHETIC Independent Operator')
            c.execute(m.platform_user_account.insert().values(user_account_id=operator,platform_role='PLATFORM_ADMIN',valid_from=date(2026,1,1)))
            maker_token=access_sessions.start(c,ids['platform_admin_user_account'],ids['tenant'],ids['demo_user_account'],environment='test')
            reviewer_token=access_sessions.start(c,operator,ids['tenant'],reviewer,environment='test')
            baseline=c.scalar(select(func.count()).select_from(m.trade))
            cash_tables=[t for t in m.metadata.tables.values() if 'cash_balance' in t.name]
            cash_before={t.fullname:c.scalar(select(func.count()).select_from(t)) for t in cash_tables}
            password=secrets.token_urlsafe(48)
            verifier=c.connection.driver_connection.pgconn.encrypt_password(password.encode(),role.encode(),b'scram-sha-256').decode()
            c.exec_driver_sql(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{verifier}'")
            grant_runtime_access(c,role);role_created=True
        runtime_url=url.set(database=name,username=role,password=password)
        runtime=create_engine(runtime_url,hide_parameters=True)
        with runtime.connect() as c:assert_runtime_role(c)
        runtime.dispose()
        state=dict(strategies=strategies,tenant=str(ids['tenant']),instrument=str(ids['bond_instrument_node']),makerToken=maker_token,reviewerToken=reviewer_token,baseURL=f'http://127.0.0.1:{ui_port}',evidence=str(evidence))
        state_path=evidence/'state.json';private_write(state_path,json.dumps(state))
        env={**os.environ,'DATABASE_URL':runtime_url.render_as_string(hide_password=False),'REFERENCE_API_URL':f'http://127.0.0.1:{api_port}','NEXT_DIST_DIR':'.next-lifecycle-panel-live','LIFECYCLE_E2E_STATE_FILE':str(state_path),'LIFECYCLE_E2E_BASE_URL':state['baseURL']}
        for label,args,cwd in [('api',[sys.executable,'-m','uvicorn','apps.reference_api.main:app','--host','127.0.0.1','--port',str(api_port)],ROOT),('frontend',[shutil.which('node'),str(ROOT/'apps/ops-console/node_modules/next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port',str(ui_port)],ROOT/'apps/ops-console')]:
            log=(evidence/(label+'.log')).open('w',encoding='utf-8');logs.append(log)
            process=subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0);processes.append(process)
            wait_for(f'http://127.0.0.1:{api_port}/health' if label=='api' else state['baseURL']+'/select-context',process)
        print('Isolated lifecycle acceptance app ready; no operating data used',flush=True)
        result=subprocess.run([shutil.which('node'),str(ROOT/'apps/ops-console/node_modules/@playwright/test/cli.js'),'test','--config','playwright.lifecycle-e2e.config.ts'],cwd=ROOT/'apps/ops-console',env=env)
        if result.returncode:return result.returncode
        with engine.connect() as c:
            targets=[UUID(value) for value in strategies.values()]
            rows=c.execute(select(m.bond_redemption_posting).where(m.bond_redemption_posting.c.strategy_id.in_(targets))).mappings().all()
            assert len(rows)==2
            assert c.scalar(select(func.count()).select_from(m.trade))==baseline+2
            for row in rows:
                trade=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(row['trade_ids'][0]))).mappings().one()
                assert trade['trade_type']=='MATURITY_REDEMPTION' and trade['quantity']==-100000 and trade['execution_price']==100
            review=next(row for row in rows if str(row['strategy_id'])==strategies['REVIEW'])
            assert review['actor_id']==reviewer and review['real_operator_id']==operator
            assert review['evidence']['authority']['operation']=='APPROVE'
            for t in cash_tables:assert c.scalar(select(func.count()).select_from(t))==cash_before[t.fullname]
        (evidence/'result.json').write_text(json.dumps(dict(status='PASSED',newClosingTrades=2,independentApproval=True,cashSnapshotsUnchanged=True)),encoding='utf-8')
        print('PASS: two sourced maturity closures; independent user/operator approval; cash snapshots unchanged',flush=True)
        return 0
    finally:
        for process in reversed(processes):
            # Stop only the processes launched by this runner, including Next's child.
            if process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else:process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill()
        for log in logs:log.close()
        if engine:engine.dispose()
        if created:
            assert name.startswith('platform_isolated_tests_browser_') and len(name.rsplit('_',1)[1])==32
            with admin.connect() as c:
                c.execute(text('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()'),dict(name=name))
                c.exec_driver_sql(f'DROP DATABASE "{name}"')
                if role_created:c.exec_driver_sql(f'DROP ROLE {role}')
        admin.dispose()
if __name__=='__main__':raise SystemExit(main())
