"""Two-connection changes cannot mix financial reads or bypass current rights."""
from sqlalchemy import update
from tests.api_client import FixtureTestClient as TestClient
from tests.test_valuation_service import valued
from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from apps.reference_api import strategy_workspace as workspace
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
import os
from sqlalchemy import create_engine


def test_release_check_does_not_require_two_simultaneous_pool_connections(valued):
    c,r,_=valued;c.commit()
    engine=create_engine(os.environ['DATABASE_URL'],pool_size=1,max_overflow=0,pool_timeout=0.2)
    try:
        with TestClient(create_app(engine=engine),raise_server_exceptions=False) as client:
            result=client.get(f'/v1/strategies/{r.strategy_id}/measures',params={
                'asOf':r.closing_cutoff.date().isoformat(),'policyId':str(r.policy_id)},headers={
                'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])})
        assert result.status_code==200,result.text
        assert result.json()['items'][0]['measures']['marketValue']['localAmount']=='110'
    finally:engine.dispose()


def test_preview_keeps_one_financial_snapshot_when_observation_is_retracted(valued,monkeypatch):
    c,r,_=valued;c.commit()
    engine=get_engine();original=workspace.snapshot
    def interleave(*args,**kw):
        result=original(*args,**kw)
        with engine.begin() as writer:
            writer.execute(update(m.market_data_observation).where(
                m.market_data_observation.c.market_data_series_id==ids['market_data_series'],
                m.market_data_observation.c.market_date==r.closing_cutoff.date()).values(quality_status='REJECTED'))
        return result
    monkeypatch.setattr(workspace,'snapshot',interleave)
    with TestClient(create_app(engine=engine)) as client:
        result=client.get(f'/v1/strategies/{r.strategy_id}/measures',params={
            'asOf':r.closing_cutoff.date().isoformat(),'policyId':str(r.policy_id)},headers={
            'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])})
    assert result.status_code==200,result.text
    assert result.json()['items'][0]['measures']['marketValue']['localAmount']=='110'


def test_preview_rechecks_current_rights_after_snapshot_selection(valued,monkeypatch):
    c,r,_=valued;c.commit()
    engine=get_engine();original=workspace.snapshot
    def interleave(*args,**kw):
        result=original(*args,**kw)
        with engine.begin() as writer:
            writer.execute(update(m.tenant_dataset_entitlement).where(
                m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
                m.tenant_dataset_entitlement.c.dataset_id==ids['dataset']).values(status='INACTIVE'))
        return result
    monkeypatch.setattr(workspace,'snapshot',interleave)
    try:
        with TestClient(create_app(engine=engine)) as client:
            result=client.get(f'/v1/strategies/{r.strategy_id}/measures',params={
                'asOf':r.closing_cutoff.date().isoformat(),'policyId':str(r.policy_id)},headers={
                'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])})
        assert result.status_code==403,result.text
        assert 'localAmount' not in result.text
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(update(m.tenant_dataset_entitlement).where(
                m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
                m.tenant_dataset_entitlement.c.dataset_id==ids['dataset']).values(status='ACTIVE'))
