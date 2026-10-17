"""HTTP acceptance companion; requires the owned synthetic server on 8009."""
import sys
from uuid import uuid4
from decimal import Decimal
import httpx

TENANT = '00000000-0000-7000-8000-000000000011'
ACTOR = '00000000-0000-7000-8000-000000000083'
INSTRUMENT = '00000000-0000-7000-8000-000000000055'
POLICY = '00000000-0000-7000-8000-000000000035'
CUT = '00000000-0000-7000-8000-000000000029'
USD = '00000000-0000-7000-8000-000000000087'


def main(strategy, reviewer):
    client = httpx.Client(base_url='http://127.0.0.1:8009', timeout=45)
    def request(method, path, body=None, actor=ACTOR, expected=200, key=None):
        response = client.request(method, path, json=body, headers={'X-Tenant-Id': TENANT, 'X-User-Account-Id': actor, 'Idempotency-Key': key or str(uuid4())})
        assert response.status_code == expected, (path, response.status_code, response.text)
        return response.json()
    options = request('GET', '/v1/valuation/options')
    assert any(s['id'] == strategy and s['label'] == 'SYNTHETIC FX Forward E2E' for s in options['strategies'])
    runs = request('GET', f'/v1/valuation/attempts?strategy_id={strategy}')['items']
    assert len(runs) == 1 and runs[0]['batch_status'] == 'STAGED', runs
    run = request('GET', '/v1/valuation/attempts/' + runs[0]['attempt_id'])
    batch = run['batch']; batch_id = batch['batch_id']
    assert Decimal(batch['summary']['marketPnl']) == 10000
    request('POST', f'/v1/valuation/batches/{batch_id}/publish', {'comment': 'Synthetic self-review must fail'}, expected=409)
    change = request('POST', f'/v1/valuation/batches/{batch_id}/amendments', {'attributionId': batch['items'][0]['attribution_id'], 'component': 'OTHER_COST', 'amount': '-10', 'reason': 'Synthetic reviewed fee', 'sourceReference': 'SYNTHETIC FEE'}, expected=201)
    request('POST', '/v1/valuation/amendments/' + change['requestId'] + '/approve', {'comment': 'Self-approval must fail'}, expected=403)
    applied = request('POST', '/v1/valuation/amendments/' + change['requestId'] + '/approve', {'comment': 'Synthetic independent fee review'}, actor=reviewer)
    revised = applied['batch']; assert Decimal(revised['summary']['netPnl']) == 9990
    published = request('POST', '/v1/valuation/batches/' + revised['batch_id'] + '/publish', {'comment': 'Synthetic independent result review'}, actor=reviewer)
    assert published['status'] == 'PUBLISHED'
    print('PASS: browser-created 10000 USD; self-publication and self-amendment denied; independent amended publication 9990 USD', flush=True)
    target = {'strategyId': strategy, 'instrumentId': INSTRUMENT}
    request('POST', '/v1/lifecycle/fx-forward/policy', {'strategyId': strategy, 'mode': 'DIRECT', 'expectedRevision': 0, 'reason': 'Synthetic maturity check', 'confirmChange': True, 'pricingPolicyId': POLICY, 'pricingCutId': CUT})
    override = {'rate': '1.125', 'sourceReference': 'SYNTHETIC COUNTERPARTY CONFIRMATION', 'reason': 'Synthetic accurate final rate'}
    preview = request('POST', '/v1/lifecycle/fx-forward/closures/preview', target | {'rateOverride': override})
    assert Decimal(preview['inputs']['suggestedPrice']) == Decimal('1.12')
    assert Decimal(preview['inputs']['price']) == Decimal('1.125')
    key = str(uuid4()); body = target | {'rateOverride': override, 'expectedFingerprint': preview['inputHash'], 'confirmBooking': True}
    posted = request('POST', '/v1/lifecycle/fx-forward/closures/book', body, expected=201, key=key)
    duplicate = request('POST', '/v1/lifecycle/fx-forward/closures/book', body, expected=201, key=key)
    assert posted['trade_ids'] == duplicate['trade_ids']
    result = request('POST', '/v1/valuation/attempts', {'strategyId': strategy, 'policyId': POLICY, 'cutId': CUT, 'reportingCurrencyId': USD, 'openingDate': '2026-09-30', 'closingDate': '2026-10-01'}, expected=201)
    assert Decimal(result['batch']['summary']['marketPnl']) == 15000, result
    assert Decimal(result['batch']['summary']['closingValue']) == 0, result
    print('PASS: maturity suggested 1.12; sourced override 1.125; idempotent closure; maturity-day P&L 15000 USD', flush=True)
    print('MATURITY_ATTEMPT=' + result['attempt']['attempt_id'], flush=True)
    client.close()


if __name__ == '__main__':
    main(*sys.argv[1:])
