"""Transport uses the same domain approval and verified real-operator lineage."""
from uuid import uuid4
from tests.api_client import ConnectionEngine,FixtureTestClient
from tests.test_valuation_service import valued
from tests.test_reviewed_mark_overrides import setup_missing,authorized_reviewer
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS as ids


def test_manual_mark_routes_preserve_scope_decimal_and_real_operator_independence(valued):
    c,r,_=valued;payload,batch=setup_missing(c,r);actor=authorized_reviewer(c)
    app=create_app(engine=ConnectionEngine(c))
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':str(uuid4())}
    with FixtureTestClient(app) as client:
        response=client.post('/v1/valuation/mark-overrides',json=payload.model_dump(mode='json',by_alias=True),headers=headers)
        assert response.status_code==201,response.text
        identity=response.json()['requestId']
        response=client.get(f'/v1/valuation/batches/{batch}/mark-overrides',headers=headers)
        assert response.status_code==200,response.text
        row=response.json()['requests'][0]
        assert row['value']=='1200.000000000001' and row['status']=='PENDING' and row['canReview'] is False
        response=client.post(f'/v1/valuation/mark-overrides/{identity}/approve',json={'comment':'Same real operator switching users'},
            headers=headers|{'X-User-Account-Id':str(actor)})
        assert response.status_code==403,response.text
        response=client.get(f'/v1/valuation/batches/{uuid4()}/mark-overrides',headers=headers)
        assert response.status_code==404,response.text
