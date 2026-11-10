"""Canonical party allocations close separately without fake catalogue identities."""
from uuid import uuid4
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup
from tests.test_lifecycle_allocation_store import clone_execution
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,current_assignment
from lifecycle import bond_service as svc


def test_bond_maturity_preserves_standard_counterparty_allocations(valued):
    c,r,trade=valued;listing,original,_=setup(c,r,trade);other=clone_execution(c,original)
    parties=c.execute(select(m.organisation.c.organisation_id).where(m.organisation.c.status=='ACTIVE').order_by(m.organisation.c.organisation_id).limit(2)).scalars().all()
    c.execute(m.trade_party_role.insert().values(trade_id=trade,organisation_id=parties[0],role='COUNTERPARTY'))
    for identity,party in zip([original,other],parties):c.execute(m.trade_party_role.insert().values(trade_id=identity,organisation_id=party,role='COUNTERPARTY'))
    profile=create_profile(c,r.tenant_id,ids['demo_user_account'],'PARTY_'+uuid4().hex,'Party allocations','Synthetic fixture')
    version=publish_profile_version(c,r.tenant_id,ids['demo_user_account'],profile['profileId'],dict(label='Party allocations',reason='Synthetic fixture',expectedVersion=0,fields=[dict(standardFieldKey='COUNTERPARTY',requirement='REQUIRED',lifecycleBehavior='ALLOCATION')]))
    assign_profile(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,version['versionId'],current_assignment(c,r.tenant_id,r.strategy_id)['revision'],'Explicit allocation strategy')
    data,_,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id==listing)))
    assert len(data['movements'])==2 and data['annotationStatus']=='READY'
    assert {m['standardInputs']['COUNTERPARTY'] for m in data['movements']}==set(map(str,parties))
    assert all(m['properties']==[] for m in data['movements'])
    assert all(m['annotationFields'][0]['displayValue'] for m in data['movements'])
    from security_master_schema.evidence import evidence_hash
    instrument=c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id==listing))
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['platform_admin_user_account'],r.strategy_id,'DIRECT',0,'Synthetic one-click mode')
    data,digest,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['platform_admin_user_account'],r.strategy_id,instrument,digest,str(uuid4()))
    from uuid import UUID
    closed=[UUID(t) for t in posted['trade_ids']]
    roles=c.execute(select(m.trade_party_role.c.organisation_id).where(m.trade_party_role.c.trade_id.in_(closed),m.trade_party_role.c.role=='COUNTERPARTY')).scalars().all()
    assert set(roles)==set(parties)
    assert set(c.execute(select(m.trade.c.trade_profile_version_id).where(m.trade.c.trade_id.in_(closed))).scalars())=={version['versionId']}
