from datetime import datetime,timedelta,timezone
from apps.reference_api.access_boundary import required_action
from security_master_schema.access_control import effective_permissions
from security_master_schema.strategy_access import SCOPED_ACTIONS

def test_self_publication_is_an_explicit_scoped_action_not_an_admin_default():
    assert 'VALUATION_SELF_PUBLISH' in SCOPED_ACTIONS
    assert 'VALUATION_SELF_PUBLISH' not in effective_permissions(role='TENANT_ADMIN',tenant_modules=['VALUATION'],grants=[])
    assert 'VALUATION_SELF_PUBLISH' in effective_permissions(role='MEMBER',tenant_modules=['VALUATION'],grants=['VALUATION_SELF_PUBLISH'])
    assert required_action('/v1/valuation/batches/id/self-publish','POST')=='VALUATION_SELF_PUBLISH'
    assert required_action('/v1/valuation/amendments/id/approve','POST')=='VALUATION_REVIEW'

def test_opt_in_expiry_does_not_default_to_self_publication():
    from valuation.self_publication import policy_active
    now=datetime(2026,10,14,tzinfo=timezone.utc)
    assert not policy_active(None,now)
    assert not policy_active({'enabled':False,'valid_until':None},now)
    assert policy_active({'enabled':True,'valid_until':None},now)
    assert policy_active({'enabled':True,'valid_until':now+timedelta(hours=1)},now)
    assert not policy_active({'enabled':True,'valid_until':now},now)
