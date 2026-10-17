"""Permission foundation for Ops-triggered lifecycle processing, not posting.

Future handlers must obtain mode and preparer ancestry from retained server-side
records, and real_operator from authenticated request context. This module neither
creates ledger entries nor enables a workflow/configuration endpoint.
"""
from uuid import UUID
from .strategy_access import require_strategy_action

MODES=frozenset({'DIRECT','REVIEW','MANUAL'})


def required_permissions(operation,mode):
    if mode not in MODES: raise ValueError('Unsupported lifecycle processing mode')
    permissions={'READ':('LIFECYCLE_READ',),'PREPARE':('LIFECYCLE_PREPARE',),
        'BOOK':('LIFECYCLE_BOOK','TRADE_WRITE'),'APPROVE':('LIFECYCLE_APPROVE','TRADE_WRITE'),
        'CONFIGURE':('LIFECYCLE_CONFIGURE',),'CORRECT':('TRADE_CORRECT',)}
    if operation not in permissions: raise ValueError('Unknown lifecycle operation')
    if operation=='BOOK' and mode=='REVIEW': raise ValueError('Review-required entries cannot use direct booking')
    if operation=='APPROVE' and mode!='REVIEW': raise ValueError('Approval applies only to review-required entries')
    return permissions[operation]


def assert_independent_review(actor,real_operator,prepared_by,prepared_operator):
    if any(identity is None for identity in (actor,real_operator,prepared_by,prepared_operator)):
        raise PermissionError('Complete selected-user and real-operator preparation ancestry required')
    try: actor,real_operator,prepared_by,prepared_operator=[UUID(str(value)) for value in (actor,real_operator,prepared_by,prepared_operator)]
    except (ValueError,TypeError,AttributeError) as exc: raise PermissionError('Invalid lifecycle reviewer/preparer identity') from exc
    if {actor,real_operator}&{prepared_by,prepared_operator}:
        raise PermissionError('Lifecycle approval requires an independent selected user and real operator')


def require_lifecycle_operation(c,tenant,actor,strategy,operation,mode,*,real_operator=None,
                              prepared_by=None,prepared_operator=None):
    permissions=required_permissions(operation,mode)
    for permission in permissions: require_strategy_action(c,tenant,actor,permission,strategy)
    operator=real_operator if real_operator is not None else actor
    if operation=='APPROVE': assert_independent_review(actor,operator,prepared_by,prepared_operator)
    # The posting/configuration transaction must retain this proof alongside its
    # concrete event/input version and financial decisions; it is not an approval.
    return dict(tenantId=str(tenant),strategyId=str(strategy),actorId=str(actor),
        realOperatorId=str(operator),operation=operation,mode=mode,permissions=list(permissions))
