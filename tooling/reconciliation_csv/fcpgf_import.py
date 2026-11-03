"""Explicit local FCPGF reconciliation operator; defaults to read-only preflight.

Not an application dependency, upload API, startup seed or supported CSV format.
Each phase commits its own retained report; native row identities make retries
safe. No valuation is calculated or published by this operator.
"""
import argparse
from collections import defaultdict
from datetime import date,datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from pathlib import Path
from uuid import UUID
from sqlalchemy import create_engine,select,func
from security_master_schema import models as m
from security_master_schema.access_management import audit
from .reconciliation import load_bundle,source_id,document
from .seed_reconciliation_bundle import apply_foundation,apply_confirmed_company
from .fcpgf_instruments import seed_funds,seed_bonds,seed_swaps,native_reference,catalogue,receipt,source_instruments

TENANT=UUID('00000000-0000-7000-8000-000000000011')
ACTOR=UUID('00000000-0000-7000-8000-000000000083')
ROOT=Path(__file__).resolve().parents[2]
PROPERTIES={'ALLOCATION_WEIGHT':'1'}


def save_map(c,bundle,foundation,nodes,**details):
    audit(c,ACTOR,TENANT,'RECONCILIATION_REFERENCE_MAP',dict(sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
        bundleHash=bundle.digest,nodes={k:str(v) for k,v in nodes.items()},**details))


def read_map(c,bundle,foundation):
    nodes={};listings={}
    for data in c.scalars(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==TENANT,
        m.access_audit_event.c.action=='RECONCILIATION_REFERENCE_MAP',m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId']),
        m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)):
        for k,v in data['nodes'].items():
            if k in nodes and nodes[k]!=UUID(v):raise ValueError('Conflicting retained source mapping')
            nodes[k]=UUID(v)
        listings.update({k:UUID(v) for k,v in data.get('fundListings',{}).items()})
    return nodes,listings


def instruments(c,bundle,f):
    from .reconciliation_products import seed_additional
    funds,listings=seed_funds(c,bundle,TENANT,ACTOR,f)
    bonds=seed_bonds(c,bundle,TENANT,ACTOR,f)
    swaps=seed_swaps(c,bundle,TENANT,ACTOR,f,bonds)
    additional=seed_additional(c,bundle,TENANT,ACTOR,f)
    nodes={**funds,**bonds,**swaps['swaps'],**swaps['references']}
    # Historical RESET references are not newly bookable contracts: only their
    # exported identity/currency is known. Keep them explicitly non-tradable.
    ins=source_instruments(bundle);currencies=catalogue(c,m.currency,'currency_code','currency_id');historical={}
    for iid in sorted({source_id(r.get('reference_instrument_id')) for r in bundle.flows}-{''}-set(nodes)):
        if iid not in ins:continue
        item=ins[iid];kind=item['instrument_type']
        if kind not in ('EQUITY OTC','DIVER OTC','ASWAP','BOND'):continue
        if iid in swaps['unsupported']:continue
        start=date.fromisoformat(item.get('effective_date') or bundle.manifest['earliestTradeDate'])
        node=native_reference(c,TENANT,ACTOR,f,bundle,'HIST_'+iid,'SWAP' if kind!='BOND' else 'BOND',
            item['short_name']+' [historical flow reference; terms unavailable]',currencies[item['currency']],start,tradable=False)
        nodes[iid]=node;historical[iid]=str(node)
    save_map(c,bundle,f,nodes,fundListings={k:str(v) for k,v in listings.items()},
        historicalReferences=historical,unsupported=swaps['unsupported'])
    return dict(funds=len(funds),bonds=len(bonds),swaps=len(swaps['swaps']),syntheticAutocalls=len(swaps['autocalls']),
        historicalFlowReferences=len(historical),unsupported=swaps['unsupported'],optionStatus='NORMALIZED_PLACEHOLDER_PENDING_STANDARD_CONTRACT_BOOKING')


def companies(c,bundle,f):
    result={}
    for iid in bundle.manifest['unmappedOrganisationIds']:
        result[iid]=apply_confirmed_company(c,bundle,TENANT,ACTOR,f,iid,'Northern Trust' if iid=='21' else 'Unverified source company '+iid,confirmed=iid=='21')
    return result


