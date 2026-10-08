"""Bound JSON bodies before parsing or opening a domain transaction."""
from starlette.requests import Request
from .problem_details import _problem_response
from datetime import datetime,timezone
from sqlalchemy import select,func


def configure_transaction_budget(connection,settings):
    for name,value in [('statement_timeout',settings.statement_timeout_ms),('lock_timeout',settings.lock_timeout_ms)]:
        connection.execute(select(func.set_config(name,str(value),True)))


def governance_date(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()


class RequestBodyBudget:
    def __init__(self, app, *, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > self.max_bytes:
                response = _problem_response(Request(scope), status_code=413,
                    code='request.too_large', title='Request too large',
                    detail='The request body exceeds the configured size limit.', type_slug='request-too-large')
                return await response(scope, receive, send)
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)
