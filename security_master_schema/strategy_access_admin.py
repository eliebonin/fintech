"""Tenant-admin access matrix and transactional, non-persisting group impact preview."""
from . import access_management as am
from .strategy_access import SCOPED_ACTIONS
from .access_control import effective_permissions
import hashlib,json


def access_fingerprint(view):
    def normalize(value):
        if isinstance(value,dict): return {key:normalize(child) for key,child in value.items()}
        if isinstance(value,list): return sorted((normalize(child) for child in value),key=lambda child:json.dumps(child,sort_keys=True))
        return value
    return hashlib.sha256(json.dumps(normalize(view),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def access_rows(view):
    rows=[]
    for user in view['users']:
        groups=[g for g in view['groups'] if g['groupId'] in user['groupIds'] and g['status']=='ACTIVE']
        permissions=effective_permissions(role=user['role'],tenant_modules=view['tenantModuleCodes'],
            grants={code for group in groups for code in group['actions']})
        for strategy in view['strategies']:
            grants={code:sorted({g['name'] for g in groups if code in g['actions'] and
                (g['scopeMode']=='ALL' or strategy['strategyId'] in g['strategyIds'])}) for code in sorted(SCOPED_ACTIONS)}
            allowed={code:sources for code,sources in grants.items() if sources and code in permissions and
                user['status']=='ACTIVE' and user['accountStatus']=='ACTIVE'}
            rows.append(dict(userId=user['userId'],name=user['name'],strategyId=strategy['strategyId'],
                strategyName=strategy['name'],actions=sorted(allowed),grantSources=allowed))
    return rows


def matrix(c,tenant,actor,strategy=None):
    view=am.tenant_access_view(c,tenant,actor)
    if strategy and str(strategy) not in {s['strategyId'] for s in view['strategies']}:
        raise am.TenantActionForbidden('Strategy is outside this tenant')
    return dict(strategies=view['strategies'],rows=[row for row in access_rows(view) if not strategy or row['strategyId']==str(strategy)])


def preview(c,tenant,actor,payload):
    before=am.tenant_access_view(c,tenant,actor)
    savepoint=c.begin_nested()
    try:
        am.save_group(c,tenant,actor,code=payload.code,name=payload.name,description=payload.description,
            status=payload.status,actions=payload.actions,group_id=payload.groupId,scope_mode=payload.scopeMode,
            strategy_ids=payload.strategyIds,expected_version=payload.expectedVersion)
        after=am.tenant_access_view(c,tenant,actor)
    finally: savepoint.rollback()
    prior={(row['userId'],row['strategyId']):set(row['actions']) for row in access_rows(before)}
    changes=[]
    for row in access_rows(after):
        previous=prior[(row['userId'],row['strategyId'])]
        added=sorted(set(row['actions'])-previous);removed=sorted(previous-set(row['actions']))
        if added or removed: changes.append(dict(userId=row['userId'],name=row['name'],strategyId=row['strategyId'],
            strategyName=row['strategyName'],added=added,removed=removed))
    previous_users={user['userId']:set(user['permissions'])-SCOPED_ACTIONS for user in before['users']}
    global_changes=[]
    for user in after['users']:
        current=set(user['permissions'])-SCOPED_ACTIONS;prior=previous_users[user['userId']]
        if current!=prior: global_changes.append(dict(name=user['name'],added=sorted(current-prior),removed=sorted(prior-current)))
    return dict(changes=changes,globalChanges=global_changes,impactHash=access_fingerprint(before),includesFutureStrategies=payload.scopeMode=='ALL',
        unassignedNewGroup=payload.groupId is None,expectedVersion=payload.expectedVersion)
