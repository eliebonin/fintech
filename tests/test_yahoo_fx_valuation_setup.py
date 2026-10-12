"""Real resolver acceptance for scoped historical Yahoo research FX setup."""
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import uuid4
import json
import pytest
from sqlalchemy import select,func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_setup_resolves_both_dates_without_changing_source_or_prior_policy():
    from apps.market_data_ingestor.yahoo_fx_valuation_setup import prepare_fx_valuation
    from market_data.providers.yahoo.onboarding import enable_personal_research
    from market_data.providers.yahoo.fx_storage import configure_fx,ingest_fx
    from market_data.providers.yahoo.valuation_permissions import enable_personal_valuation
    from security_master_schema.index_universe_seed import seed
    from tests.test_yahoo_fx import chart
    from valuation.fx import resolve_fx
    from valuation.service import ValuationRequest
    from market_data.rights import load_rights
    engine=get_engine()
    assert engine.url.database.startswith('fortem_isolated_tests_')
    with engine.connect() as c:
        tx=c.begin()
        try:
            seed(c,ids['demo_user_account'])
            enable_personal_research(c,ids['tenant'],ids['demo_user_account'],'Synthetic owner approval')
            config=configure_fx(c,ids['tenant'],ids['demo_user_account'])
            c.execute(m.strategy.update().where(m.strategy.c.strategy_id==ids['strategy']).values(effective_from=date(2026,10,6)))
            enable_personal_valuation(c,ids['tenant'],ids['demo_user_account'],config['datasetId'],'Synthetic valuation approval')
            raw=chart(['2026-10-06T14:55:00+00:00','2026-10-07T14:55:00+00:00'],[.85,.86])
            ingest_fx(c,config=config,symbol='EURGBP=X',raw_payload=json.dumps(raw),start=date(2026,10,6),end=date(2026,10,7),
                received_at=datetime.now(timezone.utc),interval='5m')
            before=c.scalar(select(func.count()).select_from(m.market_data_observation))
            prior=dict(c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==ids['valuation_policy'])).mappings().one())
            args=(c,ids['tenant'],ids['demo_user_account'],ids['platform_admin_user_account'],ids['valuation_policy'],date(2026,10,6),date(2026,10,7),'Synthetic owner historical FX approval')
            report=prepare_fx_valuation(*args)
            assert prepare_fx_valuation(*args)==report
            assert dict(c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==ids['valuation_policy'])).mappings().one())==prior
            assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before
            request=ValuationRequest(ids['tenant'],ids['strategy'],report['policyId'],ids['valuation_cut'],ids['gbp_currency'],
                datetime(2026,10,6,23,tzinfo=timezone.utc),datetime(2026,10,7,23,tzinfo=timezone.utc),datetime.now(timezone.utc))
            for day,rate in [(date(2026,10,6),Decimal('.85')),(date(2026,10,7),Decimal('.86'))]:
                conversion=resolve_fx(c,request,ids['eur_currency'],ids['gbp_currency'],day)
                assert conversion.rate==rate and conversion.observation_date==day
                assert conversion.evidence['method']=='DIRECT'
                assert conversion.selection.pricing_evidence['calendarEvidence']['sealed'] is True
            assert not load_rights(c,config['datasetId'],'NON_DISPLAY',date.today(),'COMMERCIAL').allowed
            entitlement=m.tenant_dataset_entitlement
            historical=c.execute(select(entitlement).where(entitlement.c.dataset_id==config['datasetId'],
                entitlement.c.use_purpose=='VALUATION',entitlement.c.coverage_mode=='SCOPED')).mappings().one()
            assert historical['valid_from']==date(2026,10,6) and historical['valid_to']==date(2026,10,7)
            # A historical grant alone must never bypass today's revocation.
            c.execute(entitlement.update().where(entitlement.c.dataset_id==config['datasetId'],
                entitlement.c.use_purpose=='VALUATION',entitlement.c.coverage_mode=='DATASET').values(status='SUSPENDED'))
            with pytest.raises(ValueError,match='NO_VALID_ENTITLEMENT'):
                resolve_fx(c,request,ids['eur_currency'],ids['gbp_currency'],date(2026,10,6))
            with pytest.raises(PermissionError):
                prepare_fx_valuation(c,ids['second_tenant'],ids['demo_user_account'],ids['platform_admin_user_account'],ids['valuation_policy'],date(2026,10,6),date(2026,10,7),'Foreign tenant')
        finally:
            tx.rollback()
