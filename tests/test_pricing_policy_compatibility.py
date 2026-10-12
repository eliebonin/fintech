"""Setup checks must distinguish price semantics and permissions without writes."""
from uuid import uuid4
from sqlalchemy import select,func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_composite_policy_api import call,policy_payload
from tests.test_valuation_service import valued,service


def test_metadata_catalogue_explains_actual_series_and_recorded_permissions():
    response=call('GET','/v1/market-data/policy-data-options')
    assert response.status_code==200,response.text
    data=response.json()
    assert data['sources']
    assert any(p['seriesType']=='CLOSE' and p['closingMethod']=='EXCHANGE_OFFICIAL' for source in data['sources'] for p in source['priceProfiles'])
    assert 'nonDisplayAllowed' in data['sources'][0]
    assert 'evidence_reference' not in response.text


def test_unsaved_check_reports_series_mismatch_and_never_creates_policy():
    payload=policy_payload();payload['rules'][0].update(seriesType='NO_SUCH_PRICE',valueBasis='RAW')
    with get_engine().connect() as c:
        before=c.scalar(select(func.count()).select_from(m.valuation_policy))
    response=call('POST','/v1/market-data/policy-compatibility',payload)
    assert response.status_code==200,response.text
    assert response.json()['status']=='ACTION_REQUIRED'
    assert 'PRICE_NOT_AVAILABLE' in [issue['code'] for issue in response.json()['rules'][0]['issues']]
    with get_engine().connect() as c:
        assert c.scalar(select(func.count()).select_from(m.valuation_policy))==before


def test_cross_tenant_subject_is_not_disclosed_by_setup_check():
    payload=policy_payload();payload['rules'][0]['subjectReferenceNodeId']=str(uuid4())
    response=call('POST','/v1/market-data/policy-compatibility',payload)
    assert response.status_code==422,response.text


def test_vendor_close_label_is_not_rejected_when_economics_are_unadjusted(valued):
    c,request,_=valued
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['market_data_series']).values(series_type='CLOSE'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(series_type='CLOSE'))
    assert service().calculate(c,request).period.market_pnl>0


def test_failed_input_identifies_instrument_date_and_expected_basis(valued):
    import pytest
    from datetime import date
    c,request,_=valued
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_date==date(2026,10,1)))
    with pytest.raises(service().ValuationBlocked) as error:
        service().calculate(c,request)
    message=str(error.value)
    assert '2026-10-01' in message and 'RAW' in message
    assert 'HSBA' in message or str(ids['hsbc_xlon_listing_node']) in message


def test_reporting_permission_is_not_valuation_permission():
    from apps.reference_api.valuation_policy_contracts import PolicyCreate
    from apps.reference_api.valuation_policies import compatibility
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset=c.scalar(select(m.market_data_observation.c.dataset_id).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation']))
            c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'],
                m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION').values(use_purpose='INTERNAL_REPORTING'))
            payload=policy_payload();payload['rules'][0].update(valueBasis='RAW',datasetId=str(dataset))
            report=compatibility(c,ids['tenant'],ids['demo_user_account'],PolicyCreate.model_validate(payload))
            assert report['status']=='ACTION_REQUIRED'
            assert report['rules'][0]['matchingSeriesCount']>0
            assert report['rules'][0]['eligibleSeriesCount']==0
            assert 'VALUATION_USE_NOT_GRANTED' in [i['code'] for i in report['rules'][0]['issues']]
        finally:tx.rollback()


def test_inventory_preserves_per_series_package_permissions():
    from tests.test_dataset_coverage import setup_coverage
    from market_data.policy_compatibility import profile_rows
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,_,series,_,entitlements=setup_coverage(c)
            c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id==entitlements['INTERNAL_REPORTING']).values(coverage_mode='DATASET'))
            rows=[r for r in profile_rows(c,ids['tenant']) if r['dataset_id']==dataset]
            assert {r['market_data_series_id'] for r in rows}=={s['market_data_series_id'] for s in series}
            assert {r['market_data_series_id'] for r in rows if r['valuation_allowed']}=={series[0]['market_data_series_id']}
        finally:tx.rollback()
