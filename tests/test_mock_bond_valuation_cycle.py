"""Connected synthetic coupon/maturity/review cycle, never operating data.

Catches coupon double income, lost maturity-day P&L, unauthorized self-review,
rewritten publications and automatic carry-over of manual amendments.
"""
from datetime import datetime, timezone
from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

from sqlalchemy import select, func

from tests.test_access_api import client, headers
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup
from tests.test_bond_coupons import schedule_data
from security_master_schema import models as m, access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids


def test_mock_bond_coupon_to_publication_and_corrected_successor(client, valued, monkeypatch, request):
    c, r, equity_trade = valued
    assert c.engine.url.database.startswith('platform_isolated_tests_')
    original_dates = dict(c.execute(select(m.instrument_dates).where(
        m.instrument_dates.c.instrument_node_id == ids['bond_instrument_node'])).mappings().one())
    listing, _, _ = setup(c, r, equity_trade)
    # Own the policy as well as the strategy. Resolution snapshots retain FK
    # references to selected rules, so teardown must not delete audited rules.
    owned_policy = uuid4()
    policy_row = dict(c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id == r.policy_id)).mappings().one())
    c.execute(m.valuation_policy.insert().values(**(policy_row | dict(valuation_policy_id=owned_policy,
        policy_code='MOCK_CYCLE_' + owned_policy.hex, strategy_id=r.strategy_id,
        submission_key=None, submission_fingerprint=None))))
    rule_row = dict(c.execute(select(m.valuation_policy_rule).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id == ids['valuation_policy_rule'])).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule_row | dict(
        valuation_policy_rule_id=uuid4(), valuation_policy_id=owned_policy))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.subject_reference_node_id == listing)
        .values(valuation_policy_id=owned_policy))
    r = replace(r, policy_id=owned_policy)

    def restore_shared_reference_fixture():
        c.rollback()
        with c.begin():
            c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id == ids['bond_instrument_node'])
                .values(**original_dates))

    request.addfinalizer(restore_shared_reference_fixture)
    # The fixture supplies immutable as-booked evidence. All subsequent business
    # actions below go through the real HTTP handlers and real PostgreSQL.
    original = c.execute(select(m.trade).where(m.trade.c.trade_id == equity_trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity_trade, sequence_no=2,
        event_type='CANCELLED', event_datetime_utc=original['trade_datetime_utc'],
        recorded_by_user_account_id=ids['demo_user_account'], event_payload='{}'))
    c.execute(m.strategy.update().where(m.strategy.c.strategy_id == r.strategy_id)
        .values(display_name='Mock coupon-to-maturity acceptance', base_currency_id=ids['gbp_currency']))
    group = am.save_group(c, r.tenant_id, ids['demo_user_account'], code='MOCK_REVIEW_' + uuid4().hex,
        name='Mock valuation reviewers', actions=['VALUATION_READ', 'VALUATION_RUN', 'VALUATION_REVIEW',
            'MARKET_DATA_READ', 'TRADE_READ'], scope_mode='SELECTED', strategy_ids=[r.strategy_id])
    reviewer = am.add_user(c, r.tenant_id, ids['demo_user_account'], name='Mock independent coupon reviewer')
    am.set_user_groups(c, r.tenant_id, ids['demo_user_account'], reviewer, [group])
    series = c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.reference_node_id == listing))
    source = dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id == series)).mappings().one())
    stamp = datetime(2026, 9, 30, 16, tzinfo=timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source | dict(market_data_observation_id=uuid4(),
        market_date=stamp.date(), value=D('99'), received_at_utc=stamp, observed_at_utc=stamp,
        source_published_at_utc=stamp, source_observation_key='MOCK_COUPON_' + uuid4().hex))))
    company = c.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.status == 'ACTIVE').limit(1))
    c.commit()  # Needed for the independent API/calculation transactions.
    ops = headers()
    review = ops | {'X-User-Account-Id': str(reviewer)}
    strategy = str(r.strategy_id)
    instrument = str(ids['bond_instrument_node'])
    policy = str(r.policy_id)
    cut = str(r.cut_id)
    gbp = str(ids['gbp_currency'])
    # Retain bounded, real query-boundary diagnostics if a close fails. This
    # observes the genuine ledger iterator; it does not substitute economics.
    from lifecycle import bond_service
    real_ledger = bond_service.iter_ledger_facts
    boundaries = []

    def traced_ledger(connection, request, **kwargs):
        facts = tuple(real_ledger(connection, request, **kwargs))
        rows = connection.execute(select(m.trade.c.trade_id, m.trade.c.quantity, m.trade.c.created_at_utc,
            m.trade_lifecycle_event.c.sequence_no, m.trade_lifecycle_event.c.recorded_at_utc)
            .join(m.trade_lifecycle_event).where(m.trade.c.strategy_id == request.strategy_id)).all()
        newest = max((stamp for row in rows for stamp in (row.created_at_utc, row.recorded_at_utc)), default=request.information_cutoff)
        boundaries.append(dict(asof=str(request.information_cutoff), facts=len(facts),
            newestTimestampMinusAsOfSeconds=(newest-request.information_cutoff).total_seconds(), rows=list(map(str, rows))))
        del boundaries[:-3]
        return iter(facts)

    monkeypatch.setattr(bond_service, 'iter_ledger_facts', traced_ledger)

    def ok(method, path, body=None, *, actor=None, status=200, key=None):
        response = client.request(method, path, json=body,
            headers=(actor or ops) | ({'Idempotency-Key': key or str(uuid4())} if method == 'POST' else {}))
        assert response.status_code == status, response.text + '\nLedger boundary diagnostics: ' + repr(boundaries)
        return response.json()

    def calculate(opening, closing):
        result = ok('POST', '/v1/valuation/attempts', dict(strategyId=strategy, policyId=policy,
            cutId=cut, reportingCurrencyId=gbp, openingDate=opening, closingDate=closing), status=201)
        assert result['attempt']['status'] == 'COMPLETED'
        assert result['batch']['status'] == 'STAGED'
        assert any(event['stage'] == 'STAGING' for event in result['events'])
        return result

    prior_schedule = ok('GET', f'/v1/lifecycle/coupons/schedule?strategyId={strategy}&instrumentId={instrument}')['schedule']
    schedule = ok('POST', '/v1/lifecycle/coupons/schedules', schedule_data() | dict(instrumentId=instrument,
        expectedRevision=prior_schedule['revision'] if prior_schedule else 0), status=201)
    for day, opening, closing, movement in [('2026-09-30', '980', '990', '0'), ('2026-10-01', '990', '0', '-1000')]:
        ok('POST', '/v1/valuation/accrual-inputs', dict(strategyId=strategy, instrumentId=instrument,
            valueDate=day, currencyId=gbp, reportingCurrencyId=gbp, policyId=policy, cutId=cut,
            dailyEarned='10', openingBalance=opening, closingBalance=closing, balanceMovements=movement,
            eligibleNominal='100000', sourceReference='Mock daily-interest assessment',
            eligibilityConvention='OPS_ASSESSED_NOMINAL'), status=201)
    before = calculate('2026-09-29', '2026-09-30')
    assert D(before['batch']['summary']['marketPnl']) == 500  # 100,000/100 × (99 − 98.5).
    assert D(before['batch']['summary']['grossPnl']) == 510

    account = ok('POST', '/v1/valuation/cash-accounts', dict(strategyId=strategy, companyId=str(company),
        label='Mock custodian account', accountType='CUSTODY'), status=201)['accountId']
    ok('POST', '/v1/valuation/cash-balances', dict(strategyId=strategy, rows=[dict(accountId=account,
        currencyId=gbp, valueDate='2026-10-01', amount='106000', sourceReference='Mock custody statement',
        note='Stock only; not new P&L')]), status=201)
    with c.begin():
        counts = tuple(c.scalar(select(func.count()).select_from(table)) for table in (m.trade, m.cash_balance))
    receipt = ok('POST', '/v1/lifecycle/coupons/payments', dict(strategyId=strategy,
        periodId=schedule['periods'][0]['period_id'], paymentDate='2026-10-01', amount='1000', currencyId=gbp,
        cashAccountId=account, sourceReference='Mock coupon bank receipt', note='Already earned through daily interest',
        confirmPayment=True), status=201)
    assert receipt['effects'] == dict(additionalInterestPnl='0', cashBalanceUpdated=False,
        accrualInputsUpdated=False, tradeCreated=False)
    with c.begin():
        assert tuple(c.scalar(select(func.count()).select_from(table)) for table in (m.trade, m.cash_balance)) == counts
    after_receipt = calculate('2026-09-29', '2026-09-30')
    assert D(after_receipt['batch']['summary']['grossPnl']) == 510

    ok('POST', '/v1/lifecycle/policy', dict(strategyId=strategy, mode='DIRECT', expectedRevision=0,
        reason='Mock Ops-controlled maturity timing', confirmChange=True))
    target = dict(strategyId=strategy, instrumentId=instrument)

    def close_maturity():
        preview = ok('POST', '/v1/lifecycle/bond-redemptions/preview', target)
        assert D(preview['inputs']['movements'][0]['quantity']) == -100000
        assert D(preview['inputs']['price']) == 100
        return ok('POST', '/v1/lifecycle/bond-redemptions/book', target | dict(
            expectedFingerprint=preview['inputHash'], confirmBooking=True), status=201)

    posted = close_maturity()
    maturity = calculate('2026-09-30', '2026-10-01')
    base = maturity['batch']
    assert D(base['summary']['closingValue']) == 0
    assert D(base['summary']['marketPnl']) == 1000
    assert D(base['summary']['grossPnl']) == 1010
    assert sum(D(item['components'].get('ACCRUAL', '0')) for item in base['items']) == 10
    assert any(rule['code'] == 'BOND_MATURITY_REDEMPTION' for item in base['items'] for rule in item['evidence']['appliedRules'])
    account_preview = ok('POST', '/v1/valuation/cash-balance-preview', dict(strategyId=strategy, valueDate='2026-10-01',
        policyId=policy, cutId=cut, reportingCurrencyId=gbp))
    assert account_preview['scope'] == 'DATED_CASH_VALUE_ONLY'
    assert 'NOT_CASH_PNL' in account_preview['limitations']
    # Publication has no implicit permission waiver, even for the Ops admin.
    assert client.post(f"/v1/valuation/batches/{base['batch_id']}/publish", headers=ops,
        json={'comment': 'Mock self-review must fail'}).status_code == 403
    amendment = ok('POST', f"/v1/valuation/batches/{base['batch_id']}/amendments", dict(
        attributionId=base['items'][0]['attribution_id'], component='ADJUSTMENT', amount='-5',
        reason='Mock evidenced review adjustment', sourceReference='MOCK REVIEW NOTICE'), status=201)
    assert client.post(f"/v1/valuation/batches/{base['batch_id']}/publish", headers=review,
        json={'comment': 'Pending request must block publication'}).status_code == 409
    approved = ok('POST', f"/v1/valuation/amendments/{amendment['requestId']}/approve",
        {'comment': 'Independent mock review of adjustment evidence'}, actor=review)
    revised = approved['batch']
    assert approved['status'] == 'APPLIED' and revised['status'] == 'STAGED'
    assert D(revised['summary']['grossPnl']) == 1010 and D(revised['summary']['netPnl']) == 1005
    published = ok('POST', f"/v1/valuation/batches/{revised['batch_id']}/publish",
        {'comment': 'Independent mock publication'}, actor=review)
    assert published['status'] == 'PUBLISHED'
    frozen_summary, frozen_items = published['summary'], published['items']

    # Correct the closure using the supported lifecycle cancellation/rebooking
    # route, not a fabricated sale or direct update of an immutable trade.
    ok('POST', '/v1/lifecycle/bond-redemptions/cancel', dict(strategyId=strategy,
        postingId=posted['posting_id'], reason='Mock correction of maturity booking', confirmCancel=True))
    retained = ok('GET', '/v1/valuation/attempts/' + revised['attempt_id'])['batch']
    # Approved amendments retain their own attempt and predecessor lineage.
    assert retained['status'] == 'PUBLISHED' and retained['summary'] == frozen_summary
    assert retained['items'] == frozen_items
    assert retained['sourceHealth']['status'] == 'REASSESSMENT_REQUIRED'
    close_maturity()
    successor = ok('POST', '/v1/valuation/reassessments/recalculate', dict(batchIds=[revised['batch_id']],
        reason='Mock corrected maturity evidence', confirmRecalculation=True))['items'][0]
    assert successor['status'] == 'STAGED'
    assert D(successor['comparison']['new']['closingValue']) == 0
    assert D(successor['comparison']['new']['grossPnl']) == 1010
    assert D(successor['comparison']['new']['netPnl']) == 1010  # Manual -5 is not silently reapplied.
    assert successor['comparison']['old'] == frozen_summary
    successor_publication = ok('POST', f"/v1/valuation/batches/{successor['batchId']}/publish",
        {'comment': 'Independently reviewed corrected successor; prior -5 not reapplied'}, actor=review)
    assert successor_publication['status'] == 'PUBLISHED'
    old = ok('GET', '/v1/valuation/attempts/' + revised['attempt_id'])['batch']
    assert old['status'] == 'SUPERSEDED' and old['summary'] == frozen_summary and old['items'] == frozen_items
    print('Mock bond cycle passed: market=1000, interest=10, amended net=1005, successor net=1010; '
        'post-insert timestamp delta seconds=' + str(boundaries[-1]['newestTimestampMinusAsOfSeconds']))
