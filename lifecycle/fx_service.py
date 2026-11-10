"""Deliverable forward maturity closure, distinct from currency delivery and MTM."""
import json
from datetime import datetime,time,timezone
from decimal import Decimal,localcontext
from uuid import UUID,uuid4
from types import SimpleNamespace
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from .entitlements import lifecycle_lock
from .assistance import current_assistance_proof,require_assistance
from security_master_schema.lifecycle_authority import require_lifecycle_operation
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
from security_master_schema.fx_forward_reference import load_fx_forward_booking_terms
from security_master_schema.evidence import canonical_payload,evidence_hash
from valuation.fx import resolve_fx
from .fx_maturity import closing_economics,validated_override
from .bond_service import lock,RedemptionConflict
from trading.allocation_policy import load_allocation_policy
from trading.annotations import lock_trade_catalogue
from trading.annotation_snapshots import load_trade_annotations
from positions.allocations import allocation_signature
from security_master_schema.maturity_evidence import closing_movement
from .allocations import prepare_annotations,require_annotations,persist_annotations,atomic_post,source_annotations_hash,lifecycle_profile_values

tables=(m.fx_maturity_policy,m.fx_maturity_proposal,m.fx_maturity_posting)
product_code='FX_FORWARD'


def policy(c,tenant,strategy):
    t=tables[0]
    row=c.execute(select(t).where(t.c.tenant_id==tenant,t.c.strategy_id==strategy).order_by(t.c.revision.desc()).limit(1)).mappings().one_or_none()
    return dict(row) if row else dict(mode='REVIEW',revision=0,pricing_policy_id=None,pricing_cut_id=None)


def configure(c,tenant,actor,operator,strategy,mode,revision,reason,pricing_policy_id,pricing_cut_id):
    lifecycle_lock(c,tenant)
    if mode=='DIRECT':current_assistance_proof(c,tenant,strategy,'FX_FORWARD_MATURITY','DIRECT',mode=mode)
    require_lifecycle_operation(c,tenant,actor,strategy,'CONFIGURE',mode,real_operator=operator);lock(c,tenant,strategy)
    if policy(c,tenant,strategy)['revision']!=revision:raise RedemptionConflict('Processing policy changed; reload')
    p=m.valuation_policy
    if c.scalar(select(p.c.valuation_policy_id).where(p.c.valuation_policy_id==pricing_policy_id,p.c.valuation_cut_id==pricing_cut_id,p.c.tenant_id==tenant,p.c.status=='ACTIVE',
        or_(p.c.strategy_id.is_(None),p.c.strategy_id==strategy))) is None:raise ValueError('Active pricing policy for this tenant/strategy required')
    if c.scalar(select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.valuation_cut_id==pricing_cut_id,m.valuation_cut.c.status=='ACTIVE')) is None:
        raise ValueError('Active pricing cut required')
    c.execute(tables[0].insert().values(tenant_id=tenant,strategy_id=strategy,revision=revision+1,mode=mode,reason=reason,
        pricing_policy_id=pricing_policy_id,pricing_cut_id=pricing_cut_id,actor_id=actor,real_operator_id=operator))
    return policy(c,tenant,strategy)


