"""Mock holdings + real HTTP lifecycle commands; owned disposable DB only."""
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.test_access_api import client, headers
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup
from security_master_schema import models as m, access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids


def test_mock_review_book_cancel_and_direct_rebook_journey(client, valued):
    c, request, source_trade = valued
    original_dates = dict(c.execute(select(m.instrument_dates).where(
        m.instrument_dates.c.instrument_node_id == ids['bond_instrument_node'])).mappings().one())
    listing, booked, group = setup(c, request, source_trade)
    reviewer = am.add_user(c, request.tenant_id, ids['demo_user_account'], name='Mock independent bond reviewer')
    am.set_user_groups(c, request.tenant_id, ids['demo_user_account'], reviewer, [group])
    c.commit()  # Independent HTTP transactions read only this disposable population.
    ops = headers()
    review = ops | {'X-User-Account-Id': str(reviewer)}
    target = dict(strategyId=str(request.strategy_id), instrumentId=str(ids['bond_instrument_node']))
    base = '/v1/lifecycle/bond-redemptions'

    def ok(response, status=200):
        assert response.status_code == status, response.text
        return response.json()

    def preview():
        return ok(client.post(base + '/preview', headers=ops, json=target))

    try:
        options = ok(client.get('/v1/lifecycle/options', headers=ops, params={'strategyId': str(request.strategy_id)}))
        assert options['policy']['mode'] == 'REVIEW'
        assert str(ids['bond_instrument_node']) in [row['id'] for row in options['instruments']]
        initial = preview()
        assert Decimal(initial['inputs']['movements'][0]['quantity']) == -100000
        assert Decimal(initial['inputs']['price']) == 100
        prepared_body = target | {'expectedFingerprint': initial['inputHash']}
        proposal = ok(client.post(base + '/prepare', headers=ops, json=prepared_body), 201)
        approval = prepared_body | {'proposalId': proposal['proposalId'], 'confirmBooking': True}
        assert client.post(base + '/approve', headers=ops | {'Idempotency-Key': str(uuid4())}, json=approval).status_code == 403
        key = str(uuid4())
        approved = ok(client.post(base + '/approve', headers=review | {'Idempotency-Key': key}, json=approval), 201)
        repeated = ok(client.post(base + '/approve', headers=review | {'Idempotency-Key': key}, json=approval), 201)
        assert repeated['trade_ids'] == approved['trade_ids']
        assert len(approved['trade_ids']) == 1
        assert client.post(base + '/preview', headers=ops, json=target).status_code == 409
        proposals = ok(client.get(base, headers=ops, params={'strategyId': str(request.strategy_id)}))
        assert proposals['items'][0]['status'] == 'BOOKED'
        with c.begin():
            closing = c.execute(select(m.trade).where(m.trade.c.trade_id == UUID(approved['trade_ids'][0]))).mappings().one()
            assert closing['trade_type'] == 'MATURITY_REDEMPTION'
            assert closing['quantity'] == Decimal(-100000)
            assert closing['settlement_date'] is None
            assert c.scalar(select(m.trade.c.lifecycle_status).where(m.trade.c.trade_id == booked)) == 'BOOKED'
        cancellation = target | {'postingId': approved['posting_id'], 'reason': 'Mock correction walkthrough', 'confirmCancel': True}
        cancellation.pop('instrumentId')
        cancelled = ok(client.post(base + '/cancel', headers=ops | {'Idempotency-Key': str(uuid4())}, json=cancellation))
        assert cancelled['evidence']['operation'] == 'CANCEL'
        assert Decimal(preview()['inputs']['movements'][0]['quantity']) == -100000
        proposals = ok(client.get(base, headers=ops, params={'strategyId': str(request.strategy_id)}))
        assert proposals['items'][0]['status'] == 'CANCELLED'
        ok(client.post('/v1/lifecycle/policy', headers=ops, json=dict(strategyId=str(request.strategy_id),
            mode='DIRECT', expectedRevision=0, reason='Mock Ops-triggered direct mode', confirmChange=True)))
        fresh = preview()
        direct = ok(client.post(base + '/book', headers=ops | {'Idempotency-Key': str(uuid4())},
            json=target | {'expectedFingerprint': fresh['inputHash'], 'confirmBooking': True}), 201)
        assert direct['trade_ids'] != approved['trade_ids']
        assert client.post(base + '/preview', headers=ops, json=target).status_code == 409
        postings = ok(client.get(base + '/postings', headers=ops, params={'strategyId': str(request.strategy_id)}))
        assert postings['total'] == 3  # Approved close, retained cancellation, new direct close.
    finally:
        c.rollback()
        with c.begin():
            # This HTTP fixture committed its own synthetic mark rule. Remove
            # only that rule so later rollback-based tests can reuse sequence 90.
            c.execute(m.valuation_policy_rule.delete().where(
                m.valuation_policy_rule.c.subject_reference_node_id == listing))
            c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id == ids['bond_instrument_node'])
                .values(**original_dates))
