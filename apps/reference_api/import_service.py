"""Retained, bounded trade reviews. The transaction owner commits effects and receipt together."""
import base64
import hashlib
import json
from uuid import uuid4,UUID
from sqlalchemy import select,func
from data_imports import tables as t
from data_imports.formats import parse_file,MAX_BYTES
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking,lock_booking_strategy
from security_master_schema.strategy_access import require_strategy_action,strategy_predicate
from apps.reference_api.import_adapters.trades import descriptor,prepare
from trading.booking import book_cash_trade
from security_master_schema.errors import RepositoryNotFound


class ImportConflict(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def lock(c,scope):
    value=int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(value)))


def view(item,offset=0,limit=50):
    report=item['report']
    return dict(jobId=str(item['job_id']),strategyId=str(item['strategy_id']),source=item['source'],
        filename=item['filename'],createdAt=str(item['created_at']),status=item['status'],
        total=report.get('total',0),valid=report.get('valid',0),invalid=report.get('invalid',0),
        applied=report.get('applied',0),replayed=report.get('replayed',0),reviewHash=report.get('reviewHash'),
        rows=report.get('rows',[])[offset:offset+limit],receipt=report.get('receipt',[]),offset=offset,limit=limit)


def load(c,tenant,actor,job_id,*,write=False):
    query=select(t.job).where(t.job.c.tenant_id==tenant,t.job.c.job_id==job_id)
    item=c.execute(query.with_for_update() if write else query).mappings().first()
    if item is None:raise RepositoryNotFound('Import not found.')
    action='TRADE_WRITE' if write else 'TRADE_READ'
    if write:authorize_booking(c,tenant,actor,strategy_id=item['strategy_id'])
    else:require_strategy_action(c,tenant,actor,action,item['strategy_id'])
    return item


def listing(c,tenant,actor,offset,limit):
    predicate=strategy_predicate(c,tenant,actor,'TRADE_READ',t.job.c.strategy_id)
    query=select(t.job).where(t.job.c.tenant_id==tenant,predicate)
    total=c.scalar(select(func.count()).select_from(query.subquery()))
    items=c.execute(query.order_by(t.job.c.created_at.desc(),t.job.c.job_id.desc()).offset(offset).limit(limit)).mappings()
    return dict(items=[view(item,limit=0) for item in items],total=total)


def submit(c,tenant,actor,payload,key):
    authorize_booking(c,tenant,actor,strategy_id=payload.strategy_id)
    lock_booking_strategy(c,tenant,payload.strategy_id)
    lock(c,f'import:{tenant}:{key}')
    fingerprint=digest(dict(actor=actor,**payload.model_dump(mode='json')))
    existing=c.execute(select(t.job).where(t.job.c.tenant_id==tenant,t.job.c.request_key==key)).mappings().first()
    if existing:
        if existing['request_hash']!=fingerprint:raise ImportConflict('Upload key reused with different contents or actor.')
        return view(existing)
    try:data=base64.b64decode(payload.content_base64,validate=True)
    except ValueError as exc:raise ValueError('Invalid file encoding.') from exc
    if not data or len(data)>MAX_BYTES:raise ValueError('Use a nonempty file of at most 512 KiB.')
    if not payload.filename.lower().endswith(('.csv','.xlsx')):raise ValueError('Use .csv or .xlsx only.')
    job_id=uuid4()
    c.execute(t.job.insert().values(job_id=job_id,tenant_id=tenant,strategy_id=payload.strategy_id,actor_id=actor,
        request_key=key,request_hash=fingerprint,source=payload.source,filename=payload.filename,
        artifact=data,artifact_sha256=hashlib.sha256(data).hexdigest(),status='RECEIVED',report={}))
    return view(load(c,tenant,actor,job_id,write=True))


def _prior(c,item,source_id):
    return c.execute(select(t.row).where(t.row.c.tenant_id==item['tenant_id'],t.row.c.strategy_id==item['strategy_id'],
        t.row.c.source==item['source'],t.row.c.source_trade_id==source_id)).mappings().first()


