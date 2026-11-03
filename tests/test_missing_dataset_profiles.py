"""Absence of a rights profile cannot silently select a legacy permission path."""
import os
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from market_data.rights import denied_activity_datasets
from market_data.display_access import assert_dataset_display,EvidenceDisplayDenied


@pytest.mark.parametrize('activities',[('DISPLAY',),('NON_DISPLAY',),()])
def test_missing_and_unknown_profiles_are_denied_in_batched_and_whole_populations(activities):
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx=c.begin()
        try:
            dataset=ids['dataset'];unknown=uuid4()
            c.execute(m.dataset_access_profile.delete().where(m.dataset_access_profile.c.dataset_id==dataset))
            assert dataset in denied_activity_datasets(c,ids['tenant'],date(2026,10,30),activities)
            denied=set(denied_activity_datasets(c,ids['tenant'],date(2026,10,30),activities,datasets=[dataset,unknown]))
            assert denied=={dataset,unknown}
            assert denied_activity_datasets(c,ids['tenant'],date(2026,10,30),activities,datasets=[])==[]
        finally:tx.rollback()
    engine.dispose()


def test_missing_profile_cannot_release_frozen_market_evidence():
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx=c.begin()
        try:
            c.execute(m.dataset_access_profile.delete().where(m.dataset_access_profile.c.dataset_id==ids['dataset']))
            with pytest.raises(EvidenceDisplayDenied):assert_dataset_display(c,ids['tenant'],[ids['dataset']])
        finally:tx.rollback()
    engine.dispose()


def test_display_always_requires_reporting_purpose_even_for_synthetic_data():
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx=c.begin()
        try:
            c.execute(m.tenant_dataset_entitlement.delete().where(m.tenant_dataset_entitlement.c.dataset_id==ids['dataset'],
                m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'],m.tenant_dataset_entitlement.c.use_purpose=='INTERNAL_REPORTING'))
            with pytest.raises(EvidenceDisplayDenied):assert_dataset_display(c,ids['tenant'],[ids['dataset']])
        finally:tx.rollback()
    engine.dispose()