def _exposure(c,tenant,strategy,instrument,terms,cutoff,now,*,with_rows=False):
    """Bounded canonical-contract ledger, without enabling general FX valuation."""
    from security_master_schema.tenancy import assert_tenant_owns_strategy
    assert_tenant_owns_strategy(c,tenant,strategy)
    fingerprint=fx_forward_terms_fingerprint(terms);amount=Decimal(0);sources=[];events=[];amounts={}
    rows=c.execute(select(m.trade).where(m.trade.c.strategy_id==strategy,m.trade.c.trade_subject_reference_node_id==instrument,
        m.trade.c.trade_datetime_utc<=cutoff,m.trade.c.created_at_utc<=now).order_by(m.trade.c.trade_id)).mappings().all()
    chains={r['trade_id']:[] for r in rows};identities=list(chains)
    for start in range(0,len(identities),500):
        for e in c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id.in_(identities[start:start+500]),
                m.trade_lifecycle_event.c.recorded_at_utc<=now).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings():
            chains[e['trade_id']].append(e)
    for row in rows:
        chain=chains[row['trade_id']]
        if not chain or chain[0]['event_type']!='BOOKED':raise ValueError('Missing original forward booking evidence')
        if any(e['event_type'] not in ('BOOKED','CANCELLED','SUPERSEDED') for e in chain):raise ValueError('Existing delivery/lifecycle history requires reconciliation')
        if any(e['event_type'] in ('CANCELLED','SUPERSEDED') and e['event_datetime_utc']>cutoff for e in chain):
            raise ValueError('Correction effective after maturity requires reconciliation')
        events.extend(str(e['trade_lifecycle_event_id']) for e in chain)
        if any(e['event_type'] in ('CANCELLED','SUPERSEDED') for e in chain):continue
        frozen=json.loads(chain[0]['event_payload']);kind=frozen.get('kind')
        if (row['price_basis']!='RATE' or row['quantity_unit']!='CURRENCY_AMOUNT' or row['price_currency_id']!=terms.quote_currency_id
            or row['reference_instrument_node_id']!=instrument or chain[0]['event_datetime_utc']!=row['trade_datetime_utc']
            or row['valuation_effective_date'] and row['valuation_effective_date']>cutoff.date()):
            raise ValueError('Forward booking rate, currency or recognition convention mismatch')
        if kind=='FX_FORWARD_BOOKING':
            e=frozen['economics']
            if (frozen['baseCurrencyId']!=str(terms.base_currency_id) or frozen['quoteCurrencyId']!=str(terms.quote_currency_id)
                or e['termsFingerprint']!=fingerprint or Decimal(e['agreedRate'])!=row['execution_price']
                or e['quoteConvention']!=terms.quote_convention):raise ValueError('Frozen forward terms changed; reconciliation required')
            from security_master_schema.fx_forward_booking import derive_fx_forward_obligations
            expected=derive_fx_forward_obligations(terms,'BUY' if row['quantity']>0 else 'SELL',abs(row['quantity']))
            if (e['receiveCurrency']!=expected.receive_currency or e['payCurrency']!=expected.pay_currency
                or Decimal(e['receiveAmount'])!=expected.receive_amount or Decimal(e['payAmount'])!=expected.pay_amount):
                raise ValueError('Frozen forward obligations mismatch')
        elif kind=='FX_FORWARD_MATURITY':
            inputs=frozen['inputs'];move=closing_movement(inputs,frozen.get('movementKey'))
            if (chain[0]['payload_hash']!=evidence_hash(frozen) or move['subjectId']!=str(instrument) or inputs['termsFingerprint']!=fingerprint
                or inputs['instrumentId']!=str(instrument) or inputs['strategyId']!=str(strategy)
                or Decimal(move['quantity'])!=row['quantity'] or Decimal(inputs['price'])!=row['execution_price']
                or inputs['paymentRecognised'] is not False):raise ValueError('Frozen forward maturity evidence mismatch')
        else:raise ValueError('Unsupported forward booking evidence')
        with localcontext() as context:context.prec=512;amount+=row['quantity']
        sources.append(str(row['trade_id']));amounts[row['trade_id']]=row['quantity']
    if not amount and not with_rows:raise RedemptionConflict('No remaining forward exposure to close')
    return (amount,sources,events,amounts) if with_rows else (amount,sources,events)


def _allocation_groups(amounts,policy,annotations):
    from collections import defaultdict
    grouped=defaultdict(lambda:dict(quantity=Decimal(0),sources=[]))
    with localcontext() as ctx:
        ctx.prec=512
        for trade,amount in amounts.items():
            signature=allocation_signature(policy,annotations.get(trade,{}))
            grouped[signature]['quantity']+=amount;grouped[signature]['sources'].append(str(trade))
    return [(signature,item) for signature,item in sorted(grouped.items()) if item['quantity']]