def book_funds(c,bundle,f,nodes,listings,parties):
    from trading.booking import book_cash_trade
    from trading.booking_contracts import TradeBookingRequest
    from .reconciliation_precision import native_decimal
    definitions={r.code:r for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==TENANT,m.trade_property_definition.c.status=='ACTIVE'))}
    props=[dict(definitionId=definitions[k].definition_id,value=v) for k,v in PROPERTIES.items()]
    if any(r.required and r.code not in PROPERTIES for r in definitions.values()):raise ValueError('Required custom field mapping not supplied')
    result=[];unposted=[]
    for row in sorted(bundle.positions,key=lambda r:(r['trade_datetime_utc'],r['trade_id'])):
        iid=source_id(row['instrument_id'])
        if iid not in listings:continue
        qty=native_decimal(row['quantity']);price=native_decimal(row['price'])
        q=Decimal(qty['value'])
        if Decimal(price['value'])<=0 or q==0:
            unposted.append(dict(sourceTradeId=row['trade_id'],sourceInstrumentId=iid,
                reason='NONPOSITIVE_FUND_PRICE_REQUIRES_TRANSFER_OR_SOURCE_CORRECTION' if Decimal(price['value'])<=0 else 'ZERO_SOURCE_QUANTITY',
                originalRow=row))
            continue
        execution=datetime.fromisoformat(row['trade_datetime_utc'])
        if execution.tzinfo is None:execution=execution.replace(tzinfo=timezone.utc)
        request=TradeBookingRequest(listingId=listings[iid],strategyId=f['strategyId'],side='BUY' if q>0 else 'SELL',quantity=q.copy_abs(),
            executionPrice=price['value'],tradeDatetime=execution,settlementDate=row['settlement_date'],counterpartyOrganisationId=parties[source_id(row['counterparty_id'])],
            properties=props,comment='Private FCPGF reconciliation. Share-class currency retained; source fund vehicle currency is not the trade quote currency.',
            externalReferences=[dict(referenceType='SOURCE_TRADE_ID',referenceValue=row['trade_id'],sourceSystemId=str(f['sourceId']))])
        key='fcpgf-fund-trade:'+sha256(document(dict(source=str(f['sourceId']),trade=row['trade_id']))).hexdigest()
        native=book_cash_trade(c,TENANT,ACTOR,request,key)
        old=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==TENANT,
            m.access_audit_event.c.action=='RECONCILIATION_TRADE_BOOKED',m.access_audit_event.c.details['tradeId'].as_string()==str(native.trade_id)))
        if not old:audit(c,ACTOR,TENANT,'RECONCILIATION_TRADE_BOOKED',dict(bundleHash=bundle.digest,sourceId=str(f['sourceId']),strategyId=str(f['strategyId']),
            sourceTradeId=row['trade_id'],sourceRowHash=sha256(document(row)).hexdigest(),tradeId=str(native.trade_id),sourcePayloadId=str(receipt(c,bundle,f,'trades')),
            originalRow=row,normalization=dict(quantity=qty,price=price),mappedProperties=PROPERTIES))
        result.append(str(native.trade_id))
    return dict(fundTrades=len(result),unpostedFundTrades=unposted)


