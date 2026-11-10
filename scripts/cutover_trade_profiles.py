"""Preview/apply the explicit local trade-profile cutover after migration 111.

No reseeding, trade/evidence updates, permission grants or financial runs.
The retained actor identifies a technical migration, not a new business decision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID
from sqlalchemy import create_engine,select,text
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.local_database_config import migration_url
from security_master_schema import models as m
from security_master_schema.evidence import evidence_hash
from trading.profiles.migration import backfill_profiles


def retained_financial_digest(c):
    """Ordered streaming hashes; never print records or rewrite their evidence."""
    result={}
    for table in (m.trade,m.trade_lifecycle_event,m.trade_property_value,m.trade_property_reference,m.trade_party_role,m.trade_tag_assignment,m.trade_external_reference,m.access_group_grant):
        columns=[column for column in table.c if column.name not in {'trade_profile_version_id','trade_profile_assignment_revision','source_inherited'}]
        statement=select(*columns).order_by(*table.primary_key.columns)
        digest=hashlib.sha256();count=0
        for row in c.execute(statement.execution_options(stream_results=True)).mappings().yield_per(500):
            digest.update(evidence_hash(dict(row)).encode('ascii'));count+=1
        result[table.fullname]=dict(count=count,sha256=digest.hexdigest())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor',type=UUID,required=True)
    parser.add_argument('--tenant',type=UUID)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    engine=create_engine(migration_url(),hide_parameters=True)
    try:
        with engine.connect() as c:
            transaction=c.begin()
            try:
                head=c.scalar(text('SELECT version_num FROM alembic_version'))
                if head!='20261104_111':raise RuntimeError('Apply migration 111 and inspect the database head before this cutover.')
                before=retained_financial_digest(c)
                report=backfill_profiles(c,args.actor,args.tenant)
                after=retained_financial_digest(c)
                if before!=after:raise RuntimeError('Retained financial or permission rows changed; cutover rolled back.')
                if args.apply:transaction.commit()
                else:transaction.rollback()
                print(json.dumps(dict(mode='APPLIED' if args.apply else 'PREVIEW_ROLLED_BACK',head=head,cutover=report,unchangedFinancialAndGrantHashes=before),indent=2))
            except BaseException:
                if transaction.is_active:transaction.rollback()
                raise
    finally:engine.dispose()

if __name__=='__main__':main()
