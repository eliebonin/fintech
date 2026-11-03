"""Plain bond maturity: sourced principal, immutable proposals, real closing trades."""
import json
from copy import deepcopy
from datetime import datetime,time,timezone
from decimal import Decimal
from uuid import UUID,uuid4
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.lifecycle_authority import require_lifecycle_operation
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.reconstruction import reconstruct
from security_master_schema.evidence import canonical_payload,evidence_hash
from .bond_redemption import closing_movements


class RedemptionConflict(ValueError): pass


def policy(c,tenant,strategy):
    row=c.execute(select(m.bond_redemption_policy).where(m.bond_redemption_policy.c.tenant_id==tenant,
        m.bond_redemption_policy.c.strategy_id==strategy).order_by(m.bond_redemption_policy.c.revision.desc()).limit(1)).mappings().one_or_none()
    return dict(row) if row else dict(mode='REVIEW',revision=0)


def lock(c,tenant,strategy):
    if c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id==strategy,
        m.strategy.c.status=='ACTIVE').with_for_update()) is None: raise LookupError('Active strategy unavailable')


def configure(c,tenant,actor,operator,strategy,mode,revision,reason):
    require_lifecycle_operation(c,tenant,actor,strategy,'CONFIGURE',mode,real_operator=operator);lock(c,tenant,strategy)
    if policy(c,tenant,strategy)['revision']!=revision: raise RedemptionConflict('Processing policy changed; reload')
    c.execute(m.bond_redemption_policy.insert().values(tenant_id=tenant,strategy_id=strategy,revision=revision+1,
        mode=mode,reason=reason,actor_id=actor,real_operator_id=operator))
    return policy(c,tenant,strategy)


def candidate(c,tenant,strategy,instrument):
    now=datetime.now(timezone.utc)
    terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==instrument,m.bond_terms.c.is_current,
        m.bond_terms.c.effective_from<=now.date())).mappings().one_or_none()
    dates=c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id==instrument)).mappings().one_or_none()
    if not terms or not dates or not dates['maturity_date']: raise ValueError('Approved dated bond terms and maturity required')
    day=dates['maturity_date']
    if day>now.date(): raise ValueError('Bond maturity is not due yet')
    if terms['effective_from']>day or (terms['effective_to'] and terms['effective_to']<day): raise ValueError('Terms are not effective at maturity')
    if terms['coupon_type'] not in ('FIXED','ZERO') or terms['quotation_basis']!='PCT_OF_PAR':
        raise ValueError('Only plain fixed/zero-coupon percentage-of-par bonds are supported')
    subjects=[instrument,*c.scalars(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==instrument))]
    cutoff=min(datetime.combine(day,time.max,timezone.utc),now)
    request=ProjectionRequest(tenant,strategy,cutoff,now)
    facts=tuple(iter_ledger_facts(c,request,subject_ids=subjects));projection=reconstruct(facts,request)
    buckets=[b for b in projection.buckets if b.closing_quantity]
    if not buckets: raise RedemptionConflict('No remaining bond exposure to redeem')
    price=terms['redemption_amount_per_par'];movements=closing_movements(buckets,price)
    bookings={f.trade_id:f.booking for f in facts if f.booking}
    for b in buckets:
        if b.key.product_basis!='BOND' or b.key.currency_id!=terms['issue_currency_id']: raise ValueError('Bond currency/product mismatch')
        for trade in b.trade_ids:
            frozen=bookings[trade].product_evidence or {}
            if frozen.get('maturityDate')!=day.isoformat(): raise ValueError('Frozen booked maturity differs from current sourced maturity')
    mode=policy(c,tenant,strategy)
    payload=canonical_payload(dict(strategyId=strategy,instrumentId=instrument,valueDate=day,termId=terms['bond_terms_id'],
        currencyId=terms['issue_currency_id'],price=price,mode=mode['mode'],policyRevision=mode['revision'],
        movements=[dict(item,subjectId=b.key.subject_id,tradeIds=b.trade_ids) for b,item in zip(buckets,movements)],
        ledgerEvents=[f.event_id for f in facts],scope='PRINCIPAL_ONLY',paymentRecognised=False))
    return payload,evidence_hash(payload),projection,cutoff