def bookings(c,bundle,f,*,step='all'):
    from .reconciliation_postings import prepare_position_metadata,post_positions
    from .fcpgf_option import book_standard_option
    from .reconciliation_forwards import post_forwards
    from .fcpgf_bond_completion import request_factory,extend_when_issued
    nodes,listings=read_map(c,bundle,f);parties=companies(c,bundle,f);ins=source_instruments(bundle)
    result={}
    if step in ('all','products'):
        candidates={k:v for k,v in nodes.items() if any(source_id(r['instrument_id'])==k for r in bundle.positions)
            and ins[k]['instrument_type'] in ('DIVER OTC','EQUITY OTC','ASWAP','BOND')}
        tradable=set(c.scalars(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.reference_node_id.in_(set(candidates.values())),m.financial_reference_node.c.is_tradable)))
        positions={k:v for k,v in candidates.items() if v in tradable}
        _,parties2=prepare_position_metadata(c,bundle,TENANT,ACTOR,f,product_nodes=positions);parties.update(parties2)
        extend_when_issued(c,bundle,TENANT,ACTOR,f,{k:v for k,v in positions.items() if ins[k]['instrument_type']=='BOND'})
        result=post_positions(c,bundle,TENANT,ACTOR,f,positions,parties,PROPERTIES,instrument_ids=set(positions),request_factory=request_factory(bundle))
        if result['failed']:raise ValueError('Native booking failures: '+json.dumps([r for r in result['rows'] if r['status']=='NOT_POSTED']))
        result.pop('rows',None)
    if step in ('all','funds'):result.update(book_funds(c,bundle,f,nodes,listings,parties))
    if step in ('all','derivatives'):
        option=book_standard_option(c,bundle,TENANT,ACTOR,f,PROPERTIES,parties);nodes['20265']=option['instrumentId'];result['option']=option
        orientations={source_id(r['instrument_id']):(r['trade_currency'],'GBP') for r in bundle.positions if ins[source_id(r['instrument_id'])]['instrument_type']=='FXFWD'}
        forwards=post_forwards(c,bundle,TENANT,ACTOR,f,parties,PROPERTIES,orientations,
            orientation_evidence='Quantity currency inferred from supplied trade currency; rates are GBP per unit of that currency, consistent with the owner-confirmed source quotation convention. No inversion.')
        nodes.update({r['sourceInstrumentId']:UUID(r['instrumentId']) for r in forwards});result['forwardTrades']=len(forwards)
    save_map(c,bundle,f,nodes,fundListings={k:str(v) for k,v in listings.items()})
    return result


def schedules(c,bundle,f,nodes):
    from decimal import Decimal
    from lifecycle.coupon_service import save_schedule
    from lifecycle.coupon_contracts import ScheduleCreate
    from .reconciliation_precision import native_decimal
    groups=defaultdict(list);result=[]
    bonds={source_id(r['instrument_id']):r for r in bundle.tables['bonds']}
    for row in bundle.tables.get('bond_schedules',[]):groups[source_id(row['instrument_id'])].append(row)
    for iid,rows in groups.items():
        if iid not in nodes:continue
        bond=bonds[iid];cashflows=[];prior=bond.get('int_acc_dt') or bond['issue_dt']
        for row in sorted(rows,key=lambda r:r['payment_date']):
            day=row['payment_date']
            if Decimal(row['coupon_pct'])!=0:
                if prior>=day:raise ValueError('Source coupon period start must precede payment: '+iid)
                cashflows.append(dict(cashflowKey='COUPON_'+day,cashflowType='COUPON',accrualStart=prior,accrualEnd=day,paymentDate=day,
                    amountPer100=native_decimal(row['coupon_pct'],scale='100')['value']))
                prior=day
            if Decimal(row['principal_pct'])!=0:
                cashflows.append(dict(cashflowKey='PRINCIPAL_'+day,cashflowType='PRINCIPAL',paymentDate=day,
                    amountPer100=native_decimal(row['principal_pct'],scale='100')['value']))
        if not cashflows:continue
        payload=ScheduleCreate(instrumentId=nodes[iid],expectedRevision=0,sourceReference=str(receipt(c,bundle,f,'bond_schedules'))+':'+iid,
            reason='Owner-supplied coupon/principal schedule; fraction-of-original-nominal amounts x100. Coupon accrual boundaries inferred from source accrual start and preceding scheduled payment; payment dates are not payment confirmations.',
            cashflows=cashflows,confirmSchedule=True)
        view=save_schedule(c,TENANT,ACTOR,payload,'fcpgf-schedule:'+bundle.digest+':'+iid)
        result.append(dict(sourceInstrumentId=iid,scheduleId=str(view['scheduleId']) if 'scheduleId' in view else str(view.get('schedule_id')),cashflows=len(cashflows)))
    return dict(schedules=len(result),rows=result)


