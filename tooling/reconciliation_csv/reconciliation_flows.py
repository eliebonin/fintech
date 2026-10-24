"""Date-specific RESET income from explicit known source references only."""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal


def mapped_flows(bundle,nodes):
    known=[];blocked=[]
    for row in bundle.flows:
        reference=source_id(row.get('reference_instrument_id'))
        if reference in nodes:known.append((row,nodes[reference]))
        else:blocked.append(dict(sourceTradeId=row['trade_id'],sourceReferenceId=reference or None,
            status='NOT_POSTED',reason='MISSING_REFERENCE' if not reference else 'REFERENCE_NOT_IN_IMPORTED_UNIVERSE'))
    return known,blocked


def post_flows(c,bundle,tenant,actor,foundation,*,nodes=None):
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.booking_controls import authorize_booking
    from security_master_schema.access_management import audit
    from valuation.flows import book_flow
    authorize_booking(c,tenant,actor,strategy_id=foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':trades'))
    if not payload:raise ValueError('Owned retained flow source required')
    if nodes is None:
        nodes={}
        for details in c.execute(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action=='RECONCILIATION_PRODUCTS_SEEDED',
            m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
            m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)).scalars():
            for key,value in details['swaps'].items():
                if key in nodes and nodes[key]!=UUID(value):raise ValueError('Ambiguous source reset reference')
                nodes[key]=UUID(value)
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    known,blocked=mapped_flows(bundle,nodes);posted=[]
    for row,node in known:
        with c.begin_nested():
            # A direct private node map must not adopt another tenant's instrument.
            c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
                m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',
                m.reference_node_scope.c.status=='ACTIVE')).one()
            if row.get('price') and Decimal(row['price'])!=1:raise ValueError('RESET must be a dated currency amount at price one')
            if row.get('active','True')!='True':raise ValueError('Inactive source RESET')
            amount=native_decimal(row['quantity'])
            if Decimal(amount['value'])==0:raise ValueError('Zero RESET needs separate coverage evidence, not a synthetic flow booking')
            key='recon-reset:'+sha256(document(dict(source=str(foundation['sourceId']),trade=row['trade_id']))).hexdigest()
            identity=book_flow(c,tenant,actor,dict(strategyId=foundation['strategyId'],instrumentId=node,
                currencyId=currencies[row['trade_currency']],economicDate=datetime.fromisoformat(row['trade_datetime_utc']).date(),
                amount=Decimal(amount['value']),component='RESET',recognitionRole='INCOME',paymentDate=None,
                sourceReference=str(payload)+':'+row['trade_id']),key)
            if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
                m.access_audit_event.c.action=='RECONCILIATION_RESET_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(identity))):
                audit(c,actor,tenant,'RECONCILIATION_RESET_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
                    strategyId=str(foundation['strategyId']),sourcePayloadId=str(payload),sourceTradeId=row['trade_id'],tradeId=str(identity),
                    originalRow=dict(row),normalization=amount,recognition='DATED_RESET_INCOME_NOT_POSITION_OR_CASH_BALANCE',
                    paymentConfirmed=False))
            posted.append(str(identity))
    return dict(postedFlows=len(posted),unpostedFlows=len(blocked),unposted=blocked)
