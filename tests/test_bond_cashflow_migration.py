"""An actual v94 receipt survives renames and can still be revised after upgrade."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def test_original_coupon_evidence_survives_full_schedule_upgrade():
    base = make_url(os.environ['DATABASE_URL'])
    assert base.database.startswith('platform_isolated_tests_')
    name = 'platform_isolated_tests_' + uuid4().hex
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name)
    engine = create_engine(url)
    env = dict(os.environ, DATABASE_URL=url.render_as_string(hide_password=False))
    root = Path(__file__).resolve().parents[1]
    def upgrade(target):
        result = subprocess.run([sys.executable, '-B', '-m', 'alembic', 'upgrade', target], cwd=root, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    try:
        upgrade('20261015_94')
        from security_master_schema.demo_data import load_demo_data, DEMO_IDS as ids
        load_demo_data(engine)
        with engine.begin() as c:
            values = dict(tenant=ids['tenant'], bond=ids['bond_instrument_node'], actor=ids['demo_user_account'], currency=ids['gbp_currency'], strategy=ids['strategy'])
            header = c.execute(text('''INSERT INTO secm.bond_coupon_schedule(tenant_id,instrument_id,bond_terms_id,terms_snapshot,revision,currency_id,
                source_reference,reason,request_key,request_hash,actor_id,real_operator_id)
                SELECT :tenant,:bond,bond_terms_id,'{"retained":"original"}'::jsonb,1,:currency,'Original statement','Initial','legacy-schedule','original-hash',:actor,:actor
                FROM secm.bond_terms WHERE instrument_node_id=:bond AND is_current RETURNING *'''), values).mappings().one()
            original = c.execute(text('''INSERT INTO secm.bond_coupon_period(schedule_id,coupon_key,accrual_start,accrual_end,payment_date,amount_per_100)
                VALUES(:schedule,'Original coupon','2026-04-01','2026-10-01','2026-10-01',1.234567890123) RETURNING *'''), dict(schedule=header['schedule_id'])).mappings().one()
            payment = c.execute(text('''INSERT INTO trd.bond_coupon_payment(logical_payment_id,tenant_id,strategy_id,period_id,revision,status,payment_date,
                amount,currency_id,source_reference,note,request_key,request_hash,actor_id,real_operator_id)
                VALUES(uuidv7(),:tenant,:strategy,:period,1,'CONFIRMED','2026-10-01',1234.567890123456,:currency,'Original receipt','Kept','legacy-receipt','payment-hash',:actor,:actor) RETURNING *'''),
                values | dict(period=original['period_id'])).mappings().one()
        upgrade('head')
        from lifecycle import coupon_service as service
        from lifecycle.coupon_contracts import PaymentCreate
        from tests.test_bond_coupons import grant_coupon_ops
        with engine.begin() as c:
            current = c.execute(text('SELECT * FROM secm.bond_cashflow WHERE cashflow_id=:id'), dict(id=original['period_id'])).mappings().one()
            assert current['cashflow_type'] == 'COUPON' and current['amount_per_100'] == original['amount_per_100']
            assert current['cashflow_key'] == original['coupon_key']
            assert dict(c.execute(text('SELECT * FROM secm.bond_cashflow_schedule WHERE schedule_id=:id'), dict(id=header['schedule_id'])).mappings().one()) == dict(header)
            assert dict(c.execute(text('SELECT * FROM trd.bond_coupon_payment WHERE payment_id=:id'), dict(id=payment['payment_id'])).mappings().one()) == dict(payment)
            grant_coupon_ops(c, ids['tenant'], ids['strategy'])
            correction = service.record_payment(c, ids['tenant'], ids['demo_user_account'], PaymentCreate(
                strategyId=ids['strategy'], periodId=original['period_id'], paymentDate='2026-10-01', amount='1200', currencyId=ids['gbp_currency'],
                sourceReference='Corrected statement', note='Verified correction', supersedesPaymentId=payment['payment_id'], confirmPayment=True), uuid4().hex, correction=True)
            assert correction['revision'] == 2 and correction['logical_payment_id'] == payment['logical_payment_id']
            reversal = service.reverse_payment(c, ids['tenant'], ids['demo_user_account'], ids['strategy'], correction['payment_id'], 'Synthetic reversal', uuid4().hex)
            assert reversal['revision'] == 3 and reversal['status'] == 'REVERSED'
    finally:
        engine.dispose()
        assert name.startswith('platform_isolated_tests_') and len(name.rsplit('_', 1)[1]) == 32
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