def datasets(c,bundle,f,operator):
    from dataclasses import replace
    from .reconciliation_prices import import_prices
    from .reconciliation_fx import import_fx
    from .reconciliation_accruals import post_accruals
    from .reconciliation_cash import post_cash
    from .reconciliation_flows import post_flows
    nodes,_=read_map(c,bundle,f);parties=companies(c,bundle,f);ins=source_instruments(bundle)
    currencies=catalogue(c,m.currency,'currency_code','currency_id');overrides={};comment_references={}
    for row in bundle.flows:
        iid=source_id(row.get('reference_instrument_id'))
        if iid and iid not in nodes and iid in ins:
            item=ins[iid]
            nodes[iid]=native_reference(c,TENANT,ACTOR,f,bundle,'HIST_'+iid,'SWAP',item['short_name']+' [historical flow reference; terms unavailable]',
                currencies[item['currency']],date.fromisoformat(item.get('effective_date') or bundle.manifest['earliestTradeDate']),tradable=False)
        elif not iid:
            match=re.fullmatch(r'RESET:((?:DIVEROTC|EQUITYOTC|ASWAP)[0-9]+(?:USD|GBP|EUR|JPY)?)',row.get('comment') or '')
            if not match:continue
            code=match[1]
            if code not in comment_references:
                comment_references[code]=native_reference(c,TENANT,ACTOR,f,bundle,'COMMENT_'+code,'SWAP',code+' [historical flow reference from source comment; terms unavailable]',
                    currencies[row['trade_currency']],date.fromisoformat(bundle.manifest['earliestTradeDate']),tradable=False)
            overrides[row['trade_id']]=comment_references[code]
    save_map(c,bundle,f,nodes,commentFlowReferences={k:str(v) for k,v in comment_references.items()})
    orientations={source_id(r['instrument_id']):(r['trade_currency'],'GBP') for r in bundle.positions if ins[source_id(r['instrument_id'])]['instrument_type']=='FXFWD'}
    # A source record which cannot be represented is retained, reported and not
    # disguised as a different product. The original full receipt is unchanged.
    usable=[r for r in bundle.tables['prices'] if source_id(r['instrument_id']) in nodes]
    skipped=sorted({source_id(r['instrument_id']) for r in bundle.tables['prices'] if source_id(r['instrument_id']) not in nodes})
    partial=replace(bundle,tables=dict(bundle.tables,prices=usable))
    prices=import_prices(c,partial,TENANT,ACTOR,f,operator,forward_orientations=orientations)
    fx=import_fx(c,bundle,TENANT,ACTOR,f,operator,selected=('GBP','USD','EUR','JPY'))
    bonds={k:v for k,v in nodes.items() if ins[k]['instrument_type']=='BOND'}
    interest=post_accruals(c,bundle,TENANT,ACTOR,f,bond_nodes=bonds)
    cash=post_cash(c,bundle,TENANT,ACTOR,f,parties)
    flows=post_flows(c,bundle,TENANT,ACTOR,f,nodes=nodes,reference_overrides=overrides)
    schedule=schedules(c,bundle,f,nodes)
    return dict(prices=prices,fx=fx,interest=interest,cash=cash,resets=flows,bondSchedules=schedule,unmappedPriceInstruments=skipped)


def finalize(c,bundle,f):
    """Disclose incomplete import and retire only unused source placeholders."""
    nodes,_=read_map(c,bundle,f)
    retired=[]
    for data in c.scalars(select(m.access_audit_event.c.details).where(m.access_audit_event.c.tenant_id==TENANT,
        m.access_audit_event.c.action=='RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED',
        m.access_audit_event.c.details['sourceId'].as_string()==str(f['sourceId']),m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)):
        for iid,value in data.get('options',{}).items():
            placeholder=UUID(value)
            if iid not in nodes or nodes[iid]==placeholder:continue
            c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==placeholder,
                m.reference_node_scope.c.owner_tenant_id==TENANT,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE')).one()
            if c.scalar(select(m.trade.c.trade_id).where((m.trade.c.reference_instrument_node_id==placeholder)|(m.trade.c.trade_subject_reference_node_id==placeholder)).limit(1)):
                raise ValueError('Source-normalized placeholder has bookings; explicit correction required')
            c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==placeholder).values(status='INACTIVE',is_tradable=False))
            retired.append(str(placeholder))
    actual=c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==f['strategyId']))
    expected=len(bundle.positions)+len(bundle.flows)
    missing=expected-actual
    if missing<0:raise ValueError('More native trades than retained source rows; review required')
    strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==f['strategyId'],m.strategy.c.tenant_id==TENANT)).mappings().one()
    plain=bundle.name+' — imported reconciliation';partial=plain+' [PARTIAL IMPORT]'
    if strategy['display_name'] not in (plain,partial):raise ValueError('Strategy label changed outside this import; preserve it')
    c.execute(m.strategy.update().where(m.strategy.c.strategy_id==f['strategyId']).values(display_name=partial if missing else plain))
    result=dict(sourceRows=expected,nativeTrades=actual,unpostedSourceRows=missing,status='PARTIAL_IMPORT' if missing else 'SOURCE_ROWS_POSTED',retiredUnbookedPlaceholders=retired,
        fullPortfolioValuationReady=False,reason='Resolve unposted source trades before treating this as the full portfolio; no valuation has been run or published.' if missing else 'All source rows posted with retained assumptions. Full-portfolio pricing-policy and financial acceptance remain separate; this operator has not run or published a valuation.')
    audit(c,ACTOR,TENANT,'RECONCILIATION_FCPGF_IMPORT_STATUS',dict(sourceId=str(f['sourceId']),bundleHash=bundle.digest,strategyId=str(f['strategyId']),**result))
    return result


