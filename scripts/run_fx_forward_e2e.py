"""Disposable FX-forward browser fixture; verify owned DB cleanup after stopping.

Graceful exit cleans in finally; Windows forced termination can skip finally.
Never remove a DB unless its exact owned name and disconnected state are checked.
"""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from dataclasses import replace
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    name = 'platform_isolated_tests_browser_' + uuid4().hex
    url = make_url(os.environ.get('TEST_DATABASE_ADMIN_URL',
        'postgresql+psycopg://platform:platform_local_only@localhost:54329/postgres')).set(database='postgres')
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    engine = None
    try:
        os.environ['DATABASE_URL'] = url.set(database=name).render_as_string(hide_password=False)
        subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT, check=True)
        from apps.reference_api.db import get_engine
        from apps.reference_api.main import create_app
        from security_master_schema.demo_data import load_demo_data, DEMO_IDS as ids
        from security_master_schema import models as m, access_management as am
        from tests.test_valuation_service import valued
        from tests.test_fx_maturity_service import setup
        from tests.test_fx_forward_valuation import rates
        engine = get_engine()
        load_demo_data(engine)
        fixture = valued.__wrapped__()
        c, r, equity = next(fixture)
        try:
            r = replace(r, opening_cutoff=datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc), closing_cutoff=datetime(2026, 10, 1, 23, 59, 59, 999999, tzinfo=timezone.utc), reporting_currency_id=ids['usd_currency'], daily=True)
            instrument, group, cut, spot = setup(c, r)
            c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == instrument).values(canonical_name='SYNTHETIC GBP/USD forward 2026-10-01'))
            series = rates(c, r, instrument)
            original = c.execute(select(m.trade).where(m.trade.c.trade_id == equity)).mappings().one()
            c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity, sequence_no=2, event_type='CANCELLED', event_datetime_utc=original['trade_datetime_utc'], recorded_by_user_account_id=ids['demo_user_account'], event_payload='{}'))
            c.execute(m.strategy.update().where(m.strategy.c.strategy_id == r.strategy_id).values(display_name='SYNTHETIC FX Forward E2E'))
            reviewer = am.add_user(c, r.tenant_id, ids['demo_user_account'], name='Synthetic independent FX reviewer')
            review_group = am.save_group(c, r.tenant_id, ids['demo_user_account'], code='FXREVIEW_' + uuid4().hex, name='Synthetic FX valuation review', actions=['VALUATION_READ', 'VALUATION_RUN', 'VALUATION_REVIEW', 'MARKET_DATA_READ', 'TRADE_READ'], scope_mode='SELECTED', strategy_ids=[r.strategy_id])
            am.set_user_groups(c, r.tenant_id, ids['demo_user_account'], reviewer, [review_group])
            c.commit()
            print(f'SYNTHETIC ONLY database={name} tenant={r.tenant_id} actor={ids["demo_user_account"]} reviewer={reviewer} strategy={r.strategy_id} policy={r.policy_id} cut={cut} currency={ids["usd_currency"]} instrument={instrument}', flush=True)
        finally:
            fixture.close()
        import uvicorn
        uvicorn.run(create_app(engine=engine), host='127.0.0.1', port=8009)
    finally:
        if engine:
            engine.dispose()
        assert name.startswith('platform_isolated_tests_browser_') and len(name.rsplit('_', 1)[1]) == 32
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


if __name__ == '__main__':
    main()
