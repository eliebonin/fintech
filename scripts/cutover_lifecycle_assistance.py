"""Preview/apply explicit legacy lifecycle assistance intent; never grants a tier."""
import argparse,json,sys
from pathlib import Path
from uuid import UUID
from sqlalchemy import create_engine,select,func,text
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from security_master_schema import models as m
from security_master_schema.access_management import require_platform,audit
from security_master_schema.booking_controls import lock_trade_configuration
from security_master_schema.evidence import evidence_hash
from scripts.local_database_config import migration_url
from scripts.cutover_trade_profiles import retained_financial_digest
from lifecycle.entitlements import lifecycle_lock
from lifecycle.assistance import selection,append_selection


def retained_digest(c):
    result=retained_financial_digest(c)
    import hashlib
    for table in (m.bond_redemption_policy,m.bond_redemption_proposal,m.bond_redemption_posting,m.fx_maturity_policy,m.fx_maturity_proposal,m.fx_maturity_posting,m.tenant_module_entitlement,m.tenant_lifecycle_subscription):
        digest=hashlib.sha256();count=0
        for row in c.execute(select(table).order_by(*table.primary_key.columns).execution_options(stream_results=True)).mappings().yield_per(500):digest.update(evidence_hash(dict(row)).encode('ascii'));count+=1
        result[table.fullname]=dict(count=count,sha256=digest.hexdigest())
    return result


def backfill_lifecycle_assistance(c,actor,tenant=None):
    require_platform(c,actor)
    tables=((m.bond_redemption_policy,'BOND_MATURITY'),(m.fx_maturity_policy,'FX_FORWARD_MATURITY'))
    # Discover tenant identities first, then reread current native policies under
    # the same lock order used by configuration and financial consumers.
    owners=set()
    for table,event in tables:
        statement=select(table.c.tenant_id).distinct()
        if tenant is not None:statement=statement.where(table.c.tenant_id==tenant)
        owners.update(c.scalars(statement))
    count=0
    for owner in sorted(owners,key=str):
        lifecycle_lock(c,owner);lock_trade_configuration(c,owner)
        candidates=[]
        for table,event in tables:
            latest=select(table.c.strategy_id,func.max(table.c.revision).label('revision')).where(table.c.tenant_id==owner).group_by(table.c.strategy_id).subquery()
            statement=select(table,m.strategy.c.tenant_id.label('strategy_owner')).join(latest,(latest.c.strategy_id==table.c.strategy_id)&(latest.c.revision==table.c.revision)).join(m.strategy,m.strategy.c.strategy_id==table.c.strategy_id).where(table.c.tenant_id==owner)
            candidates.extend([dict(row,event_type=event) for row in c.execute(statement).mappings()])
        for row in sorted(candidates,key=lambda r:(str(r['strategy_id']),r['event_type'])):
            if row['strategy_owner']!=owner:raise ValueError('Legacy lifecycle policy has inconsistent strategy ownership.')
            if selection(c,owner,row['strategy_id'],row['event_type']):continue
            tier=3 if row['mode']=='DIRECT' else 2
            reason=f"Technical cutover: copied explicit {row['event_type']} policy revision {row['revision']} ({row['mode']}); no subscription grant."
            append_selection(c,owner,actor,actor,row['strategy_id'],row['event_type'],tier,0,reason)
            audit(c,actor,owner,'LIFECYCLE_ASSISTANCE_CUTOVER',dict(strategyId=str(row['strategy_id']),eventType=row['event_type'],sourcePolicyRevision=row['revision'],selectedTier=tier,commercialSubscriptionChanged=False))
            count+=1
    return dict(createdSelections=count,positiveSubscriptionsGranted=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--actor',type=UUID,required=True);parser.add_argument('--tenant',type=UUID);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    engine=create_engine(migration_url(),hide_parameters=True)
    try:
        with engine.connect() as c:
            transaction=c.begin()
            try:
                if c.scalar(text('select version_num from alembic_version'))!='20261105_112':raise RuntimeError('Apply and verify migration112 before the explicit cutover.')
                before=retained_digest(c);report=backfill_lifecycle_assistance(c,args.actor,args.tenant);after=retained_digest(c)
                if before!=after:raise RuntimeError('Native/financial/grant history changed; cutover rolled back.')
                if args.apply:transaction.commit()
                else:transaction.rollback()
                print(json.dumps(dict(mode='APPLIED' if args.apply else 'PREVIEW_ROLLED_BACK',report=report,retainedHistoryAndGrantHashes=before),indent=2))
            except BaseException:
                if transaction.is_active:transaction.rollback()
                raise
    finally:engine.dispose()

if __name__=='__main__':main()
