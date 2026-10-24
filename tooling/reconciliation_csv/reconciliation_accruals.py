"""Daily source earnings, aggregated once; no inferred interest balance or carry."""
from datetime import date
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal


def aggregate_accruals(bundle):
    trades={r['trade_id']:r for r in bundle.positions};groups={};seen=set()
    with localcontext() as context:
        context.prec=100
        for row in bundle.tables['accrued_interests']:
            identity=(row['trade_id'],row['value_date'])
            if identity in seen:raise ValueError('Duplicate source trade/day daily-interest input')
            seen.add(identity);trade=trades[row['trade_id']]
            instrument=source_id(row['instrument_id'])
            if source_id(trade['instrument_id'])!=instrument:raise ValueError('Accrual source trade/bond mismatch')
            key=(instrument,row['value_date'],trade['trade_currency'])
            group=groups.setdefault(key,dict(sourceInstrumentId=instrument,valueDate=row['value_date'],
                currency=trade['trade_currency'],originalRows=[],total=Decimal(0)))
            amount=Decimal(row['trade_daily_accrual_amount'])
            if not amount.is_finite():raise ValueError('Finite earned interest required')
            group['total']+=amount;group['originalRows'].append(dict(row))
        result=[]
        for key,group in sorted(groups.items()):
            group['normalization']=native_decimal(format(group.pop('total'),'f'))
            result.append(group)
        return result


def post_accruals(c,bundle,tenant,actor,foundation):
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from valuation.accruals import record_accrual
    require_strategy_action(c,tenant,actor,'VALUATION_RUN',foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':accrued_interests'))
    if not payload:raise ValueError('Owned retained daily-interest source required')
    nodes={}
    for proposal in c.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.tenant_id==tenant,
        m.reference_data_proposal.c.source_system_id==foundation['sourceId'],m.reference_data_proposal.c.proposal_type=='CREATE_BOND',
        m.reference_data_proposal.c.status=='APPROVED')).mappings():
        source=json.loads(proposal['proposed_payload']);identifier=source.get('sourceExternalId')
        if not identifier:continue
        if identifier in nodes and nodes[identifier]!=proposal['reference_node_id']:raise ValueError('Conflicting native bond mapping')
        nodes[identifier]=proposal['reference_node_id']
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    output=[]
    for group in aggregate_accruals(bundle):
        node=nodes[group['sourceInstrumentId']];day=date.fromisoformat(group['valueDate'])
        key='recon-interest:'+sha256(document(dict(source=str(foundation['sourceId']),bundle=bundle.digest,
            instrument=group['sourceInstrumentId'],day=group['valueDate'],currency=group['currency']))).hexdigest()
        data=dict(strategyId=foundation['strategyId'],instrumentId=node,valueDate=day,inputType='DAILY_INTEREST',
            currencyId=currencies[group['currency']],dailyEarned=Decimal(group['normalization']['value']),
            sourceReference=str(payload)+':'+key,balanceReconciliation='NOT_PROVIDED',
            eligibilityConvention='Sum of supplied trade-level daily earnings for this bond/date; no missing dates or balance movements inferred')
        identity=record_accrual(c,tenant,actor,data,key)
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action=='RECONCILIATION_INTEREST_IMPORTED',m.access_audit_event.c.details['inputId'].as_string()==str(identity))):
            audit(c,actor,tenant,'RECONCILIATION_INTEREST_IMPORTED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
                strategyId=str(foundation['strategyId']),sourcePayloadId=str(payload),inputId=str(identity),**group))
        output.append(str(identity))
    return dict(sourceRows=len(bundle.tables['accrued_interests']),dailyBondInputs=len(output))
