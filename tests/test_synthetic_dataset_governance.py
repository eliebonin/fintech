import os
from sqlalchemy import create_engine,select,func
from security_master_schema import models as m
from security_master_schema.synthetic_market_data import provision_seed_profiles
from security_master_schema.demo_data import DEMO_IDS as ids
from market_data.rights import denied_activity_datasets
from datetime import date


def test_seed_profiles_are_explicit_idempotent_and_preserve_revocation():
    engine=create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                assert c.scalar(select(m.dataset_access_profile.c.usage_scope).where(m.dataset_access_profile.c.dataset_id==ids['dataset']))=='SYNTHETIC'
                counts=[c.scalar(select(func.count()).select_from(t)) for t in (m.dataset_access_profile,m.dataset_right_requirement,m.licence_activity_grant)]
                assert provision_seed_profiles(c)==[]
                assert counts==[c.scalar(select(func.count()).select_from(t)) for t in (m.dataset_access_profile,m.dataset_right_requirement,m.licence_activity_grant)]
                c.execute(m.dataset_access_profile.update().where(m.dataset_access_profile.c.dataset_id==ids['dataset']).values(status='SUSPENDED'))
                assert provision_seed_profiles(c)==[]
                assert ids['dataset'] in denied_activity_datasets(c,ids['tenant'],date(2026,10,30),['NON_DISPLAY'])
            finally:tx.rollback()
    finally:engine.dispose()