def prepare(c,tenant,actor,operator,strategy,instrument,expected):
    mode=policy(c,tenant,strategy)['mode'];require_lifecycle_operation(c,tenant,actor,strategy,'PREPARE',mode,real_operator=operator)
    lock(c,tenant,strategy);data,fingerprint,_,_=candidate(c,tenant,strategy,instrument)
    if fingerprint!=expected: raise RedemptionConflict('Closing inputs changed; refresh')
    existing=c.execute(select(m.bond_redemption_proposal.c.proposal_id).where(m.bond_redemption_proposal.c.tenant_id==tenant,
        m.bond_redemption_proposal.c.strategy_id==strategy,m.bond_redemption_proposal.c.instrument_id==instrument,
        m.bond_redemption_proposal.c.input_hash==fingerprint,m.bond_redemption_proposal.c.prepared_by==actor,
        m.bond_redemption_proposal.c.prepared_operator==operator)).scalars().first()
    if existing:return dict(proposalId=str(existing),inputs=data,inputHash=fingerprint)
    identity=c.scalar(m.bond_redemption_proposal.insert().values(tenant_id=tenant,strategy_id=strategy,instrument_id=instrument,
        inputs=data,input_hash=fingerprint,mode=mode,policy_revision=data['policyRevision'],prepared_by=actor,prepared_operator=operator)
        .returning(m.bond_redemption_proposal.c.proposal_id))
    return dict(proposalId=str(identity),inputs=data,inputHash=fingerprint)


def post(c,tenant,actor,operator,strategy,instrument,expected,key,*,proposal_id=None):
    from security_master_schema.booking_controls import booking_lock_key
    c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant,'bond-maturity',key))))
    # Match ordinary booking's instrument -> strategy lock order. Governance
    # changes coordinate through the instrument lock, avoiding stale source races.
    if c.scalar(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==instrument).with_for_update()) is None:
        raise LookupError('Bond instrument unavailable')
    lock(c,tenant,strategy);mode=policy(c,tenant,strategy)['mode'];prepared=None
    if proposal_id:
        prepared=c.execute(select(m.bond_redemption_proposal).where(m.bond_redemption_proposal.c.tenant_id==tenant,
            m.bond_redemption_proposal.c.strategy_id==strategy,m.bond_redemption_proposal.c.proposal_id==proposal_id,
            m.bond_redemption_proposal.c.instrument_id==instrument)).mappings().one_or_none()
        if not prepared: raise LookupError('Prepared redemption unavailable')
    proof=require_lifecycle_operation(c,tenant,actor,strategy,'APPROVE' if prepared else 'BOOK',mode,real_operator=operator,
        prepared_by=prepared['prepared_by'] if prepared else None,prepared_operator=prepared['prepared_operator'] if prepared else None)
    request_hash=evidence_hash(dict(strategyId=strategy,instrumentId=instrument,expected=expected,proposalId=proposal_id))
    old=c.execute(select(m.bond_redemption_posting).where(m.bond_redemption_posting.c.tenant_id==tenant,
        m.bond_redemption_posting.c.request_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=request_hash: raise RedemptionConflict('Request key reused with different inputs')
        return canonical_payload(dict(old))
    data,fingerprint,projection,cutoff=candidate(c,tenant,strategy,instrument)
    if fingerprint!=expected or (prepared and (prepared['input_hash']!=fingerprint or prepared['policy_revision']!=data['policyRevision'])):
        raise RedemptionConflict('Prepared inputs or processing policy changed; prepare again')
    # Financial quantities are reconstructed in this transaction, never supplied by browser.
    trade_ids=[]
    for b,move in zip([b for b in projection.buckets if b.closing_quantity],data['movements']):
        source=b.trade_ids[0];booking=next(f.booking for f in projection.facts if f.booking and f.trade_id==source)
        original=c.execute(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==source,
            m.trade_lifecycle_event.c.event_type=='BOOKED')).scalar_one()
        snapshot=deepcopy(json.loads(original));details=dict(priceType='CLEAN',cleanAmount=move['cleanAmount'],dirtyAmount=move['cleanAmount'],
            accruedInterestAmount='0',settlementEvidence='Principal-only maturity; final interest separate; payment not asserted')
        snapshot['economics']['bondDetails']=details;snapshot['economics']['amount']=move['cleanAmount']
        snapshot['valuationConventions']['cleanExecutionAmount']=move['cleanAmount']
        snapshot['valuationRecognition']=dict(date=data['valueDate'],timezone='UTC',basis='UTC_TRADE_DATE',reason=None)
        snapshot['lifecycleRedemption']=dict(inputs=data,authority=proof,proposalId=str(proposal_id) if proposal_id else None,sourceTradeIds=move['tradeIds'])
        identity=uuid4();q=Decimal(move['quantity'])
        c.execute(m.trade.insert().values(trade_id=identity,strategy_id=strategy,trade_subject_reference_node_id=b.key.subject_id,
            reference_instrument_node_id=instrument,trade_type='MATURITY_REDEMPTION',quantity=q,quantity_unit='NOMINAL',
            execution_price=Decimal(move['price']),price_basis='PCT_OF_PAR',price_currency_id=b.key.currency_id,
            trade_datetime_utc=cutoff,valuation_effective_date=cutoff.date(),valuation_date_basis='UTC_TRADE_DATE',
            execution_channel='LIFECYCLE_OPS',lifecycle_status='BOOKED',booked_by_user_account_id=actor,created_by_user_account_id=actor,
            comment='Contractual principal maturity redemption; not cash receipt'))
        c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=cutoff,
            event_payload=json.dumps(snapshot,sort_keys=True),payload_hash=evidence_hash(snapshot),recorded_by_user_account_id=actor,
            source_system_id='BOND_MATURITY',source_event_id=key))
        trade_ids.append(str(identity))
    subjects=[b.key.subject_id for b in projection.buckets]
    check=reconstruct(tuple(iter_ledger_facts(c,projection.request,subject_ids=subjects)),projection.request)
    if any(b.closing_quantity for b in check.buckets): raise RedemptionConflict('Closing entry did not bring exposure to zero')
    row=c.execute(m.bond_redemption_posting.insert().values(tenant_id=tenant,strategy_id=strategy,proposal_id=proposal_id,
        request_key=key,request_hash=request_hash,evidence=data|dict(authority=proof,inputHash=fingerprint),trade_ids=trade_ids,
        actor_id=actor,real_operator_id=operator).returning(m.bond_redemption_posting)).mappings().one()
    return canonical_payload(dict(row))


