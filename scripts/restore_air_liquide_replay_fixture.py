"""Replace only the known synthetic post-split workaround through normal booking."""
import argparse,json,sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.seed_valuation_review_trades import api,TENANT,ACTOR,STRATEGY

ORIGINAL=UUID('4082993c-cad1-43b7-b04e-e5f87b586b6f')
CURRENT=UUID('14a03d82-74f2-4011-a1da-585e78481e39')
LISTING=UUID('01a11297-b06f-7436-befe-b76c8c5f4888')
KEY='SYNTHETIC-PNL-REVIEW-20261013-AI-REPLAY-2024-10-15-BUY'


def replacement_payload(original,current,sequence,properties):
    for row,identity,status in ((original,ORIGINAL,'SUPERSEDED'),(current,CURRENT,'BOOKED')):
        if (row['trade_id']!=identity or row['lifecycle_status']!=status or row['strategy_id']!=STRATEGY
            or row['booked_by_user_account_id']!=ACTOR or row['trade_subject_reference_node_id']!=LISTING
            or not (row['comment'] or '').startswith('SYNTHETIC UI ACCEPTANCE ONLY.') or row['quantity']!=100):
            raise ValueError('Only the unchanged identified synthetic fixture may be corrected')
    if sequence!=2: raise ValueError('Reload the changed synthetic correction history')
    return dict(listingId=str(LISTING),strategyId=str(STRATEGY),side='BUY',quantity=str(original['quantity']),
        executionPrice=str(original['execution_price']),tradeDatetime=original['trade_datetime_utc'].isoformat(),
        settlementDate=original['settlement_date'].isoformat(),externalReference=KEY,properties=properties,
        tradePurpose='INVESTMENT',marketActivity='SECONDARY',
        comment='SYNTHETIC UI ACCEPTANCE ONLY. Restore intended October 2024 acquisition through a linked correction now that reviewed 11:10 replay is enabled. Original quantity, execution price and dates copied from the archived mock. No real execution, loyalty entitlement, fractional payment or published P&L.',
        correction=dict(tradeId=str(CURRENT),expectedSequenceNo=sequence,
            reason='Restore original mock acquisition date after fixing share-ratio replay; retain both earlier records as superseded audit history.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    from sqlalchemy import create_engine,select,func
    from security_master_schema import models as m
    from security_master_schema.database_config import local_workspace_database
    from apps.market_data_ingestor.config import IngestorSettings
    from market_data.split_replay import load_reviewed_splits
    from datetime import datetime,timezone
    from apps.reference_api.contracts import TradeBookingRequest
    engine=create_engine(IngestorSettings.from_environment().database_url)
    if engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=54329 or engine.url.database!=local_workspace_database():
        raise ValueError('Named local personal research database only')
    try:
        context=api('trades/booking-context')['data']; properties=[]
        for definition in context['properties']:
            if definition['required']:
                if definition['code']!='ALLOCATION_WEIGHT': raise ValueError('Review new required fields before restoring the fixture')
                properties.append(dict(definitionId=definition['definitionId'],value='0.125'))
        with engine.connect() as c:
            existing=c.scalar(select(m.trade_external_reference.c.trade_id).join(m.trade).where(
                m.trade_external_reference.c.reference_value==KEY,m.trade.c.strategy_id==STRATEGY))
            if existing:
                print(json.dumps(dict(mode='ALREADY_RESTORED',tradeId=str(existing))));return
            events=load_reviewed_splits(c,{LISTING},datetime.now(timezone.utc),tenant_id=TENANT)
            if not any(e.effective_date.isoformat()=='2026-06-08' and e.ratio==Decimal('1.1') for e in events):
                raise ValueError('Reviewed Air Liquide 2026 basic allocation must be active first')
            rows={row['trade_id']:row for row in c.execute(select(m.trade).where(m.trade.c.trade_id.in_([ORIGINAL,CURRENT]))).mappings()}
            sequence=c.scalar(select(func.max(m.trade_lifecycle_event.c.sequence_no)).where(m.trade_lifecycle_event.c.trade_id==CURRENT))
            payload=replacement_payload(rows[ORIGINAL],rows[CURRENT],sequence,properties)
            TradeBookingRequest.model_validate(payload)
        if not args.apply: print(json.dumps(dict(mode='PREVIEW',payload=payload)));return
        result=api('trades',payload,KEY)
        print(json.dumps(dict(mode='BOOKED_LINKED_CORRECTION',tradeId=result['data']['trade']['tradeId'],originalQuantity='100')))
    finally: engine.dispose()


if __name__=='__main__': main()