def assess(c,tenant,actor,item):
    spec=descriptor(c,tenant,actor,item['strategy_id'])
    try:parsed=parse_file(item['artifact'],item['filename'],spec)
    except ValueError as exc:
        return dict(total=0,valid=0,invalid=1,applied=0,replayed=0,rows=[dict(row=0,sourceTradeId='',status='INVALID',
            errors=[dict(field='file',code='import.format',message=str(exc))])],reviewHash=digest([str(exc)]))
    results=[];seen=set();seen_refs=set()
    for row in parsed:
        values=row['values'];source_id=values.get('sourceTradeId','')
        result=dict(row=row['row'],sourceTradeId=source_id,values=values,status='VALID',errors=[])
        try:
            if not source_id or len(source_id)>200:raise ValueError('sourceTradeId: enter a nonblank ID of at most 200 characters.')
            if source_id in seen:raise ValueError('sourceTradeId: repeated within this file; distinct executions need distinct source IDs.')
            seen.add(source_id)
            request,_=prepare(c,tenant,actor,item['strategy_id'],values,validate=False)
            row_hash=digest(request.model_dump(mode='json',by_alias=True)|{'tradeCurrency':values.get('tradeCurrency','')})
            old=_prior(c,item,source_id)
            if old:
                if old['payload_hash']!=row_hash:raise ValueError('sourceTradeId already booked with different contents. Use the normal linked correction workflow.')
                result.update(status='REPLAY',tradeId=str(old['trade_id']),payloadHash=row_hash)
            else:
                request,evidence=prepare(c,tenant,actor,item['strategy_id'],values)
                # Namespace-bearing external references cannot collide within a batch.
                for reference in request.external_references:
                    identity=(reference.source_system_id,reference.reference_type,reference.reference_value)
                    if reference.source_system_id and identity in seen_refs:raise ValueError('External reference repeats within this file.')
                    seen_refs.add(identity)
                result.update(payload=request.model_dump(mode='json',by_alias=True),payloadHash=row_hash,evidence=evidence)
        except (ValueError,ArithmeticError,RepositoryNotFound) as exc:
            result['status']='INVALID'
            field=getattr(exc,'field',None) or ('sourceTradeId' if str(exc).startswith('sourceTradeId') else 'row')
            message='Listing or related reference is unavailable in this scope.' if isinstance(exc,RepositoryNotFound) else str(exc)
            result['errors']=[dict(field=field,code='import.row_invalid',message=message)]
        results.append(result)
    valid=sum(r['status']!='INVALID' for r in results);replayed=sum(r['status']=='REPLAY' for r in results)
    return dict(total=len(results),valid=valid,invalid=len(results)-valid,applied=0,replayed=replayed,
        rows=results,reviewHash=digest(results))


def validate(c,tenant,actor,job_id):
    item=load(c,tenant,actor,job_id,write=True)
    if item['status']=='APPLIED':return view(item)
    report=assess(c,tenant,actor,item);state='NEEDS_CORRECTION' if report['invalid'] else 'READY'
    c.execute(t.job.update().where(t.job.c.job_id==job_id).values(status=state,report=report))
    return view(load(c,tenant,actor,job_id,write=True))


def confirm(c,tenant,actor,job_id,review_hash,request_id):
    item=load(c,tenant,actor,job_id,write=True)
    if item['status']=='APPLIED':
        if item['report']['reviewHash']!=review_hash:raise ImportConflict('Review hash does not match the retained booking intent.')
        return view(item)
    if item['status']!='READY' or item['report'].get('reviewHash')!=review_hash:raise ImportConflict('Validate all rows and confirm the current review before booking.')
    lock_booking_strategy(c,tenant,item['strategy_id'])
    current=assess(c,tenant,actor,item)
    if current['invalid'] or current['reviewHash']!=review_hash:raise ImportConflict('References, choices or source identities changed. Revalidate and review before booking.')
    receipt=[];count=0
    # Caller transaction binds *all* bookings, import identities, audit and receipt.
    # Any exception rolls the whole effect transaction back; no per-row swallowing.
    for result in current['rows']:
        if result['status']=='REPLAY':
            receipt.append(dict(row=result['row'],sourceTradeId=result['sourceTradeId'],tradeId=result['tradeId'],outcome='ALREADY_BOOKED'))
            continue
        from trading.booking_contracts import TradeBookingRequest
        request=TradeBookingRequest.model_validate(result['payload'])
        row_key='import:'+digest([str(tenant),str(item['strategy_id']),item['source'],result['sourceTradeId']])
        booked=book_cash_trade(c,tenant,actor,request,row_key)
        trade_id=booked.trade_id
        c.execute(t.row.insert().values(tenant_id=tenant,strategy_id=item['strategy_id'],source=item['source'],
            source_trade_id=result['sourceTradeId'],payload_hash=result['payloadHash'],trade_id=trade_id,job_id=job_id))
        # Channel is provenance only; the ordinary writer retains frozen economics.
        c.execute(m.trade.update().where(m.trade.c.trade_id==trade_id).values(execution_channel='FILE_IMPORT'))
        receipt.append(dict(row=result['row'],sourceTradeId=result['sourceTradeId'],tradeId=str(trade_id),outcome='BOOKED'));count+=1
    report=current|dict(applied=count,receipt=receipt)
    c.execute(t.job.update().where(t.job.c.job_id==job_id).values(status='APPLIED',report=report))
    return view(load(c,tenant,actor,job_id,write=True))