def candidate(c,tenant,strategy,instrument,*,rate_override=None,annotation_inputs=None):
    lifecycle_lock(c,tenant)
    assistance_proof=current_assistance_proof(c,tenant,strategy,'FX_FORWARD_MATURITY')
    override=validated_override(rate_override)
    lock_trade_catalogue(c,tenant)
    now=datetime.now(timezone.utc)
    day=c.scalar(select(m.instrument_dates.c.maturity_date).where(m.instrument_dates.c.instrument_node_id==instrument))
    if not day or day>now.date():raise ValueError('Forward maturity is not due yet')
    terms=load_fx_forward_booking_terms(c,tenant,instrument,as_of=day)
    if terms.maturity_date!=day:raise ValueError('Contractual maturity mismatch')
    cutoff=min(datetime.combine(day,time.max,timezone.utc),now)
    amount,sources,events,amounts=_exposure(c,tenant,strategy,instrument,terms,cutoff,now,with_rows=True)
    allocation_policy=load_allocation_policy(c,tenant,strategy)
    annotations=load_trade_annotations(c,tenant,list(amounts),allocation_policy)
    groups=_allocation_groups(amounts,allocation_policy,annotations)
    if not groups:raise RedemptionConflict('No remaining forward allocation exposure to close')
    mode=policy(c,tenant,strategy)
    if not mode['pricing_policy_id'] or not mode['pricing_cut_id']:raise ValueError('Configure a maturity pricing policy and cut first')
    request=SimpleNamespace(tenant_id=tenant,strategy_id=strategy,policy_id=mode['pricing_policy_id'],cut_id=mode['pricing_cut_id'],
        closing_cutoff=cutoff,information_cutoff=now)
    selected=None;selection_error=None
    try:
        selected=resolve_fx(c,request,terms.base_currency_id,terms.quote_currency_id,day)
        if selected.observation_date!=day:raise ValueError('Maturity-day FX observation required; prior-day fallback is not enabled')
    except ValueError as exc:
        selected=None;selection_error=str(exc)
    price=Decimal(override['rate']) if override else selected.rate if selected else None
    movements=[]
    for signature,group in groups:
        move=(closing_economics(group['quantity'],price) if price is not None else dict(quantity=format(group['quantity'].copy_negate(),'f'),price=None,quoteAmount=None,paymentRecognised=False))
        move.update(subjectId=str(instrument),tradeIds=group['sources'],cleanAmount=None,allocation=list(signature))
        movements.append(move)
    annotation_state=prepare_annotations(c,tenant,allocation_policy,movements,annotations,annotation_inputs)
    data=canonical_payload(dict(strategyId=strategy,instrumentId=instrument,valueDate=day,price=price,
        baseCurrencyId=terms.base_currency_id,currencyId=terms.quote_currency_id,quoteConvention=terms.quote_convention,
        termsFingerprint=fx_forward_terms_fingerprint(terms),agreedRate=terms.agreed_rate,mode=mode['mode'],policyRevision=mode['revision'],lifecycleAssistance=assistance_proof,
        movements=movements,**annotation_state,annotationSourcesHash=source_annotations_hash(annotations),ledgerEvents=events,fxEvidence=selected.evidence if selected else None,
        suggestedPrice=selected.rate if selected else None,rateOverride=override,rateSelectionError=selection_error,
        rateSource='OPS_OVERRIDE' if override else 'POLICY_SPOT' if selected else 'MISSING',
        scope='EXPOSURE_ONLY',paymentRecognised=False))
    # Revalidation advances knowledge time, not economic inputs. Retain that
    # timestamp in evidence, but hash the selected facts rather than wall time.
    def stable(value):
        if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k!='informationCutoffUtc'}
        if isinstance(value,list):return [stable(v) for v in value]
        return value
    return data,evidence_hash(stable(data)),terms,cutoff


def _authority(c,tenant,actor,operator,strategy,operation,mode,prepared=None):
    proof=require_lifecycle_operation(c,tenant,actor,strategy,operation,mode,real_operator=operator,
        prepared_by=prepared['prepared_by'] if prepared else None,prepared_operator=prepared['prepared_operator'] if prepared else None)
    if operation!='CORRECT':require_strategy_action(c,tenant,actor,'MARKET_DATA_READ',strategy)
    return proof


