"""Explicit local operator setup; dry-run and verify selection before committing."""
import argparse,json,sys
from pathlib import Path
from datetime import date,datetime,time,timezone
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine,select
from apps.market_data_ingestor.config import IngestorSettings
from apps.market_data_ingestor.yahoo_fx_valuation_setup import prepare_fx_valuation
from valuation.fx import resolve_fx
from valuation.service import ValuationRequest
from security_master_schema import models as m


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('tenant-id','actor-id','platform-actor-id','base-policy-id','strategy-id'):
        parser.add_argument('--'+name,type=UUID,required=True)
    for name in ('from-date','to-date'): parser.add_argument('--'+name,type=date.fromisoformat,required=True)
    parser.add_argument('--authorization-reference',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();settings=IngestorSettings.from_environment()
    if settings.environment not in ('local','test'): parser.error('Local personal research only')
    engine=create_engine(settings.database_url)
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                report=prepare_fx_valuation(c,args.tenant_id,args.actor_id,args.platform_actor_id,args.base_policy_id,args.from_date,args.to_date,args.authorization_reference)
                policy=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==report['policyId'])).mappings().one()
                currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.currency_code.in_(['EUR','GBP']))).all())
                request=ValuationRequest(args.tenant_id,args.strategy_id,report['policyId'],policy['valuation_cut_id'],currencies['GBP'],
                    datetime.combine(args.from_date,time.max,timezone.utc),datetime.combine(args.to_date,time.max,timezone.utc),datetime.now(timezone.utc))
                rates=[]
                for day in (args.from_date,args.to_date):
                    fx=resolve_fx(c,request,currencies['EUR'],currencies['GBP'],day)
                    rates.append(dict(date=day,rate=fx.rate,observationDate=fx.observation_date,evidence=fx.evidence))
                if args.apply: tx.commit()
                else: tx.rollback()
            except Exception:
                tx.rollback();raise
        print(json.dumps(dict(applied=args.apply,**report,version=policy['version_no'],rates=rates),default=str))
    finally: engine.dispose()


if __name__=='__main__': main()
