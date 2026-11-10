"""Selected assistance, subscription ceiling and approval mode are distinct."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m,access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from tests.test_lifecycle_entitlements import change


def configure(c,tier,event='BOND_MATURITY',strategy=None):
    from lifecycle.assistance import assistance_view,configure_assistance
    from lifecycle.assistance_contracts import AssistanceChange
    strategy=strategy or ids['strategy']
    group=am.save_group(c,TENANT,ACTOR,code='ASSIST_'+uuid4().hex,name='Synthetic lifecycle controller',actions=['LIFECYCLE_READ','LIFECYCLE_CONFIGURE','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','TRADE_WRITE'],scope_mode='ALL')
    c.execute(m.access_group_member.insert().values(tenant_id=TENANT,group_id=group,user_account_id=ACTOR))
    current=assistance_view(c,TENANT,ACTOR,strategy,event)
    return configure_assistance(c,TENANT,ACTOR,ACTOR,AssistanceChange(strategyId=strategy,eventType=event,selectedTier=tier,expectedRevision=current['assistanceRevision'],expectedSubscriptionRevision=current['subscriptionRevision'],reason='Synthetic assistance selection'))


@pytest.mark.parametrize('ceiling',range(4))
@pytest.mark.parametrize('selected',range(4))
def test_decision_does_not_clamp_selected_tier(ceiling,selected):
    from lifecycle.assistance import assistance_decision
    result=assistance_decision(ceiling,selected,'PREPARE','REVIEW')
    assert result['allowed']==(2<=selected<=ceiling)
    assert assistance_decision(ceiling,selected,'DIRECT','DIRECT')['allowed']==(selected==3 and ceiling==3)
    assert not assistance_decision(ceiling,selected,'DIRECT','REVIEW')['allowed']


def test_current_choice_is_retained_on_downgrade_and_requires_scope(connection):
    from lifecycle.assistance import assistance_view,require_assistance
    change(connection,3);selected=configure(connection,3)
    assert selected['selectedTier']==3
    change(connection,2)
    view=assistance_view(connection,TENANT,ACTOR,ids['strategy'],'BOND_MATURITY')
    assert view['selectedTier']==3 and view['maximumTier']==2 and view['status']=='BLOCKED_BY_SUBSCRIPTION'
    with pytest.raises(PermissionError):require_assistance(connection,TENANT,ACTOR,ids['strategy'],'BOND_MATURITY','PREPARE')
    with pytest.raises(PermissionError):assistance_view(connection,ids['second_tenant'],ACTOR,ids['strategy'],'BOND_MATURITY')
    assert configure(connection,1)['selectedTier']==1


def test_tier_two_can_confirm_but_cannot_book_direct_even_with_tier_three_subscription(connection):
    from lifecycle.assistance import require_assistance
    change(connection,3);configure(connection,2)
    from lifecycle.bond_service import configure as native_configure
    native_configure(connection,TENANT,ACTOR,ACTOR,ids['strategy'],'MANUAL',0,'Explicit operator-confirmation policy')
    assert require_assistance(connection,TENANT,ACTOR,ids['strategy'],'BOND_MATURITY','CONFIRM')['selectedTier']==2
    with pytest.raises(PermissionError):require_assistance(connection,TENANT,ACTOR,ids['strategy'],'BOND_MATURITY','DIRECT')