def prepare(c,tenant,actor,operator,strategy,instrument,expected,*,rate_override=None,annotation_inputs=None):
    lifecycle_lock(c,tenant)
    require_assistance(c,tenant,actor,strategy,'FX_FORWARD_MATURITY','PREPARE')
    lock(c,tenant,strategy);mode=policy(c,tenant,strategy)['mode'];_authority(c,tenant,actor,operator,strategy,'PREPARE',mode)
    data,fingerprint,_,_=candidate(c,tenant,strategy,instrument,rate_override=rate_override,annotation_inputs=annotation_inputs)
    require_annotations(data)
    if data['price'] is None:raise ValueError('Eligible maturity spot rate or sourced manual rate required')
    if fingerprint!=expected:raise RedemptionConflict('Closing inputs changed; refresh')
    p=tables[1]
    existing=c.scalar(select(p.c.proposal_id).where(p.c.tenant_id==tenant,p.c.strategy_id==strategy,p.c.instrument_id==instrument,
        p.c.input_hash==fingerprint,p.c.prepared_by==actor,p.c.prepared_operator==operator))
    identity=existing or c.scalar(p.insert().values(tenant_id=tenant,strategy_id=strategy,instrument_id=instrument,input_hash=fingerprint,inputs=data,
        policy_revision=data['policyRevision'],mode=mode,prepared_by=actor,prepared_operator=operator).returning(p.c.proposal_id))
    return dict(proposalId=str(identity),inputs=data,inputHash=fingerprint)


@atomic_post
def post(c,tenant,actor,operator,strategy,instrument,expected,key,*,proposal_id=None,rate_override=None,annotation_inputs=None):
    lifecycle_lock(c,tenant)
    from security_master_schema.booking_controls import booking_lock_key
    c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant,'fx-maturity',key))))
    if c.scalar(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==instrument).with_for_update()) is None:raise LookupError('Forward unavailable')
    lock(c,tenant,strategy);mode=policy(c,tenant,strategy)['mode'];prepared=None;p=tables[1];t=tables[2]
    if proposal_id:
        prepared=c.execute(select(p).where(p.c.tenant_id==tenant,p.c.strategy_id==strategy,p.c.instrument_id==instrument,p.c.proposal_id==proposal_id)).mappings().one_or_none()
        if not prepared:raise LookupError('Prepared forward closure unavailable')
        if rate_override is not None:raise ValueError('Approval uses the retained proposal rate; prepare a new proposal to change it')
    proof=_authority(c,tenant,actor,operator,strategy,('APPROVE' if mode=='REVIEW' else 'CONFIRM') if prepared else 'BOOK',mode,prepared)
    override=prepared['inputs'].get('rateOverride') if prepared else validated_override(rate_override)
    request_body=dict(strategyId=strategy,instrumentId=instrument,expected=expected,proposalId=proposal_id,rateOverride=override)
    if annotation_inputs is not None:request_body['annotationInputs']=annotation_inputs
    fingerprint=evidence_hash(request_body)
    old=c.execute(select(t).where(t.c.tenant_id==tenant,t.c.request_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=fingerprint:raise RedemptionConflict('Request key reused with different inputs')
        return canonical_payload(dict(old))
    require_assistance(c,tenant,actor,strategy,'FX_FORWARD_MATURITY',('APPROVE' if mode=='REVIEW' else 'CONFIRM') if prepared else 'DIRECT')
    if prepared:
        if annotation_inputs is not None:raise ValueError('Approval uses retained annotation inputs; prepare again to change them')
        annotation_inputs={item['movementKey']:item.get('properties',[]) for item in prepared['inputs'].get('movements',[]) if item.get('movementKey')}
    data,actual,terms,cutoff=candidate(c,tenant,strategy,instrument,rate_override=override,annotation_inputs=annotation_inputs)
    require_annotations(data)
    if data['price'] is None:raise ValueError('Eligible maturity spot rate or sourced manual rate required')
    if actual!=expected or prepared and prepared['input_hash']!=actual:raise RedemptionConflict('Prepared rate, exposure or policy changed; prepare again')
    trade_ids=[]
    for move in data['movements']:
        from trading.profiles.resolution import frozen_configuration
        identity=uuid4()
        snapshot=dict(schemaVersion=1,kind='FX_FORWARD_MATURITY',inputs=data,movementKey=move['movementKey'],authority=proof,proposalId=str(proposal_id) if proposal_id else None,
            lifecycleAllocation=dict(movementKey=move['movementKey'],properties=move['properties'],policy=data['allocationPolicy']),tradeConfiguration=frozen_configuration(move['profileConfiguration']))
        c.execute(m.trade.insert().values(trade_id=identity,strategy_id=strategy,trade_subject_reference_node_id=instrument,reference_instrument_node_id=instrument,
            trade_type='MATURITY_CLOSE',quantity=Decimal(move['quantity']),quantity_unit='CURRENCY_AMOUNT',execution_price=Decimal(data['price']),price_basis='RATE',
            price_currency_id=terms.quote_currency_id,trade_datetime_utc=cutoff,valuation_effective_date=cutoff.date(),valuation_date_basis='UTC_TRADE_DATE',
            execution_channel='LIFECYCLE_OPS',lifecycle_status='BOOKED',booked_by_user_account_id=actor,created_by_user_account_id=actor,
            comment=move.get('standardInputs',{}).get('COMMENT') or 'Forward maturity exposure closure only; not currency delivery or cash movement',**lifecycle_profile_values(move)))
        if move.get('sourcePreservation'):snapshot['sourcePreservedAnnotations']=move['sourcePreservation']
        c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=cutoff,
            event_payload=json.dumps(canonical_payload(snapshot),sort_keys=True),payload_hash=evidence_hash(snapshot),recorded_by_user_account_id=actor,
            source_system_id='FX_MATURITY',source_event_id=evidence_hash(dict(tenantId=tenant,requestKey=key,movementKey=move['movementKey']))))
        persist_annotations(c,tenant,identity,move);trade_ids.append(str(identity))
    _,_,_,remaining=_exposure(c,tenant,strategy,instrument,terms,cutoff,datetime.now(timezone.utc),with_rows=True)
    if _allocation_groups(remaining,load_allocation_policy(c,tenant,strategy),load_trade_annotations(c,tenant,list(remaining),load_allocation_policy(c,tenant,strategy))):
        raise RedemptionConflict('Closing entries did not bring every allocation to zero')
    row=c.execute(t.insert().values(tenant_id=tenant,strategy_id=strategy,proposal_id=proposal_id,request_key=key,request_hash=fingerprint,
        evidence=data|dict(authority=proof,inputHash=actual),trade_ids=trade_ids,actor_id=actor,real_operator_id=operator).returning(t)).mappings().one()
    return canonical_payload(dict(row))


