"""Publish normalized provider corporate-action facts with append-only revisions."""
from sqlalchemy import select,func
from security_master_schema import models as m
from .storage import insert_returning


def publish_actions(c,actions,*,listing,source_payload_id):
    """Record source ex-dates only; never certify a payment or normalization proof."""
    report=dict(inserted=0,duplicates=0,revised=0,reviewRequired=0,staleSources=0)
    if not actions: return report
    parent=listing['instrument_node_id']
    payload=m.source_payload
    incoming=c.execute(select(payload.c.received_at_utc,payload.c.source_payload_id).where(
        payload.c.source_payload_id==source_payload_id)).one()
    # Serialize provider event revisions across listings sharing one canonical parent.
    c.execute(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==parent).with_for_update())
    for action in actions:
        if action['event_type'] not in ('STOCK_SPLIT','CASH_DIVIDEND') or action['date_role']!='EX':
            raise ValueError('Unsupported normalized corporate-action semantics')
        old=c.execute(select(m.corporate_action).where(m.corporate_action.c.affected_instrument_node_id==parent,
            m.corporate_action.c.external_event_reference==action['event_reference']).order_by(m.corporate_action.c.sequence_no.desc())
            .limit(1)).mappings().one_or_none()
        if old:
            if old['source_payload_id']:
                prior=c.execute(select(payload.c.received_at_utc,payload.c.source_payload_id).where(
                    payload.c.source_payload_id==old['source_payload_id'])).one()
                if tuple(incoming)<tuple(prior):
                    report['duplicates']+=1;report['staleSources']+=1;continue
            dates=c.execute(select(m.corporate_action_date).where(m.corporate_action_date.c.corporate_action_id==old['corporate_action_id'])).mappings().all()
            effects=c.execute(select(m.corporate_action_effect).where(m.corporate_action_effect.c.corporate_action_id==old['corporate_action_id'])).mappings().all()
            currency=listing['trading_currency_id'] if action['cash_amount'] is not None else None
            identical=(old['event_type']==action['event_type'] and len(dates)==len(effects)==1
                and dates[0]['date_role']=='EX' and dates[0]['date_value']==action['date_value']
                and dates[0]['timezone_name']==action['timezone_name'] and dates[0]['timestamp_value_utc'] is None
                and effects[0]['ratio']==action['ratio'] and effects[0]['cash_amount']==action['cash_amount']
                and effects[0]['currency_id']==currency)
            if identical: report['duplicates']+=1;continue
            if old['status']!='ANNOUNCED':
                report['reviewRequired']+=1;continue  # Never revive a cancellation or replace reviewed terms.
        event=insert_returning(c,m.corporate_action,'corporate_action_id',affected_instrument_node_id=parent,
            event_type=action['event_type'],status='ANNOUNCED',external_event_reference=action['event_reference'],
            sequence_no=old['sequence_no']+1 if old else 1,source_payload_id=source_payload_id,
            recorded_at_utc=func.clock_timestamp())
        c.execute(m.corporate_action_date.insert().values(corporate_action_id=event,date_role='EX',
            date_value=action['date_value'],timezone_name=action['timezone_name']))
        c.execute(m.corporate_action_effect.insert().values(corporate_action_id=event,
            effect_type='QUANTITY_CHANGE' if action['event_type']=='STOCK_SPLIT' else 'CASH',
            target_reference_node_id=parent if action['event_type']=='STOCK_SPLIT' else None,
            ratio=action['ratio'],cash_amount=action['cash_amount'],
            currency_id=listing['trading_currency_id'] if action['cash_amount'] is not None else None))
        report['inserted']+=1;report['revised']+=bool(old)
    return report
