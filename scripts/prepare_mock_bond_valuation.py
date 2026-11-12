"""Prepare only the owner-requested mock bond's synthetic valuation inputs.

Default is read-only preview. --apply provisions new isolated source metadata,
owned synthetic rights, prices and strategy-specific policy/daily input records.
--calculate additionally requests one staged valuation; never publishes it.
"""
import argparse
from datetime import date, datetime, time, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.seed_mock_bond_strategy import api,TENANT,ACTOR,CODE,BOND_CODE

STRATEGY=UUID('07ac7abf-7477-4756-90bc-ff254130febd')
BOND=UUID('01a13eaa-8441-7270-af80-223f57983330')
PREFIX='MOCK_BOND_PRICES_20261015'
START=date(2026,9,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--calculate',action='store_true');args=parser.parse_args()
    if args.calculate and not args.apply:parser.error('--calculate requires --apply')
    from sqlalchemy import create_engine,select,func
    from security_master_schema.database_config import local_workspace_database
    from apps.reference_api.config import Settings
    from security_master_schema import models as m
    from security_master_schema.access_management import audit
    from security_master_schema.strategy_access import require_strategy_action
    from apps.reference_api.valuation_policies import authority
    from market_data.rights import load_rights
    from market_data.display_access import assert_dataset_display
    settings=Settings.from_environment();engine=create_engine(settings.database_url)
    if settings.environment!='local' or engine.url.host not in ('127.0.0.1','localhost') or engine.url.port!=15432 or engine.url.database!=local_workspace_database():
        raise ValueError('Only the named local app database is permitted')
    artifact=ROOT/'data/mock-bond-prices-20261015.json';content=artifact.read_bytes();evidence=json.loads(content);digest=sha256(content).hexdigest()
    now=datetime.now(timezone.utc)
    try:
        with engine.connect() as c:
            authority(c,TENANT,ACTOR,True);require_strategy_action(c,TENANT,ACTOR,'VALUATION_RUN',STRATEGY)
            strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==STRATEGY,m.strategy.c.tenant_id==TENANT,m.strategy.c.strategy_code==CODE)).mappings().one()
            if c.scalar(select(m.financial_reference_node.c.internal_code).where(m.financial_reference_node.c.reference_node_id==BOND))!=BOND_CODE:
                raise ValueError('Unexpected mock bond identity')
            calendar=c.execute(select(m.market_calendar).where(m.market_calendar.c.logical_code=='XLON_TRADING_2026',
                m.market_calendar.c.sealed,m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.tenant_id.is_(None))
                .order_by(m.market_calendar.c.version_no.desc()).limit(1)).mappings().one()
            for point in evidence['prices']:
                if not c.scalar(select(m.market_calendar_session.c.market_calendar_session_id).where(
                    m.market_calendar_session.c.market_calendar_id==calendar['market_calendar_id'],
                    m.market_calendar_session.c.session_date==date.fromisoformat(point['date']),m.market_calendar_session.c.session_status=='OPEN')):
                    raise ValueError('Published calendar does not cover mock date')
            org=c.scalar(select(m.tenant.c.owning_organisation_id).where(m.tenant.c.tenant_id==TENANT))
            source=c.scalar(select(m.integration_source_system.c.integration_source_system_id).where(
                m.integration_source_system.c.tenant_id==TENANT,m.integration_source_system.c.system_code==CODE))
            if source is None:raise ValueError('Run the authorized mock strategy seed first')
            currency=strategy['base_currency_id']
        print(json.dumps(dict(strategyId=str(STRATEGY),prices=evidence['prices'],valuationDate='2026-09-30',
            openingDate='2026-09-29',dailyInterest=evidence['dailyEarnedInterest'],apply=args.apply,calculate=args.calculate)))
        if not args.apply:return
        with engine.begin() as c:
            authority(c,TENANT,ACTOR,True)
            c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(PREFIX.encode()).digest()[:8],'big',signed=True))))

            def put(table,where,values,key):
                row=c.execute(select(table).where(*where)).mappings().one_or_none()
                return row[key] if row else c.scalar(table.insert().values(**values).returning(table.c[key]))

            provider=put(m.data_provider,[m.data_provider.c.provider_code==PREFIX],dict(organisation_id=org,
                provider_code=PREFIX,display_name='MOCK ONLY - tenant-one synthetic prices',owner_tenant_id=TENANT,status='ACTIVE'),'data_provider_id')
            product=put(m.provider_product,[m.provider_product.c.data_provider_id==provider,m.provider_product.c.product_code==PREFIX],
                dict(data_provider_id=provider,product_code=PREFIX,display_name='MOCK ONLY - manual bond prices',status='ACTIVE'),'provider_product_id')
            dataset=put(m.dataset,[m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==PREFIX],dict(provider_product_id=product,
                dataset_code=PREFIX,display_name='MOCK ONLY - GBP bond CLEAN RAW prices',data_domain='MARKET_DATA',
                coverage_description='Self-created synthetic values for one tenant-private mock bond; no actual market data.',
                delivery_channel='MANUAL',valid_from=START,status='ACTIVE'),'dataset_id')
            licence=put(m.data_licence,[m.data_licence.c.licence_code==PREFIX],dict(licensor_organisation_id=org,licensee_organisation_id=org,
                licence_code=PREFIX,display_name='Owner-created mock data - local personal use only',licence_reference='User request 2026-10-15; '+str(artifact.relative_to(ROOT)),
                permitted_use_description='Only our own invented values. Not third-party permission, real provider data or commercial clearance.',valid_from=START,status='ACTIVE'),'data_licence_id')
            assignment=put(m.dataset_licence_assignment,[m.dataset_licence_assignment.c.dataset_id==dataset,m.dataset_licence_assignment.c.data_licence_id==licence],
                dict(dataset_id=dataset,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=START,status='ACTIVE'),'dataset_licence_assignment_id')
            put(m.dataset_access_profile,[m.dataset_access_profile.c.dataset_id==dataset],dict(dataset_id=dataset,licensee_organisation_id=org,
                permitted_tenant_id=TENANT,usage_scope='PERSONAL',provider_enabled=True,activation_reference='Owner requested invented mock prices 2026-10-15; no third-party content.',status='ACTIVE'),'dataset_id')
            for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
                put(m.licence_activity_grant,[m.licence_activity_grant.c.dataset_licence_assignment_id==assignment,m.licence_activity_grant.c.activity==activity],
                    dict(dataset_licence_assignment_id=assignment,activity=activity,usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
                        evidence_reference='Owner-created synthetic values; user request 2026-10-15; source artifact SHA256 '+digest,valid_from=START,status='ACTIVE'),'grant_id')
                put(m.dataset_right_requirement,[m.dataset_right_requirement.c.dataset_id==dataset,m.dataset_right_requirement.c.activity==activity],
                    dict(dataset_id=dataset,activity=activity,requirement_code='SELF_CREATED_MOCK',dataset_licence_assignment_id=assignment),'requirement_id')
            for purpose in ('VALUATION','INTERNAL_REPORTING'):
                put(m.tenant_dataset_entitlement,[m.tenant_dataset_entitlement.c.tenant_id==TENANT,m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose==purpose],
                    dict(tenant_id=TENANT,dataset_id=dataset,dataset_licence_assignment_id=assignment,use_purpose=purpose,coverage_mode='DATASET',valid_from=START,status='ACTIVE'),'tenant_dataset_entitlement_id')
            payload=put(m.source_payload,[m.source_payload.c.integration_source_system_id==source,m.source_payload.c.external_message_reference==PREFIX],
                dict(integration_source_system_id=source,tenant_id=TENANT,payload_format='JSON',external_message_reference=PREFIX,
                    payload_locator=artifact.as_uri(),payload_sha256=digest,source_published_at_utc=now,received_at_utc=now,processing_status='MAPPED'),'source_payload_id')
            cut=put(m.valuation_cut,[m.valuation_cut.c.cut_code==PREFIX],dict(cut_code=PREFIX,display_name='MOCK bond EOD - London calendar',
                timezone_name='Europe/London',local_time=time(16,30),market_calendar_id=calendar['market_calendar_id'],status='ACTIVE'),'valuation_cut_id')
            measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='PRICE'))
            series=put(m.market_data_series,[m.market_data_series.c.reference_node_id==BOND,m.market_data_series.c.default_dataset_id==dataset],
                dict(reference_node_id=BOND,default_dataset_id=dataset,series_type='CLOSE',closing_method='PROVIDER_DEFINED',value_type='PRICE',
                    measure_definition_id=measure,currency_id=currency,valuation_cut_id=cut,expected_frequency_code='BUSINESS_DAILY',
                    expected_market_calendar_id=calendar['market_calendar_id'],coverage_start_date=date(2026,9,29),coverage_end_date=date(2026,10,1),
                    source_system_id=PREFIX,status='ACTIVE',is_official=False),'market_data_series_id')
            put(m.market_data_series_dimension,[m.market_data_series_dimension.c.market_data_series_id==series,m.market_data_series_dimension.c.dimension_code=='BOND_PRICE_TYPE'],
                dict(market_data_series_id=series,dimension_code='BOND_PRICE_TYPE',dimension_value='CLEAN'),'market_data_series_id')
            vintage=put(m.market_data_vintage,[m.market_data_vintage.c.dataset_id==dataset,m.market_data_vintage.c.source_vintage_key==PREFIX],
                dict(dataset_id=dataset,data_provider_id=provider,source_vintage_key=PREFIX,source_published_at_utc=now,received_at_utc=now,
                    value_basis='RAW',vintage_status='CURRENT',content_hash=digest,source_payload_id=payload),'market_data_vintage_id')
            for point in evidence['prices']:
                day=date.fromisoformat(point['date']);stamp=datetime.combine(day,time(15,30),timezone.utc);key=PREFIX+'-'+point['date']
                existing=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series,
                    m.market_data_observation.c.source_observation_key==key)).mappings().one_or_none()
                if existing and (existing['value']!=Decimal(point['close']) or existing['value_basis']!='RAW'):raise ValueError('Existing mock price conflicts; do not overwrite')
                if not existing:c.execute(m.market_data_observation.insert().values(market_data_series_id=series,dataset_id=dataset,
                    market_data_vintage_id=vintage,acquisition_licence_id=licence,source_payload_id=payload,market_date=day,valuation_cut_id=cut,
                    observed_at_utc=stamp,received_at_utc=now,source_published_at_utc=now,value=Decimal(point['close']),value_basis='RAW',
                    quality_status='ACCEPTED',source_observation_key=key,source_payload_reference=artifact.as_uri()))
            for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
                if not load_rights(c,dataset,activity,date.today(),'PERSONAL').allowed:raise ValueError('Synthetic rights incomplete for '+activity)
            assert_dataset_display(c,TENANT,{dataset},series_contexts=[(dataset,series)])
            audit(c,ACTOR,TENANT,'MOCK_BOND_PRICES_PREPARED',dict(strategyId=str(STRATEGY),instrumentId=str(BOND),datasetId=str(dataset),seriesId=str(series),artifactHash=digest))
        policy=api('market-data/valuation-policies',dict(policyCode=PREFIX,displayName='MOCK bond EOD - synthetic only',
            valuationCutId=str(cut),strategyId=str(STRATEGY),validFrom=START.isoformat(),selectionMode='STRICT',rules=[dict(
                ruleSequence=1,subjectReferenceNodeId=str(BOND),marketDataSeriesId=str(series),datasetId=str(dataset),seriesType='CLOSE',
                pricingConvention='EXPLICIT_TIME',pricingCutId=str(cut),marketCalendarId=str(calendar['market_calendar_id']),valueBasis='RAW',priceRequirement='AS_TRADED',
                selectionMethod='LAST_BEFORE_CUT',maxStalenessBusinessDays=0)]),PREFIX+'-POLICY-OTC-V2')
        # Managed versions are immutable, including status. Keep v1 as retained
        # setup history and tell the operator to select this explicit-time v2.
        for day in ('2026-09-30','2026-10-01'):
            api('valuation/accrual-inputs',dict(strategyId=str(STRATEGY),instrumentId=str(BOND),valueDate=day,
                currencyId=str(currency),dailyEarned=evidence['dailyEarnedInterest'],sourceReference='MOCK ONLY - '+PREFIX+'; illustrative position-level daily assessment'),PREFIX+'-INTEREST-'+day)
        result=dict(policyId=policy['valuationPolicyId'],policyLabel='MOCK bond EOD - synthetic only - '+PREFIX+' - v'+str(policy['versionNo']),
            cutId=str(cut),datasetId=str(dataset),seriesId=str(series),strategyId=str(STRATEGY),openingDate='2026-09-29',closingDate='2026-09-30',reportingCurrency='GBP')
        if args.calculate:
            attempt=api('valuation/attempts',dict(strategyId=str(STRATEGY),policyId=policy['valuationPolicyId'],cutId=str(cut),
                reportingCurrencyId=str(currency),openingDate='2026-09-29',closingDate='2026-09-30'),PREFIX+'-VALIDATE-20260930-OTC-V2')
            if attempt['attempt']['status']!='COMPLETED' or not attempt['batch'] or attempt['batch']['status']!='STAGED':raise ValueError('No completed staged valuation')
            summary=attempt['batch']['summary']
            if Decimal(summary['marketPnl'])!=500 or Decimal(summary['grossPnl'])!=510:raise ValueError('Mock valuation differs from hand calculation: '+str(summary))
            result.update(attemptId=attempt['attempt']['attempt_id'],batchId=attempt['batch']['batch_id'],marketPnl=summary['marketPnl'],grossPnl=summary['grossPnl'],status='COMPLETED + STAGED')
        print(json.dumps(result))
    finally:engine.dispose()


if __name__=='__main__':main()
