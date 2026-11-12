"""Preview then book explicit synthetic UI trades through the normal local API."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from uuid import UUID

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

TENANT=UUID('00000000-0000-7000-8000-000000000011')
ACTOR=UUID('00000000-0000-7000-8000-000000000083')
STRATEGY=UUID('1df14361-1a24-40f6-aabb-7c0cb86cf5fb')
PARIS=UUID('00000000-0000-7000-8000-000000000164')
DATASET=UUID('01a11302-d25d-7093-9827-3893ed3c6d86')
PREFIX='SYNTHETIC-PNL-REVIEW-20261013'


def scenarios():
    rows=[]
    for index,symbol in enumerate(('AIR','BNP','OR','MC','SAN','SU','AI','DG')):
        # Keep this UI baseline clear of Air Liquide's June 2026 split.
        # Its true pre-split holding needs replay, not a bypass of the guard.
        entries=[(date(2026,7,15) if symbol=='AI' else date(2024,10,15),'BUY',100)]
        if index<6:
            entries.extend([(date(2025,4,15),'BUY',50),(date(2025,10,15),'SELL',25),(date(2026,4,15),'BUY',40)])
        if index<3: entries.append((date(2026,10,8),'BUY',10))
        rows.extend(dict(symbol=symbol,date=day,side=side,quantity=quantity) for day,side,quantity in entries)
    return rows


def settlement_day(day,closed=()):
    """Fixture T+2 business days, excluding retained source weekday closures."""
    remaining=2
    while remaining:
        day+=timedelta(days=1)
        if day.weekday()<5 and day not in closed: remaining-=1
    return day


def api(path,body=None,key=None):
    headers={'X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(ACTOR),'Content-Type':'application/json'}
    if key: headers['Idempotency-Key']=key
    request=Request('http://127.0.0.1:8000/v1/'+path,
                    data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urlopen(request,timeout=60) as response: return json.load(response)


def prepare():
    from sqlalchemy import create_engine,select
    from security_master_schema.database_config import local_workspace_database
    from apps.market_data_ingestor.config import IngestorSettings
    from apps.reference_api.cash_booking_integrity import load_cash_booking_listing
    from apps.reference_api.contracts import TradeBookingRequest
    from security_master_schema import models as m
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
    from market_data.display_access import assert_dataset_display
    import pandas_market_calendars as calendars
    settings=IngestorSettings.from_environment()
    engine=create_engine(settings.database_url)
    if settings.environment not in ('local','test') or engine.url.database!=local_workspace_database() or engine.url.port!=15432:
        raise ValueError('Only the named local personal database is permitted')
    context=api('trades/booking-context')['data']
    calendar=calendars.get_calendar('XPAR')
    properties=[]
    for definition in context['properties']:
        if definition['required']:
            if definition['code']!='ALLOCATION_WEIGHT': raise ValueError('Review additional required trade properties before seeding')
            properties.append(dict(definitionId=definition['definitionId'],value='0.125'))
    try:
        with engine.connect() as c:
            require_strategy_action(c,TENANT,ACTOR,'TRADE_WRITE',STRATEGY)
            require_tenant_action(resolve_tenant_workspace(c,TENANT,ACTOR,date.today()),'MARKET_DATA_READ')
            strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==STRATEGY,m.strategy.c.tenant_id==TENANT,m.strategy.c.status=='ACTIVE')).mappings().one()
            if strategy['strategy_code']!='STRAT-TEST': raise ValueError('Unexpected target strategy')
            plan=[]
            for row in scenarios():
                listing=c.execute(select(m.listing).where(m.listing.c.market_venue_id==PARIS,m.listing.c.trading_symbol==row['symbol'])).mappings().one()
                load_cash_booking_listing(c,TENANT,listing['listing_node_id'],row['date'],lock=False)
                prices=c.execute(select(m.market_data_observation).join(m.market_data_series).where(
                    m.market_data_series.c.reference_node_id==listing['listing_node_id'],m.market_data_series.c.series_type=='CLOSE',m.market_data_series.c.status=='ACTIVE',
                    m.market_data_observation.c.dataset_id==DATASET,m.market_data_observation.c.market_date==row['date'],
                    m.market_data_observation.c.value_basis=='RAW',m.market_data_observation.c.quality_status=='ACCEPTED')
                    .order_by(m.market_data_observation.c.received_at_utc.desc())).mappings().all()
                if not prices or len({p['value'] for p in prices})!=1: raise ValueError(f'Missing or ambiguous RAW close: {row}')
                source=prices[0]
                assert_dataset_display(c,TENANT,{DATASET},series_contexts=[(DATASET,source['market_data_series_id'])])
                key=f"{PREFIX}-{row['symbol']}-{row['date']}-{row['side']}"
                # Trading schedule supplies fixture business days: a missing market
                # price is never treated as a holiday. Not settlement certification.
                closes=set(calendar.schedule(row['date'],row['date']+timedelta(days=14)).index.date)
                if len(closes)<3: raise ValueError('Insufficient retained session coverage for synthetic settlement')
                closed={row['date']+timedelta(days=n) for n in range(1,15)}-closes
                payload=dict(listingId=str(listing['listing_node_id']),strategyId=str(STRATEGY),side=row['side'],quantity=str(row['quantity']),
                    executionPrice=str(source['value']),tradeDatetime=datetime.combine(row['date'],time(18),timezone.utc).isoformat(),
                    settlementDate=settlement_day(row['date'],closed).isoformat(),externalReference=key,properties=properties,
                    tradePurpose='INVESTMENT',marketActivity='SECONDARY',
                    comment=f"SYNTHETIC UI ACCEPTANCE ONLY. Owner request 2026-10-13. Simulated historical execution from Yahoo RAW close; observation {source['market_data_observation_id']}. Not an actual execution. Allocation weight is fixture metadata. T+2 fixture uses pandas_market_calendars XPAR trading days, not certified settlement holidays.")
                if row['symbol']=='AI':
                    # Preserve an already-created initial fixture through the normal
                    # linked correction workflow; never overwrite its execution.
                    old_key=f'{PREFIX}-AI-2024-10-15-BUY'
                    original=c.execute(select(m.trade).join(m.trade_external_reference).where(
                        m.trade.c.strategy_id==STRATEGY,m.trade_external_reference.c.reference_value==old_key)).mappings().one_or_none()
                    if original:
                        if (original['booked_by_user_account_id']!=ACTOR or not (original['comment'] or '').startswith('SYNTHETIC UI ACCEPTANCE ONLY.')
                            or original['trade_subject_reference_node_id']!=listing['listing_node_id']):
                            raise ValueError('Original AI seed is not the expected owned synthetic record')
                        payload['correction']=dict(tradeId=str(original['trade_id']),expectedSequenceNo=1,
                            reason='Synthetic UI seed: acquire Air Liquide after its 2026-06-08 split; retain the earlier seed as superseded audit history. No corporate-action guard bypass.')
                TradeBookingRequest.model_validate(payload)
                plan.append(dict(key=key,symbol=row['symbol'],sourceObservationId=str(source['market_data_observation_id']),payload=payload))
            return plan
    finally: engine.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    plan=prepare()  # Every listing, date, price and required property must pass first.
    if not args.apply:
        print(json.dumps(dict(mode='PREVIEW',strategyId=str(STRATEGY),trades=plan),default=str));return
    for entry in plan:
        result=api('trades',entry['payload'],entry['key'])
        print(json.dumps(dict(mode='BOOKED_OR_REPLAYED',symbol=entry['symbol'],key=entry['key'],tradeId=result['data']['trade']['tradeId']),default=str),flush=True)


if __name__=='__main__': main()