@atomic_post
def cancel(c,tenant,actor,operator,strategy,posting_id,reason,key):
    lifecycle_lock(c,tenant)
    from security_master_schema.booking_controls import booking_lock_key
    c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant,'fx-maturity',key))))
    lock(c,tenant,strategy);proof=_authority(c,tenant,actor,operator,strategy,'CORRECT',policy(c,tenant,strategy)['mode']);t=tables[2]
    fingerprint=evidence_hash(dict(postingId=posting_id,strategyId=strategy,reason=reason))
    old=c.execute(select(t).where(t.c.tenant_id==tenant,t.c.request_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=fingerprint:raise RedemptionConflict('Request key reused')
        return canonical_payload(dict(old))
    original=c.execute(select(t).where(t.c.tenant_id==tenant,t.c.strategy_id==strategy,t.c.posting_id==posting_id)).mappings().one_or_none()
    if not original or original['evidence'].get('operation')=='CANCEL':raise LookupError('Original forward maturity posting unavailable')
    for identity in original['trade_ids']:
        row=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(identity),m.trade.c.strategy_id==strategy).with_for_update()).mappings().one()
        chain=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==row['trade_id']).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
        if row['trade_type']!='MATURITY_CLOSE' or row['lifecycle_status']!='BOOKED' or len(chain)!=1:raise RedemptionConflict('Closing entry already corrected')
        payload=dict(kind='BOOKING_CORRECTION',action='CANCEL_BOOKING',reason=reason,originalPostingId=str(posting_id),authority=proof)
        c.execute(m.trade_lifecycle_event.insert().values(trade_id=row['trade_id'],sequence_no=2,event_type='CANCELLED',event_datetime_utc=row['trade_datetime_utc'],
            supersedes_event_id=chain[0]['trade_lifecycle_event_id'],event_payload=json.dumps(canonical_payload(payload)),payload_hash=evidence_hash(payload),recorded_by_user_account_id=actor))
        c.execute(m.trade.update().where(m.trade.c.trade_id==row['trade_id']).values(lifecycle_status='CANCELLED'))
    row=c.execute(t.insert().values(tenant_id=tenant,strategy_id=strategy,request_key=key,request_hash=fingerprint,
        evidence=dict(operation='CANCEL',originalPostingId=str(posting_id),reason=reason,authority=proof),trade_ids=original['trade_ids'],actor_id=actor,real_operator_id=operator).returning(t)).mappings().one()
    return canonical_payload(dict(row))
