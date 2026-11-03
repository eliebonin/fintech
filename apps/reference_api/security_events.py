"""Safe denial evidence independent of financial/database transaction rollback."""
import json
import logging
import re
from datetime import datetime,timezone
from starlette.routing import Match

LOGGER=logging.getLogger('apps.reference_api.security')


def record_denial(request,status):
    route=getattr(request.scope.get('route'),'path',None)
    if not route:
        for candidate in request.app.routes:
            if candidate.matches(request.scope)[0] is Match.FULL:
                route=getattr(candidate,'path',None)
                break
    actor=getattr(request.state,'actor_context',None)
    tenant=getattr(request.state,'tenant_context',None)
    code=getattr(request.state,'security_reason',None)
    if not isinstance(code,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}',code):
        code='authentication.required' if status==401 else 'authorization.forbidden'
    event={'event':'access_denied','timestamp':datetime.now(timezone.utc).isoformat(),
        'requestId':request.state.request_id,'method':request.method,'route':route or '<unmatched>',
        'status':status,'reason':code,'identitySource':actor.source if actor else None,
        'actorId':str(getattr(request.state,'real_actor_id',actor.user_account_id)) if actor else None,
        'subjectId':str(actor.user_account_id) if actor else None,
        'tenantId':str(tenant.tenant_id) if tenant else None}
    # No raw path/query, headers, cookies, tokens, request body or exception text.
    LOGGER.warning(json.dumps(event,separators=(',',':'),ensure_ascii=True))
