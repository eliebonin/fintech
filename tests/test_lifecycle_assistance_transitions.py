"""Reviewed downgrade transitions never silently rewrite valid settings."""
import pytest
from sqlalchemy import select,func
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from tests.test_lifecycle_entitlements import change
from tests.test_lifecycle_assistance import configure
from security_master_schema import models as m
from lifecycle.entitlements import lifecycle_subscription_view


def setup(c):
    change(c,3)
    strategies=list(c.scalars(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==TENANT).order_by(m.strategy.c.strategy_id).limit(4)))
    assert len(strategies)==4
    for strategy,tier in zip(strategies,[3,2,1,0]):configure(c,tier,strategy=strategy)
    return strategies


@pytest.mark.parametrize('replacement,target,scope,expected',[
 ('HIGHEST_AVAILABLE',None,'ABOVE_NEW_CEILING',[2,2,1,0]),
 ('EXPLICIT',1,'ABOVE_NEW_CEILING',[1,2,1,0]),
 ('EXPLICIT',0,'ALL_CONFIGURED',[0,0,0,0]),
 ('EXPLICIT',2,'ALL_CONFIGURED',[2,2,2,2]),
])
def test_reviewed_replacement_uses_full_current_population(connection,replacement,target,scope,expected):
    from lifecycle.assistance_transitions import preview_assistance_transition,apply_assistance_transition
    from lifecycle.assistance_contracts import TransitionPreview,TransitionApply
    from lifecycle.entitlements import current_selections
    strategies=setup(connection)
    request=TransitionPreview(proposedMaximumTier=2,expectedSubscriptionRevision=lifecycle_subscription_view(connection,TENANT)['revision'],scope=scope,replacement=replacement,targetTier=target)
    preview=preview_assistance_transition(connection,TENANT,ACTOR,request)
    apply_assistance_transition(connection,TENANT,ACTOR,ACTOR,TransitionApply(**request.model_dump(),inputHash=preview['inputHash'],reason='Reviewed synthetic downgrade',confirmChange=True,confirmReplaceAllowed=scope=='ALL_CONFIGURED'))
    rows={r['strategy_id']:r['selected_tier'] for r in connection.execute(current_selections(connection,TENANT)).mappings()}
    assert [rows[s] for s in strategies]==expected
    assert connection.scalar(select(func.max(m.tenant_lifecycle_subscription.c.revision)).where(m.tenant_lifecycle_subscription.c.tenant_id==TENANT))==request.expectedSubscriptionRevision


def test_stale_transition_is_atomic_and_reset_requires_confirmation(connection):
    from lifecycle.assistance_transitions import preview_assistance_transition,apply_assistance_transition
    from lifecycle.assistance_contracts import TransitionPreview,TransitionApply
    strategies=setup(connection)
    request=TransitionPreview(proposedMaximumTier=2,expectedSubscriptionRevision=lifecycle_subscription_view(connection,TENANT)['revision'],scope='ALL_CONFIGURED',replacement='EXPLICIT',targetTier=0)
    preview=preview_assistance_transition(connection,TENANT,ACTOR,request)
    payload=dict(**request.model_dump(),inputHash=preview['inputHash'],reason='Synthetic reset',confirmChange=True)
    with pytest.raises(ValueError,match='confirm|Confirm'):apply_assistance_transition(connection,TENANT,ACTOR,ACTOR,TransitionApply(**payload))
    configure(connection,1,strategy=strategies[0])
    before=connection.scalar(select(func.count()).select_from(m.strategy_lifecycle_assistance))
    with pytest.raises(ValueError,match='changed|review'):apply_assistance_transition(connection,TENANT,ACTOR,ACTOR,TransitionApply(**payload,confirmReplaceAllowed=True))
    assert connection.scalar(select(func.count()).select_from(m.strategy_lifecycle_assistance))==before


def test_selected_scope_preserves_valid_lower_choices_and_keep_is_preview_only(connection):
    from lifecycle.assistance_transitions import preview_assistance_transition,apply_assistance_transition
    from lifecycle.assistance_contracts import TransitionPreview,TransitionApply
    strategies=setup(connection)
    revision=lifecycle_subscription_view(connection,TENANT)['revision']
    request=TransitionPreview(proposedMaximumTier=2,expectedSubscriptionRevision=revision,scope='SELECTED',replacement='EXPLICIT',targetTier=1,targets=[(strategies[0],'BOND_MATURITY'),(strategies[1],'BOND_MATURITY')])
    preview=preview_assistance_transition(connection,TENANT,ACTOR,request)
    assert [(r['beforeTier'],r['afterTier']) for r in preview['items']]==[(3,1),(2,2)]
    keep=request.model_copy(update={'replacement':'KEEP','targetTier':None})
    preview=preview_assistance_transition(connection,TENANT,ACTOR,keep)
    assert preview['changedCount']==0 and preview['blockedCount']==1
    with pytest.raises(ValueError,match='preview-only'):
        apply_assistance_transition(connection,TENANT,ACTOR,ACTOR,TransitionApply(**keep.model_dump(),inputHash=preview['inputHash'],reason='Keep choices',confirmChange=True))


def test_transition_covers_population_beyond_loaded_strategy_page(connection):
    from uuid import uuid4
    from lifecycle.assistance import assistance_options,append_selection
    from lifecycle.assistance_transitions import preview_assistance_transition
    from lifecycle.assistance_contracts import TransitionPreview
    setup(connection)
    for number in range(31):
        identity=uuid4()
        connection.execute(m.strategy.insert().values(strategy_id=identity,tenant_id=TENANT,strategy_code='POP_'+identity.hex,display_name=f'Population strategy {number}',strategy_type='FUND'))
        append_selection(connection,TENANT,ACTOR,ACTOR,identity,'BOND_MATURITY',3,0,'Synthetic population setting')
    page=assistance_options(connection,TENANT,ACTOR,limit=25)
    assert len(page['items'])==25 and page['total']>=35
    preview=preview_assistance_transition(connection,TENANT,ACTOR,TransitionPreview(proposedMaximumTier=2,expectedSubscriptionRevision=lifecycle_subscription_view(connection,TENANT)['revision']))
    assert len(preview['items'])==35 and preview['changedCount']==32