def cancel(c,tenant,actor,operator,strategy,posting_id,reason,key):
    from security_master_schema.booking_controls import booking_lock_key
    c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant,'bond-maturity',key))))
    lock(c,tenant,strategy)
    proof=require_lifecycle_operation(c,tenant,actor,strategy,'CORRECT',policy(c,tenant,strategy)['mode'],real_operator=operator)
    fingerprint=evidence_hash(dict(postingId=posting_id,strategyId=strategy,reason=reason))
    table=m.bond_redemption_posting
    old=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.request_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=fingerprint: raise RedemptionConflict('Request key reused')
        return canonical_payload(dict(old))
    original=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.strategy_id==strategy,table.c.posting_id==posting_id)).mappings().one_or_none()
    if not original or original['evidence'].get('operation')=='CANCEL': raise LookupError('Original maturity posting unavailable')
    prepared=[]
    for identity in original['trade_ids']:
        trade=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(identity),m.trade.c.strategy_id==strategy).with_for_update()).mappings().one()
        chain=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade['trade_id']).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
        if trade['trade_type']!='MATURITY_REDEMPTION' or trade['lifecycle_status']!='BOOKED' or len(chain)!=1 or chain[0]['event_type']!='BOOKED':
            raise RedemptionConflict('Maturity entry already corrected or has unsupported history')
        prepared.append((trade,chain[0]))
    for trade,booked in prepared:
        payload=dict(schemaVersion=1,kind='BOOKING_CORRECTION',action='CANCEL_BOOKING',reason=reason,
            originalTradeId=str(trade['trade_id']),originalPostingId=str(posting_id),authority=proof)
        c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade['trade_id'],sequence_no=2,event_type='CANCELLED',
            event_datetime_utc=trade['trade_datetime_utc'],supersedes_event_id=booked['trade_lifecycle_event_id'],
            event_payload=json.dumps(payload,sort_keys=True),payload_hash=evidence_hash(payload),recorded_by_user_account_id=actor))
        c.execute(m.trade.update().where(m.trade.c.trade_id==trade['trade_id']).values(lifecycle_status='CANCELLED'))
    row=c.execute(table.insert().values(tenant_id=tenant,strategy_id=strategy,request_key=key,request_hash=fingerprint,
        evidence=dict(operation='CANCEL',originalPostingId=str(posting_id),reason=reason,authority=proof),trade_ids=original['trade_ids'],
        actor_id=actor,real_operator_id=operator).returning(table)).mappings().one()
    return canonical_payload(dict(row))
