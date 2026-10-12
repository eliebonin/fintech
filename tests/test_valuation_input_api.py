from uuid import uuid4
from tests.test_composite_policy_api import call
from security_master_schema.demo_data import DEMO_IDS as ids


def payload():
    return dict(strategyId=str(ids['strategy']),instrumentId=str(ids['bond_instrument_node']),valueDate='2026-10-01',
        policyId=str(ids['valuation_policy']),cutId=str(ids['valuation_cut']),reportingCurrencyId=str(ids['gbp_currency']),
        openingBalance='990',dailyEarned='10',closingBalance='0',balanceMovements='-1000',eligibleNominal='100000',
        sourceReference='SYNTHETIC COUPON',eligibilityConvention='OPS_ASSESSED_NOMINAL')


def test_input_api_records_validated_local_and_base_daily_values_and_replays_key():
    key=str(uuid4());data=payload()
    response=call('POST','/v1/valuation/accrual-inputs',data,key)
    assert response.status_code==201,response.text
    assert response.json()['payload']['amounts']['dailyBase']=='10'
    assert response.json()['payload']['amounts']['balanceBase']=='0'
    again=call('POST','/v1/valuation/accrual-inputs',data,key)
    assert again.status_code==201,again.text
    assert again.json()['input_id']==response.json()['input_id']
    data['dailyEarned']='11';data['closingBalance']='1'
    assert call('POST','/v1/valuation/accrual-inputs',data,key).status_code==409


def test_input_api_rejects_bad_balance_and_unavailable_strategy():
    data=payload();data['closingBalance']='1'
    assert call('POST','/v1/valuation/accrual-inputs',data).status_code==422
    data=payload();data['strategyId']=str(uuid4())
    assert call('POST','/v1/valuation/accrual-inputs',data).status_code==404