def unit_movements(c,bundle,f):
    from .fcpgf_unit_movements import post
    nodes,listings=read_map(c,bundle,f)
    return post(c,bundle,TENANT,ACTOR,f,nodes,listings,companies(c,bundle,f),PROPERTIES)


def rate_bookings(c,bundle,f):
    from .fcpgf_rate_swaps import post
    nodes,_=read_map(c,bundle,f)
    return post(c,bundle,TENANT,ACTOR,f,nodes,companies(c,bundle,f),PROPERTIES)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',required=True,type=Path)
    parser.add_argument('--phase',choices=('instruments','bookings','product-bookings','fund-bookings','derivative-bookings','datasets','unit-movements','rate-bookings','finalize'),default='instruments')
    parser.add_argument('--operator',type=UUID)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();bundle=load_bundle(args.source_dir,'FCPGF',date(2026,10,20),include_details=True)
    if not args.apply:
        print(json.dumps(dict(mode='READ_ONLY',bundleHash=bundle.digest,positions=len(bundle.positions),resets=len(bundle.flows),files=len(bundle.files))))
        return
    from apps.reference_api.config import Settings
    from security_master_schema.database_config import local_workspace_database
    settings=Settings.from_environment();engine=create_engine(settings.database_url,pool_pre_ping=True)
    if settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=54329 or engine.url.database!=local_workspace_database():
        raise PermissionError('Explicit local workspace database required')
    if args.phase=='datasets' and args.operator is None:raise ValueError('Explicit personal file operator required')
    try:
        with engine.begin() as c:
            c.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
            c.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            f=apply_foundation(c,bundle,TENANT,ACTOR,ROOT/'logs'/'reconciliation'/str(TENANT))
            commands={'instruments':instruments,'bookings':bookings,
                'product-bookings':lambda c,b,f:bookings(c,b,f,step='products'),
                'fund-bookings':lambda c,b,f:bookings(c,b,f,step='funds'),
                'derivative-bookings':lambda c,b,f:bookings(c,b,f,step='derivatives'),
                'datasets':lambda c,b,f:datasets(c,b,f,args.operator),'finalize':finalize,'unit-movements':unit_movements,'rate-bookings':rate_bookings}
            result=commands[args.phase](c,bundle,f)
            audit(c,ACTOR,TENANT,'RECONCILIATION_FCPGF_PHASE_COMPLETED',dict(sourceId=str(f['sourceId']),bundleHash=bundle.digest,
                strategyId=str(f['strategyId']),phase=args.phase,result=json.loads(json.dumps(result,default=str))))
        path=ROOT/'logs'/'reconciliation'/str(TENANT)/bundle.digest/(args.phase+'-report.json')
        path.write_text(json.dumps(dict(strategyId=str(f['strategyId']),phase=args.phase,**result),default=str,indent=2),encoding='utf-8')
        summary={k:(len(v) if isinstance(v,list) else v) for k,v in result.items()}
        print(json.dumps(dict(status='COMMITTED',phase=args.phase,strategyId=str(f['strategyId']),report=str(path),result=summary),default=str),flush=True)
    finally:engine.dispose()


if __name__=='__main__':main()
