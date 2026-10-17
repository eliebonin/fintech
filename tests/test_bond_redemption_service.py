from datetime import date
from decimal import Decimal as D
from uuid import uuid4,UUID
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from security_master_schema import models as m,access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids


def setup(c,r,trade):
    maturity=r.closing_cutoff.date()
    booked=add_bond(c,r,trade,maturity.isoformat())
    listing=c.scalar(select(m.trade.c.trade_subject_reference_node_id).where(m.trade.c.trade_id==booked))
    c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==ids['bond_instrument_node']).values(maturity_date=maturity))
    actions=['LIFECYCLE_READ','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','LIFECYCLE_CONFIGURE','TRADE_WRITE','TRADE_CORRECT']
    group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='REDEEM_'+uuid4().hex,name='Synthetic redemption Ops',actions=actions,scope_mode='SELECTED',strategy_ids=[r.strategy_id])
    # Existing user groups preserved; this grant exists only in rollback fixture.
    c.execute(m.access_group_member.insert().values(tenant_id=r.tenant_id,group_id=group,user_account_id=ids['demo_user_account']))
    return listing,booked,group


def test_direct_maturity_books_current_nominal_once_and_replays_to_zero(valued):
    from lifecycle.bond_service import candidate,configure,post,RedemptionConflict
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    c,r,trade=valued;listing,booked,group=setup(c,r,trade)
    configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct processing')
    data,fingerprint,projection,_=candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    assert data['movements'][0]['quantity']=='-100000.000000000000'
    assert D(data['movements'][0]['price'])==100
    key=str(uuid4());posted=post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,key)
    assert len(posted['trade_ids'])==1
    closing=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(posted['trade_ids'][0]))).mappings().one()
    assert closing['trade_type']=='MATURITY_REDEMPTION' and closing['quantity']==D(-100000)
    assert closing['settlement_date'] is None
    check=reconstruct(tuple(iter_ledger_facts(c,projection.request,subject_ids=[listing])),projection.request)
    assert not check.buckets
    assert post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,key)['trade_ids']==posted['trade_ids']
    with pytest.raises(RedemptionConflict): candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    from lifecycle.bond_service import cancel
    cancellation=cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(posted['posting_id']),'Erroneous principal record',str(uuid4()))
    assert cancellation['evidence']['operation']=='CANCEL'
    reopened,_,_,_=candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    assert D(reopened['movements'][0]['quantity'])==-100000


def test_review_default_and_independent_approval_revalidate_terms(valued):
    from lifecycle.bond_service import candidate,prepare,post,RedemptionConflict
    c,r,trade=valued;listing,booked,group=setup(c,r,trade)
    data,fingerprint,_,_=candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    with pytest.raises(ValueError,match='direct booking'): post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()))
    prepared=prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint)
    assert prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint)['proposalId']==prepared['proposalId']
    with pytest.raises(PermissionError): post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()),proposal_id=UUID(prepared['proposalId']))
    reviewer=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Independent maturity reviewer')
    am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],reviewer,[group])
    c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(redemption_amount_per_par=101))
    with pytest.raises(RedemptionConflict): post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()),proposal_id=UUID(prepared['proposalId']))
    c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(redemption_amount_per_par=100))
    result=post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()),proposal_id=UUID(prepared['proposalId']))
    assert result['evidence']['authority']['operation']=='APPROVE'
    assert result['actor_id']==str(reviewer)
